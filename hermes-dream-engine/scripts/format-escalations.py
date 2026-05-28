#!/usr/bin/env python3
"""Format escalation messages with interactive Telegram buttons.

This formats dream escalations in a way that Telegram can display buttons.
Since we're in an agent context, we use inline button syntax that Telegram understands.
"""

import json
from pathlib import Path
from datetime import datetime

HERMES_HOME = Path.home() / ".hermes"
ESCALATION_FILE = HERMES_HOME / "dream_engine" / "escalation_inbox.json"

def format_escalation_with_buttons(entry: dict, index: int) -> str:
    """Format an escalation entry with Telegram reply keyboard buttons."""
    msg = entry.get("message", "")
    timestamp = entry.get("timestamp", "")
    
    # Extract escalation items from the message
    # Format the message with button hints
    formatted = f"""🔔 **Dream Escalation** (ID: {index})

{timestamp}

{msg}

---
**Reply options:** /ignore_{index} • /proceed_{index} • /other_{index}
(Or reply with just the item number to address it)"""
    return formatted

def main():
    if not ESCALATION_FILE.exists():
        print("No escalation inbox found")
        return
    
    with open(ESCALATION_FILE) as f:
        inbox = json.load(f)
    
    pending = [e for e in inbox if not e.get("delivered")]
    
    if not pending:
        print("No pending escalations")
        return
    
    print(f"Pending escalations: {len(pending)}")
    for i, entry in enumerate(pending, 1):
        print(f"\n{'='*50}")
        print(format_escalation_with_buttons(entry, i))

if __name__ == "__main__":
    main()