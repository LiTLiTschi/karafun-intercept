# Cross-Platform Windows Port — Implementation

- [x] Task 1: Create `scripts/install.ps1` (PowerShell install script)
- [x] Task 2: Update `README.md` (Windows install + prerequisites)
- [x] Task 3: Update `AGENTS.md` + `.gitignore` (venv path, cross-platform note, Windows entries)
- [x] Task 4: Add Contract 12 to `PHILOSOPHY.md`
- [x] Task 5: Create `.github/workflows/ci.yml` (Windows + Linux matrix)
- [x] Task 6: Final verification (ruff + pytest -W error + deliverables check)

## Status: COMPLETE

All deliverables verified:

- `scripts/install.ps1` — PowerShell install script (syntax validated with pwsh)
- `README.md` — Windows install + prerequisites added
- `AGENTS.md` — `.venv/bin` → also `.venv/Scripts`; cross-platform note added
- `PHILOSOPHY.md` — Contract 12: Cross-Platform added
- `.gitignore` — Windows artifacts (Thumbs.db, Desktop.ini, *.lnk)
- `.github/workflows/ci.yml` — Windows + Linux test matrix
- `ruff check src tests` — all checks passed
- `pytest -W error` — 21 passed, 1 skipped (live player test)
