import asyncio

from karafun_intercept.client import (
    Disconnected,
    Error,
    KarafunClient,
    StatusUpdate,
    build_get_status_action,
)


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

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()
        return False


class FakeFactory:
    """Yields one FakeTransport per connection attempt (reconnect-aware)."""

    def __init__(self, connections, block_when_empty=False):
        self._connections = list(connections)
        self._block_when_empty = block_when_empty
        self.calls = 0
        self.transports = []

    async def __call__(self):
        self.calls += 1
        msgs = self._connections[min(self.calls - 1, len(self._connections) - 1)]
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


def _client(
    factory,
    *,
    poll_interval: float = 100,
    poll_timeout_gap: float = 100,
) -> KarafunClient:
    return KarafunClient(
        transport_factory=factory,
        poll_interval=poll_interval,
        poll_timeout_gap=poll_timeout_gap,
        reconnect_min_delay=0.0,
        reconnect_max_delay=0.0,
    )


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
    factory = FakeFactory(
        [
            [],  # connection 1 closes immediately -> Disconnected
            [status1_xml],  # connection 2 delivers a status
        ]
    )
    client = _client(factory)

    def got_both(es):
        return any(isinstance(e, Disconnected) for e in es) and isinstance(es[-1], StatusUpdate)

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
    assert build_get_status_action() == sent[0]  # seed (full)
    assert build_get_status_action(noqueue=True) in sent  # poll fallback
