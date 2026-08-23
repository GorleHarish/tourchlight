#!/usr/bin/env bash
# Torchlight TurboQuant Studio GUI Launcher
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "⚡ Starting Torchlight TurboQuant & Multi-Engine GUI Studio..."
echo "=========================================================="

if [ -f "./venv_mlx/bin/python3" ]; then
    PYTHON_EXEC="./venv_mlx/bin/python3"
else
    PYTHON_EXEC="python3"
fi

"$PYTHON_EXEC" model_tester_gui.py "$@"
