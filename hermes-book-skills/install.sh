#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Hermes BookSkills Plugin — install.sh v1.0.0
# ─────────────────────────────────────────────────────────
# Installs / upgrades the BookSkills plugin for any Hermes agent.
#
# What it does:
#   1. Copies plugin files to ~/.hermes/plugins/hermes-book-skills/
#   2. Copies dashboard plugin (JS/CSS/manifest/plugin_api)
#   3. Installs Python dependencies (PyPDF2, EbookLib, beautifulsoup4)
#   4. Creates book-library directory
#   5. Creates skills/book-skills directory
#   6. Restarts gateway to pick up changes
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
#
# Environment variables:
#   HERMES_HOME       — defaults to ~/.hermes
#   HERMES_AGENT_DIR  — defaults to ~/.hermes/hermes-agent
#   NO_RESTART        — set to skip gateway restart
# ─────────────────────────────────────────────────────────

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[book-skills]${NC} $*" ; }
ok()    { echo -e "${GREEN}[book-skills]${NC} ✓ $*" ; }
warn()  { echo -e "${YELLOW}[book-skills]${NC} ⚠ $*" ; }
err()   { echo -e "${RED}[book-skills]${NC} ✗ $*" ; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT="${HERMES_AGENT_DIR:-$HOME/.hermes/hermes-agent}"
VENV_PYTHON="$HERMES_AGENT/venv/bin/python"
PLUGIN_DEST="$HERMES_HOME/plugins/hermes-book-skills"

info "Hermes BookSkills Plugin Installer v1.0.0"
info "HERMES_HOME = $HERMES_HOME"
info "HERMES_AGENT = $HERMES_AGENT"

# ── Pre-flight checks ─────────────────────────────────────
if [ ! -f "$VENV_PYTHON" ]; then
  err "Hermes venv not found at $VENV_PYTHON"
  err "Set HERMES_AGENT_DIR env var if your installation is elsewhere."
  exit 1
fi

# ── Step 1: Remove old version (fresh install) ───────────
info "Step 1/6: Removing old version if present..."
if [ -d "$PLUGIN_DEST" ]; then
  rm -rf "$PLUGIN_DEST"
  ok "Removed old plugin at $PLUGIN_DEST"
fi

# ── Step 2: Create directory structure ────────────────────
info "Step 2/6: Creating plugin directory structure..."
mkdir -p "$PLUGIN_DEST/dashboard/dist"
mkdir -p "$PLUGIN_DEST/scripts"
mkdir -p "$PLUGIN_DEST/references"
ok "Directory structure created"

# ── Step 3: Copy all plugin files ───────────────────────
info "Step 3/6: Copying plugin files..."

# Core plugin files
cp "$SCRIPT_DIR/__init__.py" "$PLUGIN_DEST/__init__.py"
cp "$SCRIPT_DIR/plugin.yaml" "$PLUGIN_DEST/plugin.yaml"
ok "Copied plugin metadata (__init__.py, plugin.yaml)"

# Dashboard plugin
cp "$SCRIPT_DIR/dashboard/manifest.json" "$PLUGIN_DEST/dashboard/manifest.json"
cp "$SCRIPT_DIR/dashboard/plugin_api.py" "$PLUGIN_DEST/dashboard/plugin_api.py"
cp "$SCRIPT_DIR/dashboard/dist/index.js" "$PLUGIN_DEST/dashboard/dist/index.js"
cp "$SCRIPT_DIR/dashboard/dist/style.css" "$PLUGIN_DEST/dashboard/dist/style.css"
ok "Copied dashboard plugin (manifest, API, JS, CSS)"

# Create book library directory
mkdir -p "$HERMES_HOME/book-library"
ok "Created book-library directory"

# ── Step 4: Python dependencies ───────────────────────────
info "Step 4/6: Checking Python dependencies..."
for dep in PyPDF2 EbookLib beautifulsoup4 pyyaml; do
  if "$HERMES_AGENT/venv/bin/pip" show "$dep" &>/dev/null; then
    ok "$dep already installed"
  else
    info "Installing $dep..."
    "$HERMES_AGENT/venv/bin/pip" install "$dep" 2>&1 | tail -2
    ok "$dep installed"
  fi
done

# ── Step 5: Create skills directory ───────────────────────
info "Step 5/6: Setting up skills directory..."
mkdir -p "$HERMES_HOME/skills/book-skills"
ok "Created skills/book-skills directory"

# ── Step 6: Restart gateway ───────────────────────────────
info "Step 6/6: Restarting gateway to pick up changes..."
if [ "${NO_RESTART:-}" = "1" ]; then
  warn "Skipping gateway restart (NO_RESTART=1)"
else
  if systemctl --user is-active hermes-gateway.service &>/dev/null; then
    systemctl --user restart hermes-gateway.service 2>&1
    sleep 2
    ok "Gateway restarted successfully"
  elif command -v hermes &>/dev/null 2>&1; then
    warn "Gateway running outside systemd — restart it manually:"
    warn "  hermes gateway restart"
  else
    warn "Gateway not detected — start it when ready:"
    warn "  systemctl --user start hermes-gateway.service"
  fi
fi

# ── Summary ───────────────────────────────────────────────
echo ""
echo -e "${GREEN}── Hermes BookSkills Plugin v1.0.0 installed ──${NC}"
echo ""
echo "  Dashboard:  /books tab in web dashboard (port 9119)"
echo "  Plugin:     $PLUGIN_DEST"
echo "  Library:    $HERMES_HOME/book-library"
echo "  Skills:     $HERMES_HOME/skills/book-skills"
echo ""
echo "  Upload books via the /books tab."
echo ""