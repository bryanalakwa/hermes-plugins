# Hermes ImaGen Plugin v1.0.0

Local image generation via Stable Diffusion/LCM with Gradio web interface.

## What It Does

- **Generate images** from text prompts using Stable Diffusion or LCM
- **Gradio web UI** on port 7860 (configurable)
- **Fast CPU inference** with attention slicing and LCM acceleration
- **Integrated with Hermes** — output saved to `~/.hermes/imagenv-output/`

## Quick Install

```bash
git clone https://github.com/bryanalakwa/hermes-plugins.git
cd hermes-plugins/hermes-imagenv
chmod +x install.sh
./install.sh
```

## Requirements

- Python 3.7+ with venv
- PyTorch (CPU or CUDA)
- ~2GB disk space for model

## Usage

```bash
# Start the Gradio app
python3 ~/.hermes/plugins/hermes-imagenv/gradio_app.py

# Open in browser: http://127.0.0.1:7860
```

## Model Options

- **SD 1.5** - Standard Stable Diffusion (requires ~4GB RAM)
- **LCM-Dreamshaper** - Much faster, lower quality (requires manual download)

For Tailscale Funnel access:
```bash
tailscale funnel --hostname=my-imagenv serve / http://localhost:7860
```

## Output

Images saved to: `~/.hermes/imagenv-output/generated_<timestamp>_<index>.png`