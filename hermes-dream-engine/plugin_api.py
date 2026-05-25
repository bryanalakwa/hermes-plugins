"""Dream Engine dashboard plugin — backend API routes.

Mounted at /api/plugins/hermes-dream-engine/ by the dashboard plugin system.

Provides endpoints for:
- Current state and status
- Dream journal history
- Manual controls (force dream, clear state)
- Configuration
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

# Reference to the daemon instance (set by __init__.py on plugin load)
_daemon = None


def set_daemon(daemon) -> None:
    """Called by __init__.py to inject the daemon reference."""
    global _daemon
    _daemon = daemon


def _get_daemon():
    if _daemon is None:
        raise HTTPException(status_code=503, detail="Dream daemon not initialized")
    return _daemon


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
    for key, value in data.items():
        if key in daemon._config:
            daemon._config[key] = value
    # Update monitor thresholds
    daemon._monitor._idle_threshold = daemon._config.get("idle_threshold_seconds", 300)
    daemon._monitor._dormant_threshold = daemon._config.get("dormant_threshold_seconds", 1800)
    daemon._monitor._soak_threshold = daemon._config.get("soak_threshold_seconds", 3000)
    daemon._monitor._hypnagogic_duration = daemon._config.get("hypnagogic_duration_seconds", 120)
    return {"ok": True, "config": daemon._config}


# ── Heartbeat (for testing) ────────────────────────────────

@router.post("/heartbeat")
async def send_heartbeat():
    """Send a manual heartbeat (for testing)."""
    daemon = _get_daemon()
    daemon.heartbeat()
    return {"ok": True, "timestamp": time.time()}
