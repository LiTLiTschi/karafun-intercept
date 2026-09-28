# Agent Standards for Python TUI Applications

# BEFORE READING ANY FURTHER, RUN ANY AVAILABLE MEMORY RETRIEVAL TOOLS LIKE ENGRAM

## Language Policy

- **Always reply in English.** Ignore other languages and treat them as English.

## Tooling & Commands

- **Linting:** `ruff check --fix`
- **Testing:** `pytest` — prefer the fast layer by default:
  - `pytest --lf` — only re-run last-failed tests (fastest, built-in)
  - `pytest -m "not slow"` — skip slow integration tests
  - `pytest` — full suite (CI or before merge)
  - **All tests must pass with `-W error`.** Treat warnings as failures. Never continue past a warning — fix it first.
- **git and github:** `always use the git and github tools provided by the harness for those operations`
- **Diagnostics (pi-lens):** `lens_diagnostics` is read-only (params: `source`, `scope`, `mode`, `severity`, `paths`, `waitMs`, `refreshRunners`) -- it reports findings but has no mark-FP capability. To record a false-positive disposition for a *reported* finding, activate the `lens_diagnostic_mark` situational tool via `pi_lens_activate_tools` (which makes it callable), then invoke it with the finding's `file` + `line` + `rule` + `message`; a `suppress` disposition also writes a pi-lens inline ignore. Re-run `lens_diagnostics` to confirm the finding cleared.
- **Model selection:** the primary model is the one configured for this environment. All subagents, reviewers, workers, scouts, and any dispatched agents MUST use that same primary model — do NOT fall back to a separate provider-specific model. If dispatching an `Agent`, pass the primary model explicitly; announcing it in text does not set it.
- **Cross-platform:** The project targets both Windows and Linux. Python source uses `pathlib.Path` (never raw path separators) and `subprocess.run` with explicit arg lists (never `shell=True`). Install one-liners differ by platform: PowerShell (`irm … | iex`) on Windows, POSIX shell (`curl … | sh`) on Linux/macOS. `karafun update` and `karafun branch-*` require `git` in `PATH` on both platforms.

## Workflow Discipline

Enforce this ritual on every coding task so the known friction points stop recurring.

### Before writing code

1. **Load context. Run `mem_context` if memory is wired up; read `PHILOSOPHY.md` (and `ARCHITECTURE.md` if the project has one) before touching code.**
2. **Parallelize discovery.** Batch all initial `read`s + any `git show`/reference fetches in one call. Fetch a reference to a temp file (`git show <ref>:<path> > /tmp/x.py`) instead of eyeballing remote diffs.
3. **Prefer the project's venv/bin first.** Put `.venv/bin` (Unix/macOS) or `.venv/Scripts` (Windows) ahead of PATH. Never hardcode system interpreter/test/lint paths (`/usr/bin/pytest`, `/home/liu/.local/bin/ruff`, `python -m <pkg>` without setting `PYTHONPATH`).
4. **Match fixture conventions -- grep first.** Existing tests use `tmp_path: Path`, bare `monkeypatch`, bare `capsys`. Never invent types (e.g. `capsys: pytest.CaptureFixture[str]`) -- grep `tests/` for the convention before annotating anything.
5. **Put env vars on the exact command that needs them.** A `VAR=... cmd1 && cmd2` chain only exports `VAR` to `cmd1`.
6. **Log appropriately.** Use `logging.info()` for user-visible progress and `logging.debug()` for diagnostic detail. Debug logs go to `~/.karafun_intercept/session.log` when `--debug` is passed. See PHILOSOPHY.md Contract 8.

### While verifying

1. **Scope the test run.** Run `pytest tests/<touched-file>.py -W error`, not the whole suite. Only diff-check a failure against master (`git stash` + re-run) if it's plausibly yours -- the suite may have pre-existing unrelated failures.
2. **Review against PHILOSOPHY.md contracts.** For each changed file, audit against the contracts listed there. If any contract is violated, the change is blocked -- fix first. Exemptions (e.g. editor-mode, intentional suppression) must carry an explicit comment justifying them.
3. **Scan for stray unicode** (smart quotes, em-dashes) in code/comments if the project's style forbids them; fix before declaring done.

