"""Logging configuration for karafun-intercept.

Uses only standard library ``logging.DEBUG`` and ``logging.INFO`` levels.
Console output is always at INFO. DEBUG-level diagnostics are written to
``~/.karafun_intercept/session.log`` when debug mode is enabled via
``karafun intercept --debug``.
"""

from __future__ import annotations

import logging
from pathlib import Path

LOG_DIR = Path.home() / ".karafun_intercept"
LOG_FILE = LOG_DIR / "session.log"

_CONSOLE_FORMAT = "%(name)s: %(message)s"
_FILE_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_FILE_DATEFMT = "%Y-%m-%dT%H:%M:%S%z"


def setup_logging(*, debug: bool = False) -> None:
    """Configure root logging: console at INFO, file at DEBUG (when debug=True).

    Safe to call multiple times — duplicate handlers are skipped.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    # Console handler — always present, INFO level.
    if not _has_console_handler(root):
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
        root.addHandler(console)

    if debug:
        _add_file_handler(root)


def _has_console_handler(root: logging.Logger) -> bool:
    for h in root.handlers:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            return True
    return False


def _has_file_handler(root: logging.Logger) -> bool:
    for h in root.handlers:
        if isinstance(h, logging.FileHandler):
            return True
    return False


def _add_file_handler(root: logging.Logger) -> None:
    if _has_file_handler(root):
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_FILE_DATEFMT))
    root.addHandler(handler)
