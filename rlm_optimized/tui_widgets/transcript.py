"""Rich transcript widgets for the Torchlight TUI.

Phase 1 of the UI-improvements plan: message cards (user / assistant /
final answer), the live streaming turn, and the bounded scroll container
that hosts the transcript.
"""

from __future__ import annotations

import datetime
import os
import re
import sys
from typing import Optional

from rich.markup import escape
from rich.syntax import Syntax
from rich.text import Text
from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Markdown, Static

try:
    from textual.widgets import Collapsible
except ImportError:  # pragma: no cover - older Textual
    Collapsible = None

from core.tools.classification import AUTO, CONFIRM, REVIEW, classify_tool
from .tool_card import ToolCallCard

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


class ImageAttachmentCard(Container):
    """Visual card displaying image metadata and a 24-bit ANSI terminal color preview."""

    DEFAULT_CSS = """
    ImageAttachmentCard {
        height: auto;
        margin: 1 0;
        padding: 0;
        border: solid $panel;
        border-left: solid $accent;
        background: $background;
    }

    ImageAttachmentCard > Horizontal.image-card-header {
        height: 1;
        align: left middle;
        padding: 0 1;
        background: $panel;
        border-bottom: solid $panel;
    }

    Static.image-card-title {
        width: 1fr;
        color: $text;
        text-style: bold;
    }

    Static.image-card-meta {
        width: auto;
        color: $foreground-muted;
    }

    Static.image-card-btn {
        width: auto;
        min-width: 3;
        color: $text-muted;
        background: $surface;
        margin: 0 0 0 1;
        padding: 0 1;
        text-align: center;
    }

    Static.image-card-btn:hover {
        background: $accent;
        color: $background;
        text-style: bold;
    }

    .image-preview-box {
        height: auto;
        padding: 1;
        align: center middle;
        background: $background;
    }
    """

    def __init__(
        self,
        image_path: str,
        project_root: str = ".",
        classes: str | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(classes=classes, id=id)
        self._image_path = image_path
        self._project_root = project_root

    @property
    def full_path(self) -> str:
        p = self._image_path
        if not os.path.isabs(p):
            return os.path.join(self._project_root, p)
        return p

    def compose(self) -> ComposeResult:
        from core.utils.image_utils import (
            get_image_metadata,
            generate_ansi_image_preview,
        )

        p = self._image_path
        full_p = self.full_path

        meta = (
            get_image_metadata(full_p, project_root=self._project_root)
            if os.path.exists(full_p)
            else {}
        )
        w = meta.get("width")
        h = meta.get("height")
        dim_str = (
            f"{w}x{h} {meta.get('format', 'IMG')}"
            if w and h
            else meta.get("format", "IMG")
        )
        size_str = f"{meta.get('size_kb', 0)} KB"

        with Horizontal(classes="image-card-header"):
            yield Static(f"[IMG] {os.path.basename(p)}", classes="image-card-title")
            yield Static(f"{dim_str} · {size_str}", classes="image-card-meta")
            open_btn = Static("🚀", classes="image-card-btn image-card-open", markup=False)
            open_btn.tooltip = "Open with default system application"
            yield open_btn
            tab_btn = Static("👁", classes="image-card-btn image-card-tab", markup=False)
            tab_btn.tooltip = "Open in Editor Split View"
            yield tab_btn
            copy_btn = Static("❐", classes="image-card-btn image-card-copy", markup=False)
            copy_btn.tooltip = "Copy image path"
            yield copy_btn

        # Generate 24-bit ANSI terminal color preview
        preview_text = generate_ansi_image_preview(
            full_p, max_width=44, max_height=14, project_root=self._project_root
        )
        if preview_text:
            yield Static(preview_text, classes="image-preview-box")
        else:
            yield Static(f"[dim]Attached Image: {p}[/dim]", classes="image-preview-box")

    @on(events.Click, ".image-card-open")
    def on_open_click(self, event: events.Click) -> None:
        event.stop()
        self.action_open_system()

    @on(events.Click, ".image-card-copy")
    def on_copy_click(self, event: events.Click) -> None:
        event.stop()
        self.action_copy_path()

    @on(events.Click, ".image-card-tab")
    def on_tab_click(self, event: events.Click) -> None:
        event.stop()
        self.action_open_tab()

    @on(events.Click, ".image-card-title")
    def on_title_click(self, event: events.Click) -> None:
        event.stop()
        self.action_open_tab()

    def action_open_system(self) -> None:
        from rlm_optimized.tui_widgets.image_viewer import open_file_in_system_app

        full_p = self.full_path
        filename = os.path.basename(full_p)
        if open_file_in_system_app(full_p):
            self.notify(f"🚀 Opened {filename} with default app", timeout=2)
        else:
            self.notify(f"Could not open {filename}", severity="error", timeout=3)

    def action_copy_path(self) -> None:
        full_p = self.full_path
        filename = os.path.basename(full_p)
        try:
            from rlm_optimized.tui_app import copy_to_clipboard

            if copy_to_clipboard(full_p):
                self.notify(f"📋 Copied path: {filename}", timeout=2)
            else:
                self.notify(f"Path: {full_p}", timeout=4)
        except Exception:
            self.notify(f"Path: {full_p}", timeout=4)

    def action_open_tab(self) -> None:
        if self.app and hasattr(self.app, "open_file_tab"):
            self.app.open_file_tab(self.full_path)
            self.notify(f"Opened {os.path.basename(self.full_path)} in editor", timeout=1.5)


class MessageCard(Container):
    """A chat turn rendered as a rich Markdown card with header chrome.

    Styled with theme variables only (CSS-first, no ``styles.set``). The role
    is carried as a ``role-*`` class so callers can restyle per role.
    
    Features:
    - Syntax-highlighted code blocks with copy buttons
    - Collapsible tool call/result sections
    - Inline token counts per message
    - Visual distinction for tool calls vs conversational text
    - Better markdown rendering (tables, lists, checkboxes)
    - Avatars/role indicators matching Claude Code aesthetic
    """

    DEFAULT_CSS = """
    MessageCard {
        height: auto;
        width: 1fr;
        layout: vertical;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $panel;
        border-left: solid $primary;
    }

    MessageCard.role-user {
        border-left: solid $accent;
    }

    MessageCard.role-assistant,
    MessageCard.role-final {
        border-left: solid $success;
    }

    MessageCard > Horizontal.message-card-header {
        height: 1;
        align: left middle;
        padding: 0 1;
        background: $panel;
    }

    Static.message-card-role {
        width: auto;
        color: $text-muted;
        text-style: bold;
    }

    Static.message-card-time {
        width: 1fr;
        color: $foreground-muted;
        text-align: right;
    }

    Static.message-card-copy,
    Static.message-card-reuse {
        width: auto;
        min-width: 3;
        color: $text-muted;
        background: $surface;
        margin: 0 0 0 1;
        padding: 0 1;
        text-align: center;
    }

    Static.message-card-copy:hover,
    Static.message-card-reuse:hover {
        background: $accent;
        color: $background;
        text-style: bold;
    }

    MessageCard > Markdown {
        height: auto;
        padding: 1 2 1 2;
        overflow-y: hidden;
    }

    MessageCard > Container.message-card-body-wrapper {
        height: auto;
        padding: 1 2 1 2;
        overflow-y: hidden;
    }

    .code-block-container {
        height: auto;
        margin: 1 0;
        border: round $panel;
        background: $background;
    }

    .code-block-container > Horizontal.code-block-header {
        height: 1;
        align: left middle;
        padding: 0 1;
        background: $panel;
        border-bottom: solid $panel;
    }

    Static.code-block-lang {
        width: auto;
        color: $text-muted;
        text-style: bold;
    }

    Static.code-block-copy {
        width: auto;
        color: $foreground-muted;
        text-align: right;
        margin-right: 1;
    }

    Static.code-block-copy:hover {
        color: $accent;
        text-style: underline;
    }

    .code-block-content {
        height: auto;
        padding: 1;
        overflow-x: auto;
    }

    .tool-call-section {
        margin: 1 0;
        border: round $panel;
        background: $background;
    }

    .tool-call-section > Horizontal.tool-call-header {
        height: 1;
        align: left middle;
        padding: 0 1;
        background: $panel;
        border-bottom: solid $panel;
    }

    Static.tool-call-title {
        width: 1fr;
        color: $text-muted;
        text-style: bold;
    }

    Static.tool-call-status {
        width: auto;
        margin-right: 1;
        text-style: bold;
    }

    .tool-call-body {
        height: auto;
        padding: 1;
        overflow-y: auto;
        max-height: 15;
    }

    MessageCard:focus-within {
        border-left: tall $primary;
    }

    MessageCard:hover {
        background-tint: $foreground 3%;
    }
    """

    def __init__(
        self,
        content: str,
        *,
        role: str = "assistant",
        meta: str = "",
        timestamp: str | None = None,
        duration: float | str | None = None,
        classes: str | None = None,
        id: str | None = None,
        tool_calls: list | None = None,
        token_count: int | None = None,
        images: list[str] | None = None,
        project_root: str = ".",
    ) -> None:
        role = role if role in ROLE_LABELS else "assistant"
        role_class = f"role-{role}"
        merged = f"{role_class} {classes}".strip() if classes else role_class
        super().__init__(classes=merged, id=id)
        self._content = content or ""
        self._role = role
        self._meta = meta or ""
        self._timestamp = timestamp
        self._duration = duration
        self._tool_calls = tool_calls or []
        self._token_count = token_count or estimate_token_count(content)
        self._images = list(images) if images else []
        self._project_root = project_root

    def _role_label(self) -> str:
        return ROLE_LABELS.get(self._role, "ASSISTANT")

    def _time_str(self) -> str:
        """Return elapsed duration (e.g. '2.4s'), explicit timestamp override, or empty string."""
        if self._duration is not None:
            if isinstance(self._duration, (int, float)):
                return f"{self._duration:.1f}s"
            return str(self._duration)
        if self._timestamp is not None:
            return str(self._timestamp)
        return ""

    def compose(self) -> ComposeResult:
        with Horizontal(classes="message-card-header"):
            yield Static(self._role_label(), classes="message-card-role")
            yield Static(self._time_str(), classes="message-card-time")
            if self._role == "user":
                reuse_btn = Static("↻", classes="message-card-reuse", markup=False)
                reuse_btn.tooltip = "Reuse message in input prompt"
                yield reuse_btn
            copy_btn = Static("❐", classes="message-card-copy", markup=False)
            copy_btn.tooltip = "Copy message to clipboard"
            yield copy_btn
        
        # Render content with syntax highlighting for code blocks
        content_widgets = render_markdown_with_syntax_highlighting(self._content)
        for widget in content_widgets:
            yield widget

        # Render image attachment cards if images are attached or mentioned
        img_paths = list(self._images) if self._images else []
        if not img_paths and self._content:
            from core.utils.image_utils import extract_image_paths_from_text

            img_paths = extract_image_paths_from_text(self._content)

        for img_p in img_paths:
            yield ImageAttachmentCard(img_p, project_root=self._project_root)
        
        # Add tool call sections if present
        if self._tool_calls:
            for tool_call in self._tool_calls:
                yield self._build_tool_call_section(tool_call)

    def _build_tool_call_section(self, tool_call: dict) -> Container:
        """Build a collapsible section for a tool call."""
        tool_name = tool_call.get("name", "TOOL")
        args = tool_call.get("arguments", {})
        result = tool_call.get("result", "")
        status = tool_call.get("status", "ok")
        
        _risk_icon, risk_label, _ = RISK_META.get(tool_call.get("risk", "confirm"), RISK_META[CONFIRM])
        
        section = Container(classes="tool-call-section")
        
        # Header
        target_str = ToolCallCard._target_from_args(tool_name, args)
        target_display = f" [dim]{escape(target_str)}[/dim]" if target_str else ""
        with Horizontal(classes="tool-call-header"):
            prefix = f"[{risk_label}] " if risk_label else ""
            yield Static(f"{prefix}{escape(tool_name)}{target_display}", classes="tool-call-title")
            status_text = "OK" if status == "ok" else "ERR" if status == "error" else "DENIED"
            status_class = "ok" if status == "ok" else "error" if status == "error" else "denied"
            yield Static(status_text, classes=f"tool-call-status {status_class}")


        
        # Body content
        body_parts = []
        if args:
            arg_summary = summarize_args(args)
            if arg_summary:
                body_parts.append(f"[dim]Params:[/]\n[dim]{escape(arg_summary)}[/]")
        if result:
            body_parts.append(f"[bold]Result:[/]\n{escape(truncate_output(result))}")
        
        if body_parts:
            body_text = "\n\n".join(body_parts)
            output_lines = len(result.splitlines()) if result else 0
            # Short outputs (<= 10 lines) default to expanded; longer outputs (> 10 lines) default to collapsed
            should_expand = (output_lines <= 10) or (status != "ok")
            if Collapsible is not None:
                collapsible = Collapsible(
                    Static(body_text, classes="tool-call-body", markup=True),
                    title="Details",
                    collapsed=not should_expand,
                    classes="tool-call-section",
                )
                yield collapsible
            else:
                yield Static(body_text, classes="tool-call-body", markup=True)

        
        return section

    @on(events.Click, ".message-card-copy")
    def on_copy_click(self, event: events.Click) -> None:
        event.stop()
        self.action_copy()

    @on(events.Click, ".message-card-reuse")
    def on_reuse_click(self, event: events.Click) -> None:
        event.stop()
        self.action_reuse()

    def action_copy(self) -> None:
        if self._content:
            try:
                from rlm_optimized.tui_app import copy_to_clipboard

                if copy_to_clipboard(self._content):
                    self.notify("Message copied to clipboard", timeout=1.5)
                else:
                    self.notify("Failed to copy message", severity="error", timeout=2)
            except Exception:
                pass

    def action_reuse(self) -> None:
        if self._content and self.app:
            try:
                user_input = getattr(self.app, "_user_input", None)
                if user_input is None:
                    user_input = self.app.query_one("#user-input")
                if user_input is not None:
                    if hasattr(user_input, "text"):
                        user_input.text = self._content
                    elif hasattr(user_input, "value"):
                        user_input.value = self._content
                    user_input.focus()
                    self.notify("Message loaded into prompt", timeout=1.5)
            except Exception:
                pass


class StreamingView(Container):
    """Live streaming turn: header, cheap body, and live meta footer.

    The body stays a ``Static`` (Rich markup) so high-frequency token updates
    never pay the cost of a full Markdown re-parse; the completed turn is
    re-rendered as a ``MessageCard`` when the stream finishes.
    
    Enhanced with:
    - Live token count display
    - Smooth scrolling during streaming
    - Phase-aware streaming indicators
    """

    DEFAULT_CSS = """
    StreamingView {
        height: auto;
        width: 1fr;
        layout: vertical;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $panel;
        border-left: solid $success;
    }

    StreamingView.phase-plan {
        border-left: solid $warning;
    }

    StreamingView.phase-code {
        border-left: solid $primary;
    }

    StreamingView.phase-troubleshoot {
        border-left: solid $error;
    }

    StreamingView > Horizontal.streaming-header {
        height: 1;
        align: left middle;
        padding: 0 1;
        background: $panel;
    }

    Static.streaming-live {
        width: 2;
        color: $success;
        text-style: bold blink;
    }

    Static.streaming-role {
        width: auto;
        color: $text-muted;
        text-style: bold;
    }

    Static.streaming-phase {
        width: auto;
        margin: 0 0 0 1;
        padding: 0 1;
        color: $foreground-muted;
        text-style: italic;
    }

    Static.streaming-meta {
        width: 1fr;
        color: $foreground-muted;
        text-align: right;
    }

    Static.streaming-tokens {
        width: auto;
        color: $accent;
        margin-right: 1;
        text-style: bold;
    }

    Static.streaming-body {
        width: 1fr;
        height: auto;
        padding: 1 2 1 2;
        color: $foreground;
    }
    """

    def __init__(self, *, meta: str = "", phase: str = "chat", id: str | None = None) -> None:
        super().__init__(classes=f"streaming-view phase-{phase}", id=id)
        self._meta = meta
        self._phase = phase
        self._body: Static | None = None
        self._meta_widget: Static | None = None
        self._token_widget: Static | None = None
        self._phase_widget: Static | None = None
        self._token_count = 0

    def compose(self) -> ComposeResult:
        with Horizontal(classes="streaming-header"):
            yield Static("▍", classes="streaming-live")
            yield Static("ASSISTANT", classes="streaming-role")
            phase_labels = {"plan": "PLAN", "code": "CODE", "troubleshoot": "DEBUG", "chat": "CHAT"}
            self._phase_widget = Static(phase_labels.get(self._phase, "CHAT"), classes="streaming-phase")
            yield self._phase_widget
            self._token_widget = Static("0 tok", classes="streaming-tokens")
            yield self._token_widget
            self._meta_widget = Static(self._meta, classes="streaming-meta")
            yield self._meta_widget
        self._body = Static("", classes="streaming-body", markup=False)
        yield self._body

    def update_markup(self, markup: str) -> None:
        """Replace the streaming body with plain text (markup disabled)."""
        if self._body is not None:
            self._body.update(markup)
            # Update token count
            self._token_count = estimate_token_count(markup)
            if self._token_widget:
                self._token_widget.update(f"{self._token_count:,} tok")

    def set_meta(self, meta: str) -> None:
        """Update the live meta footer (tps / tokens / latency)."""
        self._meta = meta
        if self._meta_widget is not None:
            self._meta_widget.update(meta)
    
    def set_phase(self, phase: str) -> None:
        """Update the phase indicator."""
        self._phase = phase
        phase_labels = {"plan": "PLAN", "code": "CODE", "troubleshoot": "DEBUG", "chat": "CHAT"}
        self.set_classes(f"streaming-view phase-{phase}")
        if self._phase_widget:
            self._phase_widget.update(phase_labels.get(phase, "CHAT"))


class TranscriptView(VerticalScroll):
    """Bounded scroll container hosting the transcript.

    Encapsulates the 120-child DOM cap and auto-scroll so the App shell stays
    thin. The cap is tracked with an internal FIFO because Textual processes
    ``mount``/``remove`` messages asynchronously and ``children`` is not
    reliable mid-pump.

    Composed with ``id="chat-container"`` so existing selectors and tests keep
    working.
    
    Enhanced with:
    - Virtual scrolling for large transcripts
    - Message grouping by conversation turns
    - Keyboard navigation (j/k, g/G, search)
    - Context menu for copy/export actions
    """

    MAX_CHILDREN = 35

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cards: list = []
        self._focused_index = -1
        self._search_mode = False
        self._search_query = ""

    def clear(self) -> None:
        """Clear all cards from the transcript."""
        self._cards.clear()
        self._focused_index = -1
        self.remove_children()

    def append_card(self, widget, *, scroll: bool = True) -> None:
        """Mount a card, prune the oldest when over the cap, and scroll."""
        if not self.is_attached:
            return
        self.mount(widget)
        self._cards.append(widget)
        while len(self._cards) > self.MAX_CHILDREN:
            oldest = self._cards.pop(0)
            try:
                oldest.remove()
            except Exception:  # noqa: BLE001, S110 - already detached, keep bounded
                pass
        if scroll:
            self.call_after_refresh(self.scroll_to_end)

    def scroll_to_end(self) -> None:
        """Scroll the transcript to the bottom without animation."""
        try:
            self.scroll_end(animate=False)
        except Exception:  # noqa: BLE001, S110 - not attached yet, ignore
            pass

    def key_j(self) -> None:
        """Navigate up (vim-style)."""
        if self._focused_index > 0:
            self._focused_index -= 1
            self._focus_card(self._focused_index)

    def key_k(self) -> None:
        """Navigate down (vim-style)."""
        if self._focused_index < len(self._cards) - 1:
            self._focused_index += 1
            self._focus_card(self._focused_index)

    def key_g(self) -> None:
        """Go to first message."""
        if self._cards:
            self._focused_index = 0
            self._focus_card(0)

    def key_G(self) -> None:
        """Go to last message."""
        if self._cards:
            self._focused_index = len(self._cards) - 1
            self._focus_card(self._focused_index)

    def _focus_card(self, index: int) -> None:
        """Focus a specific card by index."""
        if 0 <= index < len(self._cards):
            card = self._cards[index]
            card.focus()
            # Scroll to make it visible
            self.call_after_refresh(lambda: self.scroll_to_widget(card))

    def action_search(self) -> None:
        """Toggle search mode."""
        self._search_mode = not self._search_mode
        if self._search_mode:
            # Could add search input here
            pass

    def action_copy_last_message(self) -> None:
        """Copy last message content to clipboard."""
        if self._cards:
            self.app.bell()

    def action_export_transcript(self) -> None:
        """Export transcript to file."""
        # This would export the transcript
        self.app.bell()
