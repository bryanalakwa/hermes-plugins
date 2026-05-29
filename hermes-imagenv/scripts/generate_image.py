#!/usr/bin/env python3
"""generate_image.py — Local image generation using diffusers (LCM for fast CPU inference).

Usage: python3 generate_image.py "a beautiful sunset over mountains" [--output image.png] [--steps 4] [--width 512] [--height 512]

Model priority (CPU-optimized):
1. Segmind SSD (fastest, ~1GB)
2. LCM Dreamshaper (quality, ~1.2GB)  
3. SD 1.5 fallback (slowest, online)
"""

import sys
import os
import argparse
import torch
from pathlib import Path

MODELS_DIR = Path.home() / ".hermes" / "cache" / "ImGen" / "models"


def find_available_model():
    """Find the first available model for CPU inference."""
    # Check each model in order of preference
    model_paths = [
        ("segguided", "Segmind-SSD-1B"),
        ("lcm_dreamshaper", "LCM-Dreamshaper"),
    ]
    
    for model_name, friendly_name in model_paths:
        model_path = MODELS_DIR / model_name
        if model_path.exists():
            return model_name, str(model_path)
    
    return None, None


def generate(prompt: str, output: str = "output.png", steps: int = 8, width: int = 512, height: int = 512, seed: int = None):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    os.makedirs(os.path.dirname(os.path.abspath(output)) or ".", exist_ok=True)
    
    # Find available model
    model_name, model_path = find_available_model()
    
    if model_name == "segguided":
        # Segmind SSD - fastest for CPU
        from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
        
        print(f"Loading Segmind-SSD-1B from {model_path} on {device}...")
        pipe = StableDiffusionPipeline.from_pretrained(
            model_path,
            torch_dtype=torch.float32,
            safety_checker=None,
            requires_safety_checker=False,
        )
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
        pipe.enable_attention_slicing()
        pipe = pipe.to(device)
        actual_steps = 4
        
    elif model_name == "lcm_dreamshaper":
        # LCM Dreamshaper
        from diffusers import LatentConsistencyModelPipeline
        
        print(f"Loading LCM-Dreamshaper from {model_path} on {device}...")
        pipe = LatentConsistencyModelPipeline.from_pretrained(
            model_path,
            torch_dtype=torch.float32,
            safety_checker=None,
            requires_safety_checker=False,
            local_files_only=True,
        )
        pipe.enable_attention_slicing()
        pipe = pipe.to(device)
        actual_steps = 4
        
    else:
        # Fallback to online SD 1.5
        from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
        
        print(f"Loading SD 1.5 on {device} (will download if not cached)...")
        pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float32,
            safety_checker=None,
            requires_safety_checker=False,
        )
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
        pipe.enable_attention_slicing()
        pipe = pipe.to(device)
        actual_steps = steps
    
    # Set seed
    if seed is not None and seed != -1:
        torch.manual_seed(seed)
    
    print(f"Generating: '{prompt}' ({actual_steps} steps, {width}x{height})...")
    
    # Generate
    if model_name in ["segguided", "lcm_dreamshaper"]:
        image = pipe(
            prompt=prompt,
            num_inference_steps=actual_steps,
            guidance_scale=1.0,
            width=width,
            height=height,
        ).images[0]
    else:
        image = pipe(
            prompt=prompt,
            num_inference_steps=actual_steps,
            width=width,
            height=height,
        ).images[0]
    
    image.save(output)
    print(f"Saved: {os.path.abspath(output)}")
    return os.path.abspath(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate images locally with Stable Diffusion/LCM")
    parser.add_argument("prompt", help="Image description")
    parser.add_argument("--output", default="output.png", help="Output file path")
    parser.add_argument("--steps", type=int, default=8, help="Inference steps (LCM: 4, SD: 20-50)")
    parser.add_argument("--width", type=int, default=512, help="Width")
    parser.add_argument("--height", type=int, default=512, help="Height")
    parser.add_argument("--seed", type=int, default=-1, help="Seed (-1 for random)")
    
    args = parser.parse_args()
    
    try:
        generate(args.prompt, args.output, args.steps, args.width, args.height, seed=args.seed)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)