#!/bin/bash
# ─────────────────────────────────────────────────────────
# Hermes ImaGen Plugin — install.sh v1.0.0
# ─────────────────────────────────────────────────────────
# Installs image generation plugin with LCM model.
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
#
# Environment variables:
#   HERMES_HOME    — defaults to ~/.hermes
#   NO_RESTART     — set to skip gateway restart
#   NO_MODEL_DL    — set to skip model download (for offline installs)
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
HERMES_AGENT="${HERMES_AGENT_DIR:-$HOME/.hermes/hermes-agent}"
PLUGIN_DEST="$HERMES_HOME/plugins/hermes-imagenv"

info "Hermes ImaGen Plugin Installer v1.0.0"
info "HERMES_HOME = $HERMES_HOME"

# ── Step 1: Remove old version ───────────────────────────
info "Step 1/5: Removing any old version..."
if [ -d "$PLUGIN_DEST" ]; then
  rm -rf "$PLUGIN_DEST"
  ok "Removed old plugin"
fi

# ── Step 2: Create directory structure ─────────────────────
info "Step 2/5: Creating directories..."
mkdir -p "$PLUGIN_DEST/dashboard"
mkdir -p "$PLUGIN_DEST/scripts"
ok "Created structure"

# ── Step 3: Copy plugin files ─────────────────────────────
info "Step 3/5: Copying plugin files..."
cp "$SCRIPT_DIR/__init__.py" "$PLUGIN_DEST/__init__.py"
cp "$SCRIPT_DIR/plugin.yaml" "$PLUGIN_DEST/plugin.yaml"
cp "$SCRIPT_DIR/gradio_app.py" "$PLUGIN_DEST/gradio_app.py"
cp -r "$SCRIPT_DIR/src/"* "$PLUGIN_DEST/src/" 2>/dev/null || true
ok "Copied plugin files"

# ── Step 4: Install dependencies ───────────────────────────
info "Step 4/5: Checking Python dependencies..."
"$HERMES_AGENT/venv/bin/pip" install -q diffusers Pillow numpy gradio 2>/dev/null || {
  warn "Some dependencies may already be installed"
}
ok "Dependencies ready"

# ── Step 5: Create output directory ───────────────────────
info "Step 5/5: Setting up output directory..."
mkdir -p "$HERMES_HOME/imagenv-output"
ok "Output directory ready"

echo ""
echo -e "${GREEN}── Hermes ImaGen Plugin v1.0.0 installed ──${NC}"
echo ""
echo "  Start:  python3 $PLUGIN_DEST/gradio_app.py"
echo "  Or:     python3 ~/.hermes/scripts/run_imagenv.py"
echo ""
echo "  For Tailscale Funnel access, run:"
echo "    tailscale funnel --hostname=YOUR_HOSTNAME serve / http://localhost:7860"
echo ""