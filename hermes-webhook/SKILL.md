---
name: hermes-webhook
description: >
  Inter-agent webhook communication over Tailscale. Manage agent connections,
  send messages (AI ping or direct notify), view message history.
  Dashboard tab at /agents.
version: 2.1.0
triggers:
  - webhook
  - inter-agent
  - agent communication
  - send message
  - agent network
  - tailscale funnel
---

# Hermes Inter-Agent Webhook Plugin

Send and receive messages between AI agents via webhooks over Tailscale Funnel. No public IP or port forwarding required.

## Architecture

```
┌─────────────────┐         HTTPS          ┌─────────────────────┐
│  Sender Agent    │ ───────────────────►  │  Receiver Agent     │
│  • Dashboard UI  │   HMAC-SHA256 signed  │  • Webhook platform │
│  • send.sh       │                       │  • Tailscale Funnel │
│  • send_webhook.py│ ◄──────────────────  │  • Routes (ping/    │
│                  │   200/202 response    │    notify)          │
└─────────────────┘                        └─────────────────────┘
```

**Two message modes:**
- **AI Ping** — receiving agent reads, reasons, responds (costs tokens)
- **Direct Notify** — message forwarded verbatim to receiver's Telegram (zero token cost)

## Installation

### Quick Install
```bash
chmod +x install.sh
./install.sh
```

### Manual Install
1. Copy dashboard: `cp -r dashboard/ $HERMES_AGENT/plugins/hermes-webhook/dashboard/`
2. Copy scripts: `cp -r scripts/ $HERMES_AGENT/plugins/hermes-webhook/scripts/`
3. Copy references: `cp -r references/ $HERMES_AGENT/plugins/hermes-webhook/references/`
4. Install PyYAML: `$HERMES_AGENT/venv/bin/pip install pyyaml`
5. Create history file: `echo '[]' > ~/.hermes/webhookHistory.json`
6. Enable webhook platform in config.yaml (see below)
7. Restart gateway: `systemctl --user restart hermes-gateway.service`

## Webhook Platform Config

In `~/.hermes/config.yaml`:

```yaml
platforms:
  webhook:
    enabled: true
    extra:
      host: "0.0.0.0"
      port: 8644
      routes:
        agent-ping:
          secret: "<64-char-hex>"
          prompt: "Message from another agent: {message}\nSender: {sender}\nRespond appropriately."
          deliver: "telegram"
        agent-notify:
          secret: "<64-char-hex>"
          deliver_only: true
          deliver: "telegram"
          prompt: "📨 Agent notification: {message}"
```

## Agent Config (sender side)

In `~/.hermes/config.yaml`:

```yaml
inter_agent_webhook:
  my_name: "Eliana"
  receivers:
    remy:
      url: "https://remy.tailXXXXX.ts.net"
      secret: "<64-char-hex-shared-secret>"
      route_ping: "agent-ping"
      route_notify: "agent-notify"
```

## Dashboard

The Agents tab at `http://127.0.0.1:9119/agents` provides:

- **Agent management**: Add, edit, delete agent connections
- **Send messages**: AI Ping or Direct Notify with mode toggle
- **Test connection**: Send a test ping to verify connectivity
- **Message history**: View sent/received messages with delivery status
- **Identity display**: Shows your agent name and webhook status

## CLI Usage

```bash
# Send AI-processed message
bash ~/.hermes/skills/inter-agent-webhook/scripts/send.sh ping "Hello!"

# Send direct notification
bash ~/.hermes/skills/inter-agent-webhook/scripts/send.sh notify "Alert!"

# From Python (any platform)
python3 ~/.hermes/skills/inter-agent-webhook/scripts/send_webhook.py ping "Hello!" --receiver remy
```

## Protocol

Messages are JSON POST requests with HMAC-SHA256 authentication:

```
POST /webhooks/{route_name}
Content-Type: application/json
X-Webhook-Signature: {hmac_hex}

{"message": "Hello!", "sender": "Eliana"}
```

See `references/protocol.md` for the full protocol specification.

## Security

- HMAC-SHA256 signed messages — receivers validate every request
- Tailscale Funnel provides automatic TLS
- No open ports — Funnel is outbound-only
- Each route has its own unique secret
- Rate limiting: 30 req/min per route
- Idempotency: duplicate delivery IDs skipped for 1 hour

## Files

| File | Path |
|------|------|
| Dashboard API | `$HERMES_AGENT/plugins/hermes-webhook/dashboard/plugin_api.py` |
| Dashboard JS | `$HERMES_AGENT/plugins/hermes-webhook/dashboard/dist/index.js` |
| Install script | `$HERMES_AGENT/plugins/hermes-webhook/install.sh` |
| Python sender | `$HERMES_AGENT/plugins/hermes-webhook/scripts/send_webhook.py` |
| Bash sender | `$HERMES_AGENT/plugins/hermes-webhook/scripts/send.sh` |
| Protocol ref | `$HERMES_AGENT/plugins/hermes-webhook/references/protocol.md` |
| History log | `~/.hermes/webhookHistory.json` |
