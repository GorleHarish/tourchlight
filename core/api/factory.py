"""
LLM client factory for Torchlight.

Creates the appropriate client based on provider configuration.
Supports LM Studio, llama.cpp, Ollama, and cloud APIs.
"""

import os
from typing import Optional

from .base import LLMClient


def create_client(
    provider: str = "lmstudio",
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs,
) -> LLMClient:
    """
    Create an LLM client for the given provider.

    Supported providers:
        - "lmstudio": LM Studio (default, localhost:1234)
        - "llamacpp": llama.cpp server
        - "ollama": Ollama
        - "groq": Groq cloud API
        - "together": Together AI
        - "openrouter": OpenRouter
        - "openai": OpenAI
        - "gemini": Google Gemini
        - "cloud": Generic cloud API (uses base_url/api_key)

    Returns:
        LLMClient instance
    """
    provider = provider.lower().strip()

    if provider == "lmstudio":
        return _create_lmstudio_client(base_url, model)
    elif provider == "llamacpp":
        return _create_llamacpp_client(base_url, model)
    elif provider == "ollama":
        return _create_ollama_client(model)
    elif provider in ("groq", "together", "openrouter", "openai", "gemini"):
        return _create_cloud_client(provider, model, api_key)
    elif provider == "cloud":
        return _create_cloud_client(None, model, api_key, base_url=base_url)
    else:
        raise ValueError(
            f"Unknown provider: '{provider}'. "
            f"Supported: lmstudio, llamacpp, ollama, groq, together, openrouter, openai, gemini, cloud"
        )


def _create_lmstudio_client(base_url: Optional[str], model: Optional[str]) -> LLMClient:
    """Create LM Studio client (OpenAI-compatible API)."""
    try:
        from .lmstudio import LMStudioClient

        return LMStudioClient(
            base_url=base_url or "http://localhost:1234/v1",
            model=model,
        )
    except ImportError:
        # Fallback: use the httpx-based implementation
        return _HttpxLMStudioClient(
            base_url=base_url or "http://localhost:1234/v1",
            model=model,
        )


def _create_llamacpp_client(base_url: Optional[str], model: Optional[str]) -> LLMClient:
    """Create llama.cpp server client."""
    try:
        from rlm_optimized.llamacpp_client import LlamaCppClient

        return LlamaCppClient(
            base_url=base_url or "http://localhost:8080/v1",
            model=model or "default",
        )
    except ImportError:
        return _HttpxLMStudioClient(
            base_url=base_url or "http://localhost:8080/v1",
            model=model,
        )


def _create_ollama_client(model: Optional[str]) -> LLMClient:
    """Create Ollama client."""
    try:
        from rlm_optimized.ollama_client import OllamaClient

        return OllamaClient(model=model or "llama3.2")
    except ImportError:
        raise ImportError(
            "Ollama client requires the 'ollama' package. "
            "Install with: pip install ollama"
        )


def _create_cloud_client(
    provider: Optional[str],
    model: Optional[str],
    api_key: Optional[str],
    base_url: Optional[str] = None,
) -> LLMClient:
    """Create cloud API client (OpenAI-compatible)."""
    try:
        from rlm_optimized.cloud_client import CloudClient

        return CloudClient(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
        )
    except ImportError:
        raise ImportError(
            "Cloud client requires the 'openai' package. "
            "Install with: pip install openai"
        )


# ── Fallback httpx client ─────────────────────────────────────────────────


class _HttpxLMStudioClient:
    """
    Minimal httpx-based LM Studio client.
    Used when context_manager.api.lmstudio is not available.
    """

    def __init__(
        self, base_url: str = "http://localhost:1234/v1", model: Optional[str] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat(self, messages, params=None):
        import httpx

        payload = {"model": self.model or "", "messages": messages}
        if params:
            payload.update(params.to_payload())
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(f"{self.base_url}/chat/completions", json=payload)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    async def chat_stream(self, messages, params=None):
        import httpx

        payload = {"model": self.model or "", "messages": messages, "stream": True}
        if params:
            payload.update(params.to_payload())
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST", f"{self.base_url}/chat/completions", json=payload
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        import json

                        chunk = json.loads(line[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content

    async def health_check(self):
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base_url}/models")
                return r.status_code == 200
        except Exception:
            return False

    async def list_models(self):
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base_url}/models")
                r.raise_for_status()
                return [m["id"] for m in r.json().get("data", [])]
        except Exception:
            return []

    def query(self, prompt, system_prompt="", **kwargs):
        import httpx

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model or "", "messages": messages}
        with httpx.Client(timeout=300) as client:
            r = client.post(f"{self.base_url}/chat/completions", json=payload)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
