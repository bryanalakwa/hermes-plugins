#!/bin/bash
# ─────────────────────────────────────────────────────────
# Hermes ImaGen Plugin — install.sh v1.0.0
# ─────────────────────────────────────────────────────────
# Installs image generation wrapper. Uses existing ComfyUI
# installation or diffusers directly.
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
info "Step 1/4: Removing any old version..."
if [ -d "$PLUGIN_DEST" ]; then
  rm -rf "$PLUGIN_DEST"
  ok "Removed old plugin"
fi

# ── Step 2: Create directories ───────────────────────────
info "Step 2/4: Creating directories..."
mkdir -p "$PLUGIN_DEST/scripts"
mkdir -p "$PLUGIN_DEST/dashboard"
mkdir -p "$HERMES_HOME/imagenv-output"
ok "Directories created"

# ── Step 3: Copy plugin files ─────────────────────────────
info "Step 3/4: Copying plugin files..."
cp "$SCRIPT_DIR/__init__.py" "$PLUGIN_DEST/__init__.py"
cp "$SCRIPT_DIR/plugin.yaml" "$PLUGIN_DEST/plugin.yaml"
cp "$SCRIPT_DIR/README.md" "$PLUGIN_DEST/README.md"
ok "Files copied"

# ── Step 4: Verify dependencies ─────────────────────────
info "Step 4/4: Verifying dependencies..."
python3 -c "import diffusers, PIL, numpy" 2>/dev/null && ok "Dependencies ready" || {
  warn "Install dependencies: pip3 install diffusers Pillow numpy gradio"
}

echo ""
echo -e "${GREEN}── Hermes ImaGen Plugin v1.0.0 installed ──${NC}"
echo ""
echo "  Generate: python3 ~/.hermes/scripts/generate_image.py \"prompt\""
echo "  Or use:   python3 ~/.hermes/scripts/imagenv.py \"prompt\""
echo ""
echo "  Output: ~/.hermes/imagenv-output/"
echo ""