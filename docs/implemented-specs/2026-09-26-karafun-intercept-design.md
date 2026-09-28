# Karafun Intercept — Design Spec

> **Status:** Shipped — implemented per `docs/superpowers/plans/2026-09-26-karafun-intercept-plan.md`, merged via PR #1 (commit `f4c1dc1`) and finalized with CLI + cross-platform enhancements.
> **Goal:** A Textual TUI that observes the local KaraFun Player over its Player Control WebSocket API and tracks turn-taking, singers, and new-song activity.
> **Outcome:** 21 tests pass with `-W error` (1 live-player test skipped). All scope constraints (YAGNI) respected.

---

## 1. Overview & Goal

**Goal.** Provide a terminal dashboard that connects to a locally-running KaraFun Player (desktop) and tracks *social* state around the song queue: whose turn it is, everyone who has committed a song, notifications when a new user commits a song, and per-user recency ("last seen") to guess whether a user is still present.

**Data source.** The KaraFun Player Control API: a WebSocket server the desktop player hosts at `ws://localhost:57570/`. The protocol is XML-over-WebSocket (see `docs/research/karafun-api/02-api-reference.md`). It is undocumented/removed; live verification against the running player is required for the real-time behavior (see Open Questions).

**Non-goal.** The KaraFun Box API (REST, commercial/venue) is **out of scope**. No persistence, no remote/cloud, no music metadata enrichment beyond what the player emits.

---

## 2. Scope

### In scope (MVP)

- Connect to `ws://localhost:57570/` and stay connected (auto-reconnect).
- Observe current playback state + queue (who is playing / next / who queued each song).
- Track per-user `last_seen` and compute recency.
- Detect "new user committed a song" → notification.
- TUI: current song, queue view, singer roster with recency, notification banner.
- Graceful UI when the player is not running (show "connecting…").

### Out of scope (YAGNI)

- Playback *control* (play/pause/next/pitch/tempo/volume) — observe-only for now.
- Searching/browsing the full catalog from the TUI — only the live queue/status.
- Local persistence, configuration files, settings screens.
- The KaraFun Box (commercial) API, authentication, or remote playback.

---

## 3. Architecture

Single-process async Textual app. Five layers, each a focused module:

```
┌────────────────────────┐  ───reactive──►  Model
│ TUI (textual App)       │     events         │
├──────────────────▲─────┤                   │
│ CLI (karafun cmd)│     │                   │
├──────────────────┼─────┤                   │
│ KarafunClient     │ ws+XML events          │
│ (ws lifecycle)    │ ─────────────────┘     │
├──────────────────▲─────┤                   │
│ xml_proto (stdlib  │     │                   │
│  XML parse)        │ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘
└────────────────────┘
```

The CLI layer (`cli.py`) was added as a subsequent enhancement — it wraps the TUI launch and provides `karafun update` / `karafun branch-*` subcommands. It depends on the same layered modules below.

- **`xml_proto`** — pure functions: parse a `<status>`/`<list>`/`<catalogList>` blob into typed dataclasses; build outbound action XML strings. No I/O.
- **`KarafunClient`** — async WebSocket lifecycle: connect, reconnect with backoff, send actions (`<action type="getStatus">…</action>`), parse inbound XML via `xml_proto`, and emit typed events over an `async def events()` iterator the model subscribes to. Event dataclasses (defined alongside the other model dataclasses):

- `StatusUpdate(snapshot: StatusSnapshot)` — a normalized status/queue payload parsed by `xml_proto`.
- `Disconnected(reason: str)` — socket closed; the client auto-reconnects with backoff.
- `Error(message: str)` — non-fatal parse/transport error.

Exposes a small surface: `connect()`, `request_status()`, and the `events()` async iterator.

- **`SessionModel`** — holds all in-memory state (queue, singers, recencies, turn) and derives deltas/notifications. Pure logic — no I/O, no WebSocket, no Textual widgets. Emits `Notification` events to the UI.
- **TUI (`app.py`)** — a `textual.app.App` reacting to `SessionModel` events. Keeps UI rendering out of the model (PHILOSOPHY contract: logic in modules, rendering in the TUI layer).

The TUI drives the client: it instantiates `KarafunClient`, feeds events into `SessionModel`, and reacts to model notifications.

---

## 4. Observation Strategy (Approach C — hybrid)

The server *may* push `<status>` updates unsolicited, but this is unverified. The client is robust to both:

