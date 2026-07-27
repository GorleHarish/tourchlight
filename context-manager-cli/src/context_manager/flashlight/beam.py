"""
Flashlight Beam — query-to-code relevance scorer.

Scoring strategy (additive):
  +3.0  per token matching a path component
  +5.0  per token matching a function name
  +4.0  per token matching a class name
  +1.5  per token matching an import
  +0.5  per token matching the first 30 lines (keyword density)
  +2.0  bonus if the file was recently active (mark_active)

Beam size scales automatically with the model's context window:
  <= 4k  tokens: 1 file,  40 lines  (~400 tokens)
  <= 8k  tokens: 2 files, 80 lines  (~1200 tokens)
  > 8k   tokens: 3 files, 120 lines (~2400 tokens)

Call Flashlight.configure(max_context_tokens) once after model selection.
"""

import re
from pathlib import Path
from typing import Optional
from .indexer import SymbolIndex, FileEntry

# Defaults — overridden by configure() based on model context size
_DEFAULT_MAX_FILES     = 2
_DEFAULT_MAX_LINES     = 80
_DEFAULT_ANCHOR_PRE    = 8

# Module-level vars — CLI can write these directly after import:
#   import context_manager.flashlight.beam as _bm
#   _bm.MAX_BEAM_FILES = 1
#   _bm.MAX_LINES_PER_FILE = 50
# Flashlight.beam() reads them when max_files is None and configure() was
# never called, so both the legacy module-var override path and the proper
# .configure() path work correctly.
MAX_BEAM_FILES     = _DEFAULT_MAX_FILES
MAX_LINES_PER_FILE = _DEFAULT_MAX_LINES


def _beam_config_for_context(max_tokens: int) -> tuple[int, int, int]:
    """
    Return (max_files, max_lines_per_file, anchor_pre_lines) scaled to
    the model's context window so the beam never blows past the budget.

    Token budget breakdown (rough, ~4 chars/token):
      system_prompt      ~400
      tool_instructions  ~600
      beam               this function controls
      conversation       the rest

    For a 4096-token model we have about 800 tokens left for beam + history.
    Keep the beam under 500 tokens (1 file × 40 lines × ~12 tokens/line).
    """
    if max_tokens <= 4096:
        return 1, 40, 5    # ~400 beam tokens
    elif max_tokens <= 8192:
        return 2, 80, 8    # ~1400 beam tokens
    elif max_tokens <= 16384:
        return 3, 120, 10  # ~2800 beam tokens
    else:
        return 4, 180, 12  # ~5000 beam tokens


class BeamResult:
    """A single file's contribution to a flashlight beam."""

    __slots__ = ("path", "snippet", "reason", "symbols", "score")

    def __init__(
        self,
        path: str,
        snippet: str,
        reason: str,
        symbols: list[tuple[str, int, str]],
        score: float,
    ):
        self.path    = path
        self.snippet = snippet
        self.reason  = reason
        self.symbols = symbols
        self.score   = score

    def to_block(self) -> str:
        ext = Path(self.path).suffix.lstrip(".")
        return (
            f"### {self.path}  ({self.reason})\n"
            f"```{ext}\n"
            f"{self.snippet}\n"
            f"```"
        )


