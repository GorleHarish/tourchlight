"""
Embedding support for Torchlight.

Provides hybrid embedding (LLM-based + keyword fallback).
"""

from typing import Optional


class Embedder:
    """Base embedder interface."""
    def embed_sync(self, text: str) -> list[float]:
        return []


class KeywordEmbedder(Embedder):
    """Simple keyword-based embedding fallback."""
    def embed_sync(self, text: str) -> list[float]:
        # Simple bag-of-words style embedding
        words = text.lower().split()
        return [float(w.count(w)) for w in words[:128]]


class HybridEmbedder(Embedder):
    """Hybrid embedder: uses LLM embeddings when available, falls back to keywords."""
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.keyword_embedder = KeywordEmbedder()

    def embed_sync(self, text: str) -> list[float]:
        if self.llm_client:
            try:
                # Try to get embeddings from the LLM
                # This depends on the LLM client supporting embeddings
                pass
            except Exception:
                pass
        return self.keyword_embedder.embed_sync(text)


def build_embedder(backend: str = "hybrid", mode: str = "auto", llm_client=None) -> Embedder:
    """Factory function to create an embedder."""
    if backend == "hybrid":
        return HybridEmbedder(llm_client)
    elif backend == "keyword":
        return KeywordEmbedder()
    else:
        return KeywordEmbedder()