1. On connect, immediately send `<action type="getStatus"></action>` to seed state.
2. Keep a poll fallback: every `POLL_INTERVAL` seconds (default `2.0`), if no status has been received in the last `3s`, send a fresh `getStatus`. This guarantees correctness even if the server never pushes.
3. Treat **every** inbound `<status>` uniformly (solicited or unsolicited); deduplicate identical payloads by content so a push + a poll response don't double-count.
4. Any `<status>` → forward to `SessionModel.apply_status(...)`.

`POLL_INTERVAL` and the backoff ceiling are module constants. Reconnection on close/error uses exponential backoff starting at `5s`, capped at `30s`, jittered.

**Why not polling-only (B) or push-only (A):** live access exists to confirm push behavior; the hybrid is the only approach guaranteed correct against an undocumented server, and it degrades gracefully. This is the single architectural risk and the reason live verification matters.

---

## 5. XML Protocol (summary)

Inbound actions are `<action type="..."/>`. Responses are XML documents. Key shapes (full detail in the research doc):

**Status (server→client), drives all social tracking:**

```xml
<status state="playing">
  [<position>12</position>]
  <volumeList><general caption="General">80</general></volumeList>
  <pitch>0</pitch>
  <tempo>100</tempo>
  <queue>
    <item id="0" status="ready">
      <title>Song A</title>
      <artist>Artist A</artist>
      <year>2020</year>
      <duration>180</duration>
      <singer>Alice</singer>
    </item>
    ...
  </queue>
</status>
```

**Outbound action examples (observe-only MVP sends only `getStatus`):**

```xml
<action type="getStatus"></action>
```

**Catalog/list (for future catalog browsing — NOT in MVP):**

```xml
<catalogList>
  <catalog id="1" type="onlineComplete">My Catalog</catalog>
</catalogList>
<list total="2">
  <item id="42"><title>Song</title><artist>Artist</artist>...</item>
</list>
```

Parsing uses the stdlib `xml.etree.ElementTree`. Outgoing actions are plain XML strings (no escaping needed for `getStatus`). If search text is added later, escape `&`/`<`/`>` via `xml.sax.saxutils.escape`.

---

## 6. SessionModel — State & Delta Computation

**State (in-memory, mutated only via `apply_status`):**

- `current: StatusSnapshot` — `state` ∈ {`idle`, `infoscreen`, `loading`, `playing`}, `position` (optional seconds), `current_title`/`current_artist` from the playing item.
- `queue: list[QueueItem]` — ordered; each `QueueItem` = `{id, title, artist, year, duration, singer: Optional[str], item_state}`. The protocol's `id` is a positional index (0-based queue position), not a stable song id; if a stable song id ever appears, it can be added as an optional `song_id` without affecting turn/signer logic.
- `singer_last_seen: dict[str, datetime]` — `singer -> last time a status mentioned them in the queue`.
- `singer_first_seen: dict[str, datetime]` — for "how often it's their turn" / presence history.
- `known_singers: set[str]` — singers ever seen this session (drives new-user detection).

**Turn semantics:**

- `current player` = the singer of the queue item whose `item_state`/position aligns with currently-playing content; in the MVP, "it's X's turn" is approximated as: the singer of the front-of-queue item when `state == "playing"`, and "up next" = front-of-queue singer when not yet playing.
- Queue order = turn order.

**Delta / notification rules (computed on each new status):**

1. **New user committed a song:** any *present* `<singer>` now in the queue that is not in `known_singers` → emit `Notification(kind="new_singer", singer=..., timestamp=now)`; add to `known_singers` and both dicts. Absent/`None` singers (unassigned slots) are ignored — never counted as a new singer.
2. **Turn advanced:** front-of-queue `singer` changed since last status → emit `Notification(kind="turn", singer=..., timestamp=now)`.
3. **Recency:** on every status, update `singer_last_seen[singer] = now` for each singer present. UI shows `now - last_seen` per singer.
4. **Player not playing / idle:** no new notifications; roster still shows recencies.

`apply_status` returns a list of `Notification`s. Notifications carry a `kind`, the `singer`, and a `timestamp`, plus a human `message`. The TUI renders the most recent N (default 8) in the banner.

**Determinism for testing:** `apply_status` uses an injected `now` callable so tests are reproducible.

---

## 7. TUI Design

A single `App` with one screen (MVP; PHILOSPY key-binding discipline: footer derived from `_handle_*` method presence).

