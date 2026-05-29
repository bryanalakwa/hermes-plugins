#!/usr/bin/env python3
"""Watch for image generation triggers and process them.

Watches ~/.hermes/.img_generation/ for .json trigger files.
Each file contains: prompt, size, chat_id, thread_id
Generates image and sends back to Telegram.
"""

import json
import os
import sys
import time
import asyncio
from pathlib import Path
from datetime import datetime

HERMES_HOME = Path.home() / ".hermes"
TRIGGER_DIR = HERMES_HOME / ".img_generation"
OUTPUT_DIR = HERMES_HOME / "cache" / "ImGen" / "output"


def get_telegram_token():
    """Get Telegram bot token from environment."""
    for var in ["TELEGRAM_BOT_TOKEN", "TG_BOT_TOKEN", "BOT_TOKEN"]:
        val = os.environ.get(var)
        if val:
            return val
    return None


def generate_image(prompt: str, size: int = 512, output_path: str = None) -> str:
    """Generate image using local diffusers."""
    import torch
    from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
    
    # Try LCM first, then fallback to SD
    lcm_path = HERMES_HOME / "cache" / "ImGen" / "models" / "lcm_dreamshaper"
    
    if lcm_path.exists():
        from diffusers import LatentConsistencyModelPipeline
        print(f"Loading LCM model from {lcm_path}...")
        pipe = LatentConsistencyModelPipeline.from_pretrained(
            str(lcm_path),
            torch_dtype=torch.float32,
            safety_checker=None,
            requires_safety_checker=False,
            local_files_only=True,
        )
        pipe.enable_attention_slicing()
        num_steps = 4
    else:
        print("Loading SD 1.5 (no LCM available)...")
        pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float32,
            safety_checker=None,
            requires_safety_checker=False,
        )
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
        pipe.enable_attention_slicing()
        num_steps = 20
    
    pipe = pipe.to("cpu")
    
    # Generate
    timestamp = int(time.time())
    if output_path is None:
        output_path = str(OUTPUT_DIR / f"img_{timestamp}.png")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating: '{prompt}' ({size}x{size})...")
    image = pipe(
        prompt=prompt,
        num_inference_steps=num_steps,
        width=size,
        height=size,
    ).images[0]
    
    image.save(output_path)
    print(f"Saved: {output_path}")
    return output_path


async def send_image(chat_id: int, image_path: str, caption: str = "", thread_id: int = None):
    """Send generated image to Telegram."""
    try:
        from telegram import Bot
        from telegram.constants import ParseMode
    except ImportError:
        print("python-telegram-bot not installed")
        return False
    
    token = get_telegram_token()
    if not token:
        print("No Telegram token found")
        return False
    
    bot = Bot(token=token)
    
    try:
        # Send as photo
        await bot.send_photo(
            chat_id=chat_id,
            photo=open(image_path, "rb"),
            caption=caption,
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception as e:
        print(f"Error sending image: {e}", file=sys.stderr)
        return False


def process_triggers():
    """Process all pending trigger files."""
    if not TRIGGER_DIR.exists() or not any(TRIGGER_DIR.glob("*.json")):
        return 0
    
    count = 0
    for trigger_file in sorted(TRIGGER_DIR.glob("*.json")):
        try:
            data = json.loads(trigger_file.read_text())
            prompt = data.get("prompt", "")
            size = data.get("size", 512)
            chat_id = data.get("chat_id")
            thread_id = data.get("thread_id")
            
            if not prompt or not chat_id:
                continue
            
            # Generate image
            image_path = generate_image(prompt, size)
            
            # Send to Telegram
            asyncio.run(send_image(
                chat_id=chat_id,
                image_path=image_path,
                caption=f"🎨 Generated: {prompt[:100]}",
                thread_id=thread_id,
            ))
            
            count += 1
        except Exception as e:
            print(f"Error processing trigger {trigger_file}: {e}", file=sys.stderr)
        finally:
            # Remove trigger file
            try:
                trigger_file.unlink()
            except:
                pass
    
    return count


def main():
    count = process_triggers()
    print(f"Processed {count} image generation triggers")
    return 0


if __name__ == "__main__":
    sys.exit(main())