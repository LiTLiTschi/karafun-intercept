"""Karafun CLI dispatcher.

Usage:
    karafun intercept   Launch the Textual TUI
    karafun update      Rebuild from latest commit on the selected branch
    karafun version     Print version information
    karafun branch-show Print the currently selected branch for updates
    karafun branch-list List branches from GitHub origin
    karafun branch-switch N  Select a numbered branch as the update target
    karafun --help      Show help
"""

from __future__ import annotations

import argparse
import contextlib
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from karafun_intercept._version import __version__

KARAFUN_STATE_DIR = Path.home() / ".karafun_intercept"


def _state_dir() -> Path:
    return KARAFUN_STATE_DIR


def _selected_branch_path(state_dir: Path) -> Path:
    return state_dir / "selected-branch"


def _install_source_path(state_dir: Path) -> Path:
    return state_dir / "install-source"


def _github_default_branch() -> str | None:
    """Return the default branch name from GitHub."""
    with contextlib.suppress(FileNotFoundError, subprocess.TimeoutExpired):
        result = subprocess.run(
            [
                "git",
                "ls-remote",
                "https://github.com/LiTLiTschi/karafun-intercept.git",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            line = result.stdout.splitlines()[0]
            parts = line.split("\t")
            if len(parts) == 2 and parts[1].startswith("refs/heads/"):
                return parts[1][len("refs/heads/") :]
    return None


def _selected_branch(state_dir: Path) -> str:
    """Return the branch karafun should build from on GitHub."""
    path = _selected_branch_path(state_dir)
    if path.is_file():
        branch = path.read_text().strip()
        if branch:
            return branch
    default = _github_default_branch()
    return default if default else "master"


def _github_branches() -> list[str]:
    """List branch names from the GitHub origin (no local clone required)."""
    branches: list[str] = []
    with contextlib.suppress(FileNotFoundError, subprocess.TimeoutExpired):
        result = subprocess.run(
            [
                "git",
                "ls-remote",
                "--heads",
                "https://github.com/LiTLiTschi/karafun-intercept.git",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) == 2 and parts[1].startswith("refs/heads/"):
                    branches.append(parts[1][len("refs/heads/") :])
    return sorted(branches)


def _run_intercept(state_dir: Path, *, debug: bool = False) -> int:
    """Launch the Textual TUI."""
    from karafun_intercept.app import main as _app_main

    _app_main()
    return 0


def _is_windows() -> bool:
    """Return True when running on Windows."""
    return platform.system() == "Windows"


def _report_update_result(result: subprocess.CompletedProcess[str]) -> int:
    """Print the outcome of a completed ``uv tool install`` and return exit code."""
    if result.returncode != 0:
        if result.stderr.strip():
            print(f"uv tool install failed:\n{result.stderr}", file=sys.stderr)
        return 1

    output = result.stdout.strip()
    if "already up to date" in output.lower():
        print("karafun is already up to date.")
    else:
        print(output or "karafun updated successfully.")
    return 0


def _build_update_batch(parent_pid: int, uv_cmd_line: str) -> str:
    """Build the contents of a Windows batch file that waits for *parent_pid*
    to exit before running *uv_cmd_line*.

    Using a batch file run by ``cmd.exe`` (residing in System32) avoids
    spawning a Python child from the tool's own Scripts directory, which would
    itself hold a lock that uv cannot remove.
    """
    # Escape '%' for batch-file double-precision (% -> %%) so paths or URLs
    # containing '%' don't break the script.
    uv_cmd_line = uv_cmd_line.replace("%", "%%")
    return (
        "@echo off\n"
        f"REM karafun update — detached updater (waits for parent PID {parent_pid})\n"
        f":waitloop\n"
        f'tasklist /fi "PID eq {parent_pid}" 2>nul | find "{parent_pid}" >nul 2>&1\n'
        "if %errorlevel%==0 (\n"
        "    timeout /t 1 /nobreak >nul 2>&1\n"
        "    goto waitloop\n"
        ")\n"
        "REM Parent exited — locks released.  Grace period for handle cleanup.\n"
        "timeout /t 1 /nobreak >nul 2>&1\n"
        f"{uv_cmd_line}\n"
        "exit /b %errorlevel%\n"
    )


def _run_update_windows(cmd: list[str], *, debug: bool = False) -> int:
    """Run the update on Windows via a detached updater process.

    JUSTIFICATION (PHILOSOPHY Contract 12 — Windows-specific branching):
    On Windows the running ``karafun.exe`` launcher holds an exclusive lock on
    itself in the tool's ``Scripts`` directory.  ``uv tool install --force``
    tries to remove that directory to reinstall and fails with
    "Access is denied" (os error 5).  Linux/macOS allow deleting open files,
    so this only manifests on Windows.  The detached ``cmd.exe`` child
    (residing in System32, not the locked Scripts dir) waits for the parent
    process to exit—releasing the lock—then runs the same ``uv`` command.
    """
    parent_pid = os.getpid()
    uv_cmd_line = subprocess.list2cmdline(cmd)

    batch_content = _build_update_batch(parent_pid, uv_cmd_line)
    batch_path = Path(tempfile.gettempdir()) / f"karafun-update-{parent_pid}.bat"
    batch_path.write_text(batch_content, encoding="utf-8")

    if debug:
        print(f"Detached updater batch file: {batch_path}", file=sys.stderr)

    # Spawn detached: cmd.exe (from System32, NOT in the locked Scripts dir)
    # runs the batch in a new process group.  close_fds=True ensures we do not
    # inherit handles from the locked Scripts directory.  stdout/stderr remain
    # inherited so uv output is visible in the caller's console.
    #
    # CREATE_NEW_PROCESS_GROUP is only defined on Windows; getattr lets this
    # file type-check on every platform even though _run_update_windows is
    # only ever called on Windows.
    creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        subprocess.Popen(
            ["cmd.exe", "/c", str(batch_path)],
            creationflags=creation_flags,
            close_fds=True,
        )
    except FileNotFoundError:
        print("cmd.exe not found — cannot run the detached updater.", file=sys.stderr)
        return 1

    print(
        "Update starting in a separate process...\n"
        "The current process will exit first to release the file lock on "
        "karafun.exe (Windows file locking), then the installer will run."
    )
    return 0


def _run_update(state_dir: Path, *, debug: bool = False) -> int:
    """Update karafun by reinstalling from the latest commit on the selected branch."""
    branch = _selected_branch(state_dir)
    with contextlib.suppress(OSError):
        state_dir.mkdir(parents=True, exist_ok=True)
        _install_source_path(state_dir).write_text(branch + "\n", encoding="utf-8")

    uv_path = shutil.which("uv")
    if uv_path is None:
        print("uv is required for updates.", file=sys.stderr)
        print("Install uv: https://docs.astral.sh/uv/", file=sys.stderr)
        return 1

    git_url = f"git+https://github.com/LiTLiTschi/karafun-intercept.git@{branch}"
    print(f"Installing karafun from github origin/{branch} ...")

    cmd = [
        uv_path,
        "tool",
        "install",
        "--from",
        git_url,
        "--upgrade",
        "--force",
        "karafun-intercept",
    ]

    if debug:
        print(" ".join(cmd), file=sys.stderr)

    # On Windows the running karafun.exe locks itself in the tool's Scripts
    # directory; uv's --force reinstall cannot remove the locked file.  We
    # delegate to a detached updater that waits for this process to exit first.
    if _is_windows():
        return _run_update_windows(cmd, debug=debug)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
    except KeyboardInterrupt:
        print("Update interrupted.", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print("uv is not installed or not executable.", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired:
        print("Update timed out. Check your network connection.", file=sys.stderr)
        return 1

    return _report_update_result(result)


def _run_branch_show(state_dir: Path) -> int:
    """Print the currently selected branch."""
    print(_selected_branch(state_dir))
    return 0


def _run_branch_list(state_dir: Path) -> int:
    """Print a numbered list of branches from GitHub origin."""
    branches = _github_branches()
    if not branches:
        print("No branches found.", file=sys.stderr)
        return 1
    for i, branch in enumerate(branches, 1):
        print(f"{i}) {branch}")
    return 0


def _run_branch_switch(state_dir: Path, number: int) -> int:
    """Select a branch as the update target (no local checkout)."""
    branches = _github_branches()
    if not branches:
        print("No branches found.", file=sys.stderr)
        return 1
    if number < 1 or number > len(branches):
        print(f"Error: {number} is out of range (1-{len(branches)}).", file=sys.stderr)
        return 1
    branch = branches[number - 1]
    with contextlib.suppress(OSError):
        state_dir.mkdir(parents=True, exist_ok=True)
    _selected_branch_path(state_dir).write_text(branch + "\n", encoding="utf-8")
    print(f"Selected '{branch}' as the branch for karafun update.")
    return 0


def _run_version(state_dir: Path) -> int:
    """Print version information."""
    import platform

    python_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    platform_info = f"{platform.system()}-{platform.machine()}"

    git_sha = "?"
    with contextlib.suppress(FileNotFoundError, subprocess.TimeoutExpired):
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
            timeout=5,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            git_sha = result.stdout.strip()

    install_source = "?"
    src_path = _install_source_path(state_dir)
    if src_path.is_file():
        install_source = src_path.read_text().strip()

    print(
        f"karafun={__version__} "
        f"python={python_ver} "
        f"platform={platform_info} "
        f"git={git_sha} "
        f"install={install_source}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Karafun CLI -- subcommand dispatcher."""
    parser = argparse.ArgumentParser(
        prog="karafun",
        description="Observe the local KaraFun Player in a Textual TUI",
    )
    parser.add_argument("--version", action="version", version=f"karafun {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def _add_debug(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--debug",
            action="store_true",
            default=False,
            help="Enable debug logging",
        )

    intercept_parser = sub.add_parser("intercept", help="Launch the Textual TUI")
    _add_debug(intercept_parser)

    update_parser = sub.add_parser(
        "update",
        help="Rebuild from latest commit on selected branch (github origin)",
    )
    _add_debug(update_parser)

    sub.add_parser("branch-show", help="Print the currently selected branch")
    sub.add_parser("branch-list", help="List branches from GitHub origin")
    switch_parser = sub.add_parser(
        "branch-switch", help="Select a numbered branch as the update target"
    )
    switch_parser.add_argument(
        "number",
        type=int,
        metavar="N",
        help="Branch number from 'karafun branch-list'",
    )
    sub.add_parser("version", help="Print version information")

    args = parser.parse_args(argv)
    sd = _state_dir()

    if args.command == "intercept":
        return _run_intercept(sd, debug=args.debug)
    elif args.command == "update":
        return _run_update(sd, debug=args.debug)
    elif args.command == "branch-show":
        return _run_branch_show(sd)
    elif args.command == "branch-list":
        return _run_branch_list(sd)
    elif args.command == "branch-switch":
        return _run_branch_switch(sd, args.number)
    elif args.command == "version":
        return _run_version(sd)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
