import json
import glob
import os
import platform
import subprocess as _sp

# ── Hardware Detection ─────────────────────────────────────────
# Auto-detect Apple Silicon chip and RAM for safe default tuning.


def _detect_apple_silicon_ram() -> int:
    """Detect total RAM in GB on macOS."""
    try:
        out = _sp.check_output(
            ["sysctl", "-n", "hw.memsize"], text=True, timeout=3
        ).strip()
        return int(out) // (1024**3)
    except Exception:
        return 0


def _detect_chip() -> str:
    """Detect Apple Silicon chip name (e.g., 'Apple M1')."""
    try:
        out = _sp.check_output(
            ["sysctl", "-n", "machdep.cpu.brand_string"], text=True, timeout=3
        ).strip()
        return out
    except Exception:
        return "unknown"


IS_MACOS = platform.system() == "Darwin"
TOTAL_RAM_GB = _detect_apple_silicon_ram() if IS_MACOS else 0
CHIP_NAME = _detect_chip() if IS_MACOS else "unknown"
IS_8GB_DEVICE = 0 < TOTAL_RAM_GB <= 8

# ── Provider Mode ───────────────────────────────────────────────
# Options: "llama-cpp", "lmstudio", "ollama", "vllm", "openai", "groq"
PROVIDER = os.environ.get("RLM_PROVIDER", "llama-cpp")

# ── LM Studio (OpenAI-compatible local server) ──────────────────────────
# LM Studio's "Local Server" tab defaults to this URL. It exposes the same
# /v1/chat/completions and /v1/models endpoints as llama.cpp / Ollama.
LMSTUDIO_BASE_URL = os.environ.get("RLM_LMSTUDIO_URL", "http://localhost:1234/v1")
LMSTUDIO_API_KEY = os.environ.get("RLM_LMSTUDIO_API_KEY", "not-needed")

# ── Local Optimized Engine (llama.cpp / vLLM / Ollama / MLX) ───────────────
# NOTE: previously this defaulted to Ollama's port (11434) even when PROVIDER
# was left at its default — meaning an LM Studio user who never set
# RLM_LOCAL_API_URL by hand would silently talk to whatever (if anything)
# was listening on 11434 instead of LM Studio. LOCAL_API_BASE_URL now
# resolves to LMSTUDIO_BASE_URL whenever PROVIDER == "lmstudio", so the
# right endpoint is used automatically instead of depending on the env var
# being set correctly.
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
# Directory name for the per-workspace Kuzu graph DB. Always resolved
# relative to the active project_root (never the process cwd) so it
# can never silently point at a stale or wrong-project graph after /cd.
AST_DB_DIRNAME = os.environ.get("RLM_AST_DB_DIRNAME", ".torchlight_ast_db")

# ── Reasoning Constraints ──────────────────────────────────────
MAX_RECURSION_DEPTH = int(os.environ.get("RLM_MAX_RECURSION", "4"))
MAX_ITERATIONS_PER_LEVEL = int(
    os.environ.get("RLM_MAX_ITERATIONS", "15" if IS_8GB_DEVICE else "30")
)
MAX_THINKING_LOOPS = int(os.environ.get("RLM_MAX_THINKING_LOOPS", "6"))

# ── Context Window (Auto-scaled for hardware) ──────────────────
# 8GB M1: 12288 safe default (q4_0 KV ≈ 0.3GB)
# 16GB+: 16384 default (q4_0 KV ≈ 0.4GB)
if PROVIDER == "lmstudio":
    # LM Studio silently drops oldest messages (context shift) if we exceed its loaded context size.
    # Defaulting to 4096 ensures our TieredMemory compresses BEFORE LM Studio drops our System Prompt.
    CTX_SIZE = int(os.environ.get("RLM_CTX_SIZE", "4096"))
elif PROVIDER in ("llama-cpp", "turbo", "turboquant") or IS_8GB_DEVICE:
    # Base 12288 tokens for TurboQuant setup (q4_0 KV ≈ 0.3GB)
    CTX_SIZE = int(os.environ.get("RLM_CTX_SIZE", "12288"))
else:
    CTX_SIZE = int(os.environ.get("RLM_CTX_SIZE", "16384"))

# ── Context Profiles ──────────────────────────────────────────────
# Model-aware budget allocations for different context window sizes
from enum import Enum


