from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Optional, Protocol


class Embedder(Protocol):
    def embed_sync(self, text: str) -> list[float]:
        ...


def _normalize(v: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in v))
    if not norm:
        return v
    return [x / norm for x in v]


def _tokenize(text: str) -> list[str]:
    return [tok for tok in re.findall(r"[A-Za-z0-9_./:-]+", (text or "").lower()) if len(tok) > 1]


@dataclass
class HashEmbedder:
    dims: int = 192

    def embed_sync(self, text: str) -> list[float]:
        vec = [0.0] * self.dims
        for token in _tokenize(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dims
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        return _normalize(vec)


@dataclass
class ProviderEmbedder:
    client: any

    def embed_sync(self, text: str) -> list[float]:
        return self.client.embeddings_sync(text)


@dataclass
class FallbackEmbedder:
    primary: Embedder
    fallback: Embedder

    def embed_sync(self, text: str) -> list[float]:
        try:
            return self.primary.embed_sync(text)
        except Exception:
            return self.fallback.embed_sync(text)


def build_embedder(
    backend: str = "hybrid",
    execution_policy: str = "auto",
    llm_client: Optional[any] = None,
) -> Embedder:
    backend = (backend or "hybrid").lower()
    execution_policy = (execution_policy or "auto").lower()

    cpu_embedder = HashEmbedder()
    if execution_policy == "cpu_only":
        return cpu_embedder

    if backend in ("lexical", "hash", "cpu"):
        return cpu_embedder

    if llm_client is None:
        return cpu_embedder

    provider_embedder = ProviderEmbedder(llm_client)
    if backend in ("provider", "remote"):
        return provider_embedder

    # Default: provider-preferred with cheap CPU fallback
    return FallbackEmbedder(primary=provider_embedder, fallback=cpu_embedder)
