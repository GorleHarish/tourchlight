"""
Selective Memory Compression - Progressive context reduction for local LLMs.

FIX 1: _estimate_tokens() now uses the real TokenCounter instead of len//4.
FIX 2: _compact() now uses tokenizer.truncate() so compact_budget means TOKENS,
        not characters (the previous char-slice was silently 4× too aggressive).
FIX 3: Tokenizer is injected at construction and threaded through all helpers.
"""

import re
from dataclasses import dataclass, field
from typing import Callable, Optional, TYPE_CHECKING
from enum import Enum

from core.memory.manager import is_valid_file_path

if TYPE_CHECKING:
    from .token_counter import TokenCounter


class CompressionLevel(Enum):
    FULL    = "full"     # No compression
    COMPACT = "compact"  # Remove whitespace, shorten
    SUMMARY = "summary"  # Single-line summary
    HINT    = "hint"     # One-liner preserving key info


@dataclass
class CompressionConfig:
    """Configuration for selective memory compression."""
    # Turn thresholds (number of messages)
    full_window:        int = 3   # Keep these fully
    compact_threshold:  int = 7   # Compact after this many turns from the end
    summary_threshold:  int = 15  # Summarize after this many turns from the end

    # Token budgets per level  ← now truly in TOKENS (was silently chars before)
    full_budget:    int = 0    # 0 = unlimited
    compact_budget: int = 300  # tokens per message
    summary_budget: int = 100  # tokens per message
    hint_budget:    int = 50   # tokens per message

    # What to preserve at each level
    preserve_roles:     bool = True
    preserve_tools:     bool = True
    preserve_errors:    bool = True
    preserve_decisions: bool = True

    # Pattern matchers for important content
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
    """Summary of a conversation turn."""
    role:              str
    level:             CompressionLevel
    original_tokens:   int
    compressed_tokens: int
    content:           str
    preserved_hints:   list = field(default_factory=list)


