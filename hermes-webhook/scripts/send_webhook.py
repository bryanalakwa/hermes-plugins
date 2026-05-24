#!/usr/bin/env python3
"""
send_webhook.py — Send inter-agent messages via webhook over Tailscale

Usage:
    python3 send_webhook.py ping "Your message" [--sender NAME] [--receiver NICK]
    python3 send_webhook.py notify "Your message" [--sender NAME] [--receiver NICK]

Configuration is read from ~/.hermes/config.yaml under inter_agent_webhook:.
Run setup first: bash ~/.hermes/skills/inter-agent-webhook/scripts/setup.sh
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import urllib.request
import urllib.error

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

CONFIG_PATH = os.path.expanduser("~/.hermes/config.yaml")


def load_config(receiver_nick: str = None) -> dict:
    """Load inter_agent_webhook config from ~/.hermes/config.yaml"""
    if not os.path.exists(CONFIG_PATH):
        print(f"ERROR: {CONFIG_PATH} not found. Run setup first.", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f) or {}

    iw = config.get("inter_agent_webhook", {})
    receivers = iw.get("receivers", {})

    if not receivers:
        print("ERROR: No receivers configured. Run setup first.", file=sys.stderr)
        sys.exit(1)

    if not receiver_nick:
        receiver_nick = list(receivers.keys())[0]

    if receiver_nick not in receivers:
        available = ", ".join(receivers.keys())
        print(f"ERROR: Receiver '{receiver_nick}' not found. Available: {available}", file=sys.stderr)
        sys.exit(1)

    r = receivers[receiver_nick]
    return {
        "my_name": iw.get("my_name", "Agent"),
        "url": r["url"],
        "secret": r["secret"],
        "route_ping": r.get("route_ping", "agent-ping"),
        "route_notify": r.get("route_notify", "agent-notify"),
    }


def send_webhook(url: str, secret: str, route: str, message: str, sender: str) -> dict:
    """Send a signed webhook POST."""
    payload = json.dumps({"message": message, "sender": sender}).encode()
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    webhook_url = f"{url.rstrip('/')}/webhooks/{route}"
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {"ok": True, "status": resp.status, "body": json.loads(resp.read())}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"ok": False, "status": e.code, "body": body}
    except Exception as e:
        return {"ok": False, "status": 0, "body": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Send inter-agent webhook messages")
    parser.add_argument("mode", choices=["ping", "notify"], help="ping=AI processed, notify=direct delivery")
    parser.add_argument("message", help="Message content")
    parser.add_argument("--sender", help="Override sender name")
    parser.add_argument("--receiver", help="Receiver nickname (from config)")
    parser.add_argument("--url", help="Override webhook URL")
    parser.add_argument("--secret", help="Override webhook secret")
    args = parser.parse_args()

    # Load config
    cfg = load_config(args.receiver)

    sender = args.sender or cfg["my_name"]
    url = args.url or cfg["url"]
    secret = args.secret or cfg["secret"]
    route = cfg["route_ping"] if args.mode == "ping" else cfg["route_notify"]

    # Send
    print(f"→ Sending {args.mode} to {url}/webhooks/{route} ...")
    result = send_webhook(url, secret, route, args.message, sender)

    status = result["status"]
    body = result["body"]

    if isinstance(body, dict):
        print(f"  HTTP {status}: {json.dumps(body)}")
    else:
        print(f"  HTTP {status}: {body}")

    if result["ok"] and result["status"] in (200, 202):
        print("  ✓ Delivered successfully")
    else:
        print("  ✗ Delivery failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
