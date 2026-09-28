# Cross-Platform Windows Port — Design Spec

> **Status:** Approved — implemented and verified. Cross-platform support (Windows + Linux) is now in CI.
> **Goal:** Make karafun-intercept installable, runnable, and testable on both Windows and Linux from the start, with a PowerShell one-liner install for Windows and CI enforcing both platforms.
> **No code is written until this spec is approved.**

---

## 1. Overview & Goal

**Goal.** Port the project so it can be built, installed, updated, and tested on both Windows and Linux from the start — no separate "port more later." The Windows install one-liner uses PowerShell.

**Key insight from research.** The KaraFun *Player* application is Windows-only (`docs/research/karafun-api/07-known-limitations.md`). On Linux the app starts but cannot connect to `ws://localhost:57570` (no player to reach), showing "connecting…". This is acceptable: the *code* is cross-platform, the *tests* are hermetic (fake transports), and CI validates both. The user can develop or run the observer on any OS; only the live player connection requires Windows.

---

## 2. Scope

### In scope (this change)

- A Windows PowerShell install one-liner that mirrors the existing bash one-liner.
- `karafun update` and `karafun branch-*` working on both platforms (already cross-platform Python — verify, no changes expected).
- CI that runs `ruff check` + `pytest -W error` on both `ubuntu-latest` and `windows-latest`.
- `.gitignore` entries for Windows artifacts.
- `AGENTS.md` and `PHILOSOPHY.md` updated to encode the cross-platform requirement as a persistent contract.

### Out of scope (YAGNI)

- Standalone Windows `.exe` packaging (PyInstaller / cx_Freeze). `uv tool install` already produces a working `karafun.exe` shim on Windows; bundling the interpreter would create a parallel update path for no benefit.
- Windows-specific installers (MSI, MSIX, `.bat` launchers).
- Changing any core Python logic — the source is already platform-neutral.

---

## 3. Findings (current state)

### Already cross-platform (no changes needed)

| Component | Evidence |
| --- | --- |
| `cli.py` state dir | `Path.home() / ".karafun_intercept"` — `pathlib.Path` resolves to `%USERPROFILE%\.karafun_intercept` on Windows |
| `cli.py` git commands | `subprocess.run(["git", ...], ...)` with explicit arg lists — no `shell=True`, no bash-isms |
| `cli.py` update command | `uv tool install --from git+https://...@branch …` — uv is cross-platform |
| `cli.py` uv lookup | `shutil.which("uv")` — cross-platform |
| `client.py` | Pure `asyncio` + `websockets`; `Transport` abstraction; no platform code |
| `app.py` | Textual TUI — cross-platform terminal rendering |
| `model.py` / `xml_proto.py` | Pure Python, stdlib only |
| `pyproject.toml` | `hatchling` build backend, `textual`/`websockets` deps — all cross-platform |

### Gaps to fill

| Gap | Fix |
| --- | --- |
| Install one-liner is bash-only (`curl … \| sh`) | Add `scripts/install.ps1` + PowerShell one-liner |
| No CI | Add `.github/workflows/ci.yml` with Windows + Linux matrix |
| `.gitignore` lacks Windows entries | Add entries |
| `AGENTS.md` only references `.venv/bin` | Note `.venv/Scripts` for Windows |
| No cross-platform contract in `PHILOSOPHY.md` | Add Contract 12 |

---

## 4. The Approach (Approaches A/B/C reviewed)

- **A — Install + docs only (no CI):** cross-platform breaks silently; "persist across dev cycles" not enforced.
- **B — Install + docs + CI matrix (selected):** same as A, plus GitHub Actions matrix on Ubuntu + Windows running `ruff check` and `pytest -W error`. Enforces cross-platform on every push/PR.
- **C — + standalone exe installer:** YAGNI — `uv tool install` already creates `karafun.exe`; bundling would add a parallel update mechanism.

**Decision: Approach B.** CI is the mechanism that makes the cross-platform requirement persist across dev cycles.

---

## 5. Detailed Changes

### 5.1 `scripts/install.ps1` (new)

PowerShell equivalent of `scripts/install.sh`. Mirrors the same user experience:

1. Check if `uv` is available (`Get-Command uv -ErrorAction SilentlyContinue`).
2. If not, prompt the user (via `Read-Host`); on yes, install using the official PowerShell installer: `irm https://astral.sh/uv/install.ps1 | iex`.
   - `uv`'s PowerShell installer respects `$env:LOCALAPPDATA` and adds itself to PATH.
3. Run `uv tool install --upgrade --force git+https://github.com/LiTLiTschi/karafun-intercept.git`.
4. Print success + how to run `karafun intercept`.

