#!/usr/bin/env bash
# ==============================================================================
# MLX Server Starter Script for Torchlight Agent (Apple Silicon Metal)
# ==============================================================================
# Starts a local MLX OpenAI-compatible API server using mlx_lm.server
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

mkdir -p "$PROJECT_ROOT/.torchlight"
if [ -t 1 ]; then
    exec > >(tee -a "$PROJECT_ROOT/.torchlight/llama_server.log") 2>&1
else
    exec >> "$PROJECT_ROOT/.torchlight/llama_server.log" 2>&1
fi

PORT=${PORT:-8080}
MODEL_INPUT=${1:-""}
DRAFT_INPUT=${2:-"${DRAFT_MODEL:-""}"}

# Python executable in venv_mlx
if [ -f "$PROJECT_ROOT/venv_mlx/bin/python3" ]; then
    PYTHON_EXEC="$PROJECT_ROOT/venv_mlx/bin/python3"
else
    PYTHON_EXEC="python3"
fi

# Resolve Model Path
MODEL_PATH=""
CLEAN_INPUT="$(echo "$MODEL_INPUT" | sed 's|^mlx-community/||' | sed 's|^models--||' | tr '[:upper:]' '[:lower:]')"

is_valid_mlx_dir() {
    local dir="$1"
    if [ -d "$dir" ] && [ -f "$dir/config.json" ]; then
        if [ -f "$dir/model.safetensors" ] || [ -f "$dir/weights.safetensors" ]; then
            return 0
        fi
        local has_safetensors
        has_safetensors="$(find "$dir" -maxdepth 1 -name "*.safetensors" -print -quit 2>/dev/null)"
        if [ -n "$has_safetensors" ]; then
            if [ -f "$dir/model.safetensors.index.json" ]; then
                "$PYTHON_EXEC" -c "
import json, sys, os
try:
    with open('$dir/model.safetensors.index.json') as f:
        m = json.load(f).get('weight_map', {})
    req = set(m.values())
    if req and all(os.path.exists(os.path.join('$dir', x)) for x in req):
        sys.exit(0)
    sys.exit(1)
except Exception:
    sys.exit(1)
" 2>/dev/null
                return $?
            fi
            return 0
        fi
    fi
    return 1
}

# 1. Check if directly provided as directory with config.json and safetensors
if [ -n "$MODEL_INPUT" ] && is_valid_mlx_dir "$MODEL_INPUT"; then
    MODEL_PATH="$MODEL_INPUT"
# 2. Check if under $PROJECT_ROOT/models
elif [ -n "$MODEL_INPUT" ] && is_valid_mlx_dir "$PROJECT_ROOT/models/$MODEL_INPUT"; then
    MODEL_PATH="$PROJECT_ROOT/models/$MODEL_INPUT"
fi

