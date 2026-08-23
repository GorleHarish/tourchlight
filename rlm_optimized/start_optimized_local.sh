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

# Always capture server output to the log file (protects the TUI and preserves
# boot diagnostics such as ggml_metal_init / offload lines for troubleshooting).
mkdir -p "$PROJECT_ROOT/.torchlight"
if [ -t 1 ]; then
    # Interactive launch: mirror to the terminal AND the log file.
    exec > >(tee -a "$PROJECT_ROOT/.torchlight/llama_server.log") 2>&1
else
    # Non-interactive (TUI / daemonized) launch: log only.
    exec >> "$PROJECT_ROOT/.torchlight/llama_server.log" 2>&1
fi

# Default configuration
PORT=${PORT:-8080}
# KV cache: asymmetric real TurboQuant (TheTom/llama-cpp-turboquant fork).
# K stays q8_0 (exact, cheap); V uses turbo4 (~4.125 bpv) — verified safe on M1
# via the prefix-reuse quality gate (unlike q4_0 which garbles output).
KV_CACHE_TYPE_K=${KV_CACHE_TYPE_K:-q8_0}
KV_CACHE_TYPE_V=${KV_CACHE_TYPE_V:-turbo4}
if [ -n "${KV_CACHE_COMPRESSION:-}" ]; then
    if [ "$KV_CACHE_COMPRESSION" = "turbo3" ]; then
        KV_CACHE_TYPE_K="turbo3"
        KV_CACHE_TYPE_V="turbo3"
    elif [ "$KV_CACHE_COMPRESSION" = "turbo4" ]; then
        KV_CACHE_TYPE_K="q8_0"
        KV_CACHE_TYPE_V="turbo4"
    elif [ "$KV_CACHE_COMPRESSION" = "f16" ]; then
        KV_CACHE_TYPE_K="f16"
        KV_CACHE_TYPE_V="f16"
    else
        KV_CACHE_TYPE_K="$KV_CACHE_COMPRESSION"
        KV_CACHE_TYPE_V="$KV_CACHE_COMPRESSION"
    fi
fi

# YaRN / RoPE scaling for extended context (effective context = CTX_SIZE * YARN_FACTOR)
# Supported by llama.cpp TurboQuant fork. Values: 1.0 (disabled), 2.0, 4.0, 8.0
# Only works with models trained with RoPE (most modern LLMs: Llama, Gemma, Qwen, Mistral, etc.)
YARN_FACTOR=${YARN_FACTOR:-1.0}
MODEL_INPUT=${1:-""}
DRAFT_INPUT=${2:-"${DRAFT_MODEL:-""}"}
DRAFT_MAX=${DRAFT_MAX:-8}

if [ -n "$MODEL_INPUT" ]; then
    if [ -f "$MODEL_INPUT" ]; then
        MODEL_PATH="$MODEL_INPUT"
    elif [ -f "$PROJECT_ROOT/models/$MODEL_INPUT" ]; then
        MODEL_PATH="$PROJECT_ROOT/models/$MODEL_INPUT"
    elif [ -f "$PROJECT_ROOT/models/${MODEL_INPUT}.gguf" ]; then
        MODEL_PATH="$PROJECT_ROOT/models/${MODEL_INPUT}.gguf"
    else
        MATCH=$(find "$PROJECT_ROOT/models" "$HOME/.lmstudio/models" -name "*${MODEL_INPUT}*.gguf" 2>/dev/null | head -n 1 || true)
        if [ -n "$MATCH" ] && [ -f "$MATCH" ]; then
            MODEL_PATH="$MATCH"
        elif [[ "$MODEL_INPUT" == *"3b"* ]] || [[ "$MODEL_INPUT" == *"3B"* ]]; then
            MODEL_PATH="$PROJECT_ROOT/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf"
        elif [[ "$MODEL_INPUT" == *"qwen"* ]]; then
            MODEL_PATH="$PROJECT_ROOT/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
        elif [[ "$MODEL_INPUT" == *"4e4b"* ]] || [[ "$MODEL_INPUT" == *"e4b"* ]] || [[ "$MODEL_INPUT" == *"E4B"* ]]; then
            MODEL_PATH="$PROJECT_ROOT/models/gemma-4-E4B-it-Q4_K_M.gguf"
        elif [[ "$MODEL_INPUT" == *"4e2b"* ]] || [[ "$MODEL_INPUT" == *"e2b"* ]] || [[ "$MODEL_INPUT" == *"E2B"* ]] || [[ "$MODEL_INPUT" == *"gemma"* ]]; then
            MODEL_PATH="$PROJECT_ROOT/models/gemma-4-E2B-it-Q4_K_M.gguf"
        else
            MODEL_PATH="$MODEL_INPUT"
        fi
    fi
