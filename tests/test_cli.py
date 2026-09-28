"""Tests for the karafun CLI dispatcher (cli.py).

Covers _run_update (both the direct Linux path and the Windows detached-updater
path), _build_update_batch, _report_update_result, and _is_windows.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from karafun_intercept.cli import (
    _build_update_batch,
    _is_windows,
    _report_update_result,
    _run_update,
    _run_update_windows,
)

# ---------------------------------------------------------------------------
# _is_windows
# ---------------------------------------------------------------------------


def test_is_windows_true(monkeypatch):
    monkeypatch.setattr("karafun_intercept.cli.platform.system", lambda: "Windows")
    assert _is_windows() is True


def test_is_windows_false(monkeypatch):
    monkeypatch.setattr("karafun_intercept.cli.platform.system", lambda: "Linux")
    assert _is_windows() is False


def test_is_windows_macos(monkeypatch):
    monkeypatch.setattr("karafun_intercept.cli.platform.system", lambda: "Darwin")
    assert _is_windows() is False


# ---------------------------------------------------------------------------
# _build_update_batch
# ---------------------------------------------------------------------------


def test_build_update_batch_contains_pid_and_command():
    batch = _build_update_batch(12345, '"C:\\uv\\uv.exe" tool install --force karafun-intercept')
    assert "12345" in batch
    assert "tasklist" in batch
    assert "uv.exe" in batch
    assert "@echo off" in batch
    assert "timeout /t 1 /nobreak" in batch
    assert "exit /b %errorlevel%" in batch


def test_build_update_batch_escapes_percent_signs():
    """'%' must be doubled to '%%' inside the interpolated command line."""
    uv_cmd = "uv install --from git+https://example.com@%2Fpath"
    batch = _build_update_batch(12345, uv_cmd)
    assert "%%" in batch
    # The raw (unescaped) command line must not appear verbatim
    assert uv_cmd not in batch


def test_build_update_batch_keeps_errorlevel_unescaped():
    """Batch-file variables like %errorlevel% must NOT be escaped."""
    batch = _build_update_batch(99999, "uv tool install --force karafun-intercept")
    assert "%errorlevel%" in batch
    assert "%%errorlevel%%" not in batch


# ---------------------------------------------------------------------------
# _report_update_result
# ---------------------------------------------------------------------------


def test_report_update_result_success(capsys):
    result = subprocess.CompletedProcess([], 0, stdout="Installed karafun-intercept", stderr="")
    assert _report_update_result(result) == 0
    assert "Installed karafun-intercept" in capsys.readouterr().out


def test_report_update_result_already_up_to_date(capsys):
    result = subprocess.CompletedProcess([], 0, stdout="already up to date", stderr="")
    assert _report_update_result(result) == 0
    out = capsys.readouterr().out
    assert "already up to date" in out.lower()


def test_report_update_result_failure(capsys):
    result = subprocess.CompletedProcess([], 1, stdout="", stderr="something broke")
    assert _report_update_result(result) == 1
    err = capsys.readouterr().err
    assert "uv tool install failed" in err
    assert "something broke" in err


def test_report_update_result_failure_no_stderr(capsys):
    result = subprocess.CompletedProcess([], 1, stdout="", stderr="")
    assert _report_update_result(result) == 1
    # No stderr content to print, but still returns 1
    capsys.readouterr()


def test_report_update_result_empty_output(capsys):
    result = subprocess.CompletedProcess([], 0, stdout="", stderr="")
    assert _report_update_result(result) == 0
    assert "karafun updated successfully" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _run_update_windows
# ---------------------------------------------------------------------------


def test_run_update_windows_spawns_detached_process(tmp_path, monkeypatch, capsys):
    """The detached updater spawns cmd.exe with a batch file and returns 0."""
    captured = {}

    def fake_popen(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return MagicMock(pid=99999)

    monkeypatch.setattr("karafun_intercept.cli.subprocess.Popen", fake_popen)
    monkeypatch.setattr("karafun_intercept.cli.os.getpid", lambda: 42)
    monkeypatch.setattr("karafun_intercept.cli.tempfile.gettempdir", lambda: str(tmp_path))

    cmd = ["C:\\uv\\uv.exe", "tool", "install", "--force", "karafun-intercept"]
    rc = _run_update_windows(cmd, debug=False)

    assert rc == 0
    out = capsys.readouterr().out
    assert "separate process" in out

    # cmd.exe must be the first argument, batch file the third
    assert captured["args"][0] == "cmd.exe"
    assert captured["args"][1] == "/c"
    batch_file = Path(captured["args"][2])
    assert batch_file.exists()
    content = batch_file.read_text(encoding="utf-8")
    assert "42" in content  # parent PID baked into the batch file

    # close_fds must be True (don't inherit handles from the locked dir)
    assert captured["kwargs"].get("close_fds") is True

    batch_file.unlink(missing_ok=True)


def test_run_update_windows_debug_mode(tmp_path, monkeypatch, capsys):
    """With debug=True, the batch file path is printed to stderr."""
    monkeypatch.setattr("karafun_intercept.cli.subprocess.Popen", lambda *a, **kw: MagicMock())
    monkeypatch.setattr("karafun_intercept.cli.os.getpid", lambda: 42)
    monkeypatch.setattr("karafun_intercept.cli.tempfile.gettempdir", lambda: str(tmp_path))

    cmd = ["uv", "tool", "install", "--force", "karafun-intercept"]
    rc = _run_update_windows(cmd, debug=True)

    assert rc == 0
    err = capsys.readouterr().err
    assert "Detached updater batch file" in err


def test_run_update_windows_missing_cmdexe(tmp_path, monkeypatch, capsys):
    """If cmd.exe is not found, return error code 1."""

    def fake_popen(*args, **kwargs):
        raise FileNotFoundError("cmd.exe not found")

    monkeypatch.setattr("karafun_intercept.cli.subprocess.Popen", fake_popen)
    monkeypatch.setattr("karafun_intercept.cli.os.getpid", lambda: 42)
    monkeypatch.setattr("karafun_intercept.cli.tempfile.gettempdir", lambda: str(tmp_path))

    cmd = ["uv", "tool", "install", "--force", "karafun-intercept"]
    rc = _run_update_windows(cmd, debug=False)

    assert rc == 1
    assert "cmd.exe not found" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# _run_update integration
# ---------------------------------------------------------------------------


def _state_dir_with_branch(tmp_path: Path, branch: str = "master") -> Path:
    """Create a state dir with a pre-existing selected-branch file."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "selected-branch").write_text(branch + "\n", encoding="utf-8")
    return state_dir


