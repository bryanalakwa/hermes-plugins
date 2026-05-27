#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
#  Eliana — Fresh Initialization Script
#  =====================================
#  Run this on a fresh Hermes Agent install to set up everything:
#    plugins, skills, memory, config, dashboard auth, systemd services.
#
#  Prerequisites:
#    - Hermes Agent installed (pip install hermes-agent or from source)
#    - ~/.hermes/ directory created by `hermes setup` or `hermes gateway start`
#    - Python 3.10+, pip, git, node
#
#  Usage:
#    chmod +x init.sh
#    ./init.sh
#
#  Or with a dashboard password:
#    ./init.sh --password MySecretPass
#
#  After running:
#    1. Review ~/.hermes/config.yaml (API keys, model, Telegram token)
#    2. Start the gateway:   hermes gateway start
#    3. Start the dashboard: hermes dashboard start
#    4. Open http://127.0.0.1:9119
#    5. Enter your dashboard password
#    6. Talk to Eliana via Telegram or hermes chat
# ══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Args ─────────────────────────────────────────────────────────────────────
DASHBOARD_PASSWORD=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --password) DASHBOARD_PASSWORD="$2"; shift 2 ;;
    -h|--help)  sed -n '2,20p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *)          echo "Unknown arg: $1"; exit 1 ;;
  esac
done

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
log()  { echo "  ✓ $*"; }
warn() { echo "  ⚠ $*"; }
step() { echo ""; echo "▸ $*"; }

# ── 0. Verify prerequisites ─────────────────────────────────────────────────
step "Checking prerequisites"

command -v python3 >/dev/null 2>&1 || { echo "  ✗ python3 not found"; exit 1; }
command -v git    >/dev/null 2>&1 || { echo "  ✗ git not found"; exit 1; }

log "System: $(uname -s) $(uname -m)"
log "Python: $(python3 --version)"

# ── 1. Locate or clone Hermes Agent source ──────────────────────────────────
step "Hermes Agent source"

# Try common locations
AGENT_DIR=""
for candidate in \
  "$HERMES_HOME/hermes-agent" \
  "$HOME/hermes-agent" \
  "$(python3 -c 'import hermes_cli; import os; print(os.path.dirname(hermes_cli.__file__))' 2>/dev/null)"; do
  if [ -n "$candidate" ] && [ -d "$candidate" ] && [ -f "$candidate/hermes_cli/web_server.py" ]; then
    AGENT_DIR="$candidate"
    break
  fi
done

if [ -z "$AGENT_DIR" ]; then
  warn "Hermes Agent source not found. Cloning from GitHub..."
  AGENT_DIR="$HOME/hermes-agent"
  git clone --depth 1 https://github.com/NousResearch/hermes-agent.git "$AGENT_DIR"
fi

log "Agent source: $AGENT_DIR"

# ── 2. Ensure ~/.hermes/ exists ─────────────────────────────────────────────
step "Hermes home directory"
mkdir -p "$HERMES_HOME"
log "$HERMES_HOME"

# ── 3. Install Python dependencies ──────────────────────────────────────────
step "Python dependencies"

cd "$AGENT_DIR"

# Find or create venv
for venv_path in "$AGENT_DIR/.venv" "$AGENT_DIR/venv" "$HERMES_HOME/hermes-agent/venv"; do
  if [ -f "$venv_path/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$venv_path/bin/activate"
    log "Activated venv: $venv_path"
    break
  fi
done

if [ -z "${VIRTUAL_ENV:-}" ]; then
  warn "No venv found — creating one"
  python3 -m venv "$AGENT_DIR/.venv"
  source "$AGENT_DIR/.venv/bin/activate"
fi

# Core deps for dashboard + plugins
pip install -q fastapi "uvicorn[standard]" bcrypt python-multipart 2>/dev/null || true
log "Core deps ready"

# ── 4. Install plugins from public repo ─────────────────────────────────────
step "Plugins"

PLUGIN_DIR="$AGENT_DIR/plugins"
mkdir -p "$PLUGIN_DIR"

TMP_HP=$(mktemp -d)
trap 'rm -rf "$TMP_HP"' EXIT

git clone --depth 1 https://github.com/bryanalakwa/hermes-plugins.git "$TMP_HP/hp" 2>/dev/null || {
  warn "Could not clone hermes-plugins — plugins must be installed manually"
}

if [ -d "$TMP_HP/hp" ]; then
  for plugin in hermes-webhook hermes-dream-engine; do
    if [ -d "$TMP_HP/hp/$plugin" ]; then
      if [ -d "$PLUGIN_DIR/$plugin" ]; then
        log "$plugin already installed — updating"
        rm -rf "$PLUGIN_DIR/$plugin"
      fi
      cp -r "$TMP_HP/hp/$plugin" "$PLUGIN_DIR/"
      log "Installed $plugin"

      # Run plugin install script if present
      if [ -f "$PLUGIN_DIR/$plugin/install.sh" ]; then
        echo "    Running $plugin/install.sh..."
        (cd "$PLUGIN_DIR/$plugin" && bash install.sh) 2>/dev/null || warn "$plugin install.sh had errors"
      fi
    fi
  done
fi

# ── 5. Install skills ───────────────────────────────────────────────────────
step "Skills"

SKILL_DIR="$AGENT_DIR/skills"

if [ -d "$TMP_HP/hp" ] && [ -d "$TMP_HP/hp/hermes-webhook" ]; then
  # Copy inter-agent-webhook skill references
  mkdir -p "$SKILL_DIR/hermes-agent/references"
  for ref in plugin-development-guide.md install-template.sh dashboard-plugin-development.md; do
    [ -f "$PLUGIN_DIR/hermes-dream-engine/$ref" ] && \
      cp "$PLUGIN_DIR/hermes-dream-engine/$ref" "$SKILL_DIR/hermes-agent/references/" 2>/dev/null && \
      log "Skill ref: $ref" || true
  done