else
    MODEL_PATH="$PROJECT_ROOT/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf"
fi

# Resolve Speculative Draft Model
DRAFT_MODEL_PATH=""
if [ -n "$DRAFT_INPUT" ] && [ "$DRAFT_INPUT" != "none" ] && [ "$DRAFT_INPUT" != "None" ]; then
    if [ "$DRAFT_INPUT" = "auto" ]; then
        if [[ "$MODEL_PATH" == *"qwen"* ]]; then
            if [ -f "$PROJECT_ROOT/models/qwen2.5-coder-0.5b-instruct-q8_0.gguf" ]; then
                DRAFT_MODEL_PATH="$PROJECT_ROOT/models/qwen2.5-coder-0.5b-instruct-q8_0.gguf"
            elif [ -f "$PROJECT_ROOT/models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf" ]; then
                DRAFT_MODEL_PATH="$PROJECT_ROOT/models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
            fi
        elif [[ "$MODEL_PATH" == *"gemma"* ]] || [[ "$MODEL_PATH" == *"4e4b"* ]] || [[ "$MODEL_PATH" == *"E4B"* ]]; then
            if [ -f "$PROJECT_ROOT/models/gemma-4-E2B-it-Q4_K_M.gguf" ]; then
                DRAFT_MODEL_PATH="$PROJECT_ROOT/models/gemma-4-E2B-it-Q4_K_M.gguf"
            fi
        fi
    elif [ -f "$DRAFT_INPUT" ]; then
        DRAFT_MODEL_PATH="$DRAFT_INPUT"
    elif [ -f "$PROJECT_ROOT/models/$DRAFT_INPUT" ]; then
        DRAFT_MODEL_PATH="$PROJECT_ROOT/models/$DRAFT_INPUT"
    elif [ -f "$PROJECT_ROOT/models/${DRAFT_INPUT}.gguf" ]; then
        DRAFT_MODEL_PATH="$PROJECT_ROOT/models/${DRAFT_INPUT}.gguf"
    elif [[ "$DRAFT_INPUT" == *"0.5b"* ]] || [[ "$DRAFT_INPUT" == *"05b"* ]]; then
        DRAFT_MODEL_PATH="$PROJECT_ROOT/models/qwen2.5-coder-0.5b-instruct-q8_0.gguf"
    elif [[ "$DRAFT_INPUT" == *"1.5b"* ]] || [[ "$DRAFT_INPUT" == *"15b"* ]]; then
        DRAFT_MODEL_PATH="$PROJECT_ROOT/models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
    elif [[ "$DRAFT_INPUT" == *"4e2b"* ]] || [[ "$DRAFT_INPUT" == *"e2b"* ]] || [[ "$DRAFT_INPUT" == *"E2B"* ]] || [[ "$DRAFT_INPUT" == *"gemma"* ]]; then
        if [ -f "$PROJECT_ROOT/models/gemma-4-E2B-it-Q4_K_M.gguf" ]; then
            DRAFT_MODEL_PATH="$PROJECT_ROOT/models/gemma-4-E2B-it-Q4_K_M.gguf"
        fi
    fi
fi

# Auto-detect RAM for safe context sizing
TOTAL_RAM_GB=$(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1073741824)}')
if [ "${TOTAL_RAM_GB:-0}" -le 8 ]; then
    CTX_SIZE=${CTX_SIZE:-12288}
    THREADS=${THREADS:-3}
    BATCH_SIZE=${BATCH_SIZE:-2048}
    log_info "🔒 8GB RAM detected (${TOTAL_RAM_GB}GB) — safe mode: CTX=${CTX_SIZE}, threads=${THREADS}"
else
    CTX_SIZE=${CTX_SIZE:-12288}
    THREADS=${THREADS:-3}
    BATCH_SIZE=${BATCH_SIZE:-2048}
    log_info "✅ ${TOTAL_RAM_GB}GB RAM detected — TurboQuant base mode: CTX=${CTX_SIZE}, threads=${THREADS}"
fi

if [ ! -f "$MODEL_PATH" ]; then
    log_info "Model GGUF not found locally at $MODEL_PATH"
    if [ -f "$PROJECT_ROOT/rlm_optimized/venv/bin/activate" ]; then
        source "$PROJECT_ROOT/rlm_optimized/venv/bin/activate"
    fi
    if [[ "$MODEL_PATH" == *"3b"* ]] || [[ "$MODEL_PATH" == *"3B"* ]]; then
        python3 -m rlm_optimized.download_qwen3b
        MODEL_PATH="$PROJECT_ROOT/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf"
    elif [[ "$MODEL_PATH" == *"qwen"* ]]; then
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

