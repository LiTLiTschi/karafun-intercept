# Karafun Intercept Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Textual TUI dashboard (`karafun-intercept`) that observes the local KaraFun Player over its Player Control WebSocket (`ws://localhost:57570`), parses XML status updates, and tracks turn order, singers, new-song notifications, and per-user recency/presence — implemented bottom-up with TDD (xml_proto → client → model → app).

**Architecture:** Single-process async Textual app in four strict, non-circular layers: `xml_proto` (pure stdlib XML parsing + action builders) → `KarafunClient` (async WebSocket lifecycle + typed events) → `SessionModel` (pure in-memory state; computes turns/singer-recency/notifications) → TUI `App` (Textual widgets; reacts to model events). Approach C (hybrid): seed with `getStatus`, listen for server pushes, fall back to periodic polling.

**Tech Stack:** Python 3.14, `textual`, `websockets`, stdlib `abc`/asyncio/`dataclasses`/`datetime`/`xml.etree.ElementTree`; `pytest` with `-W error`; `ruff`. Async test transport for the client; Textual pilot for the UI.

**Roadmap:** None (single-plan MVP — see spec `docs/superpowers/specs/2026-09-26-karafun-intercept-design.md`).

**Phase:** Single-plan implementation.

---

## Files created/modified

```
src/karafun_intercept/
├── __init__.py          # package marker, __version__
├── __main__.py          # (Task 4) python -m karafun_intercept -> main()
├── xml_proto.py         # (Task 1) pure XML parse + action builders + dataclasses
├── client.py            # (Task 2) KarafunClient (ws lifecycle + events)
├── model.py             # (Task 3) SessionModel + Notification + event dataclasses
├── app.py               # (Task 4) Textual App + widgets + key handling (mostly already scaffolded)
└── _version.py          # __version__ = "0.1.0"
tests/
├── conftest.py          # shared fixtures: fake clock, recorded XML fragments
├── test_xml_proto.py    # Task 1 tests
├── test_model.py        # Task 3 tests
├── test_client.py       # Task 2 tests (fake transport)
└── test_app.py          # Task 4 tests (textual pilot)
tests/fixtures/status1.xml   # (Task 5) captured live samples
tests/fixtures/...
```

`app.py` and `__init__.py`/`pyproject.toml` already exist (scaffold commit). This plan replaces/supplements `app.py`'s body; everything else is new. All steps use `pytest ... -W error` and `ruff check src tests`.

---

## Shared fixtures (used across tasks)

`tests/conftest.py` (created in Task 1, extended in Task 3):

```python
import datetime as dt

import pytest


@pytest.fixture
def fake_now():
    """Deterministic clock; advance via monkeypatching this callable if needed."""
    base = dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc)
    state = {"t": base}

    def now():
        return state["t"]

    def _advance(delta: dt.timedelta):
        state["t"] = state["t"] + delta

    now.advance = _advance  # type: ignore[attr-defined]
    now.base = base  # type: ignore[attr-defined]
    return now


# Recorded XML fragments captured against the live player (see Open Question 11).
STATUS1_XML = """\
<status state="playing">
  <position>12</position>
  <volumeList><general caption="General">80</general></volumeList>
  <pitch>0</pitch>
  <tempo>100</tempo>
  <queue>
    <item id="0" status="ready">
      <title>Song A</title> <artist>Artist A</artist>
      <year>2020</year> <duration>180</duration>
      <singer>Alice</singer>
    </item>
    <item id="1" status="ready">
      <title>Song B</title> <artist>Artist B</artist>
      <year>2019</year> <duration>200</duration>
      <singer>Bob</singer>
    </item>
  </queue>
</status>"""

STATUS2_XML = """\
<status state="playing">
  <position>20</position>
  <pitch>0</pitch>
  <tempo>100</tempo>
  <queue>
    <item id="0" status="ready">
      <title>Song B</title> <artist>Artist B</artist>
      <year>2019</year> <duration>200</duration>
      <singer>Bob</singer>
    </item>
    <item id="1" status="ready">
      <title>Song C</title> <artist>Artist C</artist>
      <year>2021</year> <duration>190</duration>
      <singer>Cara</singer>
    </item>
  </queue>
</status>
"""


@pytest.fixture
def status1_xml():
    return STATUS1_XML


@pytest.fixture
def status2_xml():
    return STATUS2_XML
```

> Note: per the "No Placeholders" rule, these fixtures contain real, runnable content. `STATUS1_XML`/`STATUS2_XML` are synthetic but spec-faithful fragments (matching the shapes in `docs/research/karafun-api/02-api-reference.md`); real captured samples from your live player will replace/augment them in Task 5.

---

## Constants (single source of truth, defined in `xml_proto.py` and imported elsewhere)

```python
# src/karafun_intercept/xml_proto.py
PLAYER_HOST = "localhost"
PLAYER_PORT = 57570

# Observation: Approach C hybrid.
POLL_INTERVAL = 2.0        # seconds
POLL_TIMEOUT_GAP = 3.0     # seconds with no status -> force a getStatus
RECONNECT_MIN_DELAY = 5.0  # exponential backoff start
RECONNECT_MAX_DELAY = 30.0
```

---

### Task 1: `xml_proto` — parsing & action building (foundation, no deps)

**Files:**

- Create: `src/karafun_intercept/xml_proto.py`
- Create: `src/karafun_intercept/_version.py` (used by `__init__`)
- Modify: `src/karafun_intercept/__init__.py` (import/export `__version__`)
- Create: `tests/conftest.py`
- Create: `tests/test_xml_proto.py`

This task is pure (stdlib only) so it can be fully TDD'd in isolation and forms the contract the rest builds on.

- [ ] **Step 1: Write failing tests** (`tests/test_xml_proto.py`):

