"""Inter-Agent Webhook dashboard plugin — backend API routes.

Mounted at /api/plugins/webhook/ by the dashboard plugin system.

Manages agent connections, sends messages, and logs message history.
Config is stored in ~/.hermes/config.yaml under inter_agent_webhook:.
Message history is stored in ~/.hermes/webhookHistory.json.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
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
    _fastapi_available = True
except Exception:
    _fastapi_available = False
    # Stub classes for import failure case
    class APIRouter:
        def get(self, *_args, **_kwargs):
            return lambda fn: fn
        def post(self, *_args, **_kwargs):
            return lambda fn: fn
        def put(self, *_args, **_kwargs):
            return lambda fn: fn
        def delete(self, *_args, **_kwargs):
            return lambda fn: fn

# Create the router at module level (available in both success and failure cases)
router = APIRouter()

HOME = get_hermes_home()
CONFIG_PATH = HOME / "config.yaml"
HISTORY_PATH = HOME / "webhookHistory.json"
SENDER_SCRIPT = HOME / "skills" / "inter-agent-webhook" / "scripts" / "send_webhook.py"


# ── Config helpers ────────────────────────────────────────

def _load_config() -> dict:
    """Load full config.yaml."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        import yaml
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _save_config(config: dict) -> None:
    """Write config.yaml safely."""
    import yaml
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def _get_webhook_config() -> dict:
    """Get inter_agent_webhook section."""
    config = _load_config()
    return config.get("inter_agent_webhook", {})


def _set_webhook_config(section: dict) -> None:
    """Set inter_agent_webhook section."""
    config = _load_config()
    config["inter_agent_webhook"] = section
    _save_config(config)


# ── History helpers ───────────────────────────────────────

def _load_history() -> list:
    """Load message history."""
    if not HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(HISTORY_PATH.read_text())
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _save_history(history: list) -> None:
    """Save message history (keep last 500 entries)."""
    history = history[-500:]
    HISTORY_PATH.write_text(json.dumps(history, indent=2, ensure_ascii=False))


def _add_history_entry(entry: dict) -> None:
    """Append a history entry."""
    history = _load_history()
    history.append(entry)
    _save_history(history)


def _get_agent_nick_from_sender(sender: str, my_name: str) -> str:
    """Map a sender name to a configured agent nick, or return the sender name."""
    section = _get_webhook_config()
    receivers = section.get("receivers", {})
    # Check if sender matches a known receiver by name
    for nick, r in receivers.items():
        # We don't store the agent's display name in config, so we
        # match by nick or by URL hostname as a heuristic
        if nick.lower() == sender.lower():
            return nick
    # Fallback: return the sender name as-is
    return sender


# ── Send message ───────────────────────────────────────────

def _send_webhook(url: str, secret: str, route: str, message: str, sender: str) -> dict:
    """Send a signed webhook POST. Returns result dict."""
    import urllib.request
    import urllib.error

    payload = json.dumps({"message": message, "sender": sender}).encode()
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    webhook_url = f"{url.rstrip('/')}/webhooks/{route}"

    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
            return {"ok": True, "status": resp.status, "body": json.loads(body) if body else {}}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"ok": False, "status": e.code, "body": body}
    except Exception as e:
        return {"ok": False, "status": 0, "body": str(e)}


# ── API: Inbound message logging (called by webhook handler) ──

@router.post("/inbound")
async def log_inbound(data: dict):
    """Log an inbound message from another agent.

    Called by the webhook adapter when an agent-to-agent message
    is received and processed. Stores it in history for the
    conversation view.
    """
    sender = (data.get("sender") or "unknown").strip()
    message = (data.get("message") or "").strip()
    mode = (data.get("mode") or "ping").strip()
    response = (data.get("response") or "").strip()
    status = (data.get("status") or "received").strip()

    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    section = _get_webhook_config()
    my_name = section.get("my_name", "Agent")
    nick = _get_agent_nick_from_sender(sender, my_name)

    entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "direction": "in",
        "nick": nick,
        "sender_name": sender,
        "mode": mode,
        "message": message,
        "response": response,
        "status": status,
    }
    _add_history_entry(entry)

    return {"ok": True, "entry_id": entry["id"]}


# ── API: Get all agents ────────────────────────────────────

@router.get("/agents")
async def list_agents():
    """List all configured receiver agents."""
    section = _get_webhook_config()
    receivers = section.get("receivers", {})
    my_name = section.get("my_name", "Agent")
    agents = []
    for nick, r in receivers.items():
        agents.append({
            "nick": nick,
            "url": r.get("url", ""),
            "route_ping": r.get("route_ping", "agent-ping"),
            "route_notify": r.get("route_notify", "agent-notify"),
            "has_secret": bool(r.get("secret")),
            "added_at": r.get("added_at", None),
        })
    return {"agents": agents, "my_name": my_name}


