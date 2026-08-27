"""Search/replace diff block parsing, symbol boundary extraction, and indentation alignment."""

from __future__ import annotations

import ast
import re
from typing import Optional

_CONFLICT_MARKER_RE = re.compile(r"^[ \t]*(?:<{7}|>{7})", re.MULTILINE)
_DIFFSTAT_RE = re.compile(r"\(\+\d+, -\d+\)")


def _edit_succeeded(result: str) -> bool:
    """True only when an edit/write result reports a committed change."""
    return bool(result) and _DIFFSTAT_RE.search(result) is not None


def _parse_diff_block(text: str) -> tuple[Optional[str], Optional[str]]:
    """Parse Aider-style <<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE block into (old_text, new_text).
    Supports flexible variations produced by LLMs (e.g., missing 'REPLACE' label, '>>>>>>>' used as divider).
    """
    if not text:
        return None, None

    def _clean_segment(s: str) -> str:
        if s.startswith("\r\n"):
            s = s[2:]
        elif s.startswith("\n"):
            s = s[1:]
        if s.endswith("\r\n"):
            s = s[:-2]
        elif s.endswith("\n"):
            s = s[:-1]
        return s

    # 1. Flexible regex-based parsing for Search/Replace blocks
    search_match = re.search(r"<<<<<<<(?:[ \t]*SEARCH)?\r?\n", text)
    if search_match:
        after_search = text[search_match.end() :]
        # Option A: Standard divider =======
        div_match = re.search(r"\r?\n=======\r?\n", after_search)
        if div_match:
            search_part = after_search[: div_match.start()]
            after_div = after_search[div_match.end() :]
            end_match = re.search(
                r"\r?\n>>>>>>>(?:[ \t]*REPLACE)?(?:$|\r?\n)", after_div
            )
            if end_match:
                replace_part = after_div[: end_match.start()]
                return _clean_segment(search_part), _clean_segment(replace_part)
            else:
                end_match2 = re.search(r">>>>>>>(?:[ \t]*REPLACE)?", after_div)
                if end_match2:
                    replace_part = after_div[: end_match2.start()]
                    return _clean_segment(search_part), _clean_segment(replace_part)

        # Option B: Model used >>>>>>> as divider between SEARCH block and REPLACE block
        div_alt = re.search(r"\r?\n>>>>>>>(?:[ \t]*SEARCH)?\r?\n", after_search)
        if div_alt:
            search_part = after_search[: div_alt.start()]
            after_div = after_search[div_alt.end() :]
            end_match = re.search(r"\r?\n>>>>>>>(?:[ \t]*REPLACE)?", after_div)
            if end_match:
                replace_part = after_div[: end_match.start()]
                return _clean_segment(search_part), _clean_segment(replace_part)

        # Option C: Model omitted ======= divider, putting >>>>>>> REPLACE directly between search and replace
        rep_tag = re.search(r"\r?\n>>>>>>>(?:[ \t]*REPLACE)?\r?\n", after_search)
        if rep_tag:
            search_part = after_search[: rep_tag.start()]
            after_rep = after_search[rep_tag.end() :]
            end_tag = re.search(r"\r?\n>>>>>>>(?:[ \t]*REPLACE)?", after_rep)
            replace_part = after_rep[: end_tag.start()] if end_tag else after_rep
            if search_part and replace_part:
                return _clean_segment(search_part), _clean_segment(replace_part)

    # 2. String splitting fallback (legacy logic)
    search_marker = "<<<<<<< SEARCH"
    divide_marker = "======="
    replace_marker = ">>>>>>> REPLACE"

    if search_marker in text and divide_marker in text:
        try:
            after_search = text.split(search_marker, 1)[1]
            if replace_marker in after_search:
                between, _ = after_search.split(replace_marker, 1)
            elif ">>>>>>>" in after_search:
                between, _ = after_search.split(">>>>>>>", 1)
            else:
                between = after_search
            search_part, replace_part = between.split(divide_marker, 1)
            return _clean_segment(search_part), _clean_segment(replace_part)
        except Exception:
            pass

    # No recognizable block structure. Return (None, None) rather than guessing:
    # splitting arbitrary text on blank lines or at its midpoint fabricates an
    # (old_text, new_text) pair the model never asked for, which silently
    # deletes the "old" half and duplicates the "new" half.
    return None, None


def _get_symbol_bounds_ast(content: str, symbol_name: str) -> Optional[Tuple[int, int]]:
    """Helper to locate exact start and end line bounds for an AST symbol in Python source code."""
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = node.name
                if (
                    name == symbol_name
                    or symbol_name.endswith(f".{name}")
                    or f".{name}" in symbol_name
                ):
                    start = getattr(node, "lineno", None)
                    end = getattr(node, "end_lineno", None)
                    if start and end:
                        return start, end
    except Exception:
        pass
    return None


def _get_symbol_bounds_general(content: str, symbol_name: str, ext: str = "") -> Optional[Tuple[int, int]]:
    """Helper to locate exact start and end line bounds (1-based) for a symbol across Python, JS, TS, Go, Rust, etc."""
    if not content or not symbol_name:
        return None

    # 1. Python AST parsing
    ext_norm = ext.lower().lstrip(".")
    if ext_norm in ("py", ""):
        bounds = _get_symbol_bounds_ast(content, symbol_name)
        if bounds:
            return bounds

    lines = content.splitlines()
    total = len(lines)

    # 2. Brace-based languages (JS, TS, C, C++, Java, Rust, Go, CSS)
    sym_clean = re.escape(symbol_name)
    patterns = [
        re.compile(rf"^\s*(?:export\s+)?(?:async\s+)?function\s+{sym_clean}\b"),
        re.compile(rf"^\s*(?:export\s+)?(?:const|let|var)\s+{sym_clean}\s*="),
        re.compile(rf"^\s*(?:export\s+)?class\s+{sym_clean}\b"),
        re.compile(rf"^\s*(?:pub\s+)?fn\s+{sym_clean}\b"),
        re.compile(rf"^\s*(?:def|func|fun)\s+{sym_clean}\b"),
        re.compile(rf"^\s*{sym_clean}\s*\([^)]*\)\s*\{{"),
        re.compile(rf"\b{sym_clean}\b"),
    ]

    start_line = None
    for i, line in enumerate(lines):
        for pat in patterns:
            if pat.search(line):
                start_line = i + 1
                break
        if start_line is not None:
            break

    if start_line is None:
        return None

    # Track brace balance from start_line
    brace_depth = 0
    found_first_brace = False
    for i in range(start_line - 1, total):
        line = lines[i]
        clean_l = re.sub(r"//.*$", "", line)
        for char in clean_l:
            if char == "{":
                brace_depth += 1
                found_first_brace = True
            elif char == "}":
                brace_depth -= 1
                if found_first_brace and brace_depth <= 0:
                    return start_line, i + 1

    if start_line is not None:
        return start_line, start_line

    return None


def _reindent_block(old_text: str, new_text: str, content: str, start_idx: int) -> str:
    line_start = content.rfind("\n", 0, start_idx)
    line_start = 0 if line_start == -1 else line_start + 1
    leading_space_match = re.match(r"^[ \t]*", content[line_start:start_idx])
    if not leading_space_match:
        return new_text
    leading_space = leading_space_match.group(0)
    if new_text.startswith(leading_space):
        return new_text
    lines = new_text.split("\n")
    reindented = []
    for i, line in enumerate(lines):
        if i == 0:
            reindented.append(line)
        else:
            reindented.append(leading_space + line if line.strip() else line)
    return "\n".join(reindented)
