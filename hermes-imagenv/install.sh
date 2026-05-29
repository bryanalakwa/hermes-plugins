#!/bin/bash
# ─────────────────────────────────────────────────────────
# Hermes ImaGen Plugin — install.sh v1.0.0
# ─────────────────────────────────────────────────────────
# Installs image generation wrapper. Uses existing ComfyUI
# installation or diffusers directly.
#
# What it does:
#   1. Removes old plugin (if present)
#   2. Creates directories (plugin + output)
#   3. Copies plugin files
#   4. Installs Python dependencies (diffusers, Pillow, numpy, bcrypt)
#   5. Sets up dashboard password gate (optional)
#
# ─────────────────────────────────────────────────────────

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[imagenv]${NC} $*"; }
ok()    { echo -e "${GREEN}[imagenv]${NC} ✓ $*"; }
warn()  { echo -e "${YELLOW}[imagenv]${NC} ⚠ $*"; }
err()   { echo -e "${RED}[imagenv]${NC} ✗ $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PLUGIN_DEST="$HERMES_HOME/plugins/hermes-imagenv"

info "Hermes ImaGen Plugin Installer v1.0.0"
info "HERMES_HOME = $HERMES_HOME"

# ── Step 1: Remove old version ───────────────────────────
info "Step 1/5: Removing any old version..."
if [ -d "$PLUGIN_DEST" ]; then
  rm -rf "$PLUGIN_DEST"
  ok "Removed old plugin"
fi

# ── Step 2: Create directories ───────────────────────────
info "Step 2/5: Creating directories..."
mkdir -p "$PLUGIN_DEST/scripts"
mkdir -p "$PLUGIN_DEST/dashboard"
mkdir -p "$HERMES_HOME/imagenv-output"
ok "Directories created"

# ── Step 3: Copy plugin files ─────────────────────────────
info "Step 3/5: Copying plugin files..."
cp "$SCRIPT_DIR/__init__.py" "$PLUGIN_DEST/__init__.py"
cp "$SCRIPT_DIR/plugin.yaml" "$PLUGIN_DEST/plugin.yaml"
cp "$SCRIPT_DIR/README.md" "$PLUGIN_DEST/README.md"
ok "Files copied"

# ── Step 4: Verify dependencies ─────────────────────────
info "Step 4/5: Verifying dependencies..."

# Check venv exists
VENV_PYTHON="$HERMES_HOME/hermes-agent/venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
  err "Hermes venv not found at $VENV_PYTHON"
  err "Set HERMES_AGENT_DIR env var if your installation is elsewhere."
  exit 1
fi

# Install diffusers dependencies if missing
"$VENV_PYTHON" -c "import diffusers" 2>/dev/null || {
  info "Installing diffusers, Pillow, numpy..."
  "$HERMES_HOME/hermes-agent/venv/bin/pip" install --quiet diffusers Pillow numpy
  ok "Image generation dependencies installed"
}

# bcrypt for dashboard password gate
"$VENV_PYTHON" -c "import bcrypt" 2>/dev/null || {
  info "Installing bcrypt for password gate..."
  "$HERMES_HOME/hermes-agent/venv/bin/pip" install --quiet bcrypt
  ok "bcrypt installed"
}

ok "Dependencies ready"

# ── Step 5: Dashboard password gate setup ───────────────
info "Step 5/5: Dashboard password gate setup..."
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

echo ""
echo -e "${GREEN}── Hermes ImaGen Plugin v1.0.0 installed ──${NC}"
echo ""
echo "  Generate: python3 ~/.hermes/scripts/generate_image.py \"prompt\""
echo "  Or use:   python3 ~/.hermes/scripts/imagenv.py \"prompt\""
echo ""
echo "  Output: ~/.hermes/imagenv-output/"
echo ""