class Flashlight:
    """
    Shines a flashlight on the code relevant to a query.

    Usage:
        index = SymbolIndex(project_dir)
        light = Flashlight(index)
        light.configure(max_tokens=4096)   # call after model is known

        results = light.beam("how does compression work?")
        for r in results:
            print(r.to_block())

        light.mark_active("src/context_manager/compression/compactor.py")
    """

    def __init__(self, index: SymbolIndex):
        self.index         = index
        self._active_file  = ""
        self._max_files,  \
        self._max_lines,  \
        self._anchor_pre   = _DEFAULT_MAX_FILES, _DEFAULT_MAX_LINES, _DEFAULT_ANCHOR_PRE

    def configure(self, max_context_tokens: int) -> None:
        """
        Scale beam size to the model's context window.
        Call once when the model is selected or changed.

        Example:
            flashlight.configure(4096)   # Qwen2.5-Coder-3B in LM Studio default
            flashlight.configure(8192)   # larger context setting
        """
        self._max_files, self._max_lines, self._anchor_pre = \
            _beam_config_for_context(max_context_tokens)

    def mark_active(self, rel_path: str) -> None:
        self._active_file = rel_path

    def beam(self, query: str, max_files: Optional[int] = None) -> list[BeamResult]:
        import context_manager.flashlight.beam as _bm_mod
        if max_files is None:
            # Prefer module-level override (set by CLI), then instance config
            max_files = _bm_mod.MAX_BEAM_FILES if _bm_mod.MAX_BEAM_FILES != _DEFAULT_MAX_FILES \
                else self._max_files
        # Sync max_lines from module var if it was overridden externally
        if _bm_mod.MAX_LINES_PER_FILE != _DEFAULT_MAX_LINES:
            self._max_lines = _bm_mod.MAX_LINES_PER_FILE

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[float, str, FileEntry]] = []
        for rel_path, entry in self.index.files.items():
            score = self._score(entry, rel_path, query_tokens)
            if score > 0:
                scored.append((score, rel_path, entry))

        scored.sort(key=lambda x: -x[0])

        results = []
        for score, rel_path, entry in scored[:max_files]:
            snippet, anchor_line = self._extract_snippet(query_tokens, entry)
            matched_syms = [
                s for s in entry.symbols
                if query_tokens & self._tokenize(s[0])
            ]
            reason_parts = [f"score={score:.1f}"]
            if matched_syms:
                names = ", ".join(s[0] for s in matched_syms[:3])
                reason_parts.append(f"matched: {names}")
            if anchor_line > 0:
                reason_parts.append(f"line {anchor_line}")
            results.append(BeamResult(
                path    = rel_path,
                snippet = snippet,
                reason  = "  |  ".join(reason_parts),
                symbols = entry.symbols,
                score   = score,
            ))

        return results

    def beam_block(self, query: str, max_files: Optional[int] = None) -> str:
        results = self.beam(query, max_files=max_files)
        if not results:
            return ""
        parts = [r.to_block() for r in results]
        header = (
            f"[FLASHLIGHT — {len(results)} relevant file"
            f"{'s' if len(results) != 1 else ''} for this query]"
        )
        return header + "\n\n" + "\n\n".join(parts)

    def _score(self, entry: FileEntry, rel_path: str, query_tokens: set[str]) -> float:
        score = 0.0
        path_tokens = self._tokenize(rel_path)
        score += len(query_tokens & path_tokens) * 3.0
        for name, _, kind in entry.symbols:
            name_tokens = self._tokenize(name)
            overlap = len(query_tokens & name_tokens)
            score += overlap * (5.0 if kind == "function" else 4.0)
        for imp in entry.imports:
            score += len(query_tokens & self._tokenize(imp)) * 1.5
        for line in entry.lines[:30]:
            score += len(query_tokens & self._tokenize(line)) * 0.5
        if rel_path == self._active_file and score > 0:
            score += 2.0
        return score

    def _extract_snippet(self, query_tokens: set[str], entry: FileEntry,
                         max_lines: Optional[int] = None) -> tuple[str, int]:
        lines = entry.lines
        if not lines:
            return "", 0

        anchor = 0
        for name, lineno, kind in entry.symbols:
            if query_tokens & self._tokenize(name):
                anchor = max(0, lineno - 1)
                break
        else:
            best_score, best_line = -1, 0
            for i, line in enumerate(lines):
                s = len(query_tokens & self._tokenize(line))
                if s > best_score:
                    best_score, best_line = s, i
            anchor = best_line

        start   = max(0, anchor - self._anchor_pre)
        end     = min(len(lines), anchor + self._max_lines)
        snippet = "\n".join(lines[start:end])
        return snippet, anchor + 1

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        raw = set(re.findall(r"[a-zA-Z_]\w*", text.lower()))
        for token in list(raw):
            parts = re.findall(r"[a-z]+|[A-Z][a-z]*", token)
            if len(parts) > 1:
                raw.update(p.lower() for p in parts)
        return {t for t in raw if len(t) > 2}
