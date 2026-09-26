# Karafun Player Control API Authentication

## Overview

The Karafun Player Control API **does not require authentication** for local network use.

---

## Authentication Model

### Player Control API (WebSocket)

| Property | Value |
| ---------- | ------- |
| Authentication Required | **No** |
| Access Control | Physical network access only |
| Prerequisites | Karafun Player running with active subscription |
| Connection Type | Local WebSocket |

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html) - "Communications between your software and KaraFun Player are made through TCP WebSockets. A socket server is running at all time when you have an active subscription in KaraFun Player (which must be started and running) and listening on port 57570 by default."

---

## Prerequisites

### Karafun Player Requirements

1. **KaraFun Player for Windows** must be installed
2. **Active subscription** must be valid
3. **Player must be running** - the WebSocket server only listens when Player is active

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html) - "A socket server is running at all time when you have an active subscription in KaraFun Player (which must be started and running)"

---

## Connection Details

### Network Configuration

| Aspect | Default Value |
| -------- | --------------- |
| Host | `localhost` (or `127.0.0.1`) |
| Port | `57570` |
| Protocol | WebSocket (ws://) |
| Path | `/` |

### Connection URL Formats

```
ws://localhost:57570/
ws://127.0.0.1:57570/
ws://[room-ip]:57570/  (for network access)
```

Source: [natelewis/karafun-api/lib/karafun-api.js](https://github.com/natelewis/karafun-api/blob/master/lib/karafun-api.js) - Default configuration: `server = 'localhost', port = 57570`

---

## KaraFun Box API (Separate System)

**Note**: This is a different API for commercial KaraFun Box systems.

### Authentication Method

Token-based HTTP authentication via OpenAPI.

| Property | Value |
| ---------- | ------- |
| Auth Required | Yes (API token) |
| Token Generation | Through KaraFun Business Account dashboard |
| Transport | HTTPS REST API |

**How to Obtain Token:**

1. Log into KaraFun Business account at `business.karafun.com`
2. Navigate to API section in left-hand menu
3. Generate or download authentication token

Source: [KaraFun Box API Integration](https://business.karafun.com/box/features/api-integration.html) - "Generate your access token From your KaraFun Business account, click API in the left-hand menu. From there, generate your authentication token"

---

## CORS Considerations

### Player Control API

- **CORS does not apply** - WebSocket connections to localhost are not subject to CORS policy
- The API is designed for local network use, not cross-origin web requests

### Box API (REST)

- Standard HTTP/HTTPS with token authentication
- CORS policies would apply for browser-based clients

---

## Security Model

### Player Control API Security

The API relies on **physical/network security**:

- Only accessible on the local network or via secure tunnel
- No encryption (uses plain ws://, not wss://)
- No API keys or credentials required
- Access controlled by network proximity to the Karafun Player

**WARNING**: The WebSocket connection uses unencrypted `ws://` protocol. Do not expose to public networks.

Source: [Implementation observations](https://github.com/natelewis/karafun-api) - Uses `ws://` protocol

---

## Implementation Notes

### Token Requirement Status

| API | Token Required | Verification |
|-----|----------------|--------------|
| Player Control (WebSocket) | No | Requires running Player with subscription |
| Box Session Management (REST) | Yes | Requires Business account |

---

## Unverified Claims

The following details are marked unverified as they were not confirmed in the primary sources:

- Whether OAuth or other token types are supported for Box API
- TTL/expiration of Box API tokens
- Rate limiting policies for Box API
