# Karafun Player Control API Known Limitations

## Overview

This document catalogs verified limitations and quirks discovered during research of the Karafun Player Control API.

---

## Platform Limitations

### Operating System Support

| Platform | Support | Notes |
| ---------- | --------- | ------- |
| Windows | ✅ Supported | Karafun Player is Windows-only |
| macOS | ❌ Not supported | No official player client |
| Linux | ❌ Not supported | No official player client |
| Android | ✅ Via unofficial projects | polytope/AndroidKarafunAPI |

**Source:** [natelewis/karafun-api README](https://github.com/natelewis/karafun-api) - "Current KaraFun Player for Windows is the only version with this capability"

---

### Hardware Requirements

- Requires Karafun Player desktop application
- Requires active subscription
- Local network access to port 57570

---

## API Limitations

### Song Metadata Limits

**Verified limited fields in Player Control API:**

| Field | Available | Notes |
| ------- | ----------- | ------- |
| song_id | ✅ | Integer ID |
| title | ✅ | String |
| artist | ✅ | String |
| year | ✅ | String |
| duration | ✅ | Seconds |
| singer | ✅ | User-assigned |
| key | ❓ Unverified | Not in documented responses |
| bpm | ❓ Unverified | Not in documented responses |
| genre | ❓ Unverified | Not in documented responses |

**Source:** [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html) - Response format only includes basic fields

---

### Queue Limitations

| Limit | Value | Source |
|-------|-------|--------|
| Max queue items | ~100 | Approx 5 hours |
| Position values | 0, 1-n, 99999 | Official docs |

Source: [karafun/touch readme.md](https://github.com/karafun/touch/blob/master/readme.md) - "queue item count is limited to 100 (approx 5 hours of queue!)"

---

## Network Limitations

### Encryption

**The WebSocket connection uses unencrypted `ws://` protocol, not `wss://`.**

| Property | Value |
| ---------- | ------- |
| Default URL | `ws://localhost:57570/` |
| Secure WebSocket | ❌ Not supported |
| Authentication | None |

**Security Implication:** The API should only be used on local/trusted networks. Exposing to public networks is a security risk.

Source: [natelewis/karafun-api implementation](https://github.com/natelewis/karafun-api/blob/master/lib/karafun-api.js) - Uses `ws://` protocol

---

### CORS

- CORS headers are not applicable to WebSocket connections
- Browser-based clients must connect to same-origin or use proxy
- Localhost connections bypass CORS

---

## Known Issues from Community Projects

### natelewis/karafun-api

| Issue | Status | Details |
| ------- | -------- | ----------- |
| Project maintenance | Archived | Marked "NO LONGER MAINTAINED" |
| Console logging | Verbose | Logs all messages to console |
| Reconnection | Active | Auto-reconnects every 10 seconds |

Source: [natelewis/karafun-api README](https://github.com/natelewis/karafun-api) - "NO LONGER MAINTAINED"

---

## Developer Documentation Status

| Resource | Status | Notes |
| ---------- | -------- | ------- |
| karafun.com/developers/ | ❌ Removed | Redirects to affiliate page |
| Archived API docs | ✅ Available | Via Wayback Machine |
| OpenAPI spec | ⚠️ Missing | For Player Control API |
| SDK | ❌ None | Only unofficial client libraries |

Source: [business.karafun.com](https://business.karafun.com/) - Developer portal removed, OEM/business pages still active

---

## Response Format Quirks

### Boolean Attributes in XML

Some responses use attributes differently than expected:

```xml
<status state="playing">
  <position>123.45</position>  <!-- Optional, only when playing -->
</status>
```

- `position` element may be absent when player is idle
- Implementations must handle missing elements

Source: [karafun/touch javascript implementation](https://github.com/karafun/touch/blob/master/i/js/player.js) - Checks for position element presence

---

### Queue Item Position IDs

Queue items use 0-based or 1-based indexing depending on implementation:

```xml
<item id="{queue_position}" status="{item_state}">
```

Different projects interpret `id` differently:

- Some use it as 0-based queue position
- Some use it as 1-based display position

Source: [karasocket implementation](https://github.com/jon-toy/karasocket) and [karafun-touch implementation](https://github.com/karafun/touch) may differ

---

## Rate Limiting and Throttling

**Status: Unverified**

The official Player Control API documentation does not mention rate limiting. Community implementations have not reported throttling, suggesting:

- No documented rate limits for Player Control API
- Potential implicit limits not documented
- Box API (REST) may have different rate limits

---

## API Versioning

### Player Control API

- No explicit version number in protocol
- Versioned through Karafun Player client updates
- Breaking changes would require client library updates

### Box API (REST)

- Uses OpenAPI standard
- Versioned through endpoint URLs
- Proper versioning expected for commercial API

---

## Open Questions (Unverified)

The following questions could not be answered from available sources:

1. **Is there an official Python SDK?** - Only unofficial implementations found
2. **What are the actual rate limits for the Box API?** - Not documented publicly
3. **Are there API keys required for personal use?** - Player Control API uses no auth
4. **What metadata fields are available beyond the documented ones?** - Need to test with actual Player
5. **Does the API support lyrics or syllable sync data?** - Not documented in responses
6. **Video stream URL access?** - Not available in documented API
7. **OAuth / API key rotation?** - For Box API, unclear policies

---

## Testing Requirements

The following items need verification with actual Karafun Player:

- [ ] Full song metadata fields (key, bpm, genre, etc.)
- [ ] Rate limits for API calls
- [ ] Connection timeout behavior
- [ ] Large queue handling (>100 items theoretically)
- [ ] Special character handling in search queries
- [ ] Error response formats
- [ ] Offline mode behavior

---

## Recommendations

### For Personal/Home Use

1. Use the Player Control API for local network control
2. Ensure Karafun Player is running with active subscription
3. Keep WebSocket connection open for real-time updates
4. Handle reconnection automatically (5-10 second delay)

### For Production/Commercial Use

1. Consider the KaraFun Box API (REST with OpenAPI) for:
   - Session management
   - Booking system integration
   - Professional venue support

2. Contact KaraFun Business for:
   - OpenAPI/Swagger specification
   - Rate limit policies
   - Support SLA

**Source:** [KaraFun OEM & API Solutions](https://business.karafun.com/oem)
