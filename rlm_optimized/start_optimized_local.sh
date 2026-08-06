#!/usr/bin/env bash
# ==============================================================================
# RLM Local Optimized Inference Starter Script (Mac OS Metal Optimized)
# ==============================================================================
# Starts a local llama.cpp server with Metal acceleration, FlashAttention,
# and TurboQuant KV cache compression.
# ==============================================================================

set -euo pipefail

# Style definitions
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

# Redirect output to log file if attached to an interactive terminal to protect TUI
mkdir -p "$PROJECT_ROOT/.torchlight"
if [ -t 1 ]; then
    exec >> "$PROJECT_ROOT/.torchlight/llama_server.log" 2>&1
fi

# Default configuration
PORT=${PORT:-8080}
KV_CACHE_COMPRESSION=${KV_CACHE_COMPRESSION:-q4_0} # q4_0, q8_0, or f16
MODEL_INPUT=${1:-""}

if [ -n "$MODEL_INPUT" ]; then
    if [ -f "$MODEL_INPUT" ]; then
        MODEL_PATH="$MODEL_INPUT"
    elif [ -f "$PROJECT_ROOT/models/$MODEL_INPUT" ]; then
        MODEL_PATH="$PROJECT_ROOT/models/$MODEL_INPUT"
    elif [ -f "$PROJECT_ROOT/models/${MODEL_INPUT}.gguf" ]; then
        MODEL_PATH="$PROJECT_ROOT/models/${MODEL_INPUT}.gguf"
    elif [[ "$MODEL_INPUT" == *"qwen"* ]]; then
        MODEL_PATH="$PROJECT_ROOT/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
    elif [[ "$MODEL_INPUT" == *"4e4b"* ]] || [[ "$MODEL_INPUT" == *"e4b"* ]] || [[ "$MODEL_INPUT" == *"E4B"* ]]; then
        MODEL_PATH="$PROJECT_ROOT/models/gemma-4-E4B-it-Q4_K_M.gguf"
    elif [[ "$MODEL_INPUT" == *"4e2b"* ]] || [[ "$MODEL_INPUT" == *"e2b"* ]] || [[ "$MODEL_INPUT" == *"E2B"* ]]; then
        MODEL_PATH="$PROJECT_ROOT/models/gemma-4-E2B-it-Q4_K_M.gguf"
    else
        MODEL_PATH="$MODEL_INPUT"
    fi
else
    MODEL_PATH="$PROJECT_ROOT/models/gemma-4-E2B-it-Q4_K_M.gguf"
fi

# Auto-detect RAM for safe context sizing
TOTAL_RAM_GB=$(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1073741824)}')
if [ "${TOTAL_RAM_GB:-0}" -le 8 ]; then
    CTX_SIZE=${CTX_SIZE:-12288}
    THREADS=${THREADS:-4}
    BATCH_SIZE=${BATCH_SIZE:-512}
    log_info "🔒 8GB RAM detected (${TOTAL_RAM_GB}GB) — safe mode: CTX=${CTX_SIZE}, threads=${THREADS}"
else
    CTX_SIZE=${CTX_SIZE:-12288}
    THREADS=${THREADS:-8}
    BATCH_SIZE=${BATCH_SIZE:-1024}
    log_info "✅ ${TOTAL_RAM_GB}GB RAM detected — TurboQuant base mode: CTX=${CTX_SIZE}, threads=${THREADS}"
fi

if [ ! -f "$MODEL_PATH" ]; then
    log_info "Model GGUF not found locally at $MODEL_PATH"
    if [ -f "$PROJECT_ROOT/rlm_optimized/venv/bin/activate" ]; then
        source "$PROJECT_ROOT/rlm_optimized/venv/bin/activate"
    fi
    if [[ "$MODEL_PATH" == *"qwen"* ]]; then
        python3 -m rlm_optimized.download_qwen
        MODEL_PATH="$PROJECT_ROOT/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
    elif [[ "$MODEL_PATH" == *"e4b"* ]] || [[ "$MODEL_PATH" == *"E4B"* ]] || [[ "$MODEL_PATH" == *"4e4b"* ]]; then
        python3 -m rlm_optimized.download_gemma4e4b
        MODEL_PATH="$PROJECT_ROOT/models/gemma-4-E4B-it-Q4_K_M.gguf"
    else
        python3 -m rlm_optimized.download_gemma
        MODEL_PATH="$PROJECT_ROOT/models/gemma-4-E2B-it-Q4_K_M.gguf"
    fi