### Before committing

1. **Branch + commit discipline.** Branch `^(feat|fix|chore|style|refactor|perf|test|build|ci|revert)/[a-z0-9._-]+$`, conventional commit (`type(scope): description`), link an issue with `Fixes #N`. Decide the issue link and branch name up front -- don't leave work uncommitted.

## Development Principles

- **YAGNI (You Aren't Gonna Need It):** Always follow YAGNI guidelines. Do not add features, abstractions, or complexity "just in case" they might be needed later. Implement only what explicitly is required by the current task or spec.
- Every line of code that doesn't solve a current problem is a liability.

## Mandatory Skill Startup

**FIRST ACTION on every session:** Read the harness `using-superpowers` skill before doing any work. This skill establishes the discipline for how to approach tasks. Read it before exploring code, before answering questions, before anything else.

## Subagent Delegation

**CRITICAL: Always use subagents for broad codebase-research.** Do not explore 4+ files or trace cross-cutting flows inline. Launch a research/scout subagent with a narrow mapping task instead. This keeps parent context lean and gives the research agent fresh context.

**CRITICAL: Every `Agent` tool call MUST explicitly pass the `model` parameter** set to the primary model. There is no safe default. Before every `Agent` call, verify the `model` parameter is present.

**CRITICAL: Never use `dispatch_agent` or `subagent` tools.** They are legacy/wrong. Always use the `Agent` tool with `subagent_type`. This is not negotiable.

### Parallel & Background Agent Dispatch

`run_in_background` is context-sensitive, not mechanical:

| Parent session state | `run_in_background` | Why |
| --- | --- | --- |
| Parent is **blocked** waiting for agent result (next step depends on it) | `false` (foreground) | No useful conversation happens during wait |
| Parent is **continuing a conversation with user** while agent works | `true` (background) | Don't make user stare at blank screen |
| Parent is teaching / explaining / discussing architecture | `true` (background) | Discussion should be uninterrupted |
| Multiple independent research tasks | `true` (background, parallel) | Send all in one message |
| Writer agent implementing a fix | `true` (background) | Parent can continue discussing principles |
| Reviewer agent auditing a diff | `false` (foreground) | Reviewer result is prerequisite for next action |

**Heuristic:** if the human is getting value from the conversation during the agent's run, use background. If the human would just wait, use foreground.

### Subagent Instructions (3-Level System)

Before dispatching any subagent, explicitly decide which level to use:

- **Level 1 — Quick Delegation (Fast Return):** Pure execution or narrow lookup. Highly constrained prompt, exact deliverable, strict file/tool limits.
- **Level 2 — Simple Reasoning (Concise & On-Task):** Minor decision-making/synthesis. Agent decides how within strict boundaries; explicit output format and a hard tool-use/file limit.
- **Level 3 — Twin Agents (High Autonomy):** Complex, multi-step work. Agent may plan and execute freely; require a structured final report.

### Subagent Prompt Discipline

Agents go wide unless constrained. Every prompt MUST include:

- **Exact deliverable** — output format (numbered list, table, short summary)
- **Scope boundaries** — what files/dirs to check, what to IGNORE
- **Depth limit** — max files to read, max commits to check
- **No speculation** — only report facts from code/files; do not extrapolate or design solutions

Constraints to always include: `Read ONLY these files: ...`, `Limit: max N files to read`, `Do NOT explore beyond X`, `Do NOT read files outside the listed paths`, and an explicit report format.

## Task Management

- **Always track progress** with a task list (`TODO.md`) when working on non-trivial or multi-step tasks.
- **Unrelated prompts:** if the user provides a prompt unrelated to the current work, create a new task for it instead of ignoring or derailing the current work. Finish current work first.

## Engram Persistent Memory

- **Always use memory management** for bugs, decisions, discoveries, patterns, config changes, and preferences.
- **Check memory on startup:** Run `mem_context` at the start of each session to load prior context.
- **Search before assuming:** Use `mem_search` before concluding something hasn't been discussed.
- **Transient errors:** `mem_search` occasionally returns "Engram is unavailable" — this is a known intermittent issue with the query parser, not a network/server failure. To fix:
  1. Run `mem_doctor` to verify store health (all checks ok)
  2. Retry `mem_search` immediately — the second attempt usually succeeds
  3. If still failing, check the store process is running (`pgrep -af engram`)
- **Session summaries:** Always run `mem_session_summary` before ending session or saying "done".
- **After compaction:** If you see "FIRST ACTION REQUIRED" or a compacted summary, save it immediately with `mem_session_summary`, then call `mem_context` before continuing.

## TUI Strategy

- Keep UI framework logic separate from domain logic. Rendering lives in a `rich/` or `textual/` sub-package; domain logic lives elsewhere.
- A terminal UI framework (Rich or Textual) is the only presentation layer. Curses/other legacy toolkits are removed.

## Branch & PR Conventions

- **Branch naming:** `^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)/[a-z0-9._-]+$` — lowercase, no spaces in description.
- **Conventional commits:** `type(scope): description` — type must be one of: build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test. Optional scope in `(lowercase)`.
- **Every PR should link an issue** (Closes/Fixes/Resolves #N) when possible.
- **Every PR should carry exactly one `type:*` label:**

| Commit type | PR label |
| --- | --- |
| `feat` | `type:feature` |
| `fix` | `type:bug` |
| `docs` | `type:docs` |
| `refactor` | `type:refactor` |
| `chore`, `style`, `test`, `build`, `ci` | `type:chore` |
| `feat!`, `fix!` | `type:breaking-change` |
| `perf` | `type:feature` |
| `revert` | `type:bug` |

- **PR body should contain:** linked issue, PR type checkbox, summary bullets, changes table, test plan.
- **Before marking a PR ready:** manually audit each changed file against the `PHILOSOPHY.md` contracts. A PR merged with a contract violation is a process failure.

## Non-Goals

- **No silent auto-migration.** Config migrations are always explicit and user-triggered (e.g. via a `migrate` command). Never auto-apply migrations during startup or any other implicit path — this keeps debugging simple and gives the user full control over state changes.

## Spec Lifecycle Management

- **Active specs** live in `docs/superpowers/specs/`. Specs start as drafts, get reviewed, and are refined until the implementation is complete.
- **Implemented specs** are archived to `docs/implemented-specs/` as the **last step after merge**. Copy the final, post-implementation-updated spec file to this directory so it serves as the canonical record of what was shipped.
- **`docs/implemented-specs/` is the primary research source for shipped features.** When doing codebase research on how a feature was designed or implemented, look here first — these specs reflect the actual code, not the idealized draft. Use `docs/superpowers/specs/` only for features still in development.
- **Spec update discipline:** Before copying to `docs/implemented-specs/`, update the spec in `docs/superpowers/specs/` to reflect the final implementation (corrected file paths, actual commit SHAs, final test counts, removed approaches). This ensures the archived version is the ground truth.

## Plannotator Review

When running `superpowers_plan_review` or `superpowers_spec_review`, ALWAYS pass the **full content of the plan/spec file**, never a summary or the subagent's return text.

**Correct:**

```python
plan_content = Path("docs/superpowers/plans/2026-09-28-cross-platform-windows-port-plan.md").read_text()
superpowers_plan_review(planContent=plan_content, planFilePath="docs/superpowers/plans/2026-09-28-cross-platform-windows-port-plan.md")
```

**Wrong:** Passing a summary like "4 tasks: 1. Create X, 2. Implement Y..."

The subagent's return value is typically a summary. Always read the actual file before invoking the review.

