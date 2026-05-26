# Hermes Plugins

Plugins for [Hermes Agent](https://github.com/NousResearch/hermes-agent) that add new capabilities — not forks, not wrappers. Drop-in packages that extend what your agent can do.

## Plugins

| Plugin | What it does |
|---|---|
| [hermes-dream-engine](hermes-dream-engine/) | 🌙 Autonomous dreaming — idle-time memory consolidation, problem re-evaluation, and creative invention. Event-driven state machine (Active→Idle→Dormant→Hypnagogic→Dreaming). LLM-driven dream phases. Telegram escalation for high-priority items. Blog-style journal in dashboard. |
| [hermes-webhook](hermes-webhook/) | 🤖 Inter-agent messaging — send/receive messages between Hermes agents over Tailscale. HMAC-SHA256 signed. Per-agent conversation view in dashboard. Sender-aware routing. |

## Installing a Plugin

Each plugin is self-contained with its own installer. General pattern:

```bash
# 1. Go to the plugin directory
cd hermes-dream-engine/    # or hermes-webhook/

# 2. Run the installer
chmod +x install.sh
./install.sh

# 3. Restart the gateway
systemctl --user restart hermes-gateway.service
```

### hermes-dream-engine

The dream engine installer handles everything automatically:

```bash
cd hermes-dream-engine/
./install.sh
systemctl --user restart hermes-gateway.service
```

What the installer does:
1. Sets up holographic fact store (SQLite + FTS5 + WAL)
2. Creates memory directory structure (`~/.hermes/memories/`)
3. Configures `memory.provider: holographic` in config.yaml
4. Copies plugin files to `~/.hermes/hermes-agent/plugins/`
5. Installs dependencies
6. Verifies installation

After restart, the dashboard tab appears at the **Dream Engine** tab in the web dashboard (port 9119).

### hermes-webhook

```bash
cd hermes-webhook/
./install.sh
systemctl --user restart hermes-gateway.service
```

Requires a Tailscale Funnel URL and shared secret. See the plugin's `README.md` for configuration details.

## Requirements

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed
- Python 3.11+ with venv
- Linux or WSL

## Contributing

Found a bug? Have an idea? Open an issue or a pull request.

## License

MIT
