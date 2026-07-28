#!/bin/bash
set -e  # exit immediately on any error

cd "$(dirname "$0")"

# BUG FIX: check that the venv exists before trying to activate it,
# otherwise the script silently runs with the system Python which may
# not have any of the required packages installed.
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "../rlm_optimized/venv/bin/activate" ]; then
    source ../rlm_optimized/venv/bin/activate
elif [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
else
    echo "❌ Virtual environment not found. Run the following to set it up:"
    echo "   python3 -m venv venv && source venv/bin/activate && pip install -e ."
    exit 1
fi

export COLORTERM="${COLORTERM:-truecolor}"
export TERM="${TERM:-xterm-256color}"
export PYTHONPATH="$(pwd)/src:${PYTHONPATH:-}"

# Load .env if it exists (dotenv inside the app does this too, but exporting
# here means CLI commands launched from this script also see the variables).
if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

echo "⚡ Starting Torchlight CLI TUI..."
# Run the CLI interactive chat session
python3 -m context_manager.cli.main chat "$@"
