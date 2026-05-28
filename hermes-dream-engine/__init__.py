"""Dream Engine plugin for Hermes Agent.

Autonomous event-driven dreaming system with 5-state sleep detection.
Runs as a background daemon with dashboard integration.

Entry point: register(ctx) — called by the Hermes plugin system.
"""

import logging
import os
import time
from pathlib import Path

_log = logging.getLogger(__name__)
_daemon = None


def _get_home() -> Path:
    """Resolve HERMES_HOME."""
    val = os.environ.get("HERMES_HOME", "").strip()
    return Path(val) if val else Path.home() / ".hermes"


def _load_plugin_config() -> dict:
    """Load dream engine config from config.yaml."""
    home = _get_home()
    config_path = home / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
        return config.get("plugins", {}).get("hermes-dream-engine", {})
    except Exception:
        return {}


def register(ctx) -> None:
    """Plugin entry point — called by Hermes plugin system on load."""
    global _daemon

    home = _get_home()
    plugin_config = _load_plugin_config()

    # Paths
    state_path = home / "dream_engine" / "state.json"
    journal_path = home / "dream_engine" / "journal.json"
    memory_source = home / "dreams" / "state.json"

    # Import here to avoid import-time side effects
    try:
        from .daemon import DreamDaemon
    except ImportError:
        from daemon import DreamDaemon

    # Create and start daemon
    _daemon = DreamDaemon(
        config=plugin_config,
        state_path=state_path,
        journal_path=journal_path,
        memory_source_path=memory_source if memory_source.exists() else None,
    )

    # Register hooks
    ctx.register_hook("pre_gateway_dispatch", _on_gateway_dispatch)
    ctx.register_hook("pre_tool_call", _on_tool_call)

    # Start the daemon loop
    _daemon.start()
    _log.info("hermes-dream-engine: plugin loaded, daemon started")

    # Inject daemon reference into plugin_api
    try:
        from . import plugin_api
        plugin_api.set_daemon(_daemon)
    except Exception as e:
        _log.warning("Could not inject daemon into plugin_api: %s", e)


def _on_gateway_dispatch(**kwargs) -> None:
    """Hook: fires on every incoming message from any platform."""
    if _daemon:
        _daemon.heartbeat()


def _on_tool_call(**kwargs) -> None:
    """Hook: fires on every tool invocation (bash, web, memory, etc.)."""
    if _daemon:
        _daemon.heartbeat()
