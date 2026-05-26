"""Dream Engine dashboard plugin — backend API routes.

Mounted at /api/plugins/hermes-dream-engine/ by the dashboard plugin system.

Provides endpoints for:
- Current state and status
- Dream journal history
- Manual controls (force dream, clear state)
- Configuration
- HRR-powered title generation

The daemon is created lazily on first API call. In the dashboard process,
this module owns the daemon. In the gateway process, __init__.py may also
call set_daemon() to enable hook-based heartbeat injection.

NOTE: Authentication is handled by the dashboard's global auth middleware
(web_server.py), which validates the X-Hermes-Session-Token header on all
/api/ routes. No per-plugin auth is needed.
"""

from __future__ import annotations

import json
import logging
import sys
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

        _plugin_dir = Path(__file__).resolve().parent
        _pkg_dir = _plugin_dir.parent  # plugin root (where daemon.py lives)
        try:
            from .daemon import DreamDaemon
        except (ImportError, ModuleNotFoundError):
            # When loaded as a standalone file (dashboard process), add the
            # package root to sys.path so absolute imports work.
            if str(_pkg_dir) not in sys.path:
                sys.path.insert(0, str(_pkg_dir))
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


@router.delete("/journal/{session_id}")
async def delete_journal_entry(session_id: str):
    """Delete a specific journal entry by session_id."""
    daemon = _get_daemon()
    deleted = daemon._engine.delete_journal_entry(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"ok": True, "session_id": session_id}


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

def _save_config_to_yaml(config: dict) -> None:
    """Persist dream engine config back to ~/.hermes/config.yaml.

    Only updates the plugins.hermes-dream-engine section, leaving
    all other config untouched.
    """
    try:
        import yaml
        home = _get_home()
        config_path = home / "config.yaml"
        if not config_path.exists():
            _log.warning("config.yaml not found — config not persisted")
            return
        with open(config_path) as f:
            full_cfg = yaml.safe_load(f) or {}
        plugins_cfg = full_cfg.setdefault("plugins", {})
        plugin_cfg = plugins_cfg.setdefault("hermes-dream-engine", {})
        plugin_cfg.update(config)
        with open(config_path, "w") as f:
            yaml.dump(full_cfg, f, default_flow_style=False, allow_unicode=True)
        _log.info("dream engine config persisted to config.yaml")
    except ImportError:
        _log.warning("PyYAML not available — config not persisted to config.yaml")
    except Exception as exc:
        _log.warning("failed to persist config to config.yaml: %s", exc)


@router.get("/config")
async def get_config():
    """Get current dream engine configuration."""
    daemon = _get_daemon()
    return {"config": daemon._config}


@router.put("/config")
async def update_config(data: dict):
    """Update dream engine configuration and persist to config.yaml."""
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
    # Persist to config.yaml so changes survive gateway restart
    _save_config_to_yaml(daemon._config)
    # Also save daemon state (which includes config)
    daemon._save_state()
    return {"ok": True, "config": daemon._config, "updated": list(updated.keys())}


# ── HRR-Powered Title Generation ───────────────────────────

# Sentinel for "not yet initialized" caching
_HRR_CACHE_SENTINEL = object()


def _get_chroma_search():
    """Self-healing accessor for ChromaDB search function.

    Returns the vector_store.search function, or None if ChromaDB is
    unavailable. Caches the result after first successful initialization.
    """
    cached = _get_chroma_search._cache
    if cached is not _HRR_CACHE_SENTINEL:
        return cached

    try:
        _home = _get_home()
        _holo_plugin = _home / "hermes-agent" / "plugins" / "memory" / "holographic"
        if str(_holo_plugin) not in sys.path:
            sys.path.insert(0, str(_holo_plugin))
        from vector_store import search as _chroma_search_fn
        _get_chroma_search._cache = _chroma_search_fn
        _log.info("ChromaDB search initialized for HRR title generation")
        return _chroma_search_fn
    except (ImportError, ModuleNotFoundError) as e:
        _log.info("ChromaDB not available for HRR titles: %s", e)
        _get_chroma_search._cache = None
        return None
    except Exception as e:
        _log.warning("Failed to initialize ChromaDB for HRR titles: %s", e)
        _get_chroma_search._cache = None
        return None

_get_chroma_search._cache = _HRR_CACHE_SENTINEL


@router.post("/title/generate")
async def generate_title(data: dict):
    """Generate a contextually meaningful title using HRR vector similarity.

    Takes dream insight text, finds the nearest neighbor in the holographic
    fact store via ChromaDB, and returns that fact's most distinctive phrase
    as a blog-style title.

    Request: {"text": "dream insight text...", "session_id": "..."}
    Response: {"title": "...", "source_fact": "...", "distance": 0.12}
    """
    text = data.get("text", "")
    if not text or len(text) < 10:
        return {"title": "Dream Session", "source_fact": None, "distance": None}

    title, source, distance = _hrr_title_from_chroma(text)
    if title:
        return {"title": title, "source_fact": source, "distance": distance}

    return {"title": _extract_title_phrase(text), "source_fact": None, "distance": None}


def _hrr_title_from_chroma(query_text: str):
    """Use ChromaDB to find the nearest fact to the query text.

    Returns (title_phrase, source_fact_preview, distance) or (None, None, None).
    """
    _chroma_search_fn = _get_chroma_search()
    if _chroma_search_fn is None:
        return None, None, None

    try:
        results = _chroma_search_fn(query_text, n_results=3)
        if not results:
            return None, None, None

        best = None
        for r in results:
            dist = r.get("distance") or 1.0
            if dist > 0.6:
                continue
            preview = r.get("content_preview", "")
            trust = r.get("trust_score", 0)
            score = (1.0 - dist) * (0.5 + trust * 0.5)
            if best is None or score > best[0]:
                best = (score, preview, dist)

        if best is None:
            return None, None, None

        _, preview, distance = best
        title = _extract_title_phrase(preview)
        return title, preview[:100], distance

    except Exception as exc:
        _log.warning("HRR title generation failed: %s", exc)
        return None, None, None


def _extract_title_phrase(text: str):
    """Extract a short, meaningful title phrase from fact text."""
    if not text:
        return "Dream Session"

    import re as _re
    cleaned = _re.sub(r'\[\w+\]\s*', '', text).strip()

    prefixes = [
        r'^resolved:\s*', r'^idea:\s*', r'^connection:\s*',
        r'^new perspective:\s*', r'^escalation:\s*',
        r'^the\s+', r'^a\s+', r'^an\s+',
    ]
    for p in prefixes:
        cleaned = _re.sub(p, '', cleaned, flags=_re.IGNORECASE).strip()

    clause = _re.split(r'[,;.!?—–]', cleaned)[0].strip()
    words = clause.split()[:7]
    title = " ".join(words)

    if len(title) > 60:
        title = title[:57] + "..."
    if len(title) < 3:
        return "Dream Session"

    return title[0].upper() + title[1:]


# ── Heartbeat (for testing) ────────────────────────────────

@router.post("/heartbeat")
async def send_heartbeat():
    """Send a manual heartbeat (for testing)."""
    daemon = _get_daemon()
    daemon.heartbeat()
    return {"ok": True, "timestamp": time.time()}
