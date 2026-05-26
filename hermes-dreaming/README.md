# ⚠️ DEPRECATED — Hermes Dreaming Plugin v2.0

**This plugin has been superseded by [hermes-dream-engine](../hermes-dream-engine/).**

The old `hermes-dreaming` plugin used cron jobs and ChromaDB vector search for idle-time memory consolidation. The new `hermes-dream-engine` replaces it with:
- Event-driven state machine (no cron dependency)
- LLM-driven dream phases (consolidation, re-evaluation, invention, integration)
- Telegram escalation for high-priority items
- Holographic fact store only (no ChromaDB dependency)
- Blog-style journal with modal detail view

## Migration

```bash
# 1. Install the new dream engine
cd hermes-dream-engine/
./install.sh

# 2. The old dreaming plugin will be overwritten automatically

# 3. Restart the gateway
systemctl --user restart hermes-gateway.service
```

See [hermes-dream-engine](../hermes-dream-engine/) for full documentation.
