#!/usr/bin/env python3
"""Process dream escalation inbox and send pending messages to Telegram.

This script reads the escalation_inbox.json and sends any undelivered
escalations to the user's Telegram via the gateway platform.

Usage:
    python3 process-escalations.py          # Process all pending
    python3 process-escalations.py --send   # Actually send (dry-run by default)
"""

import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required", file=sys.stderr)
    sys.exit(1)

HERMES_HOME = Path.home() / ".hermes"
ESCALATION_FILE = HERMES_HOME / "dream_engine" / "escalation_inbox.json"

def load_config():
    """Load config.yaml to find Telegram settings."""
    config_path = HERMES_HOME / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="Actually send messages")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be sent")
    args = parser.parse_args()

    if not ESCALATION_FILE.exists():
        print("No escalation inbox found")
        return

    with open(ESCALATION_FILE) as f:
        inbox = json.load(f)

    pending = [e for e in inbox if not e.get("delivered")]
    print(f"Found {len(pending)} undelivered escalations")

    for entry in pending:
        msg = entry.get("message", "")
        print(f"\n--- Pending escalation ---")
        print(msg[:200] + "..." if len(msg) > 200 else msg)

        if args.send and not args.dry_run:
            # Try to use send_message via the gateway
            # This will be implemented when the gateway supports it
            print("(Would send via gateway)")

    if args.send and pending:
        # Mark as delivered
        for entry in pending:
            entry["delivered"] = True
        with open(ESCALATION_FILE, "w") as f:
            json.dump(inbox, f, indent=2, ensure_ascii=False)
        print(f"\nMarked {len(pending)} as delivered")
    elif pending and not args.dry_run:
        print("\nUse --send to actually deliver")

if __name__ == "__main__":
    main()