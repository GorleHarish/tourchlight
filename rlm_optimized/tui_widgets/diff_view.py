"""Inline diff rendering for the Torchlight TUI.

Phase 3 of the UI-improvements plan: show *what changed* before and after.
``render_unified_diff`` is a pure ``difflib`` wrapper (no Rich/Textual, so it
is trivially unit-testable), ``diff_markup`` turns the entries into Rich
markup, and ``build_diff_preview`` reads the current file from disk — UI
layer only, never touching the model context. ``DiffView`` is the widget.

Styled with theme variables only (CSS-first, no ``styles.set``).
"""

from __future__ import annotations

import os
from difflib import unified_diff

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static

KIND_ADD = "add"
KIND_DEL = "del"
KIND_CTX = "context"
KIND_META = "meta"

LINE_COLORS = {
    KIND_ADD: "green",
    KIND_DEL: "red",
    KIND_CTX: None,
    KIND_META: "magenta",
}


def escape_markup(text: str) -> str:
    """Safely escape text for Textual markup parsing.

    Escapes backslashes first, then all square brackets [, preventing
    unmatched brackets or bracketed code/strings from causing MarkupError.
    """
    if not text:
        return ""
    return str(text).replace("\\", "\\\\").replace("[", "\\[")


def render_unified_diff(
    old_text: str,
    new_text: str,
    *,
    path: str = "",
    context: int = 3,
) -> list[tuple[str, str]]:
    """Render ``old_text`` vs ``new_text`` as a list of (kind, line) entries.

    Kinds: ``add`` (+), ``del`` (-), ``context`` (unchanged), ``meta``
    (header / hunk ``@@``). Pure function — safe to unit test.
    """
    old_lines = (old_text or "").splitlines()
    new_lines = (new_text or "").splitlines()
    if not old_lines and not new_lines:
        return []
    from_label = f"a/{path}" if path else "a"
    to_label = f"b/{path}" if path else "b"
    diff = unified_diff(
        old_lines,
        new_lines,
        fromfile=from_label,
        tofile=to_label,
        n=context,
        lineterm="",
    )
    entries: list[tuple[str, str]] = []
    for line in diff:
        if line.startswith(("+++", "---", "@@")):
            entries.append((KIND_META, line))
        elif line.startswith("+"):
            entries.append((KIND_ADD, line))
        elif line.startswith("-"):
            entries.append((KIND_DEL, line))
        else:
            entries.append((KIND_CTX, line))
    return entries


def diff_summary(entries: list[tuple[str, str]]) -> str:
    """Short "+N −M" stat for a diff entry list ('' when empty)."""
    adds = sum(1 for kind, _ in entries if kind == KIND_ADD)
    dels = sum(1 for kind, _ in entries if kind == KIND_DEL)
    if not adds and not dels:
        return ""
    return f"+{adds} −{dels}"


def diff_markup(
    entries: list[tuple[str, str]],
    *,
    max_lines: int = 80,
) -> str:
    """Render diff entries as Rich/Textual markup, truncated to ``max_lines``."""
    out: list[str] = []
    for kind, line in entries:
        color = LINE_COLORS.get(kind)
        escaped_line = escape_markup(line)
        if color:
            out.append(f"[{color}]{escaped_line}[/]")
        else:
            out.append(escaped_line)
        if len(out) >= max_lines:
            out.append("[dim]... [Diff Truncated for UI Performance][/]")
            break
    return "\n".join(out)


def build_diff_preview(
    tool_name: str,
    args: dict | None,
    project_root: str,
    *,
    old_text: str | None = None,
) -> tuple[str, str, str, list[tuple[str, str]]] | None:
    """Build a diff preview for a WRITE_FILE / EDIT_FILE action.

    Returns ``(path, old_text, new_text, entries)``, or ``None`` when the
    action has no diffable content / the target file cannot be read. Pure
    filesystem access in the UI layer — nothing is injected into model
    context.

    ``old_text`` lets callers pass a pre-write snapshot (captured at approval
    time) so the "before" side reflects the real prior content even though
    the file has already been written by the time the step reports.
    """
    if not isinstance(args, dict):
        return None
    path = str(args.get("path") or args.get("file_path") or "")
    if not path or not os.path.isabs(path):
        return None
    if tool_name not in ("WRITE_FILE", "EDIT_FILE", "CODE_FILE_WRITE"):
        return None

    new_text_arg = str(args.get("content") or args.get("new_text") or "")
    if not new_text_arg:
        return None

    # Disk state (post-edit once the write has landed, pre-edit while the
    # preview runs ahead of an apply).
    disk = None
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                disk = f.read()
        except OSError:
            disk = None

    old_text_arg = args.get("old_text")
    old = old_text  # caller-supplied pre-write snapshot wins
    if old is not None:
        new_text = new_text_arg
    elif tool_name == "EDIT_FILE" and isinstance(old_text_arg, str) and old_text_arg:
        if disk is not None:
            if old_text_arg in disk:
                # Disk is pre-edit → apply the edit forward.
                old = disk
                new_text = disk.replace(old_text_arg, new_text_arg, 1)
            else:
                # Disk is post-edit → back the edit out for the "before" side.
                old = disk.replace(new_text_arg, old_text_arg, 1)
                new_text = disk
        else:
            old = ""
            new_text = new_text_arg
    else:
        old = disk or ""
        new_text = new_text_arg

    return path, old, new_text, render_unified_diff(old, new_text, path=path)


class DiffView(Container):
    """A unified diff card: header (path + +N −M) + colored body.

    Rendered client-side from file contents — no LLM context involvement.
    """

    DEFAULT_CSS = """
    DiffView {
        height: auto;
        width: 1fr;
        layout: vertical;
        margin: 0 0 1 0;
        background: $surface;
        border: round $panel;
        border-left: thick $success;
    }

    DiffView > Horizontal.diff-view-header {
        height: 1;
        align: left middle;
        padding: 0 1;
        background: $panel;
    }

    Static.diff-view-path {
        width: 1fr;
        color: $text-muted;
        text-style: bold;
        text-overflow: ellipsis;
    }

    Static.diff-view-stat {
        width: auto;
        color: $foreground-muted;
    }

    Static.diff-view-body {
        width: 1fr;
        height: auto;
        padding: 1 2;
        color: $foreground;
    }
    """

    def __init__(
        self,
        entries: list[tuple[str, str]],
        *,
        path: str = "",
        id: str | None = None,
    ) -> None:
        super().__init__(classes="diff-view", id=id)
        self._entries = entries
        self._path = path

    def compose(self) -> ComposeResult:
        with Horizontal(classes="diff-view-header"):
            yield Static(self._path or "diff", classes="diff-view-path", markup=False)
            yield Static(diff_summary(self._entries), classes="diff-view-stat", markup=False)
        yield Static(diff_markup(self._entries), classes="diff-view-body")