# Locate llama-server: prefer the TurboQuant fork (enables turbo2/3/4 KV cache
# types), then the LM Studio bundled build, then common builds / PATH.
LLAMA_SERVER_BIN=""
if [ -f "./llama-cpp-turboquant/build/bin/llama-server" ]; then
    LLAMA_SERVER_BIN="./llama-cpp-turboquant/build/bin/llama-server"
elif [ -f "/Users/harishgorle/.lmstudio/extensions/backends/llama.cpp-mac-arm64-apple-metal-advsimd-2.25.2/llama-server" ]; then
    LLAMA_SERVER_BIN="/Users/harishgorle/.lmstudio/extensions/backends/llama.cpp-mac-arm64-apple-metal-advsimd-2.25.2/llama-server"
elif [ -f "./llama.cpp/build/bin/llama-server" ]; then
    LLAMA_SERVER_BIN="./llama.cpp/build/bin/llama-server"
elif command -v "llama-server" &>/dev/null; then
    LLAMA_SERVER_BIN="llama-server"
else
    log_error "llama-server command not found. Please install the TurboQuant fork or compile in './llama-cpp-turboquant'."
fi

# Free port if in use by an existing server process
if lsof -ti :"$PORT" &>/dev/null; then
    log_warn "Port $PORT is currently in use. Freeing port..."
    lsof -ti :"$PORT" | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Set global default parameters that can be overridden per model
FLASH_ATTENTION="on"
REPEAT_PENALTY="1.1"

# Per-model overrides (must run before the boot-log block so the log reflects reality)
EXTRA_ARGS=()
if [[ "$MODEL_PATH" == *"qwen"* ]]; then
    EXTRA_ARGS=(--jinja --chat-template-file "$SCRIPT_DIR/qwen2.jinja" --rope-freq-base 1000000)
    # Qwen 2.5: K stays q8_0, V uses turbo4 (asymmetric — symmetric turbo is
    # catastrophic on Qwen2.5 Q4_K_M, PPL 3556). turbo4 V verified coherent via
    # the prefix-reuse quality gate.
    KV_CACHE_TYPE_K="q8_0"
    KV_CACHE_TYPE_V="turbo4"
    FLASH_ATTENTION="on"
    REPEAT_PENALTY="1.0"
elif [[ "$MODEL_PATH" == *"gemma"* ]]; then
    if [ -z "$KV_CACHE_COMPRESSION" ]; then
        KV_CACHE_TYPE_K="q8_0"
        KV_CACHE_TYPE_V="q8_0"
    fi
fi

log_info "Booting llama-server with the following parameters:"
log_info "  - Model: $MODEL_PATH"
if [ -n "$DRAFT_MODEL_PATH" ] && [ -f "$DRAFT_MODEL_PATH" ]; then
    log_info "  - ⚡ Speculative Draft Model: $DRAFT_MODEL_PATH (draft-max: $DRAFT_MAX)"
fi
log_info "  - Port: $PORT"
log_info "  - Context Size: $CTX_SIZE"
if [ "$YARN_FACTOR" != "1.0" ]; then
    log_info "  - YaRN Factor: $YARN_FACTOR (effective context: $((CTX_SIZE * ${YARN_FACTOR%.*})))"
fi
log_info "  - KV Cache (K/V): $KV_CACHE_TYPE_K / $KV_CACHE_TYPE_V (TurboQuant)"
log_info "  - FlashAttention: ON"
log_info "  - Metal GPU Layers: ALL (-ngl 99)"
log_info "  - Threads: $THREADS"
log_info "  - Batch Size: $BATCH_SIZE"

exec_args=(
    "$LLAMA_SERVER_BIN"
    -m "$MODEL_PATH"
    --port "$PORT"
    -c "$CTX_SIZE"
    -ngl 99
    -fa "$FLASH_ATTENTION"
    -t "$THREADS"
    -b "$BATCH_SIZE"
    -np 1
    --repeat-penalty "$REPEAT_PENALTY"
    --cache-type-k "$KV_CACHE_TYPE_K"
    --cache-type-v "$KV_CACHE_TYPE_V"
)

if [ -n "$DRAFT_MODEL_PATH" ] && [ -f "$DRAFT_MODEL_PATH" ]; then
    exec_args+=(
        -md "$DRAFT_MODEL_PATH"
        --spec-draft-n-max "$DRAFT_MAX"
        -ngld 99
    )
fi

if [ "$YARN_FACTOR" != "1.0" ]; then
    exec_args+=(--yarn-attn-factor "$YARN_FACTOR")
fi

if [ ${#EXTRA_ARGS[@]} -gt 0 ]; then
    exec_args+=("${EXTRA_ARGS[@]}")
fi

exec "${exec_args[@]}"
