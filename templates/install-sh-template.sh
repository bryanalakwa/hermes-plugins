#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Plugin Installer Template
# ─────────────────────────────────────────────────────────
# A standardized install.sh for Hermes plugins that handles
# upgrades safely WITHOUT destroying user data.
#
# KEY PRINCIPLE: User data lives in $HERMES_HOME/ or $HERMES_AGENT/
# Plugin code lives in $PLUGIN_DEST/ — these are ALWAYS separate.
#
# During upgrades:
#   - User data files are NEVER deleted
#   - Existing config is preserved
#   - History/logs are preserved
#   - Only plugin code (this repo) is refreshed
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
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[plugin]${NC} $*"; }
ok()    { echo -e "${GREEN}[plugin]${NC} ✓ $*"; }
warn()  { echo -e "${YELLOW}[plugin]${NC} ⚠ $*"; }
err()   { echo -e "${RED}[plugin]${NC} ✗ $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT="${HERMES_AGENT_DIR:-$HOME/.hermes/hermes-agent}"
VENV_PYTHON="$HERMES_AGENT/venv/bin/python"
PLUGIN_NAME="your-plugin-name"  # ← CHANGE THIS
PLUGIN_DEST="$HERMES_HOME/plugins/$PLUGIN_NAME"

# ── Pre-flight checks ─────────────────────────────────────
if [ ! -f "$VENV_PYTHON" ]; then
  err "Hermes venv not found at $VENV_PYTHON"
  err "Set HERMES_AGENT_DIR env var if your installation is elsewhere."
  exit 1
fi

# ── USER DATA PRESERVATION ─────────────────────────────────
# List files that MUST survive an upgrade (in $HERMES_HOME/)
USER_DATA_FILES=(
  # "your_plugin/state.json"
  # "your_plugin/history.json"
  # "memories/MEMORY.md"
  # "memories/USER.md"
)

# Preserve user data by creating backup before any destructive ops
for data_file in "${USER_DATA_FILES[@]}"; do
  full_path="$HERMES_HOME/$data_file"
  if [ -f "$full_path" ]; then
    cp "$full_path" "${full_path}.upgrade_backup"
    info "Preserved user data: $full_path"
  fi
done

# ── Step 1: Remove old plugin code (NOT user data) ────────
info "Step 1/5: Removing old plugin files..."
if [ -d "$PLUGIN_DEST" ]; then
  # ONLY remove the plugin directory — user data is elsewhere
  rm -rf "$PLUGIN_DEST"
  ok "Removed old plugin at $PLUGIN_DEST"
else
  info "No previous installation found (fresh install)"
fi

# ── Step 2: Create directory structure ──────────────────────
info "Step 2/5: Creating plugin directory structure..."
mkdir -p "$PLUGIN_DEST/dashboard/dist"
mkdir -p "$PLUGIN_DEST/scripts"
mkdir -p "$PLUGIN_DEST/references"
ok "Directory structure created"

# ── Step 3: Copy plugin files ───────────────────────────────
info "Step 3/5: Copying plugin files..."

# Root-level files
for f in __init__.py plugin.yaml; do
  if [ -f "$SCRIPT_DIR/$f" ]; then
    cp "$SCRIPT_DIR/$f" "$PLUGIN_DEST/$f"
  fi
done

# Dashboard files (manifest + API backend + JS)
if [ -d "$SCRIPT_DIR/dashboard" ]; then
  cp -r "$SCRIPT_DIR/dashboard/"* "$PLUGIN_DEST/dashboard/" 2>/dev/null || true
fi

# Scripts
if [ -d "$SCRIPT_DIR/scripts" ]; then
  cp -r "$SCRIPT_DIR/scripts/"* "$PLUGIN_DEST/scripts/" 2>/dev/null || true
fi

# References
if [ -d "$SCRIPT_DIR/references" ]; then
  cp -r "$SCRIPT_DIR/references/"* "$PLUGIN_DEST/references/" 2>/dev/null || true
fi

ok "Plugin files copied"

# ── Step 4: Install dependencies ───────────────────────────
info "Step 4/5: Installing dependencies..."
# Example: PyYAML for config parsing
"$VENV_PYTHON" -c "import yaml" 2>/dev/null && {
  ok "PyYAML already installed"
} || {
  info "Installing PyYAML..."
  "$HERMES_AGENT/venv/bin/pip" install pyyaml 2>&1 | tail -3
  ok "PyYAML installed"
}

# ── Step 5: Restore user data ───────────────────────────────
info "Step 5/5: Restoring preserved user data..."
for data_file in "${USER_DATA_FILES[@]}"; do
  full_path="$HERMES_HOME/$data_file"
  backup_path="${full_path}.upgrade_backup"
  if [ -f "$backup_path" ]; then
    # Only restore if user data doesn't exist (truly fresh)
    if [ ! -f "$full_path" ]; then
      mv "$backup_path" "$full_path"
      ok "Restored user data: $full_path"
    else
      rm "$backup_path"
      ok "User data intact: $full_path"
    fi
  fi
done

# ── Restart gateway ───────────────────────────────────────
if [ "${NO_RESTART:-}" = "1" ]; then
  warn "Skipping gateway restart (NO_RESTART=1)"
else
  if systemctl --user is-active hermes-gateway.service &>/dev/null; then
    systemctl --user restart hermes-gateway.service 2>&1
    sleep 2
    if systemctl --user is-active hermes-gateway.service &>/dev/null; then
      ok "Gateway restarted successfully"
    else
      err "Gateway failed to restart — check logs:"
      err "  journalctl --user -u hermes-gateway.service --no-pager -n 20"
    fi
  fi
fi

# ── Summary ───────────────────────────────────────────────
echo ""
echo -e "${GREEN}── $PLUGIN_NAME installed successfully ──${NC}"
echo ""
echo "  Plugin code: $PLUGIN_DEST"
echo "  User data:   $HERMES_HOME/$PLUGIN_NAME/"
echo ""
echo "  Open dashboard at http://127.0.0.1:9119"
echo ""