```python
from karafun_intercept.xml_proto import (
    parse_status,
    build_get_status_action,
    PLAYER_HOST,
    PLAYER_PORT,
    POLL_INTERVAL,
)


def test_parse_status_basic(status1_xml):
    s = parse_status(status1_xml)
    assert s.state == "playing"
    assert s.position == 12
    assert s.pitch == 0
    assert s.tempo == 100
    assert len(s.queue) == 2
    first = s.queue[0]
    assert first.id == 0
    assert first.title == "Song A"
    assert first.artist == "Artist A"
    assert first.year == 2020
    assert first.duration == 180
    assert first.singer == "Alice"
    assert first.item_state == "ready"


def test_parse_status_optional_fields():
    # No <position>/<pitch>/<tempo> in this fragment -> all optional/None.
    xml = (
        '<status state="playing">'
        '<queue>'
        '<item id="0" status="ready">'
        '<title>Only</title><artist>Uno</artist><singer>Alice</singer>'
        '</item>'
        '</queue></status>'
    )
    s = parse_status(xml)
    assert s.position is None
    assert s.pitch is None
    assert s.tempo is None
    assert len(s.queue) == 1
    assert s.queue[0].singer == "Alice"


def test_parse_status_singer_absent_when_missing():
    s = parse_status("<status state=\"idle\"><queue></queue></status>")
    assert s.state == "idle"
    assert s.queue == []


def test_build_get_status_action_has_no_queue():
    xml = build_get_status_action(noqueue=False)
    assert xml == "<action type=\"getStatus\"></action>"


def test_build_get_status_action_noqueue():
    xml = build_get_status_action(noqueue=True)
    assert xml == "<action type=\"getStatus\" noqueue></action>"


def test_constants():
    from karafun_intercept.xml_proto import (
        PLAYER_HOST, PLAYER_PORT, POLL_INTERVAL,
        RECONNECT_MIN_DELAY, RECONNECT_MAX_DELAY,
    )
    assert PLAYER_HOST == "localhost"
    assert PLAYER_PORT == 57570
    assert POLL_INTERVAL == 2.0
```

- [ ] **Step 2: Run tests, verify FAIL** (`ModuleNotFoundError: No module named 'karafun_intercept.xml_proto'`).

Run: `pytest tests/test_xml_proto.py -v`
Expected: FAIL — module not importable.

- [ ] **Step 3: Write minimal implementation** (`src/karafun_intercept/xml_proto.py`):

```python
"""XML protocol parsing and action builders for the KaraFun Player Control API.

Pure: stdlib only, no I/O. Forms the boundary between the WebSocket
transport (client.py) and the in-memory model (model.py).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

# --- Network / observation constants (single source of truth) ---
PLAYER_HOST = "localhost"
PLAYER_PORT = 57570

POLL_INTERVAL = 2.0
POLL_TIMEOUT_GAP = 3.0
RECONNECT_MIN_DELAY = 5.0
RECONNECT_MAX_DELAY = 30.0


@dataclass(frozen=True)
class QueueItem:
    """One entry in the player's queue.

    `id` is the protocol's positional queue index (0-based), not a stable
    song id (see spec §6). `singer` is Optional because the protocol omits
    it for unassigned slots.
    """

    id: int
    title: str
    artist: str
    year: Optional[int]
    duration: Optional[int]
    singer: Optional[str]
    item_state: str


@dataclass(frozen=True)
class StatusSnapshot:
    """Normalized, in-memory view of a <status> response."""

    state: str
    position: Optional[int]
    pitch: Optional[int]
    tempo: Optional[int]
    queue: list[QueueItem] = field(default_factory=list)


def _text(elem: Optional[ET.Element]) -> Optional[str]:
    """Return stripped text of *elem*, or None if absent/empty."""
    if elem is None or (elem.text or "").strip() == "":
        return None
    return elem.text.strip()


def _to_int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_queue_item(item: ET.Element) -> QueueItem:
    return QueueItem(
        id=int(item.get("id", "0")),
        title=_text(item.find("title")) or "",
        artist=_text(item.find("artist")) or "",
        year=_to_int(_text(item.find("year"))),
        duration=_to_int(_text(item.find("duration"))),
        singer=_text(item.find("singer")),
        item_state=item.get("status", ""),
    )


def parse_status(xml_text: str) -> StatusSnapshot:
    root = ET.fromstring(xml_text)
    assert root.tag == "status", f"expected <status>, got <{root.tag}>"
    return StatusSnapshot(
        state=root.get("state", "idle"),
        position=_to_int(_text(root.find("position"))),
        pitch=_to_int(_text(root.find("pitch"))),
        tempo=_to_int(_text(root.find("tempo"))),
        queue=[
            parse_queue_item(item)
            for item in root.findall(".//queue/item")
        ],
    )


def build_get_status_action(noqueue: bool = False) -> str:
    if noqueue:
        return "<action type=\"getStatus\" noqueue></action>"
    return "<action type=\"getStatus\"></action>"
```

And `_version.py`:

```python
__version__ = "0.1.0"
```

Update `src/karafun_intercept/__init__.py` (the existing one) to:

```python
"""Karafun Intercept — observe the local KaraFun Player in a TUI."""

from karafun_intercept._version import __version__

__all__ = ["__version__"]
```

- [ ] **Step 4: Run tests, verify PASS.**

Run: `pytest tests/test_xml_proto.py -v -W error`
Expected: all PASS.

- [ ] **Step 5: Lint.**

Run: `ruff check src/karafun_intercept/xml_proto.py tests/test_xml_proto.py tests/conftest.py`
Expected: `All checks passed!`

- [ ] **Step 6: Commit.**

```bash
git add src/karafun_intercept/xml_proto.py src/karafun_intercept/_version.py \
        src/karafun_intercept/__init__.py tests/conftest.py tests/test_xml_proto.py
git commit -m "feat: add XML protocol parsing & action builders (xml_proto) with tests"
```