# ── API: Add new agent ─────────────────────────────────────

@router.post("/agents")
async def add_agent(data: dict):
    """Add a new receiver agent."""
    nick = (data.get("nick") or "").strip()
    url = (data.get("url") or "").strip().rstrip("/")
    secret = (data.get("secret") or "").strip()
    route_ping = (data.get("route_ping") or "agent-ping").strip()
    route_notify = (data.get("route_notify") or "agent-notify").strip()

    if not nick:
        raise HTTPException(status_code=400, detail="Agent nickname is required")
    if not url:
        raise HTTPException(status_code=400, detail="Agent URL is required")
    if not secret:
        raise HTTPException(status_code=400, detail="Webhook secret is required")

    section = _get_webhook_config()
    if "receivers" not in section:
        section["receivers"] = {}

    section["receivers"][nick] = {
        "url": url,
        "secret": secret,
        "route_ping": route_ping,
        "route_notify": route_notify,
        "added_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    _set_webhook_config(section)

    return {"ok": True, "nick": nick, "url": url}


# ── API: Update agent ──────────────────────────────────────

@router.put("/agents/{nick}")
async def update_agent(nick: str, data: dict):
    """Update an existing receiver agent."""
    section = _get_webhook_config()
    receivers = section.get("receivers", {})
    if nick not in receivers:
        raise HTTPException(status_code=404, detail=f"Agent '{nick}' not found")

    r = receivers[nick]
    if "url" in data:
        r["url"] = data["url"].strip().rstrip("/")
    if "secret" in data and data["secret"]:
        r["secret"] = data["secret"].strip()
    if "route_ping" in data:
        r["route_ping"] = data["route_ping"].strip()
    if "route_notify" in data:
        r["route_notify"] = data["route_notify"].strip()

    section["receivers"] = receivers
    _set_webhook_config(section)
    return {"ok": True, "nick": nick}


# ── API: Delete agent ──────────────────────────────────────

@router.delete("/agents/{nick}")
async def delete_agent(nick: str):
    """Remove a receiver agent."""
    section = _get_webhook_config()
    receivers = section.get("receivers", {})
    if nick not in receivers:
        raise HTTPException(status_code=404, detail=f"Agent '{nick}' not found")
    del receivers[nick]
    section["receivers"] = receivers
    _set_webhook_config(section)
    return {"ok": True}


# ── API: Send message ──────────────────────────────────────

@router.post("/send")
async def send_message(data: dict):
    """Send a message to a receiver agent."""
    nick = (data.get("nick") or "").strip()
    mode = (data.get("mode") or "ping").strip()  # "ping" or "notify"
    message = (data.get("message") or "").strip()

    if not nick:
        raise HTTPException(status_code=400, detail="Receiver nickname is required")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    section = _get_webhook_config()
    receivers = section.get("receivers", {})
    if nick not in receivers:
        raise HTTPException(status_code=404, detail=f"Agent '{nick}' not found")

    r = receivers[nick]
    my_name = section.get("my_name", "Agent")
    route = r.get("route_ping" if mode == "ping" else "route_notify", mode)

    result = _send_webhook(
        url=r["url"],
        secret=r["secret"],
        route=route,
        message=message,
        sender=my_name,
    )

    # Log to history
    entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "direction": "out",
        "nick": nick,
        "mode": mode,
        "message": message,
        "status": "delivered" if result["ok"] else "failed",
        "http_status": result.get("status", 0),
        "response": result.get("body", {}),
    }
    _add_history_entry(entry)

    return {
        "ok": result["ok"],
        "status": result.get("status", 0),
        "response": result.get("body", {}),
        "entry_id": entry["id"],
    }


# ── API: Full message history ──────────────────────────────

@router.get("/history")
async def get_history(limit: int = Query(default=50, ge=1, le=500), offset: int = Query(default=0, ge=0)):
    """Get full message history, newest first."""
    history = _load_history()
    total = len(history)
    history_rev = list(reversed(history))
    page = history_rev[offset:offset + limit]
    return {"messages": page, "total": total, "offset": offset, "limit": limit}


# ── API: Per-agent conversation history ────────────────────