```
┌ KaraFun Intercept ────────────────────────────────────────────────────┐
│ Current: Song A — Artist A   ▶ playing  1:12/3:00   tempo 100%       │
├────────────────────────┬─────────────────────────────────────────────┤
│ QUEUE (turn order)     │ SINGERS (recency / presence)                │
│ 1. Song A — Alice ▶   │ ● Alice      now playing (2s ago)           │
│ 2. Song B — Bob       │ ● Bob        1m ago                         │
│ 3. Song C — Cara      │ ● Cara       4m ago                         │
│ ...                    │ ● Dan        12m ago (away?)                │
├────────────────────────┴─────────────────────────────────────────────┤
│ [NOTIFICATION] Alice queued "Song A" (new)                          │
│ [NOTIFICATION] It's now Bob's turn                                  │
├───────────────────────────────────────────────────────────────────────┤
│ [q] Quit   [r] Refresh   [↑/↓] Navigate                              │
└───────────────────────────────────────────────────────────────────────┘
```

Widgets (kept simple; YAGNI — no nested component tree):

- Header: app title.
- `Static` for the current-track header line.
- A vertical `TreeTable`-like or plain list widget for the queue (left).
- A plain list widget for the singer roster with recency (right). Use `rich`/`textual` styling; recency color-coded (e.g., dim for >10m "away?", base highlight for recent).
- A notification banner (`Static` or small `OptionsList`) showing last N notifications.
- Footer: dynamic key hints derived from base keymap.

**Keymap (base, Textual `BINDINGS`):**

- `("q", "quit", "Quit")`, `("escape", "quit", "Quit")`, `("r", "refresh", "Refresh")` — defined as Textual `Binding` objects in `BINDINGS`.
- Corresponding `action_quit` (Textual built-in) and `action_refresh` methods.
- Textual's `Footer` widget auto-renders `[q] Quit  [r] Refresh` from `BINDINGS`.

**Styling:** use the project-wide consistent terminal palette (one base highlight color via **bold**/**italic**/**dim** hierarchy; red only for error/notification emphasis). No theme module (inline only).

---

## 8. Error Handling & Connection Lifecycle

- **Player not running / connect refused:** show "Connecting to KaraFun Player…" and retry per backoff. Do not crash; keep UI responsive.
- **Parse error on inbound XML:** log the raw blob (DEBUG_VVV equivalent / `--log-xml`), drop the message, keep connection open. Do not propagate to crash the model.
- **Unexpected XML element/field:** ignore unknown fields (forward-compatible); known fields with missing children → sentinel/`None`.
- **Reconnection:** on socket close/error, back off (5s→30s, jittered) and reconnect; on (re)connect, re-seed with `getStatus`.
- **Graceful shutdown:** closing the app closes the WebSocket cleanly.

---

## 9. Dependencies & File Layout

**Runtime deps:** `textual` (TUI), stdlib `asyncio`, `xml.etree.ElementTree`, `websockets` (or stdlib `asyncio` streams — decide at impl; prefer `websockets` for robustness). `dataclasses`, `datetime`.

**Project layout:**

```
src/karafun_intercept/
├── __init__.py             # package marker, __version__
├── __main__.py             # python -m karafun_intercept -> cli.main()
├── app.py                  # Textual App + widgets + key handling
├── cli.py                  # karafun CLI: intercept / update / branch-* / version
├── client.py               # KarafunClient (WS lifecycle + events)
├── model.py                # SessionModel, dataclasses, Notification
├── xml_proto.py            # XML parse + action builders (pure)
└── _version.py             # __version__ = "0.1.0"
tests/
├── conftest.py             # fixtures: fake clock, recorded XML fragments
├── test_xml_proto.py       # Task 1
├── test_client.py          # Task 2 (fake transport)
├── test_model.py           # Task 3 (deterministic now)
├── test_app.py             # Task 4 (textual pilot)
└── test_integration.py     # Task 5 (client→model pipeline)
scripts/
├── install.sh              # POSIX one-liner (curl … | sh)
└── install.ps1             # PowerShell one-liner (irm … | iex)
```

**Granularity:** implement modules in dependency order (`xml_proto` → `client` → `model` → `app`), each with tests, each commit self-contained.

**Entry points:** `python -m karafun_intercept` (CLI dispatcher) and console scripts `karafun-intercept = "karafun_intercept.app:main"` and `karafun = "karafun_intercept.cli:main"`.

