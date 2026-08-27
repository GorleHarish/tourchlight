"""Transcript formatting helpers, syntax caching, and metadata utilities."""

from __future__ import annotations

import datetime
import os
import re
from functools import lru_cache
from typing import Optional

from rich.markup import escape
from rich.syntax import Syntax
from rich.text import Text
from textual.containers import Container
from textual.widgets import Markdown, Static

from core.tools.classification import AUTO, CONFIRM, REVIEW, classify_tool

ROLE_LABELS = {
    "user": "YOU",
    "assistant": "ASSISTANT",
    "final": "ANSWER",
}

RISK_META = {
    AUTO: ("", "AUTO", "risk-auto"),
    CONFIRM: ("", "CONFIRM", "risk-confirm"),
    REVIEW: ("", "REVIEW", "risk-review"),
}

TOOL_ICONS: dict[str, str] = {
    "READ_FILE": "",
    "GREP": "",
    "READ_SYMBOLS": "",
    "SEARCH_AST": "",
    "LIST_DIR": "",
    "WRITE_FILE": "",
    "EDIT_FILE": "",
    "RUN_COMMAND": "",
    "INSPECT_WEB": "",
    "WEB_FETCH": "",
    "WEB_SEARCH": "",
    "SAVE_MEMORY": "",
    "UPDATE_TASK_GRAPH": "",
    "GIT": "",
    "FORMAT_CODE": "",
    "VERIFY": "",
}


def escape_markup(text: str) -> str:
    """Safely escape text for Textual markup parsing."""
    if not text:
        return ""
    return str(text).replace("\\", "\\\\").replace("[", "\\[")

def summarize_args(args: dict | None) -> str:
    """Compact key/value summary of tool args (path, cmd, query, ...)."""
    if not args:
        return ""
    lines = []
    for key in (
        "path",
        "file_path",
        "command",
        "cmd",
        "pattern",
        "query",
        "url",
        "name",
        "tool",
        "symbol",
        "start_line",
        "end_line",
    ):
        if key in args and args[key] not in (None, ""):
            val = str(args[key])
            if len(val) > 200:
                val = val[:200] + "..."
            lines.append(f"{key}: {val}")

    # For EDIT_FILE or WRITE_FILE, format preview of edits/diffs
    if args.get("diff"):
        diff_str = str(args["diff"]).strip()
        preview = diff_str[:300] + ("..." if len(diff_str) > 300 else "")
        lines.append(f"diff:\n{preview}")
    elif "old_text" in args or "new_text" in args:
        old_val = str(args.get("old_text", "")).strip()
        new_val = str(args.get("new_text", "")).strip()
        if old_val:
            preview_old = old_val[:150] + ("..." if len(old_val) > 150 else "")
            lines.append(f"old_text:\n{preview_old}")
        if new_val:
            preview_new = new_val[:150] + ("..." if len(new_val) > 150 else "")
            lines.append(f"new_text:\n{preview_new}")
    elif args.get("content"):
        content_str = str(args["content"]).strip()
        if len(content_str) > 200:
            preview_cnt = content_str[:200] + "..."
            lines.append(f"content:\n{preview_cnt}")
        else:
            lines.append(f"content:\n{content_str}")

    if not lines:
        lines.append(f"{len(args)} argument(s)")
    return "\n".join(lines)


def truncate_output(text: str, *, max_lines: int = 40, max_chars: int = 15000) -> str:
    """Truncate tool output for the UI: hard char + line caps."""
    if len(text) > max_chars:
        text = text[:max_chars]
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        return "\n".join(lines) + "\n... [Output Truncated for UI Performance]"
    return text


def estimate_token_count(text: str) -> int:
    """Cheap token estimate (≈3 chars/token, matching the engine heuristic)."""
    return max(1, len(text) // 3)


def card_meta_for(content: str) -> str:
    """Footer summary for an assistant card: word count + token estimate."""
    words = len(content.split())
    return f"{words:,} words · ≈{estimate_token_count(content):,} tok"


def timestamp_str() -> str:
    """Current time as a compact HH:MM label (local time, display only)."""
    return datetime.datetime.now().strftime("%H:%M")  # noqa: DTZ005


from functools import lru_cache

@lru_cache(maxsize=128)
def _build_cached_syntax(code: str, lang: str) -> Syntax:
    """Cache Pygments syntax objects to avoid re-parsing identical code blocks."""
    return Syntax(code, lang, theme="monokai", line_numbers=False, word_wrap=True)


@lru_cache(maxsize=128)
def extract_code_blocks(markdown_text: str) -> tuple[tuple[str, str, int, int], ...]:
    """Extract code blocks from markdown text.
    
    Returns tuple of (language, code, start_pos, end_pos) tuples.
    """
    pattern = r'```(\w*)\n(.*?)\n```'
    blocks = []
    for match in re.finditer(pattern, markdown_text, re.DOTALL):
        lang = match.group(1) or "text"
        code = match.group(2)
        blocks.append((lang, code, match.start(), match.end()))
    return tuple(blocks)


def render_markdown_with_syntax_highlighting(markdown_text: str) -> list:
    """Parse markdown and return widgets with syntax-highlighted code blocks.
    
    Splits markdown into text segments and code blocks, rendering code blocks
    with rich.syntax.Syntax for proper highlighting.
    """
    widgets = []
    blocks = extract_code_blocks(markdown_text)
    
    if not blocks:
        # No code blocks, return single markdown widget
        widgets.append(Markdown(markdown_text, classes="message-card-body"))
        return widgets
    
    last_end = 0
    for lang, code, start, end in blocks:
        # Add text before code block
        if start > last_end:
            text_segment = markdown_text[last_end:start]
            if text_segment.strip():
                widgets.append(Markdown(text_segment, classes="message-card-body"))
        
        # Add syntax-highlighted code block
        try:
            syntax = _build_cached_syntax(code, lang)
            code_container = Container(classes="code-block-container")
            code_container._syntax = syntax  # Store for rendering
            code_container._lang = lang
            code_container._code = code
            widgets.append(code_container)
        except Exception:
            # Fallback to plain markdown code block
            widgets.append(Markdown(f"```{lang}\n{code}\n```", classes="message-card-body"))
        
        last_end = end
    
    # Add remaining text after last code block
    if last_end < len(markdown_text):
        text_segment = markdown_text[last_end:]
        if text_segment.strip():
            widgets.append(Markdown(text_segment, classes="message-card-body"))
    
    return widgets
