#!/bin/bash
# ─────────────────────────────────────────────────────────
# Hermes Inter-Agent Webhook Plugin — install.sh v1.0.0
# ─────────────────────────────────────────────────────────
# Installs / upgrades the webhook plugin for any Hermes agent.
#
# What it does:
#   1. Copies plugin files to ~/.hermes/plugins/hermes-webhook/
#   2. Copies dashboard plugin (JS/CSS/manifest/plugin_api)
#   3. Copies send scripts, setup script, and protocol reference
#   4. Copies __init__.py and plugin.yaml (version + metadata)
#   5. Installs Python dependency (PyYAML)
#   6. Creates webhookHistory.json for message logging (preserves existing)
#   7. Sets up dashboard password gate (optional, skips if exists)
#   8. Enables webhook platform in config if not already enabled
#   9. Restarts gateway and dashboard to pick up changes
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

info()  { echo -e "${CYAN}[webhook]${NC} $*"; }
ok()    { echo -e "${GREEN}[webhook]${NC} ✓ $*"; }
warn()  { echo -e "${YELLOW}[webhook]${NC} ⚠ $*"; }
err()   { echo -e "${RED}[webhook]${NC} ✗ $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT="${HERMES_AGENT_DIR:-$HOME/.hermes/hermes-agent}"
VENV_PYTHON="$HERMES_AGENT/venv/bin/python"
CONFIG="$HERMES_HOME/config.yaml"
PLUGIN_DEST="$HERMES_HOME/plugins/hermes-webhook"

info "Hermes Inter-Agent Webhook Plugin Installer v1.0.0"
info "HERMES_HOME = $HERMES_HOME"

# ── Pre-flight checks ─────────────────────────────────────
if [ ! -f "$VENV_PYTHON" ]; then
  err "Hermes venv not found at $VENV_PYTHON"
  err "Set HERMES_AGENT_DIR env var if your installation is elsewhere."
  exit 1
fi

PYTHON="$VENV_PYTHON"

# ── Step 1: Plugin destination ready ─────────────────────────────
# Note: We do NOT rm -rf here because this script runs from within the plugin directory
# Files are copied in-place which updates existing installations safely
info "Step 1/9: Preparing plugin directory..."
mkdir -p "$PLUGIN_DEST"

# ── Step 2: Create directory structure ───────────────────────
info "Step 2/9: Creating plugin directory structure..."
mkdir -p "$PLUGIN_DEST/scripts"
mkdir -p "$PLUGIN_DEST/references"
ok "Directory structure created"

# ── Step 3: Copy plugin files ────────────────────────────────
info "Step 3/9: Copying plugin files..."

# Core plugin files (version, metadata)
cp "$SCRIPT_DIR/__init__.py" "$PLUGIN_DEST/__init__.py"
cp "$SCRIPT_DIR/plugin.yaml" "$PLUGIN_DEST/plugin.yaml"
ok "Copied plugin metadata (__init__.py, plugin.yaml)"

# Dashboard plugin (manifest, API backend, JS UI, CSS)
cp "$SCRIPT_DIR/dashboard/manifest.json" "$PLUGIN_DEST/dashboard/manifest.json"
cp "$SCRIPT_DIR/dashboard/plugin_api.py" "$PLUGIN_DEST/dashboard/plugin_api.py"
cp "$SCRIPT_DIR/dashboard/dist/index.js" "$PLUGIN_DEST/dashboard/dist/index.js"
cp "$SCRIPT_DIR/dashboard/dist/style.css" "$PLUGIN_DEST/dashboard/dist/style.css"
ok "Copied dashboard plugin (manifest, API, JS, CSS)"

# Scripts (send, setup)
cp -r "$SCRIPT_DIR/scripts/"* "$PLUGIN_DEST/scripts/"
ok "Copied scripts (send_webhook.py, send.sh, setup.sh)"

# References
cp -r "$SCRIPT_DIR/references/"* "$PLUGIN_DEST/references/"
ok "Copied references (protocol.md)"

# ── Step 4: Install dependencies ────────────────────────────
info "Step 4/9: Checking Python dependencies..."

# PyYAML
if "$PYTHON" -c "import yaml" 2>/dev/null; then
  ok "PyYAML already installed"
else
  info "Installing PyYAML..."
  "$HERMES_AGENT/venv/bin/pip" install --quiet pyyaml
  ok "PyYAML installed"
fi

# bcrypt for dashboard password gate
if ! "$PYTHON" -c "import bcrypt" 2>/dev/null; then
  info "Installing bcrypt for password gate..."
  "$HERMES_AGENT/venv/bin/pip" install --quiet bcrypt
  ok "bcrypt installed"
fi

# ── Step 5: Create history file ──────────────────────────────
info "Step 5/9: Setting up message history..."
HISTORY_FILE="$HERMES_HOME/webhookHistory.json"
if [ ! -f "$HISTORY_FILE" ]; then
  echo "[]" > "$HISTORY_FILE"
  ok "Created webhookHistory.json"
else
  ok "webhookHistory.json already exists"
fi

# ── Step 6: Dashboard password gate setup ────────────────────
info "Step 6/9: Dashboard password gate setup..."
DASHBOARD_AUTH="$HERMES_HOME/dashboard.auth"

if [ ! -f "$DASHBOARD_AUTH" ]; then
  echo ""
  echo "The dashboard password gate protects your agent's web UI."
  read -rsp "Set a dashboard password (press Enter to skip): " PASSWORD
  echo ""
  if [ -n "$PASSWORD" ]; then
    # Create bcrypt hash
    HASH=$(python3 -c "
import bcrypt
import sys
password = sys.argv[1]
hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
print(hash)
" "$PASSWORD")
    echo "$HASH" > "$DASHBOARD_AUTH"
    ok "Dashboard password set"
  else
    ok "No password set - dashboard accessible without authentication"
  fi
else
  ok "Dashboard password already configured"
fi

# ── Step 7: Enable webhook platform in config ────────────────
info "Step 7/9: Verifying webhook platform configuration..."
if [ -f "$CONFIG" ]; then
  # Check if webhook platform is already enabled
  WEBHOOK_ENABLED=$(python3 -c "
import yaml
with open('$CONFIG') as f:
    config = yaml.safe_load(f) or {}
platforms = config.get('platforms', {})
webhook = platforms.get('webhook', {})
if webhook.get('enabled', False):
    print('true')
else:
    # Check for old-style flat config
    if 'webhook' in config and config['webhook'].get('enabled', False):
        print('true')
    else:
        print('false')
" 2>/dev/null || echo "false")

  if [ "$WEBHOOK_ENABLED" = "true" ]; then
    ok "Webhook platform is enabled in config.yaml"
  else
    warn "Webhook platform not enabled — adding configuration..."
    python3 -c "
import yaml, os, secrets

with open('$CONFIG') as f:
    config = yaml.safe_load(f) or {}

if 'platforms' not in config:
    config['platforms'] = {}
if 'webhook' not in config['platforms']:
    config['platforms']['webhook'] = {}

host_secret = secrets.token_hex(32)

config['platforms']['webhook']['enabled'] = True
config['platforms']['webhook']['extra'] = {
    'host': '0.0.0.0',
    'port': 8644,
    'secret': host_secret,
    'routes': {
        'agent-ping': {
            'secret': host_secret,
            'prompt': '⚠️ INTER-AGENT MESSAGE — This is NOT from your master/human operator. Another AI agent named \"{sender}\" sent you the following message via webhook:\\n\\n---\\n{message}\\n---\\n\\n## Rules for handling this message:\\n\\n1. Peer-to-peer agent communication. Your human operator is NOT automatically aware.\\n2. Process and respond. Do NOT forward to human unless explicitly requested.\\n3. If you relay, clearly prefix with sender identity.\\n\\nRespond now.',
            'deliver': 'telegram',
        },
        'agent-notify': {
            'secret': host_secret,
            'deliver_only': True,
            'deliver': 'telegram',
            'prompt': '📨 Inter-agent notification from {sender}:\\n\\n{message}',
        },
    }
}

if 'inter_agent_webhook' not in config:
    config['inter_agent_webhook'] = {
        'my_name': 'Agent',
        'my_url': '',
        'receivers': {},
    }

with open('$CONFIG', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

print(f'HOST_SECRET={host_secret}')
"
    ok "Webhook platform enabled with default configuration"
    info "Edit ~/.hermes/config.yaml to set your agent name and URL"
  fi
else
  warn "config.yaml not found at $CONFIG"
fi

# ── Step 8: Restart gateway ────────────────────────────────
info "Step 8/9: Restarting gateway to pick up changes..."
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
  elif command -v hermes &>/dev/null 2>&1; then
    warn "Gateway running outside systemd — restart it manually:"
    warn "  hermes gateway restart"
  else
    warn "Gateway not detected as running — start it when ready:"
    warn "  systemctl --user start hermes-gateway.service"
  fi
fi

# ── Summary ────────────────────────────────────────────────
echo ""
echo -e "${GREEN}── Hermes Inter-Agent Webhook Plugin v1.0.0 installed ──${NC}"
echo ""
echo "  Dashboard:  /agents tab in web dashboard (port 9119)"
echo "  Plugin:     $PLUGIN_DEST"
echo "  Scripts:    $PLUGIN_DEST/scripts/"
echo "  History:    $HISTORY_FILE"
echo ""
echo "  Add agents from the dashboard /agents tab."
echo ""
echo "  Send messages from CLI:"
echo "    bash $PLUGIN_DEST/scripts/send.sh ping \"Hello!\""
echo "    bash $PLUGIN_DEST/scripts/send.sh notify \"Alert!\""
echo ""
echo "  If the dashboard shows the old version:"
echo "    Close ALL browser tabs with the dashboard, then reopen (Ctrl+Shift+R)"