class ContextProfile(Enum):
    """Context window profiles with profile-specific budget allocations."""
    SMALL_4K = "4k"       # 4096 tokens - Gemma 2B, small models
    MEDIUM_8K = "8k"      # 8192 tokens - medium models
    LARGE_12K = "12k"     # 12288 tokens - TurboQuant base (default)
    XLARGE_32K = "32k"    # 32768 tokens - large context models
    CUSTOM = "custom"     # Custom context size

    @classmethod
    def from_context_size(cls, ctx_size: int) -> "ContextProfile":
        """Auto-detect profile from context size."""
        if ctx_size <= 5000:
            return cls.SMALL_4K
        elif ctx_size <= 9000:
            return cls.MEDIUM_8K
        elif ctx_size <= 16000:
            return cls.LARGE_12K
        elif ctx_size <= 40000:
            return cls.XLARGE_32K
        else:
            return cls.CUSTOM

    def get_budget_allocations(self, max_tokens: int, metadata_overhead: int = 0) -> dict:
        """Get profile-specific budget allocations."""
        available = max(0, max_tokens - metadata_overhead)
        
        if self == ContextProfile.SMALL_4K:
            return {
                "recent_window": 1,
                "recent_tokens_fraction": 0.40,
                "pinned_token_budget": 200,
                "compression_threshold": 0.80,
                "summary_trigger_fraction": 0.40,
                "message_compact_threshold": 200,
                "l0_scratchpad_fraction": 0.10,
                "max_messages": 50,
            }
        elif self == ContextProfile.MEDIUM_8K:
            return {
                "recent_window": 2,
                "recent_tokens_fraction": 0.35,
                "pinned_token_budget": 300,
                "compression_threshold": 0.80,
                "summary_trigger_fraction": 0.50,
                "message_compact_threshold": 300,
                "l0_scratchpad_fraction": 0.08,
                "max_messages": 75,
            }
        elif self == ContextProfile.LARGE_12K:
            return {
                "recent_window": 3,
                "recent_tokens_fraction": 0.25,
                "pinned_token_budget": 600,
                "compression_threshold": 0.75,
                "summary_trigger_fraction": 0.75,
                "message_compact_threshold": 500,
                "l0_scratchpad_fraction": 0.07,
                "max_messages": 100,
            }
        elif self == ContextProfile.XLARGE_32K:
            return {
                "recent_window": 5,
                "recent_tokens_fraction": 0.20,
                "pinned_token_budget": 1000,
                "compression_threshold": 0.70,
                "summary_trigger_fraction": 0.75,
                "message_compact_threshold": 800,
                "l0_scratchpad_fraction": 0.05,
                "max_messages": 200,
            }
        else:
            # Custom - use 12K defaults
            return {
                "recent_window": 3,
                "recent_tokens_fraction": 0.25,
                "pinned_token_budget": 600,
                "compression_threshold": 0.75,
                "summary_trigger_fraction": 0.75,
                "message_compact_threshold": 500,
                "l0_scratchpad_fraction": 0.07,
                "max_messages": 100,
            }

    def apply_to_config(self, config, max_tokens: int, metadata_overhead: int = 0) -> None:
        """Apply profile-specific settings to a MemoryConfig."""
        allocations = self.get_budget_allocations(max_tokens, metadata_overhead)
        available = max(0, max_tokens - metadata_overhead)
        
        config.recent_window = allocations["recent_window"]
        config.recent_tokens = int(available * allocations["recent_tokens_fraction"])
        config.pinned_token_budget = allocations["pinned_token_budget"]
        config.compression_threshold = allocations["compression_threshold"]
        config.summary_trigger_tokens = int(available * allocations["summary_trigger_fraction"])
        config.message_compact_threshold = allocations["message_compact_threshold"]
        config.max_messages = allocations["max_messages"]


def get_context_profile() -> ContextProfile:
    """Get the current context profile based on CTX_SIZE."""
    return ContextProfile.from_context_size(CTX_SIZE)


# ── Generation Parameters ──────────────────────────────────────
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.7"))
TOP_P = float(os.environ.get("TOP_P", "0.9"))
REPEAT_PENALTY = float(
    os.environ.get("REPEAT_PENALTY", os.environ.get("REPETITION_PENALTY", "1.10"))
)
REPETITION_PENALTY = REPEAT_PENALTY
PRESENCE_PENALTY = float(os.environ.get("PRESENCE_PENALTY", "0.20"))
FREQUENCY_PENALTY = float(os.environ.get("FREQUENCY_PENALTY", "0.15"))
# Finite default safety bound: if the GBNF grammar is ever dropped (e.g. a
# future server switch that rejects it again), unlimited generation (-1) lets
# the model ramble until the client timeout and kills the loop. 2048 tokens is
# generous for a single tool call / step; override with RLM_NUM_PREDICT.
NUM_PREDICT = int(os.environ.get("RLM_NUM_PREDICT", "2048"))


