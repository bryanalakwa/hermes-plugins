#!/usr/bin/env python3
"""Deliver pending dream escalations via Telegram with inline buttons.

Each escalation item gets its own message with per-item buttons:
- ❌ Ignore — dismiss this specific item
- ✅ Accept — have the agent proceed with this item  
- ✏️ Other — provide custom guidance for this item

Usage: Run manually or via cron to deliver pending escalations.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

try:
    from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.constants import ParseMode
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

HERMES_HOME = Path.home() / ".hermes"
ESCALATION_FILE = HERMES_HOME / "dream_engine" / "escalation_inbox.json"


def get_telegram_token() -> Optional[str]:
    """Get Telegram bot token from environment or config."""
    for var in ["TELEGRAM_BOT_TOKEN", "TG_BOT_TOKEN", "BOT_TOKEN"]:
        val = os.environ.get(var)
        if val:
            return val
    return None


async def send_single_item_with_buttons(
    chat_id: str,
    session_id: str,
    item: Dict[str, Any],
    item_index: int,
    bot_token: str,
) -> bool:
    """Send a single escalation item with its own inline buttons."""
    if not TELEGRAM_AVAILABLE:
        return False

    bot = Bot(token=bot_token)

    action_id = session_id[:8]
    text = item.get("item", str(item))
    sig = item.get("significance", "?")

    # Escape HTML special chars
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Build message
    text_lines = [
        f"🔔 <b>Dream Escalation</b> #{action_id}",
        f"⏰ <i>{time.strftime('%Y-%m-%d %H:%M:%S')}</i>",
        "",
        f"<b>Item {item_index}.</b> [{sig}/5] {text}",
    ]

    text_str = "\n".join(text_lines)

    # Build inline keyboard for this specific item
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❌ Ignore", callback_data=f"esc:ignore:{session_id}:{item_index}"),
            InlineKeyboardButton("✅ Accept", callback_data=f"esc:proceed:{session_id}:{item_index}"),
        ],
        [
            InlineKeyboardButton("✏️ Other", callback_data=f"esc:other:{session_id}:{item_index}"),
        ],
    ])

    try:
        await bot.send_message(
            chat_id=int(chat_id),
            text=text_str,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_notification=True,
        )
        return True
    except Exception as e:
        print(f"Error sending escalation item {item_index}: {e}", file=sys.stderr)
        return False


def load_pending_escalations() -> List[dict]:
    """Load undelivered escalations from inbox."""
    if not ESCALATION_FILE.exists():
        return []

    with open(ESCALATION_FILE) as f:
        inbox = json.load(f)

    return [e for e in inbox if not e.get("delivered")]


def mark_delivered(entry: dict) -> None:
    """Mark an escalation entry as delivered."""
    path = ESCALATION_FILE
    if not path.exists():
        return

    inbox = json.loads(path.read_text())
    for e in inbox:
        if e.get("action_id") == entry.get("action_id"):
            e["delivered"] = True
            e["delivered_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    path.write_text(json.dumps(inbox, indent=2, ensure_ascii=False))


def main():
    """Main entry point for escalation delivery."""
    if not TELEGRAM_AVAILABLE:
        print("python-telegram-bot not installed. Install with: pip install python-telegram-bot")
        return 1

    token = get_telegram_token()
    if not token:
        print("No Telegram bot token found. Set TELEGRAM_BOT_TOKEN env var.")
        return 1

    pending = load_pending_escalations()
    if not pending:
        print("No pending escalations")
        return 0

    import asyncio

    async def send_all():
        sent_count = 0
        for entry in pending:
            session_id = entry.get("session_id", entry.get("action_id", "unknown"))
            items = entry.get("items", [])
            chat_id = entry.get("chat_id") or "467058917"  # Default to home channel

            # Skip if no items
            if not items:
                print(f"Skipping {session_id[:8]} - no items for inline buttons")
                continue

            # Send each item as a separate message
            for i, item in enumerate(items, 1):
                success = await send_single_item_with_buttons(
                    chat_id=chat_id,
                    session_id=session_id,
                    item=item,
                    item_index=i,
                    bot_token=token,
                )
                if success:
                    sent_count += 1

            # Mark as delivered
            if sent_count > 0:
                mark_delivered(entry)

    asyncio.run(send_all())
    print(f"Delivered {sent_count} escalation items with inline buttons")
    return 0


if __name__ == "__main__":
    sys.exit(main())