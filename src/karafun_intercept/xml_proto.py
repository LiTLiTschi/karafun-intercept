"""XML protocol parsing and action builders for the KaraFun Player Control API.

Pure: stdlib only, no I/O. Forms the boundary between the WebSocket
transport (client.py) and the in-memory model (model.py).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

# --- Network / observation constants (single source of truth) ---
# Use 127.0.0.1 (not "localhost") so the websockets library avoids IPv6 ::1
# resolution on Windows, where the KaraFun Player binds IPv4 only.
PLAYER_HOST = "127.0.0.1"
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
    year: int | None
    duration: int | None
    singer: str | None
    item_state: str


@dataclass(frozen=True)
class StatusSnapshot:
    """Normalized, in-memory view of a <status> response."""

    state: str
    position: int | None
    pitch: int | None
    tempo: int | None
    queue: list[QueueItem] = field(default_factory=list)


def _text(elem: ET.Element | None) -> str | None:
    """Return stripped text of *elem*, or None if absent/empty."""
    if elem is None:
        return None
    text = elem.text
    if text is None:
        return None
    stripped = text.strip()
    if stripped == "":
        return None
    return stripped


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_queue_item(item: ET.Element) -> QueueItem:
    return QueueItem(
        id=_to_int(item.get("id")) or 0,
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
        queue=[parse_queue_item(item) for item in root.findall(".//queue/item")],
    )


def build_get_status_action(noqueue: bool = False) -> str:
    if noqueue:
        return '<action type="getStatus" noqueue></action>'
    return '<action type="getStatus"></action>'
