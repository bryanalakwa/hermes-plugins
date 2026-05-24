"""Dreaming dashboard plugin — backend API routes.

Mounted at /api/plugins/dreaming/ by the dashboard plugin system.

Serves dream journal entries, dreaming state, and vector store stats to the frontend.
"""

from __future__ import annotations

import json
import subprocess
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

router = APIRouter()


def _dreams_dir() -> Path:
    return get_hermes_home() / "dreams"


def _state_path() -> Path:
    return _dreams_dir() / "state.json"


def _vector_store_script() -> Path:
    return get_hermes_home() / "hermes-agent" / "plugins" / "memory" / "holographic" / "vector_store.py"


def _load_state() -> Dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {
            "last_dream_at": None,
            "dreams_today": 0,
            "last_dream_date": None,
            "total_dreams": 0,
        }
    try:
        return json.loads(path.read_text())
    except Exception:
        return {
            "last_dream_at": None,
            "dreams_today": 0,
            "last_dream_date": None,
            "total_dreams": 0,
        }


def _list_dream_files() -> List[Path]:
    d = _dreams_dir()
    if not d.is_dir():
        return []
    return sorted(d.glob("dream-*.md"), reverse=True)


def _parse_dream_file(path: Path) -> Dict[str, Any]:
    content = path.read_text()
    lines = content.splitlines()

    title = ""
    timestamp = ""
    duration = ""
    processed = []
    connections = []
    insights = []
    actions = []
    notified = False
    notification_reason = ""
    vector_searches = []

    section = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not title:
            title = stripped[2:]
        elif stripped.startswith("## "):
            section = stripped[3:].lower()
        elif "timestamp" in stripped.lower() and ":" in stripped:
            timestamp = stripped.split(":", 1)[1].strip()
        elif "duration" in stripped.lower() and ":" in stripped:
            duration = stripped.split(":", 1)[1].strip()
        elif section == "what was processed" and stripped.startswith("-"):
            processed.append(stripped[1:].strip())
        elif section == "vector searches run" and stripped.startswith("-"):
            vector_searches.append(stripped[1:].strip())
        elif section == "key connections" and stripped.startswith("-"):
            connections.append(stripped[1:].strip())
        elif section == "insights" and stripped.startswith("-"):
            insights.append(stripped[1:].strip())
        elif section == "actions taken" and stripped.startswith("-"):
            actions.append(stripped[1:].strip())
        elif "notified" in stripped.lower() and ":" in stripped:
            val = stripped.split(":", 1)[1].strip().lower()
            notified = val in ("true", "yes")
        elif "notification reason" in stripped.lower() and ":" in stripped:
            notification_reason = stripped.split(":", 1)[1].strip()

    mtime = path.stat().st_mtime

    return {
        "id": path.stem,
        "title": title or path.stem,
        "timestamp": timestamp or time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)),
        "duration": duration or "unknown",
        "processed": processed,
        "vector_searches": vector_searches,
        "connections": connections,
        "insights": insights,
        "actions": actions,
        "notified_user": notified,
        "notification_reason": notification_reason,
        "content": content,
        "file_size": path.stat().st_size,
        "mtime": mtime,
    }


def _run_vector_stats() -> Dict[str, Any]:
    """Run vector_store.py stats and parse output."""
    script = _vector_store_script()
    if not script.exists():
        return {"installed": False, "error": "vector_store.py not found"}

    try:
        result = subprocess.run(
            ["python3", str(script), "stats"],
            capture_output=True, text=True, timeout=15,
            cwd=str(script.parent),
            env={**__import__("os").environ, "HERMES_HOME": str(get_hermes_home())}
        )
        output = result.stdout + result.stderr
        stats = {"installed": True, "raw_output": output}

        for line in output.splitlines():
            if "Facts:" in line:
                stats["facts"] = line.split(":")[-1].strip()
            elif "Indexed:" in line:
                stats["indexed"] = line.split(":")[-1].strip()
            elif "Size:" in line and "KB" in line:
                stats["size"] = line.split(":")[-1].strip()

        return stats
    except subprocess.TimeoutExpired:
        return {"installed": True, "error": "timeout"}
    except Exception as e:
        return {"installed": True, "error": str(e)}


@router.get("/state")
async def get_dreaming_state():
    state = _load_state()
    files = _list_dream_files()
    state["total_entries"] = len(files)
    state["dreams_dir"] = str(_dreams_dir())
    return state


@router.get("/dreams")
async def list_dreams(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    files = _list_dream_files()
    total = len(files)
    page = files[offset:offset + limit]
    dreams = [_parse_dream_file(f) for f in page]
    return {"dreams": dreams, "total": total, "offset": offset, "limit": limit}


@router.get("/dreams/{dream_id}")
async def get_dream(dream_id: str):
    safe_id = dream_id.replace("/", "").replace("..", "")
    path = _dreams_dir() / f"{safe_id}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Dream {dream_id} not found")
    return _parse_dream_file(path)


@router.get("/vector-stats")
async def get_vector_stats():
    return _run_vector_stats()


@router.post("/reindex")
async def trigger_reindex():
    """Trigger vector store re-index."""
    script = _vector_store_script()
    if not script.exists():
        raise HTTPException(status_code=404, detail="vector_store.py not found")

    try:
        result = subprocess.run(
            ["python3", str(script), "index"],
            capture_output=True, text=True, timeout=60,
            cwd=str(script.parent),
            env={**__import__("os").environ, "HERMES_HOME": str(get_hermes_home())}
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Reindex timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
