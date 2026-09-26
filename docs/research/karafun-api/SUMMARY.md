# Karafun API Research Summary

## Research Completed

This document summarizes findings from comprehensive research of the Karafun API across multiple community projects and archived official documentation.

---

## Key Findings

1. **Two distinct APIs:**
   - Karafun Player Control API (WebSocket, local use): Unofficial but documented for controlling the Windows desktop player
   - KaraFun Box API (REST/OpenAPI): Official commercial API for venue management

2. **Player Control API requires no authentication** - connects via `ws://localhost:57570/` when Karafun Player is running with active subscription

3. **XML-over-WebSocket protocol** - all messages are XML strings; responses include status, catalog, and song list data

4. **Documentation removed** - the official developer portal (`karafun.com/developers/`) has been removed; archived copies are the authoritative source

5. **Six community implementation projects identified** - from Java (AndroidKarafunAPI) to JavaScript (karafun/touch, karasocket, karafun-api)

---

## File Structure Created

```
docs/research/karafun-api/
├── 01-overview.md              # API introduction, architecture, status
├── 02-api-reference.md          # Complete action/query reference with XML syntax
├── 03-authentication.md         # No-auth model, token auth for Box API
├── 04-endpoints.md              # Detailed endpoint documentation
├── 05-data-formats.md           # XML structure, field definitions
├── 06-community-tools.md        # Library catalog, project comparison
├── 07-known-limitations.md      # Verified limits and unverified questions
└── SUMMARY.md                   # This file
```

---

## Source Citations

### Primary Sources (GitHub Repositories)

- [natelewis/karafun-api](https://github.com/natelewis/karafun-api) - Node.js implementation
- [karafun/touch](https://github.com/karafun/touch) - Official KaraFun touchscreen
- [polytope/AndroidKarafunAPI](https://github.com/polytope/AndroidKarafunAPI) - Java Android client
- [jon-toy/karasocket](https://github.com/jon-toy/karasocket) - React web app

### External Sources

- Web Archive capture of [karafun.com API docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)
- [business.karafun.com/oem](https://business.karafun.com/oem) - OEM/Box API information
- [business.karafun.com/box/features/api-integration.html](https://business.karafun.com/box/features/api-integration.html) - Box API documentation

---

## Documented Actions

The following WebSocket actions are fully documented:

| Category | Actions |
| ---------- | --------- |
| Player Control | play, pause, next, seek, pitch, tempo |
| Querying | getStatus, getCatalogList, getList, search |
| Volume | setVolume |
| Queue | clearQueue, addToQueue, removeFromQueue, changeQueuePosition |
| Screen | screenPosition, fullscreen |

---

## Verified Response Fields

**Status Response:**

- `state`: idle, infoscreen, loading, playing
- `position`: seconds (optional)
- `volumeList`: general, bv, lead1, lead2
- `pitch`: integer value
- `tempo`: integer value (percentage)
- `queue`: item list with title, artist, year, duration, singer

**Song List Response:**

- `id`: unique identifier
- `title`, `artist`, `year`, `duration`

---

## Known Gaps

The following metadata fields appear in Karafun's marketing but were **not verified in the Player Control API responses**:

- Musical key (e.g., C, G#m)
- Beats per minute (BPM)
- Genre/style tags
- Lyrics/syllable synchronization
- Video stream URLs
- Difficulty levels

These may be available in the official KaraFun Box API for commercial partners.

---

## Recommendations

### For Python TUI Integration (karafun-intercept)

1. The Player Control API uses **XML over WebSocket** - use `websocket-client` or `websockets` library
2. Parse responses with `xml.etree.ElementTree` (stdlib) or `lxml`
3. Implement auto-reconnection (5-10 second delay recommended)
4. Handle optional elements (position only when playing)
5. Escape special characters in outgoing search queries

### For Further Research

1. Test with actual Karafun Player to verify all metadata fields
2. Contact KaraFun Business for OpenAPI spec for Box API
3. Investigate rate limits for commercial API
