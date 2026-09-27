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
from collections.abc import AsyncIterator, Awaitable
from dataclasses import dataclass
from typing import Callable

from typing_extensions import Self

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

    async def recv(self) -> str | None:
        raise NotImplementedError  # None / "" => closed

    async def close(self) -> None:
        raise NotImplementedError

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()


class WebSocketTransport(Transport):
    def __init__(self, ws):
        self._ws = ws

    async def send(self, data: str) -> None:
        await self._ws.send(data)

    async def recv(self) -> str | None:
        try:
            msg = await self._ws.recv()
        except Exception as e:  # noqa: BLE001  # lazy ws import; any recv failure => closed stream
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
        transport_factory: Callable[[], Awaitable[Transport]] | None = None,
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
        self._last_status_time: float | None = None

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

    def _dispatch(self, raw: str) -> object | None:
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
