"""Dream state machine — manages transitions between the 5 states.

States: ACTIVE → IDLE → DORMANT → (gate) → HYPNAGOGIC → DREAMING

The state machine is deliberately separated from the daemon loop:
- This module decides *what state we should be in*
- The daemon loop decides *when to check and act* on state transitions
- The activity_monitor module tracks *timing*

This separation makes the state machine fully testable without threads
or timers.
"""

import logging
import threading
from typing import Callable, Optional

try:
    from .dream_state import DreamState
except ImportError:
    from dream_state import DreamState

logger = logging.getLogger(__name__)


class StateTransition:
    """Represents a single state transition event."""

    def __init__(self, from_state: DreamState, to_state: DreamState,
                 reason: str, timestamp: float):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "from": self.from_state.value,
            "to": self.to_state.value,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


class DreamStateMachine:
    """Manages the 5-state dreaming state machine.

    Transition table (from the spec):
      ACTIVE     → IDLE        when idle_timer >= T1
      IDLE       → ACTIVE      on heartbeat
      IDLE       → DORMANT     when idle_timer >= T2
      DORMANT    → ACTIVE      on heartbeat (wakeup)
      DORMANT    → GATE_CHECK  when soak_timer >= T3
      GATE_CHECK → HYPNAGOGIC  when quota < max
      GATE_CHECK → DORMANT     when quota >= max (reset soak)
      HYPNAGOGIC → DREAMING    when T4 elapsed, no wakeup
      HYPNAGOGIC → ACTIVE      on heartbeat (cancel prep)
      DREAMING   → ACTIVE      on session complete
      DREAMING   → ACTIVE      on heartbeat (save partial)
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._state = DreamState.ACTIVE
        self._transitions: list[StateTransition] = []
        self._on_transition: Optional[Callable] = None

    @property
    def state(self) -> DreamState:
        with self._lock:
            return self._state

    def set_transition_callback(self, callback: Callable) -> None:
        self._on_transition = callback

    def _transition_to(self, new_state: DreamState, reason: str,
                       timestamp: float) -> StateTransition:
        with self._lock:
            old = self._state
            self._state = new_state
        t = StateTransition(old, new_state, reason, timestamp)
        self._transitions.append(t)
        logger.info("state: %s → %s (%s)",
                    old.value, new_state.value, reason)
        if self._on_transition:
            try:
                self._on_transition(t)
            except Exception:
                logger.exception("transition callback error")
        return t

    # ── transition handlers ─────────────────────────────────

    def on_heartbeat(self, timestamp: float) -> Optional[StateTransition]:
        """Process a heartbeat (wakeup signal).

        From any state except ACTIVE, transitions to ACTIVE.
        From DORMANT/HYPNAGOGIC/DREAMING, this is the wakeup signal.
        """
        with self._lock:
            current = self._state

        if current == DreamState.ACTIVE:
            return None  # no transition needed

        # Wakeup from any non-active state
        reason_map = {
            DreamState.IDLE: "heartbeat received in IDLE",
            DreamState.DORMANT: "wakeup signal during DORMANT",
            DreamState.HYPNAGOGIC: "wakeup signal — dream prep cancelled",
            DreamState.DREAMING: "wakeup signal — dream session interrupted",
        }
        reason = reason_map.get(current, f"heartbeat in {current.value}")
        return self._transition_to(DreamState.ACTIVE, reason, timestamp)

    def on_idle_timeout(self, timestamp: float) -> Optional[StateTransition]:
        """T1 exceeded: ACTIVE → IDLE."""
        with self._lock:
            if self._state != DreamState.ACTIVE:
                return None
        return self._transition_to(
            DreamState.IDLE,
            f"T1 idle threshold exceeded",
            timestamp,
        )

    def on_dormant_timeout(self, timestamp: float) -> Optional[StateTransition]:
        """T2 exceeded: IDLE → DORMANT (cumulative from last heartbeat)."""
        with self._lock:
            if self._state != DreamState.IDLE:
                return None
        return self._transition_to(
            DreamState.DORMANT,
            f"T2 dormant threshold exceeded",
            timestamp,
        )

    def on_soak_complete(self, timestamp: float,
                         dreams_today: int,
                         max_dreams: int) -> Optional[StateTransition]:
        """T3 exceeded: DORMANT → GATE CHECK → HYPNAGOGIC or back to DORMANT."""
        with self._lock:
            if self._state != DreamState.DORMANT:
                return None

        if dreams_today < max_dreams:
            return self._transition_to(
                DreamState.HYPNAGOGIC,
                f"dream gate passed ({dreams_today}/{max_dreams} dreams today)",
                timestamp,
            )
        else:
            # Quota exhausted — reset soak and stay dormant
            return self._transition_to(
                DreamState.DORMANT,
                f"dream gate blocked (quota {dreams_today}/{max_dreams})",
                timestamp,
            )

    def on_hypnagogic_complete(self, timestamp: float) -> Optional[StateTransition]:
        """T4 elapsed: HYPNAGOGIC → DREAMING."""
        with self._lock:
            if self._state != DreamState.HYPNAGOGIC:
                return None
        return self._transition_to(
            DreamState.DREAMING,
            f"T4 hypnagogic prep complete",
            timestamp,
        )

    def on_dream_complete(self, timestamp: float) -> Optional[StateTransition]:
        """Dream session finished: DREAMING → ACTIVE."""
        with self._lock:
            if self._state != DreamState.DREAMING:
                return None
        return self._transition_to(
            DreamState.ACTIVE,
            "dream session complete",
            timestamp,
        )

    # ── history ─────────────────────────────────────────────

    def get_transitions(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return [t.to_dict() for t in self._transitions[-limit:]]
