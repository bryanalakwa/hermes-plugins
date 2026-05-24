---
name: hermes-dreaming
description: >
  Idle-time memory consolidation and insight generation for Hermes agents.
  Two-tier memory: holographic fact store (SQLite) + ChromaDB vector search.
  Dashboard tab at /dreams. Cron-triggered every 30min with max 2 dreams/day.
triggers:
  - dream
  - dreaming
  - memory consolidation
  - idle cognition
  - dream journal
  - vector store
  - chromadb
---

# Hermes Dreaming Plugin

Idle-time cognition system for Hermes agents. Dreams trigger after 30 minutes of inactivity, consolidate memories across two tiers, and surface insights worth sharing.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Dreaming Cron (30min)               │
│  Gate: 30min idle? Max 2/day? 8h cooldown?          │
└──────────────┬──────────────────────┬───────────────┘
               │                      │
    ┌──────────▼──────────┐ ┌────────▼────────────┐
    │  Tier 1: Holographic │ │  Tier 2: ChromaDB   │
    │  SQLite fact_store   │ │  Vector search      │
    │  • fact_store tool   │ │  • vector_store.py  │
    │  • fact_feedback     │ │  • Semantic search  │
    │  • Entity resolution │ │  • Unlimited capacity│
    │  • Trust scoring     │ │  • Pattern finding  │
    └──────────┬──────────┘ └────────┬────────────┘
               │                      │
    ┌──────────▼──────────────────────▼───────────────┐
    │              Dream Processing                    │
    │  Consolidate → Connect → Rehearse → Prune       │
    │  → Synthesize → Re-index → Journal              │
    └──────────┬──────────────────────┬───────────────┘
               │                      │
    ┌──────────▼──────────┐ ┌────────▼────────────┐
    │  Dream Journal       │ │  Dashboard (/dreams) │
    │  ~/.hermes/dreams/   │ │  • Journal entries   │
    │  dream-YYYY-MM-DD.md │ │  • Vector stats      │
    │  state.json          │ │  • Re-index button   │
    └─────────────────────┘ └──────────────────────┘
```

## Installation

### Quick Install

```bash
# From the plugin directory:
chmod +x install.sh
./install.sh
```

### Manual Install

1. **Copy dashboard plugin:**
   ```bash
   cp -r dashboard/ $HERMES_AGENT/plugins/hermes-dreaming/dashboard/
   ```

2. **Copy vector store script:**
   ```bash
   cp vector_store.py $HERMES_AGENT/plugins/memory/holographic/vector_store.py
   ```

3. **Install dependencies:**
   ```bash
   $HERMES_AGENT/venv/bin/pip install chromadb
   ```

4. **Create dreams directory:**
   ```bash
   mkdir -p ~/.hermes/dreams
   echo '{"last_dream_at":null,"dreams_today":0,"last_dream_date":null,"total_dreams":0}' > ~/.hermes/dreams/state.json
   ```

5. **Create cron job:**
   ```bash
   hermes cron add --name "dreaming" --schedule "every 30m" --deliver origin --prompt "..."
   ```

6. **Update config.yaml:**
   ```yaml
   memory:
     memory_char_limit: 8000
     user_char_limit: 4000
   ```

7. **Restart gateway:**
   ```bash
   systemctl --user restart hermes-gateway.service
   ```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `idle_threshold_minutes` | 30 | Minutes of inactivity before dreaming |
| `max_dreams_per_day` | 2 | Daily dream cap |
| `cooldown_hours` | 8 | Minimum hours between dreams |
| `memory_char_limit` | 8000 | Max memory chars per session turn |
| `vector_collection` | holographic_facts | ChromaDB collection name |

## Dream Procedure

### Phase 1: Gate Checks
All must pass:
1. 30+ minutes since last user activity
2. Fewer than 2 dreams today
3. 8+ hours since last dream
4. New facts or conversations since last dream

### Phase 2: Memory Trawl
1. `fact_store` (action=list, limit=50) — high-trust facts
2. `session_search` — recent conversations
3. Read last dream journal entry
4. `python vector_store.py stats` — vector health

### Phase 3: Deep Vector Search
```bash
python vector_store.py search "user preferences patterns"
python vector_store.py search "problems challenges unresolved"
python vector_store.py search "connections between topics"
```

### Phase 4: Process
- **Consolidate**: Merge related facts, remove duplicates
- **Connect**: Find unexpected relationships via vector search
- **Rehearse**: Re-examine past problems with fresh eyes
- **Prune**: Remove low-trust, stale, contradicted facts
- **Synthesize**: Generate new insights, add new facts
- **Re-index**: `python vector_store.py index`

### Phase 5: Evaluate Wake-Worthiness
Only notify user for genuine insights:
- New connection between unrelated memories
- Better solution to a known problem
- Important contradiction found
- Otherwise: stay silent, just journal

### Phase 6: Journal
Write to `~/.hermes/dreams/dream-YYYY-MM-DD-HHMM.md`:
- What was processed, vector searches run
- Key connections, insights, actions taken
- Whether user was notified

### Phase 7: Update State
Update `~/.hermes/dreams/state.json`:
```json
{
  "last_dream_at": 1716400800,
  "dreams_today": 1,
  "last_dream_date": "2026-05-24",
  "total_dreams": 42
}
```

## Vector Store Management

### Re-index after adding facts:
```bash
cd $HERMES_AGENT/plugins/memory/holographic
HERMES_HOME=$HERMES_HOME python vector_store.py index
```

### Search manually:
```bash
python vector_store.py search "your query here"
```

### Check stats:
```bash
python vector_store.py stats
```

## Dashboard

The Dreams tab appears in the web dashboard at `http://127.0.0.1:9119/dreams`:
- Dream journal entries with insights and connections highlighted
- Vector store stats (facts count, indexed count, storage size)
- Re-index button to sync vector store with holographic facts
- Stats: total dreams, dreams today, journal entries, last dream

## Files

| File | Path |
|------|------|
| Plugin manifest | `$HERMES_AGENT/plugins/hermes-dreaming/plugin.yaml` |
| Dashboard API | `$HERMES_AGENT/plugins/hermes-dreaming/dashboard/plugin_api.py` |
| Dashboard JS | `$HERMES_AGENT/plugins/hermes-dreaming/dashboard/dist/index.js` |
| Dashboard CSS | `$HERMES_AGENT/plugins/hermes-dreaming/dashboard/dist/style.css` |
| Vector store | `$HERMES_AGENT/plugins/memory/holographic/vector_store.py` |
| Install script | `$HERMES_AGENT/plugins/hermes-dreaming/install.sh` |
| Dream journal | `~/.hermes/dreams/dream-YYYY-MM-DD-HHMM.md` |
| Dream state | `~/.hermes/dreams/state.json` |
| Vector DB | `~/.hermes/chroma_db/` |
| Holographic DB | `~/.hermes/memory_store.db` |

## Constraints
- Keep dreams compact: 8-15 tool calls
- Always re-index after modifying facts
- Only surface truly valuable insights
- Don't re-dream the same material
- Max 2 dreams per day, 8h cooldown
