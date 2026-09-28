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
