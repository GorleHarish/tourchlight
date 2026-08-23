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

    def count_image(self, image_input: Optional[object] = None) -> int:
        """
        Estimate token consumption for an image input (~600-800 tokens for standard 1024x1024 / tile).
        Calibrated for Gemma 3, Qwen VL, Llama 3.2 Vision, and GPT-4o.
        """
        if image_input == "":
            return 0
        return 640

    def count_message(self, message: object) -> int:
        """Count total tokens in a Message object including text and attached images."""
        if not message:
            return 0
        text = getattr(message, "content", "")
        if isinstance(text, list):
            tot = 0
            for part in text:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        tot += self.count(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        tot += self.count_image(part.get("image_url"))
            return tot

        tot = self.count(str(text))
        images = getattr(message, "images", None)
        if images:
            for img in images:
                tot += self.count_image(img)
        return tot


_counters: dict[str, "TokenCounter"] = {}


def get_token_counter(model: str = "cl100k_base") -> TokenCounter:
    global _counters
    if model not in _counters:
        _counters[model] = TokenCounter(model)
    return _counters[model]
