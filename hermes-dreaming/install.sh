#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Hermes Dreaming Plugin — install.sh
# ─────────────────────────────────────────────────────────
# Installs the dreaming plugin for any Hermes agent:
#   1. Copies dashboard plugin to hermes-agent/plugins/
#   2. Copies the vector_store.py overlay for holographic memory
#   3. Installs Python dependencies (chromadb)
#   4. Creates ~/.hermes/dreams/ directory and state.json
#   5. Sets up the 30-minute dreaming cron job
#   6. Re-indexes existing holographic facts into ChromaDB
#   7. Increases memory_char_limit for richer context injection
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
#
# Or directly:
#   bash install.sh
# ─────────────────────────────────────────────────────────

set -euo pipefail

# ── Colours ──────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[dreaming]${NC} $*"; }
ok()    { echo -e "${GREEN}[dreaming]${NC} ✓ $*"; }
warn()  { echo -e "${YELLOW}[dreaming]${NC} ⚠ $*"; }
err()   { echo -e "${RED}[dreaming]${NC} ✗ $*"; }

# ── Resolve paths ────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT="${HERMES_AGENT_DIR:-$HERMES_HOME/hermes-agent}"
VENV_PYTHON="$HERMES_AGENT/venv/bin/python"
DREAMS_DIR="$HERMES_HOME/dreams"

# ── Pre-flight checks ────────────────────────────────────
info "Hermes Dreaming Plugin Installer v2.0"
info "HERMES_HOME = $HERMES_HOME"
info "HERMES_AGENT = $HERMES_AGENT"

if [ ! -f "$VENV_PYTHON" ]; then
  err "Hermes venv not found at $VENV_PYTHON"
  err "Set HERMES_AGENT_DIR env var if your installation is elsewhere."
  exit 1
fi

PYTHON="$VENV_PYTHON"

# ── Step 1: Dashboard plugin ─────────────────────────────
info "Step 1/7: Installing dashboard plugin..."

PLUGIN_DEST="$HERMES_AGENT/plugins/hermes-dreaming"
mkdir -p "$PLUGIN_DEST/dashboard/dist"

# Copy dashboard files
cp -r "$SCRIPT_DIR/dashboard/"* "$PLUGIN_DEST/dashboard/"

# Copy vector_store.py to memory plugin
VECTOR_DEST="$HERMES_AGENT/plugins/memory/holographic"
if [ -d "$VECTOR_DEST" ]; then
  cp "$SCRIPT_DIR/../references/vector_store_template.py" "$VECTOR_DEST/vector_store.py" 2>/dev/null || \
  cp "$SCRIPT_DIR/vector_store.py" "$VECTOR_DEST/vector_store.py" 2>/dev/null || \
  warn "vector_store.py not found in package — you may need to copy it manually"
  ok "Dashboard plugin installed at $PLUGIN_DEST"
else
  warn "Holographic memory plugin not found — vector_store.py link skipped"
fi

# ── Step 2: ChromaDB dependency ──────────────────────────
info "Step 2/7: Installing Python dependencies..."

"$PYTHON" -c "import chromadb" 2>/dev/null && {
  ok "ChromaDB already installed"
} || {
  info "Installing chromadb (this may take a minute)..."
  "$HERMES_AGENT/venv/bin/pip" install chromadb 2>&1 | tail -3
  ok "ChromaDB installed"
}

# ── Step 3: Create dreams directory ──────────────────────
info "Step 3/7: Setting up dreams directory..."

mkdir -p "$DREAMS_DIR"

if [ ! -f "$DREAMS_DIR/state.json" ]; then
  cat > "$DREAMS_DIR/state.json" << 'EOF'
{
  "last_dream_at": null,
  "dreams_today": 0,
  "last_dream_date": null,
  "total_dreams": 0
}
EOF
  ok "Created state.json"
else
  ok "state.json already exists"
fi

# ── Step 4: Vector store first index ────────────────────
info "Step 4/7: Running initial vector store indexing..."

VECTOR_SCRIPT="$HERMES_AGENT/plugins/memory/holographic/vector_store.py"
if [ -f "$VECTOR_SCRIPT" ]; then
  cd "$HERMES_AGENT/plugins/memory/holographic"
  HERMES_HOME="$HERMES_HOME" "$PYTHON" vector_store.py index 2>&1 | tail -3
  ok "Vector store indexed"
else
  warn "vector_store.py not found — skipping initial index"
fi

# ── Step 5: Create/update cron job ──────────────────────
info "Step 5/7: Setting up dreaming cron job (every 30 min)..."