---

### Task 2: `client.py` — `KarafunClient` (WS lifecycle, Approach C, injectable transport)

**Files:**

- Create: `src/karafun_intercept/client.py`
- Modify: `pyproject.toml` (add runtime dep `websockets>=12`)

Defines the typed event stream consumed by `model` and `app`: `StatusUpdate(snapshot: StatusSnapshot)`, `Disconnected(reason)`, `Error(message)`. Connection lifecycle: seed a full `getStatus` on connect -> read messages -> parse -> emit; on close, emit `Disconnected` and reconnect with exponential backoff; a poll task forces a no-queue `getStatus` when the server has been silent for `POLL_TIMEOUT_GAP`. Transport is abstracted behind a `Transport` ABC so tests never touch the network.

- [ ] **Step 0: Env.** Add `websockets>=12` to `pyproject.toml` `dependencies`:

  ```toml
  dependencies = ["textual>=0.85", "websockets>=12"]
  ```

  Then: `uv pip install -e .` (resolves `websockets` into `.venv`). Verify: `python -c "import websockets"`.

- [ ] **Step 1: Write failing tests** (`tests/test_client.py`) — hermetic, driven via `asyncio.run` (no `pytest-asyncio` needed):

```python
import asyncio
from karafun_intercept.client import (
    KarafunClient,
    StatusUpdate,
    Disconnected,
    Error,
)
from karafun_intercept.xml_proto import build_get_status_action


class FakeTransport:
    """In-memory transport: replays scripted messages, records sends."""

    def __init__(self, messages, block_when_empty=False):
        self._messages = list(messages)
        self._block_when_empty = block_when_empty
        self.sent = []
        self.closed = False

    async def send(self, data):
        self.sent.append(data)

    async def recv(self):
        if self._messages:
            return self._messages.pop(0)
        if self._block_when_empty:
            await asyncio.sleep(100)  # simulate a silent server
        return ""

    async def close(self):
        self.closed = True


class FakeFactory:
    """Yields one FakeTransport per connection attempt (reconnect-aware)."""

    def __init__(self, connections, block_when_empty=False):
        self._connections = list(connections)
        self._block_when_empty = block_when_empty
        self.calls = 0
        self.transports = []

    async def __call__(self):
        self.calls += 1
        msgs = self._connections[
            min(self.calls - 1, len(self._connections) - 1)
        ]
        t = FakeTransport(msgs, block_when_empty=self._block_when_empty)
        self.transports.append(t)
        return t


def _collect(client, predicate, timeout=0.5):
    """Drive client.events() until *predicate(events)* is True or timeout."""
    collected = []

    async def main():
        async for ev in client.events():
            collected.append(ev)
            if predicate(collected):
                return

    try:
        asyncio.run(asyncio.wait_for(main(), timeout))
    except asyncio.TimeoutError:
        pass
    return collected


def _client(factory, **kw):
    defaults = dict(
        reconnect_min_delay=0.0,
        reconnect_max_delay=0.0,
        poll_interval=100,
        poll_timeout_gap=100,
    )
    defaults.update(kw)
    return KarafunClient(transport_factory=factory, **defaults)


def test_seeds_get_status_and_emits_status_update(status1_xml):
    factory = FakeFactory([[status1_xml]])
    client = _client(factory)
    events = _collect(client, lambda es: isinstance(es[-1], StatusUpdate))
    assert isinstance(events[-1], StatusUpdate)
    assert events[-1].snapshot.queue[0].title == "Song A"
    assert factory.transports[0].sent[0] == build_get_status_action()


def test_emits_error_on_malformed_xml():
    factory = FakeFactory([["<status broken"]])
    client = _client(factory)
    events = _collect(client, lambda es: isinstance(es[-1], Error))
    assert isinstance(events[-1], Error)
    assert "parse" in events[-1].message.lower()


def test_disconnect_then_reconnect_emits_status(status1_xml):
    factory = FakeFactory([
        [],            # connection 1 closes immediately -> Disconnected
        [status1_xml], # connection 2 delivers a status
    ])
    client = _client(factory)

    def got_both(es):
        return (
            any(isinstance(e, Disconnected) for e in es)
            and isinstance(es[-1], StatusUpdate)
        )

    events = _collect(client, got_both)
    assert factory.calls == 2
    assert isinstance(events[0], Disconnected)
    assert isinstance(events[-1], StatusUpdate)


def test_poll_fallback_sends_noqueue_when_silent(status1_xml):
    # recv blocks forever (silent server); poll task must re-seed.
    factory = FakeFactory([[]], block_when_empty=True)
    client = _client(factory, poll_interval=0.01, poll_timeout_gap=0.02)
    _collect(client, lambda _: False, timeout=0.1)
    sent = factory.transports[0].sent
    assert build_get_status_action() == sent[0]          # seed (full)
    assert build_get_status_action(noqueue=True) in sent  # poll fallback
```

- [ ] **Step 2: Run tests, verify FAIL** (`ModuleNotFoundError: No module named 'karafun_intercept.client'`).

Run: `pytest tests/test_client.py -v`
Expected: FAIL — `client.py` not yet created.

- [ ] **Step 3: Write minimal implementation** (`src/karafun_intercept/client.py`):

