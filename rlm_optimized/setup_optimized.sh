#!/usr/bin/env bash
# ==============================================================================
# RLM Local Optimized Setup Script
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

info "Setting up Python virtual environment for RLM optimized package..."
if [ ! -d "rlm_optimized/venv" ]; then
    python3 -m venv rlm_optimized/venv
    ok "Created rlm_optimized/venv/"
fi

info "Installing dependencies inside virtual environment..."
source rlm_optimized/venv/bin/activate
pip install --upgrade pip --quiet
pip install -r rlm_optimized/requirements.txt --quiet
ok "Dependencies installed successfully."

# Check for llama-server binary in common places
info "Checking for local llama.cpp installation..."
if command -v llama-server &>/dev/null; then
    ok "llama-server found in system PATH."
elif [ -f "./llama-cpp-turboquant/build/bin/llama-server" ] || [ -f "./llama.cpp/build/bin/llama-server" ]; then
    ok "llama-server binary found in build directories."
else
    info "llama.cpp not found. To build it with TurboQuant options:"
    info "  git clone https://github.com/ggerganov/llama.cpp.git"
    info "  cd llama.cpp && make"
fi

ok "Setup Complete! Start your local server first and then launch RLM."
info "To start server:  ./rlm_optimized/start_optimized_local.sh <model_path>"
info "To run RLM:       source rlm_optimized/venv/bin/activate && python3 -m rlm_optimized.main_optimized"
