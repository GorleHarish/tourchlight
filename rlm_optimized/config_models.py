"""Model name normalization, display label formatting, and multi-provider model discovery."""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


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
    models_candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models")),
        os.path.abspath(os.path.join(os.getcwd(), "models")),
    ]
    models_dir = next((d for d in models_candidates if os.path.exists(d)), models_candidates[0])
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
    models_candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models")),
        os.path.abspath(os.path.join(os.getcwd(), "models")),
    ]
    models_dir = next((d for d in models_candidates if os.path.exists(d)), models_candidates[0])
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


_PROVIDER_CACHE: dict[str, tuple[float, list[str]]] = {}


def fetch_provider_models(base_url: str, timeout: float = 0.4) -> list[str]:
    """Query an OpenAI-compatible /models endpoint (LM Studio, Ollama, llama.cpp)
    or Ollama /api/tags and return the ids of whatever is currently loaded/available.

    Returns cached results if queried within the last 5.0s, and returns an empty list
    (never raises) if unreachable.
    """
    import json
    import time
    import urllib.request

    now = time.monotonic()
    if base_url in _PROVIDER_CACHE:
        cached_ts, cached_ids = _PROVIDER_CACHE[base_url]
        if now - cached_ts < 5.0:
            return cached_ids

    url = base_url.rstrip("/") + "/models"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            ids = [m.get("id", "") for m in body.get("data", []) if m.get("id")]
            if ids:
                res = sorted(ids)
                _PROVIDER_CACHE[base_url] = (now, res)
                return res
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
                    res = sorted(ids)
                    _PROVIDER_CACHE[base_url] = (now, res)
                    return res
        except Exception:
            pass

    _PROVIDER_CACHE[base_url] = (now, [])
    return []