def estimate_metadata_overhead(
    system_content: str = "", ctx_size: int = CTX_SIZE
) -> int:
    """Estimate tokens consumed by system prompt, tool schemas, and the flashlight beam."""
    base = max(400, len(system_content) // 4) if system_content else 800
    if ctx_size <= 5000:
        beam = 600
    elif ctx_size <= 9000:
        beam = 1500
    else:
        beam = 3000
    return base + beam


# ── M1 Thread Tuning ──────────────────────────────────────────
# M1 has 4 performance + 4 efficiency cores. Use perf cores only
# to avoid thread migration overhead on unified memory.
METAL_GPU_LAYERS = 99
THREADS = 4 if IS_8GB_DEVICE else 8

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


def normalize_model_name(name: str, provider: str = "") -> str:
    """Normalize model alias names (e.g. 'gemma-2-2b', 'qwen', 'gemma 4 E2B', 'gemma 4 4e4b', 'gemma 3 4b')."""
    if not name:
        return name
    name_str = str(name).strip()
    provider_clean = (provider or "").lower().strip()
    if provider_clean in ("lmstudio", "ollama") or name_str.startswith("lmstudio"):
        return name_str

    name_lower = (
        name_str.lower()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .replace(":", "")
    )
    if provider_clean == "mlx" or "mlx" in name_lower:
        if "deepseek" in name_lower or "r1" in name_lower:
            if "1.5b" in name_lower or "15b" in name_lower:
                return "mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit"
            return "mlx-community/DeepSeek-R1-Distill-Qwen-7B-4bit"
        if "qwen" in name_lower or name_lower == "qwen2.5coder":
            if "1.5b" in name_lower or "15b" in name_lower:
                return "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
            elif "3b" in name_lower:
                return "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"
            return "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
        if (
            "gemma" in name_lower
            or "4e4b" in name_lower
            or "4e4" in name_lower
            or "e4b" in name_lower
            or "4e2b" in name_lower
            or "4e2" in name_lower
            or "e2b" in name_lower
        ):
            if "4e4b" in name_lower or "4e4" in name_lower or "e4b" in name_lower or "44b" in name_lower:
                return "mlx-community/gemma-4-E4B-it-4bit"
            if "4e2b" in name_lower or "4e2" in name_lower or "e2b" in name_lower or "gemma4" in name_lower:
                return "mlx-community/gemma-4-E2B-it-4bit"
            if "gemma3" in name_lower:
                if "1b" in name_lower:
                    return "mlx-community/gemma-3-1b-it-4bit"
                if "12b" in name_lower:
                    return "mlx-community/gemma-3-12b-it-4bit"
                if "27b" in name_lower:
                    return "mlx-community/gemma-3-27b-it-4bit"
                return "mlx-community/gemma-3-4b-it-4bit"
            if "gemma2" in name_lower:
                if "9b" in name_lower:
                    return "mlx-community/gemma-2-9b-it-4bit"
                if "27b" in name_lower:
                    return "mlx-community/gemma-2-27b-it-4bit"
                return "mlx-community/gemma-2-2b-it-4bit"
            return "mlx-community/gemma-2-2b-it-4bit"
    if "deepseek" in name_lower or "r1" in name_lower:
        if "1.5b" in name_lower or "15b" in name_lower:
            return "deepseek-r1-distill-qwen-1.5b"
        return "deepseek-r1-distill-qwen-7b"
    if "qwen" in name_lower:
        if "1.5b" in name_lower or "15b" in name_lower:
            return "qwen2.5-coder-1.5b-instruct"
        elif "3b" in name_lower:
            return "qwen2.5-coder-3b-instruct"
        return "qwen2.5-coder-7b-instruct"
    if (
        "gemma4e4b" in name_lower
        or "gemma4e4" in name_lower
        or "gemma44b" in name_lower
        or "4e4b" in name_lower
        or "e4b" in name_lower
    ):
        return "gemma-4-E4B-it"
    if "gemma4e2b" in name_lower or "gemma4e2" in name_lower or "4e2b" in name_lower or "e2b" in name_lower:
        return "gemma-4-E2B-it"
    if "gemma4" in name_lower:
        return "gemma-4-E2B-it"
    if "gemma3" in name_lower or "gemma-3" in name_lower:
        if "1b" in name_lower:
            return "gemma-3-1b-it"
        if "12b" in name_lower:
            return "gemma-3-12b-it"
        if "27b" in name_lower:
            return "gemma-3-27b-it"
        if "4b" in name_lower:
            return "gemma-3-4b-it"
        return "gemma3:4b"
    if "gemma2" in name_lower or "gemma-2" in name_lower:
        if "9b" in name_lower:
            return "gemma-2-9b-it"
        if "27b" in name_lower:
            return "gemma-2-27b-it"
        return "gemma-2-2b-it"
    if "gemma" in name_lower:
        if "9b" in name_lower:
            return "gemma-2-9b-it"
        if "27b" in name_lower:
            return "gemma-2-27b-it"
        if "4b" in name_lower:
            return "gemma-4-E4B-it"
        if "2b" in name_lower:
            return "gemma-2-2b-it"
    return name_str


def format_model_display_name(fname_or_id: str, provider: str = "") -> str:
    """Format a model ID or filename into a concise, human-readable display name.

    Examples:
        - 'qwen2.5-coder-3b-instruct-q4_k_m.gguf' -> 'Qwen 2.5 Coder 3B'
        - 'qwen2.5-coder-7b-instruct-q4_k_m.gguf' -> 'Qwen 2.5 Coder 7B'
        - 'DeepSeek-R1-Distill-Qwen-1.5B-4bit' -> 'DeepSeek R1 Distill 1.5B (MLX)'
        - 'gemma-4-E2B-it-Q4_K_M.gguf' -> 'Gemma 4 E2B'
        - 'gemma-4-E4B-it-Q4_K_M.gguf' -> 'Gemma 4 E4B'
        - 'mlx-community/gemma-4-E4B-it-4bit' -> 'Gemma 4 E4B (MLX)'
        - 'mlx-community/gemma-2-2b-it-4bit' -> 'Gemma 2 2B (MLX)'
        - 'gemini-2.5-flash' -> 'Gemini 2.5 Flash'
    """
    if not fname_or_id:
        return ""
    import re

    raw = str(fname_or_id).replace(".gguf", "").replace("Local GGUF:", "").strip()
    raw_lower = raw.lower()

    if "deepseek" in raw_lower or "r1" in raw_lower:
        base = "DeepSeek R1 Distill"
        if "1.5b" in raw_lower or "15b" in raw_lower:
            name = f"{base} 1.5B"
        elif "7b" in raw_lower:
            name = f"{base} 7B"
        elif "8b" in raw_lower:
            name = f"{base} 8B"
        elif "14b" in raw_lower:
            name = f"{base} 14B"
        elif "32b" in raw_lower:
            name = f"{base} 32B"
        elif "70b" in raw_lower:
            name = f"{base} 70B"
        else:
            name = base
        if "mlx" in raw_lower or provider == "mlx":
            name += " (MLX)"
        return name

    if "qwen" in raw_lower:
        base = "Qwen 2.5 Coder"
        if "0.5b" in raw_lower or "05b" in raw_lower:
            name = f"{base} 0.5B"
        elif "1.5b" in raw_lower or "15b" in raw_lower:
            name = f"{base} 1.5B"
        elif "3b" in raw_lower:
            name = f"{base} 3B"
        elif "7b" in raw_lower:
            name = f"{base} 7B"
        elif "14b" in raw_lower:
            name = f"{base} 14B"
        elif "32b" in raw_lower:
            name = f"{base} 32B"
        else:
            name = base
        if "mlx" in raw_lower or provider == "mlx":
            name += " (MLX)"
        return name

    if "gemma" in raw_lower:
        if "4e2b" in raw_lower or "4-e2b" in raw_lower or "e2b" in raw_lower:
            name = "Gemma 4 E2B"
        elif "4e4b" in raw_lower or "4-e4b" in raw_lower or "e4b" in raw_lower:
            name = "Gemma 4 E4B"
        elif "3:4b" in raw_lower or "gemma3-4b" in raw_lower or "gemma-3-4b" in raw_lower:
            name = "Gemma 3 4B"
        elif "3:1b" in raw_lower or "gemma3-1b" in raw_lower or "gemma-3-1b" in raw_lower:
            name = "Gemma 3 1B"
        elif "3:12b" in raw_lower or "gemma3-12b" in raw_lower or "gemma-3-12b" in raw_lower:
            name = "Gemma 3 12B"
        elif "3:27b" in raw_lower or "gemma3-27b" in raw_lower or "gemma-3-27b" in raw_lower:
            name = "Gemma 3 27B"
        elif "gemma3" in raw_lower or "gemma-3" in raw_lower:
            name = "Gemma 3 4B"
        elif "2-9b" in raw_lower or "9b" in raw_lower:
            name = "Gemma 2 9B"
        elif "2-27b" in raw_lower or "27b" in raw_lower:
            name = "Gemma 2 27B"
        elif "2-2b" in raw_lower or "2b" in raw_lower:
            name = "Gemma 2 2B"
        else:
            name = "Gemma"
        if "mlx" in raw_lower or provider == "mlx":
            name += " (MLX)"
        return name

    if "gemini" in raw_lower:
        # Parse version and variant from the model id (e.g. "gemini-2.5-pro" → "Gemini 2.5 Pro")
        import re as _re
        parts = _re.sub(r'^gemini-?', '', raw, flags=_re.IGNORECASE).replace('-', ' ').strip()
        return "Gemini " + " ".join(w.capitalize() if not w[0].isdigit() else w for w in parts.split() if w) if parts else "Gemini"

    clean = re.sub(
        r"[-_](q\d+[_a-z\d]*|f16|f32|it|instruct|chat)",
        "",
        raw,
        flags=re.IGNORECASE,
    )
    clean = clean.replace("-", " ").replace("_", " ").strip()
    clean = " ".join(
        word.capitalize() if not word.isupper() else word for word in clean.split()
    )
    if "mlx" in raw_lower or provider == "mlx":
        clean += " (MLX)"
    return clean[:28]


def is_valid_mlx_directory(dir_path: str) -> bool:
    """Check if directory contains a complete MLX model with valid configuration and weight files."""
    if not dir_path or not os.path.isdir(dir_path):
        return False
    if not os.path.exists(os.path.join(dir_path, "config.json")):
        return False
    if os.path.exists(os.path.join(dir_path, "model.safetensors")) or os.path.exists(
        os.path.join(dir_path, "weights.safetensors")
    ):
        return True
    idx_path = os.path.join(dir_path, "model.safetensors.index.json")
    if os.path.exists(idx_path):
        try:
            with open(idx_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            weight_map = data.get("weight_map", {})
            required_files = set(weight_map.values())
            if required_files and all(
                os.path.exists(os.path.join(dir_path, fname)) for fname in required_files
            ):
                return True
        except Exception:
            pass
        return False
    import glob

    safes = glob.glob(os.path.join(dir_path, "*.safetensors"))
    return len(safes) > 0


def list_available_models() -> list[dict[str, str]]:
    """Scan local models directory and returns available GGUF and MLX models."""
    models_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "models")
    )
    available = [
        {
            "name": "Gemma 4 E2B",
            "id": "gemma-4-E2B-it",
            "provider": "turbo",
        },
        {
            "name": "Gemma 4 E4B",
            "id": "gemma-4-E4B-it",
            "provider": "turbo",
        },
        {
            "name": "Qwen 2.5 Coder 3B",
            "id": "qwen2.5-coder-3b-instruct",
            "provider": "turbo",
        },
        {
            "name": "Qwen 2.5 Coder 7B",
            "id": "qwen2.5-coder-7b-instruct",
            "provider": "turbo",
        },
        {
            "name": "DeepSeek R1 Distill 1.5B (MLX)",
            "id": "mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit",
            "provider": "mlx",
        },
        {
            "name": "DeepSeek R1 Distill 7B (MLX)",
            "id": "mlx-community/DeepSeek-R1-Distill-Qwen-7B-4bit",
            "provider": "mlx",
        },
        {
            "name": "Gemma 4 E4B (MLX)",
            "id": "mlx-community/gemma-4-E4B-it-4bit",
            "provider": "mlx",
        },
        {
            "name": "Gemma 4 E2B (MLX)",
            "id": "mlx-community/gemma-4-E2B-it-4bit",
            "provider": "mlx",
        },
        {
            "name": "Gemma 2 2B (MLX)",
            "id": "mlx-community/gemma-2-2b-it-4bit",
            "provider": "mlx",
        },
        {
            "name": "Gemini 2.5 Flash",
            "id": "gemini-2.5-flash",
            "provider": "gemini",
        },
    ]
    if os.path.exists(models_dir):
        for fname in sorted(os.listdir(models_dir)):
            item_path = os.path.join(models_dir, fname)
            if fname.endswith(".gguf"):
                model_id = fname.replace(".gguf", "")
                display_name = format_model_display_name(fname, provider="turbo")
                if not any(m["id"] == model_id for m in available):
                    available.append(
                        {
                            "name": display_name,
                            "id": model_id,
                            "provider": "turbo",
                        }
                    )
            elif os.path.isdir(item_path) and is_valid_mlx_directory(item_path):
                display_name = format_model_display_name(fname, provider="mlx")
                if not any(m["id"] == fname or m["id"] == item_path for m in available):
                    available.append(
                        {
                            "name": display_name,
                            "id": fname,
                            "provider": "mlx",
                        }
                    )

    # Also scan Hugging Face cache for valid complete MLX models
    hf_hub = os.path.expanduser("~/.cache/huggingface/hub")
    if os.path.exists(hf_hub):
        try:
            for entry in sorted(os.listdir(hf_hub)):
                if entry.startswith("models--"):
                    clean_repo = entry.replace("models--", "").replace("--", "/")
                    clean_lower = clean_repo.lower()
                    if any(
                        skip in clean_lower
                        for skip in ("whisper", "sentence-transformers", "embedding", "rerank", "bge", "all-minilm")
                    ):
                        continue
                    snap_base = os.path.join(hf_hub, entry, "snapshots")
                    if os.path.exists(snap_base):
                        for snap in sorted(os.listdir(snap_base)):
                            snap_path = os.path.join(snap_base, snap)
                            if is_valid_mlx_directory(snap_path):
                                disp = format_model_display_name(clean_repo, provider="mlx")
                                if not any(m["id"] == clean_repo or m["id"] == snap_path for m in available):
                                    available.append(
                                        {
                                            "name": disp,
                                            "id": clean_repo,
                                            "provider": "mlx",
                                        }
                                    )
                                break
        except Exception:
            pass

    return available


