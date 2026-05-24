# Inter-Agent Webhook Protocol

## Message Format

All inter-agent messages are JSON POST requests with HMAC-SHA256 authentication.

### HTTP Request

```
POST /webhooks/{route_name} HTTP/1.1
Content-Type: application/json
X-Webhook-Signature: {hmac_hex_digest}

{"message": "Hello from another agent.", "sender": "AgentName"}
```

### Payload Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | The message content |
| `sender` | string | Yes | Name of the sending agent |

### Signature Computation

The signature is HMAC-SHA256 of the raw request body bytes using the shared secret:

```python
import hmac, hashlib
signature = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
```

The signature is sent as a hex string in the `X-Webhook-Signature` header.

### Response Codes

| Code | Meaning |
|------|---------|
| 200 | Delivered successfully (direct delivery) |
| 202 | Accepted for processing (AI route — agent will respond asynchronously) |
| 400 | Malformed JSON body |
| 401 | Invalid or missing HMAC signature |
| 404 | Unknown route name |
| 413 | Payload too large (>1MB default) |
| 429 | Rate limit exceeded (30 req/min default) |
| 502 | Target delivery failed |

### Response Body (success)

```json
{"status": "delivered", "route": "agent-notify", "target": "telegram", "delivery_id": "..."}
```

### Response Body (duplicate)

```json
{"status": "duplicate", "delivery_id": "..."}
```

## Route Types

### AI Processing Route (`agent-ping`)

The message becomes a prompt for the AI agent. The agent reads it, reasons, and composes a response. The response is delivered to the configured target (Telegram, Discord, etc.).

**Flow:**
1. POST arrives → HMAC validated
2. Payload rendered into prompt template
3. Agent processes the prompt
4. Agent's response delivered to target platform
5. HTTP 202 returned immediately (processing is asynchronous)

### Direct Delivery Route (`agent-notify`)

The rendered prompt template IS the message. No agent processing — forwarded directly to the target platform.

**Flow:**
1. POST arrives → HMAC validated
2. Prompt template rendered with payload fields
3. Rendered message delivered to target platform
4. HTTP 200 returned after delivery confirmation

## Tailscale Funnel Setup

To make a webhook receiver publicly accessible without port forwarding:

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate
sudo tailscale up

# Enable Funnel (one-time tailnet admin step first)
sudo tailscale funnel --bg http://localhost:8644
```

This produces a public URL: `https://<name>.tailXXXXX.ts.net`

### Funnel Prerequisites

1. Tailscale installed and authenticated on the receiver
2. Funnel enabled on the tailnet (admin visits `https://login.tailscale.com/f/funnel?node=<nodeID>`)
3. Webhook platform enabled in receiver's `config.yaml`
4. At least one route configured with a secret

## Security Considerations

- **Always use HMAC signatures** — never expose an unauthenticated webhook endpoint
- **Use per-route secrets** — don't reuse the same secret across routes
- **Tailscale Funnel provides TLS** — no need for separate certificate management
- **Rate limiting** prevents abuse (30 req/min default)
- **Idempotency** prevents duplicate processing on retries (1-hour dedup window)
- **Body size limit** prevents memory exhaustion (1MB default)
