# Fair-Queue Table View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use /skill:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full-screen, auto-updating, sortable table view to the Karafun Intercept TUI with 4 columns (Singer, Last Added, # Turns, Since Last Turn), accessible via `Tab`, showing all known singers for fair-queue management.

**Architecture:** A new `FairQueueScreen` (Textual `Screen` + `DataTable`) shares the existing `SessionModel`. `Tab` on the dashboard pushes the table screen; `Tab` on the table pops back. The model is extended with per-singer turn/add tracking. A 1-second timer on the table screen keeps elapsed-time columns live.

**Tech Stack:** Python 3.9+, Textual 0.85+, pytest (with `-W error`), ruff

**Roadmap:** None (single-plan implementation)

**Phase:** Single-plan implementation

---

## File Structure

| File | Change |
| --- | --- |
| `src/karafun_intercept/model.py` | Add 4 new tracking fields + logic in `apply_status()` |
| `src/karafun_intercept/app.py` | Add `FairQueueScreen` class + `_format_elapsed` helper + `Tab` binding on `KaraFunInterceptApp` |
| `tests/conftest.py` | Add `status3_xml` fixture (Alice/Bob with new songs) |
| `tests/test_model.py` | Add 4 tests: turn tracking, turn dedup, last-added on new song, idle no-turn |
| `tests/test_app.py` | Add 5 tests: table renders singers, sorting, empty state, live timer, Tab switch |

**Verification:** `pytest tests/test_model.py tests/test_app.py -W error` and `ruff check src/karafun_intercept/model.py src/karafun_intercept/app.py tests/test_model.py tests/test_app.py`

---

## Task 1: Extend SessionModel with Fair-Queue Tracking

**Files:**
- Modify: `src/karafun_intercept/model.py` — add 4 fields to `__init__`, add tracking logic in `apply_status`
- Modify: `tests/conftest.py` — add `STATUS3_XML` fixture
- Test: `tests/test_model.py` — add 4 tests

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_model.py`:

```python
# --- Fair-queue tracking tests ---

def _clocked_model(base=dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc)):
    """SessionModel with a clock that advances 1 second per call."""
    state = {"t": base}
    def now():
        state["t"] += dt.timedelta(seconds=1)
        return state["t"]
    return SessionModel(now=now)


def test_fair_queue_turn_tracking(status1_xml, status2_xml):
    m = _clocked_model()
    m.apply_status(parse_status(status1_xml))  # Alice front + playing -> turn 1
    m.apply_status(parse_status(status2_xml))  # Bob front + playing -> turn 1
    assert m.singer_turns == {"Alice": 1, "Bob": 1}


def test_fair_queue_turn_dedup(status1_xml):
    m = _clocked_model()
    m.apply_status(parse_status(status1_xml))  # Alice turn 1
    m.apply_status(parse_status(status1_xml))  # Alice still front+playing -> no new turn
    assert m.singer_turns == {"Alice": 1}


def test_fair_queue_last_added_updates_on_new_song(status1_xml, status3_xml):
    m = _clocked_model()
    m.apply_status(parse_status(status1_xml))   # Alice adds "Song A"
    m.apply_status(parse_status(status3_xml))   # Alice adds "Song D" (new song)
    base = dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc)
    # last_added is updated to the snapshot time, first_seen is unchanged
    assert m.singer_last_added["Alice"] == base + dt.timedelta(seconds=2)
    assert m.singer_first_seen["Alice"] == base + dt.timedelta(seconds=1)


def test_fair_queue_idle_preserves_turns(status1_xml):
    m = _clocked_model()
    m.apply_status(parse_status(status1_xml))  # Alice turn 1
    idle = parse_status('<status state="idle"><queue></queue></status>')
    m.apply_status(idle)
    assert m.singer_turns == {"Alice": 1}
    assert m.singer_last_turn["Alice"] is not None
