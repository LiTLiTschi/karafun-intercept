# Philosophy & Architectural Contracts

Strictly enforced rules that encode the project's mental model into verifiable constraints. Violations are always bugs — not style choices, not "fix later."

## Core Principle: Mental Model ↔ Codebase Alignment

The semantically-mental model of the app MUST always align with the resulting real-world behavior. When a change to the highest abstraction level (a base class) does not cause predictable, uniform changes in all semantically-inheriting subclasses, the architecture is broken.

The contracts below enforce this alignment mechanically.

## Refactoring Principle

Refactoring is welcome if it centralizes the logic and simplifies the codebase.

---

## Contract 1: Template Method — `super()` Mandate

**Statement:** Any subclass override of a Template Method (`handle_action`, `render`, `handle_raw_input`) MUST delegate unmatched cases to `super().method()` as the final fallthrough.

A terminal `return Stay()` / `return None` in an override that shadows a non-trivial base implementation is **always a bug**, because it silently swallows any future base-class behavior.

**Correct:**

```python
def handle_action(self, action: str) -> object:
    if action == "custom_thing":
        return self._handle_custom()
    return super().handle_action(action)  # all unmatched -> base class
```

**Wrong (generic sink — base-class behavior silenced):**

```python
def handle_action(self, action: str) -> object:
    if action == "cancel":
        ...
    if action == "back":
        ...
    return Stay()  # silently ignores any future base-class action
```

**Why it matters:** When a new universal action is added to the base menu class (e.g. `tab`, `page_up`), every subclass that calls `super()` inherits it automatically. Subclasses that end in `return Stay()` silently ignore it. The divergence between mental model and reality grows without any error or warning.

**Detection:** grep for `def handle_action` in subclasses -> verify the final `return` is `super().handle_action(action)` (or that the class is documented as a terminal override).

---

## Contract 2: Hook-Override Discipline

**Statement:** Base classes define public hooks. Subclasses MUST NOT re-implement control flow that the base class already provides.

In a base menu class, cursor navigation (up/down/enter/back/cancel) is base-class territory. Subclasses MAY add new branches before delegating to `super()`. They MUST NOT shadow base behavior with equivalent re-implementations.

**Example (allowed):**

```python
def handle_action(self, action: str) -> object:
    if action == "sub_import":
        return self._handle_import()
    return super().handle_action(action)
```

**Example (forbidden — re-implements back):**

```python
def handle_action(self, action: str) -> object:
    if action == "back":
        return Back()  # re-implementing what super() already does
    return Stay()
```

---

## Contract 3: `is_navigable` Truth Contract

**Statement:** Two arrow-dispatch pathways exist, and they are mutually exclusive per class.

| `is_navigable` | Arrow dispatch pathway | Mechanism |
| --- | --- | --- |
| `True` | Keymap arrow entries -> `handle_action` | Runner intercepts arrows, dispatches via keymap |
| `False` | `handle_raw_input` | Subclass receives raw arrow/escape codes directly |

A class MUST NOT use both pathways simultaneously. It MUST document which pathway it uses with a comment next to `is_navigable`.

**Detection:** grep for arrow codes (`\x1b[A`, etc.) in `handle_raw_input` + grep for `is_navigable` -> verify mutual exclusion.

---

## Contract 4: No Generic Sink Fallthroughs

**Statement:** A method ending in `return Stay()` (or equivalent terminal value) without any preceding `super().method()` call is a **generic sink** — it silently consumes all unmatched actions and prevents base-class behavior from propagating.

If this pattern is intentional (e.g. editor-mode menus that handle all input through `handle_raw_input`), it MUST be justified with an explicit comment explaining WHY base-class behavior is intentionally suppressed.

**Without documentation, it is a bug.**

---

## Contract 5: Run-In-Background Context Sensitivity

**Statement:** The `run_in_background` parameter for agent dispatch is context-sensitive, not mechanical.

| Parent session state | `run_in_background` | Rationale |
| --- | --- | --- |
| Parent is **blocked** waiting for agent result | `false` (foreground) | No useful conversation happens during wait |
| Parent is **continuing discussion** with user while agent works | `true` (background) | Don't make user stare at blank screen |
| Parent is teaching / explaining / discussing architecture | `true` (background) | Discussion should be uninterrupted |
| Multiple independent research tasks | `true` (background, parallel) | Send all in one message |
| Writer agent implementing a fix | `true` (background) | Parent can continue discussing principles |
| Reviewer agent auditing a diff | `false` (foreground) | Reviewer result is prerequisite for next action |

**Heuristic:** if the human is getting value from the conversation during the agent's run, use background. If the human would just wait, use foreground.

---

## Contract 6: YAGNI