@router.get("/history/{nick}")
async def get_agent_history(nick: str, limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    """Get conversation history with a specific agent, newest first.

    Returns both inbound and outbound messages involving the given
    agent nick, so the dashboard can render a full conversation thread.
    """
    history = _load_history()
    # Filter messages involving this nick (either direction)
    filtered = [
        m for m in history
        if m.get("nick", "").lower() == nick.lower()
    ]
    total = len(filtered)
    filtered_rev = list(reversed(filtered))
    page = filtered_rev[offset:offset + limit]
    return {"messages": page, "total": total, "offset": offset, "limit": limit, "nick": nick}


# ── API: Conversations list ────────────────────────────────

@router.get("/conversations")
async def get_conversations():
    """List all agent conversations with last message preview.

    Returns a summary per agent nick: last message, timestamp,
    message count, and unread indicator.
    """
    history = _load_history()
    conversations: Dict[str, dict] = {}

    for entry in history:
        nick = entry.get("nick", "unknown")
        if nick not in conversations:
            conversations[nick] = {
                "nick": nick,
                "last_message": entry.get("message", ""),
                "last_timestamp": entry.get("timestamp", ""),
                "last_direction": entry.get("direction", ""),
                "count": 0,
                "in_count": 0,
                "out_count": 0,
            }
        conv = conversations[nick]
        conv["count"] += 1
        conv["last_message"] = entry.get("message", "")
        conv["last_timestamp"] = entry.get("timestamp", "")
        conv["last_direction"] = entry.get("direction", "")
        if entry.get("direction") == "in":
            conv["in_count"] += 1
        else:
            conv["out_count"] += 1

    # Sort by last timestamp descending
    result = sorted(conversations.values(), key=lambda c: c["last_timestamp"], reverse=True)
    return {"conversations": result, "total": len(result)}


# ── API: Clear history ─────────────────────────────────────

@router.delete("/history")
async def clear_history():
    """Clear all message history."""
    _save_history([])
    return {"ok": True}


# ── API: Clear history for specific agent ──────────────────

@router.delete("/history/{nick}")
async def clear_agent_history(nick: str):
    """Clear message history for a specific agent."""
    history = _load_history()
    filtered = [m for m in history if m.get("nick", "").lower() != nick.lower()]
    _save_history(filtered)
    return {"ok": True, "removed": len(history) - len(filtered)}


# ── API: Get my identity ───────────────────────────────────

@router.get("/identity")
async def get_identity():
    """Get this agent's identity (name, webhook status)."""
    section = _get_webhook_config()
    config = _load_config()

    # Check if webhook platform is enabled
    platforms = config.get("platforms", {})
    webhook_platform = platforms.get("webhook", {})
    webhook_enabled = webhook_platform.get("enabled", False)
    webhook_port = webhook_platform.get("extra", {}).get("port", 8644)
    routes = webhook_platform.get("extra", {}).get("routes", {})

    return {
        "my_name": section.get("my_name", "Agent"),
        "my_url": section.get("my_url", ""),
        "webhook_enabled": webhook_enabled,
        "webhook_port": webhook_port,
        "routes": list(routes.keys()),
        "receiver_count": len(section.get("receivers", {})),
        "host_secret": webhook_platform.get("extra", {}).get("secret", ""),
    }


# ── API: Generate a secure webhook secret ──────────────────

@router.get("/generate-secret")
async def generate_secret():
    """Generate a cryptographically secure 64-char hex HMAC secret.

    Uses os.urandom (CSPRNG) — suitable for production use.
    Returns the secret once; the caller must store it.
    """
    import secrets
    secret = secrets.token_hex(32)  # 32 bytes = 64 hex chars
    return {"secret": secret}


# ── API: Test connection ───────────────────────────────────

@router.post("/test/{nick}")
async def test_connection(nick: str):
    """Send a test ping to verify the agent connection works."""
    section = _get_webhook_config()
    receivers = section.get("receivers", {})
    if nick not in receivers:
        raise HTTPException(status_code=404, detail=f"Agent '{nick}' not found")

    r = receivers[nick]
    my_name = section.get("my_name", "Agent")

    result = _send_webhook(
        url=r["url"],
        secret=r["secret"],
        route=r.get("route_ping", "agent-ping"),
        message=f"🔔 Test ping from {my_name} — connection verified!",
        sender=my_name,
    )

    # Log test
    entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "direction": "out",
        "nick": nick,
        "mode": "ping",
        "message": f"🔔 Test ping from {my_name}",
        "status": "delivered" if result["ok"] else "failed",
        "http_status": result.get("status", 0),
        "response": result.get("body", {}),
        "is_test": True,
    }
    _add_history_entry(entry)

    return {
        "ok": result["ok"],
        "status": result.get("status", 0),
        "response": result.get("body", {}),
    }
