# Cross-Platform Windows Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use /skill:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make karafun-intercept installable, runnable, and testable on both Windows and Linux from the start, with a PowerShell one-liner install for Windows and CI enforcing both platforms.

**Architecture:** No code changes to the Python source — `src/karafun_intercept/` is already cross-platform (`pathlib.Path`, explicit `subprocess.run` arg lists with no `shell=True`, `textual`/`websockets` deps). Add a PowerShell install script, update documentation (README, AGENTS.md, PHILOSOPHY.md), add Windows entries to `.gitignore`, and add a GitHub Actions CI matrix testing on Ubuntu + Windows.

**Tech Stack:** PowerShell 5.1+ (install script), GitHub Actions YAML (CI), Python 3.9+ with `uv` (dev workflow).

**Roadmap:** None

**Phase:** Single-plan implementation

---

## Files created/modified

```text
scripts/
├── install.ps1            # NEW  — PowerShell install script (Windows one-liner)
├── install.sh             # UNCHANGED — bash install script (Linux/macOS one-liner)
.github/
└── workflows/
    └── ci.yml             # NEW  — CI matrix: ubuntu-latest + windows-latest
README.md                  # MODIFY — add Windows install + prerequisites
AGENTS.md                  # MODIFY — .venv/bin → also .venv/Scripts; cross-platform context
PHILOSOPHY.md              # MODIFY — add Contract 12: Cross-Platform
.gitignore                 # MODIFY — add Windows artifacts
```

---

## Verification

- `ruff check src tests` — Python source unchanged, must still pass
- `pytest -W error` — existing hermetic tests must still pass
- `pwsh` syntax check on `scripts/install.ps1`
- CI YAML structural assertions

---

### Task 1: Create `scripts/install.ps1`

**Files:**
- Create: `scripts/install.ps1`

PowerShell equivalent of `scripts/install.sh`. Mirrors the same flow: check for `uv`, offer to install if missing, then run `uv tool install`.

- [ ] **Step 1: Write the install script**

```powershell
<#
.SYNOPSIS
    karafun-intercept install script (Windows / PowerShell)

.USAGE
    irm https://raw.githubusercontent.com/LiTLiTschi/karafun-intercept/master/scripts/install.ps1 | iex

.DESCRIPTION
    Checks for uv, offers to install it if missing, then runs
    `uv tool install` to install the karafun command globally.
    Mirrors scripts/install.sh for POSIX systems.
#>

$ErrorActionPreference = "Stop"

# ── Prerequisites ────────────────────────────────────────────────────

$uvExe = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvExe) {
    Write-Host "uv is not installed."
    Write-Host ""
    Write-Host "You can install uv in one of the following ways:"
    Write-Host ""
    Write-Host "  Option A (recommended -- automatic):"
    Write-Host "    irm https://astral.sh/uv/install.ps1 | iex"
    Write-Host ""
    Write-Host "  Option B (using a package manager):"
    Write-Host "    winget install uv        # Windows"
    Write-Host "    pip install uv           # any platform (requires pip)"
    Write-Host ""

    # Prompt for automatic install (default Y, matching install.sh behavior)
    try {
        $resp = Read-Host "Install uv automatically now? [Y/n]"
    } catch {
        $resp = ""
    }
    $resp = if ([string]::IsNullOrWhiteSpace($resp)) { "Y" } else { $resp }

    if ($resp -match "^[Yy]") {
        Write-Host "Installing uv..."
        irm https://astral.sh/uv/install.ps1 | iex

        # uv's installer updates user PATH; refresh current session PATH
        $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
        $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
        $env:Path = "$userPath;$machinePath;$env:Path"

        $uvExe = Get-Command uv -ErrorAction SilentlyContinue
        if (-not $uvExe) {
            Write-Host "uv was installed but is not on PATH in this session."
            Write-Host "Please restart your shell and re-run this script."
            exit 1
        }
        Write-Host "uv installed."
    } else {
        Write-Host "Please install uv using one of the options above, then re-run this script."
        exit 1
    }
}

# ── Install ──────────────────────────────────────────────────────────

Write-Host "Installing karafun-intercept..."
$KARAFUN_REPO = "git+https://github.com/LiTLiTschi/karafun-intercept.git"

& $uvExe tool install --upgrade --force $KARAFUN_REPO

Write-Host ""
Write-Host "karafun-intercept installed successfully."
Write-Host "Run 'karafun intercept' to launch the TUI."
```

- [ ] **Step 2: Verify PowerShell syntax**

