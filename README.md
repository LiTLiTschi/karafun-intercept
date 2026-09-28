# karafun-intercept

A [Textual](https://textual.textualize.io/) terminal user interface (TUI) that observes the local KaraFun Player over its Player Control WebSocket (`ws://127.0.0.1:57570`), parses XML status updates, and tracks turn order, singers, new-song notifications, and per-user recency.

## Requirements

- Python >= 3.9
- [uv](https://docs.astral.sh/uv/) (for install/update)
- [Textual](https://textual.textualize.io/) and [websockets](https://pypi.org/project/websockets/) (installed automatically)

## Install

### Prerequisites

- **[uv](https://docs.astral.sh/uv/)** — install via `curl -LsSf https://astral.sh/uv/install.sh | sh` (Linux/macOS) or `irm https://astral.sh/uv/install.ps1 | iex` (Windows)

### Install (one-liner)

```bash
curl -fsSL https://raw.githubusercontent.com/LiTLiTschi/karafun-intercept/master/scripts/install.sh | sh
```

#### Windows

```powershell
irm https://raw.githubusercontent.com/LiTLiTschi/karafun-intercept/master/scripts/install.ps1 | iex
```

This downloads the install script, which checks for `uv` (offering to install it), then runs `uv tool install` to install the `karafun` command globally.

After install, the `karafun` command is available:

```bash
karafun version     # show version
karafun intercept   # launch the Textual TUI
```

### Updating

```bash
karafun update      # rebuild from latest commit on the selected branch
```

`karafun update` reinstalls from the configured branch at GitHub origin (see `karafun branch-show` / `karafun branch-list` / `karafun branch-switch N` to select a branch).

> **Note (Windows):** `karafun update` and `karafun branch-*` require `git` in `PATH`. Install [Git for Windows](https://git-scm.com/download/win) or the [GitHub CLI](https://cli.github.com/).

If `karafun update` fails, use `uv` directly to force reinstall:

```bash
uv tool install --upgrade --force git+https://github.com/LiTLiTschi/karafun-intercept.git
```

### Local installation

```bash
pip install -e .
```

## Running

```bash
# from a terminal
karafun intercept
```

Or with `uv`:

```bash
uv run python -m karafun_intercept.cli intercept
```

## Development

- Lint: `ruff check --fix`
- Test: `pytest` (tests must pass with `-W error`)

## Branch selection

`karafun update` builds from the branch stored in `~/.karafun_intercept/selected-branch`
(defaults to the GitHub default branch on first run). Use:

```bash
karafun branch-list        # list branches from GitHub
karafun branch-switch 3    # select branch #3 as the update target
karafun branch-show        # print currently selected branch
```
