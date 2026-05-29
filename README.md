# Hermes Plugins

Plugins for [Hermes Agent](https://github.com/NousResearch/hermes-agent) that add new capabilities — not forks, not wrappers. Drop-in packages that extend what your agent can do.

## Plugins

- **hermes-dream-engine** — 🌙 Autonomous dreaming. Idle-time memory consolidation, problem re-evaluation, and creative invention. Event-driven state machine (Active→Idle→Dormant→Hypnagogic→Dreaming). LLM-driven dream phases, Telegram escalation for high-priority items, blog-style journal in dashboard.

- **hermes-webhook** — 🤖 Inter-agent messaging. Send/receive messages between Hermes agents over Tailscale. HMAC-SHA256 signed, per-agent conversation view in dashboard, sender-aware routing.

- **hermes-book-skills** — 📚 Book upload to skill generation. PDF/EPUB/TXT support, LLM extraction of concepts & methods into reusable Hermes skills, library tabs for books and skills.

## Installing a Plugin

Each plugin is self-contained with its own installer. General pattern:

```bash
# 1. Go to the plugin directory
cd hermes-dream-engine/    # or hermes-webhook/ or hermes-book-skills/

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
4. Copies plugin files to `~/.hermes/plugins/`
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

### hermes-book-skills

```bash
cd hermes-book-skills/
./install.sh
systemctl --user restart hermes-gateway.service
```

Upload books via the Books tab, then create skills from extracted concepts and methods.

## Requirements

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed
- Python 3.11+ with venv
- Linux or WSL

## Plugin Development

Plugins follow a standardized installer pattern. See `templates/install-sh-template.sh` for the reference install script.

### Key Rules

1. **User data separation**: All user data MUST be stored in `$HERMES_HOME/<plugin-name>/` — NEVER in the plugin code directory (`$HERMES_HOME/plugins/<plugin-name>/`). The installer will completely replace plugin code during upgrades.

2. **Safe upgrades**: Install scripts use `rm -rf "$PLUGIN_DEST"` to remove old code, then copy fresh. Your user data must survive this. See `templates/plugin-development-guide.md` for details.

3. **Idempotent installers**: Running install twice should be safe and produce the same result. Check for existing files before creating.

### Structure

```
hermes-plugins/
├── templates/
│   ├── install-sh-template.sh      # Reference installer script
│   └── plugin-development-guide.md   # User data preservation rules
├── hermes-dream-engine/            # Example plugin (user data in ~/.hermes/dream_engine/)
├── hermes-webhook/               # Example plugin (user data in ~/.hermes/webhookHistory.json)
├── hermes-book-skills/           # Example plugin (user data in ~/.hermes/book-library/)
```

## Contributing

Found a bug? Have an idea? Open an issue or a pull request.

## License

MIT