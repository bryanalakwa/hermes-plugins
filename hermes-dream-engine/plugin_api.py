"""Dream Engine dashboard plugin — backend API routes.

Mounted at /api/plugins/hermes-dream-engine/ by the dashboard plugin system.

Provides endpoints for:
- Current state and status
- Dream journal history
- Manual controls (force dream, clear state)
- Configuration

The daemon is created lazily on first API call. In the dashboard process,
this module owns the daemon. In the gateway process, __init__.py may also
call set_daemon() to enable hook-based heartbeat injection.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from hermes_constants import get_hermes_home
except ImportError:
    import os as _os
    def get_hermes_home() -> Path:
        val = (_os.environ.get("HERMES_HOME") or "").strip()
        return Path(val) if val else Path.home() / ".hermes"

try:
    from fastapi import APIRouter, HTTPException, Query
except Exception:
    class APIRouter:
        def get(self, *_args, **_kwargs):
            return lambda fn: fn
        def post(self, *_args, **_kwargs):
            return lambda fn: fn
        def put(self, *_args, **_kwargs):
            return lambda fn: fn
        def delete(self, *_args, **_kwargs):
            return lambda fn: fn

router = APIRouter()
_log = logging.getLogger(__name__)

# Imports deferred until needed
_daemon = None
_daemon_lock = None


def _get_home() -> Path:
    val = Path.home() / ".hermes"
    return val


def _ensure_daemon():
    """Create the daemon singleton if it doesn't exist yet."""
    global _daemon, _daemon_lock
    if _daemon is not None:
        return _daemon

    # Lazy import to avoid circular deps
    import threading
    if _daemon_lock is None:
        _daemon_lock = threading.Lock()

    with _daemon_lock:
        if _daemon is not None:
            return _daemon

        home = _get_home()
        config_path = home / "config.yaml"
        config = {}
        if config_path.exists():
            try:
                import yaml
                with open(config_path) as f:
                    cfg = yaml.safe_load(f) or {}
                config = cfg.get("plugins", {}).get("hermes-dream-engine", {})
            except Exception:
                pass

        try:
            from .daemon import DreamDaemon
        except ImportError:
            from daemon import DreamDaemon
        _daemon = DreamDaemon(
            config=config,
            state_path=home / "dream_engine" / "state.json",
            journal_path=home / "dream_engine" / "journal.json",
            memory_source_path=home / "dreams" / "state.json",
        )
        _daemon.start()
        _log.info("Dream daemon auto-started in dashboard process")
        return _daemon


def set_daemon(daemon) -> None:
    """Called by __init__.py (gateway process) to inject a daemon reference.
    If called, the injected daemon is used instead of creating our own."""
    global _daemon
    _daemon = daemon
    _log.info("Dream daemon injected from gateway")


def _get_daemon():
    return _ensure_daemon()


# ── Status ─────────────────────────────────────────────────

@router.get("/status")
async def get_status():
    """Get current daemon status (state, timers, quota)."""
    return _get_daemon().get_status()


# ── Journal ────────────────────────────────────────────────

@router.get("/journal")
async def get_journal(limit: int = Query(default=50, ge=1, le=200)):
    """Get dream journal entries, newest first."""
    daemon = _get_daemon()
    journal = daemon._engine.read_journal(limit)
    return {"entries": journal, "total": len(journal)}


@router.delete("/journal")
async def clear_journal():
    """Clear the dream journal."""
    daemon = _get_daemon()
    journal_path = daemon._journal_path
    if journal_path.exists():
        journal_path.write_text("[]")
    return {"ok": True}


# ── Manual controls ────────────────────────────────────────

@router.post("/dream/force")
async def force_dream():
    """Manually trigger a dream session."""
    daemon = _get_daemon()
    session_id = daemon.force_dream()
    if session_id is None:
        raise HTTPException(
            status_code=429,
            detail=f"Dream quota exhausted ({daemon._dreams_today}/{daemon._config['max_dreams_per_day']} today)",
        )
    return {"ok": True, "session_id": session_id}


@router.post("/state/reset")
async def reset_state():
    """Reset all state (dreams today, timers, state machine)."""
    daemon = _get_daemon()
    daemon.clear_state()
    return {"ok": True}


# ── Configuration ──────────────────────────────────────────

@router.get("/config")
async def get_config():
    """Get current dream engine configuration."""
    daemon = _get_daemon()
    return {"config": daemon._config}


@router.put("/config")
async def update_config(data: dict):
    """Update dream engine configuration."""
    daemon = _get_daemon()
    updated = {}
    for key, value in data.items():
        if key in daemon._config:
            daemon._config[key] = value
            updated[key] = value
    # Update monitor thresholds
    daemon._monitor._idle_threshold = daemon._config.get("idle_threshold_seconds", 300)
    daemon._monitor._dormant_threshold = daemon._config.get("dormant_threshold_seconds", 1800)
    daemon._monitor._soak_threshold = daemon._config.get("soak_threshold_seconds", 3000)
    daemon._monitor._hypnagogic_duration = daemon._config.get("hypnagogic_duration_seconds", 120)
    return {"ok": True, "config": daemon._config, "updated": list(updated.keys())}


# ── Heartbeat (for testing) ────────────────────────────────

@router.post("/heartbeat")
async def send_heartbeat():
    """Send a manual heartbeat (for testing)."""
    daemon = _get_daemon()
    daemon.heartbeat()
    return {"ok": True, "timestamp": time.time()}
