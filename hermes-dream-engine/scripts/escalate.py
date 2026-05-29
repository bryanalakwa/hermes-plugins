"""Shared escalation handling for dream engine plugins.

Provides a platform-agnostic interface for:
- Queueing escalations (from daemon)
- Fetching pending escalations (for any platform adapter)
- Resolving escalations (user response)
- Formatting escalation messages

This module can be used by any agent/gateway without Telegram-specific coupling.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Path resolution
# ============================================================================

def get_escalation_path() -> Path:
    """Return the escalation inbox path, preferring HERMES_HOME if set."""
    try:
        from hermes_constants import get_hermes_home
        home = get_hermes_home()
    except ImportError:
        home = Path(os.environ.get("HERMES_HOME", "")).strip()
        if not home:
            home = Path.home() / ".hermes"
        home = Path(home)
    return home / "dream_engine" / "escalation_inbox.json"


def _ensure_escalation_path() -> None:
    """Ensure the escalation inbox file exists with valid JSON."""
    path = get_escalation_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]", ensure_ascii=False)


# ============================================================================
# Core operations
# ============================================================================

def queue_escalation(
    action_id: str,
    session_id: str,
    items: List[Dict[str, Any]],
    chat_id: Optional[str] = None,
) -> None:
    """Add an escalation to the inbox for delivery.

    Args:
        action_id: Unique identifier for this escalation (first 8 chars of session_id)
        session_id: Full session ID for reference
        items: List of dicts with 'item' and 'significance' keys
        chat_id: Optional target chat (defaults to home channel)
    """
    _ensure_escalation_path()
    path = get_escalation_path()

    try:
        inbox = json.loads(path.read_text())
    except Exception:
        inbox = []

    entry = {
        "action_id": action_id,
        "session_id": session_id,
        "items": items,
        "timestamp": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        "delivered": False,
    }
    if chat_id:
        entry["chat_id"] = str(chat_id)

    inbox.append(entry)
    path.write_text(json.dumps(inbox, indent=2, ensure_ascii=False))
    logger.info("Escalation queued: %s (%d items)", action_id, len(items))


def get_pending() -> List[Dict[str, Any]]:
    """Return all undelivered escalations from the inbox."""
    path = get_escalation_path()
    if not path.exists():
        return []

    try:
        inbox = json.loads(path.read_text())
        return [e for e in inbox if not e.get("delivered")]
    except Exception:
        return []


def mark_delivered(action_id: str, delivered_at: Optional[str] = None) -> bool:
    """Mark an escalation as delivered. Returns True if found and updated."""
    path = get_escalation_path()
    if not path.exists():
        return False

    try:
        inbox = json.loads(path.read_text())
        for entry in inbox:
            if entry.get("action_id") == action_id:
                entry["delivered"] = True
                if delivered_at:
                    entry["delivered_at"] = delivered_at
                path.write_text(json.dumps(inbox, indent=2, ensure_ascii=False))
                return True
        return False
    except Exception as exc:
        logger.debug("Failed to mark escalation delivered: %s", exc)
        return False


def resolve_escalation(action_id: str, resolution: str) -> bool:
    """Mark an escalation as resolved (ignored, or with guidance).

    Args:
        action_id: The escalation action_id
        resolution: "ignored" or the user's guidance text

    Returns True if found and updated.
    """
    path = get_escalation_path()
    if not path.exists():
        return False

    try:
        inbox = json.loads(path.read_text())
        for entry in inbox:
            if entry.get("action_id") == action_id:
                entry["delivered"] = True
                entry["resolution"] = resolution
                path.write_text(json.dumps(inbox, indent=2, ensure_ascii=False))
                return True
        return False
    except Exception as exc:
        logger.debug("Failed to resolve escalation %s: %s", action_id, exc)
        return False


def resolve_escalation_item(
    session_id: str,
    item_index: int,
    resolution: str,  # "ignore", or custom guidance text
) -> bool:
    """Resolve a single item within an escalation.

    Args:
        session_id: Full session ID (used to find action_id)
        item_index: 1-based index of the specific item
        resolution: "ignore" or guidance text for this item

    Returns True if found and updated.
    """
    path = get_escalation_path()
    if not path.exists():
        return False

    action_id = session_id[:8]

    try:
        inbox = json.loads(path.read_text())
        for entry in inbox:
            if entry.get("action_id") == action_id:
                # Track per-item resolutions
                if "item_resolutions" not in entry:
                    entry["item_resolutions"] = {}

                items = entry.get("items", [])
                if 1 <= item_index <= len(items):
                    entry["item_resolutions"][str(item_index)] = resolution

                    # Remove delivered items (they're done)
                    remaining = [
                        i for i, item in enumerate(items, 1)
                        if str(i) not in entry.get("item_resolutions", {})
                    ]

                    # If all items resolved, mark as fully delivered
                    if not remaining:
                        entry["delivered"] = True
                        entry["resolution"] = "all_items_resolved"

                path.write_text(json.dumps(inbox, indent=2, ensure_ascii=False))
                return True
        return False
    except Exception as exc:
        logger.debug("Failed to resolve escalation item %s[%d]: %s", action_id, item_index, exc)
        return False


# ============================================================================
# Message formatting
# ============================================================================

def format_escalation_message(
    action_id: str,
    session_id: str,
    items: List[Dict[str, Any]],
) -> str:
    """Format an escalation for display in a platform message.

    Args:
        action_id: Short ID for display
        session_id: Full session ID for reference
        items: List of escalation item dicts

    Returns formatted markdown/text message.
    """
    lines = [
        f"🔔 **Dream Escalation**",
        f"Session `{session_id[:8]}` — {len(items)} item(s) need your attention:",
        "",
    ]

    for i, item in enumerate(items, 1):
        significance = item.get("significance", "?")
        text = item.get("item", "")
        # Truncate long items for readability
        if len(text) > 200:
            text = text[:197] + "..."
        lines.append(f"  {i}. [{significance}/5] {text}")

    lines.append("")
    lines.append("Reply with the item number, or use the buttons below.")
    return "\n".join(lines)


# ============================================================================
# Integration helpers
# ============================================================================

def extract_items_from_phase_output(phase_output: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract escalation items from dream_log phase output.

    Args:
        phase_output: The dream_log phase output dict

    Returns list of item dicts, or empty list if no escalations.
    """
    action_plan = phase_output.get("action_plan", {}) or {}
    escalate = action_plan.get("escalate", []) or []
    return escalate if isinstance(escalate, list) else []