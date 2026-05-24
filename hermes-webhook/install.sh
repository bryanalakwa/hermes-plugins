#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Hermes Inter-Agent Webhook Plugin — install.sh
# ─────────────────────────────────────────────────────────
# Installs the webhook plugin for any Hermes agent:
#   1. Copies dashboard plugin to hermes-agent/plugins/
#   2. Copies send scripts and protocol reference
#   3. Installs Python dependency (PyYAML)
#   4. Creates webhookHistory.json for message logging
#   5. Verifies webhook platform is enabled in config
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
NC='\033[0m'

info()  { echo -e "${CYAN}[webhook]${NC} $*"; }
ok()    { echo -e "${GREEN}[webhook]${NC} ✓ $*"; }
warn()  { echo -e "${YELLOW}[webhook]${NC} ⚠ $*"; }
err()   { echo -e "${RED}[webhook]${NC} ✗ $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT="${HERMES_AGENT_DIR:-$HOME/.hermes/hermes-agent}"
VENV_PYTHON="$HERMES_AGENT/venv/bin/python"
CONFIG="$HERMES_HOME/config.yaml"

info "Hermes Inter-Agent Webhook Plugin Installer v2.0"
info "HERMES_HOME = $HERMES_HOME"
info "HERMES_AGENT = $HERMES_AGENT"

if [ ! -f "$VENV_PYTHON" ]; then
  err "Hermes venv not found at $VENV_PYTHON"
  err "Set HERMES_AGENT_DIR env var if your installation is elsewhere."
  exit 1
fi

PYTHON="$VENV_PYTHON"

# ── Step 1: Dashboard plugin ─────────────────────────────
info "Step 1/5: Installing dashboard plugin..."
PLUGIN_DEST="$HERMES_AGENT/plugins/hermes-webhook"
mkdir -p "$PLUGIN_DEST/dashboard/dist" "$PLUGIN_DEST/scripts" "$PLUGIN_DEST/references"
cp -r "$SCRIPT_DIR/dashboard/"* "$PLUGIN_DEST/dashboard/"
cp -r "$SCRIPT_DIR/scripts/"* "$PLUGIN_DEST/scripts/"
cp -r "$SCRIPT_DIR/references/"* "$PLUGIN_DEST/references/"
ok "Dashboard plugin installed at $PLUGIN_DEST"

# ── Step 2: PyYAML dependency ─────────────────────────────
info "Step 2/5: Checking Python dependencies..."
"$PYTHON" -c "import yaml" 2>/dev/null && {
  ok "PyYAML already installed"
} || {
  info "Installing PyYAML..."
  "$HERMES_AGENT/venv/bin/pip" install pyyaml 2>&1 | tail -3
  ok "PyYAML installed"
}

# ── Step 3: Create history file ──────────────────────────
info "Step 3/5: Setting up message history..."
HISTORY_FILE="$HERMES_HOME/webhookHistory.json"
if [ ! -f "$HISTORY_FILE" ]; then
  echo "[]" > "$HISTORY_FILE"
  ok "Created webhookHistory.json"
else
  ok "webhookHistory.json already exists"
fi

# ── Step 4: Verify webhook platform ─────────────────────
info "Step 4/5: Verifying webhook platform configuration..."
if [ -f "$CONFIG" ]; then
  WEBHOOK_ENABLED=$(grep -A5 "^  webhook:" "$CONFIG" 2>/dev/null | grep "enabled:" | head -1 | awk '{print $2}' || echo "false")
  if [ "$WEBHOOK_ENABLED" = "true" ]; then
    ok "Webhook platform is enabled in config.yaml"
  else
    warn "Webhook platform may not be enabled in config.yaml"
    warn "Add the following to ~/.hermes/config.yaml if not present:"
    warn ""
    warn "platforms:"
    warn "  webhook:"
    warn "    enabled: true"
    warn "    extra:"
    warn '      host: "0.0.0.0"'
    warn "      port: 8644"
    warn "      routes:"
    warn "        agent-ping:"
    warn '          secret: "<your-secret>"'
    warn '          prompt: "Message from another agent: {message}\nSender: {sender}\nRespond appropriately."'
    warn '          deliver: "telegram"'
    warn "        agent-notify:"
    warn '          secret: "<your-secret>"'
    warn "          deliver_only: true"
    warn '          deliver: "telegram"'
    warn '          prompt: "📨 Agent notification: {message}"'
  fi
else
  warn "config.yaml not found — skipping webhook platform check"
fi

# ── Step 5: Summary ─────────────────────────────────────
info "Step 5/5: Installation complete!"
echo ""
echo -e "${GREEN}── Hermes Inter-Agent Webhook Plugin v2.0 installed ──${NC}"
echo ""
echo "  Dashboard:  /agents tab in web dashboard (port 9119)"
echo "  Scripts:    $PLUGIN_DEST/scripts/"
echo "  History:    $HISTORY_FILE"
echo ""
echo "  Add agents from the dashboard, or via CLI:"
echo "    bash $PLUGIN_DEST/scripts/setup.sh"
echo ""
echo "  Send messages from CLI:"
echo "    bash $PLUGIN_DEST/scripts/send.sh ping \"Hello!\""
echo "    bash $PLUGIN_DEST/scripts/send.sh notify \"Alert!\""
echo ""
echo "  Restart the gateway for dashboard changes:"
echo "    systemctl --user restart hermes-gateway.service"
