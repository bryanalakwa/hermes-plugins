#!/usr/bin/env python3
"""generate_image.py — Local image generation using diffusers (LCM for fast CPU inference).
Usage: python3 generate_image.py "a beautiful sunset over mountains" [--output image.png] [--steps 4] [--width 512] [--height 512]
"""
import sys
import os
import argparse
import torch

def generate(prompt: str, output: str = "output.png", steps: int = 8, width: int = 512, height: int = 512, use_lcm: bool = True, seed: int = None):
    if use_lcm and os.path.exists("/home/bry/.hermes/cache/ImGen/models/lcm_dreamshaper"):
        # Use LCM model if available
        from diffusers import LatentConsistencyModelPipeline
        
        model_path = "/home/bry/.hermes/cache/ImGen/models/lcm_dreamshaper"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"Loading LCM model from {model_path} on {device}...")
        pipe = LatentConsistencyModelPipeline.from_pretrained(
            model_path,
            torch_dtype=torch.float32 if device == "cpu" else torch.float16,
            safety_checker=None,
            requires_safety_checker=False,
            local_files_only=True,
        )
        pipe = pipe.to(device)
        pipe.enable_attention_slicing()  # CPU memory optimization
        
        # Set seed if provided
        if seed is not None and seed != -1:
            torch.manual_seed(seed)
        
        print(f"Generating: '{prompt}' ({steps} steps, {width}x{height})...")
        image = pipe(
            prompt=prompt,
            num_inference_steps=steps,
            guidance_scale=1.0,  # Optimized for LCM
            width=width,
            height=height,
        ).images[0]
        
    else:
        # Fallback to SD 1.5
        from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
        
        # Use a smaller model that fits in RAM
        model_id = "runwayml/stable-diffusion-v1-5"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"Loading model on {device}...")
        pipe = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float32,
            safety_checker=None,
            requires_safety_checker=False,
        )
        # Use faster scheduler
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
        pipe = pipe.to(device)
        
        if device == "cpu":
            pipe.enable_attention_slicing()
            pipe.enable_sequential_cpu_offload()
        
        if seed is not None and seed != -1:
            torch.manual_seed(seed)
        
        print(f"Generating: '{prompt}' ({steps} steps, {width}x{height})...")
        image = pipe(
            prompt=prompt,
            num_inference_steps=steps,
            width=width,
            height=height,
        ).images[0]
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output)) or ".", exist_ok=True)
    
    image.save(output)
    print(f"Saved: {os.path.abspath(output)}")
    return os.path.abspath(output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate images locally with Stable Diffusion/LCM")
    parser.add_argument("prompt", help="Image description")
    parser.add_argument("--output", default="output.png", help="Output file path")
    parser.add_argument("--steps", type=int, default=8, help="Inference steps (LCM: 4-8, SD: 20-50)")
    parser.add_argument("--width", type=int, default=512, help="Width")
    parser.add_argument("--height", type=int, default=512, help="Height")
    parser.add_argument("--lcm", action="store_true", help="Use LCM model if available")
    parser.add_argument("--seed", type=int, default=-1, help="Seed (-1 for random)")
    args = parser.parse_args()
    
    try:
        generate(args.prompt, args.output, args.steps, args.width, args.height, 
                 use_lcm=args.lcm, seed=args.seed)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)