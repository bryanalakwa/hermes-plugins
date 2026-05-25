"""Heartbeat tracking and activity detection for the dream engine.

The activity monitor is the "sensory system" of the dreaming plugin.
It receives heartbeats from the agent's I/O boundary (via plugin hooks)
and tracks whether the agent is active, idle, or dormant.

Thread-safe: all mutations are protected by a lock so heartbeat callbacks
from the gateway thread and timer checks in the daemon thread cannot race.
"""

import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ActivityMonitor:
    """Tracks agent activity via heartbeats and manages timer thresholds.

    States (external, managed by the state machine):
      - last_heartbeat: timestamp of the most recent activity event
      - current_state:  the agent's current sleep/wake state
      - soak_elapsed:   seconds spent continuously in DORMANT
      - hypnagogic_elapsed: seconds spent in HYPNAGOGIC phase

    All elapsed counters are derived from timestamps, not accumulated,
    so they are immune to drift or missed ticks.
    """

    def __init__(self, config: dict):
        self._lock = threading.Lock()
        self._idle_threshold = config.get("idle_threshold_seconds", 300)
        self._dormant_threshold = config.get("dormant_threshold_seconds", 1800)
        self._soak_threshold = config.get("soak_threshold_seconds", 3000)
        self._hypnagogic_duration = config.get("hypnagogic_duration_seconds", 120)
        self._last_heartbeat: float = time.time()
        self._soak_start: Optional[float] = None
        self._hypnagogic_start: Optional[float] = None
        self._wakeup_callbacks: list[Callable] = []

    # ── public API ──────────────────────────────────────────

    def heartbeat(self) -> float:
        """Record an activity event. Returns the timestamp.

        Called by hook handlers at the entry point of every I/O handler.
        Resets soak and hypnagogic timers.
        """
        now = time.time()
        with self._lock:
            was_dormant = self._soak_start is not None
            self._last_heartbeat = now
            self._soak_start = None
            self._hypnagogic_start = None
        # Fire callbacks outside the lock to avoid deadlocks
        if was_dormant:
            for cb in self._wakeup_callbacks:
                try:
                    cb(now)
                except Exception:
                    logger.exception("wakeup callback error")
        logger.debug("heartbeat recorded at %.0f", now)
        return now

    def register_wakeup_callback(self, callback: Callable) -> None:
        """Register a callable that fires when a heartbeat arrives
        during DORMANT, HYPNAGOGIC, or DREAMING state."""
        self._wakeup_callbacks.append(callback)

    # ── timer queries (called by daemon tick) ───────────────

    def seconds_since_heartbeat(self) -> float:
        """Wall-clock seconds since the last heartbeat."""
        return time.time() - self._last_heartbeat

    def is_idle(self) -> bool:
        """True if no heartbeat for >= T1 (idle threshold)."""
        return self.seconds_since_heartbeat() >= self._idle_threshold

    def is_dormant(self) -> bool:
        """True if no heartbeat for >= T2 (dormant threshold, cumulative
        from last heartbeat — not from entering IDLE)."""
        return self.seconds_since_heartbeat() >= self._dormant_threshold

    def start_soak(self) -> None:
        """Mark the beginning of the soak period (entered DORMANT)."""
        with self._lock:
            self._soak_start = time.time()
        logger.info("soak started (T3=%ds)", self._soak_threshold)

    def start_hypnagogic(self) -> None:
        """Mark the beginning of the hypnagogic prep phase."""
        with self._lock:
            self._hypnagogic_start = time.time()
        logger.info("hypnagogic started (T4=%ds)", self._hypnagogic_duration)

    def is_soak_complete(self) -> bool:
        """True if soak timer has reached T3 without a heartbeat."""
        if self._soak_start is None:
            return False
        return (time.time() - self._soak_start) >= self._soak_threshold

    def is_hypnagogic_complete(self) -> bool:
        """True if hypnagogic timer has reached T4."""
        if self._hypnagogic_start is None:
            return False
        return (time.time() - self._hypnagogic_start) >= self._hypnagogic_duration

    def reset_soak(self) -> None:
        """Reset soak timer to zero (used when dream gate blocks)."""
        with self._lock:
            self._soak_start = time.time()

    def reset_all(self) -> None:
        """Full reset — call on heartbeat or wakeup."""
        now = time.time()
        with self._lock:
            self._last_heartbeat = now
            self._soak_start = None
            self._hypnagogic_start = None

    # ── status snapshot ─────────────────────────────────────

    def snapshot(self) -> dict:
        """Return a JSON-serializable status dict."""
        now = time.time()
        with self._lock:
            return {
                "last_heartbeat": self._last_heartbeat,
                "last_ago_seconds": round(now - self._last_heartbeat, 1),
                "is_idle": self.is_idle(),
                "is_dormant": self.is_dormant(),
                "soak_start": self._soak_start,
                "soak_elapsed": (
                    round(now - self._soak_start, 1) if self._soak_start else None
                ),
                "hypnagogic_start": self._hypnagogic_start,
                "hypnagogic_elapsed": (
                    round(now - self._hypnagogic_start, 1)
                    if self._hypnagogic_start
                    else None
                ),
                "thresholds": {
                    "T1_idle": self._idle_threshold,
                    "T2_dormant": self._dormant_threshold,
                    "T3_soak": self._soak_threshold,
                    "T4_hypnagogic": self._hypnagogic_duration,
                },
            }