```python
"""WebSocket client for the KaraFun Player Control API.

Approach C: seed a full `getStatus` on connect, consume server pushes, and
periodically re-seed (no-queue) when the server goes silent. Typed events
flow up to model.py / app.py. Parsing is delegated to xml_proto.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import AsyncIterator, Awaitable, Callable, Optional

from karafun_intercept.xml_proto import (
    PLAYER_HOST,
    PLAYER_PORT,
    POLL_INTERVAL,
    POLL_TIMEOUT_GAP,
    RECONNECT_MAX_DELAY,
    RECONNECT_MIN_DELAY,
    StatusSnapshot,
    build_get_status_action,
    parse_status,
)

_log = logging.getLogger(__name__)


# --- Events ---------------------------------------------------------------
@dataclass
class StatusUpdate:
    snapshot: StatusSnapshot


@dataclass
class Disconnected:
    reason: str = ""


@dataclass
class Error:
    message: str


# --- Transport abstraction -------------------------------------------------
class Transport:
    """Minimal async send/recv facade over a WebSocket stream."""

    async def send(self, data: str) -> None:
        raise NotImplementedError

    async def recv(self) -> Optional[str]:
        raise NotImplementedError  # None / "" => closed

    async def close(self) -> None:
        raise NotImplementedError

    async def __aenter__(self) -> "Transport":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()


class WebSocketTransport(Transport):
    def __init__(self, ws):
        self._ws = ws

    async def send(self, data: str) -> None:
        await self._ws.send(data)

    async def recv(self) -> Optional[str]:
        try:
            msg = await self._ws.recv()
        except Exception as e:  # websockets.ConnectionClosed, etc.
            _log.debug("recv closed: %s", e)
            return None
        if isinstance(msg, bytes):
            return msg.decode("utf-8", "replace")
        return msg

    async def close(self) -> None:
        with contextlib.suppress(Exception):
            await self._ws.close()


async def _connect_websocket(host: str, port: int) -> Transport:
    import websockets

    uri = f"ws://{host}:{port}/"
    ws = await websockets.connect(uri)
    return WebSocketTransport(ws)


# --- Client ---------------------------------------------------------------
class KarafunClient:
    """Observe the local KaraFun player over WebSocket.

    `events` is an async generator yielding StatusUpdate / Disconnected /
    Error. Inject a `transport_factory` for hermetic tests.
    """

    def __init__(
        self,
        host: str = PLAYER_HOST,
        port: int = PLAYER_PORT,
        *,
        transport_factory: Optional[Callable[[], Awaitable[Transport]]] = None,
        poll_interval: float = POLL_INTERVAL,
        poll_timeout_gap: float = POLL_TIMEOUT_GAP,
        reconnect_min_delay: float = RECONNECT_MIN_DELAY,
        reconnect_max_delay: float = RECONNECT_MAX_DELAY,
    ):
        if transport_factory is not None:
            self._transport_factory = transport_factory
        else:
            self._transport_factory = lambda: _connect_websocket(host, port)
        self._poll_interval = poll_interval
        self._poll_timeout_gap = poll_timeout_gap
        self._reconnect_min = reconnect_min_delay
        self._reconnect_max = reconnect_max_delay
        self._last_status_time: Optional[float] = None

    @staticmethod
    def _now() -> float:
        return time.monotonic()

    async def _poll_loop(self, transport: Transport) -> None:
        """Force a no-queue getStatus when the server has been silent."""
        while True:
            await asyncio.sleep(self._poll_interval)
            last = self._last_status_time
            if last is not None and (self._now() - last) > self._poll_timeout_gap:
                try:
                    await transport.send(build_get_status_action(noqueue=True))
                except OSError as e:
                    _log.warning("poll send failed: %s", e)

    def _dispatch(self, raw: str) -> Optional[object]:
        if not raw.lstrip().startswith("<status"):
            return None  # action ack / unknown frame: ignore
        try:
            snapshot = parse_status(raw)
        except ET.ParseError as e:
            _log.warning("parse error: %r", raw[:120])
            return Error(message=f"parse error: {e}")
        return StatusUpdate(snapshot=snapshot)

    async def events(self) -> AsyncIterator[object]:
        backoff = self._reconnect_min
        while True:
            try:
                transport = await self._transport_factory()
            except OSError as e:
                yield Error(message=f"connect failed: {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self._reconnect_max)
                continue
            backoff = self._reconnect_min
            poll = asyncio.create_task(self._poll_loop(transport))
            try:
                async with transport:
                    await transport.send(build_get_status_action())  # seed
                    self._last_status_time = self._now()
                    while True:
                        raw = await transport.recv()
                        if not raw:
                            yield Disconnected(reason="closed")
                            break
                        event = self._dispatch(raw)
                        if event is not None:
                            if isinstance(event, StatusUpdate):
                                self._last_status_time = self._now()
                            yield event
            except OSError as e:
                yield Disconnected(reason=f"io error: {e}")
            finally:
                poll.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await poll
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self._reconnect_max)


def main() -> None:
    """Smoke entry: stream events to logging (manual testing only)."""
    logging.basicConfig(level=logging.INFO)
    client = KarafunClient()
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_consume(client))


async def _consume(client: KarafunClient) -> None:
    async for ev in client.events():
        _log.info("%s", ev)
```

- [ ] **Step 4: Run tests, verify PASS.**

Run: `pytest tests/test_client.py -v -W error`
Expected: all 4 PASS.

- [ ] **Step 5: Lint.**

Run: `ruff check src/karafun_intercept/client.py tests/test_client.py`
Expected: `All checks passed!`

- [ ] **Step 6: Commit.**

```bash
git add src/karafun_intercept/client.py pyproject.toml tests/test_client.py
git commit -m "feat: add WebSocket KaraFunClient with Approach C lifecycle & tests"
```

---

### Task 3: `model.py` — `SessionModel` (state deltas, notifications, recency)

**Files:**

- Create: `src/karafun_intercept/model.py`
- Create: `tests/test_model.py`

Synchronous, pure, fully unit-testable: `SessionModel.apply_status(snapshot: StatusSnapshot) -> list[Notification]`. Spec §6-aligned: state is `current: StatusSnapshot`; recency is `singer_last_seen: dict[str, datetime]` / `singer_first_seen` / `known_singers: set[str]`; `apply_status` takes an injected `now` callable (deterministic tests). Notification vocabulary matches spec §6 rule set: `NewSinger(singer, timestamp, message)` (a singer now in the queue, not previously known) and `TurnAdvanced(singer, timestamp, message)` (front-of-queue singer changed). Per spec §6 rule 4, idle produces **no** notification (the roster still retains recencies). Absent/`None` singers are never counted (spec rule 1). No I/O; depends only on `xml_proto`.