def test_run_update_non_windows_uses_direct_subprocess(tmp_path, monkeypatch, capsys):
    """On non-Windows, _run_update uses subprocess.run directly."""
    state_dir = _state_dir_with_branch(tmp_path, "master")
    fake_result = subprocess.CompletedProcess(
        [], 0, stdout="Installed karafun-intercept", stderr=""
    )

    monkeypatch.setattr(
        "karafun_intercept.cli.shutil.which",
        lambda name: "/fake/uv" if name == "uv" else None,
    )
    monkeypatch.setattr("karafun_intercept.cli._is_windows", lambda: False)
    monkeypatch.setattr("karafun_intercept.cli.subprocess.run", lambda *a, **kw: fake_result)

    rc = _run_update(state_dir, debug=False)

    assert rc == 0
    out = capsys.readouterr().out
    assert "Installing karafun from github origin/master" in out
    assert "Installed karafun-intercept" in out


def test_run_update_non_windows_failure(tmp_path, monkeypatch, capsys):
    """A uv failure on non-Windows produces stderr and exit code 1."""
    state_dir = _state_dir_with_branch(tmp_path, "master")
    fake_result = subprocess.CompletedProcess([], 1, stdout="", stderr="disk full")

    monkeypatch.setattr(
        "karafun_intercept.cli.shutil.which",
        lambda name: "/fake/uv" if name == "uv" else None,
    )
    monkeypatch.setattr("karafun_intercept.cli._is_windows", lambda: False)
    monkeypatch.setattr("karafun_intercept.cli.subprocess.run", lambda *a, **kw: fake_result)

    rc = _run_update(state_dir, debug=False)

    assert rc == 1
    assert "uv tool install failed" in capsys.readouterr().err