```

Add to `tests/conftest.py`:

```python
STATUS3_XML = """\
<status state="playing">
  <position>30</position>
  <pitch>0</pitch>
  <tempo>100</tempo>
  <queue>
    <item id="0" status="ready">
      <title>Song D</title> <artist>Artist D</artist>
      <year>2022</year> <duration>210</duration>
      <singer>Alice</singer>
    </item>
    <item id="1" status="ready">
      <title>Song E</title> <artist>Artist E</artist>
      <year>2020</year> <duration>185</duration>
      <singer>Bob</singer>
    </item>
  </queue>
</status>"""
```

```python
@pytest.fixture
def status3_xml():
    return STATUS3_XML
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/test_model.py -v -k "fair_queue"
```
Expected: FAIL with `AttributeError` (fields `singer_turns`, `singer_last_added`, `singer_last_turn` don't exist yet).

- [ ] **Step 3: Implement the model extensions**

Edit `src/karafun_intercept/model.py` — add to `__init__`:

```python
        self.singer_last_added: dict[str, datetime] = {}
        self.singer_turns: dict[str, int] = {}
        self.singer_last_turn: dict[str, datetime] = {}
        self._seen_song_keys: set[tuple[str, str]] = set()
        self._last_scored_turn_singer: str | None = None
```

Edit `apply_status` — insert new-add detection after `self._current = snapshot`:

```python
        # --- new-add detection: which songs are new to the queue? ---
        current_song_keys = {(q.title, q.artist) for q in snapshot.queue}
        new_items = [
            q for q in snapshot.queue
            if (q.title, q.artist) not in self._seen_song_keys
        ]
        for item in new_items:
            if item.singer:
                self.singer_last_added[item.singer] = now
        self._seen_song_keys = current_song_keys
```

Edit `apply_status` — after `front = ...` and before the existing `TurnAdvanced` notification, add turn counting:

```python
        # --- turn counting: front singer while playing ---
        if snapshot.state == "playing" and front is not None:
            if front != self._last_scored_turn_singer:
                self.singer_turns[front] = self.singer_turns.get(front, 0) + 1
                self.singer_last_turn[front] = now
                self._last_scored_turn_singer = front
```

**Important:** The existing `TurnAdvanced` notification logic and `self._front_singer = front` line stay unchanged after this insertion.

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/test_model.py -v -W error
```
Expected: All tests pass (existing + new).

- [ ] **Step 5: Commit**

```bash
git add src/karafun_intercept/model.py tests/conftest.py tests/test_model.py
git commit -m "feat: add fair-queue tracking to SessionModel"
```

---

## Task 2: Add FairQueueScreen Class

**Files:**
- Modify: `src/karafun_intercept/app.py` — add `FairQueueScreen`, `_format_elapsed`, required imports
- Test: `tests/test_app.py` — add 3 tests (renders, sorting, empty state)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_app.py`:

```python
from datetime import datetime, timezone
from unittest.mock import patch

from textual.widgets import DataTable


def test_fair_queue_table_renders_all_singers(status1_xml, status2_xml):
    app = KaraFunInterceptApp()

    async def main():
        async with app.run_test() as pilot:
            app.feed_snapshot(parse_status(status1_xml))
            app.feed_snapshot(parse_status(status2_xml))
            await pilot.pause()
            await pilot.press("tab")
            await pilot.pause()
            table = app.query_one("#fair_queue_table", DataTable)
            # Alice, Bob, Cara = 3 known singers
            assert table.row_count == 3
            row_labels = [str(table.get_row_at(i)) for i in range(table.row_count)]
            assert any("alice" in r.lower() for r in row_labels)
            assert any("bob" in r.lower() for r in row_labels)
            assert any("cara" in r.lower() for r in row_labels)

    _run(main())


def test_fair_queue_table_sorting(status1_xml, status2_xml):
    app = KaraFunInterceptApp()

    async def main():
        async with app.run_test() as pilot:
            app.feed_snapshot(parse_status(status1_xml))
            app.feed_snapshot(parse_status(status2_xml))
            await pilot.pause()
            await pilot.press("tab")
            await pilot.pause()

            table = app.query_one("#fair_queue_table", DataTable)

            # Default sort: name ascending
            first_asc = str(table.get_row_at(0))
            # Trigger sort on "# turns" column by calling the handler directly
            screen = app.query_one(FairQueueScreen)
            screen._sort_column = "turns"
            screen._sort_reverse = False
            screen._render_table()
            await pilot.pause()

            # Alice has 1 turn, Bob has 1 turn, Cara has 0 turns -> Cara first
            first_turns = str(table.get_row_at(0))
            assert "cara" in first_turns.lower()

            # Reverse: Cara has 0, so should be last
            screen._sort_reverse = True
            screen._render_table()
            await pilot.pause()
            first_rev = str(table.get_row_at(0))
            assert "cara" not in first_rev.lower()

    _run(main())