- [ ] **Step 1: Write failing tests** (`tests/test_model.py`):

```python
from karafun_intercept.xml_proto import parse_status
from karafun_intercept.model import (
    SessionModel,
    NewSinger,
    TurnAdvanced,
)


def _idle_status():
    return parse_status('<status state="idle"><queue></queue></status>')


def _kinds(notes):
    """Order-independent check of notification (kind, singer), ignoring timestamps."""
    return [(type(n).__name__, n.singer) for n in notes]


def test_first_status_emits_new_singers_and_turn(status1_xml):
    m = SessionModel()
    notes = m.apply_status(parse_status(status1_xml))
    assert _kinds(notes) == [
        ("NewSinger", "Alice"),
        ("NewSinger", "Bob"),
        ("TurnAdvanced", "Alice"),
    ]
    assert m.current_singer == "Alice"
    assert m.current_song == ("Song A", "Artist A")
    assert m.position == 12
    assert m.queue[0].title == "Song A"
    assert m.known_singers == {"Alice", "Bob"}
    assert m.state == "playing"
    assert m.tempo == 100


def test_second_status_emits_new_singer_and_turn(status1_xml, status2_xml):
    m = SessionModel()
    m.apply_status(parse_status(status1_xml))
    notes = m.apply_status(parse_status(status2_xml))
    # Bob already known; Cara is new. Front moves Alice -> Bob.
    assert _kinds(notes) == [
        ("NewSinger", "Cara"),
        ("TurnAdvanced", "Bob"),
    ]
    assert m.current_singer == "Bob"
    assert m.current_song == ("Song B", "Artist B")


def test_no_change_is_silent(status1_xml):
    m = SessionModel()
    m.apply_status(parse_status(status1_xml))
    # Same status again: all singers known, front unchanged -> no notifications.
    assert m.apply_status(parse_status(status1_xml)) == []


def test_singer_recency_tracks_all_singers(status1_xml, status2_xml):
    m = SessionModel()
    m.apply_status(parse_status(status1_xml))
    m.apply_status(parse_status(status2_xml))
    assert set(m.singer_recency) == {"Alice", "Bob", "Cara"}
    assert m.current_singer == "Bob"


def test_idle_yields_no_notification(status1_xml):
    m = SessionModel()
    m.apply_status(parse_status(status1_xml))
    notes = m.apply_status(_idle_status())
    assert notes == []                       # spec §6 rule 4
    assert m.state == "idle"
    assert m.current_singer is None
    # recencies are retained (roster still shows them)
    assert {"Alice", "Bob"} <= set(m.singer_recency)


def test_absent_singer_not_counted():
    # An unassigned slot (no <singer>) is ignored entirely.
    xml = (
        '<status state="playing"><queue>'
        '<item id="0" status="ready"><title>T</title><artist>A</artist></item>'
        '</queue></status>'
    )
    m = SessionModel()
    notes = m.apply_status(parse_status(xml))
    assert notes == []
    assert m.current_singer is None
    assert m.known_singers == set()
    assert m.singer_recency == []
```

- [ ] **Step 2: Run tests, verify FAIL** (`ModuleNotFoundError: No module named 'karafun_intercept.model'`).

Run: `pytest tests/test_model.py -v`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation** (`src/karafun_intercept/model.py`):

```python
"""Session model: normalize StatusSnapshots into notifications + view state.

Spec §6 contract: `current` snapshot + recency dicts (`singer_last_seen` /
`singer_first_seen` keyed by `datetime`) + `known_singers`. Delta rules:
  1. a singer newly present in the queue -> NewSinger
  2. front-of-queue singer changed       -> TurnAdvanced
  3. every status updates last_seen for present singers
  4. idle -> no notification (roster retains recencies)
`now` is injected so tests are reproducible. No I/O; only depends on xml_proto.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from karafun_intercept.xml_proto import QueueItem, StatusSnapshot


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class NewSinger:
    singer: str
    timestamp: datetime
    message: str


@dataclass(frozen=True)
class TurnAdvanced:
    singer: str
    timestamp: datetime
    message: str


Notification = NewSinger | TurnAdvanced


class SessionModel:
    """Stateful observer of KaraFun player status (spec §6)."""

    def __init__(
        self,
        *,
        now: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._now = now
        self._current: Optional[StatusSnapshot] = None
        self.singer_last_seen: dict[str, datetime] = {}
        self.singer_first_seen: dict[str, datetime] = {}
        self.known_singers: set[str] = set()
        self._front_singer: Optional[str] = None

    @property
    def state(self) -> str:
        return self._current.state if self._current else "idle"

    @property
    def position(self) -> Optional[int]:
        return self._current.position if self._current else None

    @property
    def tempo(self) -> Optional[int]:
        return self._current.tempo if self._current else None

    @property
    def queue(self) -> list[QueueItem]:
        return list(self._current.queue) if self._current else []

    @property
    def current_song(self) -> Optional[tuple[str, str]]:
        if self._current and self._current.queue:
            item = self._current.queue[0]
            return (item.title, item.artist)
        return None

    @property
    def current_singer(self) -> Optional[str]:
        if self._current and self._current.queue:
            return self._current.queue[0].singer
        return None

    def singer_recency(self) -> list[str]:
        """Singers ordered most-recent-first by last seen."""
        return [
            s for s, _ in sorted(
                self.singer_last_seen.items(), key=lambda kv: kv[1], reverse=True
            )
        ]

    def apply_status(self, snapshot: StatusSnapshot) -> list[Notification]:
        now = self._now()
        notes: list[Notification] = []
        self._current = snapshot

        present = [q.singer for q in snapshot.queue if q.singer]
        for s in present:
            if s not in self.known_singers:
                # spec rule 1: new user committed a song -> NewSinger
                self.known_singers.add(s)
                self.singer_first_seen.setdefault(s, now)
                self.singer_last_seen[s] = now
                notes.append(
                    NewSinger(singer=s, timestamp=now,
                              message=f"{s} joined the queue")
                )
            else:
                # spec rule 3: refresh recency for present singers
                self.singer_last_seen[s] = now

        # spec rule 2: front-of-queue singer changed -> TurnAdvanced.
        # A None front (unassigned slot) is not a turn change.
        front = snapshot.queue[0].singer if snapshot.queue else None
        if front is not None and front != self._front_singer:
            notes.append(
                TurnAdvanced(singer=front, timestamp=now,
                             message=f"It's now {front}'s turn")
            )
        self._front_singer = front

        # spec rule 4: idle -> no notification; recencies retained above.
        return notes
```

