"""Tool call cards for the Torchlight TUI.

Phase 2 of the UI-improvements plan: every tool call renders as a
status-aware card with a risk badge, elapsed time, collapsible params and
truncated output. Cards start in a ``running`` state (mounted as soon as a
``<tool_call>`` marker streams in) and flip to ``ok`` / ``error`` / ``denied``
when the engine reports the matching step.

Styled with theme variables only (CSS-first, no ``styles.set``).
"""

from __future__ import annotations

import time

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static

from core.tools.classification import AUTO, CONFIRM, REVIEW, classify_tool

try:
    from textual.widgets import Collapsible
except ImportError:  # pragma: no cover - older Textual
    Collapsible = None


# ── Risk tier presentation ───────────────────────────────────────────────

RISK_META = {
    AUTO: ("🔍", "AUTO", "risk-auto"),
    CONFIRM: ("⚠️", "CONFIRM", "risk-confirm"),
    REVIEW: ("🛑", "REVIEW", "risk-review"),
}

TOOL_ICONS = {
    "READ_FILE": "📄",
    "GREP": "🔎",
    "READ_SYMBOLS": "🧩",
    "SEARCH_AST": "🌳",
    "LIST_DIR": "📂",
    "WRITE_FILE": "✏️",
    "EDIT_FILE": "✏️",
    "RUN_COMMAND": "⚙️",
    "INSPECT_WEB": "🌐",
    "WEB_FETCH": "🌐",
    "WEB_SEARCH": "🔍",
    "SAVE_MEMORY": "💾",
    "UPDATE_TASK_GRAPH": "🕸️",
    "GIT": "🔀",
    "FORMAT_CODE": "✨",
    "VERIFY": "✅",
}

STATUS_GLYPHS = {
    "running": "⏳",
    "ok": "✓",
    "error": "✗",
    "denied": "⚠️",
}


def risk_for_tool(tool_name: str, args: dict | None = None) -> str:
    """Risk tier for a tool call, mirroring the shared classification module."""
    return classify_tool(tool_name, args or {})


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
    ):
        if key in args and args[key] not in (None, ""):
            val = str(args[key])
            if len(val) > 200:
                val = val[:200] + "..."
            lines.append(f"{key}: {val}")
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