The Windows install one-liner:
```powershell
irm https://raw.githubusercontent.com/LiTLiTschi/karafun-intercept/master/scripts/install.ps1 | iex
```

### 5.2 `README.md`

Add a **Windows** subsection under **Prerequisites** and **Install**:

- **Prerequisites:** `uv` install via `irm https://astral.sh/uv/install.ps1 | iex` (PowerShell).
- **Install (one-liner):** the PowerShell one-liner above, alongside the existing bash one.
- **Note:** `karafun update` and `karafun branch-*` require `git` in PATH on Windows (Git for Windows or GitHub CLI).

### 5.3 `AGENTS.md`

- Update the venv path reference (line ~29): `.venv/bin` → note that on Windows the venv binaries live under `.venv/Scripts/` instead. This is a documentation note, not a code change — the agent commands (`ruff`, `pytest`, `python`) remain the same.
- Add a brief cross-platform dev context note under Tooling & Commands.

### 5.4 `PHILOSOPHY.md` — Contract 12: Cross-Platform

```markdown
## Contract 12: Cross-Platform — Windows + Linux First

**Statement:** The project MUST build, install, run, and test on both Windows and Linux.
No platform-specific shell scripts or Unix-only assumptions are permitted in any
code path that a user or developer touches.

- Install one-liners exist for **both** platforms: PowerShell (`irm … | iex`) for
  Windows, POSIX shell (`curl … | sh`) for Linux/macOS.
- `karafun update` and `karafun branch-*` MUST work on both platforms — they rely
  only on `uv` and `git` being in PATH (both available cross-platform).
- No code may branch on `sys.platform`/`os.name` into platform-specific behavior
  unless explicitly justified (path separators are always handled via `pathlib.Path`).
- `.gitignore` MUST include Windows-specific artifacts (Thumbs.db, etc.).
- CI MUST run tests on both Windows and Linux (matrix).
```

**Rationale:** The KaraFun Player is Windows-only, but the observer app's code and tests are cross-platform. Encoding this as a contract ensures cross-platform support is never accidentally broken — it becomes as non-negotiable as the Template Method or Key Binding contracts.

### 5.5 `.gitignore`

Add:
```
# Windows
Thumbs.db
Desktop.ini
*.lnk
```

### 5.6 `.github/workflows/ci.yml` (new)

```yaml
name: CI

on:
  push:
    branches: [master, main]
  pull_request:

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Install Python & deps
        run: uv sync --extra dev

      - name: Lint
        run: uv run ruff check src tests

      - name: Test
        run: uv run pytest -W error
```

**Why `uv sync` instead of `uv tool install`:** CI tests the source checkout (editable install), not the installed CLI tool. The CLI's `update`/`branch-*` commands are tested via unit tests with fake transports. `uv sync --extra dev` installs runtime + dev deps (`textual`, `websockets`, `pytest`, `ruff`) into a `.venv`.

**Why `fail-fast: false`:** so a Linux failure doesn't cancel the Windows job (and vice versa) — you see both results.

### 5.7 Python source — no changes

The entire `src/karafun_intercept/` tree is verified cross-platform. No edits to application code.

---

## 6. Testing Strategy

- **Existing hermetic tests** (`tests/`) run unchanged on both platforms — they use `FakeTransport` (no network, no player).
- **CI** runs `ruff check src tests` and `pytest -W error` on both `ubuntu-latest` and `windows-latest`.
- The PowerShell install script can't be unit-tested in CI without a Windows shell, but its structure mirrors the bash script which has no automated tests either. Manual verification is acceptable for install scripts.

### Verification checklist

- [ ] `scripts/install.ps1` syntax-validates in PowerShell (`pwsh -NoProfile -Command "$null = [System.Management.Automation.PSParser]::Tokenize((Get-Content scripts/install.ps1 -Raw), [ref]$null)"`)
- [ ] `ruff check src tests` passes
- [ ] `pytest -W error` passes (all existing tests)
- [ ] CI workflow runs on both Ubuntu and Windows

---

## 7. PHILOSOPHY / AGENTS Compliance

- **Contract 6 (YAGNI):** No exe packaging, no MSI, no `.bat` launchers. `uv tool install` suffices.
- **Contract 7 (Flat config):** No config changes.
- **PHILOSOPHY Contract 9 (Key Bindings):** No TUI changes; Textual key bindings are cross-platform.
- **PHILOSOPHY Contract 10 (Colors):** No UI changes.
- **AGENTS.md branch discipline:** branch `feat/cross-platform-windows`, conventional commit.
- **AGENTS.md venv path:** updated to note `.venv/Scripts` on Windows.
