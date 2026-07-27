#!/usr/bin/env bash
# ==============================================================================
# Torchlight Apple MLX Local Server Launcher (Apple Silicon Metal Optimized)
# ==============================================================================
# Launches mlx_lm.server leveraging Apple's native Metal GPU zero-copy memory.
# ==============================================================================

set -euo pipefail

MODEL=${1:-"mlx-community/gemma-2-2b-it-4bit"}
PORT=${PORT:-8080}

PYTHON_BIN="/opt/homebrew/bin/python3.11"
if ! command -v "$PYTHON_BIN" &>/dev/null; then
    PYTHON_BIN="python3"
fi

# Automatically free port if in use by an existing server
if lsof -ti :"$PORT" &>/dev/null; then
    echo "⚠️ Port $PORT is currently in use. Freeing port..."
    lsof -ti :"$PORT" | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Force HuggingFace to download MLX models into the local models directory
export HF_HOME="$(pwd)/models"

echo "🍎 Launching Apple MLX Native Metal Server..."
echo "   - Model: $MODEL"
echo "   - Port: $PORT"
echo "   - Engine: Apple MLX (Zero-Copy Unified Memory)"
echo "   - Storage: $HF_HOME/hub"

# Ensure mlx-lm is installed
if ! "$PYTHON_BIN" -c "import mlx_lm" &>/dev/null; then
    echo "📦 Installing mlx-lm for Apple Silicon GPU..."
    "$PYTHON_BIN" -m pip install mlx mlx-lm
fi

exec "$PYTHON_BIN" -m mlx_lm.server --model "$MODEL" --port "$PORT"