def test_run_update_non_windows_missing_uv(tmp_path, monkeypatch, capsys):
    """If uv is not found, return error."""
    state_dir = _state_dir_with_branch(tmp_path, "master")
    monkeypatch.setattr("karafun_intercept.cli.shutil.which", lambda name: None)

    rc = _run_update(state_dir, debug=False)

    assert rc == 1
    assert "uv is required" in capsys.readouterr().err


def test_run_update_windows_delegates_to_detached(tmp_path, monkeypatch, capsys):
    """On Windows, _run_update delegates to the detached updater."""
    state_dir = _state_dir_with_branch(tmp_path, "master")
    spawned = []

    def fake_popen(args, **kwargs):
        spawned.append(args)
        return MagicMock(pid=99999)

    monkeypatch.setattr(
        "karafun_intercept.cli.shutil.which",
        lambda name: "C:\\fake\\uv.exe" if name == "uv" else None,
    )
    monkeypatch.setattr("karafun_intercept.cli._is_windows", lambda: True)
    monkeypatch.setattr("karafun_intercept.cli.subprocess.Popen", fake_popen)
    monkeypatch.setattr("karafun_intercept.cli.os.getpid", lambda: 42)
    monkeypatch.setattr("karafun_intercept.cli.tempfile.gettempdir", lambda: str(tmp_path))

    rc = _run_update(state_dir, debug=False)

    assert rc == 0
    assert len(spawned) == 1
    assert spawned[0][0] == "cmd.exe"
    out = capsys.readouterr().out
    assert "separate process" in out


def test_run_update_writes_branch_to_state_dir(tmp_path, monkeypatch, capsys):
    """_run_update records the selected branch in the install-source state file."""
    state_dir = tmp_path / "state"  # does NOT exist yet — mkdir should create it
    monkeypatch.setattr(
        "karafun_intercept.cli.shutil.which",
        lambda name: "/fake/uv" if name == "uv" else None,
    )
    monkeypatch.setattr("karafun_intercept.cli._is_windows", lambda: False)
    monkeypatch.setattr(
        "karafun_intercept.cli.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess([], 0, stdout="", stderr=""),
    )

    rc = _run_update(state_dir, debug=False)

    assert rc == 0
    install_source = (state_dir / "install-source").read_text(encoding="utf-8")
    assert "master" in install_source


def test_run_update_uses_selected_branch_from_state(tmp_path, monkeypatch, capsys):
    """The branch from the state dir is used in the git URL."""
    state_dir = _state_dir_with_branch(tmp_path, "dev")
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")

    monkeypatch.setattr(
        "karafun_intercept.cli.shutil.which",
        lambda name: "/fake/uv" if name == "uv" else None,
    )
    monkeypatch.setattr("karafun_intercept.cli._is_windows", lambda: False)
    monkeypatch.setattr("karafun_intercept.cli.subprocess.run", fake_run)

    _run_update(state_dir, debug=False)

    cmd_str = " ".join(captured["cmd"])
    assert "dev" in cmd_str
    assert "github.com/LiTLiTschi/karafun-intercept.git@dev" in cmd_str


def test_run_update_debug_prints_command(tmp_path, monkeypatch, capsys):
    """With debug=True, the uv command is printed to stderr."""
    state_dir = _state_dir_with_branch(tmp_path, "master")
    monkeypatch.setattr(
        "karafun_intercept.cli.shutil.which",
        lambda name: "/fake/uv" if name == "uv" else None,
    )
    monkeypatch.setattr("karafun_intercept.cli._is_windows", lambda: False)
    monkeypatch.setattr(
        "karafun_intercept.cli.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess([], 0, stdout="", stderr=""),
    )

    _run_update(state_dir, debug=True)

    err = capsys.readouterr().err
    assert "/fake/uv" in err
    assert "tool" in err
    assert "install" in err
