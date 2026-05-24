#!/bin/bash
# setup.sh — Interactive setup for inter-agent webhook communication
# Prompts for secrets and stores them in ~/.hermes/config.yaml

set -euo pipefail

CONFIG="$HOME/.hermes/config.yaml"

echo "═══════════════════════════════════════════════════"
echo "  Inter-Agent Webhook Setup"
echo "═══════════════════════════════════════════════════"
echo ""

# ── Dependency Check ────────────────────────────────────
echo "── Checking Dependencies ──"
echo ""

MISSING=()

# Check python3
if ! command -v python3 &>/dev/null; then
    MISSING+=("python3")
    echo "  ✗ python3 — not found"
else
    echo "  ✓ python3 — $(python3 --version 2>&1)"
fi

# Check curl
if ! command -v curl &>/dev/null; then
    MISSING+=("curl")
    echo "  ✗ curl — not found"
else
    echo "  ✓ curl — $(curl --version 2>&1 | head -1)"
fi

# Check pip (for installing pyyaml)
if ! python3 -m pip --version &>/dev/null 2>&1; then
    MISSING+=("pip")
    echo "  ✗ pip — not found (needed to install PyYAML)"
else
    echo "  ✓ pip — $(python3 -m pip --version 2>&1 | head -1)"
fi

# Check pyyaml
if python3 -c "import yaml" &>/dev/null 2>&1; then
    echo "  ✓ PyYAML — installed"
else
    echo "  ⚠ PyYAML — not installed (will auto-install)"
fi

echo ""

# Install missing packages
if ! python3 -c "import yaml" &>/dev/null 2>&1; then
    echo "Installing PyYAML..."
    python3 -m pip install --user pyyaml 2>/dev/null || python3 -m pip install pyyaml
    echo "  ✓ PyYAML installed"
    echo ""
fi

# Handle system-level missing deps
if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "── Missing System Dependencies ──"
    echo ""
    for dep in "${MISSING[@]}"; do
        case "$dep" in
            python3)
                echo "  python3 is required. Install it with:"
                echo "    Ubuntu/Debian:  sudo apt install python3"
                echo "    macOS:          brew install python3"
                echo "    Windows:        winget install Python.Python.3"
                ;;
            curl)
                echo "  curl is required for the bash sender. Install it with:"
                echo "    Ubuntu/Debian:  sudo apt install curl"
                echo "    macOS:          brew install curl"
                echo "    Windows:        winget install cURL.cURL"
                ;;
            pip)
                echo "  pip is required to install PyYAML. Install it with:"
                echo "    Ubuntu/Debian:  sudo apt install python3-pip"
                echo "    macOS:          python3 -m ensurepip --upgrade"
                echo "    Windows:        python -m ensurepip --upgrade"
                ;;
        esac
        echo ""
    done

    # If python3 or pip is missing, we can't continue
    if [[ " ${MISSING[*]} " =~ " python3 " ]] || [[ " ${MISSING[*]} " =~ " pip " ]]; then
        echo "ERROR: Cannot continue without python3 and pip. Install them first, then re-run setup."
        exit 1
    fi

    # If only curl is missing, warn but continue (Python sender still works)
    if [[ " ${MISSING[*]} " =~ " curl " ]]; then
        echo "⚠ curl is missing — the bash sender (send.sh) will not work."
        echo "  The Python sender (send_webhook.py) works without curl."
        echo "  Install curl later for bash support."
        echo ""
        read -rp "Continue anyway? [Y/n]: " CONTINUE
        CONTINUE="${CONTINUE:-Y}"
        if [[ ! "$CONTINUE" =~ ^[Yy] ]]; then
            echo "Aborted. Install curl and re-run."
            exit 0
        fi
    fi
fi

echo "── All dependencies satisfied ──"
echo ""
echo "This script configures your agent to send messages"
echo "to other agents via webhooks over Tailscale."
echo ""

