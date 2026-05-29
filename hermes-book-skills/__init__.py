"""BookSkills Plugin for Hermes Agent.

Book-to-skill generation plugin. Upload PDF/EPUB/TXT books, extract key concepts
via LLM processing, and generate reusable Hermes skills.

Entry point: register(ctx) — called by the Hermes plugin system.
"""

import logging
import os
from pathlib import Path

_log = logging.getLogger(__name__)


def _get_home() -> Path:
    """Resolve HERMES_HOME."""
    val = os.environ.get("HERMES_HOME", "").strip()
    return Path(val) if val else Path.home() / ".hermes"


def _load_plugin_config() -> dict:
    """Load BookSkills config from config.yaml."""
    home = _get_home()
    config_path = home / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
        return config.get("plugins", {}).get("hermes-book-skills", {})
    except Exception:
        return {}


def register(ctx) -> None:
    """Plugin entry point — called by Hermes plugin system on load."""
    plugin_config = _load_plugin_config()

    # Ensure library paths exist
    home = _get_home()
    library_path = home / "book-library"
    skills_path = home / "skills" / "book-skills"

    try:
        library_path.mkdir(parents=True, exist_ok=True)
        skills_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        _log.warning("Could not create library directories: %s", e)

    _log.info("hermes-book-skills: plugin loaded (books: %s, skills: %s)",
              library_path, skills_path)

    # Verify plugin_api is loadable for dashboard
    try:
        from . import dashboard
        _log.debug("Dashboard module loaded successfully")
    except Exception as e:
        _log.warning("Could not load dashboard module: %s", e)