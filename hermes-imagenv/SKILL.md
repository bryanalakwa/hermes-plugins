---
name: hermes-imagenv
description: "Local image generation using Stable Diffusion and LCM models. Integration with Telegram via inline buttons, ComfyUI workflow support, and automatic model download."
version: 1.0.0
triggers:
  - image generation
  - generate image
  - stable diffusion
  - LCM
  - comfyui
  - DALL-E alternative
---

# Hermes ImaGen Plugin

Local image generation using Stable Diffusion and Latent Consistency Models (LCM) for fast CPU inference.

## Features

- **Local inference** — No API calls, all generation happens on your machine
- **LCM support** — Fast 4-8 step generation with lightweight models
- **Telegram integration** — Generate images via inline buttons
- **ComfyUI compatible** — Drop-in model support
- **Progress feedback** — Visual progress bars for long generations

## Installation

```bash
cd ~/.hermes/plugins/hermes-imagenv
./install.sh
```

## Usage

### CLI
```bash
python3 ~/.hermes/scripts/generate_image.py "a beautiful sunset over mountains"
```

### Telegram
Send an image generation request and use the inline buttons for variations.

### Model Sizes (for CPU with 8GB RAM)

| Model | Size | Notes |
|-------|------|-------|
| LCM-Dreamshaper | ~1.2GB | Recommended for CPU |
| SD 1.5 | ~8GB | Needs swap; slower |
| SD 2.1 | ~8GB | Needs swap; slower |

## Files

| File | Path |
|------|------|
| Image generator | `~/.hermes/scripts/generate_image.py` |
| Model cache | `~/.hermes/cache/ImGen/models/` |
| Install script | `install.sh` |
