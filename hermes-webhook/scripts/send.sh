#!/bin/bash
# send.sh — Send an inter-agent webhook message
#
# Usage:
#   bash send.sh ping <message> [receiver_nick]
#   bash send.sh notify <message> [receiver_nick]
#
# Reads configuration from ~/.hermes/config.yaml (inter_agent_webhook section)
# Falls back to environment variables if config is not set.

set -euo pipefail

MODE="${1:?Usage: $0 <ping|notify> <message> [receiver_nick]}"
MESSAGE="${2:?Usage: $0 <ping|notify> <message> [receiver_nick]}"
RECEIVER_NICK="${3:-}"

CONFIG="$HOME/.hermes/config.yaml"

# ── Read config from YAML ───────────────────────────────
if [[ -f "$CONFIG" ]]; then
    # Extract values using python for reliable YAML parsing
    CONFIG_JSON=$(python3 -c "
import yaml, json, sys
with open(sys.argv[1]) as f:
    cfg = yaml.safe_load(f) or {}
iw = cfg.get('inter_agent_webhook', {})
receivers = iw.get('receivers', {})
nick = sys.argv[2] if sys.argv[2] else (list(receivers.keys())[0] if receivers else '')
if nick and nick in receivers:
    r = receivers[nick]
    print(json.dumps({
        'my_name': iw.get('my_name', 'Agent'),
        'url': r.get('url', ''),
        'secret': r.get('secret', ''),
        'route_ping': r.get('route_ping', 'agent-ping'),
        'route_notify': r.get('route_notify', 'agent-notify'),
    }))
" "$CONFIG" "$RECEIVER_NICK" 2>/dev/null) || CONFIG_JSON=""
fi

if [[ -n "$CONFIG_JSON" ]]; then
    MY_NAME=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['my_name'])")
    BASE_URL=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['url'])")
    SECRET=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['secret'])")
    ROUTE_PING=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['route_ping'])")
    ROUTE_NOTIFY=$(echo "$CONFIG_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['route_notify'])")
else
    # Fallback to environment variables
    MY_NAME="${MY_NAME:-Agent}"
    BASE_URL="${RECEIVER_URL:-}"
    SECRET="${WEBHOOK_SECRET:-}"
    ROUTE_PING="${ROUTE_PING:-agent-ping}"
    ROUTE_NOTIFY="${ROUTE_NOTIFY:-agent-notify}"
fi

# ── Validate ────────────────────────────────────────────
if [[ -z "$BASE_URL" ]]; then
    echo "ERROR: No receiver URL configured."
    echo "Run setup first: bash ~/.hermes/skills/inter-agent-webhook/scripts/setup.sh"
    exit 1
fi

if [[ -z "$SECRET" ]]; then
    echo "ERROR: No webhook secret configured."
    echo "Run setup first: bash ~/.hermes/skills/inter-agent-webhook/scripts/setup.sh"
    exit 1
fi

# ── Build payload ───────────────────────────────────────
PAYLOAD=$(python3 -c "
import json, sys
print(json.dumps({'message': sys.argv[1], 'sender': sys.argv[2]}))
" "$MESSAGE" "$MY_NAME")

# ── Compute HMAC-SHA256 signature ───────────────────────
SIGNATURE=$(python3 -c "
import hmac, hashlib, sys
print(hmac.new(sys.argv[1].encode(), sys.argv[2].encode(), hashlib.sha256).hexdigest())
" "$SECRET" "$PAYLOAD")

# ── Select route ────────────────────────────────────────
case "$MODE" in
    ping)   ROUTE="$ROUTE_PING" ;;
    notify) ROUTE="$ROUTE_NOTIFY" ;;
    *)      echo "ERROR: Mode must be 'ping' or 'notify'"; exit 1 ;;
esac

URL="${BASE_URL%/}/webhooks/${ROUTE}"

# ── Send ────────────────────────────────────────────────
echo "→ Sending $MODE to $URL ..."
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$URL" \
    -H "Content-Type: application/json" \
    -H "X-Webhook-Signature: $SIGNATURE" \
    -d "$PAYLOAD" 2>&1)

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

echo "  HTTP $HTTP_CODE"
echo "  $BODY"

if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "202" ]]; then
    echo "  ✓ Delivered successfully"
else
    echo "  ✗ Delivery failed"
    exit 1
fi
