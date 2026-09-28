# Fair-Queue Table View — Design Spec

> **Status:** Draft
> **Goal:** Add a full-screen, auto-updating table view to the Karafun Intercept TUI that helps users manage the song queue fairly — preventing the same people always taking turns and ensuring new joiners don't wait too long.
> **Approach:** New Textual `Screen` with a `DataTable`, sharing the existing `SessionModel`.

---

## 1. Overview

The Karafun Intercept TUI currently shows a dashboard with current song, queue, singer roster, and notifications. This spec adds a **second full-screen view** — a fair-queue table — accessible via `Tab`. The table displays per-singer metrics (last added, turn count, time since last turn) and supports sortable column headers for manual fairness auditing.

## 2. Scope

### In Scope

- Four columns: **Singer**, **Last Added** (HH:MM clock time), **# Turns**, **Since Last Turn** (HH:MM elapsed)
- `DataTable`-based sortable columns (click to sort ascending, click again to sort descending)
- `Tab` key to switch between dashboard and table view
- Auto-update: 1-second live timer for elapsed-time columns + re-render on new player snapshots
- Table shows ALL known singers (not just those currently queued) so fairness can be audited
- Model extensions to track per-singer turn/add timestamps and counts

### Out of Scope (YAGNI)

- No recommendation/priority column (deferred to future spec)
- No queue reordering, singer removal, or playback control from the table
- No configuration options (sort defaults are hardcoded)
- No persistence across app restarts (state is in-memory during the session)

## 3. Architecture

The table is a **new `Screen` subclass** that shares the existing `SessionModel` instance. The dashboard screen (`KaraFunInterceptApp`) is unchanged except for a new `Tab` binding that pushes the table screen.

```
┌─────────────────────────┐
│  KaraFunInterceptApp    │  ← existing dashboard (unchanged)
│  ┌─ Tab → FairQueueScreen │
└──────┬─────────────┬────┘
       │             │
       │             │  (shared SessionModel instance)
       ▼             ▼
┌───────────────┐  ┌───────────────┐
│ SessionModel  │  │ KarafunClient │
│ (extended)    │  │ (unchanged)   │
└───────▲───────┘  └───────▲───────┘
        │                    │
        │                    │  (existing feed_snapshot path)
        └────────────────────┘
```

Key decisions:
- **New Screen:** `FairQueueScreen(textual.app.Screen)` using `textual.widgets.DataTable`
- **Shared model:** `FairQueueScreen.__init__` receives `model: SessionModel` — no duplication
- **Own timer:** `set_interval(1.0, self._tick)` for live elapsed-time updates
- **Own CSS/bindings:** independent lifecycle, easy to test

## 4. Data Model Extension (SessionModel)

`SessionModel.apply_status()` is extended to compute 4 new fields. These persist across idle states (like existing recency dicts).

### New Fields

| Field | Type | Meaning |
|---|---|---|
| `singer_last_added` | `dict[str, datetime]` | Clock time when a singer's song first appeared in a snapshot (new to the queue) |
| `singer_turns` | `dict[str, int]` | Count of turns — incremented when their song is front-of-queue AND `state == "playing"` |
| `singer_last_turn` | `dict[str, datetime]` | Clock time of their most recent turn (front + playing) |
| `_seen_song_keys` | `set[tuple[str, str]]` | `(title, artist)` pairs from the *previous* snapshot — used to detect new queue additions |

### Computation in `apply_status()`

1. **New-add detection** (`singer_last_added`): Before processing, compare current queue items (by `(title, artist)`) against `_seen_song_keys`. For each new item (not in prev set) that has a `singer`, set `singer_last_added[singer] = now`. Then replace `_seen_song_keys` with the current set of `(title, artist)` pairs.

   **Rationale:** A singer adding a *new* song (different title/artist) updates `last_added`. Re-queuing the same song that's already known does not.

2. **Turn detection** (`singer_turns`, `singer_last_turn`): When `snapshot.state == "playing"` and `snapshot.queue[0].singer` is not `None`, this is a turn for that singer. Increment `singer_turns[singer]` and set `singer_last_turn[singer] = now`.

   **Dedup:** Use a new `_last_scored_turn_singer: str | None` guard (parallel to existing `_front_singer`) to avoid double-counting the same singer across consecutive identical snapshots. Only increment when the front-playing singer differs from the last scored turn singer.

3. **All timestamps** use the model's injected `now` callable (deterministic in tests via `fake_now` fixture).

### Exposed Read API