- [ ] **Step 4: Run tests, verify PASS.**

Run: `pytest tests/test_model.py -v -W error`
Expected: all 6 PASS.

- [ ] **Step 5: Lint.**

Run: `ruff check src/karafun_intercept/model.py tests/test_model.py`
Expected: `All checks passed!`

- [ ] **Step 6: Commit.**

```bash
git add src/karafun_intercept/model.py tests/test_model.py
git commit -m "feat: add SessionModel (spec §6: datetime recency, NewSinger/TurnAdvanced) with tests"
```

---

### Task 4: `app.py` — Textual TUI (Header/Current/Queue/Singers/Notifications/Footer)

**Files:**

- Rewrite: `src/karafun_intercept/app.py` (body only; scaffold already exists)
- Create: `src/karafun_intercept/__main__.py` (per spec §9: `python -m karafun_intercept`)
- Create: `tests/test_app.py`

Layout matches spec §7: single screen; `#current` Static header line; a `Horizontal` split of queue `OptionList` (left) and singer `OptionList` (right); `#notifications` Static banner; `Header`/`Footer`. `Footer` derives hints from `BINDINGS` (spec §7). `app` owns a `SessionModel`; in production `on_mount` launches a `run_worker` consuming `client.events()` and calling `feed_snapshot`; tests inject `client=None` (no worker) and call `feed_snapshot` directly for deterministic Pilot assertions. The app is a pure reactor — notifications carry a ready `message` from the model, so the UI only renders `n.message`.

- [ ] **Step 1: Write failing UI tests** (`tests/test_app.py`) — Textual Pilot via `asyncio.run` (no plugin):

```python
import asyncio
from karafun_intercept.app import KaraFunInterceptApp
from karafun_intercept.xml_proto import parse_status


def _run(coro, timeout=2.0):
    return asyncio.run(asyncio.wait_for(coro, timeout))


def test_first_snap_renders_current_queue_singers(status1_xml):
    app = KaraFunInterceptApp()

    async def main():
        async with app.run_test() as pilot:
            app.feed_snapshot(parse_status(status1_xml))
            await pilot.pause()
            cur = str(app.query_one("#current").renderable).lower()
            assert "song a" in cur and "artist a" in cur and "playing" in cur
            ql = app.query_one("#queue")
            assert ql.option_count == 2
            qlabels = [str(ql.get_option_at_index(i).prompt) for i in range(ql.option_count)]
            assert any("song a" in s.lower() for s in qlabels)
            sl = app.query_one("#singers")
            slabels = [str(sl.get_option_at_index(i).prompt) for i in range(sl.option_count)]
            assert any("alice" in s.lower() for s in slabels)
            assert any("bob" in s.lower() for s in slabels)
            # NewSinger + TurnAdvanced for Alice/Bob land in the banner.
            assert "alice" in str(app.query_one("#notifications").renderable).lower()

    _run(main())


def test_new_song_produces_notification(status1_xml, status2_xml):
    app = KaraFunInterceptApp()

    async def main():
        async with app.run_test() as pilot:
            app.feed_snapshot(parse_status(status1_xml))
            app.feed_snapshot(parse_status(status2_xml))
            await pilot.pause()
            note = str(app.query_one("#notifications").renderable).lower()
            assert "bob" in note  # NewSinger + TurnAdvanced for Bob
            assert "song b" in str(app.query_one("#current").renderable).lower()

    _run(main())


def test_empty_snapshot_renders_idle():
    app = KaraFunInterceptApp()
    idle = parse_status('<status state="idle"><queue></queue></status>')

    async def main():
        async with app.run_test() as pilot:
            app.feed_snapshot(idle)
            await pilot.pause()
            assert "idle" in str(app.query_one("#current").renderable).lower()
            assert app.query_one("#queue").option_count == 0
            assert app.query_one("#singers").option_count == 0

    _run(main())


def test_refresh_action_renames_current(status1_xml):
    app = KaraFunInterceptApp()

    async def main():
        async with app.run_test() as pilot:
            app.feed_snapshot(parse_status(status1_xml))
            await pilot.pause()
            app.action_refresh()
            await pilot.pause()
            assert "song a" in str(app.query_one("#current").renderable).lower()

    _run(main())
```

- [ ] **Step 2: Run tests, verify FAIL** (missing `feed_snapshot`/`action_refresh`, or `OptionList` API mismatch).

Run: `pytest tests/test_app.py -v`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation** (`src/karafun_intercept/app.py` + `__main__.py`):

