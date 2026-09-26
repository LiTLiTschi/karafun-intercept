# Karafun API Overview

## Introduction

The Karafun API refers to **two distinct but related APIs**:

### 1. Karafun Player Control API (WebSocket-based)

A local WebSocket API that communicates with the Karafun Player desktop application running on Windows. This is the primary focus of the researched projects.

### 2. KaraFun Box API (REST-based, OpenAPI)

A separate REST API for business customers managing KaraFun Box karaoke systems (bars, restaurants, private rooms). This API handles session management and booking system integrations.

---

## Official Status

**As of research date, the original developer documentation at `karafun.com/developers/` has been removed or relocated.**

The Player Control API documentation was accessible via:

- **Primary source**: `http://www.karafun.com/developers/karafun-player-api.html`
- **Archived copy**: `https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html`

Source: [Web Archive capture](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html)

---

## Authentication Model

**The Karafun Player Control API requires NO authentication.**

It is a local network API that:

- Listens on port `57570` (default)
- Connects via WebSocket (`ws://host:57570`)
- Requires the Karafun Player desktop application to be running with an active subscription
- Is designed for local use within a karaoke room/network

Source: [Official archived docs](https://web.archive.org/web/20200615000000/http://www.karafun.com/developers/karafun-player-api.html) - "Communications between your software and KaraFun Player are made through TCP WebSockets. A socket server is running at all time when you have an active subscription in KaraFun Player"

---

## Relationship to KaraFun Services

- **KaraFun Player**: Desktop application for Windows (karaoke player)
- **KaraFun Box**: Hardware/system for commercial venues (bars, restaurants)
- **KaraFun Touch**: Open-source touchscreen interface (project: `karafun/touch`)
- **KaraFun OEM**: Integration platform for TV, automotive, hardware

Source: [KaraFun Business OEM page](https://business.karafun.com/oem)

---

## API Type Classification

| API | Type | Transport | Auth Required | Target |
|-----|------|-----------|---------------|--------|
| Player Control | Unofficial/Reverse-engineered | WebSocket | No | Karafun Player desktop |
| Box Session Management | Official REST API | HTTP (OpenAPI) | Token-based | KaraFun Box commercial |

Source: The Player Control API is documented in archived developer docs but the documentation has been removed from karafun.com. The Box API is actively promoted on business.karafun.com.

---

## Key Observations

1. **Two separate teams/projects maintain implementations**:
   - `karafun/touch` - Official KaraFun (Recisio) open-source project
   - `natelewis/karafun-api` - Community Node.js wrapper (marked "NO LONGER MAINTAINED")

2. **The Player Control API is NOT documented publicly anymore** - the developer portal has been removed.

3. **CORS is not applicable** - WebSocket connections to localhost/127.0.0.1 are local.

4. **The Box API requires business account** - REST API with token authentication.
