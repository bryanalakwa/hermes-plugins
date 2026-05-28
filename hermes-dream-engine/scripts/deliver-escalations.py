#!/usr/bin/env python3
"""Deliver pending dream escalations via Telegram with interactive commands.

This formats escalations with clear reply commands for the user:
- /ignore <id> - Dismiss this escalation
- /proceed <id> - Have the agent proceed with the suggested action  
- /other <id> <text> - Provide custom guidance

Usage: Run manually or via cron to deliver pending escalations.
"""

import json
import sys
from pathlib import Path

HERMES_HOME = Path.home() / ".hermes"
ESCALATION_FILE = HERMES_HOME / "dream_engine" / "escalation_inbox.json"

def extract_escalation_items(message: str) -> list:
    """Extract numbered escalation items from message format."""
    items = []
    lines = message.split('\n')
    in_items = False
    for line in lines:
        if 'need your attention' in line.lower() or 'item(s) need' in line.lower():
            in_items = True
            continue
        if in_items and line.strip() and line.strip().startswith(('1.', '2.', '3.', '4.', '5.')):
            # Parse "  1. [5/5] item text" format
            parts = line.strip().split(' ', 2)
            if len(parts) >= 3:
                items.append({
                    'num': parts[0].rstrip('.'),
                    'significance': parts[1].strip('[]'),
                    'text': parts[2] if len(parts) > 2 else ''
                })
    return items

def format_escalation_with_commands(entry: dict, index: int) -> str:
    """Format escalation with interactive command buttons."""
    msg = entry.get("message", "")
    timestamp = entry.get("timestamp", "")
    
    items = extract_escalation_items(msg)
    
    # Build response with button-like commands
    formatted = f"""🔔 **Dream Escalation** #{index}
⏰ {timestamp}

{msg}

---
**Your options:**
• `/ignore {index}` — Dismiss this escalation
"""
    
    # Add proceed commands for each item
    for item in items:
        formatted += f"• `/proceed {index} {item['num']}` — Do: {item['text'][:60]}...\n"
    
    formatted += f"• `/other {index} <your guidance>` — Tell me what to do instead\n"
    
    return formatted

def main():
    if not ESCALATION_FILE.exists():
        print("No escalation inbox found")
        return 0
    
    with open(ESCALATION_FILE) as f:
        inbox = json.load(f)
    
    pending = [e for e in inbox if not e.get("delivered")]
    
    if not pending:
        print("No pending escalations")
        return 0
    
    print(f"Found {len(pending)} pending escalations to deliver\n")
    
    for i, entry in enumerate(pending, 1):
        print(format_escalation_with_commands(entry, i))
        print("\n" + "="*60 + "\n")
    
    return len(pending)

if __name__ == "__main__":
    count = main()
    sys.exit(0 if count == 0 else 1)  # Exit 1 if there were escalations (triggers delivery)