"""Tests for the logging configuration module (setup_logging).

Covers:
  - console handler added at INFO level
  - debug=True adds a file handler at DEBUG level writing to ~/.karafun_intercept/session.log
  - root logger level set correctly
  - setup_logging() is idempotent (no duplicate handlers on repeated calls)
"""

import logging

from karafun_intercept._logging import setup_logging


def _root():
    return logging.getLogger()


def _clear_root():
    root = _root()
    root.handlers.clear()
    root.setLevel(logging.WARNING)


def _console_handlers():
    return [
        h
        for h in _root().handlers
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
    ]


def _file_handlers():
    return [h for h in _root().handlers if isinstance(h, logging.FileHandler)]


def test_setup_logging_adds_console_at_info():
    _clear_root()
    setup_logging()
    root = _root()
    console = _console_handlers()
    assert len(console) == 1
    assert console[0].level == logging.INFO
    assert root.level == logging.INFO


def test_setup_logging_debug_sets_root_level_debug(tmp_path, monkeypatch):
    from karafun_intercept import _logging

    monkeypatch.setattr(_logging, "LOG_DIR", tmp_path / "karafun_intercept")
    monkeypatch.setattr(_logging, "LOG_FILE", tmp_path / "karafun_intercept" / "session.log")
    _clear_root()
    setup_logging(debug=True)
    assert _root().level == logging.DEBUG


def test_setup_logging_debug_adds_file_handler(tmp_path, monkeypatch):
    from karafun_intercept import _logging

    log_dir = tmp_path / "karafun_intercept"
    monkeypatch.setattr(_logging, "LOG_DIR", log_dir)
    monkeypatch.setattr(_logging, "LOG_FILE", log_dir / "session.log")

    _clear_root()
    setup_logging(debug=True)
    files = _file_handlers()
    assert len(files) == 1
    assert files[0].level == logging.DEBUG
    # File should not exist yet — only created when a log record is emitted.
    # But the FileHandler opens the file in append mode, so it does exist.
    assert files[0].baseFilename == str(log_dir / "session.log")
    assert log_dir.exists()


def test_setup_logging_no_debug_no_file_handler():
    _clear_root()
    setup_logging(debug=False)
    assert len(_file_handlers()) == 0


def test_setup_logging_idempotent_no_duplicate_handlers():
    _clear_root()
    setup_logging()
    setup_logging()
    assert len(_console_handlers()) == 1
    assert len(root_handlers()) == 1


def test_setup_logging_idempotent_with_debug(tmp_path, monkeypatch):
    from karafun_intercept import _logging

    log_dir = tmp_path / "karafun_intercept"
    monkeypatch.setattr(_logging, "LOG_DIR", log_dir)
    monkeypatch.setattr(_logging, "LOG_FILE", log_dir / "session.log")

    _clear_root()
    setup_logging(debug=True)
    setup_logging(debug=True)
    assert len(_console_handlers()) == 1
    assert len(_file_handlers()) == 1


def root_handlers():
    return _root().handlers
