"""
Flashlight Beam — query-to-code relevance scorer.

Scoring strategy (additive):
  +3.0  per token matching a path component
  +5.0  per token matching a function name
  +4.0  per token matching a class name
  +1.5  per token matching an import
  +0.5  per token matching the first 30 lines
  +2.0  bonus if the file was recently active
"""

import re
from pathlib import Path
from typing import Optional
from .indexer import SymbolIndex, FileEntry

_DEFAULT_MAX_FILES = 2
_DEFAULT_MAX_LINES = 80
_DEFAULT_ANCHOR_PRE = 8

MAX_BEAM_FILES = _DEFAULT_MAX_FILES
MAX_LINES_PER_FILE = _DEFAULT_MAX_LINES


def _beam_config_for_context(max_tokens: int) -> tuple[int, int, int]:
    if max_tokens <= 4096:
        return 1, 40, 5
    elif max_tokens <= 8192:
        return 2, 80, 8
    elif max_tokens <= 16384:
        return 3, 120, 10
    else:
        return 4, 180, 12


class BeamResult:
    __slots__ = ("path", "snippet", "reason", "symbols", "score")

    def __init__(self, path: str, snippet: str, reason: str, symbols: list, score: float):
        self.path = path
        self.snippet = snippet
        self.reason = reason
        self.symbols = symbols
        self.score = score

    def to_block(self) -> str:
        ext = Path(self.path).suffix.lstrip(".")
        return f"### {self.path}  ({self.reason})\n```{ext}\n{self.snippet}\n```"


class Flashlight:
    def __init__(self, index: SymbolIndex):
        self.index = index
        self._active_file = ""
        self._max_files = _DEFAULT_MAX_FILES
        self._max_lines = _DEFAULT_MAX_LINES
        self._anchor_pre = _DEFAULT_ANCHOR_PRE

    def configure(self, max_context_tokens: int) -> None:
        self._max_files, self._max_lines, self._anchor_pre = _beam_config_for_context(max_context_tokens)

    def mark_active(self, rel_path: str) -> None:
        self._active_file = rel_path

    def beam(self, query: str, max_files: Optional[int] = None) -> list[BeamResult]:
        if max_files is None:
            max_files = self._max_files

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scored = []
        for rel_path, entry in self.index.files.items():
            score = self._score(entry, rel_path, query_tokens)
            if score > 0:
                scored.append((score, rel_path, entry))

        scored.sort(key=lambda x: -x[0])

        results = []
        for score, rel_path, entry in scored[:max_files]:
            snippet, anchor_line = self._extract_snippet(query_tokens, entry)
            matched_syms = [s for s in entry.symbols if query_tokens & self._tokenize(s[0])]
            reason_parts = [f"score={score:.1f}"]
            if matched_syms:
                names = ", ".join(s[0] for s in matched_syms[:3])
                reason_parts.append(f"matched: {names}")
            if anchor_line > 0:
                reason_parts.append(f"line {anchor_line}")
            results.append(BeamResult(
                path=rel_path, snippet=snippet,
                reason="  |  ".join(reason_parts),
                symbols=entry.symbols, score=score,
            ))

        return results

    def beam_block(self, query: str, max_files: Optional[int] = None) -> str:
        results = self.beam(query, max_files=max_files)
        if not results:
            return ""
        parts = [r.to_block() for r in results]
        header = f"[FLASHLIGHT — {len(results)} relevant file{'s' if len(results) != 1 else ''} for this query]"
        return header + "\n\n" + "\n\n".join(parts)

    def _score(self, entry: FileEntry, rel_path: str, query_tokens: set) -> float:
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

    def _extract_snippet(self, query_tokens: set, entry: FileEntry, max_lines: Optional[int] = None) -> tuple[str, int]:
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
        start = max(0, anchor - self._anchor_pre)
        end = min(len(lines), anchor + self._max_lines)
        snippet = "\n".join(lines[start:end])
        return snippet, anchor + 1

    @staticmethod
    def _tokenize(text: str) -> set:
        raw = set(re.findall(r"[a-zA-Z_]\w*", text.lower()))
        for token in list(raw):
            parts = re.findall(r"[a-z]+|[A-Z][a-z]*", token)
            if len(parts) > 1:
                raw.update(p.lower() for p in parts)
        return {t for t in raw if len(t) > 2}
