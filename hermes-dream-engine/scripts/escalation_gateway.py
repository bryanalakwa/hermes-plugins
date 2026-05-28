"""Escalation gateway handling — integration between dream engine and messaging platforms.

This module provides:
1. A simple text-intercept mechanism for escalation responses
2. Thread-safe storage for pending escalation responses
3. Integration points for platform adapters (Telegram, Discord, etc.)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Module-level state for escalation text capture
# ============================================================================

@dataclass
class _EscalationEntry:
    action_id: str
    session_id: str
    item_num: Optional[int]
    event: threading.Event = field(default_factory=threading.Event)
    response: Optional[str] = None


_lock = threading.RLock()
# action_id → _EscalationEntry
_pending: Dict[str, _EscalationEntry] = {}


def register_escalation_text_capture(
    action_id: str,
    session_id: str,
    item_num: Optional[int] = None,
) -> _EscalationEntry:
    """Register an escalation for text-capture mode.

    Called when user clicks "Other" or an Item button.
    Returns the entry for later resolution.
    """
    with _lock:
        # Remove any existing entry for this action_id
        _pending.pop(action_id, None)
        entry = _EscalationEntry(
            action_id=action_id,
            session_id=session_id,
            item_num=item_num,
        )
        _pending[action_id] = entry
        return entry


def resolve_escalation_response(action_id: str) -> Optional[str]:
    """Get and clear the pending escalation response.

    Called when text-intercept captures user's response.
    Returns the response text, or None if not captured.
    """
    with _lock:
        entry = _pending.get(action_id)
        if entry is None:
            return None
        response = entry.response
        _pending.pop(action_id, None)
        return str(response) if response else None


def set_escalation_response(action_id: str, response: str) -> bool:
    """Set the response on a pending escalation entry.

    Called by text-intercept handler.
    """
    with _lock:
        entry = _pending.get(action_id)
        if entry is None:
            return False
        entry.response = str(response)
        entry.event.set()
        return True


def get_pending_for_message(
    session_key: str,
    chat_id: str,
    thread_id: Optional[str] = None,
) -> Optional[_EscalationEntry]:
    """Check if there's a pending escalation expecting text input.

    This is called by _handle_text_message to detect if the incoming
    message is actually an escalation response.

    Note: This is a simple implementation. A more robust version would
    track the originating chat/thread for proper routing.
    """
    with _lock:
        for entry in _pending.values():
            if entry.response is None:
                return entry
        return None


def clear_escalation(action_id: str) -> int:
    """Clear a pending escalation entry.

    Returns 1 if found and cleared, 0 otherwise.
    """
    with _lock:
        if action_id in _pending:
            _pending.pop(action_id)
            return 1
        return 0