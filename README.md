# Hermes Plugins

Plugins for [Hermes Agent](https://github.com/NousResearch/hermes-agent) that add new capabilities — not forks, not wrappers. Drop-in packages that extend what your agent can do.

## Plugins

| Plugin | What it does |
|---|---|
| [hermes-dreaming](hermes-dreaming/) | 🌙 Idle-time memory consolidation — dreams while you're away, surfaces insights worth sharing. Two-tier memory (holographic + ChromaDB). Dashboard tab at `/dreams`. |
| [hermes-webhook](hermes-webhook/) | 🤖 Inter-agent messaging — send/receive messages between Hermes agents or any HTTP endpoint. HMAC-SHA256 signed. Dashboard tab at `/agents`. |

## Installing a Plugin

Each plugin is self-contained. To install:

```bash
# 1. Go to the plugin directory
cd hermes-dreaming/    # or hermes-webhook/

# 2. Run the installer
chmod +x install.sh
./install.sh

# 3. Restart the gateway
systemctl --user restart hermes-gateway.service
```

Each plugin has its own `README.md` with full install instructions, configuration, and troubleshooting.

## Requirements

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed
- Python 3.11+ with venv
- Linux or WSL

## Contributing

Found a bug? Have an idea? Open an issue or a pull request. These plugins are built to be useful — if something doesn't work or could work better, say so.

## License

MIT — use them, fork them, improve them. Just don't blame me if your agent starts dreaming about your browser history. 😄
