# Cross-Platform Windows Port — Complete

All tasks finished. PR #2 merged (squash commit `20fc59b`). Spec archived to `docs/implemented-specs/`.

## Deliverables

- `scripts/install.ps1` — PowerShell install script (`.\irm … | iex` one-liner for Windows)
- `.github/workflows/ci.yml` — CI matrix on ubuntu-latest + windows-latest (ruff + pytest -W error)
- `PHILOSOPHY.md` — Contract 12: Cross-Platform (Windows + Linux first)
- `AGENTS.md` — venv path note (`.venv/Scripts` on Windows) + Spec Lifecycle Management + Plannotator Review sections
- `README.md` — Windows install instructions + prerequisites + git note
- `.gitignore` — Windows artifacts (Thumbs.db, Desktop.ini, *.lnk)
- `docs/implemented-specs/README.md` — archive directory marker
- `docs/implemented-specs/2026-09-28-cross-platform-windows-port-design.md` — archived final spec

## Verification

- `ruff check src tests` — All checks passed
- `pytest -W error` — 21 passed, 1 skipped (live player)
- `pwsh` syntax check — 0 errors
- CI: `test (ubuntu-latest): pass` / `test (windows-latest): pass`