```python
"""Textual TUI observing the local KaraFun Player.

Layers: client.py (events) -> this App -> model.SessionModel. The UI is a
pure reactor over model state. A background worker (started on mount when a
client is injected) forwards live events into the model; tests bypass the
worker by calling feed_snapshot() directly on the (worker-less) app.
"""
from __future__ import annotations

import logging
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Header, OptionList, Static

from karafun_intercept.client import Disconnected, Error, KarafunClient, StatusUpdate
from karafun_intercept.model import SessionModel
from karafun_intercept.xml_proto import StatusSnapshot

_log = logging.getLogger(__name__)

MAX_NOTIFICATIONS = 50


class KaraFunInterceptApp(App):
    """Karafun Intercept — the TUI."""

    title = "KaraFun Intercept"

    CSS = """
    Screen { layout: vertical; }
    #current { height: 1; color: bold; }
    #queue { width: 1fr; border-right: solid $primary; }
    #singers { width: 30; border-left: solid $primary; }
    #notifications { height: auto; border-top: solid; }
    OptionList { height: 1fr; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(
        self,
        *,
        model: Optional[SessionModel] = None,
        client: Optional[KarafunClient] = None,
    ):
        super().__init__()
        self._model = model or SessionModel()
        self._client = client
        self._notifications: list[str] = []

    # --- composition ------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="current")
        with Horizontal():
            yield OptionList(id="queue")
            yield OptionList(id="singers")
        yield Static("", id="notifications")
        yield Footer()

    # --- lifecycle --------------------------------------------------------
    def on_mount(self) -> None:
        self._render_all()
        if self._client is not None:
            self.run_worker(self._observe(), exclusive=True)

    def action_refresh(self) -> None:
        self._render_all()

    # --- live observation (production) ------------------------------------
    async def _observe(self) -> None:
        assert self._client is not None
        async for ev in self._client.events():
            if isinstance(ev, StatusUpdate):
                self.feed_snapshot(ev.snapshot)
            elif isinstance(ev, Disconnected):
                self._set_current(f"disconnected: {ev.reason}")
            elif isinstance(ev, Error):
                self._set_current(f"error: {ev.message}")

    # --- public: feed a snapshot (tests + observe worker) -----------------
    def feed_snapshot(self, snapshot: StatusSnapshot) -> None:
        notes = self._model.apply_status(snapshot)
        if notes:
            self._notifications.extend(n.message for n in notes)
            self._notifications = self._notifications[-MAX_NOTIFICATIONS:]
        self._render_all()

    # --- rendering --------------------------------------------------------
    def _render_all(self) -> None:
        self._render_current()
        self._render_queue()
        self._render_singers()
        self._render_notifications()

    def _set_current(self, msg: str) -> None:
        try:
            self.query_one("#current", Static).update(msg)
        except Exception:
            pass

    def _render_current(self) -> None:
        m = self._model
        if m.current_song and m.state == "playing":
            title, artist = m.current_song
            pos = f" {m.position}s" if m.position is not None else ""
            line = f"playing  {title} - {artist}{pos}"
        elif m.current_song:
            title, artist = m.current_song
            line = f"{title} - {artist}"
        else:
            line = m.state
        self._set_current(line)

    def _render_queue(self) -> None:
        m = self._model
        top = m.current_song
        items = []
        for i, item in enumerate(m.queue):
            here = (item.title, item.artist) == top
            mark = "|> " if here else "   "
            singer = item.singer or "-"
            items.append(f"{mark}{i + 1}. {item.title} - {item.artist}  [{singer}]")
        ql = self.query_one("#queue", OptionList)
        ql.clear_options()
        if items:
            ql.add_options(*items)

    def _render_singers(self) -> None:
        m = self._model
        cur = m.current_singer
        lines = [f"{'*' if s == cur else '.'} {s}" for s in m.singer_recency()]
        sl = self.query_one("#singers", OptionList)
        sl.clear_options()
        if lines:
            sl.add_options(*lines)

    def _render_notifications(self) -> None:
        banner = "\n".join(self._notifications[-8:]) if self._notifications else ""
        self.query_one("#notifications", Static).update(banner)


def main() -> None:
    """Entry point for the karafun-intercept TUI."""
    import logging

    logging.basicConfig(level=logging.INFO)
    KaraFunInterceptApp().run()


if __name__ == "__main__":
    main()
```

`__main__.py`:

```python
"""Run with: python -m karafun_intercept"""
from karafun_intercept.app import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests, verify PASS.**

Run: `pytest tests/test_app.py -v -W error`
Expected: all 4 PASS. (`run_test()` is headless by default; no TTY needed.)

- [ ] **Step 5: Lint.**

Run: `ruff check src/karafun_intercept/app.py src/karafun_intercept/__main__.py tests/test_app.py`
Expected: `All checks passed!`

- [ ] **Step 6: Commit.**

```bash
git add src/karafun_intercept/app.py src/karafun_intercept/__main__.py tests/test_app.py
git commit -m "feat: add Textual TUI (queue/singers/notifications) with pilot tests"
```

---

### Task 5: live-player fixtures + end-to-end integration (gated on live player)

**Files:**

- Create: `tests/test_integration.py`
- (Manual, live-only) Optionally add: `tests/fixtures/status_live_*.xml`

Closes the loop: real captured XML must parse and drive the full client → model pipeline. The integration test is hermetic (replays `STATUS1_XML`/`STATUS2_XML` through a `FakeFactory`-fed `KarafunClient` into a real `SessionModel`, asserting `NewSinger`/`TurnAdvanced` deltas). A second test is `@pytest.mark.skip`-gated on the live player.

- [ ] **Step 1: Write integration tests** (`tests/test_integration.py`):

```python
import asyncio

import pytest

from karafun_intercept.client import KarafunClient, StatusUpdate
from karafun_intercept.model import SessionModel


def _kinds(notes):
    return [(type(n).__name__, n.singer) for n in notes]