**Statement:** Do not add features, abstractions, or complexity "just in case" they might be needed later. Implement only what is explicitly required by the current task or spec.

Every line of code that doesn't solve a current problem is a liability. Every abstraction layer that isn't used by at least two concrete consumers is overhead.

---

## Contract 7: Config is Flat

**Statement:** The application's config store is flat key-value. Never use nested objects or dotted keys — the config editor/parser/template all assume flat structure and break silently when nested.

Use `log_level`, not `logging.level`.

---

## Contract 8: DEBUG_VVV Logging — Log Everything

**Statement:** At the deepest debug level (`DEBUG - 2`, e.g. `DEBUG_VVV`), everything even theoretically loggable MUST be logged — as much detail as possible. This level is only used for agentic/debugging, so any and every detail that CAN be logged SHOULD be logged.

**Import pattern (project-specific path):**

```python
from <project>.logging._config import DEBUG_VVV
```

**Usage:**

```python
_log.log(DEBUG_VVV, "descriptive message with %s interpolation", some_value)
```

Every state transition, every decision branch, every value that might inform debugging should be surfaced at this level. No detail is too small. The cost of missing a log line during debugging is higher than the cost of logging it.

**Detection:** grep for the project's `DEBUG_VVV` import in new modules -> verify used pervasively in methods with branching logic or state transitions.

---

## Contract 9: Key Binding Discipline — One Key Per Action, Method Presence Detection

**Statement:** Every action string that a component handles MUST have a corresponding `_handle_{action}()` method on the component class (or inherited from a base class). The footer dynamically detects which actions are handled by checking for the presence of these methods, and only shows keys for actions whose handler exists.

This eliminates two bugs:

1. **Irrelevant keys** — `[Space] Select` shown on menus with nothing to select
2. **Duplicate keys** — `[↑] Scroll Up` and `[k] Scroll Up` for the same action

**No `GLOBAL_KEYMAP`.** The runner does not inject universal key bindings into every component's footer. Instead, base classes define their own default keymap + handlers:

| Base Class | `keymap` | Built-in Handler Methods |
| --- | --- | --- |
| Base menu | `{"q": "back", "escape": "cancel", "\r": "enter"}` | `_handle_back`, `_handle_cancel`, `_handle_enter`, `_handle_up`, `_handle_down` |
| Base popup | `{"q": "back", "escape": "cancel"}` | `_handle_back`, `_handle_cancel` |

Subclasses inherit both the key bindings AND the handler methods — nothing else to do.

**Dynamic detection rule** (enforced by the runner at render time):

```python
def render_footer(keymap, component):
    for key, action in keymap.items():
        has_handler = hasattr(component, f"_handle_{action}") and callable(
            getattr(component, f"_handle_{action}")
        )
        if has_handler:
            # Show this key in footer
```

**One key per action** — a component's `keymap` dict MUST NOT map multiple keys to the same action string:

```python
# CORRECT: one key per action
keymap = {"d": "dismiss"}

# WRONG: same action from two keys
keymap = {"d": "dismiss", "D": "dismiss"}

# WRONG: arrows AND vim keys both to scroll_up/down
keymap = {"\x1b[A": "scroll_up", "\x1b[B": "scroll_down", "k": "scroll_up", "j": "scroll_down"}
```

**Exemption:** The `q` + `escape` navigation pair is accepted terminal practice. Components may map both `q` and `escape` to the same navigation action (`"back"` or `"cancel"`), but no other keys may share that action.

**Correct pattern** (menu with a custom action):

```python
class MyMenu(BaseMenu):
    keymap = {"d": "dismiss"}  # footer auto-shows [d] Dismiss

    def _handle_dismiss(self) -> Any:
        ...  # presence of this method enables the footer entry
        return Stay()

    def handle_action(self, action: str) -> Any:
        if action == "dismiss":
            return self._handle_dismiss()
        return super().handle_action(action)  # Contract 1: super()
```

**Why this "just works":**

- A new subclass adding a handler method `_handle_wobble()` and a keymap entry `"w": "wobble"` automatically gets `[w] Wobble` in its footer — no other changes needed.
- Subclasses that don't override `handle_action()` at all still show `[q] Back  [Esc] Cancel  [↵] Enter` because the base class's handler methods are inherited.

**Enforcement:** Three-layer test:

1. `ast-grep` rule: a component's `keymap` must not have duplicate action values (same action from multiple keys)
2. `pytest` contract: for each component, every action in `keymap` must have a corresponding `_handle_{action}` method on the component's MRO
3. `ruff` lint: standard formatting

---

## Contract 10: Color Schema — Consistent Terminal Palette

Every UI style string derives from a single base color with hierarchy expressed through **bold**, **italic**, and **dim** attributes. The only exception is red/amber for semantic error/warning markers.

