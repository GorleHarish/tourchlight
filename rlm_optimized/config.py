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
USE_GRAMMAR_CONSTRAINT = os.environ.get("RLM_USE_GRAMMAR", "false").lower() in (
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

# ── Generation Parameters ──────────────────────────────────────
TEMPERATURE = 0.7
TOP_P = 0.9
NUM_PREDICT = int(
    os.environ.get("RLM_NUM_PREDICT", "-1")
)  # -1 = unlimited (generate until stop token)


def estimate_metadata_overhead(
    system_content: str = "", ctx_size: int = CTX_SIZE
) -> int:
    """Estimate tokens consumed by system prompt, tool schemas, and the flashlight beam.

    Mirrors the CLI's `_calculate_metadata_overhead`: base system-prompt cost plus a
    beam allowance scaled to the context window. Fed into `MemoryConfig.auto_tune` so
    the history budget is net of prompt-assembly overhead and the assembled prompt
    always stays inside the model's context window.
    """
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
    """Normalize model alias names (e.g. 'gemma-2-2b', 'qwen', 'gemma 4 E2B', 'gemma 4 4e4b')."""
    if not name:
        return name
    name_str = str(name).strip()
    provider_clean = (provider or "").lower().strip()
    if provider_clean in ("lmstudio", "ollama") or name_str.startswith("lmstudio"):
        return name_str

    name_lower = (
        name_str.lower().replace(" ", "").replace("-", "").replace("_", "").replace(":", "")
    )
    if provider_clean == "mlx" or "mlx" in name_lower:
        if "qwen" in name_lower or name_lower == "qwen2.5coder":
            if "1.5b" in name_lower or "15b" in name_lower:
                return "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
            elif "3b" in name_lower:
                return "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"
            return "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
        if "gemma" in name_lower:
            if "4e4b" in name_lower or "4e4" in name_lower or "e4b" in name_lower:
                return "mlx-community/gemma-4-E4B-it-4bit"
            if "4e2b" in name_lower or "4e2" in name_lower or "gemma4" in name_lower:
                return "mlx-community/gemma-4-E2B-it-4bit"
            return "mlx-community/gemma-2-2b-it-4bit"
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
    if "gemma4e2b" in name_lower or "gemma4" in name_lower or "gemma4e2" in name_lower:
        return "gemma-4-E2B-it"
    if "gemma2" in name_lower:
        return "gemma-2-2b-it"
    elif name_lower in ("gemma34b", "gemma3"):
        return "gemma3:4b"
    return name_str


def list_available_models() -> list[dict[str, str]]:
    """Scan local models directory and returns available GGUF and MLX models."""
    models_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "models")
    )
    available = [
        {
            "name": "Gemma 4 E2B Instruct (2B TurboQuant)",
            "id": "gemma-4-E2B-it",
            "provider": "turbo",
        },
        {
            "name": "Gemma 4 E4B Instruct (4B TurboQuant)",
            "id": "gemma-4-E4B-it",
            "provider": "turbo",
        },
        {
            "name": "Gemma 4 E4B Instruct (MLX Metal)",
            "id": "mlx-community/gemma-4-E4B-it-4bit",
            "provider": "mlx",
        },
        {
            "name": "Gemma 2 2B Instruct (MLX Metal)",
            "id": "mlx-community/gemma-2-2b-it-4bit",
            "provider": "mlx",
        },
        {
            "name": "Qwen 2.5 Coder 7B (TurboQuant)",
            "id": "qwen2.5-coder-7b-instruct",
            "provider": "turbo",
        },
        {
            "name": "Gemini 2.5 Flash (Cloud API)",
            "id": "gemini-2.5-flash",
            "provider": "gemini",
        },
    ]
    if os.path.exists(models_dir):
        for fname in os.listdir(models_dir):
            if fname.endswith(".gguf"):
                model_id = fname.replace(".gguf", "")
                if not any(m["id"] == model_id for m in available):
                    available.append(
                        {
                            "name": f"Local GGUF: {fname}",
                            "id": model_id,
                            "provider": "turbo",
                        }
                    )
    return available


def fetch_provider_models(base_url: str, timeout: float = 2.5) -> list[str]:
    """Query an OpenAI-compatible /models endpoint (LM Studio, Ollama, llama.cpp)
    and return the ids of whatever is currently loaded/available.

    Returns an empty list (never raises) if the provider is unreachable, so
    callers can treat a network failure the same as "no models loaded".
    """
    import json
    import urllib.request

    url = base_url.rstrip("/") + "/models"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            ids = [m.get("id", "") for m in body.get("data", []) if m.get("id")]
            return sorted(ids)
    except Exception:
        return []


def is_port_in_use(port: int = 8080) -> bool:
    """Check if server port 8080 is actively listening."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) == 0