class ToolCallCard(Container):
    """A status-aware tool call card.

    Header shows the risk-tier icon, tool name, risk badge, target, elapsed
    time and status glyph. Params and output live in a collapsible section
    populated on completion (kept collapsed on success, expanded on
    error/denied so the failure is glanceable).
    """

    DEFAULT_CSS = """
    ToolCallCard {
        height: auto;
        width: 1fr;
        layout: vertical;
        margin: 0 0 1 0;
        background: $surface;
        border: round $panel;
        border-left: thick $accent;
    }

    ToolCallCard.risk-auto {
        border-left: thick $success;
    }

    ToolCallCard.risk-confirm {
        border-left: thick $warning;
    }

    ToolCallCard.risk-review {
        border-left: thick $error;
    }

    ToolCallCard > Horizontal.tool-card-header {
        height: 1;
        align: left middle;
        padding: 0 1;
        background: $panel;
    }

    Static.tool-card-name {
        width: auto;
        color: $foreground;
        text-style: bold;
    }

    Static.risk-badge {
        width: auto;
        margin: 0 0 0 1;
        padding: 0 1;
        text-style: bold;
    }

    Static.risk-badge.risk-auto {
        color: $success;
    }

    Static.risk-badge.risk-confirm {
        color: $warning;
    }

    Static.risk-badge.risk-review {
        color: $error;
    }

    Static.tool-card-target {
        width: 1fr;
        color: $text-muted;
        padding: 0 1;
        text-overflow: ellipsis;
    }

    Static.tool-card-time {
        width: auto;
        color: $foreground-muted;
    }

    Static.tool-card-status {
        width: auto;
        margin: 0 0 0 1;
    }

    Static.tool-card-status.running {
        color: $accent;
        text-style: bold blink;
    }

    Static.tool-card-status.ok {
        color: $success;
        text-style: bold;
    }

    Static.tool-card-status.error {
        color: $error;
        text-style: bold;
    }

    Static.tool-card-status.denied {
        color: $warning;
        text-style: bold;
    }

    Collapsible.tool-card-section > CollapsibleContents > Static.tool-card-body,
    Static.tool-card-body {
        width: 1fr;
        color: $foreground;
        padding: 1 2;
    }

    ToolCallCard:hover {
        background-tint: $foreground 3%;
    }
    """

    def __init__(
        self,
        tool_name: str,
        *,
        risk: str | None = None,
        args: dict | None = None,
        target: str = "",
        id: str | None = None,
    ) -> None:
        risk = risk or risk_for_tool(tool_name, args)
        super().__init__(classes=f"tool-card risk-{risk}", id=id)
        self._tool_name = tool_name or "TOOL"
        self._risk = risk
        self._target = target or self._target_from_args(args)
        self._status = "running"
        self._elapsed_ms: float | None = None
        self._started_at = time.monotonic()
        self._risk_widget: Static | None = None
        self._time_widget: Static | None = None
        self._status_widget: Static | None = None

    @staticmethod
    def _target_from_args(args: dict | None) -> str:
        if not args:
            return ""
        for key in ("path", "file_path", "command", "cmd", "query", "url", "pattern"):
            if key in args and args[key] not in (None, ""):
                return str(args[key])
        return ""

    def compose(self) -> ComposeResult:
        risk_icon, risk_label, _risk_cls = RISK_META.get(self._risk, RISK_META[CONFIRM])
        tool_icon = TOOL_ICONS.get(self._tool_name, "🔧")
        with Horizontal(classes="tool-card-header"):
            yield Static(
                f"{risk_icon} {tool_icon} {escape(self._tool_name)}",
                classes="tool-card-name",
            )
            self._risk_widget = Static(
                risk_label, classes=f"risk-badge risk-{self._risk}"
            )
            yield self._risk_widget
            yield Static(escape(self._target), classes="tool-card-target")
            self._time_widget = Static("", classes="tool-card-time")
            yield self._time_widget
            self._status_widget = Static(
                STATUS_GLYPHS["running"], classes="tool-card-status running"
            )
            yield self._status_widget

    # ── Status / timing ──────────────────────────────────────────────────

    def _render_time(self) -> None:
        if self._time_widget is None:
            return
        if self._elapsed_ms is None:
            self._time_widget.update("")
            return
        ms = int(self._elapsed_ms)
        self._time_widget.update(f"{ms / 1000:.1f}s" if ms >= 1000 else f"{ms}ms")

    def _set_status(self, status: str) -> None:
        self._status = status if status in STATUS_GLYPHS else "ok"
        if self._status_widget is not None:
            self._status_widget.update(STATUS_GLYPHS.get(self._status, "✓"))
            self._status_widget.set_classes(f"tool-card-status {self._status}")

    def update_running(self) -> None:
        """Refresh the elapsed counter while the tool is still running."""
        if self._status == "running":
            self._elapsed_ms = (time.monotonic() - self._started_at) * 1000
            self._render_time()

    @staticmethod
    def _status_from_result(result: str) -> str:
        if not result:
            return "ok"
        res_lower = result.lower()
        if "denied" in res_lower:
            return "denied"
        if result.startswith(("Error", "❌")):
            return "error"
        return "ok"

    def complete(
        self,
        *,
        result: str = "",
        args: dict | None = None,
        thinking: str = "",
        elapsed_ms: float | None = None,
        status: str | None = None,
    ) -> None:
        """Flip the card from running to done and fill params + output.

        Re-derives the risk badge once the full args are known (a RUN_COMMAND
        can escalate to REVIEW once its command is parsed).
        """
        new_risk = risk_for_tool(self._tool_name, args)
        if new_risk != self._risk:
            self._risk = new_risk
            self.set_classes(f"tool-card risk-{new_risk}")
            if self._risk_widget is not None:
                _icon, label, _cls = RISK_META.get(new_risk, RISK_META[CONFIRM])
                self._risk_widget.update(label)
                self._risk_widget.set_classes(f"risk-badge risk-{new_risk}")

        if elapsed_ms is None:
            elapsed_ms = (time.monotonic() - self._started_at) * 1000
        self._elapsed_ms = elapsed_ms
        self._render_time()

        if status is None:
            status = self._status_from_result(result)
        self._set_status(status)

        body_parts = []
        if thinking:
            body_parts.append(
                f"[dim magenta]💭 Rationale:[/]\n[dim]{escape(thinking)}[/]"
            )
        arg_summary = summarize_args(args)
        if arg_summary:
            body_parts.append(f"[dim]Params:[/]\n[dim]{escape(arg_summary)}[/]")
        if result:
            body_parts.append(f"[bold]Result:[/]\n{escape(truncate_output(result))}")
        if body_parts:
            self._mount_sections(body_parts, expand=status in ("error", "denied"))

    def _mount_sections(self, body_parts: list[str], *, expand: bool) -> None:
        if not self.is_attached:
            return
        body = "\n\n".join(body_parts)
        if Collapsible is not None:
            section = Collapsible(
                Static(body, classes="tool-card-body"),
                title="Details",
                collapsed=not expand,
                classes="tool-card-section",
            )
        else:
            section = Static(body, classes="tool-card-body")
        try:
            self.mount(section)
        except Exception:  # noqa: BLE001, S110 - already detached, ignore
            pass
