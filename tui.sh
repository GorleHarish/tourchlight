#!/usr/bin/env bash
# Script to launch the Torchlight TUI Agent

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "rlm_optimized/venv/bin/activate" ]; then
    source rlm_optimized/venv/bin/activate
elif [ -f "context-manager-cli/venv/bin/activate" ]; then
    source context-manager-cli/venv/bin/activate
else
    echo "❌ Virtual environment not found. Please set up venv in rlm_optimized or context-manager-cli."
    exit 1
fi

export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"

if [[ $# -gt 0 && "$1" != -* ]]; then
    PROVIDER="$1"
    shift
else
    PROVIDER="lmstudio"
fi

exec python3 -m rlm_optimized.tui_app --provider "$PROVIDER" "$@"