Run:
```bash
pwsh -NoProfile -Command "$null = [System.Management.Automation.Language.Parser]::ParseFile('scripts/install.ps1', [ref]$null, [ref]$null); 'Syntax OK'"
```
Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/install.ps1
git commit -m "feat: add PowerShell install script for Windows"
```

---

### Task 2: Update `README.md` with Windows install instructions

**Files:**
- Modify: `README.md`

Three edits to `README.md`:

**Edit 2a — Prerequisites section:** change the uv bullet to mention both platforms:

Before:
```text
- **[uv](https://docs.astral.sh/uv/)** — install via `curl -LsSf https://astral.sh/uv/install.sh | sh`
```

After:
```text
- **[uv](https://docs.astral.sh/uv/)** — install via `curl -LsSf https://astral.sh/uv/install.sh | sh` (Linux/macOS) or `irm https://astral.sh/uv/install.ps1 | iex` (Windows)
```

**Edit 2b — Install section:** add a Windows subsection after the bash one-liner block:

Current structure:
~~~
### Install (one-liner)

```bash
curl -fsSL .../install.sh | sh
```

This downloads the install script...
~~~

After (insert between the bash block and "This downloads"):
```text
#### Windows

```powershell
irm https://raw.githubusercontent.com/LiTLiTschi/karafun-intercept/master/scripts/install.ps1 | iex
```
```

**Edit 2c — Updating section:** add a Windows git note after the `karafun update` block:

Insert after the `karafun update` code block:
```text
> **Note (Windows):** `karafun update` and `karafun branch-*` require `git` in `PATH`.
> Install [Git for Windows](https://git-scm.com/download/win) or the GitHub CLI.
```

- [ ] **Step 1: Edit Prerequisites section** (Edit 2a)
- [ ] **Step 2: Add Windows install subsection** (Edit 2b)
- [ ] **Step 3: Add Windows git note to Updating** (Edit 2c)
- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add Windows install instructions and prerequisites"
```

---

### Task 3: Update `AGENTS.md` + `.gitignore`

**Files:**
- Modify: `AGENTS.md`
- Modify: `.gitignore`

- [ ] **Step 1: Update AGENTS.md line 29**

Change:
```text
Put `.venv/bin` (or the project-local `scripts/dev/*` wrappers if present) ahead of PATH.
```
to:
```text
Put `.venv/bin` (Unix/macOS) or `.venv/Scripts` (Windows) ahead of PATH.
```

- [ ] **Step 2: Add cross-platform note to AGENTS.md Tooling & Commands**

Add a bullet after the existing `pytest`/`ruff` lines:
```text
- **Cross-platform:** The project targets both Windows and Linux. Python source uses `pathlib.Path` (never raw path separators) and `subprocess.run` with explicit arg lists (never `shell=True`). Install one-liners differ by platform: PowerShell (`irm … | iex`) on Windows, POSIX shell (`curl … | sh`) on Linux/macOS. `karafun update` and `karafun branch-*` require `git` in `PATH` on both platforms.
```

- [ ] **Step 3: Add Windows entries to `.gitignore`**

Append at end of file:
```text
# Windows
Thumbs.db
Desktop.ini
*.lnk
```

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md .gitignore
git commit -m "chore: document cross-platform dev conventions; add Windows gitignore"
```

---

### Task 4: Add Contract 12 to `PHILOSOPHY.md`

**Files:**
- Modify: `PHILOSOPHY.md`

Append at the end of `PHILOSOPHY.md` (after Contract 11's Enforcement section):

```markdown

---

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

**Why it matters:** The KaraFun Player is Windows-only, but the observer app's code
and tests are cross-platform. CI on both platforms ensures cross-platform correctness
is enforced on every change — not just documented and forgotten.

**Detection:** grep for `sys.platform`, `os.name`, `os.path.join`, `shell=True` in
`src/` — flag any without explicit justification comments; verify `.github/workflows/ci.yml`
runs on a matrix including `windows-latest`.
```

- [ ] **Step 1: Append Contract 12 to PHILOSOPHY.md**
- [ ] **Step 2: Verify**

```bash
grep -c "Contract 12" PHILOSOPHY.md
```
Expected: `1`

- [ ] **Step 3: Commit**

```bash
git add PHILOSOPHY.md
git commit -m "docs(philosophy): add Contract 12 — Cross-Platform Windows + Linux First"
```

---

### Task 5: Create `.github/workflows/ci.yml`

**Files:**
- Create: `.github/workflows/ci.yml`

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

      - name: Install Python & dependencies
        run: uv sync --extra dev

      - name: Lint
        run: uv run ruff check src tests

      - name: Test
        run: uv run pytest -W error
```

- [ ] **Step 1: Create directory + file**
- [ ] **Step 2: Validate structure**

```bash
python3 -c "
content = open('.github/workflows/ci.yml').read()
assert 'name: CI' in content
assert 'ubuntu-latest' in content
assert 'windows-latest' in content
assert 'ruff check' in content
assert 'pytest -W error' in content
print('CI workflow structure OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add Windows + Linux test matrix (ruff + pytest)"
```

---

### Task 6: Final verification

- [ ] **Step 1: Lint**

```bash
.venv/bin/ruff check src tests
```
Expected: `All checks passed!`

- [ ] **Step 2: Tests** (all must pass with `-W error`)

```bash
.venv/bin/pytest -W error
```
Expected: all PASS (22 tests: xml_proto, client, model, app, integration; live test skipped).

- [ ] **Step 3: Verify all deliverables exist**

```bash
[ -f scripts/install.ps1 ] && echo "install.ps1 OK" || echo "MISSING install.ps1"
[ -f .github/workflows/ci.yml ] && echo "ci.yml OK" || echo "MISSING ci.yml"
grep -q "Contract 12" PHILOSOPHY.md && echo "Contract 12 OK" || echo "MISSING Contract 12"
grep -q "Thumbs.db" .gitignore && echo ".gitignore OK" || echo "MISSING .gitignore entries"
grep -q "install.ps1" README.md && echo "README OK" || echo "MISSING README Windows section"
grep -q "Scripts" AGENTS.md && echo "AGENTS OK" || echo "MISSING AGENTS venv note"
```

---

## Self-review

1. **Spec coverage:** All six spec sections (Overview, Scope, Findings, Approach, Detailed Changes, Testing Strategy, Compliance) are covered by Tasks 1–6. ✅
2. **Placeholder scan:** No TBD/TODO/FIXME (except checkboxes). Every step contains actual code or commands. ✅
3. **Type consistency:** No Python code changes — types unchanged. PowerShell and YAML are validated by syntax checks. ✅
4. **Phase boundary health:** All changes are additive (new files + docs). No existing functionality is broken. The Python test suite remains green. ✅

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-28-cross-platform-windows-port-plan.md`. Ready to execute it task-by-task.
