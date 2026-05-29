#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Dream Engine v1.0.0 — install.sh
# ─────────────────────────────────────────────────────────
# Installs the hermes-dream-engine plugin for Hermes Agent.
# This script:
#   1. Runs memory setup (holographic fact store + directories)
#   2. Copies plugin files to ~/.hermes/plugins/
#   3. Installs Python dependencies (bcrypt, PyYAML)
#   4. Sets up dashboard password gate (optional)
#   5. Configures plugin in config.yaml
#   6. Verifies installation
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
# ─────────────────────────────────────────────────────────

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[dream-engine]${NC} $*"; }
ok()    { echo -e "${GREEN}[dream-engine]${NC} ✓ $*"; }
warn()  { echo -e "${YELLOW}[dream-engine]${NC} ⚠ $*"; }
err()   { echo -e "${RED}[dream-engine]${NC} ✗ $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT="${HERMES_AGENT_DIR:-$HOME/.hermes/hermes-agent}"
VENV_PYTHON="$HERMES_AGENT/venv/bin/python"
VENV_PIP="$HERMES_AGENT/venv/bin/pip"
CONFIG="$HERMES_HOME/config.yaml"

echo ""
echo -e "${BOLD}── Dream Engine Installer v1.0.0 ──${NC}"
echo ""

if [ ! -f "$VENV_PYTHON" ]; then
  err "Hermes venv not found at ${VENV_PYTHON}"
  err "Install Hermes Agent first: https://hermes-agent.nousresearch.com/docs"
  exit 1
fi

# ══════════════════════════════════════════════════════════
# PHASE 1: Memory Setup
# ══════════════════════════════════════════════════════════
echo -e "${BOLD}━━ Phase 1: Memory Setup ━━${NC}"
echo ""

if [ -f "$SCRIPT_DIR/install-memory.sh" ]; then
  # Run the memory setup script
  bash "$SCRIPT_DIR/install-memory.sh"
else
  warn "install-memory.sh not found — running inline memory setup"

  # Inline fallback: create minimal structure
  mkdir -p "$HERMES_HOME/memories"
  mkdir -p "$HERMES_HOME/dream_engine/archive"
  mkdir -p "$HERMES_HOME/dream_engine/context"

  if [ ! -f "$HERMES_HOME/memories/MEMORY.md" ]; then
    echo "# Memory" > "$HERMES_HOME/memories/MEMORY.md"
    ok "Created MEMORY.md"
  fi
  if [ ! -f "$HERMES_HOME/memories/USER.md" ]; then
    echo "# User Profile" > "$HERMES_HOME/memories/USER.md"
    ok "Created USER.md"
  fi

  # Create holographic DB if needed
  if [ ! -f "$HERMES_HOME/memory_store.db" ]; then
    "$VENV_PYTHON" -c "
import sqlite3
from pathlib import Path
db = Path.home() / '.hermes' / 'memory_store.db'
conn = sqlite3.connect(str(db))
conn.execute('PRAGMA journal_mode=WAL')
conn.execute('''CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY, content TEXT UNIQUE, category TEXT DEFAULT 'general',
    tags TEXT DEFAULT '', trust_score REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
conn.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(content, tags, content=facts, content_rowid=id)''')
conn.commit(); conn.close()
"
    ok "Created holographic fact store"
  fi
fi

echo ""

# ══════════════════════════════════════════════════════════
# PHASE 2: Plugin Installation
# ══════════════════════════════════════════════════════════
echo -e "${BOLD}━━ Phase 2: Plugin Installation ━━${NC}"
echo ""

PLUGIN_DEST="$HERMES_HOME/plugins/hermes-dream-engine"

# Create directory structure
mkdir -p "$PLUGIN_DEST/dashboard/dist"
mkdir -p "$PLUGIN_DEST/references"

# Copy all plugin files
info "Copying plugin files..."

# Root-level Python files
for f in __init__.py daemon.py plugin.yaml; do
  if [ -f "$SCRIPT_DIR/$f" ]; then
    cp "$SCRIPT_DIR/$f" "$PLUGIN_DEST/$f"
  fi
done

# Dashboard API handler
if [ -f "$SCRIPT_DIR/plugin_api.py" ]; then
  cp "$SCRIPT_DIR/plugin_api.py" "$PLUGIN_DEST/plugin_api.py"
fi

# Dashboard files
if [ -d "$SCRIPT_DIR/dashboard" ]; then
  cp -r "$SCRIPT_DIR/dashboard/"* "$PLUGIN_DEST/dashboard/" 2>/dev/null || true
fi

# References
if [ -d "$SCRIPT_DIR/references" ]; then
  cp -r "$SCRIPT_DIR/references/"* "$PLUGIN_DEST/references/" 2>/dev/null || true
fi

ok "Plugin files installed at ${PLUGIN_DEST}"

# ══════════════════════════════════════════════════════════
# PHASE 3: Dependencies
# ══════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}━━ Phase 3: Dependencies ━━${NC}"
echo ""

"$VENV_PYTHON" -c "import yaml" 2>/dev/null && {
  ok "PyYAML already installed"
} || {
  info "Installing PyYAML..."
  "$VENV_PIP" install pyyaml 2>&1 | tail -3
  ok "PyYAML installed"
}

# Install bcrypt for dashboard password gate
if ! "$VENV_PYTHON" -c "import bcrypt" 2>/dev/null; then
  info "Installing bcrypt for password gate..."
  "$VENV_PIP" install --quiet bcrypt
  ok "bcrypt installed"
fi

# ══════════════════════════════════════════════════════════
# PHASE 4: Dashboard Password Gate
# ══════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}━━ Phase 4: Dashboard Password Gate ━━${NC}"
echo ""

DASHBOARD_AUTH="$HERMES_HOME/dashboard.auth"

if [ ! -f "$DASHBOARD_AUTH" ]; then
  echo ""
  echo "The dashboard password gate protects your agent's web UI."
  read -rsp "Set a dashboard password (press Enter to skip): " PASSWORD
  echo ""
  if [ -n "$PASSWORD" ]; then
    HASH=$("$VENV_PYTHON" -c "
import bcrypt
password = '''$PASSWORD'''
hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
print(hash)
")
    echo "$HASH" > "$DASHBOARD_AUTH"
    ok "Dashboard password set"
  else
    ok "No password set - dashboard accessible without authentication"
  fi
else
  ok "Dashboard password already configured"
fi

# ══════════════════════════════════════════════════════════
# PHASE 5: Configuration
# ══════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}━━ Phase 5: Configuration ━━${NC}"
echo ""

if [ -f "$CONFIG" ]; then
  # Check if dream engine is in enabled plugins
  if grep -q "hermes-dream-engine" "$CONFIG" 2>/dev/null; then
    ok "Dream engine already in plugins.enabled"
  else
    warn "Adding hermes-dream-engine to plugins.enabled"
    # Add to enabled list (idempotent)
    if grep -q "^  enabled:" "$CONFIG" 2>/dev/null; then
      # Has enabled section — append if not present
      if ! grep -A 20 "enabled:" "$CONFIG" | grep -q "hermes-dream-engine"; then
        sed -i '/^  enabled:/a \  - hermes-dream-engine' "$CONFIG" 2>/dev/null || true
      fi
    else
      # No enabled section — add one
      if grep -q "^plugins:" "$CONFIG" 2>/dev/null; then
        sed -i '/^plugins:/a \  enabled:\n  - hermes-dream-engine' "$CONFIG" 2>/dev/null || true
      fi
    fi
    ok "Added to plugins.enabled"
  fi

  # Check memory provider
  if grep -q "provider: holographic" "$CONFIG" 2>/dev/null; then
    ok "Memory provider is holographic"
  else
    warn "Memory provider should be 'hierarchical' for dream engine"
    echo "  Add to config.yaml: memory.provider: holographic"
  fi
else
  warn "config.yaml not found — manual configuration required"
fi

# ══════════════════════════════════════════════════════════
# PHASE 6: Verification
# ══════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}━━ Phase 6: Verification ━━${NC}"
echo ""

ERRORS=0

# Python imports
"$VENV_PYTHON" -c "
import sys
sys.path.insert(0, '${PLUGIN_DEST}')
from daemon import DreamDaemon
from dream_engine import DreamEngine
from dream_state import DreamState, DEFAULT_CONFIG
from state_machine import DreamStateMachine
from activity_monitor import ActivityMonitor
print('All imports OK')
" 2>/dev/null && {
  ok "Python imports verified"
} || {
  err "Python import verification failed"
  ERRORS=$((ERRORS + 1))
}

# Dashboard files
[ -f "$PLUGIN_DEST/dashboard/dist/index.js" ] && {
  node -c "$PLUGIN_DEST/dashboard/dist/index.js" 2>/dev/null && {
    ok "Dashboard JS syntax valid"
  } || {
    warn "Dashboard JS has syntax errors"
    ERRORS=$((ERRORS + 1))
  }
} || {
  warn "Dashboard JS not found"
  ERRORS=$((ERRORS + 1))
}

[ -f "$PLUGIN_DEST/dashboard/manifest.json" ] && {
  python3 -c "import json; json.load(open('${PLUGIN_DEST}/dashboard/manifest.json'))" 2>/dev/null && {
    ok "Dashboard manifest valid"
  } || {
    warn "Dashboard manifest invalid"
    ERRORS=$((ERRORS + 1))
  }
} || warn "Dashboard manifest not found"

[ -f "$PLUGIN_DEST/dashboard/plugin_api.py" ] && {
  ok "Dashboard plugin_api.py present"
} || {
  warn "Dashboard plugin_api.py missing — API routes won't mount"
  ERRORS=$((ERRORS + 1))
}

# Memory setup
[ -f "$HERMES_HOME/memory_store.db" ] && ok "Holographic DB exists" || { warn "Holographic DB missing"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/memories/MEMORY.md" ] && ok "MEMORY.md exists" || { warn "MEMORY.md missing"; ERRORS=$((ERRORS+1)); }
[ -f "$HERMES_HOME/memories/USER.md" ] && ok "USER.md exists" || { warn "USER.md missing"; ERRORS=$((ERRORS+1)); }
[ -d "$HERMES_HOME/dream_engine" ] && ok "Dream engine data directory exists" || { warn "Dream engine directory missing"; ERRORS=$((ERRORS+1)); }

# ── Summary ───────────────────────────────────────────────
echo ""
if [ $ERRORS -eq 0 ]; then
  echo -e "${GREEN}${BOLD}── Dream Engine v1.0.0 installed successfully ──${NC}"
else
  echo -e "${YELLOW}${BOLD}── Dream Engine v1.0.0 installed with ${ERRORS} warning(s) ──${NC}"
fi
echo ""
echo "  Plugin:      ${PLUGIN_DEST}"
echo "  Data:        ${HERMES_HOME}/dream_engine/"
echo "  Fact store:  ${HERMES_HOME}/memory_store.db"
echo "  Memories:    ${HERMES_HOME}/memories/"
echo "  Dashboard:   /dream-engine tab in web dashboard (port 9119)"
echo ""
echo "  Restart the gateway for changes to take effect:"
echo "    systemctl --user restart hermes-gateway.service"
echo ""
echo "  After restart, verify the API is mounted:"
echo "    curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9119/api/plugins/hermes-dream-engine/status"
echo "    # Expected: 401 (mounted, needs auth)"
echo ""
