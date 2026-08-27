"""
Configuration settings, model registries, context profiles, and hardware detection for Torchlight.

Modularized into:
- rlm_optimized.config_hardware: Apple Silicon detection & thread tuning
- rlm_optimized.config_context: ContextProfile & budget allocations
- rlm_optimized.config_models: Model normalization & multi-provider discovery
"""

from __future__ import annotations

import os

from rlm_optimized.config_context import (
    ContextProfile,
    estimate_metadata_overhead,
    get_context_profile,
)
from rlm_optimized.config_hardware import (
    CHIP_NAME,
    IS_8GB_DEVICE,
    IS_MACOS,
    METAL_GPU_LAYERS,
    THREADS,
    TOTAL_RAM_GB,
    _detect_apple_silicon_ram,
    _detect_chip,
    is_port_in_use,
)
from rlm_optimized.config_models import (
    fetch_provider_models,
    format_model_display_name,
    is_valid_mlx_directory,
    list_available_draft_models,
    list_available_models,
    normalize_model_name,
)

# ── Provider Mode ───────────────────────────────────────────────
# Options: "llama-cpp", "lmstudio", "ollama", "vllm", "openai", "groq"
PROVIDER = os.environ.get("RLM_PROVIDER", "llama-cpp")

# ── LM Studio (OpenAI-compatible local server) ──────────────────────────
LMSTUDIO_BASE_URL = os.environ.get("RLM_LMSTUDIO_URL", "http://localhost:1234/v1")
LMSTUDIO_API_KEY = os.environ.get("RLM_LMSTUDIO_API_KEY", "not-needed")

# ── Local Optimized Engine (llama.cpp / vLLM / Ollama / MLX) ───────────────
MODEL_NAME = os.environ.get("RLM_MODEL_NAME", "gemma-4-E2B-it")
if PROVIDER == "lmstudio":
    LOCAL_API_BASE_URL = os.environ.get("RLM_LOCAL_API_URL", LMSTUDIO_BASE_URL)
    LOCAL_API_KEY = os.environ.get("RLM_LOCAL_API_KEY", LMSTUDIO_API_KEY)
elif PROVIDER == "ollama":
    LOCAL_API_BASE_URL = os.environ.get(
        "RLM_LOCAL_API_URL", "http://localhost:11434/v1"
    )
    LOCAL_API_KEY = os.environ.get("RLM_LOCAL_API_KEY", "not-needed")
else:
    # Default for llama-cpp / turbo / mlx: llama-server runs on port 8080
    LOCAL_API_BASE_URL = os.environ.get("RLM_LOCAL_API_URL", "http://localhost:8080/v1")
    LOCAL_API_KEY = os.environ.get("RLM_LOCAL_API_KEY", "not-needed")

# ── Cloud Provider Engine ──────────────────────────────────────
CLOUD_MODEL = os.environ.get("RLM_CLOUD_MODEL", "gemini-2.5-flash")
CLOUD_BASE_URL = os.environ.get("RLM_CLOUD_BASE_URL", "")
CLOUD_API_KEY = os.environ.get("RLM_CLOUD_API_KEY", "")

# ── Grammar Validation ─────────────────────────────────────────
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
GRAMMAR_FILE = os.environ.get(
    "RLM_GRAMMAR_FILE", os.path.join(_PKG_DIR, "grammar.gbnf")
)
USE_GRAMMAR_CONSTRAINT = os.environ.get("RLM_USE_GRAMMAR", "true").lower() in (
    "true",
    "1",
    "yes",
)

# ── AST Knowledge Graph ──────────────────────────────────────────
AST_DB_DIRNAME = os.environ.get("RLM_AST_DB_DIRNAME", ".torchlight_ast_db")

# ── Reasoning Constraints ──────────────────────────────────────
MAX_RECURSION_DEPTH = int(os.environ.get("RLM_MAX_RECURSION", "4"))
MAX_ITERATIONS_PER_LEVEL = int(
    os.environ.get("RLM_MAX_ITERATIONS", "15" if IS_8GB_DEVICE else "30")
)
MAX_THINKING_LOOPS = int(os.environ.get("RLM_MAX_THINKING_LOOPS", "6"))

# ── Context Window (Auto-scaled for hardware) ──────────────────
if PROVIDER == "lmstudio":
    CTX_SIZE = int(os.environ.get("RLM_CTX_SIZE", "4096"))
elif PROVIDER in ("llama-cpp", "turbo", "turboquant") or IS_8GB_DEVICE:
    CTX_SIZE = int(os.environ.get("RLM_CTX_SIZE", "12288"))
else:
    CTX_SIZE = int(os.environ.get("RLM_CTX_SIZE", "16384"))

# ── Generation Parameters ──────────────────────────────────────
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.7"))
TOP_P = float(os.environ.get("TOP_P", "0.9"))
REPEAT_PENALTY = float(
    os.environ.get("REPEAT_PENALTY", os.environ.get("REPETITION_PENALTY", "1.1"))
)
REPETITION_PENALTY = REPEAT_PENALTY
PRESENCE_PENALTY = float(os.environ.get("PRESENCE_PENALTY", "0.0"))
FREQUENCY_PENALTY = float(os.environ.get("FREQUENCY_PENALTY", "0.0"))
NUM_PREDICT = int(os.environ.get("NUM_PREDICT", "1024"))

# ── Sandbox Settings ───────────────────────────────────────────
CODE_TIMEOUT_SECONDS = 10
ALLOWED_MODULES = [
    "math",
    "json",
    "re",
    "collections",
    "itertools",
    "functools",
    "statistics",
    "random",
    "datetime",
    "string",
    "os",
    "sys",
    "pathlib",
    "glob",
    "shutil",
    "subprocess",
]

__all__ = [
    "IS_MACOS",
    "TOTAL_RAM_GB",
    "CHIP_NAME",
    "IS_8GB_DEVICE",
    "_detect_apple_silicon_ram",
    "_detect_chip",
    "METAL_GPU_LAYERS",
    "THREADS",
    "is_port_in_use",
    "PROVIDER",
    "LMSTUDIO_BASE_URL",
    "LMSTUDIO_API_KEY",
    "LOCAL_API_BASE_URL",
    "LOCAL_API_KEY",
    "MODEL_NAME",
    "CLOUD_MODEL",
    "CLOUD_BASE_URL",
    "CLOUD_API_KEY",
    "GRAMMAR_FILE",
    "USE_GRAMMAR_CONSTRAINT",
    "AST_DB_DIRNAME",
    "MAX_RECURSION_DEPTH",
    "MAX_ITERATIONS_PER_LEVEL",
    "MAX_THINKING_LOOPS",
    "CTX_SIZE",
    "ContextProfile",
    "get_context_profile",
    "estimate_metadata_overhead",
    "TEMPERATURE",
    "TOP_P",
    "REPEAT_PENALTY",
    "REPETITION_PENALTY",
    "PRESENCE_PENALTY",
    "FREQUENCY_PENALTY",
    "NUM_PREDICT",
    "CODE_TIMEOUT_SECONDS",
    "ALLOWED_MODULES",
    "normalize_model_name",
    "format_model_display_name",
    "is_valid_mlx_directory",
    "list_available_models",
    "list_available_draft_models",
    "fetch_provider_models",
]
