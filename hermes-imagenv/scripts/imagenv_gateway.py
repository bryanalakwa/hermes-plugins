#!/usr/bin/env python3
"""ImaGen Telegram integration — handle inline button callbacks for image generation.

Callback format: img:generate:<safe_prompt> or img:variations:<safe_prompt>:<type>
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, Any

HERMES_HOME = Path.home() / ".hermes"
CACHE_DIR = HERMES_HOME / "cache" / "ImGen"
OUTPUT_DIR = CACHE_DIR / "output"

# Import telegram modules (may fail if not installed)
_telegram_modules: Any
try:
    import telegram
    _telegram_modules = telegram
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


def get_telegram_token() -> Optional[str]:
    """Get Telegram bot token from environment."""
    for var in ["TELEGRAM_BOT_TOKEN", "TG_BOT_TOKEN", "BOT_TOKEN"]:
        val = os.environ.get(var)
        if val:
            return val
    return None


def create_inline_buttons(prompt: str) -> Any:
    """Create inline buttons for image generation options."""
    if not TELEGRAM_AVAILABLE:
        return None
    
    # Sanitize prompt for callback data (max 64 bytes)
    safe_prompt = prompt[:40].replace(" ", "_")
    
    return _telegram_modules.InlineKeyboardMarkup([
        [
            _telegram_modules.InlineKeyboardButton("🎨 Generate", callback_data=f"img:generate:{safe_prompt}"),
            _telegram_modules.InlineKeyboardButton("🔄 Variations", callback_data=f"img:variations:{safe_prompt}"),
        ],
        [
            _telegram_modules.InlineKeyboardButton("📐 512x512", callback_data=f"img:size:{safe_prompt}:512"),
            _telegram_modules.InlineKeyboardButton("📐 768x768", callback_data=f"img:size:{safe_prompt}:768"),
        ],
    ])


async def send_generation_prompt(chat_id: str, prompt: str, bot_token: str) -> bool:
    """Send a prompt with inline buttons to Telegram."""
    if not TELEGRAM_AVAILABLE:
        return False
    
    bot = _telegram_modules.Bot(token=bot_token)
    
    text = f"🎨 <b>Image Generation</b>\n\n{prompt}\n\nSelect options below:"
    keyboard = create_inline_buttons(prompt)
    
    try:
        await bot.send_message(
            chat_id=int(chat_id),
            text=text,
            parse_mode=_telegram_modules.constants.ParseMode.HTML,
            reply_markup=keyboard,
        )
        return True
    except Exception as e:
        print(f"Error sending prompt: {e}", file=sys.stderr)
        return False


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 imagenv_gateway.py <prompt>")
        return 1
    
    if not TELEGRAM_AVAILABLE:
        print("python-telegram-bot not installed")
        return 1
    
    prompt = sys.argv[1]
    token = get_telegram_token()
    if not token:
        print("No Telegram token found")
        return 1
    
    import asyncio
    asyncio.run(send_generation_prompt("467058917", prompt, token))
    return 0


if __name__ == "__main__":
    sys.exit(main())