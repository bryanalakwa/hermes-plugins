"""Hermes ImaGen Plugin — Local image generation via diffusers.

Image generation plugin using Stable Diffusion/LCM with Gradio web UI.
"""

import logging
import os
from pathlib import Path

__version__ = "1.0.0"

_log = logging.getLogger(__name__)


def _get_home() -> Path:
    """Resolve HERMES_HOME."""
    val = os.environ.get("HERMES_HOME", "").strip()
    return Path(val) if val else Path.home() / ".hermes"


def _load_plugin_config() -> dict:
    """Load imagenv config from config.yaml."""
    home = _get_home()
    config_path = home / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
        return config.get("plugins", {}).get("hermes-imagenv", {})
    except Exception:
        return {}


def register(ctx) -> None:
    """Plugin entry point — called by Hermes plugin system on load."""
    plugin_config = _load_plugin_config()
    
    home = _get_home()
    output_dir = home / "imagenv-output"
    
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        _log.warning("Could not create output directory: %s", e)
    
    _log.info("hermes-imagenv: plugin loaded (output: %s)", output_dir)