"""Dream daemon — the autonomous loop that drives the state machine.

The daemon runs in a background thread and:
1. Ticks every N seconds to check timers and state transitions
2. Manages the dream gate (quota check, midnight reset)
3. Triggers LLM-driven dream sessions when the state machine enters DREAMING
4. Persists state to disk for crash recovery

Dream phase execution is LLM-driven, not scripted:
- The daemon writes context files with memories, facts, and phase prompts
- A cron job is triggered that runs the Hermes agent on each phase
- The agent's output is collected and written to the journal
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from .activity_monitor import ActivityMonitor
except ImportError:
    from activity_monitor import ActivityMonitor
try:
    from .dream_state import DEFAULT_CONFIG, DreamState
except ImportError:
    from dream_state import DEFAULT_CONFIG, DreamState
try:
    from .dream_engine import DreamEngine
except ImportError:
    from dream_engine import DreamEngine
try:
    from .state_machine import DreamStateMachine
except ImportError:
    from state_machine import DreamStateMachine

logger = logging.getLogger(__name__)


class DreamDaemon:
    """Autonomous daemon that runs the dream state machine."""

    def __init__(self, config: dict, state_path: Path, journal_path: Path,
                 memory_source_path: Optional[Path] = None):
        self._config = {**DEFAULT_CONFIG, **config}
        self._state_path = Path(state_path)
        self._journal_path = Path(journal_path)
        self._memory_source_path = Path(memory_source_path) if memory_source_path else None
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._journal_path.parent.mkdir(parents=True, exist_ok=True)

        # Core components
        self._monitor = ActivityMonitor(self._config)
        self._state_machine = DreamStateMachine()
        self._engine = DreamEngine(
            journal_path,
            self._memory_source_path,
        )

        # Daemon control
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._tick_interval = 10  # seconds between timer checks
        self._dreams_today = 0
        self._last_quota_date = ""

        # Load persisted state
        self._load_state()

    # ── lifecycle ──────────────────────────────────────────

    def start(self) -> None:
        """Start the daemon background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("dream daemon started")

    def stop(self) -> None:
        """Stop the daemon and save state."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=30)
        self._save_state()
        logger.info("dream daemon stopped")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ── public API (called by hooks and dashboard) ─────────

    def heartbeat(self) -> None:
        """Record an activity heartbeat. Called by plugin hooks."""
        self._monitor.heartbeat()
        self._state_machine.on_heartbeat(time.time())
        self._save_state()

    def get_status(self) -> dict:
        """Return full daemon status for the dashboard."""
        self._check_quota_reset()
        # Get cognitive budget from engine (if available)
        cb = getattr(self._engine, '_cognitive_budget', None) or {}
        return {
            "state": self._state_machine.state.value,
            "monitor": self._monitor.snapshot(),
            "dreams_today": self._dreams_today,
            "max_dreams": self._config["max_dreams_per_day"],
            "dream_running": self._engine.is_running,
            "transitions": self._state_machine.get_transitions(20),
            "config": {
                "T1_idle": self._config["idle_threshold_seconds"],
                "T2_dormant": self._config["dormant_threshold_seconds"],
                "T3_soak": self._config["soak_threshold_seconds"],
                "T4_hypnagogic": self._config["hypnagogic_duration_seconds"],
                "max_dreams": self._config["max_dreams_per_day"],
                # Cognitive budget info
                "depth": cb.get("depth_label", "adaptive"),
                "richness": cb.get("richness_score", None),
            },
        }

    def force_dream(self) -> Optional[str]:
        """Manually trigger a dream session (for testing/dashboard).
        Returns the session ID or None if blocked."""
        self._check_quota_reset()
        if self._dreams_today >= self._config["max_dreams_per_day"]:
            return None
        self._monitor.reset_all()
        self._monitor.start_hypnagogic()
        self._state_machine._transition_to(
            DreamState.HYPNAGOGIC, "manual trigger", time.time()
        )
        # Immediately transition to dreaming
        self._state_machine._transition_to(
            DreamState.DREAMING, "manual trigger — skip hypnagogic", time.time()
        )
        return self._run_dream_session()

    def clear_state(self) -> None:
        """Reset all state (for testing)."""
        self._dreams_today = 0
        self._monitor.reset_all()
        self._state_machine._transition_to(
            DreamState.ACTIVE, "manual reset", time.time()
        )
        self._save_state()

    # ── main loop ──────────────────────────────────────────

    def _run_loop(self) -> None:
        """Main daemon loop — ticks every N seconds."""
        logger.info("dream daemon loop starting")
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception:
                logger.exception("daemon tick error")
            self._stop_event.wait(self._tick_interval)
        logger.info("dream daemon loop ended")

    def _tick(self) -> None:
        """Single tick — check timers and advance state machine."""
        now = time.time()
        self._check_quota_reset()

        state = self._state_machine.state

        if state == DreamState.ACTIVE:
            if self._monitor.is_idle():
                self._state_machine.on_idle_timeout(now)

        elif state == DreamState.IDLE:
            if not self._monitor.is_idle():
                self._state_machine.on_heartbeat(now)
            elif self._monitor.is_dormant():
                self._state_machine.on_dormant_timeout(now)
                self._monitor.start_soak()

        elif state == DreamState.DORMANT:
            if self._monitor.is_soak_complete():
                t = self._state_machine.on_soak_complete(
                    now, self._dreams_today, self._config["max_dreams_per_day"]
                )
                if t and t.to_state == DreamState.DORMANT:
                    self._monitor.reset_soak()
                elif t and t.to_state == DreamState.HYPNAGOGIC:
                    self._monitor.start_hypnagogic()

        elif state == DreamState.HYPNAGOGIC:
            if self._monitor.is_hypnagogic_complete():
                t = self._state_machine.on_hypnagogic_complete(now)
                if t:
                    self._run_dream_session()

        elif state == DreamState.DREAMING:
            pass

        self._save_state()

    # ── dream session runner (LLM-driven) ──────────────────

    def _run_dream_session(self) -> Optional[str]:
        """Execute a full dream session. Called when state enters DREAMING."""
        logger.info("starting dream session")
        try:
            session = self._engine.start_session()
            session = self._engine.run_all_phases()
            self._dreams_today += 1
            self._state_machine.on_dream_complete(time.time())
            logger.info(
                "dream session %s complete (%d/%d today)",
                session.session_id, self._dreams_today,
                self._config["max_dreams_per_day"],
            )
            # Escalate high-priority items to the user via Telegram
            self._escalate_to_user(session)
            return session.session_id
        except Exception:
            logger.exception("dream session failed")
            self._state_machine.on_dream_complete(time.time())
            return None

    def _escalate_to_user(self, session) -> None:
        """Send escalated action plan items to the user via Telegram.

        Called after each dream session completes. Only sends if there
        are items in the 'escalate' list of the dream_log action_plan.
        """
        try:
            dream_log_output = session.phase_outputs.get("dream_log", {})
            action_plan = dream_log_output.get("action_plan", {})
            escalate_items = action_plan.get("escalate", [])
            if not escalate_items:
                return

            # Build the escalation message
            lines = [
                "🔔 **Dream Escalation**",
                f"Session `{session.session_id}` — {len(escalate_items)} item(s) need your attention:",
                "",
            ]
            for i, item in enumerate(escalate_items, 1):
                text = item.get("item", str(item)) if isinstance(item, dict) else str(item)
                sig = item.get("significance", "?") if isinstance(item, dict) else "?"
                lines.append(f"  {i}. [{sig}/5] {text}")
            lines.append("")
            lines.append("Reply with the number to address an item, or /ignore to dismiss.")

            message = "\n".join(lines)

            # Try sending via the Hermes gateway REST API
            self._send_via_gateway(message)

        except Exception:
            logger.exception("escalation send failed — non-critical")

    def _send_via_gateway(self, message: str) -> None:
        """Send a message through the Hermes gateway to the user's Telegram.

        Uses the gateway's REST API at localhost:9119. Falls back to
        writing to the escalation file if the gateway is unreachable.
        """
        import urllib.request
        import urllib.error

        # Try the gateway's agent-invoke endpoint first
        try:
            payload = json.dumps({
                "message": message,
                "session_id": "dream-escalation",
                "deliver": "telegram",
            }).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:9119/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            # Use a short timeout — don't block the daemon
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status in (200, 201, 202):
                    logger.info("escalation sent via gateway")
                    return
        except Exception as e:
            logger.debug("gateway send failed: %s", e)

        # Fallback: write to escalation inbox file
        try:
            escalation_path = self._state_path.parent / "escalation_inbox.json"
            inbox = []
            if escalation_path.exists():
                inbox = json.loads(escalation_path.read_text())
            inbox.append({
                "message": message,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "delivered": False,
            })
            escalation_path.write_text(json.dumps(inbox, indent=2, ensure_ascii=False))
            logger.info("escalation written to inbox file (gateway unavailable)")
        except Exception:
            logger.exception("escalation fallback write failed")

    def _on_wakeup(self, timestamp: float) -> None:
        """Called when a heartbeat arrives during DORMANT/HYPNAGOGIC/DREAMING."""
        logger.info("wakeup signal at %.0f", timestamp)
        if self._engine.is_running:
            self._engine.interrupt()
        self._state_machine.on_heartbeat(timestamp)

    # ── quota management ───────────────────────────────────

    def _check_quota_reset(self) -> None:
        """Reset dreams_today at midnight local time."""
        today = time.strftime("%Y-%m-%d")
        if today != self._last_quota_date:
            if self._last_quota_date:
                logger.info("quota reset (new day: %s)", today)
                self._dreams_today = 0
            self._last_quota_date = today

    # ── persistence ────────────────────────────────────────

    def _load_state(self) -> None:
        """Load persisted state from disk."""
        if not self._state_path.exists():
            return
        try:
            data = json.loads(self._state_path.read_text())
            self._dreams_today = data.get("dreams_today", 0)
            self._last_quota_date = data.get("last_quota_date", "")
            # Restore persisted config overrides (survives config.yaml edits)
            persisted_config = data.get("config", {})
            if persisted_config:
                self._config.update(persisted_config)
        except Exception:
            logger.warning("failed to load state from %s", self._state_path)

    def _save_state(self) -> None:
        """Persist state to disk."""
        try:
            self._state_path.write_text(json.dumps({
                "state": self._state_machine.state.value,
                "dreams_today": self._dreams_today,
                "last_quota_date": self._last_quota_date,
                "config": self._config,
                "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }, ensure_ascii=False))
        except Exception:
            logger.warning("failed to save state")
