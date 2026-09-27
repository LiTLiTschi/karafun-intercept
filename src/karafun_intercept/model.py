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
from typing import Callable

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

    def __init__(self, *, now: Callable[[], datetime] = _utcnow) -> None:
        self._now = now
        self._current: StatusSnapshot | None = None
        self.singer_last_seen: dict[str, datetime] = {}
        self.singer_first_seen: dict[str, datetime] = {}
        self.known_singers: set[str] = set()
        self._front_singer: str | None = None

    @property
    def state(self) -> str:
        return self._current.state if self._current else "idle"

    @property
    def position(self) -> int | None:
        return self._current.position if self._current else None

    @property
    def tempo(self) -> int | None:
        return self._current.tempo if self._current else None

    @property
    def queue(self) -> list[QueueItem]:
        return list(self._current.queue) if self._current else []

    @property
    def current_song(self) -> tuple[str, str] | None:
        if self._current and self._current.queue:
            item = self._current.queue[0]
            return (item.title, item.artist)
        return None

    @property
    def current_singer(self) -> str | None:
        if self._current and self._current.queue:
            return self._current.queue[0].singer
        return None

    @property
    def singer_recency(self) -> list[str]:
        """Singers ordered most-recent-first by last seen."""
        return [
            singer
            for singer, _ts in sorted(
                self.singer_last_seen.items(), key=lambda kv: kv[1], reverse=True
            )
        ]

    def apply_status(self, snapshot: StatusSnapshot) -> list[Notification]:
        """Fold a status into state; return the notifications it produced."""
        now = self._now()
        notes: list[Notification] = []
        self._current = snapshot

        # spec rule 1 & 3: present singers -> NewSinger if new, else refresh recency
        present = [q.singer for q in snapshot.queue if q.singer]
        for singer in present:
            if singer not in self.known_singers:
                self.known_singers.add(singer)
                self.singer_first_seen.setdefault(singer, now)
                self.singer_last_seen[singer] = now
                notes.append(
                    NewSinger(
                        singer=singer,
                        timestamp=now,
                        message=f"{singer} joined the queue",
                    )
                )
            else:
                self.singer_last_seen[singer] = now

        # spec rule 2: front-of-queue singer changed -> TurnAdvanced.
        # An unassigned front slot (None) does not advance the turn.
        front = snapshot.queue[0].singer if snapshot.queue else None
        if front is not None and front != self._front_singer:
            notes.append(
                TurnAdvanced(
                    singer=front,
                    timestamp=now,
                    message=f"It's now {front}'s turn",
                )
            )
        self._front_singer = front

        # spec rule 4: idle -> no notification; recencies retained above.
        return notes
