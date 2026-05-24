# Hermes Dreaming Plugin v2.0

Idle-time memory consolidation and insight generation for Hermes agents.

Dreams trigger after **30 minutes** of inactivity, consolidate memories across a **two-tier system** (holographic fact store + ChromaDB vector search), and surface insights worth sharing with the user.

## Features

- **Two-tier memory**: Holographic SQLite fact store (structured, trusted) + ChromaDB vector search (unlimited, semantic)
- **30-minute idle trigger**: Dreams start sooner than the old 40-minute threshold
- **Dashboard tab**: `/dreams` in the web dashboard — view journal entries, vector stats, re-index button
- **Smart gating**: Max 2 dreams/day, 8-hour cooldown, only dreams when there's new material
- **Self-maintaining**: Automatically re-indexes vector store after modifying facts
- **Fully local**: No cloud dependencies, no API keys needed

## Requirements

- Hermes Agent with `hermes-agent` installed
- Python 3.11+ venv at `$HERMES_AGENT/venv/`
- Holographic memory plugin (`plugins/memory/holographic/`)
- ~80MB disk space for the ONNX embedding model (downloaded on first use)
- ~6GB RAM available

## Quick Install

```bash
# Clone or copy this plugin directory, then:
cd hermes-dreaming/
chmod +x install.sh
./install.sh
```

The install script handles everything:
1. Copies dashboard plugin files
2. Links vector_store.py to the holographic memory plugin
3. Installs ChromaDB (`pip install chromadb`)
4. Creates `~/.hermes/dreams/` directory and state.json
5. Runs initial vector store indexing
6. Creates the 30-minute dreaming cron job
7. Updates `memory_char_limit` to 8000 in config.yaml

**After install, restart the gateway:**
```bash
systemctl --user restart hermes-gateway.service
```

## Manual Install

See SKILL.md for step-by-step manual installation instructions.

## Importing Into Another Agent

To give another Hermes agent the dreaming ability:

1. **Copy the plugin directory** to the target agent:
   ```bash
   cp -r hermes-dreaming/ $TARGET_HERMES_AGENT/plugins/hermes-dreaming/
   ```

2. **Copy the vector store script:**
   ```bash
   cp hermes-dreaming/vector_store.py $TARGET_HERMES_AGENT/plugins/memory/holographic/vector_store.py
   ```

3. **Run the install script** on the target:
   ```bash
   cd $TARGET_HERMES_AGENT/plugins/hermes-dreaming/
   HERMES_AGENT_DIR=$TARGET_HERMES_AGENT ./install.sh
   ```

4. **Restart the target's gateway:**
   ```bash
   systemctl --user restart hermes-gateway.service
   ```

The Dreams tab will appear in the target agent's dashboard at `http://127.0.0.1:9119/dreams`.

## Dashboard

Once installed, the Dreams tab shows:

- **Stats**: Total dreams, dreams today, journal entries, last dream time
- **Vector Store**: Facts count, indexed count, storage size, re-index button
- **Dream Journal**: Cards showing each dream's insights and connections
- **Detail View**: Click any dream to see the full journal entry

## Configuration

Edit `~/.hermes/config.yaml`:

```yaml
memory:
  memory_char_limit: 8000    # was 2200 — more facts per turn
  user_char_limit: 4000      # was 1375
  provider: holographic
```

## How Dreams Work

1. **Every 30 minutes**, the cron job fires
2. **Gate checks**: 30min idle? <2 dreams today? 8h cooldown? New material?
3. **Memory trawl**: Gather facts from both tiers
4. **Vector search**: Semantic search across ALL facts for hidden connections
5. **Process**: Consolidate, connect, rehearse, prune, synthesize
6. **Re-index**: Keep vector store in sync
7. **Evaluate**: Only wake user for genuine insights
8. **Journal**: Write compact entry to `~/.hermes/dreams/`

## Files

```
hermes-dreaming/
├── install.sh                    # One-command installer
├── plugin.yaml                   # Plugin manifest
├── SKILL.md                      # Skill reference for agents
├── README.md                     # This file
├── dashboard/
│   ├── manifest.json             # Dashboard tab config
│   ├── plugin_api.py             # Backend API routes
│   └── dist/
│       ├── index.js              # Frontend React component
│       └── style.css             # Plugin styles
└── references/
    └── dreaming.md               # Dreaming procedure reference
```

## Troubleshooting

**"ChromaDB not installed" in dashboard:**
```bash
$HERMES_AGENT/venv/bin/pip install chromadb
```

**Vector store out of sync:**
```bash
cd $HERMES_AGENT/plugins/memory/holographic
HERMES_HOME=$HERMES_HOME python vector_store.py index
```

**Dreams not triggering:**
```bash
# Check cron job:
hermes cron list

# Check state:
cat ~/.hermes/dreams/state.json

# Check logs:
journalctl --user -u hermes-gateway.service -f
```

**ONNX model download slow:**
The first run downloads ~80MB embedding model. This is a one-time cost. Subsequent runs use the cached model at `~/.cache/chroma/onnx_models/`.
