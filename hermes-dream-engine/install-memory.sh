#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Dream Engine — Memory Setup
# ─────────────────────────────────────────────────────────
# Configures the holographic memory layer required by the
# dream engine. Run this BEFORE installing the dream engine.
#
# The dream engine needs:
#   1. Holographic memory provider (local SQLite fact store)
#   2. MEMORY.md and USER.md in ~/.hermes/memories/
#   3. Config.yaml with memory.provider = holographic
#   4. (Optional) ChromaDB vector overlay for semantic search
#
# Usage:
#   chmod +x install-memory.sh
#   ./install-memory.sh
# ─────────────────────────────────────────────────────────

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[dream-memory]${NC} $*"; }
ok()    { echo -e "${GREEN}[dream-memory]${NC} ✓ $*"; }
warn()  { echo -e "${YELLOW}[dream-memory]${NC} ⚠ $*"; }
err()   { echo -e "${RED}[dream-memory]${NC} ✗ $*"; }
step()  { echo -e "${BOLD}[dream-memory]${NC} Step $1: $2"; }

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT="${HERMES_AGENT_DIR:-$HOME/.hermes/hermes-agent}"
VENV_PYTHON="$HERMES_AGENT/venv/bin/python"
VENV_PIP="$HERMES_AGENT/venv/bin/pip"
CONFIG="$HERMES_HOME/config.yaml"

echo ""
echo -e "${BOLD}── Dream Engine Memory Setup v1.0 ──${NC}"
echo ""

# ── Pre-flight ──
if [ ! -f "$VENV_PYTHON" ]; then
  err "Hermes venv not found. Install Hermes Agent first."
  exit 1
fi

# ══════════════════════════════════════════════════════════
# STEP 1: Install holographic memory provider
# ══════════════════════════════════════════════════════════
step "1" "Installing holographic memory provider"

# The holographic memory store is part of hermes-agent's memory plugins
# Check if it's already available
"$VENV_PYTHON" -c "
import sys
sys.path.insert(0, '${HERMES_AGENT}')
try:
    from plugins.memory.holographic import store
    print('holographic: available')
except ImportError as e:
    print(f'holographic: missing ({e})')
" 2>/dev/null || true

# Ensure PyYAML is installed (needed by memory provider)
"$VENV_PYTHON" -c "import yaml" 2>/dev/null && {
  ok "PyYAML already installed"
} || {
  info "Installing PyYAML..."
  "$VENV_PIP" install pyyaml 2>&1 | tail -3
  ok "PyYAML installed"
}

# ══════════════════════════════════════════════════════════
# STEP 2: Create memory directories and files
# ══════════════════════════════════════════════════════════
step "2" "Setting up memory directory structure"

# Create memories directory
mkdir -p "$HERMES_HOME/memories"
ok "Created: ${HERMES_HOME}/memories/"

# Create dream engine data directories
mkdir -p "$HERMES_HOME/dream_engine"
mkdir -p "$HERMES_HOME/dream_engine/archive"
mkdir -p "$HERMES_HOME/dream_engine/context"
ok "Created: ${HERMES_HOME}/dream_engine/"

# Create MEMORY.md if it doesn't exist
if [ ! -f "$HERMES_HOME/memories/MEMORY.md" ]; then
  cat > "$HERMES_HOME/memories/MEMORY.md" << 'MEMEOF'
# Memory

This file stores durable facts about the agent's environment, preferences, and learned conventions.

## Format
- One fact per paragraph
- Separate facts with `§` on its own line
- Keep facts compact and focused

## Example
User prefers concise responses.
§
Project uses pytest with xdist for testing.
MEMEOF
  ok "Created: ${HERMES_HOME}/memories/MEMORY.md"
else
  ok "MEMORY.md already exists"
fi

# Create USER.md if it doesn't exist
if [ ! -f "$HERMES_HOME/memories/USER.md" ]; then
  cat > "$HERMES_HOME/memories/USER.md" << 'USEREOF'
# User Profile

This file stores information about the user.

## Format
- One fact per paragraph
- Separate facts with `§` on its own line

## Example
User's AI assistant is named Eliana.
§
Language: English.
USEREOF
  ok "Created: ${HERMES_HOME}/memories/USER.md"
else
  ok "USER.md already exists"
fi

# ══════════════════════════════════════════════════════════
# STEP 3: Initialize holographic fact store
# ══════════════════════════════════════════════════════════
step "3" "Initializing holographic fact store"

DB_PATH="$HERMES_HOME/memory_store.db"

info "Setting up holographic memory schema..."
"$VENV_PYTHON" << 'PYEOF'
import sqlite3
import sys
from pathlib import Path

