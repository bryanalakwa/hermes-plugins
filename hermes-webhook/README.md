# Hermes Inter-Agent Webhook Plugin v1.0.0

Agent-to-agent communication over Tailscale. Send messages between Hermes AI agents, manage connections, and view per-agent conversation history from the dashboard.

## What It Does

- **Send messages** to other Hermes agents via webhook (ping = AI-processed, notify = direct delivery)
- **Receive messages** from other agents and respond automatically
- **Dashboard UI** at `/agents` tab — add agents, send messages, view conversation history per agent
- **CLI scripts** for sending messages from the terminal
- **HMAC-signed** webhook payloads for security

## Quick Install

```bash
git clone https://github.com/bryanalakwa/hermes-plugins.git
cd hermes-plugins/hermes-webhook
chmod +x install.sh
./install.sh
```

The installer will:
1. Remove any old version completely
2. Copy all plugin files (dashboard, scripts, references)
3. Install Python dependencies
4. Enable the webhook platform in config (with auto-generated secrets)
5. Restart the gateway

**Note:** If the dashboard shows the old version after install, close ALL browser tabs with the dashboard and reopen (Ctrl+Force-Reload).

## Requirements

- Hermes Agent with gateway running (systemd or `hermes gateway`)
- Python 3.7+ with venv
- Tailscale (for inter-agent communication)
- PyYAML (auto-installed)

## Configuration

After install, edit `~/.hermes/config.yaml`:

```yaml
inter_agent_webhook:
  my_name: YourAgentName
  my_url: https://your-agent.tailscale-host.ts.net
  receivers:
    OtherAgent:
      url: https://other-agent.tailscale-host.ts.net
      secret: <shared-secret>
      route_ping: agent-ping
      route_notify: agent-notify
```

## Sending Messages

```bash
# AI-processed ping (the receiving agent thinks and responds)
bash scripts/send.sh ping "Hello from my agent!"

# Direct notification (delivered as-is)
bash scripts/send.sh notify "System alert: backup complete"

# Or use the Python script directly
python3 scripts/send_webhook.py ping "Hello!" --receiver OtherAgent
```

## Files

| Path | Purpose |
|------|---------|
| `install.sh` | Full installer / upgrader |
| `plugin.yaml` | Plugin metadata and dashboard config |
| `__init__.py` | Plugin version |
| `dashboard/` | Dashboard UI (JS, CSS, manifest, API) |
| `scripts/` | CLI send scripts |
| `references/protocol.md` | Webhook protocol documentation |

## Changelog

### v1.0.0 (2026-05-24)
- Initial release: webhook send/receive, dashboard UI, CLI scripts
- Dashboard tab at `/agents` for agent management
- Secure HMAC-signed webhook payloads
- Python and bash CLI scripts for message sending