# Remove old dreaming cron if exists
OLD_CRON=$(hermes cron list --json 2>/dev/null | "$PYTHON" -c "
import sys, json
jobs = json.load(sys.stdin)
for j in jobs:
    if j.get('name') == 'dreaming':
        print(j['job_id'])
" 2>/dev/null) || true

if [ -n "$OLD_CRON" ]; then
  hermes cron remove "$OLD_CRON" 2>/dev/null || true
  info "Removed old dreaming cron job"
fi

# Create new cron job with the full prompt
CROM_PROMPT=$(cat << 'DREAM_PROMPT'
You are Eliana's DREAMING system. This fires every 30 minutes, but you only dream when conditions are right.

## Gate Checks (all must pass)
1. **Idle threshold**: 30+ minutes since last user activity (check ~/.hermes/dreams/state.json for last_dream_at, and check recent session activity)
2. **Max dreams per day**: 2 (check dreams_today in state.json)
3. **Cooldown**: 8+ hours between dreams (check last_dream_at timestamp)
4. **Meaningful activity**: There should be new facts or conversations since the last dream

If any gate fails, do nothing and exit.

## Memory Architecture (TWO-TIER)

**Tier 1 — Holographic Store** (primary):
- SQLite fact store at ~/.hermes/memory_store.db
- Use `fact_store` tool (actions: add, search, probe, related, reason, contradict, update, remove, list)
- Use `fact_feedback` tool to rate facts (helpful/unhelpful)
- Structured facts with entity resolution, trust scoring

**Tier 2 — ChromaDB Vector Store** (overflow/semantic search):
- Persistent vector index at ~/.hermes/chroma_db/
- Script: python ~/.hermes/hermes-agent/plugins/memory/holographic/vector_store.py
- `python vector_store.py index` — re-index all facts
- `python vector_store.py search "query"` — semantic search
- `python vector_store.py stats` — show stats
- Unlimited capacity — use for deep recall, pattern finding

## Dream Procedure

### Phase 1: Gather Raw Material
1. `fact_store` (action=list, limit=50) — recent/high-trust facts
2. `session_search` — recent conversations
3. Read last dream journal: ls ~/.hermes/dreams/dream-*.md | tail -1
4. `python vector_store.py stats` — check vector health
5. Look for contradictions, stale facts, unresolved problems

### Phase 2: Deep Vector Search
Run semantic searches to find hidden connections:
- `python vector_store.py search "user preferences patterns"`
- `python vector_store.py search "problems challenges unresolved"`
- `python vector_store.py search "connections between topics"`

### Phase 3: Process
- **Consolidate**: Merge related facts, remove duplicates
- **Connect**: Find unexpected relationships via vector search
- **Rehearse**: Re-examine past problems with fresh eyes
- **Prune**: Remove low-trust, stale, contradicted facts
- **Synthesize**: Generate new insights, add new facts
- **Re-index**: Run `python vector_store.py index` after changes

### Phase 4: Evaluate — only wake user for genuine insights
- New connection between unrelated memories?
- Better solution to a known problem?
- Important contradiction found?
- Otherwise: stay silent, just journal

### Phase 5: Dream Journal
Write to ~/.hermes/dreams/dream-YYYY-MM-DD-HHMM.md with:
- What was processed, vector searches run
- Key connections, insights, actions taken
- Whether user was notified

### Phase 6: Update State
Update ~/.hermes/dreams/state.json with timestamps and counters.

## Constraints
- Keep dreams compact: 8-15 tool calls
- Always re-index after modifying facts
- Only surface truly valuable insights
- Don't re-dream the same material
DREAM_PROMPT
)

hermes cron add \
  --name "dreaming" \
  --schedule "every 30m" \
  --prompt "$CROM_PROMPT" \
  --deliver origin \
  2>&1 | head -5

ok "Dreaming cron job created (every 30 min)"

# ── Step 6: Update config.yaml ───────────────────────────
info "Step 6/7: Updating memory configuration..."

CONFIG_FILE="$HERMES_HOME/config.yaml"
if [ -f "$CONFIG_FILE" ]; then
  # Check current values
  CURRENT_MEM=$(grep "memory_char_limit:" "$CONFIG_FILE" | awk '{print $2}' || echo "2200")
  if [ "$CURRENT_MEM" -lt 8000 ] 2>/dev/null; then
    info "Increasing memory_char_limit: $CURRENT_MEM → 8000"
    sed -i 's/memory_char_limit: [0-9]*/memory_char_limit: 8000/' "$CONFIG_FILE"
    sed -i 's/user_char_limit: [0-9]*/user_char_limit: 4000/' "$CONFIG_FILE"
    ok "Config updated (restart gateway to take effect)"
  else
    ok "memory_char_limit already ≥ 8000"
  fi
else
  warn "config.yaml not found at $CONFIG_FILE — skipping config update"
fi

# ── Step 7: Summary ─────────────────────────────────────
info "Step 7/7: Installation complete!"
echo ""
echo -e "${GREEN}── Hermes Dreaming Plugin v2.0 installed ──${NC}"
echo ""
echo "  Dashboard:    /dreams tab in web dashboard (port 9119)"
echo "  Cron job:     every 30 min (max 2 dreams/day)"
echo "  Dreams dir:   $DREAMS_DIR"
echo "  Vector store: $HERMES_HOME/chroma_db/"
echo "  Memory:       8000 char limit (was 2200)"
echo ""
echo "  Re-index:     cd $HERMES_AGENT/plugins/memory/holographic"
echo "                HERMES_HOME=$HERMES_HOME $PYTHON vector_store.py index"
echo ""
echo "  Restart the gateway for config changes to take effect:"
echo "    systemctl --user restart hermes-gateway.service"
# Note: Cron prompt updated 2024-05-24 with proper idle detection using sessions.json updated_at
