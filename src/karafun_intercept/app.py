"""Textual TUI observing the local Karafun Player.

Layers: client.py (events) -> this App -> model.SessionModel. The UI is a pure
reactor over model state. A background worker (started on mount when a client is
injected) forwards live events into the model; tests bypass the worker by
calling feed_snapshot() directly on the worker-less app.
"""

from __future__ import annotations

import logging
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal
from textual.widgets import Footer, Header, OptionList, Static

from karafun_intercept.client import Disconnected, Error, KarafunClient, StatusUpdate
from karafun_intercept.model import SessionModel
from karafun_intercept.xml_proto import StatusSnapshot

_log = logging.getLogger(__name__)

MAX_NOTIFICATIONS = 50


class KaraFunInterceptApp(App):
    """Karafun Intercept — the observer TUI."""

    CSS = """
    Screen { layout: vertical; }
    #current { height: 1; }
    #queue { width: 1fr; border-right: solid $primary; }
    #singers { width: 30; border-left: solid $primary; }
    #notifications { height: auto; border-top: solid; }
    OptionList { height: 1fr; }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(
        self,
        *,
        model: SessionModel | None = None,
        client: KarafunClient | None = None,
    ) -> None:
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
        # `title` is Reactive[str]; set at runtime (not as a class attr) to stay
        # type-clean under pyright (class-level str would override Reactive[str]).
        self.title = "KaraFun Intercept"
        self._render_all()
        if self._client is not None:
            self.run_worker(self._observe(), exclusive=True)

    def action_refresh(self) -> None:
        self._render_all()

    # --- live observation (production) ------------------------------------
    async def _observe(self) -> None:
        client = self._client
        if client is None:
            return
        async for ev in client.events():
            if isinstance(ev, StatusUpdate):
                self.feed_snapshot(ev.snapshot)
            elif isinstance(ev, Disconnected):
                _log.debug("player disconnected: %s", ev.reason)
                self._set_current(f"connecting… ({ev.reason})")
            elif isinstance(ev, Error):
                _log.debug("player error: %s", ev.message)
                self._set_current(f"error: {ev.message}")

    # --- public: feed a snapshot (tests + observe worker) ----------------
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
        self.query_one("#current", Static).update(msg)

    def _render_current(self) -> None:
        m = self._model
        song = m.current_song
        if song and m.state == "playing":
            title, artist = song
            pos = f" {m.position}s" if m.position is not None else ""
            line = f"playing  {title} - {artist}{pos}"
        elif song:
            title, artist = song
            line = f"{title} - {artist}"
        else:
            line = m.state
        self._set_current(line)

    def _render_queue(self) -> None:
        m = self._model
        top = m.current_song
        items: list[str] = []
        for i, item in enumerate(m.queue):
            here = (item.title, item.artist) == top
            mark = "|> " if here else "   "
            singer = item.singer or "-"
            items.append(f"{mark}{i + 1}. {item.title} - {item.artist}  [{singer}]")
        ql = self.query_one("#queue", OptionList)
        ql.clear_options()
        if items:
            ql.add_options(items)

    def _render_singers(self) -> None:
        m = self._model
        cur = m.current_singer
        lines = [f"{'*' if s == cur else '.'} {s}" for s in m.singer_recency]
        sl = self.query_one("#singers", OptionList)
        sl.clear_options()
        if lines:
            sl.add_options(lines)

    def _render_notifications(self) -> None:
        banner = "\n".join(self._notifications[-8:]) if self._notifications else ""
        self.query_one("#notifications", Static).update(banner)


def main() -> None:
    """Entry point for the karafun-intercept TUI."""
    logging.basicConfig(level=logging.INFO)
    KaraFunInterceptApp().run()


if __name__ == "__main__":
    main()