# 3. Search ~/.cache/huggingface/hub for cached MLX snapshots if not resolved or if input was a GGUF/alias
if [ -z "$MODEL_PATH" ] && [ -n "$CLEAN_INPUT" ] && [[ "$CLEAN_INPUT" != *".gguf"* ]]; then
    for snap_dir in $(find "$HOME/.cache/huggingface/hub" -name "snapshots" 2>/dev/null); do
        hub_model_dir="$(dirname "$snap_dir")"
        hub_name="$(basename "$hub_model_dir" | tr '[:upper:]' '[:lower:]')"
        if [[ "$hub_name" == *"$CLEAN_INPUT"* ]] || [[ "$CLEAN_INPUT" == *"$hub_name"* ]]; then
            for s in "$snap_dir"/*; do
                if is_valid_mlx_dir "$s"; then
                    MODEL_PATH="$s"
                    break 2
                fi
            done
        fi
    done
fi

# 4. Handle Gemma / DeepSeek / Qwen specific fallbacks
if [ -z "$MODEL_PATH" ]; then
    INPUT_LOWER="$(echo "$MODEL_INPUT" | tr '[:upper:]' '[:lower:]')"
    if [[ "$INPUT_LOWER" == *"gemma"* ]] || [[ "$INPUT_LOWER" == *"4e4b"* ]] || [[ "$INPUT_LOWER" == *"4e2b"* ]] || [[ "$INPUT_LOWER" == *"e4b"* ]] || [[ "$INPUT_LOWER" == *"e2b"* ]]; then
        # Search for local gemma dir or cached MLX snapshot
        for gemma_dir in "$PROJECT_ROOT/models"/gemma* "$PROJECT_ROOT/models"/*gemma*; do
            if is_valid_mlx_dir "$gemma_dir"; then
                MODEL_PATH="$gemma_dir"
                break
            fi
        done
        if [ -z "$MODEL_PATH" ]; then
            for snap in $(find "$HOME/.cache/huggingface/hub" -path "*gemma*" -name "config.json" 2>/dev/null); do
                s_dir="$(dirname "$snap")"
                if is_valid_mlx_dir "$s_dir"; then
                    MODEL_PATH="$s_dir"
                    break
                fi
            done
        fi
        if [ -z "$MODEL_PATH" ]; then
            if [[ "$INPUT_LOWER" == *"bf16"* ]] && ([[ "$INPUT_LOWER" == *"e2b"* ]] || [[ "$INPUT_LOWER" == *"4e2b"* ]]); then
                MODEL_PATH="mlx-community/gemma-4-e2b-it-bf16"
            elif [[ "$INPUT_LOWER" == *"4e4b"* ]] || [[ "$INPUT_LOWER" == *"e4b"* ]] || [[ "$INPUT_LOWER" == *"4e4"* ]] || [[ "$INPUT_LOWER" == *"44b"* ]]; then
                MODEL_PATH="mlx-community/gemma-4-E4B-it-4bit"
            elif [[ "$INPUT_LOWER" == *"4e2b"* ]] || [[ "$INPUT_LOWER" == *"e2b"* ]] || [[ "$INPUT_LOWER" == *"4e2"* ]] || [[ "$INPUT_LOWER" == *"gemma4"* ]]; then
                MODEL_PATH="mlx-community/gemma-4-E2B-it-4bit"
            elif [[ "$INPUT_LOWER" == *"gemma3"* ]] || [[ "$INPUT_LOWER" == *"gemma-3"* ]]; then
                if [[ "$INPUT_LOWER" == *"1b"* ]]; then
                    MODEL_PATH="mlx-community/gemma-3-1b-it-4bit"
                elif [[ "$INPUT_LOWER" == *"12b"* ]]; then
                    MODEL_PATH="mlx-community/gemma-3-12b-it-4bit"
                elif [[ "$INPUT_LOWER" == *"27b"* ]]; then
                    MODEL_PATH="mlx-community/gemma-3-27b-it-4bit"
                else
                    MODEL_PATH="mlx-community/gemma-3-4b-it-4bit"
                fi
            elif [[ "$INPUT_LOWER" == *"9b"* ]]; then
                MODEL_PATH="mlx-community/gemma-2-9b-it-4bit"
            elif [[ "$INPUT_LOWER" == *"27b"* ]]; then
                MODEL_PATH="mlx-community/gemma-2-27b-it-4bit"
            else
                MODEL_PATH="mlx-community/gemma-2-2b-it-4bit"
            fi
        fi
    elif [[ "$INPUT_LOWER" == *"deepseek"* ]] || [[ "$INPUT_LOWER" == *"r1"* ]]; then
        if is_valid_mlx_dir "$PROJECT_ROOT/models/DeepSeek-R1-Distill-Qwen-7B-4bit"; then
            MODEL_PATH="$PROJECT_ROOT/models/DeepSeek-R1-Distill-Qwen-7B-4bit"
        else
            # Search for any valid cached deepseek snapshot
            for snap in $(find "$HOME/.cache/huggingface/hub" -path "*deepseek*" -name "config.json" 2>/dev/null); do
                s_dir="$(dirname "$snap")"
                if is_valid_mlx_dir "$s_dir"; then
                    MODEL_PATH="$s_dir"
                    break
                fi
            done
            if [ -z "$MODEL_PATH" ]; then
                if [[ "$INPUT_LOWER" == *"7b"* ]]; then
                    MODEL_PATH="mlx-community/DeepSeek-R1-Distill-Qwen-7B-4bit"
                else
                    MODEL_PATH="mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit"
                fi
            fi
        fi
    elif [[ "$INPUT_LOWER" == *"qwen"* ]]; then
        if is_valid_mlx_dir "$PROJECT_ROOT/models/Qwen2.5-Coder-3B-Instruct-4bit"; then
            MODEL_PATH="$PROJECT_ROOT/models/Qwen2.5-Coder-3B-Instruct-4bit"
        else
            if [[ "$INPUT_LOWER" == *"1.5b"* ]] || [[ "$INPUT_LOWER" == *"15b"* ]]; then
                MODEL_PATH="mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
            elif [[ "$INPUT_LOWER" == *"7b"* ]]; then
                MODEL_PATH="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
            else
                MODEL_PATH="mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"
            fi
        fi
    elif [[ "$MODEL_INPUT" == *"/"* ]]; then
        MODEL_PATH="$MODEL_INPUT"
    else
        # Default fallback
        if is_valid_mlx_dir "$PROJECT_ROOT/models/DeepSeek-R1-Distill-Qwen-7B-4bit"; then
            MODEL_PATH="$PROJECT_ROOT/models/DeepSeek-R1-Distill-Qwen-7B-4bit"
        elif is_valid_mlx_dir "$PROJECT_ROOT/models/Qwen2.5-Coder-3B-Instruct-4bit"; then
            MODEL_PATH="$PROJECT_ROOT/models/Qwen2.5-Coder-3B-Instruct-4bit"
        else
            MODEL_PATH="mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit"
        fi
    fi
fi

# Free port if occupied
if lsof -ti :"$PORT" &>/dev/null; then
    log_warn "Port $PORT is currently in use. Freeing port..."
    lsof -ti :"$PORT" | xargs kill -9 2>/dev/null || true
    sleep 1
fi

log_info "Booting Apple MLX Server for Torchlight Agent:"
log_info "  - Model: $MODEL_PATH"
log_info "  - Port: $PORT"
log_info "  - Python: $PYTHON_EXEC"

EXEC_ARGS=(
    "$PYTHON_EXEC" -m mlx_lm.server
    --model "$MODEL_PATH"
    --port "$PORT"
    --host "127.0.0.1"
    --max-tokens 2048
    --temp 0.2
    --min-p 0.05
)

if [ -n "$DRAFT_INPUT" ] && [ "$DRAFT_INPUT" != "none" ] && [ -d "$DRAFT_INPUT" ]; then
    log_info "  - Speculative Draft Model: $DRAFT_INPUT"
    EXEC_ARGS+=(--draft-model "$DRAFT_INPUT")
fi

log_success "Launching MLX API Server on http://127.0.0.1:$PORT/v1..."
exec "${EXEC_ARGS[@]}"
