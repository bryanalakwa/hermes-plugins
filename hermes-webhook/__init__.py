"""Hermes Inter-Agent Webhook Plugin — agent-to-agent communication over Tailscale."""

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
    """Load webhook config from config.yaml."""
    home = _get_home()
    config_path = home / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
        return config.get("plugins", {}).get("hermes-webhook", {})
    except Exception:
        return {}


def register(ctx) -> None:
    """Plugin entry point — called by Hermes plugin system on load."""
    plugin_config = _load_plugin_config()

    _log.info("hermes-webhook: plugin loaded")