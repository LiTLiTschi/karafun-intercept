# karafun-intercept

A [Textual](https://textual.textualize.io/) terminal user interface (TUI) that observes the local KaraFun Player over its Player Control WebSocket (`ws://localhost:57570`), parses XML status updates, and tracks turn order, singers, new-song notifications, and per-user recency.

## Requirements

- Python >= 3.9
- [uv](https://docs.astral.sh/uv/) (for install/update)
- [Textual](https://textual.textualize.io/) and [websockets](https://pypi.org/project/websockets/) (installed automatically)
- A GitHub token with `repo` scope (the repo is private)

## Install

### Prerequisites

- **[uv](https://docs.astral.sh/uv/)** — install via `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **GH_TOKEN** — set a GitHub token with `repo` scope:

  ```bash
  # Option A: Use gh CLI (recommended)
  export GH_TOKEN="$(gh auth token)"

  # Option B: Manual PAT (Settings → Developer settings → Personal access tokens)
  export GH_TOKEN=ghp_xxxxxxxxxxxx
  ```

### Install / Update (one-liner)

```bash
export GH_TOKEN="$(gh auth token)"
curl -fsSL "https://${GH_TOKEN}@raw.githubusercontent.com/LiTLiTschi/karafun-intercept/master/scripts/install.sh" | sh
```

This downloads the install script via authenticated curl, runs it, and installs the `karafun` command globally via `uv tool install`.

After install, the `karafun` command is available globally:

```bash
karafun version     # show version
karafun intercept   # launch the Textual TUI
```

Alternatively, set a PAT manually:

```bash
export GH_TOKEN=ghp_xxxxxxxxxxxx
curl -fsSL "https://${GH_TOKEN}@raw.githubusercontent.com/LiTLiTschi/karafun-intercept/master/scripts/install.sh" | sh
```

### Updating

```bash
karafun update      # rebuild from latest commit on the selected branch
```

`karafun update` rebuilds from the configured branch at GitHub origin (see `karafun branch-show` / `karafun branch-list` / `karafun branch-switch N` to select a branch) and reinstalls via `uv tool install --force`.

If `karafun update` fails, use `uv` directly to force reinstall:

```bash
uv tool install --upgrade --force git+https://${GH_TOKEN}@github.com/LiTLiTschi/karafun-intercept.git
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