class SelectiveCompressor:
    """
    Progressive compression that preserves semantic meaning.

    Strategy:
    - Recent turns  : Keep full
    - Medium turns  : Compact (remove noise) — token-truncated to compact_budget
    - Older turns   : Summarize (extract key points)
    - Oldest turns  : Hint (preserve only critical info)

    IMPORTANT: pass a real TokenCounter so budget enforcement uses the same
    counting as the rest of the system.  Falls back to the old char//4 heuristic
    only when no tokenizer is supplied.
    """

    def __init__(
        self,
        config: Optional[CompressionConfig] = None,
        tokenizer: "Optional[TokenCounter]" = None,
    ):
        self.config    = config or CompressionConfig()
        self.tokenizer = tokenizer  # may be None → falls back to _char_estimate

        self._compiled_decision_re = self._compile_patterns(self.config.decision_patterns)
        self._compiled_error_re    = self._compile_patterns(self.config.error_patterns)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _compile_patterns(self, patterns: list) -> re.Pattern:
        return re.compile("|".join(patterns), re.IGNORECASE)

    def _count_tokens(self, text: str) -> int:
        """FIX 1 & 3: use injected tokenizer; only fall back to heuristic if absent."""
        if self.tokenizer is not None:
            return self.tokenizer.count(text)
        return self._char_estimate(text)

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """FIX 2: token-aware truncation instead of character slicing."""
        if self.tokenizer is not None:
            return self.tokenizer.truncate(text, max_tokens)
        # Fallback: estimate ~4 chars/token
        return text[: max_tokens * 4]

    @staticmethod
    def _char_estimate(text: str) -> int:
        """Legacy heuristic — only used when no tokenizer is injected."""
        return len(text) // 4

    # ── compression level ────────────────────────────────────────────────────

    def get_compression_level(self, turn_index: int, total_turns: int) -> CompressionLevel:
        """Determine compression level based on turn position from the end."""
        turns_from_end = total_turns - 1 - turn_index
        if turns_from_end < self.config.full_window:
            return CompressionLevel.FULL
        elif turns_from_end < self.config.compact_threshold:
            return CompressionLevel.COMPACT
        elif turns_from_end < self.config.summary_threshold:
            return CompressionLevel.SUMMARY
        else:
            return CompressionLevel.HINT

    # ── per-turn compression ─────────────────────────────────────────────────

    def compress_turn(
        self, role: str, content: str, level: CompressionLevel
    ) -> TurnSummary:
        original_tokens = self._count_tokens(content)

        if level == CompressionLevel.FULL:
            return TurnSummary(
                role=role, level=level,
                original_tokens=original_tokens, compressed_tokens=original_tokens,
                content=content,
            )
        elif level == CompressionLevel.COMPACT:
            compressed = self._compact(content)
            return TurnSummary(
                role=role, level=level,
                original_tokens=original_tokens,
                compressed_tokens=self._count_tokens(compressed),
                content=compressed,
            )
        elif level == CompressionLevel.SUMMARY:
            summary = self._summarize(content, role)
            return TurnSummary(
                role=role, level=level,
                original_tokens=original_tokens,
                compressed_tokens=self._count_tokens(summary),
                content=summary,
                preserved_hints=self._extract_hints(content),
            )
        else:  # HINT
            hint = self._extract_hint(content, role)
            return TurnSummary(
                role=role, level=level,
                original_tokens=original_tokens,
                compressed_tokens=self._count_tokens(hint),
                content=hint,
                preserved_hints=self._extract_hints(content),
            )

    # ── content transforms ───────────────────────────────────────────────────

    def _compact(self, content: str) -> str:
        """
        FIX 2: Remove whitespace/noise then TOKEN-TRUNCATE to compact_budget.

        The original code did `' '.join(compacted)[:self.config.compact_budget]`
        which sliced by characters.  With compact_budget=200 that gives only
        ~50 tokens instead of 200.  We now call _truncate_to_tokens().
        """
        lines = content.split("\n")
        compacted_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            line = re.sub(r"^>>> \d+:\s*", "", line)   # strip grep line numbers
            line = re.sub(r"^---\s*", "",     line)    # strip markdown separators
            compacted_lines.append(line)

        joined = " ".join(compacted_lines)
        # ← FIX: token-aware truncation, not character slice
        return self._truncate_to_tokens(joined, self.config.compact_budget)

    def _summarize(self, content: str, role: str) -> str:
        hints      = self._extract_hints(content)
        role_label = {"user": "User", "assistant": "Agent", "tool": "Tool"}.get(
            role.lower(), role
        )
        base = f"[{role_label}] "

        if hints:
            hint_text = " | ".join(hints[:3])
            full      = base + hint_text
        else:
            sentences = re.split(r"[.!?]", content)
            first     = sentences[0].strip() if sentences else ""
            full      = base + first

        return self._truncate_to_tokens(full, self.config.summary_budget)

    def _extract_hint(self, content: str, role: str) -> str:
        role_label = {"user": "User", "assistant": "Agent", "tool": "Tool"}.get(
            role.lower(), role
        )
        base   = f"[{role_label}] "
        hints  = self._extract_hints(content)

        if hints:
            full = base + hints[0]
        else:
            compacted = self._compact(content)
            full      = base + compacted

        return self._truncate_to_tokens(full, self.config.hint_budget)

    def _extract_hints(self, content: str) -> list:
        hints = []

        # Decision hints
        if self._compiled_decision_re.search(content):
            m = self._compiled_decision_re.search(content)
            hints.append(f"decision: {m.group(0)[:30]}")

        # Error hints
        if self._compiled_error_re.search(content):
            m     = self._compiled_error_re.search(content)
            start = max(0, m.start() - 5)
            end   = min(len(content), m.end() + 60)
            ctx   = content[start:end].replace("\n", " ").strip()
            hints.append(f"ERROR: {ctx[:50]}")

        # Test results
        passed = len(re.findall(r"\bpassed\b|\bok\b",   content, re.IGNORECASE))
        failed = len(re.findall(r"\bfailed\b",           content, re.IGNORECASE))
        if passed or failed:
            hints.append(f"tests: {passed}✓ {failed}✗")

        # File paths
        raw_paths = re.findall(r"[\w\-/]+\.[a-zA-Z]{2,6}(?::\d+)?", content)
        paths = [p for p in raw_paths if is_valid_file_path(p.split(":")[0])]
        if paths:
            hints.append(f"files: {', '.join(paths[:2])}")

        # Commands
        cmds = re.findall(
            r"(?:pytest|python|npm|git|node)\s+[^\n]{1,40}", content
        )
        if cmds:
            hints.append(f"cmd: {cmds[0][:40]}")

        return hints[:3]

    # ── conversation-level helpers ───────────────────────────────────────────

    def compress_conversation(self, messages: list) -> list[TurnSummary]:
        """
        Compress a list of message dicts with progressive levels.

        Args:
            messages: list of {"role": str, "content": str}

        Returns:
            list of TurnSummary objects, one per message.
        """
        total      = len(messages)
        compressed = []
        for i, msg in enumerate(messages):
            level = self.get_compression_level(i, total)
            turn  = self.compress_turn(
                msg.get("role", "assistant"),
                msg.get("content", ""),
                level,
            )
            compressed.append(turn)
        return compressed

    def build_compressed_context(self, messages: list, max_tokens: int) -> str:
        """
        Build a compressed context string within token budget.

        Uses the real token counter (FIX 1) so the budget check is accurate.

        Args:
            messages:   list of {"role": str, "content": str}
            max_tokens: maximum tokens allowed

        Returns:
            Compressed context string with level markers.
        """
        compressed   = self.compress_conversation(messages)
        lines: list  = []
        total_tokens = 0
        skipped      = 0

        for turn in reversed(compressed):
            tokens = turn.compressed_tokens  # now accurate (FIX 1)
            if total_tokens + tokens > max_tokens:
                skipped += 1
                continue

            if turn.level == CompressionLevel.COMPACT:
                marker = "[c] "
            elif turn.level == CompressionLevel.SUMMARY:
                marker = "[s] "
            elif turn.level == CompressionLevel.HINT:
                marker = "[h] "
            else:
                marker = ""

            if turn.level in (CompressionLevel.HINT, CompressionLevel.SUMMARY):
                # content already contains the role prefix
                lines.insert(0, f"{marker}{turn.content}")
            else:
                lines.insert(0, f"{marker}[{turn.role}] {turn.content}")

            total_tokens += tokens

        if skipped > 0:
            lines.insert(0, f"... {skipped} earlier turns omitted ...")

        return "\n".join(lines)