fi

# Pre-computation tuning check for MacOS
log_info "Detecting macOS hardware capabilities..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Attempt to query wired limit or recommend working set optimizations
    log_info "Tuning GPU work limits for Metal backend..."
    RECOMMENDED_LIMIT_MB=6144
    log_warn "If running low memory contexts, run: 'sudo sysctl iogpu.wired_limit_mb=$RECOMMENDED_LIMIT_MB' to reserve VRAM."
else
    log_warn "Non-macOS system detected. Metal optimizations are skipped."
fi

# Locate llama-server / llama-cli
LLAMA_SERVER_BIN="/Users/harishgorle/.lmstudio/extensions/backends/llama.cpp-mac-arm64-apple-metal-advsimd-2.25.2/llama-server"
if ! command -v "$LLAMA_SERVER_BIN" &>/dev/null; then
    # Check common build directories
    if [ -f "./llama-cpp-turboquant/build/bin/llama-server" ]; then
        LLAMA_SERVER_BIN="./llama-cpp-turboquant/build/bin/llama-server"
    elif [ -f "./llama.cpp/build/bin/llama-server" ]; then
        LLAMA_SERVER_BIN="./llama.cpp/build/bin/llama-server"
    elif command -v "llama-server" &>/dev/null; then
        LLAMA_SERVER_BIN="llama-server"
    else
        log_error "llama-server command not found. Please install llama.cpp or compile in './llama-cpp-turboquant'."
    fi
fi

# Free port if in use by an existing server process
if lsof -ti :"$PORT" &>/dev/null; then
    log_warn "Port $PORT is currently in use. Freeing port..."
    lsof -ti :"$PORT" | xargs kill -9 2>/dev/null || true
    sleep 1
fi

log_info "Booting llama-server with the following parameters:"
log_info "  - Model: $MODEL_PATH"
log_info "  - Port: $PORT"
log_info "  - Context Size: $CTX_SIZE"
log_info "  - KV Cache Compression: $KV_CACHE_COMPRESSION"
log_info "  - FlashAttention: ON"
log_info "  - Metal GPU Layers: ALL (-ngl 99)"
log_info "  - Threads: $THREADS"
log_info "  - Batch Size: $BATCH_SIZE"

# Set global default parameters that can be overridden per model
FLASH_ATTENTION="on"
REPEAT_PENALTY="1.1"

# Launch server
EXTRA_ARGS=()
if [[ "$MODEL_PATH" == *"qwen"* ]]; then
    EXTRA_ARGS=(--jinja --chat-template-file "$SCRIPT_DIR/qwen2.jinja" --rope-freq-base 1000000)
    # Qwen 2.5 overrides to fix GQA / TurboQuant noise amplification (q8_0)
    # Note: FLASH_ATTENTION must be 'on' because llama.cpp requires it for V cache quantization
    KV_CACHE_COMPRESSION="q8_0"
    FLASH_ATTENTION="on"
    REPEAT_PENALTY="1.0"
fi

exec "$LLAMA_SERVER_BIN" \
    -m "$MODEL_PATH" \
    --port "$PORT" \
    -c "$CTX_SIZE" \
    -ngl 99 \
    -fa "$FLASH_ATTENTION" \
    -t "$THREADS" \
    -b "$BATCH_SIZE" \
    -np 1 \
    --repeat-penalty "$REPEAT_PENALTY" \
    --cache-type-k "$KV_CACHE_COMPRESSION" \
    --cache-type-v "$KV_CACHE_COMPRESSION" \
    "${EXTRA_ARGS[@]}"
