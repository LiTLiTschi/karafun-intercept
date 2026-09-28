#!/usr/bin/env bash
# karafun-intercept install script
# Usage:
#   export GH_TOKEN="$(gh auth token)"
#   curl -fsSL "https://${GH_TOKEN}@raw.githubusercontent.com/LiTLiTschi/karafun-intercept/master/scripts/install.sh" | bash
set -euo pipefail

# ── Prerequisites ────────────────────────────────────────────────────

if ! command -v uv &>/dev/null; then
	echo "uv is not installed."
	echo ""
	echo "You can install uv in one of the following ways:"
	echo ""
	echo "  Option A (recommended -- automatic):"
	echo "    curl -LsSf https://astral.sh/uv/install.sh | bash"
	echo ""
	echo "  Option B (using a package manager):"
	echo "    brew install uv        # macOS"
	echo "    sudo apt install uv    # Debian/Ubuntu"
	echo "    pip install uv         # any platform (requires pip)"
	echo ""
	echo "After installing, ensure ~/.local/bin is on your PATH:"
	echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
	echo ""
	if [ -t 0 ]; then
		printf "Install uv automatically now? [Y/n] "
		read -r INSTALL_UV
	elif [ -e /dev/tty ] && [ -r /dev/tty ] && [ -w /dev/tty ]; then
		printf "Install uv automatically now? [Y/n] " </dev/tty
		read -r INSTALL_UV </dev/tty
	else
		INSTALL_UV=""
	fi
	INSTALL_UV="${INSTALL_UV:-Y}"

	if [ "$INSTALL_UV" = "Y" ] || [ "$INSTALL_UV" = "y" ]; then
		echo "Installing uv…"
		curl -LsSf https://astral.sh/uv/install.sh | bash
		export PATH="$HOME/.local/bin:$PATH"
		echo "uv installed."
	else
		echo "Please install uv using one of the options above, then re-run this script."
		exit 1
	fi
fi

# ── Auth ─────────────────────────────────────────────────────────────

if [ -z "${GH_TOKEN:-}" ]; then
	if command -v gh &>/dev/null; then
		echo "Getting GitHub token from gh CLI…"
		export GH_TOKEN="$(gh auth token 2>/dev/null || true)"
	fi
fi

if [ -z "${GH_TOKEN:-}" ]; then
	echo "ERROR: GH_TOKEN is not set."
	echo ""
	echo "  Option A (recommended):"
	echo "    export GH_TOKEN=\$(gh auth token)"
	echo "    curl -fsSL https://raw.githubusercontent.com/LiTLiTschi/karafun-intercept/master/scripts/install.sh | bash"
	echo ""
	echo "  Option B:"
	echo "    export GH_TOKEN=ghp_xxxxx"
	echo "    curl -fsSL https://raw.githubusercontent.com/LiTLiTschi/karafun-intercept/master/scripts/install.sh | bash"
	exit 1
fi

# ── Install ──────────────────────────────────────────────────────────

echo "Installing karafun-intercept…"
KARAFUN_REPO="git+https://${GH_TOKEN}@github.com/LiTLiTschi/karafun-intercept.git"
uv tool install --upgrade --force "$KARAFUN_REPO"

echo ""
echo "karafun-intercept installed successfully."
echo "Run 'karafun intercept' to launch the TUI."