# ── factory ──────────────────────────────────────────────────────────────────

def create_progressive_compressor(
    ctx_window: int,
    tokenizer: "Optional[TokenCounter]" = None,  # FIX 3: thread real tokenizer in
) -> SelectiveCompressor:
    """Create a compressor tuned for the given context window.

    Always pass the shared TokenCounter so budget maths are consistent across
    the whole system.
    """
    if ctx_window <= 4000:
        cfg = CompressionConfig(
            full_window=2, compact_threshold=5, summary_threshold=10,
            compact_budget=200, summary_budget=80, hint_budget=40,
        )
    elif ctx_window <= 8000:
        cfg = CompressionConfig(
            full_window=3, compact_threshold=8, summary_threshold=15,
            compact_budget=300, summary_budget=100, hint_budget=50,
        )
    else:
        cfg = CompressionConfig(
            full_window=4, compact_threshold=10, summary_threshold=20,
            compact_budget=400, summary_budget=150, hint_budget=60,
        )

    return SelectiveCompressor(config=cfg, tokenizer=tokenizer)


# ── CLI smoke-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from .token_counter import get_token_counter as _get_tc

    print("=== Selective Memory Compression Demo ===\n")

    messages = [
        {"role": "user",      "content": "Create a function to add two numbers"},
        {"role": "assistant", "content": "I'll create a simple add function."},
        {"role": "tool",      "content": "[WRITE_FILE] Written 45 chars to add.py"},
        {"role": "assistant", "content": "I've written the add function. Let me run tests."},
        {"role": "tool",      "content": "PASSED: test_add PASSED: test_negative\nAll tests passed!"},
        {"role": "user",      "content": "Now add multiply and divide functions"},
        {"role": "assistant", "content": "I'll add multiply and divide using TDD. First writing tests."},
        {"role": "tool",      "content": "[WRITE_FILE] test_math.py written"},
        {"role": "assistant", "content": "Tests written. Now implementing multiply."},
        {"role": "tool",      "content": "DEF ERROR: name 'multiply' not defined\nLine 5: result = multiply(a, b)"},
        {"role": "assistant", "content": "Found the bug — forgot to implement multiply. Let me fix it."},
    ]

    tc         = _get_tc()
    compressor = create_progressive_compressor(4000, tokenizer=tc)

    print("=== Original Messages ===")
    for i, m in enumerate(messages):
        tokens = tc.count(m["content"])
        print(f"{i}: [{m['role']}] ({tokens}t) {m['content'][:60]}")

    print("\n=== Compressed Context (max 500 tokens) ===")
    result = compressor.build_compressed_context(messages, max_tokens=500)
    print(result)

    print("\n=== Stats ===")
    orig_tokens = sum(tc.count(m["content"]) for m in messages)
    comp_tokens = tc.count(result)
    print(f"Original:   {orig_tokens} tokens")
    print(f"Compressed: {comp_tokens} tokens")
    print(f"Reduction:  {100 * (orig_tokens - comp_tokens) // orig_tokens}%")
