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
from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static

def escape_markup(text: str) -> str:
    """Safely escape text for Textual markup parsing."""
    if not text:
        return ""
    return str(text).replace("\\", "\\\\").replace("[", "\\[")

from core.tools.classification import AUTO, CONFIRM, REVIEW, classify_tool

try:
    from textual.widgets import Collapsible
except ImportError:  # pragma: no cover - older Textual
    Collapsible = None


# ── Risk tier presentation ───────────────────────────────────────────────

RISK_META = {
    AUTO: ("", "AUTO", "risk-auto"),
    CONFIRM: ("", "CONFIRM", "risk-confirm"),
    REVIEW: ("", "REVIEW", "risk-review"),
}

TOOL_ICONS: dict[str, str] = {}

STATUS_GLYPHS = {
    "running": "...",
    "ok": "OK",
    "error": "ERR",
    "denied": "DENIED",
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
        "task_id",
        "task",
        "description",
        "subtask",
        "intent",
        "focus",
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
        border: solid $panel;
        border-left: solid $accent;
    }

    ToolCallCard.risk-auto {
        border-left: solid $success;
    }

    ToolCallCard.risk-confirm {
        border-left: solid $warning;
    }

    ToolCallCard.risk-review {
        border-left: solid $error;
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
        margin: 0 1 0 0;
        padding: 0 0;
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


    ToolCallCard.status-ok,
    ToolCallCard.risk-done {
        border-left: solid $success;
    }

    ToolCallCard.status-error,
    ToolCallCard.risk-error {
        border-left: solid $error;
    }

    ToolCallCard.status-denied,
    ToolCallCard.risk-denied {
        border-left: solid $warning;
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

    Static.tool-card-copy {
        width: auto;
        min-width: 3;
        color: $text-muted;
        background: $surface;
        margin: 0 0 0 1;
        padding: 0 1;
        text-align: center;
    }

    Static.tool-card-copy:hover {
        background: $accent;
        color: $background;
        text-style: bold;
    }

    Collapsible.tool-card-section {
        background: transparent;
        border: none;
        border-top: solid $panel;
        margin: 0;
        padding: 0;
    }

    Collapsible.tool-card-section > CollapsibleTitle {
        background: $panel;
        color: $text-muted;
        padding: 0 1;
        height: 1;
    }

    Collapsible.tool-card-section > CollapsibleContents {
        background: transparent;
        padding: 0;
        margin: 0;
    }

    Collapsible.tool-card-section > CollapsibleContents > Static.tool-card-body,
    Static.tool-card-body {
        width: 1fr;
        max-height: 20;
        overflow-y: auto;
        color: $foreground;
        padding: 1 2;
        margin: 0;
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
        self._args = args or {}
        self._result = ""
        self._target = target or self._target_from_args(self._tool_name, args)
        self._status = "running"
        self._elapsed_ms: float | None = None
        self._started_at = time.monotonic()
        self._risk_widget: Static | None = None
        self._target_widget: Static | None = None
        self._time_widget: Static | None = None
        self._status_widget: Static | None = None

    @classmethod
    def _target_from_args(cls, arg1: Any = None, arg2: dict | None = None) -> str:
        """Derive target file path, AST search query, or command from tool args."""
        tool_name = ""
        args = {}
        if isinstance(arg1, str) and isinstance(arg2, dict):
            tool_name = arg1.upper()
            args = arg2
        elif isinstance(arg1, dict):
            args = arg1
        elif isinstance(arg2, dict):
            args = arg2

        if not args:
            return ""

        # 1. AST Search Queries / Symbol extraction
        if tool_name in ("SEARCH_AST", "READ_SYMBOLS") or "query" in args:
            query = args.get("query") or args.get("symbol") or args.get("pattern") or args.get("node_type")
            path = args.get("path") or args.get("file_path") or args.get("file")
            if query and path:
                return f"{path} :: {query}"
            if query:
                return f"query: {query}"
            if path:
                return str(path)

        # 2. GREP Search
        if tool_name == "GREP" or "pattern" in args:
            pat = args.get("pattern") or args.get("query")
            p = args.get("path") or args.get("search_path")
            if pat and p:
                return f"/{pat}/ in {p}"
            if pat:
                return f"/{pat}/"

        # 3. File Operations (READ_FILE, WRITE_FILE, EDIT_FILE)
        path = (
            args.get("path")
            or args.get("file_path")
            or args.get("file")
            or args.get("target")
            or args.get("filename")
        )
        if path:
            target = str(path)
            start_line = args.get("start_line")
            end_line = args.get("end_line")
            symbol = args.get("symbol")
            if ":" not in target:
                if start_line is not None and end_line is not None:
                    target += f":L{start_line}-L{end_line}"
                elif start_line is not None:
                    target += f":L{start_line}"
                elif symbol:
                    target += f":{symbol}"

            task_id = args.get("task_id") or args.get("task")
            desc = (
                args.get("description")
                or args.get("subtask")
                or args.get("intent")
                or args.get("focus")
                or args.get("summary")
            )
            if task_id and desc:
                target += f" — [{task_id}] {desc}"
            elif desc:
                target += f" — {desc}"
            elif task_id:
                target += f" — [{task_id}]"

            return target

        # 4. Commands, URLs, Keys, Goals
        for key in ("command", "cmd", "query", "url", "pattern", "task_id", "key", "action"):
            if key in args and args[key] not in (None, ""):
                val = str(args[key])
                desc = (
                    args.get("description")
                    or args.get("subtask")
                    or args.get("intent")
                    or args.get("focus")
                )
                tid = args.get("task_id") or args.get("task")
                if key not in ("task_id", "query") and desc:
                    if tid and tid != val:
                        return f"{val} — [{tid}] {desc}"
                    return f"{val} — {desc}"
                return val
        return ""

    def compose(self) -> ComposeResult:
        risk_icon, risk_label, _risk_cls = RISK_META.get(self._risk, RISK_META[CONFIRM])
        tool_icon = TOOL_ICONS.get(self._tool_name, "")
        header_parts = [p for p in (risk_icon, tool_icon, escape_markup(self._tool_name)) if p]
        header_text = " ".join(header_parts)
        with Horizontal(classes="tool-card-header"):
            self._risk_widget = Static(
                risk_label, classes=f"risk-badge risk-{self._risk}"
            )
            yield self._risk_widget
            yield Static(
                header_text,
                classes="tool-card-name",
            )
            self._target_widget = Static(self._target, classes="tool-card-target", markup=False)
            yield self._target_widget
            self._time_widget = Static("", classes="tool-card-time")
            yield self._time_widget
            self._status_widget = Static(
                STATUS_GLYPHS["running"], classes="tool-card-status running"
            )
            yield self._status_widget
            copy_btn = Static("❐", classes="tool-card-copy", markup=False)
            copy_btn.tooltip = "Copy tool output"
            yield copy_btn


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
            self._status_widget.update(STATUS_GLYPHS.get(self._status, "OK"))
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
        if result.startswith(("Error", "ERR", "FAIL")):
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

        if args:
            self._args = args
            updated_target = self._target_from_args(self._tool_name, args)
            if updated_target and (not self._target or self._target != updated_target):
                self._target = updated_target
                if self._target_widget is not None:
                    self._target_widget.update(self._target)

        if result:
            self._result = result

        if status is None:
            status = self._status_from_result(result)
        self._set_status(status)

        if status == "ok":
            self.set_classes(f"tool-card risk-{self._risk} status-ok")
        elif status == "error":
            self.set_classes(f"tool-card risk-{self._risk} status-error")
        elif status == "denied":
            self.set_classes(f"tool-card risk-{self._risk} status-denied")

        body_parts = []

        if thinking:
            body_parts.append(
                f"[dim magenta]Rationale:[/]\n[dim]{escape_markup(thinking)}[/]"
            )
        arg_summary = summarize_args(args)
        if arg_summary:
            body_parts.append(f"[dim]Params:[/]\n[dim]{escape_markup(arg_summary)}[/]")
        if result:
            body_parts.append(f"[bold]Result:[/]\n{escape_markup(truncate_output(result))}")
        if body_parts:
            output_lines = len(result.splitlines()) if result else 0
            # Short outputs (<= 10 lines) default to expanded; longer outputs (> 10 lines) default to collapsed
            should_expand = (output_lines <= 10) or (status in ("error", "denied"))
            self._mount_sections(body_parts, expand=should_expand)


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

    @on(events.Click, ".tool-card-copy")
    def on_copy_click(self, event: events.Click) -> None:
        event.stop()
        self.action_copy()

    def action_copy(self) -> None:
        text = self._result or self._target or summarize_args(self._args)
        if text:
            try:
                from rlm_optimized.tui_app import copy_to_clipboard

                if copy_to_clipboard(text):
                    self.notify("Tool output copied to clipboard", timeout=1.5)
                else:
                    self.notify("Failed to copy tool output", severity="error", timeout=2)
            except Exception:
                pass


class TestVerificationCard(Container):
    """Card rendering for live test verification and web inspection results."""

    DEFAULT_CSS = """
    TestVerificationCard {
        width: 1fr;
        height: auto;
        border: solid $panel;
        border-left: solid $success;
        background: $surface;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    TestVerificationCard.test-failed {
        border-left: solid $error;
    }

    TestVerificationCard > Horizontal.test-header {
        height: 1;
        width: 1fr;
    }

    TestVerificationCard Static.test-title {
        width: 1fr;
        text-style: bold;
    }

    TestVerificationCard Static.test-duration {
        width: auto;
        color: $foreground-muted;
    }

    TestVerificationCard Static.test-body {
        width: 1fr;
        height: auto;
        color: $foreground;
        padding: 0 1;
    }
    """

    def __init__(self, data: dict, *, id: str | None = None) -> None:
        self.data = data or {}
        all_passed = bool(self.data.get("all_passed", False))
        cls = "test-card " + ("test-passed" if all_passed else "test-failed")
        super().__init__(classes=cls, id=id)

    def compose(self) -> ComposeResult:
        cmd = self.data.get("command", "Tests")
        passed = self.data.get("passed", 0)
        failed = self.data.get("failed", 0)
        duration_ms = self.data.get("duration_ms", 0.0)
        all_passed = bool(self.data.get("all_passed", False))

        if all_passed:
            title = f"[bold green]✓ 🧪 VERIFICATION PASSED:[/] [cyan]{escape(str(cmd))}[/] ({passed} passed)"
        else:
            title = f"[bold red]❌ 🧪 TEST FAILURE:[/] [cyan]{escape(str(cmd))}[/] ({failed} failed, {passed} passed)"

        with Horizontal(classes="test-header"):
            yield Static(title, classes="test-title")
            yield Static(f"[dim]{duration_ms:.0f}ms[/]", classes="test-duration")

        stdout = (self.data.get("stdout") or "").strip()
        stderr = (self.data.get("stderr") or "").strip()
        body_text = ""
        if not all_passed and stderr:
            body_text = f"[bold red]Failure Details:[/]\n{escape(stderr[:600])}"
        elif not all_passed and stdout:
            body_text = f"[bold red]Failure Details:[/]\n{escape(stdout[:600])}"
        elif stdout and ("FPS" in stdout or "Canvas" in stdout or "Playwright" in stdout):
            body_text = f"[dim]{escape(stdout[:300])}[/]"

        if body_text:
            yield Static(body_text, classes="test-body")