# ── Agent Name ──────────────────────────────────────────
echo "── Your Agent Name ──"
echo "What should other agents call you? (e.g., Eliana, Remy, Atlas)"
read -rp "Your agent name: " MY_NAME
MY_NAME="${MY_NAME:-Agent}"
echo ""

# ── Receiver Details ────────────────────────────────────
echo "── Receiver Agent ──"
echo "Enter the details of the agent you want to talk to."
echo ""

read -rp "Receiver's Tailscale Funnel URL (e.g., https://remy.tailXXXXX.ts.net): " RECEIVER_URL
if [[ -z "$RECEIVER_URL" ]]; then
    echo "ERROR: URL is required."
    exit 1
fi

# Strip trailing slash
RECEIVER_URL="${RECEIVER_URL%/}"

read -rp "Receiver's webhook secret (64-char hex string from their config): " RECEIVER_SECRET
if [[ -z "$RECEIVER_SECRET" ]]; then
    echo "ERROR: Secret is required."
    exit 1
fi

read -rp "Route name for AI-processed messages [agent-ping]: " ROUTE_PING
ROUTE_PING="${ROUTE_PING:-agent-ping}"

read -rp "Route name for direct notifications [agent-notify]: " ROUTE_NOTIFY
ROUTE_NOTIFY="${ROUTE_NOTIFY:-agent-notify}"

read -rp "Nickname for this receiver (e.g., remy) [receiver]: " RECEIVER_NICK
RECEIVER_NICK="${RECEIVER_NICK:-receiver}"

echo ""
echo "── Summary ──"
echo "  Your name:      $MY_NAME"
echo "  Receiver URL:   $RECEIVER_URL"
echo "  Receiver nick:  $RECEIVER_NICK"
echo "  Ping route:     $ROUTE_PING"
echo "  Notify route:   $ROUTE_NOTIFY"
echo ""

read -rp "Save this configuration? [Y/n]: " CONFIRM
CONFIRM="${CONFIRM:-Y}"
if [[ ! "$CONFIRM" =~ ^[Yy] ]]; then
    echo "Aborted."
    exit 0
fi

# ── Write to config.yaml ────────────────────────────────
echo ""
echo "Writing configuration to $CONFIG ..."

# Use Python to safely merge YAML (avoiding corruption)
python3 - "$CONFIG" "$MY_NAME" "$RECEIVER_NICK" "$RECEIVER_URL" "$RECEIVER_SECRET" "$ROUTE_PING" "$ROUTE_NOTIFY" <<'PYEOF'
import sys, yaml, os

config_path = sys.argv[1]
my_name = sys.argv[2]
nick = sys.argv[3]
url = sys.argv[4]
secret = sys.argv[5]
route_ping = sys.argv[6]
route_notify = sys.argv[7]

# Load existing config
if os.path.exists(config_path):
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
else:
    config = {}

# Ensure inter_agent_webhook section exists
if "inter_agent_webhook" not in config:
    config["inter_agent_webhook"] = {}

# Set agent name
config["inter_agent_webhook"]["my_name"] = my_name

# Ensure receivers dict exists
if "receivers" not in config["inter_agent_webhook"]:
    config["inter_agent_webhook"]["receivers"] = {}

# Add/update receiver
config["inter_agent_webhook"]["receivers"][nick] = {
    "url": url,
    "secret": secret,
    "route_ping": route_ping,
    "route_notify": route_notify,
}

# Write back
with open(config_path, "w") as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

print(f"  ✓ Saved receiver '{nick}' to config.yaml")
PYEOF

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ✓ Setup complete!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "Send messages with:"
echo "  bash ~/.hermes/skills/inter-agent-webhook/scripts/send.sh ping \"Hello!\""
echo "  bash ~/.hermes/skills/inter-agent-webhook/scripts/send.sh notify \"Alert!\""
echo ""
echo "Or from Python:"
echo "  python3 ~/.hermes/skills/inter-agent-webhook/scripts/send_webhook.py ping \"Hello!\""
echo ""
