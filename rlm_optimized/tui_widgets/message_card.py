"""Message turn card widget with syntax highlighting, badges, and tool call details."""

from __future__ import annotations

import os
from typing import Optional

from rich.markup import escape
from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Markdown, Static

try:
    from textual.widgets import Collapsible
except ImportError:  # pragma: no cover - older Textual
    Collapsible = None

from core.tools.classification import CONFIRM
from rlm_optimized.tui_widgets.tool_card import ToolCallCard
from rlm_optimized.tui_widgets.image_card import ImageAttachmentCard
from rlm_optimized.tui_widgets.transcript_utils import (
    ROLE_LABELS,
    RISK_META,
    estimate_token_count,
    summarize_args,
    truncate_output,
    render_markdown_with_syntax_highlighting,
)


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
