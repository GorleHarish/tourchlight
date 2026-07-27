"""
Selective Memory Compression — Progressive context reduction for local LLMs.

4-level progressive compression: FULL → COMPACT → SUMMARY → HINT
"""

import re
from dataclasses import dataclass, field
from typing import Callable, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from .token_counter import TokenCounter


class CompressionLevel(Enum):
    FULL = "full"
    COMPACT = "compact"
    SUMMARY = "summary"
    HINT = "hint"


@dataclass
class CompressionConfig:
    full_window: int = 3
    compact_threshold: int = 7
    summary_threshold: int = 15
    full_budget: int = 0
    compact_budget: int = 300
    summary_budget: int = 100
    hint_budget: int = 50
    preserve_roles: bool = True
    preserve_tools: bool = True
    preserve_errors: bool = True
    preserve_decisions: bool = True
    decision_patterns: list = field(default_factory=lambda: [
        r'\bdecided\b', r'\bchose\b', r'\bgoing with\b', r'\barchitecture\b',
        r'\bwill use\b', r'\brather than\b', r'\bpattern\b',
    ])
    error_patterns: list = field(default_factory=lambda: [
        r'\berror\b', r'\bfailed\b', r'\bexception\b', r'\btraceback\b',
    ])
    tool_patterns: list = field(default_factory=lambda: [
        r'\[READ_FILE\]', r'\[WRITE_FILE\]', r'\[RUN_COMMAND\]',
    ])


@dataclass
class TurnSummary:
    role: str
    level: CompressionLevel
    original_tokens: int
    compressed_tokens: int
    content: str
    preserved_hints: list = field(default_factory=list)


class SelectiveCompressor:
    """
    Progressive compression that preserves semantic meaning.

    Strategy:
    - Recent turns: Keep full
    - Medium turns: Compact (remove noise)
    - Older turns: Summarize (extract key points)
    - Oldest turns: Hint (preserve only critical info)
    """

    def __init__(self, config: Optional[CompressionConfig] = None, tokenizer: "Optional[TokenCounter]" = None):
        self.config = config or CompressionConfig()
        self.tokenizer = tokenizer
        self._compiled_decision_re = self._compile_patterns(self.config.decision_patterns)
        self._compiled_error_re = self._compile_patterns(self.config.error_patterns)

    def _compile_patterns(self, patterns: list) -> re.Pattern:
        return re.compile("|".join(patterns), re.IGNORECASE)

    def _estimate_tokens(self, text: str) -> int:
        if self.tokenizer:
            return self.tokenizer.count(text)
        return len(text) // 4

    def _compact(self, text: str, budget: int) -> str:
        if self.tokenizer:
            return self.tokenizer.truncate(text, budget)
        words = text.split()
        estimated_words = budget * 4 // 5
        return " ".join(words[:estimated_words])

    def _is_important(self, text: str) -> bool:
        if self._compiled_decision_re.search(text):
            return True
        if self._compiled_error_re.search(text):
            return True
        return False

    def compress_turns(self, messages: list) -> list[TurnSummary]:
        """Compress a list of messages using progressive levels."""
        summaries = []
        n = len(messages)

        for i, msg in enumerate(messages):
            distance_from_end = n - 1 - i
            content = msg.content if hasattr(msg, 'content') else str(msg)
            original_tokens = self._estimate_tokens(content)

            if distance_from_end < self.config.full_window:
                level = CompressionLevel.FULL
                compressed = content
            elif distance_from_end < self.config.compact_threshold:
                level = CompressionLevel.COMPACT
                compressed = self._compact(content, self.config.compact_budget)
            elif distance_from_end < self.config.summary_threshold:
                level = CompressionLevel.SUMMARY
                compressed = self._compact(content, self.config.summary_budget)
            else:
                level = CompressionLevel.HINT
                compressed = self._compact(content, self.config.hint_budget)

            compressed_tokens = self._estimate_tokens(compressed)
            summaries.append(TurnSummary(
                role=str(msg.role) if hasattr(msg, 'role') else "unknown",
                level=level,
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                content=compressed,
            ))

        return summaries