def list_available_draft_models(target_model: str = "") -> list[dict[str, any]]:
    """Scan local models directory for potential speculative draft models.

    Returns a list of dictionaries with id, name, provider, and compatibility info.
    """
    models_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "models")
    )
    drafts = [
        {
            "name": "None (Disabled)",
            "id": "none",
            "provider": "turbo",
            "is_compatible": True,
        },
        {
            "name": "⚡ Auto-Match for Target",
            "id": "auto",
            "provider": "turbo",
            "is_compatible": True,
        },
    ]
    if os.path.exists(models_dir):
        for fname in sorted(os.listdir(models_dir)):
            if fname.endswith(".gguf"):
                model_id = fname.replace(".gguf", "")
                display_name = format_model_display_name(fname, provider="turbo")
                fname_lower = fname.lower()
                is_comp = True
                if target_model:
                    t_lower = target_model.lower()
                    if "qwen" in t_lower:
                        is_comp = "qwen" in fname_lower
                    elif "gemma" in t_lower:
                        is_comp = "gemma" in fname_lower
                    elif "llama" in t_lower:
                        is_comp = "llama" in fname_lower

                drafts.append(
                    {
                        "name": f"⚡ {display_name}",
                        "id": model_id,
                        "provider": "turbo",
                        "is_compatible": is_comp,
                    }
                )
    return drafts


def fetch_provider_models(base_url: str, timeout: float = 2.0) -> list[str]:
    """Query an OpenAI-compatible /models endpoint (LM Studio, Ollama, llama.cpp)
    or Ollama /api/tags and return the ids of whatever is currently loaded/available.

    Returns an empty list (never raises) if the provider is unreachable, so
    callers can treat a network failure the same as 'no models loaded'.
    """
    import json
    import urllib.request

    url = base_url.rstrip("/") + "/models"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            ids = [m.get("id", "") for m in body.get("data", []) if m.get("id")]
            if ids:
                return sorted(ids)
    except Exception:
        pass

    # If Ollama endpoint (port 11434), check /api/tags
    if "11434" in base_url or "ollama" in base_url.lower():
        try:
            root_url = base_url.split("/v1")[0].rstrip("/") + "/api/tags"
            req = urllib.request.Request(root_url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                ids = [
                    m.get("name", "")
                    for m in body.get("models", [])
                    if m.get("name")
                ]
                if ids:
                    return sorted(ids)
        except Exception:
            pass

    return []


def is_port_in_use(port: int = 8080) -> bool:
    """Check if server port 8080 is actively listening."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) == 0