```python
# Public attributes on SessionModel (initialized in __init__):
singer_last_added: dict[str, datetime]    # clock time of last new song add
singer_turns: dict[str, int]             # turn count per singer
singer_last_turn: dict[str, datetime]   # clock time of last turn
```

The model does NOT format dates or compute elapsed time — that is TUI rendering logic. The TUI reads the raw `datetime` values and formats them.

## 5. Table Screen UI (`FairQueueScreen`)

### Class

```python
class FairQueueScreen(Screen):
    """Full-screen sortable table of singer fair-queue metrics."""

    BINDINGS = [
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
        self.set_interval(1.0, self._tick)  # live timer for elapsed columns
```

### Columns

| Column Key | Header | Data Source | Format |
|---|---|---|---|
| `name` | Singer | `model.known_singers` | Singer name string |
| `last_added` | Last Added | `model.singer_last_added[singer]` | `HH:MM` (clock time, e.g. `14:32`) or `—` if never |
| `turns` | # Turns | `model.singer_turns.get(singer, 0)` | Integer string |
| `since_last_turn` | Since Last Turn | `now - model.singer_last_turn[singer]` | `HH:MM` elapsed (e.g. `18:22`) or `never` |

### Table setup

```python
def _setup_table(self) -> None:
    table = self.query_one("#fair_queue_table", DataTable)
    table.add_column("Singer", key="name")
    table.add_column("Last Added", key="last_added", width=12)
    table.add_column("# Turns", key="turns", width=10)
    table.add_column("Since Last Turn", key="since_last_turn", width=14)
```

### Row computation & sorting

```python
def _compute_rows(self) -> list[dict[str, str]]:
    """Return formatted rows sorted by current sort column/reverse."""
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

    rows = []
    for s in singers:
        last_turn = self._model.singer_last_turn.get(s)
        elapsed = datetime.now(timezone.utc) - last_turn if last_turn else None
        rows.append({
            "name": s,
            "last_added": (self._model.singer_last_added.get(s, datetime.min)
                           .strftime("%H:%M") if s in self._model.singer_last_added else "—"),
            "turns": str(self._model.singer_turns.get(s, 0)),
            "since_last_turn": _format_elapsed(elapsed) if elapsed else "never",
        })
    return rows
```

**`_format_elapsed`:** Converts a `timedelta` to `HH:MM` string (e.g. 18 min 22 sec → `18:22`). Uses total seconds.

### Column header click → sort

```python
def on_data_table_header_clicked(self, event: events.HeaderClicked) -> None:
    col_key = event.column.key  # "name" / "last_added" / "turns" / "since_last_turn"
    if self._sort_column == col_key:
        self._sort_reverse = not self._sort_reverse
    else:
        self._sort_column = col_key
        self._sort_reverse = False
    self._render_table()
```

### Live timer

```python
def _tick(self) -> None:
    """Called every 1 second — refreshes elapsed-time columns."""
    table = self.query_one("#fair_queue_table", DataTable)
    if table.is_mounted:
        self._render_table()
```

### Render

```python
def _render_table(self) -> None:
    table = self.query_one("#fair_queue_table", DataTable)
    table.clear()
    rows = self._compute_rows()
    for i, row in enumerate(rows):
        table.add_row(row["name"], row["last_added"], row["turns"], row["since_last_turn"], key=str(i))
```

## 6. Navigation & Key Bindings

| Key | On Dashboard | On Table Screen |
|---|---|---|
| `Tab` | `action_switch_view()` → push `FairQueueScreen` | `action_switch_view()` → pop screen (back to dashboard) |
| `q` | `action_quit()` (existing) | `action_quit()` (quits app) |
| `escape` | `action_quit()` (existing) | `action_quit()` (quits app) |
| `r` | `action_refresh()` (existing) | `action_refresh()` → re-render table from model |
| Click column header | N/A | Sort by column (asc → desc) |

**Binding discipline** (PHILOSOPHY Contract 9): One key per action. `q` + `escape` exempted for quit. The table screen's `Tab` binding is `switch_view`, distinct from the dashboard's `Tab` binding (same action name, different context).

### Dashboard integration

```python
# In KaraFunInterceptApp:
BINDINGS: ClassVar[list[BindingType]] = [
    Binding("q", "quit", "Quit"),
    Binding("escape", "quit", "Quit"),
    Binding("r", "refresh", "Refresh"),
    Binding("tab", "switch_view", "Table"),  # NEW
]

def action_switch_view(self) -> None:
    if not self._table_screen:
        self._table_screen = FairQueueScreen(model=self._model)
    self.push_screen(self._table_screen)
```

## 7. Auto-Update Mechanism

Two refresh pathways:

1. **Snapshot-driven:** `feed_snapshot()` → `model.apply_status()` → model state changes. Both screens need to re-render. The dashboard re-renders via existing `_render_all()`. The table screen re-renders by subscribing: `KaraFunInterceptApp` calls `self._table_screen._render_table()` when a table screen is active and a new snapshot arrives.

   ```python
   # In KaraFunInterceptApp.feed_snapshot():
   def feed_snapshot(self, snapshot):
       notes = self._model.apply_status(snapshot)
       # ... existing notification logic ...
       self._render_all()
       # NEW: if table screen is active, re-render it
       if self._table_screen is not None and isinstance(self.screen, FairQueueScreen):
           self._table_screen._render_table()
   ```

2. **Live-timer-driven:** `FairQueueScreen.set_interval(1.0, self._tick)` → `_tick()` → `_render_table()`. This keeps the "Since Last Turn" column ticking in real-time even when no new snapshots arrive. The timer is scoped to the screen — it is automatically cancelled when the screen is popped (Textual lifecycle).

## 8. Error Handling

| Scenario | Behavior |
|---|---|
| Player not running | Table shows all known singers with stale data. Footer shows `connecting…` style message. No crash. |
| No singers known yet | Table body is empty; shows placeholder text `"Waiting for singers to join…"` centered in the table area. |
| Singer has never taken a turn | `# Turns` = `0`, `Since Last Turn` = `never` (sortable — sorts last in ascending order) |
| Screen popped while timer fires | `_tick()` checks `table.is_mounted` before rendering — no `NoActiveApp` error |
| Snapshot arrives while table not active | No re-render triggered (guarded by `isinstance(self.screen, FairQueueScreen)`) |
| Sort on column with missing data | `datetime.min` sentinel for never-seen singers, `0` for turn count — consistent, deterministic sort |

## 9. Testing Strategy

### New test fixtures

- `status3_xml` — a snapshot where Alice (already known) adds a *second* song with a different title. Used to test that `singer_last_added` updates on new songs by an existing singer, while `singer_last_seen` and `NewSinger` behavior remain correct.

### New tests

| Test | What it verifies | Tools |
|---|---|---|
| `test_fair_queue_turn_tracking` | `singer_turns` increments only when front singer + playing; dedup across consecutive snapshots | `SessionModel` with `fake_now` + STATUS1/STATUS2 |
| `test_fair_queue_last_added` | `singer_last_added` updates when a known singer adds a new song (diff tracking); does NOT update for re-seen songs | `SessionModel` + STATUS1 + status3 fixtures |
| `test_fair_queue_idle_no_turn` | Idle state does not increment turns; existing turn counts preserved | `SessionModel` + idle snapshot |
| `test_fair_queue_tab_switch` | `Tab` on dashboard pushes `FairQueueScreen`; `Tab` on table pops back | `pilot` on `KaraFunInterceptApp` |
| `test_fair_queue_sorting` | Clicking column headers cycles asc/desc sort correctly | `pilot` on `FairQueueScreen` in `run_test()` |
| `test_fair_queue_live_timer` | After 1.1s, `Since Last Turn` column reflects elapsed time | `pilot.pause(1.1)` on the screen's timer |
| `test_fair_queue_empty_state` | No singers → table shows placeholder message | `FairQueueScreen` with empty model |

All tests pass with `-W error`. `ruff check` clean.

## 10. PHILOSOPHY Contract Compliance

| Contract | Compliance |
|---|---|
| **Contract 9 (Key Binding Discipline)** | One key per action: `tab`→`switch_view`, `q`/`escape`→`quit`, `r`→`refresh`. `q`+`escape` pair exempted. Footer auto-derived from handler method presence. |
| **Contract 10 (Color Palette)** | Uses project base highlight color via Textual CSS variables (`$primary`, `$text`). No new colors introduced. |
| **Contract 12 (Cross-Platform)** | Uses `datetime.now(timezone.utc)` and `strftime` — no platform-specific time APIs. No `sys.platform` checks. |

## 11. Files Modified / Created

| File | Change |
|---|---|
| `src/karafun_intercept/model.py` | Add 4 new fields to `SessionModel.__init__`; extend `apply_status()` with turn/add tracking |
| `src/karafun_intercept/app.py` | Add `Tab` binding + `action_switch_view()` to `KaraFunInterceptApp`; add `FairQueueScreen` class |
| `tests/conftest.py` | Add `status3_xml` fixture |
| `tests/test_model.py` | Add turn-tracking, last-added, idle-no-turn tests |
| `tests/test_app.py` | Add tab-switch, sorting, live-timer, empty-state tests |