# Local fake transport/factory (mirrors tests/test_client.py; kept local so
# each commit is self-contained per spec §9).
class _FT:
    def __init__(self, messages):
        self._m = list(messages)
        self.sent = []
        self.closed = False

    async def send(self, data):
        self.sent.append(data)

    async def recv(self):
        if self._m:
            return self._m.pop(0)
        return ""

    async def close(self):
        self.closed = True


class _FF:
    def __init__(self, connections):
        self._c = list(connections)
        self.calls = 0

    async def __call__(self):
        self.calls += 1
        msgs = self._c[min(self.calls - 1, len(self._c) - 1)]
        return _FT(msgs)


def test_client_to_model_pipeline(status1_xml, status2_xml):
    factory = _FF([[status1_xml, status2_xml]])
    client = KarafunClient(
        transport_factory=factory, reconnect_min_delay=0.0,
        reconnect_max_delay=0.0, poll_interval=100, poll_timeout_gap=100,
    )
    model = SessionModel()
    collected = []

    async def run():
        async for ev in client.events():
            if isinstance(ev, StatusUpdate):
                notes = model.apply_status(ev.snapshot)
                collected.append(notes)
                if len(collected) == 2:
                    return

    asyncio.run(asyncio.wait_for(run(), 1.0))
    assert _kinds(collected[0]) == [
        ("NewSinger", "Alice"), ("NewSinger", "Bob"), ("TurnAdvanced", "Alice")
    ]
    assert _kinds(collected[1]) == [
        ("NewSinger", "Cara"), ("TurnAdvanced", "Bob")
    ]
    assert model.current_singer == "Bob"
    assert set(model.singer_recency()) == {"Alice", "Bob", "Cara"}
    assert model.singer_recency()[0] == "Cara"  # most recent


@pytest.mark.skip(reason="live player only: requires KaraFun Player at ws://localhost:57570")
def test_live_player_emits_status():
    seen = []

    async def run():
        async for ev in KarafunClient().events():
            seen.append(ev)
            return

    asyncio.run(asyncio.wait_for(run(), 5.0))
    assert seen  # reached only against a live player
```

- [ ] **Step 2: Run tests, verify PASS** (skip honored).

Run: `pytest tests/test_integration.py -v -W error`
Expected: `test_client_to_model_pipeline` PASS; `test_live_player_emits_status` SKIPPED.

- [ ] **Step 3: Lint.**

Run: `ruff check src tests`
Expected: `All checks passed!`

- [ ] **Step 4: Full-suite check.**

Run: `pytest -W error`
Expected: all PASS (Task 1–5 tests; live test skipped).

- [ ] **Step 5: Commit.**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end client->model integration tests (live test skipped)"
```

---

## Review gate (writing-plans step 7) — self-review findings reconciliation

Reviewer audited the plan against `docs/superpowers/specs/...design.md`, `docs/research/karafun-api/02-api-reference.md`, and `PHILOSOPHY.md`. Resolutions:

- **B1 (test assertion `></action"` missing `>`):** Reporter stale — line 213 in the plan already reads `noqueue></action>` (closed form, matching impl line 328 and research §05). **PASS.**
- **B2 / research #3 / #10 (`<volumeList>`):** **intentionally not parsed.** `parse_status` ignores unknown fields — forward-compatible per spec §8 ("ignore unknown fields") and out of MVP scope (spec §2 YAGNI: volume not part of singer/turn/recency observation). Not mapped to any task. **ACCEPTED (not a defect).**
- **review #6 (recency / notifications):** **RECONCILED against spec §6.** Task 3 now uses `singer_last_seen: dict[str, datetime]`, `singer_first_seen`, `known_singers: set[str]`, an injected `now` callable, and only `NewSinger`/`TurnAdvanced` notifications (idle = no notification, spec rule 4; absent singers ignored, spec rule 1). Task 4 (`feed_snapshot` renders `n.message`) and Task 5 assertions updated to match. **FIXED.**
- **review #7 (PHILOSOPHY Contract 9 — key binding):** **RECONCILED (no code change).** PHILOSOPHY.md on disk is Crystal-era (`keymap` dict + `_handle_*` + `render_footer`); the spec (§7) mandates a Textual TUI, so bindings use Textual's native `BINDINGS` + `action_*` + `Footer` widget — the same "footer shows only handled actions" contract. PHILOSOPHY.md is stale (the Goal intended generalizing it; not yet done on disk). Tracked as a separate housekeeping task, not a plan defect.
- **#8 timing / #9 FakeTransport deadlock:** **PASS.**

### Writing-plans 4-point checklist

- [x] **A — Spec/roadmap coverage:** §2 scope, §4 architecture, §5 state, §6 SessionModel, §7 TUI+keymap+footer, §8 error lifecycle/reconnect/reseed, §9 file layout + entry point, §10 testing strategy — all mapped.
- [x] **B — Placeholder scan:** no `TODO`/`pass`-only stubs; every test asserts concrete values; the earlier broken compose stub is corrected.
- [x] **C — Type consistency:** annotations resolve; 3.9+ generics (runtime 3.14); `Notification = NewSinger | TurnAdvanced` union valid.
- [x] **D — Phase boundary health:** `xml_proto` ← client ← (app); `xml_proto` ← model ← (app); no cycles; each layer's tests depend only on own + lower layers.

- [ ] **Commit the final plan** (local; no remote here):

  ```bash
  git add docs/superpowers/plans/2026-09-26-karafun-intercept-plan.md
  git commit -m "docs(plan): finalize Task 1-5 plan; reconcile spec §6/§8/§10 + reviewer findings"
  ```

---

> Plan complete through Task 5 + review gate (reconciled). **Handoff to execution:** prefer the `executing-plans` subagent (one task at a time with isolated test gates) over inline implementation; each task is self-contained and TDD. MVP stays observe-only (no playback control / catalogue / persistence). Suggestion: file a separate cleanup task to generalize `PHILOSOPHY.md` away from Crystal before the first code review.
