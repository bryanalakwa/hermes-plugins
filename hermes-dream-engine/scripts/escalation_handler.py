#!/usr/bin/env python3
"""Escalation delivery handler - adapts to messaging gateway capabilities.

This provides a unified interface for dream engine escalations:
- Detects available messaging platforms from config
- Formats messages appropriately for each platform
- For Telegram: uses reply commands (buttons via slash commands)
- For other platforms: plain text with clear action hints
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

HERMES_HOME = Path.home() / ".hermes"
ESCALATION_FILE = HERMES_HOME / "dream_engine" / "escalation_inbox.json"

def load_config() -> dict:
    """Load config.yaml to find platform settings."""
    config_path = HERMES_HOME / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        import yaml
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

def get_preferred_platform(config: dict) -> Optional[str]:
    """Detect preferred messaging platform from config."""
    platforms = config.get("platforms", {})
    
    # Check which platforms are enabled
    for platform in ["telegram", "discord", "slack"]:
        if platforms.get(platform, {}).get("enabled"):
            return platform
    
    return None

def format_escalation_for_telegram(message: str, session_id: str, items: List[dict]) -> str:
    """Format escalation with Telegram reply commands (acts like buttons)."""
    action_id = session_id[:8] if session_id else str(uuid.uuid4())[:8]
    
    # Parse items from the message if not provided
    if not items:
        lines = message.split('\n')
        for line in lines:
            if line.strip() and line.strip()[0].isdigit():
                items.append({"raw": line.strip()})
    
    formatted = f"""🔔 *Dream Escalation* #{action_id}
⏰ _{time.strftime('%Y-%m-%d %H:%M:%S')}_

*{len(items)} item(s) need your attention:*

"""
    
    for i, item in enumerate(items, 1):
        if isinstance(item, dict):
            text = item.get("item", item.get("raw", ""))
            sig = item.get("significance", "?")
            formatted += f"*{i}.* [{sig}/5] {text}\n\n"
        else:
            formatted += f"*{i}.* {item}\n\n"
    
    formatted += f"""
*Choose action:*
/ignore_{action_id} — Dismiss all
/proceed_{action_id} — Address item (reply with number)
/other_{action_id} <answer> — Provide custom guidance
"""
    return formatted

def format_escalation_generic(message: str, session_id: str) -> str:
    """Format escalation for non-Telegram platforms."""
    action_id = session_id[:8] if session_id else str(uuid.uuid4())[:8]
    
    return f"""🔔 Dream Escalation #{action_id}
Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}

{message}

Actions: ignore_{action_id} | proceed_{action_id} | other_{action_id}"""

def create_escalation_entry(session_id: str, items: List[dict]) -> dict:
    """Create a properly formatted escalation entry."""
    action_id = session_id[:8]
    message_lines = [
        f"🔔 **Dream Escalation** #{action_id}",
        f"⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Session `{session_id}` — {len(items)} item(s) need your attention:",
        "",
    ]
    
    for i, item in enumerate(items, 1):
        text = item.get("item", str(item)) if isinstance(item, dict) else str(item)
        sig = item.get("significance", "?") if isinstance(item, dict) else "?"
        message_lines.append(f"  {i}. [{sig}/5] {text}")
    
    message_lines.append("")
    message_lines.append(f"**Your options:**")
    message_lines.append(f"• `/ignore_{action_id}` — Dismiss this escalation")
    message_lines.append(f"• `/proceed_{action_id} <num>` — Do action # (e.g., `/proceed_{action_id} 1`)")
    message_lines.append(f"• `/other_{action_id} <text>` — Give custom guidance")
    
    return {
        "message": "\n".join(message_lines),
        "action_id": action_id,
        "session_id": session_id,
        "items": items,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "delivered": False,
        "platform": get_preferred_platform(load_config())
    }

def deliver_escalation_via_send_message(message: str, action_id: str, platform: Optional[str]) -> bool:
    """Attempt to deliver via send_message tool (requires agent context).
    
    Returns True if delivery attempted, False if would fallback to inbox.
    """
    # This function would be called from within an agent context
    # where send_message tool is available
    # For now, we just write to the inbox
    return False

def queue_escalation(session_id: str, items: List[dict]) -> dict:
    """Queue an escalation for delivery."""
    entry = create_escalation_entry(session_id, items)
    
    # Load existing inbox
    inbox = []
    if ESCALATION_FILE.exists():
        try:
            with open(ESCALATION_FILE) as f:
                inbox = json.load(f)
        except Exception:
            inbox = []
    
    inbox.append(entry)
    ESCALATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ESCALATION_FILE, "w") as f:
        json.dump(inbox, f, indent=2, ensure_ascii=False)
    
    return entry

def get_pending_escalations() -> List[dict]:
    """Get all undelivered escalations."""
    if not ESCALATION_FILE.exists():
        return []
    
    try:
        with open(ESCALATION_FILE) as f:
            inbox = json.load(f)
        return [e for e in inbox if not e.get("delivered")]
    except Exception:
        return []

def mark_delivered(action_id: str) -> bool:
    """Mark escalations as delivered by action_id."""
    if not ESCALATION_FILE.exists():
        return False
    
    try:
        with open(ESCALATION_FILE) as f:
            inbox = json.load(f)
        
        updated = False
        for entry in inbox:
            if entry.get("action_id") == action_id or entry.get("session_id", "").startswith(action_id):
                entry["delivered"] = True
                entry["delivered_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                updated = True
        
        if updated:
            with open(ESCALATION_FILE, "w") as f:
                json.dump(inbox, f, indent=2, ensure_ascii=False)
        
        return updated
    except Exception:
        return False

def main():
    """Demo/test function."""
    config = load_config()
    platform = get_preferred_platform(config)
    
    pending = get_pending_escalations()
    print(f"Pending escalations: {len(pending)}")
    print(f"Preferred platform: {platform or 'none detected'}")
    
    for entry in pending[-3:]:
        print(f"\n--- {entry.get('action_id')} ---")
        print(entry.get("message", "")[:500])

if __name__ == "__main__":
    main()