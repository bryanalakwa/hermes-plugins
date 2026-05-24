# Hermes Inter-Agent Webhook Plugin v2.0

Send and receive messages between Hermes agents — or between your agent and any HTTP endpoint. Comes with a dashboard tab for managing agents, sending test messages, and viewing history.

## Features

- **Two send modes:**
  - `agent-ping` — sends a message, the receiving agent reasons and responds
  - `agent-notify` — direct verbatim forward, zero LLM cost
- **Dashboard tab:** `/agents` in the web dashboard — manage connections, send messages, view history
- **HMAC-SHA256 signing** — every message is authenticated with a shared secret
- **Hermes skill included** — agents can set up the webhook programmatically via the skill
- **Scripts included** — `send.sh` and `send_webhook.py` for use outside the agent (CI, cron, etc.)

## Requirements

- Hermes Agent with `hermes-agent` installed
- Python 3.11+ venv at `$HERMES_AGENT/venv/`
- A publicly reachable URL for the receiving agent (Tailscale Funnel, ngrok, public IP, etc.)

## Quick Install

```bash
# Clone or copy this plugin directory, then:
cd hermes-webhook/
chmod +x install.sh
./install.sh
```

The install script handles everything:
1. Copies dashboard plugin files to `~/.hermes/hermes-agent/plugins/hermes-webhook/`
2. Installs the `inter-agent-webhook` skill to `~/.hermes/skills/inter-agent-webhook/`
3. Creates `~/.hermes/webhookAgents.json` (empty agent list)
4. Creates `~/.hermes/webhookHistory.json` (empty history)

**After install, restart the gateway:**
```bash
systemctl --user restart hermes-gateway.service
```

## Connecting Two Agents

On **Agent A** (the sender), run:

```bash
# Add Agent B as a connection
hermes webhook add --name "Agent B" \
  --url "https://agent-b.example.com/webhook" \
  --secret "your-shared-secret"
```

On **Agent B** (the receiver), the webhook endpoint needs to:
1. Verify the HMAC-SHA256 signature (header: `X-Hermes-Signature`)
2. Process the JSON body
3. Return `{"status": "accepted"}` or `{"status": "delivered"}`

See `references/protocol.md` for the full protocol specification.

## Sending Messages

Via the skill:
```bash
# AI-powered ping (agent reasons, then responds)
hermes webhook send --agent "Agent B" --mode ping --message "Hello from Agent A!"

# Direct notify (verbatim, zero LLM cost)
hermes webhook send --agent "Agent B" --mode notify --message "FYI: deployment complete"
```

Via script:
```bash
# send.sh (uses configured agents)
./scripts/send.sh "Agent B" "ping" "Hello!"

# send_webhook.py (standalone)
./scripts/send_webhook.py \
  --url "https://agent-b.example.com/webhook" \
  --secret "your-secret" \
  --mode ping \
  --message "Hello!"
```

## Dashboard

Once installed, the Agents tab at `http://127.0.0.1:9119/agents` shows:

- **Connected Agents** — list of configured agent connections (name, URL, status)
- **Send Message** — pick an agent, choose mode, type a message, send
- **History** — log of all sent/received messages with timestamps
- **Test** — ping an agent and see the response inline

## Files

```
hermes-webhook/
├── install.sh                    # One-command installer
├── plugin.yaml                   # Plugin manifest
├── SKILL.md                      # Skill reference for agents
├── dashboard/
│   ├── manifest.json             # Dashboard tab config
│   ├── plugin_api.py             # Backend API routes
│   └── dist/
│       ├── index.js              # Frontend React component
│       └── style.css             # Plugin styles
├── scripts/
│   ├── send.sh                   # Bash sender (uses configured agents)
│   ├── send_webhook.py           # Python sender (standalone)
│   └── setup.sh                  # Initial setup helper
└── references/
    └── protocol.md               # Full webhook protocol specification
```

## Protocol

Messages are signed JSON POST requests. See `references/protocol.md` for:
- Message format
- HMAC-SHA256 signature verification
- `agent-ping` vs `agent-notify` semantics
- Error handling

## Troubleshooting

**"Connection failed" when sending:**
```bash
# Test the URL is reachable
curl -I https://agent-b.example.com/webhook

# Check the agent config
cat ~/.hermes/webhookAgents.json
```

**Signature verification failing on receiver:**
```bash
# Test with the included script
./scripts/send_webhook.py --url <url> --secret <secret> --mode notify --message "test"
```