# Try to import the authoritative schema from hermes-agent
db_path = Path.home() / ".hermes" / "memory_store.db"
db_path.parent.mkdir(parents=True, exist_ok=True)

# Check if DB exists and what schema version it has
needs_migration = False
needs_created = not db_path.exists()

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    columns = {row[1] for row in conn.execute("PRAGMA table_info(facts)").fetchall()}
    # Detect old schema: uses 'id' instead of 'fact_id'
    if 'id' in columns and 'fact_id' not in columns:
        info = "old"
        needs_migration = True
        print("Schema migration needed: old schema detected (id column)")
    elif 'fact_id' in columns:
        info = "current"
        print("Schema: already using current schema")
    else:
        info = "unknown"
        print("Schema: unknown variant, will apply authoritative schema")
    conn.close()
else:
    info = "creating"
    print("Creating fresh memory_store.db")

# Try to use authoritative store.py schema
try:
    store_path = Path.home() / ".hermes" / "hermes-agent" / "plugins" / "memory" / "holographic" / "store.py"
    if store_path.exists():
        # Import the schema constant
        sys.path.insert(0, str(store_path.parent.parent.parent.parent))
        from plugins.memory.holographic.store import _SCHEMA, MemoryStore
        print("Using authoritative schema from store.py")
        
        # Initialize via MemoryStore (handles WAL, schema creation, and migration)
        store = MemoryStore(db_path=str(db_path))
        store.close()
        print(f"Database initialized via MemoryStore: {db_path}")
    else:
        raise ImportError("store.py not found")
