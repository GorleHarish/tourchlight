"""
Hybrid Embedding & Vector Retrieval Engine for Torchlight.

Provides BM25/TF-IDF keyword vectors, dense vector cosine similarity,
AST symbol scoring, and multi-channel hybrid memory retrieval.
"""

import math
import re
from datetime import datetime
from typing import Optional, Union
from .models import MemoryObject, MemoryNeedle


def tokenize_text(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric words for TF-IDF / BM25 index."""
    if not text:
        return []
    return re.findall(r"\b[a-zA-Z0-9_]{2,}\b", text.lower())


def compute_tf_idf_score(query_tokens: list[str], target_tokens: list[str]) -> float:
    """Compute BM25 / TF-IDF similarity score between query tokens and target tokens."""
    if not query_tokens or not target_tokens:
        return 0.0

    target_counts = {}
    for t in target_tokens:
        target_counts[t] = target_counts.get(t, 0) + 1

    doc_len = len(target_tokens)
    k1 = 1.2
    b = 0.75
    avg_len = 50.0  # reference average memory summary token length

    score = 0.0
    for qt in query_tokens:
        tf = target_counts.get(qt, 0)
        if tf > 0:
            # BM25 term frequency saturation
            tf_score = (tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * (doc_len / avg_len)))
            score += tf_score

    return min(1.0, score / max(1.0, len(query_tokens)))


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two float vector embeddings."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))


class Embedder:
    """Base embedder interface."""
    def embed_sync(self, text: str) -> list[float]:
        return []


class KeywordEmbedder(Embedder):
    """Simple term-frequency vector embedding."""
    def embed_sync(self, text: str) -> list[float]:
        words = tokenize_text(text)
        if not words:
            return [0.0] * 32
        freqs = {}
        for w in words:
            freqs[w] = freqs.get(w, 0) + 1
        # Produce a normalized 32-dim hash vector
        vec = [0.0] * 32
        for w, count in freqs.items():
            idx = abs(hash(w)) % 32
            vec[idx] += float(count)
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


import os


def _is_low_memory() -> bool:
    """Return True on machines with <= 8GB RAM or when TORCHLIGHT_FORCE_KEYWORD_EMBEDDINGS is set."""
    if os.environ.get("TORCHLIGHT_FORCE_KEYWORD_EMBEDDINGS"):
        return True
    try:
        import psutil
        return psutil.virtual_memory().total <= 8 * 1024**3
    except ImportError:
        try:
            mem = int(os.popen("sysctl -n hw.memsize").read().strip())
            return mem <= 8 * 1024**3
        except Exception:
            return False


class HybridEmbedder(Embedder):
    """Hybrid embedder: uses LLM embeddings when available, falls back to keyword vectors."""
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.keyword_embedder = KeywordEmbedder()

    def embed_sync(self, text: str) -> list[float]:
        if _is_low_memory():
            return self.keyword_embedder.embed_sync(text)
        if self.llm_client and hasattr(self.llm_client, "get_embeddings"):
            try:
                emb = self.llm_client.get_embeddings(text)
                if isinstance(emb, list) and emb:
                    return emb
            except Exception:
                pass
        return self.keyword_embedder.embed_sync(text)


class HybridMemoryRetriever:
    """Hybrid Memory Retrieval Engine.

    Ranks MemoryObject items combining BM25/TF-IDF token matching, dense embedding
    cosine similarity, AST symbol relevance, and recency time-decay.
    Supports channel-aware filtering (`channel_id`).
    """

    def __init__(self, embedder: Optional[Embedder] = None):
        self.embedder = embedder or KeywordEmbedder()

    def score_memory_object(
        self,
        query: str,
        query_tokens: list[str],
        query_vec: list[float],
        mem: MemoryObject,
        current_time: Optional[datetime] = None,
    ) -> float:
        """Score a single MemoryObject against a query."""
        current_time = current_time or datetime.now()

        # 1. TF-IDF / BM25 term overlap score
        target_text = f"{mem.summary} {mem.text} {' '.join(mem.file_paths)} {' '.join(mem.symbols)} {' '.join(mem.errors)}"
        target_tokens = mem.vector_tokens or tokenize_text(target_text)
        tfidf_score = compute_tf_idf_score(query_tokens, target_tokens)

        # 2. Embedding Cosine Similarity score
        vec_score = 0.0
        if mem.embedding and query_vec:
            vec_score = cosine_similarity(query_vec, mem.embedding)

        # 3. AST / Symbol relevance score
        symbol_score = 0.0
        if mem.ast_symbols or mem.symbols:
            mem_syms = set(mem.ast_symbols + mem.symbols)
            for q_tok in query_tokens:
                if any(q_tok in sym.lower() for sym in mem_syms):
                    symbol_score = 1.0
                    break

        # 4. Recency decay score (half-life of ~7 days = 604,800s)
        recency_score = 1.0
        if mem.timestamp:
            try:
                age_seconds = max(0.0, (current_time - mem.timestamp).total_seconds())
                recency_score = math.exp(-age_seconds / 604800.0)
            except Exception:
                recency_score = 1.0

        # Weighted combination: 0.4 TFIDF + 0.3 Dense Vector + 0.15 AST Symbol + 0.15 Recency
        final_score = (
            (0.40 * tfidf_score)
            + (0.30 * vec_score)
            + (0.15 * symbol_score)
            + (0.15 * recency_score)
        )
        return final_score

    def retrieve(
        self,
        query: str,
        memories: list[MemoryObject],
        channel_id: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.15,
    ) -> list[tuple[MemoryObject, float]]:
        """Retrieve and rank the top_k relevant MemoryObject items matching the query."""
        if not memories or not query.strip():
            return []

        query_tokens = tokenize_text(query)
        query_vec = self.embedder.embed_sync(query)
        now = datetime.now()

        scored_items = []
        for mem in memories:
            # Channel filter: match exact channel_id, or allow if channel_id is None or "default"
            if channel_id and mem.channel_id and mem.channel_id not in ("default", channel_id):
                continue

            score = self.score_memory_object(query, query_tokens, query_vec, mem, current_time=now)
            if score >= min_score:
                scored_items.append((mem, score))

        scored_items.sort(key=lambda item: item[1], reverse=True)
        return scored_items[:top_k]


def build_embedder(backend: str = "hybrid", mode: str = "auto", llm_client=None) -> Embedder:
    """Factory function to create an embedder."""
    if backend == "hybrid":
        return HybridEmbedder(llm_client)
    elif backend == "keyword":
        return KeywordEmbedder()
    else:
        return KeywordEmbedder()
