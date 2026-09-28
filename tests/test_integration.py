"""End-to-end integration: client -> model pipeline (hermetic).

Replays recorded STATUS1/STATUS2 XML through a fake transport-fed KarafunClient
into a real SessionModel, asserting the NewSinger/TurnAdvanced deltas the model
emits. No network, no live player.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from karafun_intercept.client import KarafunClient, StatusUpdate, Transport
from karafun_intercept.model import SessionModel


def _kinds(notes):
    """Order-independent (kind, singer) view of notifications, ignoring timestamps."""
    return [(type(n).__name__, n.singer) for n in notes]


# Local fake transport/factory (mirrors tests/test_client.py; kept local so each
# commit is self-contained per spec §9).
class _FakeTransport(Transport):
    """In-memory transport (subtype of Transport: satisfies the
    transport_factory type contract and inherits __aenter__/__aexit__)."""

    def __init__(self, messages):
        self._m = list(messages)
        self.sent = []
        self.closed = False

    async def send(self, data):
        self.sent.append(data)

    async def recv(self):
        if self._m:
            return self._m.pop(0)
        return ""  # clean EOF -> Disconnected

    async def close(self):
        self.closed = True


class _FakeFactory:
    def __init__(self, connections):
        self._c = list(connections)
        self.calls = 0

    async def __call__(self):
        self.calls += 1
        msgs = self._c[min(self.calls - 1, len(self._c) - 1)]
        return _FakeTransport(msgs)


def test_client_to_model_pipeline(status1_xml, status2_xml):
    factory = _FakeFactory([[status1_xml, status2_xml]])
    client = KarafunClient(
        transport_factory=factory,
        reconnect_min_delay=0.0,
        reconnect_max_delay=0.0,
        poll_interval=100,
        poll_timeout_gap=100,
    )
    # Inject a deterministic clock so STATUS1 < STATUS2 timestamps are distinct.
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ticks = {"n": 0}

    def _now():
        ticks["n"] += 1
        return base + timedelta(seconds=ticks["n"])

    model = SessionModel(now=_now)
    collected = []

    async def run():
        async for ev in client.events():
            if isinstance(ev, StatusUpdate):
                collected.append(model.apply_status(ev.snapshot))
                if len(collected) == 2:
                    return

    asyncio.run(asyncio.wait_for(run(), 1.0))
    assert _kinds(collected[0]) == [
        ("NewSinger", "Alice"),
        ("NewSinger", "Bob"),
        ("TurnAdvanced", "Alice"),
    ]
    assert _kinds(collected[1]) == [
        ("NewSinger", "Cara"),
        ("TurnAdvanced", "Bob"),
    ]
    assert model.current_singer == "Bob"
    # Alice is absent from STATUS2's queue -> least-recently seen; Bob & Cara both
    # seen in STATUS2 (tied for most-recent).
    assert model.singer_recency[-1] == "Alice"
    assert set(model.singer_recency) == {"Alice", "Bob", "Cara"}


@pytest.mark.skip(reason="live player only: requires KaraFun Player at ws://localhost:57570")
def test_live_player_emits_status():
    seen = []

    async def run():
        async for ev in KarafunClient().events():
            seen.append(ev)
            return

    asyncio.run(asyncio.wait_for(run(), 5.0))
    assert seen  # reached only against a live player