### Palette

| Role | Style | Used For |
| --- | --- | --- |
| Primary highlight | `bold bright_magenta` | cursor, focused item label, action items, active tab, header title, spinner, category headers |
| Sub-header | `bold italic bright_magenta` | type/sub-type headers within categories |
| Unhighlighted action | `bright_magenta` | action items when not focused |
| Metadata | `dim` | breadcrumbs, separators, key hints, "… N more" rows, inactive elements |
| Error / debug | `bold red` | error messages, failure tables, error panels |

### Panel Borders (`panel_border_style`)

| Color | Used By |
| --- | --- |
| base highlight color | all popups and menus |
| `red` | error panels only (constructed inline) |

### Hierarchical Rule

Content follows exactly three levels of depth:

```text
Category header (bold bright_magenta)        <- Level 1
├── Type header (bold italic bright_magenta)  <- Level 2
│   └── Selectable item (bold bright_magenta) <- Level 3 (when focused)
```

Action items are rendered **outside** this hierarchy — they use `bright_magenta` (unhighlighted) / `bold bright_magenta` (highlighted) with a `dim` separator and no checkbox.

### Exclusions

- **Error/debug panels** keep their red semantic color.
- **Data-validation warning indicators** keep `bold yellow` — this is a semantic marker, not a UI decoration.

### Implementation Rule

All style strings are inline at the point of use. There is no theme module. Never introduce a color other than the base highlight color, `red`, or `dim` for UI styling — any deviation must be documented with a comment explaining the semantic reason.

---

## Contract 11: Progress Popup Logging Level

**Statement:** All workflows MUST use standard Python `logging` for progress reporting that should appear in the progress display. A config key (e.g. `progress_popup_logging_level`) controls the minimum log level bridged into the active progress popup via a popup log bridge handler.

### Mechanism

A popup log bridge attaches a handler to a named Python logger. The handler's `emit()` filters each record: if `record.levelno < self._min_level`, it is dropped. Only records at or above the configured threshold reach the popup's `log()` method.

### Config values

| Config value | Logger level appearing in popup |
| --- | --- |
| `CRITICAL` | Only `CRITICAL` records |
| `ERROR` | `ERROR` and above |
| `WARNING` | `WARNING` and above |
| `INFO` | `INFO` and above |
| `DEBUG` | `DEBUG` and above (includes all workflow progress) |
| `OFF` | No log records bridged |

Default: `"INFO"`.

### Workflow rules

1. **Per-file/per-item progress** MUST be logged at `logging.DEBUG` level, not the deepest debug level. This is the standard level for detailed progress that users opt into by setting `progress_popup_logging_level` to `"DEBUG"`.

2. **Batch-level status** (start, completion, summary counts) MUST be logged at `logging.INFO` level so they always appear in the popup at default verbosity.

3. **Workflow implementation pattern** — a workflow that wants its logger bridged to the popup MUST use the popup log bridge for its named logger:

   ```python
   from <project>.rich.popup_log_bridge import PopupLogBridge

   with PopupLogBridge("project.workflow.my_workflow", context, "DEBUG"):
       ...  # all logging at DEBUG+ reaches the popup
   ```

   The level argument should come from the workflow's own level reader or be read directly from config.

4. **`context.log()` and `context.set_status()` are NOT a replacement for structured logging.** They provide immediate direct feedback, bypassing level filtering. Use them for:
   - One-shot start/end messages
   - Error summaries
   - Status line updates (not individual item progress)

   Use the logger's `info()`/`debug()` for per-item progress that respects the user's configured verbosity.

5. **Workflow code MUST NOT use the deepest debug level (`DEBUG_VVV`) for progress that should ever appear in the popup.** That level is a firehose for debugging only. Popup-bridge filtering is configured independently via `progress_popup_logging_level` — they serve different purposes.

### Example

```python
_log = logging.getLogger("project.workflow.copy_files")

# Per-file progress (visible in popup only when level=DEBUG)
_log.debug("Copying: %s", relative_path)

# Batch summary (always visible in popup)
_log.info("Copied %d files to %s", count, target)
```

**Detection:** verify each workflow uses `_logger.debug()` for per-item progress and `_logger.info()` for batch summaries; verify the popup log bridge is used where the logger should feed into the popup; verify `DEBUG_VVV` is NOT used for popup-visible progress.

---

## Enforcement

These contracts are **part of code review**, not optional guidelines. Any change that violates a contract has produced buggy code. The fix is not to add a comment — it's to restructure the code to obey the contract.

When in doubt, ask: **"Would this change to a base class propagate correctly to all subclasses?"** If the answer is no, the architecture is wrong.