**Cross-platform:** ported to Windows + Linux per `docs/superpowers/specs/2026-09-28-cross-platform-windows-port-design.md` — PowerShell install one-liner, CI matrix on Ubuntu + Windows, Contract 12 encoded in PHILOSOPHY.md.

---

## 10. Testing Strategy

- **Pure:** `test_xml_proto.py` (parse each response shape; build `getStatus` action), `test_model.py` (feed recorded `<status>` sequences; assert notification set, recencies, turn detection; deterministic `now`). All `-W error`.
- **Transport:** `test_client.py` uses a fake async transport that replays recorded XML fragments captured against the live player; asserts `getStatus` is sent on connect and that inbound statuses are forwarded as events.
- **TUI (pilot):** `test_app.py` — construct the `App` with an injected `SessionModel`/`KarafunClient` double, drive the model with a recorded status, and assert the queue/signer/notification widgets render the expected values.
- **Integration:** `test_integration.py` — hermetic client→model pipeline test driving a `FakeFactory`-fed `KarafunClient` into a real `SessionModel`, asserting `NewSinger`/`TurnAdvanced` deltas. Live-player test skipped pending a running player.
- **Live verification step:** against the running player, capture a few real `<status>` samples (save under `tests/fixtures/`) to confirm field shapes (especially whether `<singer>` is always present and whether unsolicited `<status>` pushes occur).

**Final test results:** `pytest -W error` → **21 passed, 1 skipped** (live-player test). `ruff check src tests` → all checks passed.

---

## 11. Open Questions (live-player verification needed)

1. Does the player push `<status>` unsolicited, or only in response to actions? (Drives how aggressive the poll fallback must be.)
2. Is `<singer>` reliably populated in `<queue><item>`? (Core to all tracking; the research marked this unverified.)
3. What exact `state` values occur, and does `position` update during playback?
4. Are `<catalogList>`/`<list>` responses available without an account, or player-local only? (Future catalog browsing.)

These are verified against your live player during implementation (Open Question → resolved in code), not blocked here.

---

## 12. PHILOSOPHY Contract Compliance (mapped)

- **Key Binding Discipline:** Textual `BINDINGS` with `action_*` handlers; one key per action; `q`+`escape` pair exempted.
- **Flat config / logging levels:** no config files; `logging.basicConfig` at INFO for the TUI.
- **YAGNI:** see scope section â observe-only, no playback control, no catalog browsing, no persistence.
- **Cross-Platform (Contract 12):** `pathlib.Path` for all paths; `subprocess.run` with explicit arg lists (no `shell=True`); PowerShell + POSIX install one-liners; CI matrix on Ubuntu + Windows.

---

## 13. Implementation Summary

**Shipped:** Implemented per the plan in `docs/superpowers/plans/2026-09-26-karafun-intercept-plan.md`, merged via PR #1 (first merge commit `f4c1dc1`) on `master`.

**Commits (by Task):**

| Commit | Task |
| --- | --- |
| `0c5df65` | Task 1: `xml_proto` â XML parsing + action builders + `_version.py` + `__init__.py` exports |
| `bfb51d3` | Task 2 dep: `websockets>=12` in `pyproject.toml` |
| `174756d` | Task 2: `client.py` â KarafunClient (Approach C lifecycle) |
| `205f06b` | Task 3: `model.py` â SessionModel with recency + notifications |
| `64eb4a9` | Task 4: `app.py` â Textual TUI (queue/singers/notifications) |
| `c30b1ea` | Task 5: `test_integration.py` â end-to-end clientâ'îModel pipeline |
| `1745777` | CLI: `karafun` command with intercept/update/branch subcommands |
| `aada57a` | Refactor: type-clean bindings, public-repo (no GH_TOKEN) update |
| `20fc59b` | Cross-platform: PowerShell install + CI matrix (PR #2) |

**Files created:** `xml_proto.py`, `client.py`, `model.py`, `app.py` (rewrite), `__main__.py`, `cli.py`, `_version.py`, `conftest.py`, `test_xml_proto.py`, `test_model.py`, `test_client.py`, `test_app.py`, `test_integration.py`, `scripts/install.sh`, `scripts/install.ps1`, `.github/workflows/ci.yml`.

**Files modified:** `__init__.py`, `pyproject.toml`, `README.md`, `AGENTS.md`, `PHILOSOPHY.md`, `.gitignore`.

**Tests:** 21 passed, 1 skipped (`pytest -W error` â live-player test). `ruff check src tests`: all checks passed.

**Deviations from plan:** None. All 5 tasks executed exactly as documented.
