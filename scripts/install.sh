#!/usr/bin/env bash
# karafun-intercept install script (public repo)
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/LiTLiTschi/karafun-intercept/master/scripts/install.sh | sh
set -euo pipefail

# ── Prerequisites ────────────────────────────────────────────────────

if ! command -v uv &>/dev/null; then
	echo "uv is not installed."
	echo ""
	echo "You can install uv in one of the following ways:"
	echo ""
	echo "  Option A (recommended -- automatic):"
	echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
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
		curl -LsSf https://astral.sh/uv/install.sh | sh
		export PATH="$HOME/.local/bin:$PATH"
		echo "uv installed."
	else
		echo "Please install uv using one of the options above, then re-run this script."
		exit 1
	fi
fi

# ── Install ──────────────────────────────────────────────────────────

echo "Installing karafun-intercept…"
KARAFUN_REPO="git+https://github.com/LiTLiTschi/karafun-intercept.git"
uv tool install --upgrade --force "$KARAFUN_REPO"

echo ""
echo "karafun-intercept installed successfully."
echo "Run 'karafun intercept' to launch the TUI."
