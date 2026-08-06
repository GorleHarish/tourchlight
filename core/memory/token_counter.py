"""
Token counting for Torchlight.

Uses tiktoken when available, falls back to a word-based heuristic.
"""

import re
from typing import Optional

try:
    import tiktoken
    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False


class TokenCounter:
    def __init__(self, model: str = "cl100k_base"):
        self.model = model
        self._encoder: Optional[object] = None
        if _HAS_TIKTOKEN:
            try:
                self._encoder = tiktoken.get_encoding(model)
            except Exception:
                self._encoder = None

    def count(self, text: str) -> int:
        if not text:
            return 0
        if self._encoder:
            return len(self._encoder.encode(text))
        return self._estimate(text)

    def _estimate(self, text: str) -> int:
        if not text:
            return 0
        cjk = len(re.findall(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", text))
        words = len(re.findall(r"\b\w+\b", text))
        operators = len(re.findall(r"[{}()\[\]<>!=+\-*/&|^~%@;:,.]", text))
        newlines = text.count("\n")
        return int((words + cjk + operators + (newlines // 2)) * 1.1)

    def truncate(self, text: str, max_tokens: int) -> str:
        if not text:
            return ""
        if self.count(text) <= max_tokens:
            return text
        if self._encoder:
            tokens = self._encoder.encode(text)
            truncated = self._encoder.decode(tokens[:max_tokens])
            return truncated
        words = text.split()
        lo, hi = 0, len(words)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.count(" ".join(words[:mid])) <= max_tokens:
                lo = mid
            else:
                hi = mid - 1
        return " ".join(words[:lo])


_counters: dict[str, "TokenCounter"] = {}


def get_token_counter(model: str = "cl100k_base") -> TokenCounter:
    global _counters
    if model not in _counters:
        _counters[model] = TokenCounter(model)
    return _counters[model]