except ImportError:
    print("Falling back to inline schema creation")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    # Minimal inline schema (fallback when hermes-agent not available)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS facts (
            fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL UNIQUE,
            category TEXT DEFAULT 'general',
            tags TEXT DEFAULT '',
            trust_score REAL DEFAULT 0.5,
            retrieval_count INTEGER DEFAULT 0,
            helpful_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            hrr_vector BLOB,
            source_context TEXT DEFAULT 'realtime',
            verification_status TEXT DEFAULT 'verified'
        );

        CREATE TABLE IF NOT EXISTS entities (
            entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            entity_type TEXT DEFAULT 'unknown',
            aliases TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS fact_entities (
            fact_id INTEGER REFERENCES facts(fact_id),
            entity_id INTEGER REFERENCES entities(entity_id),
            PRIMARY KEY (fact_id, entity_id)
        );

        CREATE INDEX IF NOT EXISTS idx_facts_trust ON facts(trust_score DESC);
        CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);
        CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);

        CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts
            USING fts5(content, tags, content=facts, content_rowid=fact_id);

        CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
            INSERT INTO facts_fts(rowid, content, tags)
                VALUES (new.fact_id, new.content, new.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
            INSERT INTO facts_fts(facts_fts, rowid, content, tags)
                VALUES ('delete', old.fact_id, old.content, old.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
            INSERT INTO facts_fts(facts_fts, rowid, content, tags)
                VALUES ('delete', old.fact_id, old.content, old.tags);
            INSERT INTO facts_fts(rowid, content, tags)
                VALUES (new.fact_id, new.content, new.tags);
        END;

        CREATE TABLE IF NOT EXISTS memory_banks (
            bank_id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_name TEXT NOT NULL UNIQUE,
            vector BLOB NOT NULL,
            dim INTEGER NOT NULL,
            fact_count INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
    print(f"Database created with inline schema: {db_path}")
PYEOF

# ══════════════════════════════════════════════════════════
# STEP 4: Configure config.yaml
# ══════════════════════════════════════════════════════════
step "4" "Configuring config.yaml"

if [ ! -f "$CONFIG" ]; then
  warn "config.yaml not found — creating minimal config"
  cat > "$CONFIG" << 'CFGEOF'
_config_version: 23
agent:
  max_turns: 90
  verbose: false
memory:
  provider: holographic
  memory_enabled: true
  memory_char_limit: 8000
  user_char_limit: 4000
  user_profile_enabled: true
  flush_min_turns: 6
  nudge_interval: 10
plugins:
  enabled: []
  hermes-memory-store:
    auto_extract: true
    db_path: $HERMES_HOME/memory_store.db
    default_trust: 0.5
    hrr_dim: 1024
CFGEOF
  ok "Created minimal config.yaml"
else
  # Check if memory provider is set to holographic
  if grep -q "provider: holographic" "$CONFIG" 2>/dev/null; then
    ok "Memory provider already set to holographic"
  else
    warn "Memory provider not set to holographic"
    echo ""
    echo "  Add to ~/.hermes/config.yaml under 'memory:'"
    echo "    provider: holographic"
    echo "    memory_enabled: true"
    echo "    memory_char_limit: 8000"
    echo "    user_char_limit: 4000"
    echo ""
    echo "  And under 'plugins:' add:"
    echo "    hermes-memory-store:"
    echo "      auto_extract: true"
    echo "      db_path: \$HERMES_HOME/memory_store.db"
    echo "      default_trust: 0.5"
    echo "      hrr_dim: 1024"
    echo ""
  fi

  # Check if dream engine is in enabled plugins
  if grep -q "hermes-dream-engine" "$CONFIG" 2>/dev/null; then
    ok "Dream engine found in config.yaml"
  else
    warn "Dream engine not in plugins.enabled list"
    echo "  Add 'hermes-dream-engine' to plugins.enabled in config.yaml"
  fi
fi

# ══════════════════════════════════════════════════════════
# STEP 5: (Optional) ChromaDB vector overlay
# ══════════════════════════════════════════════════════════
step "5" "Checking ChromaDB vector overlay (optional)"

read -p "Install ChromaDB for semantic vector search? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
  "$VENV_PYTHON" -c "import chromadb" 2>/dev/null && {
    ok "ChromaDB already installed"
  } || {
    info "Installing ChromaDB..."
    "$VENV_PIP" install chromadb 2>&1 | tail -3
    ok "ChromaDB installed"
  }

  # Create ChromaDB directory
  mkdir -p "$HERMES_HOME/chroma_db"
  ok "ChromaDB data directory: ${HERMES_HOME}/chroma_db/"
else
  info "Skipping ChromaDB — the dream engine works without it"
  info "ChromaDB adds semantic similarity search on top of holographic FTS5"
fi

# ══════════════════════════════════════════════════════════
# STEP 6: Verify
# ══════════════════════════════════════════════════════════
step "6" "Verifying memory setup"

ERRORS=0

# Check DB exists and has correct schema
"$VENV_PYTHON" << 'VERIFYEOF'
import sqlite3
from pathlib import Path

db_path = Path.home() / ".hermes" / "memory_store.db"
if not db_path.exists():
    print("FAIL: memory_store.db does not exist")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = {row[0] for row in cursor.fetchall()}
required = {"facts", "facts_fts", "entities", "fact_entities", "memory_banks"}
missing = required - tables
if missing:
    print(f"FAIL: Missing tables: {missing}")
    exit(1)
print("OK: All required tables present")

# Check FTS
cursor.execute("SELECT count(*) FROM facts_fts")
fts_count = cursor.fetchone()[0]
print(f"OK: FTS index has {fts_count} entries")

# Check indexes
cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
indexes = [row[0] for row in cursor.fetchall()]
print(f"OK: Indexes: {', '.join(indexes)}")

# Check new columns (source_context, verification_status)
columns = {row[1] for row in cursor.execute("PRAGMA table_info(facts)").fetchall()}
required_cols = {"fact_id", "content", "source_context", "verification_status"}
missing_cols = required_cols - columns
if missing_cols:
    print(f"WARN: Missing trust-scoring columns: {missing_cols}")
    print("  These will be added on next access or run migration manually.")
else:
    print("OK: All trust-scoring columns present (source_context, verification_status)")

conn.close()
VERIFYEOF

# Check memory files
[ -f "$HERMES_HOME/memories/MEMORY.md" ] && ok "MEMORY.md exists" || { warn "MEMORY.md missing"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/memories/USER.md" ] && ok "USER.md exists" || { warn "USER.md missing"; ERRORS=$((ERRORS+1)); }
[ -d "$HERMES_HOME/dream_engine" ] && ok "dream_engine directory exists" || { warn "dream_engine directory missing"; ERRORS=$((ERRORS+1)); }

# ══════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════
echo ""
if [ $ERRORS -eq 0 ]; then
  echo -e "${GREEN}${BOLD}── Dream Engine Memory Setup complete ──${NC}"
else
  echo -e "${YELLOW}${BOLD}── Memory Setup complete with ${ERRORS} warning(s) ──${NC}"
fi
echo ""
echo "  Fact store:  ${HERMES_HOME}/memory_store.db"
echo "  Memories:    ${HERMES_HOME}/memories/"
echo "  Dream data:  ${HERMES_HOME}/dream_engine/"
echo "  Config:      ${CONFIG}"
echo ""
echo "  Next step: Install the dream engine plugin"
echo "    cd /path/to/hermes-dream-engine"
echo "    ./install.sh"
echo ""