fi
log "Skills ready"

# ── 6. Dashboard password auth gate ─────────────────────────────────────────
step "Dashboard auth gate"

AUTH_FILE="$HERMES_HOME/dashboard.auth"

if [ -n "$DASHBOARD_PASSWORD" ]; then
  python3 -c "
import bcrypt, sys
pw = sys.argv[1]
h = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
with open('$AUTH_FILE', 'w') as f:
    f.write(h)
" "$DASHBOARD_PASSWORD"
  chmod 600 "$AUTH_FILE"
  log "Dashboard password hash saved"
elif [ -f "$AUTH_FILE" ] && [ -s "$AUTH_FILE" ]; then
  log "Dashboard auth file exists"
else
  warn "No dashboard password set."
  warn "  Set one with: ./init.sh --password YourPassword"
  warn "  Or after install: hermes dashboard --set-password"
fi

if grep -q "_build_password_gate" "$AGENT_DIR/hermes_cli/web_server.py" 2>/dev/null; then
  log "Password gate already in web_server.py"
else
  warn "Password gate not found in web_server.py — may need manual patch"
fi

# ── 7. Memory files ─────────────────────────────────────────────────────────
step "Memory files"

mkdir -p "$HERMES_HOME/memories" "$HERMES_HOME/dreams"

if [ ! -f "$HERMES_HOME/memories/MEMORY.md" ]; then
  cat > "$HERMES_HOME/memories/MEMORY.md" << 'EOF'
Eliana — Personal AI assistant, developed by ZOO company.
Analytical, methodical, adaptable, nurturing, pragmatic. Tone: warm.
Role: Personal assistant in charge of all dealings and AI agents.
Language: English. Response length: balanced, concise but complete.
Initialized via init.sh on fresh Hermes Agent install.
EOF
  log "MEMORY.md created"
else
  log "MEMORY.md exists — preserved"
fi

if [ ! -f "$HERMES_HOME/memories/USER.md" ]; then
  cat > "$HERMES_HOME/memories/USER.md" << 'EOF'
User's AI assistant is named Eliana.
Role: Personal assistant in charge of all dealings and AI agents.
Language: English. Response length: balanced, concise but complete.
GitHub backup repo: bryanalakwa/Eliana_backup (private).
Public plugins repo: bryanalakwa/hermes-plugins (public).
Initialized via init.sh.
EOF
  log "USER.md created"
else
  log "USER.md exists — preserved"
fi

# ── 8. Dream state ──────────────────────────────────────────────────────────
if [ ! -f "$HERMES_HOME/dreams/state.json" ]; then
  cat > "$HERMES_HOME/dreams/state.json" << 'EOF'
{
  "last_dream_at": null,
  "dreams_today": 0,
  "last_date": null,
  "total_dreams": 0,
  "entries": []
}
EOF
  log "Dream state initialized"
else
  log "Dream state exists — preserved"
fi

# ── 9. Systemd services (Linux/WSL only) ────────────────────────────────────
step "Systemd services"

if command -v systemctl >/dev/null 2>&1 && [ -d "$HOME/.config/systemd/user" -o -w "$HOME/.config/systemd/user" ]; then
  mkdir -p "$HOME/.config/systemd/user"

  # Dashboard service
  DSVC="$HOME/.config/systemd/user/hermes-dashboard.service"
  if [ ! -f "$DSVC" ]; then
    HERMES_USER="$USER"
    cat > "$DSVC" << SVCEOF
[Unit]
Description=Hermes Agent Dashboard
BindsTo=hermes-gateway.service
After=hermes-gateway.service

[Service]
Type=simple
ExecStartPre=/bin/sleep 2
ExecStart=$AGENT_DIR/.venv/bin/hermes dashboard --host 127.0.0.1 --port 9119 --no-open
Restart=on-failure
RestartSec=5
Environment=PATH=$AGENT_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
SVCEOF
    log "hermes-dashboard.service created"
  else
    log "hermes-dashboard.service exists"
  fi

  systemctl --user daemon-reload 2>/dev/null || true
  systemctl --user enable hermes-dashboard.service 2>/dev/null || true
  systemctl --user enable hermes-gateway.service 2>/dev/null || true
  log "Services enabled"
else
  warn "systemctl not available — skipping service setup"
fi

# ── 10. Config idempotency check ────────────────────────────────────────────
step "Config check"

if [ ! -f "$HERMES_HOME/config.yaml" ]; then
  warn "No config.yaml found. Run 'hermes setup' to create one."
else
  log "config.yaml exists"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "  ═══════════════════════════════════════════════════════════════"
echo "  Eliana installation complete."
echo ""
echo "  Files set up:"
echo "    Agent:    $AGENT_DIR"
echo "    Plugins:  $PLUGIN_DIR"
echo "    Skills:   $SKILL_DIR"
echo "    Memory:   $HERMES_HOME/memories/"
echo "    Dreams:   $HERMES_HOME/dreams/"
echo "    Config:   $HERMES_HOME/config.yaml"
echo "    Auth:     ${AUTH_FILE}"
echo ""
echo "  Next steps:"
echo "    1. Edit ~/.hermes/config.yaml — add API keys, Telegram token"
echo "    2. Start gateway:   hermes gateway start"
echo "    3. Start dashboard: hermes dashboard start"
echo "    4. Open: http://127.0.0.1:9119"
echo "    5. Enter dashboard password"
echo ""
echo "  To verify everything works:"
echo "    hermes chat"
echo "  ═══════════════════════════════════════════════════════════════"