def test_fair_queue_table_empty_state():
    app = KaraFunInterceptApp()

    async def main():
        async with app.run_test() as pilot:
            await pilot.press("tab")
            await pilot.pause()
            table = app.query_one("#fair_queue_table", DataTable)
            assert table.row_count == 1
            row = str(table.get_row_at(0))
            assert "waiting" in row.lower()

    _run(main())
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/test_app.py -v -k "fair_queue" -W error
```
Expected: FAIL — `FairQueueScreen` class not found, `Tab` binding not registered.

- [ ] **Step 3: Implement FairQueueScreen**

Add imports to `app.py`:

```python
from datetime import datetime, timedelta, timezone
from typing import Any

from textual.app import App, ComposeResult, Screen
from textual.widgets import DataTable, Footer, Header, OptionList, Static
```

Add module-level helper:

```python
def _format_elapsed(delta: timedelta) -> str:
    """Convert a timedelta to HH:MM string (e.g. 18m22s -> '18:22')."""
    total = int(delta.total_seconds())
    hours, remainder = divmod(total, 3600)
    minutes = remainder // 60
    return f"{hours:02d}:{minutes:02d}"
```

Add `FairQueueScreen` class (after `KaraFunInterceptApp`, before `main()`):

```python
class FairQueueScreen(Screen):
    """Full-screen sortable table of singer fair-queue metrics."""

    CSS = """
    Screen { layout: vertical; }
    #fair_queue_table { width: 100%; height: 1fr; border: solid $primary; }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("tab", "switch_view", "Back"),
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, *, model: SessionModel, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model = model
        self._sort_column: str = "name"
        self._sort_reverse: bool = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="fair_queue_table")
        yield Footer()

    def on_mount(self) -> None:
        self._setup_table()
        self._render_table()
        self.set_interval(1.0, self._tick)

    def _setup_table(self) -> None:
        table = self.query_one("#fair_queue_table", DataTable)
        table.add_column("Singer", key="name")
        table.add_column("Last Added", key="last_added", width=12)
        table.add_column("# Turns", key="turns", width=10)
        table.add_column("Since Last Turn", key="since_last_turn", width=14)

    def _tick(self) -> None:
        if self.is_mounted:
            self._render_table()

    def action_switch_view(self) -> None:
        self.app.pop_screen()

    def action_refresh(self) -> None:
        self._render_table()

    def _compute_rows(self) -> list[dict[str, str]]:
        singers = list(self._model.known_singers)

        def sort_key(singer: str) -> Any:
            if self._sort_column == "name":
                return singer.lower()
            elif self._sort_column == "last_added":
                return self._model.singer_last_added.get(singer, datetime.min)
            elif self._sort_column == "turns":
                return self._model.singer_turns.get(singer, 0)
            elif self._sort_column == "since_last_turn":
                return self._model.singer_last_turn.get(singer, datetime.min)
            return singer

        singers.sort(key=sort_key, reverse=self._sort_reverse)

        rows: list[dict[str, str]] = []
        for s in singers:
            last_turn = self._model.singer_last_turn.get(s)
            elapsed = (datetime.now(timezone.utc) - last_turn) if last_turn else None
            last_added = self._model.singer_last_added.get(s)
            rows.append({
                "name": s,
                "last_added": last_added.strftime("%H:%M") if last_added else "—",
                "turns": str(self._model.singer_turns.get(s, 0)),
                "since_last_turn": _format_elapsed(elapsed) if elapsed else "never",
            })
        return rows

    def _render_table(self) -> None:
        if not self.is_mounted:
            return
        table = self.query_one("#fair_queue_table", DataTable)
        table.clear()
        rows = self._compute_rows()
        if not rows:
            table.add_row("Waiting for singers to join…", "", "", "", key="empty")
            return
        for i, row in enumerate(rows):
            table.add_row(row["name"], row["last_added"], row["turns"],
                          row["since_last_turn"], key=str(i))

    def on_data_table_header_clicked(self, event) -> None:
        col_key = event.column.key
        if self._sort_column == col_key:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = col_key
            self._sort_reverse = False
        self._render_table()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/test_app.py -v -k "fair_queue" -W error
```
Expected: All 3 new tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/karafun_intercept/app.py tests/test_app.py
git commit -m "feat: add FairQueueScreen with sortable table view"
```

---

## Task 3: Integrate Tab Navigation & Auto-Update

**Files:**
- Modify: `src/karafun_intercept/app.py` — add `Tab` binding + `action_switch_view` + `_table_screen` ref + `feed_snapshot` integration
- Test: `tests/test_app.py` — add 2 tests (Tab switch roundtrip, snapshot updates table)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_app.py`:

```python
def test_fair_queue_tab_roundtrip(status1_xml, status2_xml):
    app = KaraFunInterceptApp()

    async def main():
        async with app.run_test() as pilot:
            app.feed_snapshot(parse_status(status1_xml))
            app.feed_snapshot(parse_status(status2_xml))
            await pilot.pause()

            # Dashboard: queue list has items
            ql = app.query_one("#queue", OptionList)
            assert ql.option_count == 2

            # Tab -> table view
            await pilot.press("tab")
            await pilot.pause()
            assert app.query_one("#fair_queue_table", DataTable) is not None

            # Tab again -> back to dashboard
            await pilot.press("tab")
            await pilot.pause()
            assert app.query_one("#queue", OptionList) is not None

    _run(main())


def test_fair_queue_updates_on_snapshot(status1_xml, status2_xml):
    app = KaraFunInterceptApp()

    async def main():
        async with app.run_test() as pilot:
            app.feed_snapshot(parse_status(status1_xml))
            await pilot.pause()
            app.feed_snapshot(parse_status(status2_xml))
            await pilot.pause()

            # Table should reflect 3 singers (Alice, Bob, Cara)
            await pilot.press("tab")
            await pilot.pause()
            table = app.query_one("#fair_queue_table", DataTable)
            assert table.row_count == 3

    _run(main())
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/test_app.py -v -k "tab_roundtrip or updates_on_snapshot" -W error
```
Expected: FAIL — `feed_snapshot` doesn't call `_render_table`, `Tab` binding not registered on app.

- [ ] **Step 3: Implement Tab navigation + feed_snapshot integration**

Edit `KaraFunInterceptApp.BINDINGS` — add Tab binding:

```python
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("tab", "switch_view", "Table"),
    ]
```

Edit `KaraFunInterceptApp.__init__` — add table screen ref:

```python
        self._table_screen: FairQueueScreen | None = None
```

Edit `feed_snapshot` — add table re-render after `_render_all()`:

```python
    def feed_snapshot(self, snapshot: StatusSnapshot) -> None:
        notes = self._model.apply_status(snapshot)
        if notes:
            self._notifications.extend(n.message for n in notes)
            self._notifications = self._notifications[-MAX_NOTIFICATIONS:]
        self._render_all()
        if self._table_screen is not None:
            self._table_screen._render_table()
```

Add `action_switch_view` to `KaraFunInterceptApp` (after `on_mount`):

```python
    def action_switch_view(self) -> None:
        if self._table_screen is None:
            self._table_screen = FairQueueScreen(model=self._model)
        self.push_screen(self._table_screen)
```

- [ ] **Step 4: Run full test suite to verify everything passes**

Run:
```bash
pytest tests/test_model.py tests/test_app.py -v -W error
```
Expected: All tests pass.

Run:
```bash
ruff check src/karafun_intercept/app.py src/karafun_intercept/model.py tests/test_model.py tests/test_app.py
```
Expected: All checks passed.

- [ ] **Step 5: Commit**

```bash
git add src/karafun_intercept/app.py tests/test_app.py
git commit -m "feat: wire up Tab navigation and auto-update for fair-queue table"
```

---

## Final Verification

- [ ] Run full test suite: `pytest -W error` (all existing + new tests pass)
- [ ] Run linter: `ruff check src tests`
- [ ] Verify no circular imports: `python -c "from karafun_intercept.app import FairQueueScreen, KaraFunInterceptApp; print('OK')"`
