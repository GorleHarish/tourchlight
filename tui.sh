#!/usr/bin/env bash
# Script to launch the Torchlight TUI Agent

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

cleanup() {
    printf "\033[?1000l\033[?1002l\033[?1003l\033[?1006l\033[?25h" 2>/dev/null || true
    stty sane 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [ -f "rlm_optimized/venv/bin/activate" ]; then
    source rlm_optimized/venv/bin/activate
elif [ -f "context-manager-cli/venv/bin/activate" ]; then
    source context-manager-cli/venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Please set up venv in rlm_optimized or context-manager-cli."
    exit 1
fi

export COLORTERM="${COLORTERM:-truecolor}"
export TERM="${TERM:-xterm-256color}"
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"

if [[ $# -gt 0 && "$1" != -* ]]; then
    PROVIDER="$1"
    shift
else
    PROVIDER="lmstudio"
fi

ARGS=()
while [[ $# -gt 0 ]]; do
    if [[ "$1" != -* ]]; then
        ARGS+=("--model" "$1")
    else
        ARGS+=("$1")
    fi
    shift
done

python3 -m rlm_optimized.tui_app --provider "$PROVIDER" "${ARGS[@]}"
cleanup

