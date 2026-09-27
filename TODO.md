# Karafun Intercept Implementation Tasks

## Tasks (from plan)

- [x] Task 1: `xml_proto.py` — XML protocol parsing & action builders
  - Create `src/karafun_intercept/xml_proto.py`
  - Create `src/karafun_intercept/_version.py`
  - Modify `src/karafun_intercept/__init__.py` (import/export `__version__`)
  - Create `tests/conftest.py`
  - Create `tests/test_xml_proto.py`
  - Verify: `pytest tests/test_xml_proto.py -W error` + `ruff check`
  - Commit

- [ ] Task 2: `client.py` — KarafunClient (WS lifecycle, Approach C)
  - Create `src/karafun_intercept/client.py`
  - Modify `pyproject.toml` (add `websockets>=12` dependency)
  - Create `tests/test_client.py`
  - Verify: `pytest tests/test_client.py -W error` + `ruff check`
  - Commit

- [ ] Task 3: `model.py` — SessionModel (state deltas, notifications, recency)
  - Create `src/karafun_intercept/model.py`
  - Create `tests/test_model.py`
  - Verify: `pytest tests/test_model.py -W error` + `ruff check`
  - Commit

- [ ] Task 4: `app.py` — Textual TUI (queue/singers/notifications)
  - Rewrite `src/karafun_intercept/app.py`
  - Create `src/karafun_intercept/__main__.py`
  - Create `tests/test_app.py`
  - Verify: `pytest tests/test_app.py -W error` + `ruff check`
  - Commit

- [ ] Task 5: Integration tests
  - Create `tests/test_integration.py`
  - Verify: `pytest -W error` (live test skipped)
  - Commit
