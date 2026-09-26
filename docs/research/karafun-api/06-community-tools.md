# Karafun API Community Tools and Libraries

## Overview

Multiple open-source projects have implemented Karafun Player Control API clients. This document catalogs them with implementation details.

---

## Node.js Libraries

### karafun-api (natelewis/karafun-api)

| Property | Value |
| ---------- | ------- |
| Language | JavaScript |
| Status | **NO LONGER MAINTAINED** |
| Stars | 5 |
| Repository | <https://github.com/natelewis/karafun-api> |

**Description:** A Node.js wrapper around the Karafun WebSocket API that provides event-based interface.

**Features:**

- EventEmitter-based API
- Automatic reconnection with configurable delay
- Event callbacks: `connecting`, `connected`, `closed`, `connectionFailed`, `connectionError`, `statusUpdated`, `playStarted`, `playStopped`

**Dependencies:**

- `websocket` (v1.0.26)
- `xml2js` (v0.4.19)

**Source:** [natelewis/karafun-api/README.md](https://github.com/natelewis/karafun-api/blob/master/README.md)

**License:** Apache 2.0

---

### karasocket (jon-toy/karasocket)

| Property | Value |
| ---------- | ------- |
| Language | JavaScript (React) |
| Status | Archived |
| Stars | N/A (private?) |
| Repository | <https://github.com/jon-toy/karasocket> |

**Description:** A React/Redux web application that connects to KaraFun via websockets.

**Features:**

- React frontend with Redux state management
- Remote song search and queue management
- Mobile-friendly interface for guest participation

**Source:** [jon-toy/karasocket](https://github.com/jon-toy/karasocket)

---

## Java Libraries

### KarafunAPI (polytope/AndroidKarafunAPI)

| Property | Value |
| ---------- | ------- |
| Language | Java (Android) |
| Status | Active/Maintained |
| Repository | <https://github.com/polytope/AndroidKarafunAPI> |

**Description:** Android client library for the Karafun Player Control API.

**Key Files:**

- `KarafunClient.java` - Main client class
- `KarafunListener.java` - Event listener interface
- `model/Song.java`, `model/Status.java`, `model/QueueList.java` - Data models

**Source:** [polytope/AndroidKarafunAPI](https://github.com/polytope/AndroidKarafunAPI)

---

## Open-Source Projects

### KaraFun Touch (karafun/touch)

| Property | Value |
|----------|-------|
| Language | JavaScript (Chrome App) |
| Repository | <https://github.com/karafun/touch> |

**Description:** The official KaraFun touchscreen interface for controlling KaraFun Player remotely.

**Features:**

- Touchscreen UI for song selection
- Queue management
- Player controls (play, pause, next, seek, pitch, tempo)
- Multi-screen support (position, fullscreen)

**Documentation Sources:**

- `readme.md` - Complete API reference for this project

**Source:** [karafun/touch](https://github.com/karafun/touch)

---

### KaraFun Touch (recisio/karafun-touch)

| Property | Value |
| ---------- | ------- |
| Language | JavaScript (Chrome App) |
| Last Updated | 2015 |
| Repository | <https://github.com/recisio/karafun-touch> |

**Description:** Early open-source touchscreen interface (predecessor to karafun/touch).

**Source:** [recisio/karafun-touch](https://github.com/recisio/karafun-touch)

---

## Project Comparison

### Socket Connection Details

| Project | Default Host | Default Port | Reconnection |
| --------- | -------------- | -------------- | -------------- |
| natelewis/karafun-api | localhost | 57570 | 10s configurable |
| jon-toy/karasocket | user-specified | 57570 | 1s configurable |
| polytope/AndroidKarafunAPI | user-specified | 57570 | Manual reconnect |
| karafun/touch | user-specified | 57570 | 3s reconnect |

Source: Various project implementations

---

### Event/Response Handling

| Project | Parser | Response Types |
| --------- | -------- | ---------------- |
| natelewis/karafun-api | xml2js | status, playStarted, playStopped |
| jon-toy/karasocket | xml-js | status.queue, status.state, list |
| polytope/AndroidKarafunAPI | XmlPullParser | status, catalogList, list |
| karafun/touch | jQuery parseXML | status, catalogList, list |

---

## Implementation Analysis

### Common Patterns

1. **XML Parsing:**
   - JavaScript: `xml-json` (karasocket), `xml2js` (natelewis)
   - Java: `XmlPullParser` (AndroidKarafunAPI)
   - jQuery: `.parseXML()` (karafun-touch)

2. **Connection Management:**
   - All implement auto-reconnection
   - Backoff strategies vary (1s to 10s)

3. **Event Architecture:**
   - Node.js: EventEmitter pattern
   - Java: Listener interface pattern
   - JavaScript: Redux actions / DOM events

---

## KaraFun Box (Business) API

### OpenAPI Integration

The KaraFun Box API for commercial venues uses OpenAPI/Swagger specification.

**Access:** Through KaraFun Business account dashboard

**Token Generation:** Required for all requests

**Source:** [KaraFun Box API Integration](https://business.karafun.com/box/features/api-integration.html)

---

## Notable Observations

### Project Status Timeline

1. **2015** - recisio/karafun-touch (early implementation)
2. **2018** - natelewis/karafun-api (Node.js wrapper)
3. **2018** - polytope/AndroidKarafunAPI (Android client)
4. **2018+** - jon-toy/karasocket (React web app)
5. **2020+** - karafun/touch (Official KaraFun project)

### Fork Relationships

The repository graph shows:

- `natelewis/karafun-api` has 1 fork
- Multiple projects reference the same API documentation URL

---

## Community Resources

| Resource | URL |
| ---------- | ----- |
| Karafun/touch (official) | <https://github.com/karafun/touch> |
| AndroidKarafunAPI | <https://github.com/polytope/AndroidKarafunAPI> |
| karasocket | <https://github.com/jon-toy/karasocket> |
| karafun-api (Node.js) | <https://github.com/natelewis/karafun-api> |
| karafun-touch (legacy) | <https://github.com/recisio/karafun-touch> |

---

## Third-Party API Clients

Several unofficial third-party clients exist but were not verified in this research:

- Python implementations
- C#/.NET wrappers
- Python-TUI (this project's focus)

**Unverified:** These would need separate verification against the API specification documented above.
