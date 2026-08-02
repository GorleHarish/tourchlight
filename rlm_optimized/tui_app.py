"""
Torchlight Agent — Codex / Tiny-Brain 2 Style IDE TUI (Textual)
Full-featured IDE coding agent experience with sidebar, file tree, memory meter, and modal approvals.
"""

from __future__ import annotations
import os
import re
import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import Optional
import hashlib

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Vertical, Horizontal, Container
from textual.widgets import (
    Header,
    Footer,
    Static,
    Input,
    Button,
    Label,
    DirectoryTree,
    ProgressBar,
    TextArea,
    ListItem,
    ListView,
)

try:
    from textual.widgets import Collapsible
except ImportError:
    Collapsible = None
from textual.screen import ModalScreen
from textual.theme import Theme
from textual.binding import Binding
from textual import work, on

from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.markup import escape

import sys
import subprocess
from rlm_optimized.config import (
    MODEL_NAME,
    MAX_RECURSION_DEPTH,
    PROVIDER,
    CHIP_NAME,
    TOTAL_RAM_GB,
    IS_8GB_DEVICE,
    CTX_SIZE,
    normalize_model_name,
    list_available_models,
    is_port_in_use,
    LMSTUDIO_BASE_URL,
    LMSTUDIO_API_KEY,
    fetch_provider_models,
)
from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized, Step
from core.tools.classification import CONFIRM, REVIEW
from rlm_optimized.memory_monitor import format_memory_status, is_memory_safe
from rlm_optimized.tui_widgets.format import build_plan_text
from rlm_optimized.tui_widgets.transcript import (
    MessageCard,
    StreamingView,
    TranscriptView,
    card_meta_for,
)
from rlm_optimized.tui_widgets.thinking_block import thinking_block
from rlm_optimized.tui_widgets.tool_card import ToolCallCard
from rlm_optimized.tui_widgets.trajectory_rail import TrajectoryRail
from rlm_optimized.tui_widgets.diff_view import (
    DiffView,
    build_diff_preview,
    diff_markup,
)
from rlm_optimized.tui_widgets.status_bar import StatusBar
from rlm_optimized.tui_widgets.command_palette import (
    CommandPalette,
    PaletteResult,
    PromptTextArea,
)
from rlm_optimized.tui_widgets.file_tree import GitFileTree

STATE_FILE = os.path.expanduser("~/.torchlight_state.json")


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard across macOS, Linux, and Windows."""
    if not text:
        return False
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception:
        pass

    if sys.platform == "darwin":
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
            return True
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        for cmd in [["xclip", "-selection", "clipboard"], ["wl-copy"], ["xsel", "-b"]]:
            try:
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                p.communicate(text.encode("utf-8"))
                return True
            except Exception:
                pass
    elif sys.platform == "win32":
        try:
            p = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-16le"))
            return True
        except Exception:
            pass
    return False


def load_last_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_last_state(data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        state = load_last_state()
        state.update(data)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def _provider_runtime_info(provider_key: str) -> tuple[int, bool]:
    """Return (port, externally_managed) for a given provider key.

    externally_managed=True means Torchlight does not own the server process
    (the person starts LM Studio / `ollama serve` themselves), so the sidebar
    Start/Restart buttons should just re-check connectivity instead of trying
    to launch a bundled script.
    """
    if provider_key in ("llama-cpp", "turbo", "turboquant", "mlx"):
        return 8080, False
    if provider_key == "lmstudio":
        return 1234, True
    if provider_key == "ollama":
        return 11434, True
    return 0, True  # cloud providers — no local port to track


# ── Approval Modal ──────────────────────────────────────────────────────


class ApprovalModal(ModalScreen[bool]):
    """Modal dialog for tool & file modification approval in Cyberpunk Sci-Fi style."""

    BINDINGS = [
        ("y", "allow", "Allow"),
        ("Y", "allow", "Allow"),
        ("n", "deny", "Deny"),
        ("N", "deny", "Deny"),
        ("escape", "deny", "Deny"),
    ]

    DEFAULT_CSS = """
    ApprovalModal {
        align: center middle;
    }
    #approval-dialog {
        width: 76;
        max-height: 85%;
        border: heavy $warning;
        background: #121614;
        padding: 1 2;
    }
    #approval-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    #approval-tool {
        margin-bottom: 1;
        color: $foreground;
    }
    #approval-args {
        color: $success;
        max-height: 6;
        overflow-y: auto;
        border: solid $panel;
        background: #0A0D0B;
        padding: 1;
    }
    #approval-diff-label {
        margin-top: 1;
        margin-bottom: 1;
        color: $warning;
        text-style: bold;
    }
    #approval-diff {
        color: $foreground;
        max-height: 16;
        overflow-y: auto;
        border: solid $panel;
        background: #0A0D0B;
        padding: 1;
    }
    #approval-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    #approval-buttons Button {
        margin: 0 2;
        min-width: 18;
    }
    #approval-hint {
        text-align: center;
        color: $foreground-muted;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        tool_name: str,
        risk: str,
        tool_args: dict,
        *,
        diff_entries: list | None = None,
        diff_path: str = "",
    ):
        super().__init__()
        self.tool_name = tool_name
        self.risk = risk
        self.tool_args = tool_args
        self.diff_entries = diff_entries or []
        self.diff_path = diff_path

    def compose(self) -> ComposeResult:
        risk_icon = "🛑" if self.risk == REVIEW else "⚠️ "
        risk_label = (
            f"RISK_LEVEL: {self.risk.upper()}" if self.risk else "RISK_LEVEL: CONFIRM"
        )

        with Vertical(id="approval-dialog"):
            yield Static(
                f"{risk_icon} {risk_label}\nModification requires manual operational validation.",
                id="approval-title",
            )
            yield Static(
                f"Action Payload: [bold bright_yellow]{escape(self.tool_name)}[/]",
                id="approval-tool",
            )

            display_args = dict(self.tool_args) if self.tool_args else {}
            if self.tool_name == "WRITE_FILE" and "content" in display_args:
                display_args["content"] = (
                    f"... [{len(str(display_args['content']))} chars of code hidden]"
                )
            elif self.tool_name == "EDIT_FILE":
                if "old_text" in display_args:
                    display_args["old_text"] = (
                        f"... [{len(str(display_args['old_text']))} chars hidden]"
                    )
                if "new_text" in display_args:
                    display_args["new_text"] = (
                        f"... [{len(str(display_args['new_text']))} chars hidden]"
                    )

            args_str = json.dumps(display_args, indent=2)
            if len(args_str) > 4000:
                args_str = args_str[:4000] + "\n... [Arguments Truncated]"
            yield Static(escape(args_str), id="approval-args")
            if self.diff_entries:
                yield Static(
                    f"⬇ DIFF PREVIEW — {escape(self.diff_path or 'file')}",
                    id="approval-diff-label",
                )
                yield Static(
                    diff_markup(self.diff_entries, max_lines=120),
                    id="approval-diff",
                )
            with Horizontal(id="approval-buttons"):
                yield Button("APPROVE (Y)", classes="btn-gold", id="allow-btn")
                yield Button("REJECT (N)", classes="btn-outline", id="deny-btn")
            yield Static(
                "[dim]Press Y to approve, N or Esc to reject[/]", id="approval-hint"
            )

    def on_mount(self) -> None:
        try:
            self.set_focus(self.query_one("#allow-btn"))
        except Exception:
            pass

    def action_allow(self) -> None:
        self.dismiss(True)

    def action_deny(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#allow-btn")
    def on_allow(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#deny-btn")
    def on_deny(self) -> None:
        self.dismiss(False)


# ── Folder Picker Modal ──────────────────────────────────────────────────


class FolderPickerModal(ModalScreen[Optional[str]]):
    """Modal dialog for interactive visual folder selection across the entire computer."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    FolderPickerModal {
        align: center middle;
    }
    #picker-dialog {
        width: 86;
        height: 90%;
    }
    #picker-jumps {
        height: 3;
        align: center middle;
        margin-bottom: 1;
    }
    #picker-jumps Button {
        margin: 0 1;
        min-width: 12;
    }
    #picker-path {
        color: $success;
        margin-bottom: 1;
    }
    #picker-input {
        margin-bottom: 1;
    }
    #picker-tree {
        height: 1fr;
        margin-bottom: 1;
    }
    """

    def __init__(self, initial_path: str):
        super().__init__()
        self.selected_path = os.path.abspath(initial_path)
        self.root_path = "/" if os.path.exists("/") else os.path.expanduser("~")

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-dialog"):
            yield Static(
                "📂 Select Working Directory Folder (Computer Wide)", id="picker-title"
            )
            with Horizontal(id="picker-jumps"):
                yield Button("💻 Root (/)", variant="default", id="jump-root")
                yield Button("🏠 Home (~)", variant="default", id="jump-home")
                yield Button("🖥️ Desktop", variant="default", id="jump-desktop")
                yield Button("📁 Current", variant="default", id="jump-current")
            yield Input(
                placeholder="Or type/paste path directly...",
                value=self.selected_path,
                id="picker-input",
            )
            yield Static(f"Selected: {escape(self.selected_path)}", id="picker-path")
            yield DirectoryTree(self.root_path, id="picker-tree")
            with Horizontal(id="picker-buttons"):
                yield Button(
                    "✅ Select This Folder", variant="success", id="select-folder-btn"
                )
                yield Button("❌ Cancel", variant="error", id="cancel-folder-btn")

    @on(Input.Submitted, "#picker-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        target = os.path.abspath(os.path.expanduser(event.value.strip()))
        if os.path.isdir(target):
            self.selected_path = target
            self.query_one("#picker-path", Static).update(
                f"Selected: [bold green]{escape(self.selected_path)}[/]"
            )
            try:
                tree = self.query_one("#picker-tree", DirectoryTree)
                tree.path = target
            except Exception:
                pass
        else:
            self.query_one("#picker-path", Static).update(
                f"[bold red]Invalid directory:[/] {escape(target)}"
            )

    @on(DirectoryTree.DirectorySelected, "#picker-tree")
    def on_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        self.selected_path = str(event.path)
        try:
            self.query_one("#picker-path", Static).update(
                f"Selected: [bold green]{escape(self.selected_path)}[/]"
            )
            self.query_one("#picker-input", Input).value = self.selected_path
        except Exception:
            pass

    @on(Button.Pressed, "#jump-root")
    def on_jump_root(self) -> None:
        self._set_tree_path("/")

    @on(Button.Pressed, "#jump-home")
    def on_jump_home(self) -> None:
        self._set_tree_path(os.path.expanduser("~"))

    @on(Button.Pressed, "#jump-desktop")
    def on_jump_desktop(self) -> None:
        self._set_tree_path(os.path.expanduser("~/Desktop"))

    @on(Button.Pressed, "#jump-current")
    def on_jump_current(self) -> None:
        self._set_tree_path(self.selected_path)

    def _set_tree_path(self, path: str) -> None:
        target = os.path.abspath(os.path.expanduser(path))
        if os.path.exists(target):
            self.selected_path = target
            try:
                self.query_one("#picker-path", Static).update(
                    f"Selected: [bold green]{escape(self.selected_path)}[/]"
                )
                self.query_one("#picker-input", Input).value = self.selected_path
                tree = self.query_one("#picker-tree", DirectoryTree)
                tree.path = target
            except Exception:
                pass

    @on(Button.Pressed, "#select-folder-btn")
    def on_select(self) -> None:
        self.dismiss(self.selected_path)

    @on(Button.Pressed, "#cancel-folder-btn")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ── Model Picker Modal ──────────────────────────────────────────────────


class ModelPickerModal(ModalScreen[Optional[dict]]):
    """Modal dialog to visually pick models and engine providers."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    ModelPickerModal {
        align: center middle;
    }
    #model-dialog {
        width: 76;
        height: 80%;
    }
    """

    def __init__(self):
        super().__init__()
        self.models = list_available_models()
        self.lmstudio_models = fetch_provider_models(LMSTUDIO_BASE_URL)
        for model_id in self.lmstudio_models:
            self.models.append(
                {
                    "name": f"LM Studio: {model_id}",
                    "id": model_id,
                    "provider": "lmstudio",
                }
            )

    def compose(self) -> ComposeResult:
        with Vertical(id="model-dialog"):
            yield Label("🤖 Select Execution Model & Provider", id="model-title")
            with VerticalScroll():
                if self.lmstudio_models:
                    yield Static(
                        f"[bold]🟢 LM Studio[/] — [dim]{LMSTUDIO_BASE_URL}[/]\n"
                        f"[green]{len(self.lmstudio_models)} model(s) currently loaded[/]",
                        classes="model-card",
                    )
                else:
                    yield Static(
                        f"[bold]🔴 LM Studio[/] — [dim]{LMSTUDIO_BASE_URL}[/]\n"
                        "[yellow]No live models found. Open LM Studio, load a model, start its "
                        "Local Server, then reopen this picker (Ctrl+M) to refresh.[/]",
                        classes="model-card",
                    )
                for idx, m in enumerate(self.models):
                    btn_id = f"model-select-{idx}"
                    yield Static(
                        f"[bold text-white]{escape(m['name'])}[/]\n"
                        f"[dim]ID:[/] [cyan]{escape(m['id'])}[/]  │  [dim]Provider:[/] [yellow]{escape(m['provider'])}[/]",
                        classes="model-card",
                    )
                    yield Button(f"Use {m['name']}", id=btn_id, variant="primary")
            yield Button("Cancel", id="cancel-model-btn", variant="error")

    @on(Button.Pressed)
    def on_button(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-model-btn":
            self.dismiss(None)
            return
        if event.button.id and event.button.id.startswith("model-select-"):
            idx = int(event.button.id.replace("model-select-", ""))
            self.dismiss(self.models[idx])


# ── Copy Selection Modal ──────────────────────────────────────────────────


class CopySelectionModal(ModalScreen[Optional[str]]):
    """Modal dialog to select and copy specific messages, code blocks, or text turns."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    CopySelectionModal {
        align: center middle;
    }
    #copy-dialog {
        width: 84;
        height: 80%;
    }
    """

    def __init__(self, history: list[dict]):
        super().__init__()
        self.history = history

    def compose(self) -> ComposeResult:
        with Vertical(id="copy-dialog"):
            yield Label("📋 Select Message Turn or Code to Copy", id="copy-title")
            with VerticalScroll():
                if not self.history:
                    yield Static(
                        "[dim italic]No conversation turns available to select.[/]"
                    )
                else:
                    for idx, item in enumerate(reversed(self.history)):
                        role = item.get("role", "user")
                        content = item.get("content", "")
                        snippet = content[:150] + ("..." if len(content) > 150 else "")
                        role_icon = "💬 User" if role == "user" else "🤖 Assistant"
                        btn_id = f"copy-turn-{idx}"
                        yield Static(
                            f"[bold text-white]{role_icon}[/]\n"
                            f"[dim]{escape(snippet)}[/]",
                            classes="copy-item-card",
                        )
                        yield Button(
                            f"Copy {role_icon} Turn #{len(self.history) - idx}",
                            id=btn_id,
                            variant="primary",
                        )
            yield Button("Cancel", id="cancel-copy-btn", variant="error")

    @on(Button.Pressed)
    def on_button(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-copy-btn":
            self.dismiss(None)
            return
        if event.button.id and event.button.id.startswith("copy-turn-"):
            idx = int(event.button.id.replace("copy-turn-", ""))
            rev_history = list(reversed(self.history))
            if 0 <= idx < len(rev_history):
                self.dismiss(rev_history[idx]["content"])
            else:
                self.dismiss(None)


# ── Session Mode Picker Modal ──────────────────────────────────────────


class SessionModePickerModal(ModalScreen[Optional[str]]):
    """Modal dialog for selecting session execution mode (Chat vs Goal)."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    SessionModePickerModal {
        align: center middle;
    }
    #mode-dialog {
        width: 74;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }
    #mode-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #mode-tooltip {
        background: $boost;
        color: $text-muted;
        padding: 1;
        margin: 1 0;
        border: solid $accent;
    }
    .mode-btn {
        margin: 1 0;
        width: 1fr;
    }
    """

    def __init__(self, current_mode: str = "chat"):
        super().__init__()
        self.current_mode = current_mode

    def compose(self) -> ComposeResult:
        with Vertical(id="mode-dialog"):
            yield Static("⚙️ Select Torchlight Execution Mode", id="mode-title")
            yield Static(
                "Choose the operation mode for your session:\n\n"
                "• 💬 Chat Mode: Fast, lightweight Q&A and ad-hoc edits. No disk task tracking files created.\n"
                "• 🎯 Goal Mode: Continuous autonomous harness with disk-backed task graph (.torchlight/tasks.md).",
                id="mode-desc",
            )
            yield Static(
                "💡 Tooltip: Goal Mode initializes .torchlight/goal_spec.json and .torchlight/tasks.md "
                "to track multi-epoch sub-tasks across context resets and enforce verification gates.",
                id="mode-tooltip",
            )
            with Horizontal():
                yield Button(
                    "💬 Chat Mode (Lightweight)",
                    id="select-chat-btn",
                    variant="primary",
                    classes="mode-btn",
                )
                yield Button(
                    "🎯 Goal Mode (Harness)",
                    id="select-goal-btn",
                    variant="success",
                    classes="mode-btn",
                )
            yield Button("Cancel", id="cancel-mode-btn", variant="default")

    @on(Button.Pressed, "#select-chat-btn")
    def select_chat(self) -> None:
        self.dismiss("chat")

    @on(Button.Pressed, "#select-goal-btn")
    def select_goal(self) -> None:
        self.dismiss("goal")

    @on(Button.Pressed, "#cancel-mode-btn")
    def cancel_btn(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ── File Action Modal (OS Tool Selector) ────────────────────────────────


class FileActionModal(ModalScreen[str]):
    """Modal dialog presenting OS options when a file is selected in the Explorer tree."""

    BINDINGS = [
        ("escape", "action_cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    FileActionModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #file-action-dialog {
        width: 62;
        height: auto;
        padding: 1 2;
        background: $panel;
        border: thick $primary;
    }
    .file-action-title {
        text-align: center;
        margin-bottom: 1;
    }
    .file-action-btn {
        width: 100%;
        margin-top: 1;
    }
    """

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = os.path.abspath(file_path)
        self.filename = os.path.basename(self.file_path)

    def compose(self) -> ComposeResult:
        with Vertical(id="file-action-dialog"):
            yield Static(
                f"[bold cyan]📄 {escape(self.filename)}[/bold cyan]\n"
                f"[dim]{escape(self.file_path)}[/dim]",
                classes="file-action-title",
            )
            yield Button(
                "🚀 Open with System Default App",
                id="act-open-system",
                variant="primary",
                classes="file-action-btn",
            )
            yield Button(
                "📝 Open in VS Code / Editor",
                id="act-open-code",
                variant="success",
                classes="file-action-btn",
            )
            yield Button(
                "📋 Copy Absolute File Path",
                id="act-copy-path",
                variant="default",
                classes="file-action-btn",
            )
            yield Button(
                "✕ Cancel", id="act-cancel", variant="error", classes="file-action-btn"
            )

    @on(Button.Pressed, "#act-open-system")
    def action_open_system(self) -> None:
        self.dismiss("system")

    @on(Button.Pressed, "#act-open-code")
    def action_open_code(self) -> None:
        self.dismiss("code")

    @on(Button.Pressed, "#act-copy-path")
    def action_copy_path(self) -> None:
        self.dismiss("copy")

    @on(Button.Pressed, "#act-cancel")
    def action_cancel(self) -> None:
        self.dismiss("cancel")


# ── Agent Status & Telemetry Modal ──────────────────────────────────────


class AgentStatusModal(ModalScreen[None]):
    """Modal dialog for complete visibility into background agent actions & status telemetry."""

    BINDINGS = [
        ("escape", "dismiss_modal", "Close"),
        ("ctrl+a", "dismiss_modal", "Close"),
        ("c", "clear_logs", "Clear Logs"),
    ]

    DEFAULT_CSS = """
    AgentStatusModal {
        align: center middle;
    }
    #status-dialog {
        width: 88;
        height: 85%;
    }
    #status-metrics-row {
        height: 4;
        margin-bottom: 1;
    }
    .metric-badge {
        padding: 0 1;
    }
    .status-log-entry {
        margin-bottom: 1;
        padding-bottom: 1;
        border-bottom: solid $panel;
    }
    """

    def __init__(self, current_state: str, events: list[dict], meta_summary: str):
        super().__init__()
        self.current_state = current_state
        self.events = events
        self.meta_summary = meta_summary

    def compose(self) -> ComposeResult:
        with Vertical(id="status-dialog"):
            yield Static(
                "📡 Background Agent Action Telemetry & Live Inspector",
                id="status-title",
            )
            with Horizontal(id="status-metrics-row"):
                yield Static(
                    f"Current State:\n[bold cyan]{escape(self.current_state)}[/]",
                    classes="metric-badge",
                )
                yield Static(
                    f"Total Events Logged:\n[bold yellow]{len(self.events)}[/]",
                    classes="metric-badge",
                )
                yield Static(
                    f"System Context:\n[dim]{escape(self.meta_summary.splitlines()[0]) if self.meta_summary else ''}[/]",
                    classes="metric-badge",
                )
            yield Static(
                "📜 Real-Time Agent Action Log:", classes="sidebar-section-title"
            )
            with VerticalScroll(id="status-log-scroll"):
                # Autonomous Sub-agent Goal Telemetry if goal_spec exists
                try:
                    goal_spec_path = Path.cwd() / ".torchlight" / "goal_spec.json"
                    if goal_spec_path.exists():
                        with open(goal_spec_path, "r", encoding="utf-8") as f:
                            goal_data = json.load(f)
                        title = goal_data.get("title", "Goal")
                        tasks = goal_data.get("tasks", [])
                        tot = len(tasks)
                        ver = sum(1 for t in tasks if t.get("status") == "verified")
                        pct = (ver / tot * 100) if tot > 0 else 0
                        yield Static(
                            f"🎯 Autonomous Goal: [bold cyan]{escape(title)}[/] ({pct:.0f}% - {ver}/{tot} Verified)",
                            classes="status-log-entry",
                        )
                        for t in tasks:
                            st = t.get("status", "pending")
                            badge = (
                                "[bold green]✓ VERIFIED[/]"
                                if st == "verified"
                                else "[bold cyan]● RUNNING[/]"
                                if st == "in_progress"
                                else "[bold red]✗ FAILED[/]"
                                if st == "failed"
                                else "[yellow]⏳ PENDING[/]"
                            )
                            yield Static(
                                f"  {badge} [bold]{escape(str(t.get('id')))}[/bold]: {escape(str(t.get('description')))} (Attempts: {t.get('attempts', 0)}/{t.get('max_attempts', 3)})",
                                classes="status-log-entry",
                            )
                except Exception:
                    pass

                if not self.events:
                    yield Static(
                        "[dim italic]No agent background activity recorded yet.[/]"
                    )
                else:
                    for ev in reversed(self.events):
                        ts = ev.get("time", "")
                        state = ev.get("state", "INFO")
                        det = json.dumps(ev.get("details", {}))
                        if len(det) > 1000:
                            det = det[:1000] + " ...[Truncated]"
                        badge_style = (
                            "bold green"
                            if state in ("IDLE", "TOOL_DONE")
                            else "bold cyan"
                            if "TOOL" in state
                            else "bold yellow"
                        )
                        yield Static(
                            f"[{ts}] [{badge_style}]{state}[/]\n[dim]{escape(det)}[/]",
                            classes="status-log-entry",
                        )
            with Horizontal(id="status-buttons"):
                yield Button(
                    "🧹 Clear Logs (C)", variant="warning", id="clear-status-btn"
                )
                yield Button("❌ Close (Esc)", variant="primary", id="close-status-btn")

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    def action_clear_logs(self) -> None:
        self.events.clear()
        try:
            scroll = self.query_one("#status-log-scroll", VerticalScroll)
            scroll.remove_children()
            scroll.mount(Static("[dim italic]Logs cleared.[/]"))
        except Exception:
            pass

    @on(Button.Pressed, "#clear-status-btn")
    def on_clear(self) -> None:
        self.action_clear_logs()

    @on(Button.Pressed, "#close-status-btn")
    def on_close(self) -> None:
        self.dismiss(None)


# ── Main Codex IDE App ──────────────────────────────────────────────────

# ── Shortcuts & Help Modal ──────────────────────────────────────────────────


class ShortcutsHelpModal(ModalScreen[None]):
    """Modal dialog displaying keyboard shortcuts and slash commands."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    ShortcutsHelpModal {
        align: center middle;
    }
    #help-dialog {
        width: 76;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    #help-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    #help-close-btn {
        margin-top: 1;
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Static(
                "⌨️ Torchlight Codex - Shortcuts & Slash Commands", id="help-title"
            )
            help_md = """
### ⌨️ Keyboard Shortcuts
- **Enter** — Send prompt
- **Shift+Enter** — New line in prompt (multi-line input)
- **Ctrl+P** — Open Command Palette
- **Ctrl+N** — Compact Context
- **Ctrl+B** — Toggle Sidebar
- **Ctrl+T** — Cycle Theme
- **Ctrl+M** — Select Active Model
- **Ctrl+O** — Change Working Directory (Computer Wide)
- **Ctrl+H** — Open Shortcuts & Help Modal
- **Ctrl+A** — Open Telemetry & Status
- **Ctrl+X** — Copy Selection
- **Ctrl+Y** — Copy Entire Chat History
- **Ctrl+E** — Copy Last Response
- **Ctrl+L** — Clear Chat Screen
- **Ctrl+C** — Quit Application

### 🛠️ Slash Commands
- `/start` / `/restart` / `/stop` — Engine server control
- `/model <name>` — Switch active model
- `/cd <path>` — Change directory
- `/index` — Build AST Knowledge Graph
- `/status` — Open telemetry modal
- `/clear` — Clear chat history
- `/help` — Show shortcuts guide
"""
            yield Static(Markdown(help_md))
            yield Button("Close (Esc)", variant="primary", id="help-close-btn")

    @on(Button.Pressed, "#help-close-btn")
    def on_close(self) -> None:
        self.dismiss()


_TORCHLIGHT_THEME = Theme(
    name="torchlight",
    primary="#58a6ff",
    accent="#79c0ff",
    foreground="#f0f6fc",
    background="#0d1117",
    surface="#161b22",
    panel="#21262d",
    success="#7ee787",
    warning="#d29922",
    error="#f85149",
    dark=True,
    variables={
        "footer-key-foreground": "#79c0ff",
        "footer-background": "#161b22",
        "footer-description-foreground": "#8b949e",
        "block-hover-background": "#1c2128",
        "block-cursor-background": "#58a6ff",
        "block-cursor-foreground": "#0d1117",
        "input-cursor-background": "#f0f6fc",
        "input-cursor-foreground": "#0d1117",
        "input-selection-background": "#1f3a5f",
        "button-color-foreground": "#ffffff",
        "button-foreground": "#f0f6fc",
        "button-focus-text-style": "bold",
        "text-primary": "#f0f6fc",
        "text-success": "#7ee787",
        "text-warning": "#d29922",
        "text-error": "#f85149",
        "text": "#f0f6fc",
        "primary-muted": "#1a3a5c",
        "success-muted": "#1a3c2a",
        "warning-muted": "#3c2e1a",
        "error-muted": "#3c1a1a",
        "border": "#30363d",
        "border-blurred": "#21262d",
        "scrollbar": "#30363d",
        "scrollbar-hover": "#484f58",
        "scrollbar-active": "#58a6ff",
        "scrollbar-background": "#0d1117",
        "scrollbar-background-hover": "#161b22",
        "scrollbar-background-active": "#161b22",
        "scrollbar-corner-color": "#0d1117",
    },
)

_BLUEPRINT_LIGHT_THEME = Theme(
    name="blueprint-light",
    primary="#005599",
    accent="#0080ff",
    foreground="#0a2540",
    background="#ebf5fc",
    surface="#ffffff",
    panel="#ddeef9",
    success="#008855",
    warning="#d97706",
    error="#dc2626",
    dark=False,
    variables={
        "footer-key-foreground": "#005599",
        "footer-background": "#ddeef9",
        "footer-description-foreground": "#0a2540",
        "block-hover-background": "#d4e8f7",
        "block-cursor-background": "#005599",
        "block-cursor-foreground": "#ffffff",
        "input-cursor-background": "#005599",
        "input-cursor-foreground": "#ffffff",
        "input-selection-background": "#b3d7f2",
        "button-color-foreground": "#ffffff",
        "button-foreground": "#005599",
        "button-focus-text-style": "bold",
        "text-primary": "#005599",
        "text-success": "#008855",
        "text-warning": "#d97706",
        "text-error": "#dc2626",
        "text": "#0a2540",
        "primary-muted": "#b3d7f2",
        "success-muted": "#b8e6d2",
        "warning-muted": "#fde68a",
        "error-muted": "#fca5a5",
        "border": "#005599",
        "border-blurred": "#a0c4e2",
        "scrollbar": "#005599",
        "scrollbar-hover": "#0080ff",
        "scrollbar-active": "#003366",
        "scrollbar-background": "#ebf5fc",
        "scrollbar-background-hover": "#ddeef9",
        "scrollbar-background-active": "#ddeef9",
        "scrollbar-corner-color": "#ebf5fc",
    },
)


class TorchlightApp(App):
    """Codex / Tiny-Brain 2 Style Agent IDE TUI."""

    TITLE = "Torchlight Codex IDE"
    SUB_TITLE = "Autonomous Agent TUI"
    CSS_PATH = "tui_app.tcss"

    BINDINGS = [
        Binding("ctrl+h", "show_help", "Shortcuts & Help", show=True),
        Binding("ctrl+a", "toggle_status_modal", "Agent Telemetry", show=True),
        Binding("ctrl+x", "copy_selection", "Copy Selection", show=True),
        Binding("ctrl+y", "copy_chat", "Copy Chat", show=True),
        Binding("ctrl+p", "command_palette", "Command Palette", show=True),
        Binding("ctrl+e", "copy_last", "Copy Last", show=True),
        Binding("ctrl+o", "open_folder", "Open Folder", show=True),
        Binding("ctrl+m", "select_model", "Select Model", show=True),
        Binding("ctrl+g", "select_mode", "Session Mode", show=True),
        Binding("ctrl+b", "toggle_sidebar", "Toggle Sidebar", show=True),
        Binding("ctrl+t", "cycle_theme", "Theme", show=True),
        Binding("ctrl+n", "compact_context", "Compact Context", show=True),
        Binding("ctrl+r", "reset_session", "Reset REPL", show=False),
        Binding("ctrl+l", "clear", "Clear Chat", show=False),
        Binding("ctrl+c", "quit", "Quit", show=True),
    ]

    def __init__(
        self,
        engine: RLMEngineOptimized,
        model_name: str = "",
        provider_name: str = "",
        engine_port: int = 8080,
        externally_managed: bool = False,
    ):
        super().__init__()
        self.engine = engine
        self.model_name = model_name
        self.provider_name = provider_name
        self.engine_port = engine_port
        self.externally_managed = externally_managed
        self._streaming_text = ""
        self._streaming_widget: Optional[Static] = None
        self._streaming_view: Optional[StreamingView] = None
        self._pending_tool_card: Optional[ToolCallCard] = None
        self._pending_tool_name: Optional[str] = None
        self._trajectory_rail: Optional[TrajectoryRail] = None
        self._is_running = False
        self._show_sidebar = True
        self._chat_history: list = []
        self._agent_state: str = "IDLE"
        self._agent_events: list[dict] = []
        self._server_starting: bool = False
        self._open_tabs: dict[str, dict] = {}
        self._active_tab_path: Optional[str] = None
        self._split_editor_visible: bool = True
        self._stream_start_time: Optional[float] = None
        self._first_token_time: Optional[float] = None
        self._stream_token_count: int = 0
        self._live_tps: float = 0.0
        self._live_latency_ms: float = 0.0
        self._prewrite_snapshots: dict[str, str] = {}
        self._file_tree: Optional[GitFileTree] = None
        self._user_input: Optional[PromptTextArea] = None
        self._status_bar: Optional[StatusBar] = None

    def _handle_status_change(self, payload: dict) -> None:
        import datetime

        state = payload.get("state", "IDLE")
        details = payload.get("details", {})
        self._agent_state = state
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._agent_events.append(
            {
                "time": ts,
                "state": state,
                "details": details,
            }
        )
        if len(self._agent_events) > 200:
            self._agent_events.pop(0)

        if state == "REFINED":
            flaws = details.get("flaws", [])
            tool_name = details.get("tool_name", "")
            target = f" for {escape(tool_name)}" if tool_name else ""
            escaped_flaws = [escape(f) for f in flaws]
            flaw_str = (
                f" [dim](Fixed: {', '.join(escaped_flaws)})[/dim]" if flaws else ""
            )
            try:
                container = self.query_one("#chat-container")
                self._safe_mount(
                    container,
                    Static(
                        f" [bold green]✨ Refined proposal{target}[/bold green]{flaw_str}"
                    ),
                )
            except Exception:
                pass

        try:
            self.call_after_refresh(self.update_status_bar)
        except Exception:
            self.update_status_bar()

    def compose(self) -> ComposeResult:
        # Top HUD Header
        with Horizontal(id="top-hud-header"):
            yield Static("📐 CODEX_MANAGER_V1.0", id="hud-title")
            yield Static("FLOW: 24.2 t/s", id="hud-epoch", classes="hud-badge")
            yield Static("LATENCY: 12ms", id="hud-reverts", classes="hud-badge")
            yield Static("● LIVE: UTF-8", id="hud-uplink", classes="hud-badge-green")
            yield Static("", id="hud-spacer")
            mode_lbl = (
                "🎯 GOAL_MODE: ACTIVE"
                if getattr(self.engine, "execution_mode", None)
                and getattr(self.engine.execution_mode, "value", None) == "GOAL"
                else "💬 CHAT_MODE: ACTIVE"
            )
            mode_cls = "mode-badge-goal" if "GOAL" in mode_lbl else "mode-badge-chat"
            yield Button(mode_lbl, id="mode-toggle-btn", classes=mode_cls)
            yield Button(
                f"🤖 {escape(self.model_name)} ▾",
                id="input-model-badge",
                variant="default",
            )
            yield Button("🗜️ Compact", id="compact-btn", variant="warning")
            yield Button("⌨️ Help", id="help-btn", variant="default")

        with Horizontal(id="main-ide-container"):
            # 1. Left Explorer Sidebar (Files, System Health, Plan)
            with Vertical(id="explorer-sidebar"):
                yield Static(
                    "EXPLORER / BLUEPRINT WORKSPACE", classes="panel-header-title"
                )
                self._file_tree = GitFileTree(self.engine.project_root, id="file-tree")
                yield self._file_tree
                if Collapsible is not None:
                    yield Collapsible(
                        Static(
                            self._build_system_health_text(), id="system-health-panel"
                        ),
                        title="📊 Inference Speedometer & Memory",
                        collapsed=False,
                        id="health-collapsible",
                    )
                    yield Collapsible(
                        Static(self._build_plan_text(), id="plan-panel"),
                        title="📑 SESSION_LOGS & TASKS",
                        collapsed=False,
                        id="plan-collapsible",
                    )
                else:
                    yield Static("System Health", classes="sidebar-section-title")
                    yield Static(
                        self._build_system_health_text(), id="system-health-panel"
                    )

            # 2. Main Right Area: Agent Terminal, Reasoning Trajectory & Logs
            with Vertical(id="agent-split-pane"):
                with Horizontal(id="terminal-header-bar"):
                    yield Static(
                        "TERMINAL / REASONING & AGENT LOG", classes="panel-header-title"
                    )
                with Horizontal(id="transcript-area"):
                    yield TranscriptView(id="chat-container")
                    self._trajectory_rail = TrajectoryRail(id="trajectory-rail")
                    yield self._trajectory_rail

                # Bottom Command Input Row
                with Vertical(id="input-area"):
                    with Horizontal(id="input-row"):
                        yield Static("> ", id="prompt-symbol")
                        self._user_input = PromptTextArea(
                            id="user-input",
                            language=None,
                            show_line_numbers=False,
                            soft_wrap=True,
                            tab_behavior="indent",
                            suggestion_callback=self._on_suggestion_matches,
                        )
                        yield self._user_input
                        yield Button("SEND ↗", id="send-btn", variant="primary")
                        yield Static("", id="input-spinner")
                    yield ListView(id="input-suggestions")

        # Bottom Context Progress & Telemetry Meter
        with Vertical(id="telemetry-bar"):
            yield Static(self._build_context_progress_text(), id="context-meter-bar")
            self._status_bar = StatusBar(id="status-bar")
            yield self._status_bar

        # Bottom Navigation Dock
        with Horizontal(id="bottom-nav-dock"):
            yield Button(
                "📄 SHELL",
                id="dock-btn-shell",
                classes="nav-dock-btn nav-dock-btn-active",
            )
            yield Button("📖 CONTEXT", id="dock-btn-context", classes="nav-dock-btn")
            yield Button("📋 LOGS", id="dock-btn-goal", classes="nav-dock-btn")
            yield Button("⚙️ SYS", id="dock-btn-sys", classes="nav-dock-btn")

        yield Footer()

    def open_tab(self, file_path: str) -> None:
        self.open_file_tab(file_path)

    def open_file(self, file_path: str) -> None:
        self.open_file_tab(file_path)

    def open_file_tab(self, file_path: str) -> None:
        try:
            abs_path = os.path.abspath(file_path)
            if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
                self.notify(
                    f"File not found: {escape(file_path)}",
                    severity="warning",
                    timeout=2,
                )
                return

            filename = os.path.basename(abs_path)

            def _on_action_choice(choice: Optional[str]) -> None:
                if not choice or choice == "cancel":
                    return

                if choice == "system":
                    try:
                        if sys.platform == "darwin":
                            subprocess.Popen(["open", abs_path])
                        elif sys.platform == "win32":
                            os.startfile(abs_path)
                        else:
                            subprocess.Popen(["xdg-open", abs_path])
                        self.notify(
                            f"🚀 Opened {filename} with default app",
                            severity="information",
                            timeout=2,
                        )
                    except Exception as err:
                        self.notify(
                            f"Could not open file: {err}", severity="error", timeout=3
                        )

                elif choice == "code":
                    try:
                        subprocess.Popen(["code", abs_path])
                        self.notify(
                            f"📝 Opened {filename} in VS Code",
                            severity="information",
                            timeout=2,
                        )
                    except Exception:
                        try:
                            if sys.platform == "darwin":
                                subprocess.Popen(["open", abs_path])
                            else:
                                subprocess.Popen(["xdg-open", abs_path])
                            self.notify(
                                f"🚀 Opened {filename} with default app",
                                severity="information",
                                timeout=2,
                            )
                        except Exception as err:
                            self.notify(
                                f"Could not launch editor: {err}",
                                severity="error",
                                timeout=3,
                            )

                elif choice == "copy":
                    try:
                        if sys.platform == "darwin":
                            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                            p.communicate(abs_path.encode("utf-8"))
                        elif sys.platform == "win32":
                            p = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
                            p.communicate(abs_path.encode("utf-16"))
                        else:
                            p = subprocess.Popen(
                                ["xclip", "-selection", "clipboard"],
                                stdin=subprocess.PIPE,
                            )
                            p.communicate(abs_path.encode("utf-8"))
                        self.notify(
                            f"📋 Copied path: {filename}",
                            severity="information",
                            timeout=2,
                        )
                    except Exception:
                        self.notify(
                            f"Path: {abs_path}", severity="information", timeout=4
                        )

            self.push_screen(FileActionModal(abs_path), _on_action_choice)
        except Exception as e:
            self.notify(f"File action error: {e}", severity="warning", timeout=2)

    def close_file_tab(self, file_path: str) -> None:
        if file_path in self._open_tabs:
            del self._open_tabs[file_path]
            if self._active_tab_path == file_path:
                remaining = list(self._open_tabs.keys())
                self._active_tab_path = remaining[-1] if remaining else None
            self._refresh_editor_split_view()

    def _get_tab_hash(self, file_path: str) -> str:
        return hashlib.md5(file_path.encode("utf-8")).hexdigest()[:10]

    def _refresh_editor_split_view(self) -> None:
        try:
            tab_container = self.query_one("#tab-buttons-container")
            content_area = self.query_one("#editor-content-area")
        except Exception:
            return

    @on(DirectoryTree.FileSelected)
    def on_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        path = getattr(event, "path", None)
        if not path:
            return
        abs_path = os.path.abspath(str(path))
        if os.path.isfile(abs_path):
            self.open_file_tab(abs_path)

    @on(DirectoryTree.NodeSelected)
    def on_node_selected(self, event: DirectoryTree.NodeSelected) -> None:
        node = getattr(event, "node", None)
        if node and hasattr(node, "data") and node.data:
            path = getattr(node.data, "path", None)
            if path:
                abs_path = os.path.abspath(str(path))
                if os.path.isfile(abs_path):
                    self.open_file_tab(abs_path)

    @on(Button.Pressed, "#toggle-split-btn")
    def on_toggle_split_btn(self) -> None:
        try:
            editor_pane = self.query_one("#editor-split-pane")
            editor_pane.display = not editor_pane.display
            status = "shown" if editor_pane.display else "hidden"
            self.notify(
                f"Editor split pane {status}", severity="information", timeout=2
            )
        except Exception:
            pass

    @on(Button.Pressed)
    def on_tab_action_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if not (btn_id.startswith("tsel_") or btn_id.startswith("tcls_")):
            return

        h_target = btn_id.split("_", 1)[1]
        matching_path = None
        for path in self._open_tabs.keys():
            if self._get_tab_hash(path) == h_target:
                matching_path = path
                break

        if not matching_path:
            return

        if btn_id.startswith("tcls_"):
            self.close_file_tab(matching_path)
        else:
            self._active_tab_path = matching_path
            self._refresh_editor_split_view()

    def _build_system_health_text(self) -> str:
        cpu_pct = 0
        ram_pct = 0
        ram_detail = ""

        try:
            import psutil

            cpu_val = psutil.cpu_percent(interval=None)
            if cpu_val == 0.0:
                cpu_val = psutil.cpu_percent(interval=0.03)
            cpu_pct = min(100, max(0, int(round(cpu_val))))

            vm = psutil.virtual_memory()
            ram_pct = min(100, max(0, int(round(vm.percent))))
            used_gb = vm.used / (1024**3)
            total_gb = vm.total / (1024**3)
            ram_detail = f" ({used_gb:.1f}/{total_gb:.1f} GB)"
        except Exception:
            try:
                load1, _, _ = os.getloadavg()
                cpu_count = os.cpu_count() or 1
                cpu_pct = min(100, int((load1 / cpu_count) * 100))
            except Exception:
                cpu_pct = 0

            try:
                import subprocess

                p = subprocess.run(
                    ["vm_stat"], capture_output=True, text=True, timeout=2
                )
                lines = p.stdout.splitlines()
                pages = {}
                for line in lines[1:]:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = int(parts[1].strip().rstrip("."))
                        pages[key] = val
                page_size = 4096
                free = (
                    pages.get("Pages free", 0) + pages.get("Pages speculative", 0)
                ) * page_size
                active = pages.get("Pages active", 0) * page_size
                wired = pages.get("Pages wired down", 0) * page_size
                compressed = pages.get("Pages occupied by compressor", 0) * page_size
                used = active + wired + compressed
                total = used + free + (pages.get("Pages inactive", 0) * page_size)
                ram_pct = int((used / total) * 100) if total > 0 else 0
            except Exception:
                ram_pct = 0

        # Context Token Calculation
        mem = getattr(self.engine, "_memory", None)
        if mem and hasattr(mem, "total_tokens") and mem.total_tokens > 0:
            tokens_est = mem.total_tokens
        else:
            tokens_est = getattr(self.engine, "_total_llm_calls", 0) * 450

        ctx_max = CTX_SIZE
        ctx_pct = min(100, int((tokens_est / ctx_max) * 100)) if ctx_max > 0 else 0

        tps_val = getattr(self, "_live_tps", 0.0)
        lat_val = getattr(self, "_live_latency_ms", 0.0)

        tps_str = (
            f"{tps_val:.1f}"
            if tps_val > 0
            else ("0.0" if not self._is_running else "calculating...")
        )
        lat_str = (
            f"{int(lat_val)}ms"
            if lat_val > 0
            else ("0ms" if not self._is_running else "--")
        )

        is_engine_ready = (self.engine_port <= 0 or getattr(self, "_last_server_online", False))
        status_badge = "[bold green]● ENGINE READY[/bold green]" if is_engine_ready else "[bold red]○ ENGINE OFFLINE (Port 1234)[/bold red]"

        speedometer = (
            f"[bold cyan]⚡ INFERENCE SPEEDOMETER[/bold cyan]  {status_badge}\n"
            f"[bold green]SPEED: {tps_str} t/s[/bold green] [dim](Latency: {lat_str})[/dim]\n"
        )

        bar_width = 14
        filled = min(bar_width, int(round((ctx_pct / 100.0) * bar_width)))
        hatch_active = "█" * filled
        hatch_free = "░" * (bar_width - filled)
        bar = f"{hatch_active}{hatch_free}"

        ctx_color = "green" if ctx_pct < 50 else "yellow" if ctx_pct < 75 else "red"

        memory_block = (
            f"[bold cyan]🧠 CONTEXT MEMORY USAGE[/bold cyan]\n"
            f"[bold {ctx_color}]{tokens_est:,} / {ctx_max:,} TOKENS[/bold {ctx_color}] [bold yellow]({ctx_pct}%)[/bold yellow]\n"
            f"[{bar}]"
        )

        return f"{speedometer}\n{memory_block}"

    def _build_plan_text(self) -> str:
        project_root = getattr(self.engine, "project_root", os.getcwd())
        is_goal = bool(
            getattr(self.engine, "execution_mode", None)
            and getattr(self.engine.execution_mode, "value", None) == "GOAL"
        )
        return build_plan_text(project_root, is_goal)

    def _build_context_progress_text(self) -> str:
        mem = getattr(self.engine, "_memory", None)
        if mem and hasattr(mem, "total_tokens") and mem.total_tokens > 0:
            tokens_est = mem.total_tokens
        else:
            tokens_est = getattr(self.engine, "_total_llm_calls", 0) * 450

        ctx_max = CTX_SIZE
        pct = min(100, int((tokens_est / ctx_max) * 100)) if ctx_max > 0 else 0
        bar_width = 24
        filled = min(bar_width, int(round((pct / 100.0) * bar_width)))
        bar = "█" * filled + "░" * (bar_width - filled)

        state_str = getattr(self, "_agent_state", "READY")

        return (
            f"[bold cyan]> SYSTEM:[/] [bold green]{state_str}[/bold green]  │  "
            f"[bold cyan]MODE:[/] [bold white]{'🎯 GOAL' if getattr(self.engine, 'execution_mode', None) and getattr(self.engine.execution_mode, 'value', None) == 'GOAL' else '💬 CHAT'}[/bold white]  │  "
            f"[bold cyan]CONTEXT:[/] [{bar}] [bold yellow]{pct}%[/bold yellow] [dim]({tokens_est:,}/{ctx_max:,})[/dim]"
        )

    def _build_meta_text(self) -> str:
        mem = getattr(self.engine, "_memory", None)
        if mem and hasattr(mem, "total_tokens") and mem.total_tokens > 0:
            tokens_est = mem.total_tokens
        else:
            tokens_est = getattr(self.engine, "_total_llm_calls", 0) * 450

        server_status_str = getattr(self, "engine_server_status", "● Active")
        if (
            "Offline" in server_status_str
            or "Error" in server_status_str
            or "404" in server_status_str
        ):
            server_status_str = f"[bold red]{escape(server_status_str)}[/bold red]"
        else:
            server_status_str = f"[bold green]{escape(server_status_str)}[/bold green]"

        mem_line = ""
        if mem and hasattr(mem, "messages"):
            mem_line = f"[bold]Messages:[/] {len(mem.messages)}\n"

        return (
            f"[bold]Engine Server:[/] {server_status_str}\n"
            f"[bold]Provider:[/] [cyan]{escape(self.provider_name)}[/]\n"
            f"[bold]Model:[/] [magenta]{escape(self.model_name)}[/]\n"
            f"[bold]Context:[/] {CTX_SIZE:,} tokens\n"
            f"[bold]LLM Calls:[/] {self.engine._total_llm_calls}\n"
            f"[bold]Live Tokens:[/] {tokens_est:,} / {CTX_SIZE:,}\n"
            f"[bold]Depth Limit:[/] {self.engine.max_depth}\n"
            f"{mem_line}"
        ).strip()

    def update_sidebar_meta(self) -> None:
        try:
            shp = self.query_one("#system-health-panel")
            shp.update(self._build_system_health_text())
        except Exception:
            pass
        try:
            cmb = self.query_one("#context-meter-bar")
            cmb.update(self._build_context_progress_text())
        except Exception:
            pass
        try:
            pp = self.query_one("#plan-panel")
            pp.update(self._build_plan_text())
        except Exception:
            pass
        try:
            mb = self.query_one("#input-model-badge", Button)
            mb.label = f"🤖 {self.model_name} ▾"
        except Exception:
            pass
        try:
            tps_val = getattr(self, "_live_tps", 0.0)
            lat_val = getattr(self, "_live_latency_ms", 0.0)
            tps_str = (
                f"{tps_val:.1f} t/s"
                if tps_val > 0
                else ("idle" if not self._is_running else "calculating...")
            )
            lat_str = (
                f"{int(lat_val)}ms"
                if lat_val > 0
                else ("0ms" if not self._is_running else "--")
            )

            self.query_one("#hud-epoch").update(f"TPS: {tps_str}")
            self.query_one("#hud-reverts").update(f"LATENCY: {lat_str}")
        except Exception:
            pass
        try:
            mtb = self.query_one("#mode-toggle-btn", Button)
            is_goal = (
                getattr(self.engine, "execution_mode", None)
                and getattr(self.engine.execution_mode, "value", None) == "GOAL"
            )
            mtb.label = "🎯 GOAL_MODE: ACTIVE" if is_goal else "💬 CHAT_MODE: ACTIVE"
            if is_goal:
                mtb.remove_class("mode-badge-chat")
                mtb.add_class("mode-badge-goal")
            else:
                mtb.remove_class("mode-badge-goal")
                mtb.add_class("mode-badge-chat")
        except Exception:
            pass

    def action_show_help(self) -> None:
        self.push_screen(ShortcutsHelpModal())

    @on(Button.Pressed, "#help-btn")
    def on_help_pressed(self) -> None:
        self.action_show_help()

    @on(Button.Pressed, "#input-model-badge")
    def on_model_badge_clicked(self) -> None:
        self.action_select_model()

    @on(Button.Pressed, "#compact-btn")
    def on_compact_btn_clicked(self) -> None:
        self.action_compact_context()

    @on(Button.Pressed, "#health-compact-btn")
    def on_health_compact_btn_clicked(self) -> None:
        self.action_compact_context()

    @on(Button.Pressed, "#mode-toggle-btn")
    def on_mode_toggle_pressed(self) -> None:
        self.action_select_mode()

    @on(Button.Pressed, ".nav-dock-btn")
    def on_dock_btn_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        for b in self.query(".nav-dock-btn"):
            b.remove_class("nav-dock-btn-active")
        event.button.add_class("nav-dock-btn-active")
        if btn_id == "dock-btn-shell":
            try:
                self.set_focus(self.query_one("#user-input"))
            except Exception:
                pass
        elif btn_id == "dock-btn-context":
            self.action_toggle_sidebar()
        elif btn_id == "dock-btn-goal":
            self.action_select_mode()
        elif btn_id == "dock-btn-sys":
            self.action_toggle_status_modal()

    async def _submit_user_input(self) -> None:
        """Extract text from the TextArea, clear it, and dispatch."""
        try:
            inp = self.query_one("#user-input", TextArea)
        except Exception:
            return
        user_text = inp.text.strip()
        if not user_text or self._is_running:
            return

        inp.clear()

        if user_text.startswith("/"):
            await self._handle_slash_command(user_text)
            return

        self._chat_history.append({"role": "user", "content": user_text})
        try:
            container = self.query_one("#chat-container")
            if hasattr(container, "append_card"):
                container.append_card(MessageCard(user_text, role="user"))
            else:
                self._safe_mount(
                    container,
                    Static(
                        Panel(
                            escape(user_text),
                            title="You",
                            border_style="bright_blue",
                        )
                    ),
                )
        except Exception:
            pass

        self._run_agent(user_text)

    @on(Button.Pressed, "#send-btn")
    async def on_send_button(self) -> None:
        if self._is_running:
            self.stop_current_agent()
            return
        await self._submit_user_input()

    # ── Input Suggestions (slash / @file autocomplete) ────────────────────

    def _on_suggestion_matches(self, matches: list[str]) -> None:
        try:
            lv = self.query_one("#input-suggestions", ListView)
        except Exception:
            return
        if matches:
            lv.clear()
            for match in matches:
                lv.append(ListItem(Label(match)))
            lv.display = True
            if self._user_input is not None:
                lv.index = self._user_input.highlight_index
        else:
            lv.clear()
            lv.display = False

    def _on_suggestion_highlight(self, index: int) -> None:
        try:
            lv = self.query_one("#input-suggestions", ListView)
            if lv.display and lv.index != index:
                lv.index = index
        except Exception:
            pass

    @on(ListView.Selected, "#input-suggestions")
    def on_input_suggestion_selected(self, event: ListView.Selected) -> None:
        try:
            if self._user_input is None:
                return
            self._user_input.set_highlight(event.list_view.index or 0)
            self._user_input.accept_suggestion()
            self._user_input.focus()
        except Exception:
            pass

    @on(PromptTextArea.SubmitRequested, "#user-input")
    async def on_user_input_submit(self, event: PromptTextArea.SubmitRequested) -> None:
        await self._submit_user_input()

    def stop_current_agent(self) -> None:
        if not self._is_running:
            return
        try:
            self.workers.cancel_group(self, "agent")
        except Exception:
            pass
        self._is_running = False
        self._set_input_enabled(True)
        self.notify("Agent execution stopped by user", severity="warning", timeout=2)

    def _set_input_enabled(self, enabled: bool) -> None:
        try:
            inp = self.query_one("#user-input", TextArea)
            btn = self.query_one("#send-btn", Button)
            spinner = self.query_one("#input-spinner")
            inp.disabled = not enabled
            if not enabled:
                btn.label = "⏹ STOP"
                btn.variant = "error"
                btn.disabled = False
                spinner.update("[bold cyan]●[/]")
            else:
                btn.label = "SEND ↗"
                btn.variant = "primary"
                btn.disabled = False
                spinner.update("")
        except Exception:
            pass

    def _auto_refresh_engine_status(self) -> None:
        self.update_status_bar()
        self.update_sidebar_meta()

        if getattr(self, "_server_starting", False):
            return

        if self.engine_port <= 0:
            return

        is_online = is_port_in_use(self.engine_port)
        if getattr(self, "_last_server_online", None) != is_online:
            self._last_server_online = is_online
            if hasattr(self, "_conn_banner_widget") and self._conn_banner_widget:
                if is_online:
                    self._conn_banner_widget.update(
                        f"  [bold green]Connected to {escape(self.provider_name)} ({escape(self.model_name)}) on port {self.engine_port}[/]\n"
                    )
                elif self.externally_managed:
                    self._conn_banner_widget.update(
                        f"  [bold red]Cannot connect to {escape(self.provider_name)}![/] Nothing on port {self.engine_port}.\n"
                    )
                else:
                    self._conn_banner_widget.update(
                        f"  [bold red]Cannot connect to {escape(self.provider_name)}![/] Server offline on port {self.engine_port}.\n"
                    )

    def on_mount(self) -> None:
        try:
            self.register_theme(_TORCHLIGHT_THEME)
            self.register_theme(_MATRIX_PHOSPHOR_THEME)
            self.register_theme(_BLUEPRINT_LIGHT_THEME)
            self.theme = "blueprint-light"
        except Exception:
            try:
                self.theme = "torchlight"
            except Exception:
                pass

        try:
            self.set_interval(1.0, self.update_sidebar_meta)
        except Exception:
            pass

        try:
            self.call_after_refresh(self._refresh_editor_split_view)
        except Exception:
            pass

        try:
            container = self.query_one("#chat-container")

            # Welcome banner - 3-step quick start
            container.mount(
                Static(
                    Panel(
                        "[bold cyan]Torchlight Codex IDE[/]\n\n"
                        "[bold white]1.[/] Check engine status in sidebar (green = ready)\n"
                        "[bold white]2.[/] Pick a model with [bold yellow]Ctrl+M[/] or use the default\n"
                        "[bold white]3.[/] Type your task below and press [bold yellow]Send[/] or Enter\n\n"
                        "[dim]Press Ctrl+B for sidebar | Ctrl+T for theme | /help for commands[/]",
                        title="Welcome",
                        border_style="cyan",
                    )
                )
            )

            if self.engine_port <= 0:
                is_online = True
                self._last_server_online = True
                banner_text = f"  [bold green]Using {escape(self.provider_name)} ({escape(self.model_name)})[/]\n"
            else:
                is_online = is_port_in_use(self.engine_port)
                self._last_server_online = is_online
                if is_online:
                    banner_text = f"  [bold green]Connected to {escape(self.provider_name)} ({escape(self.model_name)}) on port {self.engine_port}[/]\n"
                elif self.externally_managed:
                    banner_text = (
                        f"  [bold red]Cannot connect to {escape(self.provider_name)}![/]\n"
                        f"    [dim]Nothing on port {self.engine_port}. Start it yourself, then click Start to re-check.[/]\n"
                    )
                else:
                    banner_text = (
                        f"  [bold red]Cannot connect to {escape(self.provider_name)}![/]\n"
                        f"    [dim]Server offline on port {self.engine_port}. Click Start or Restart.[/]\n"
                    )

            self._conn_banner_widget = Static(banner_text, id="conn-banner")
            container.mount(self._conn_banner_widget)
        except Exception as e:
            try:
                self.notify(f"UI initialization warning: {e}", severity="warning")
            except Exception:
                pass

        try:
            self.set_interval(1.0, self._auto_refresh_engine_status)
        except Exception:
            pass

        try:
            self._refresh_git_tree()
            self.update_status_bar()
        except Exception:
            pass

        try:
            self.set_focus(self.query_one("#user-input", TextArea))
        except Exception:
            pass

        try:
            self.call_after_refresh(self._apply_responsive_layout)
        except Exception:
            pass

    def _apply_responsive_layout(self) -> None:
        try:
            w, h = self.size.width, self.size.height
            screen = self.query_one("Screen")
            screen.set_class(w < 80, "narrow-terminal")
            screen.set_class(w < 50, "very-narrow-terminal")
            screen.set_class(h < 24, "short-terminal")
        except Exception:
            pass

    def on_resize(self) -> None:
        self._apply_responsive_layout()

    async def on_key(self, event) -> None:
        """Enter submits the prompt; Shift+Enter inserts a newline."""
        if event.key == "enter":
            # Check if the TextArea is currently focused
            try:
                inp = self.query_one("#user-input", TextArea)
            except Exception:
                return
            if self.focused is inp:
                event.prevent_default()
                event.stop()
                await self._submit_user_input()

    # ── Slash Command Handler ───────────────────────────────────────────

    async def _handle_slash_command(self, cmd_text: str) -> None:
        container = self.query_one("#chat-container")
        parts = cmd_text.split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/help":
            help_md = """### Commands
- `/start` / `/restart` / `/stop` -- Engine server control
- `/kill` -- Kill session & reset REPL
- `/cd <path>` -- Change working directory
- `/model <name>` -- Switch model
- `/index` -- Build AST knowledge graph
- `/clear` -- Clear chat
- `/reset` -- Reset Python sandbox
- `/status` -- Open telemetry modal
- `/help` -- This cheat sheet
"""
            container.mount(
                Static(Panel(Markdown(help_md), title="Help", border_style="yellow"))
            )

        elif cmd in ("/start", "/startengine"):
            self.on_start_engine_btn()

        elif cmd in ("/restart", "/restartengine"):
            self.on_restart_engine_btn()

        elif cmd in ("/stop", "/terminate", "/stopengine"):
            self.on_stop_engine_btn()

        elif cmd in ("/kill", "/killsession", "/kill-session"):
            self.on_kill_session_btn()

        elif cmd in ("/engine", "/provider"):
            self.action_select_model()

        elif cmd in ("/select", "/copyselect", "/copyselection"):
            self.action_copy_selection()

        elif cmd in ("/status", "/telemetry"):
            self.action_toggle_status_modal()

        elif cmd == "/mode":
            if not arg:
                self.action_select_mode()
            else:
                m_str = arg.lower().strip()
                if m_str in ("chat", "goal"):
                    from core.memory.models import ExecutionMode

                    new_mode = (
                        ExecutionMode.GOAL if m_str == "goal" else ExecutionMode.CHAT
                    )
                    if hasattr(self.engine.memory.state, "execution_mode"):
                        self.engine.memory.state.execution_mode = new_mode
                    if m_str == "goal":
                        try:
                            from core.execution.autonomous_harness import (
                                AutonomousHarness,
                            )

                            harness = AutonomousHarness(
                                project_root=self.engine.project_root,
                                memory=self.engine.memory,
                            )
                            harness.ensure_goal_spec_initialized()
                        except Exception:
                            pass
                        self.notify(
                            "Switched to Goal Mode (Task Graph initialized in .torchlight/tasks.md)",
                            severity="success",
                            timeout=3,
                        )
                    else:
                        self.notify(
                            "Switched to Chat Mode (Lightweight Q&A)",
                            severity="information",
                            timeout=3,
                        )
                    self.update_status_bar()
                else:
                    self.notify(
                        "Usage: /mode chat or /mode goal", severity="warning", timeout=3
                    )

        elif cmd in ("/cd", "/workdir", "/open", "/browse"):
            if not arg:
                await self.action_open_folder_picker()
                return
            target_path = os.path.abspath(os.path.expanduser(arg))
            if os.path.isdir(target_path):
                self.engine.set_project_root(target_path)
                os.chdir(target_path)
                save_last_state({"last_workdir": target_path})
                self.update_status_bar()
                # Reload file tree
                self._refresh_git_tree()
                self.notify(
                    f"Directory changed to {target_path}",
                    severity="information",
                    timeout=2,
                )
            else:
                self.notify(f"Directory not found: {arg}", severity="error", timeout=3)

        elif cmd in ("/index", "/reindex"):
            self._start_ast_indexing()

        elif cmd == "/model":
            if not arg:
                self.notify(
                    f"Current model: {escape(self.model_name)}. Usage: /model <name>",
                    severity="information",
                    timeout=3,
                )
            else:
                normalized = normalize_model_name(arg)
                self.model_name = normalized
                if hasattr(self.engine.client, "model"):
                    self.engine.client.model = normalized
                self.update_status_bar()
                self.update_sidebar_meta()
                self.notify(
                    f"Switched model to {escape(normalized)}",
                    severity="information",
                    timeout=2,
                )

        elif cmd in ("/compress", "/compact"):
            self.action_compact_context()

        elif cmd in ("/clear", "/cls"):
            self.action_clear()

        elif cmd == "/reset":
            self.action_reset_session()

        elif cmd in ("/copy", "/copyall"):
            self.action_copy_chat()

        elif cmd == "/copylast":
            self.action_copy_last()

        else:
            self.notify(
                f"Unknown command: {cmd}. Type /help for list.",
                severity="error",
                timeout=3,
            )

    # ── Agent Worker ────────────────────────────────────────────────────

    def _safe_mount(self, container, widget) -> None:
        """Mount a widget defensively and scroll safely after layout pass."""
        try:
            if not container.is_attached:
                container = self.query_one("#chat-container")
            if container.is_attached:
                container.mount(widget)
                # Keep maximum 120 elements in chat container to prevent scroll overflow & DOM memory bloat
                if len(container.children) > 120:
                    try:
                        container.children[0].remove()
                    except Exception:
                        pass
                self.call_after_refresh(self._scroll_chat_to_end)
        except Exception:
            pass

    def _scroll_chat_to_end(self) -> None:
        try:
            container = self.query_one("#chat-container")
            if container.is_attached:
                container.scroll_end(animate=False)
        except Exception:
            pass

    @work(exclusive=True, group="agent")
    async def _run_agent(self, task: str) -> None:
        import time

        self._is_running = True
        self._set_input_enabled(False)
        self._stream_start_time = time.time()
        self._first_token_time = None
        self._stream_token_count = 0
        container = self.query_one("#chat-container")

        self.engine.on_step = self._handle_step
        self.engine.approval_fn = self._handle_approval
        self.engine.on_token = self._append_token
        self.engine.on_status_change = self._handle_status_change

        self._streaming_text = ""
        self._ensure_streaming_widget()

        try:
            try:
                result = await self.engine.solve_async(task)
            except Exception as first_err:
                err_msg = str(first_err).lower()
                port = self.engine_port
                connection_failed = (
                    "connection refused" in err_msg or "connection error" in err_msg
                )
                if connection_failed and port > 0 and self.externally_managed:
                    raise ConnectionError(
                        f"Could not reach {self.provider_name} on port {port}. "
                        f"Make sure it's running (for LM Studio: open the app, load a model, "
                        f"and start its Local Server), then try again."
                    ) from first_err
                if connection_failed and port > 0 and not is_port_in_use(port):
                    self._remove_streaming()
                    self.notify(
                        f"Server refused on port {port}, auto-starting engine...",
                        severity="warning",
                        timeout=3,
                    )
                    self.on_start_engine_btn()

                    # Wait up to 10 seconds for the port to become ready
                    server_ready = False
                    for _ in range(10):
                        await asyncio.sleep(1)
                        if is_port_in_use(port):
                            server_ready = True
                            break

                    if server_ready:
                        self.notify(
                            f"Engine active on port {port}, retrying task...",
                            severity="information",
                            timeout=2,
                        )
                        self._streaming_text = ""
                        self._ensure_streaming_widget()
                        result = await self.engine.solve_async(task)
                    else:
                        raise ConnectionError(
                            f"Could not auto-start local engine server on port {port}. "
                            "Please click Start in sidebar or run ./rlm_optimized/start_optimized_local.sh"
                        ) from first_err
                else:
                    raise first_err

            self._remove_streaming()
            self.update_sidebar_meta()

            container.mount(
                Static(
                    f"  [dim]── ✓ {result.total_llm_calls} LLM call(s), "
                    f"{len(result.steps)} step(s) ──[/]",
                    classes="step-status",
                )
            )
            self.call_after_refresh(self._scroll_chat_to_end)

        except asyncio.CancelledError:
            self._remove_streaming()
            self._safe_mount(container, Static("[yellow]  ⚠ Agent task cancelled[/]"))
        except Exception as e:
            self._remove_streaming()
            raw_err = str(e)
            if len(raw_err) > 500:
                raw_err = raw_err[:500] + "... [truncated]"
            err_str = escape(raw_err)
            self._safe_mount(container, Static(f"  [bold red]Error:[/] {err_str}"))
        finally:
            self._is_running = False
            self._set_input_enabled(True)
            self._agent_state = "IDLE"
            self.update_status_bar()
            try:
                self.set_focus(self.query_one("#user-input", TextArea))
            except Exception:
                pass

    # ── Token Streaming ─────────────────────────────────────────────────

    def _ensure_streaming_widget(self) -> StreamingView:
        if getattr(self, "_streaming_widget", None) is None:
            self._streaming_view = StreamingView()
            if Collapsible is not None:
                self._streaming_widget = Collapsible(
                    self._streaming_view, title="💭 Thinking...", collapsed=False
                )
            else:
                self._streaming_widget = self._streaming_view
            container = self.query_one("#chat-container")
            container.mount(self._streaming_widget)
            self.call_after_refresh(self._scroll_chat_to_end)
        return self._streaming_view

    def _ensure_pending_tool_card(self, tool_name: str, target: str = "") -> None:
        """Mount a running ToolCallCard for a streamed ``<tool_call>`` marker.

        Kept as a single in-flight card: the next tool ``Step`` completes it
        (via ``_handle_step``) instead of stacking "Preparing..." strings.
        """
        if self._pending_tool_card is not None:
            return
        try:
            container = self.query_one("#chat-container")
        except Exception:
            return
        card = ToolCallCard(tool_name, target=target)
        self._pending_tool_card = card
        self._pending_tool_name = tool_name
        if self._trajectory_rail is not None:
            self._trajectory_rail.add_pending(tool_name)
        if hasattr(container, "append_card"):
            container.append_card(card, scroll=True)
        else:
            self._safe_mount(container, card)

    def _append_token(self, chunk: str) -> None:
        import time

        self._streaming_text += chunk
        now = time.time()
        if self._first_token_time is None and self._stream_start_time:
            self._first_token_time = now
            self._live_latency_ms = max(
                1.0, (self._first_token_time - self._stream_start_time) * 1000.0
            )

        self._stream_token_count += max(1, len(chunk) // 3)
        if self._first_token_time and (now - self._first_token_time) > 0.05:
            self._live_tps = self._stream_token_count / (now - self._first_token_time)

        try:
            widget = self._ensure_streaming_widget()
            display_text = self._streaming_text

            if "<tool_call>" in display_text.lower():
                parts = re.split(r"<tool_call>", display_text, flags=re.IGNORECASE)
                display_text = parts[0].strip()
                raw_payload = parts[1] if len(parts) > 1 else ""
                try:
                    name_match = re.search(r'"name"\s*:\s*"([^"]+)"', raw_payload)
                    if name_match:
                        t_name = name_match.group(1)
                        target_match = re.search(
                            r'"(?:path|file|file_path|cmd|command|pattern|query)"\s*:\s*"([^"]+)"',
                            raw_payload,
                        )
                        target_str = target_match.group(1) if target_match else ""
                        self._ensure_pending_tool_card(t_name, target_str)
                except Exception:
                    pass

            if len(display_text) > 4000:
                display_text = "... [truncated streaming] ...\n" + display_text[-4000:]

            escaped = escape(display_text)

            widget.update_markup(escaped)

            meta_parts = []
            if self._live_tps > 0:
                meta_parts.append(f"{self._live_tps:.1f} tps")
            meta_parts.append(f"{self._stream_token_count:,} tok")
            if self._live_latency_ms > 0:
                meta_parts.append(f"{self._live_latency_ms:.0f}ms")
            widget.set_meta(" · ".join(meta_parts))

            if self._pending_tool_card is not None:
                self._pending_tool_card.update_running()
            self.call_after_refresh(self._scroll_chat_to_end)
        except Exception:
            pass

    def _remove_streaming(self) -> None:
        if getattr(self, "_streaming_widget", None) is not None:
            try:
                self._streaming_widget.remove()
            except Exception:
                pass
            self._streaming_widget = None
            self._streaming_view = None
        self._streaming_text = ""

    # ── Step Display ────────────────────────────────────────────────────

    def _handle_step(self, step: Step) -> None:
        container = self.query_one("#chat-container")
        self._remove_streaming()

        try:
            has_thinking = bool(
                step.thinking and step.thinking.strip() not in ("(forced)", "")
            )
            trimmed_thinking = ""
            if has_thinking:
                trimmed_thinking = step.thinking.strip()
                if len(trimmed_thinking) > 15000:
                    trimmed_thinking = (
                        trimmed_thinking[:15000] + "\n... [Reasoning Truncated]"
                    )

            # Tool execution - Single Unified Card (with embedded Rationale if present)
            if step.action == "tool":
                label = step.tool_name or "TOOL"
                display_args = (
                    dict(step.tool_args) if isinstance(step.tool_args, dict) else {}
                )

                target_name = ""
                if "path" in display_args:
                    target_name = str(display_args["path"])
                elif "file_path" in display_args:
                    target_name = str(display_args["file_path"])
                elif "command" in display_args:
                    target_name = str(display_args["command"])
                elif "query" in display_args:
                    target_name = str(display_args["query"])

                if label == "WRITE_FILE" and "content" in display_args:
                    display_args["content"] = (
                        f"... [{len(str(display_args['content']))} chars of code hidden]"
                    )
                elif label == "EDIT_FILE":
                    if "old_text" in display_args:
                        display_args["old_text"] = (
                            f"... [{len(str(display_args['old_text']))} chars hidden]"
                        )
                    if "new_text" in display_args:
                        display_args["new_text"] = (
                            f"... [{len(str(display_args['new_text']))} chars hidden]"
                        )

                res_raw = step.result or ""
                denied = "denied" in res_raw.lower()
                is_err = (
                    res_raw.startswith("Error")
                    or res_raw.startswith("❌")
                    or ("requires" in res_raw.lower() and "block" in res_raw.lower())
                    or ("failed" in res_raw.lower() and "error" in res_raw.lower())
                )
                if denied:
                    status = "denied"
                elif is_err:
                    status = "error"
                else:
                    status = "ok"

                # Complete the pending card created while streaming, or mount a
                # fresh completed card (engines that don't stream markers).
                card = self._pending_tool_card
                self._pending_tool_card = None
                self._pending_tool_name = None
                if card is None:
                    if self._trajectory_rail is not None:
                        self._trajectory_rail.add_pending(label)
                    card = ToolCallCard(label, args=display_args, target=target_name)
                    if hasattr(container, "append_card"):
                        container.append_card(card, scroll=True)
                    else:
                        self._safe_mount(container, card)
                if self._trajectory_rail is not None:
                    self._trajectory_rail.complete(status)
                card.complete(
                    result=res_raw,
                    args=display_args,
                    thinking=trimmed_thinking,
                    status=status,
                )

                # Phase 3: inline diff for successful file writes/edits.
                # Computed client-side from disk — zero LLM context overhead.
                if (
                    step.tool_name in ("WRITE_FILE", "EDIT_FILE", "CODE_FILE_WRITE")
                    and status == "ok"
                    and not is_err
                ):
                    try:
                        step_args = (
                            dict(step.tool_args)
                            if isinstance(step.tool_args, dict)
                            else {}
                        )
                        old_snapshot = None
                        step_path = str(
                            step_args.get("path") or step_args.get("file_path") or ""
                        )
                        if step_path and os.path.isabs(step_path):
                            old_snapshot = self._prewrite_snapshots.pop(step_path, None)
                        preview = build_diff_preview(
                            step.tool_name,
                            step_args,
                            self.engine.project_root,
                            old_text=old_snapshot,
                        )
                        if preview is not None:
                            path, _old, _new, entries = preview
                            if entries:
                                container.append_card(
                                    DiffView(entries, path=path), scroll=True
                                )
                    except Exception:
                        pass

                if (
                    step.tool_name in ("WRITE_FILE", "EDIT_FILE")
                    and step.result
                    and not (is_err or denied)
                ):
                    try:
                        self._refresh_git_tree()
                    except Exception:
                        pass
                    self._start_ast_indexing()
                    self.update_sidebar_meta()

            else:
                # Standalone Reasoning (for non-tool steps)
                if has_thinking:
                    raw_check = trimmed_thinking.strip()
                    is_raw_dict = (
                        raw_check.startswith("{") and raw_check.endswith("}")
                    ) or (raw_check.startswith("(") and raw_check.endswith(")"))
                    if (
                        not is_raw_dict
                        and len(raw_check) > 5
                        and not raw_check.startswith("{'path'")
                    ):
                        escaped_thinking = escape(trimmed_thinking)
                        step_title = (
                            f"💭 Step {step.step_number} Reasoning"
                            if getattr(step, "step_number", None)
                            else "💭 Reasoning"
                        )
                        self._safe_mount(
                            container,
                            thinking_block(
                                step_title,
                                escaped_thinking,
                                collapsed=True,
                            ),
                        )

                # Code execution
                if step.action == "code":
                    display_content = step.content
                    if len(display_content) > 10000:
                        display_content = (
                            display_content[:10000]
                            + "\n\n... [Output Truncated for UI Performance]"
                        )
                    self._safe_mount(
                        container,
                        Static(
                            Panel(
                                Syntax(
                                    display_content,
                                    "python",
                                    theme="monokai",
                                    line_numbers=True,
                                ),
                                title="⚡ Code Execution",
                                border_style="cyan",
                            )
                        ),
                    )
                    if step.result:
                        display_result = step.result
                        if len(display_result) > 10000:
                            display_result = (
                                display_result[:10000] + "\n... [Truncated]"
                            )
                        style = "red" if step.result.startswith("ERROR") else "green"
                        self._safe_mount(
                            container,
                            Static(
                                Panel(
                                    Text(display_result),
                                    title="📤 Output",
                                    border_style=style,
                                )
                            ),
                        )

                # Final answer
                elif step.action == "final_answer":
                    display_content = step.content
                    if len(display_content) > 15000:
                        display_content = (
                            display_content[:15000]
                            + "\n\n... [Output Truncated for UI Performance]"
                        )
                    self._safe_mount(
                        container,
                        MessageCard(
                            display_content,
                            role="final",
                            meta=card_meta_for(display_content),
                        ),
                    )
                    self._chat_history.append(
                        {"role": "assistant", "content": step.content}
                    )

                # Sub-queries
                elif step.action == "sub_queries":
                    display_content = step.content
                    if len(display_content) > 10000:
                        display_content = display_content[:10000] + "\n... [Truncated]"
                    self._safe_mount(
                        container,
                        Static(
                            Panel(
                                escape(display_content),
                                title="🔄 Sub-Queries",
                                border_style="yellow",
                            )
                        ),
                    )
                    if step.result and step.result != "DEPTH LIMIT REACHED":
                        self._safe_mount(
                            container,
                            Static(
                                Panel(
                                    escape(step.result[:2000]),
                                    title="📥 Sub-Query Results",
                                    border_style="dim green",
                                )
                            ),
                        )
        except Exception:
            pass

        # Update sidebar plan panel & metadata in real-time after every step
        try:
            self.update_sidebar_meta()
        except Exception:
            pass

        if step.action != "final_answer":
            self._ensure_streaming_widget()

    def action_copy_chat(self) -> None:
        if not self._chat_history:
            self.notify("No chat history to copy", severity="warning")
            return

        lines = []
        for item in self._chat_history:
            role_title = "You" if item["role"] == "user" else "Assistant"
            lines.append(f"### {role_title}\n\n{item['content']}\n")

        full_text = "\n".join(lines).strip()
        if copy_to_clipboard(full_text):
            self.notify(
                "Chat transcript copied to clipboard", severity="information", timeout=2
            )
        else:
            self.notify("Failed to copy to clipboard", severity="error", timeout=3)

    def action_copy_last(self) -> None:
        last_assistant = None
        for item in reversed(self._chat_history):
            if item["role"] == "assistant":
                last_assistant = item["content"]
                break
        if not last_assistant:
            self.notify("No assistant responses found to copy", severity="warning")
            return

        if copy_to_clipboard(last_assistant):
            self.notify(
                "Last response copied to clipboard", severity="information", timeout=2
            )
        else:
            self.notify("Failed to copy to clipboard", severity="error", timeout=3)

    def action_copy_selection(self) -> None:
        # 1. Try screen native selection text
        try:
            sel_text = self.screen.get_selected_text()
        except Exception:
            sel_text = None

        if sel_text and sel_text.strip():
            if copy_to_clipboard(sel_text.strip()):
                self.notify(
                    "Selected text copied to clipboard",
                    severity="information",
                    timeout=2,
                )
            else:
                self.notify("Failed to copy selection", severity="error", timeout=3)
            return

        def _on_turn_selected(content: Optional[str]):
            if content:
                if copy_to_clipboard(content):
                    self.notify(
                        "Turn copied to clipboard", severity="information", timeout=2
                    )
                else:
                    self.notify("Failed to copy turn", severity="error", timeout=3)

        self.push_screen(CopySelectionModal(self._chat_history), _on_turn_selected)

    def action_select_mode(self) -> None:
        def _on_mode_selected(selected_mode: Optional[str]):
            if selected_mode:
                mem = getattr(self.engine, "memory", None)
                from core.memory.models import ExecutionMode

                new_mode = (
                    ExecutionMode.GOAL
                    if selected_mode == "goal"
                    else ExecutionMode.CHAT
                )
                if (
                    mem
                    and hasattr(mem, "state")
                    and hasattr(mem.state, "execution_mode")
                ):
                    mem.state.execution_mode = new_mode

                if selected_mode == "goal":
                    try:
                        from core.execution.autonomous_harness import AutonomousHarness

                        harness = AutonomousHarness(
                            project_root=self.engine.project_root, memory=mem
                        )
                        harness.ensure_goal_spec_initialized()
                    except Exception:
                        pass
                    self.notify(
                        "Switched to Goal Mode (Task Graph in .torchlight/tasks.md)",
                        severity="success",
                        timeout=3,
                    )
                else:
                    self.notify(
                        "Switched to Chat Mode (Lightweight Q&A)",
                        severity="information",
                        timeout=3,
                    )
                self.update_status_bar()

        mem = getattr(self.engine, "memory", None)
        current_m = getattr(getattr(mem, "state", None), "execution_mode", "chat")
        m_str = (
            current_m.value if hasattr(current_m, "value") else str(current_m or "chat")
        )
        self.push_screen(SessionModePickerModal(m_str), _on_mode_selected)

    def action_select_model(self) -> None:
        def _on_model_picked(selected: Optional[dict]):
            if selected:
                new_model = selected["id"]
                new_provider = selected["provider"]
                self.notify(
                    f"Switching to {selected['name']}...",
                    severity="information",
                    timeout=3,
                )

                # 1. Kill old server processes
                try:
                    subprocess.run(
                        ["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL
                    )
                    subprocess.run(
                        ["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass

                # 2. Update model and provider names
                self.model_name = new_model
                self.provider_name = selected["name"]

                # 3. Re-instantiate engine client
                if new_provider in ("llama-cpp", "turbo", "turboquant"):
                    from rlm_optimized.llamacpp_client import LlamaCppClient

                    self.engine.client = LlamaCppClient(
                        base_url="http://localhost:8080/v1", model=new_model
                    )
                elif new_provider == "mlx":
                    from rlm_optimized.cloud_client import CloudClient

                    self.engine.client = CloudClient(
                        provider="mlx",
                        model=new_model,
                        base_url="http://localhost:8080/v1",
                        api_key="not-needed",
                    )
                elif new_provider == "ollama":
                    from rlm_optimized.ollama_client import OllamaClient

                    self.engine.client = OllamaClient(model=new_model)
                elif new_provider == "lmstudio":
                    from rlm_optimized.cloud_client import CloudClient

                    self.engine.client = CloudClient(
                        provider=None,
                        model=new_model,
                        base_url=LMSTUDIO_BASE_URL,
                        api_key=LMSTUDIO_API_KEY,
                    )
                else:
                    from rlm_optimized.cloud_client import CloudClient

                    self.engine.client = CloudClient(
                        provider=new_provider, model=new_model
                    )

                # 4. Update tracked port / management mode for the new provider
                self.engine_port, self.externally_managed = _provider_runtime_info(
                    new_provider
                )

                # 5. Launch new background server if local
                if new_provider in ("llama-cpp", "turbo", "turboquant", "mlx"):
                    self.on_start_engine_btn()

                self.notify(
                    f"Switched to {selected['name']}", severity="information", timeout=2
                )
                self.update_status_bar()
                self.update_sidebar_meta()

        self.push_screen(ModelPickerModal(), _on_model_picked)

    def action_open_folder(self) -> None:
        def _on_folder_picked(path: Optional[str]):
            if path and os.path.exists(path):
                self.engine.set_project_root(path)
                self._refresh_git_tree()
                self.notify(
                    f"Workspace set to {path}", severity="information", timeout=2
                )
                self.update_sidebar_meta()

        self.push_screen(
            FolderPickerModal(initial_path=self.engine.project_root), _on_folder_picked
        )

    @work(thread=True)
    def _start_ast_indexing(self) -> None:
        """Build the AST knowledge graph silently in background thread."""
        target = self.engine.project_root
        try:
            from rlm_optimized.ast_indexer import index_directory

            index_directory(target)
            self.call_from_thread(
                self.notify,
                f"✓ AST graph indexed for {os.path.basename(target)}",
                severity="information",
                timeout=2,
            )
        except Exception:
            pass

    @work
    async def _poll_server_launch(self) -> None:
        port = self.engine_port
        for _ in range(30):
            await asyncio.sleep(0.5)
            if is_port_in_use(port):
                self._server_starting = False
                self._last_server_online = True
                self.update_status_bar()
                self.update_sidebar_meta()
                if hasattr(self, "_conn_banner_widget") and self._conn_banner_widget:
                    self._conn_banner_widget.update(
                        f"  [bold green]Connected to {escape(self.provider_name)} ({escape(self.model_name)}) on port {port}[/]\n"
                    )
                self.notify(
                    f"Engine server active on port {port}",
                    severity="information",
                    timeout=2,
                )
                return

        self._server_starting = False
        self._last_server_online = False
        self.update_status_bar()
        self.update_sidebar_meta()
        self.notify(
            f"Engine server failed to bind to port {port} within 15 seconds",
            severity="error",
            timeout=5,
        )

    @on(Button.Pressed, "#start-engine-btn")
    def on_start_engine_btn(self) -> None:
        container = self.query_one("#chat-container")

        if self.engine_port <= 0:
            self.notify(
                f"{self.provider_name} is a cloud provider, nothing to start locally",
                severity="information",
                timeout=2,
            )
            self.update_status_bar()
            self.update_sidebar_meta()
            return

        if is_port_in_use(self.engine_port):
            self._server_starting = False
            self.notify(
                f"Engine server already active on port {self.engine_port}",
                severity="information",
                timeout=2,
            )
            self.update_status_bar()
            self.update_sidebar_meta()
            return

        if self.externally_managed:
            self.notify(
                f"{self.provider_name} offline on port {self.engine_port}. Start it yourself, then retry.",
                severity="warning",
                timeout=5,
            )
            self.update_status_bar()
            self.update_sidebar_meta()
            return

        self._server_starting = True
        self.notify(
            f"Launching local engine on port {self.engine_port}...",
            severity="information",
            timeout=3,
        )
        if hasattr(self, "_conn_banner_widget") and self._conn_banner_widget:
            self._conn_banner_widget.update(
                f"  [bold yellow]Starting local engine server ({self.model_name})...[/]\n"
            )
        self.update_status_bar()
        self.update_sidebar_meta()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        provider_str = getattr(self, "provider_name", "").lower()
        script_name = (
            "start_mlx_server.sh"
            if "mlx" in provider_str
            else "start_optimized_local.sh"
        )
        target_script = os.path.join(script_dir, script_name)

        if not os.path.exists(target_script):
            target_script = os.path.abspath(
                os.path.join(self.engine.project_root, "rlm_optimized", script_name)
            )

        if os.path.exists(target_script):
            try:
                log_dir = os.path.join(self.engine.project_root, ".torchlight")
                os.makedirs(log_dir, exist_ok=True)
                server_log_path = os.path.join(log_dir, "llama_server.log")
                server_log_file = open(server_log_path, "a", encoding="utf-8")
                subprocess.Popen(
                    [target_script],
                    cwd=os.path.dirname(target_script),
                    stdout=server_log_file,
                    stderr=server_log_file,
                    start_new_session=True,
                )
                self._poll_server_launch()
            except Exception as e:
                self._server_starting = False
                self.notify(
                    f"Failed to launch server: {escape(str(e))}",
                    severity="error",
                    timeout=5,
                )
                self.update_status_bar()
                self.update_sidebar_meta()
        else:
            self._server_starting = False
            self.notify(
                f"Server launch script not found: {target_script}",
                severity="error",
                timeout=5,
            )
            self.update_status_bar()
            self.update_sidebar_meta()

    @on(Button.Pressed, "#stop-engine-btn")
    def on_stop_engine_btn(self) -> None:
        if self.externally_managed:
            self.notify(
                f"{self.provider_name} is managed externally, stop it from its own app",
                severity="information",
                timeout=3,
            )
            return
        try:
            subprocess.run(["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL)
            self.notify("Engine server stopped", severity="warning", timeout=2)
        except Exception as e:
            self.notify(
                f"Failed to stop server: {escape(str(e))}", severity="error", timeout=5
            )

    @on(Button.Pressed, "#restart-engine-btn")
    def on_restart_engine_btn(self) -> None:
        if self.externally_managed:
            self.notify(
                f"Re-checking connection to {self.provider_name}...",
                severity="information",
                timeout=2,
            )
            self.update_status_bar()
            self.update_sidebar_meta()
            return

        self.notify(
            "Restarting with defaults (gemma 4 E2B + TurboQuant)...",
            severity="information",
            timeout=3,
        )

        # 1. Reset defaults to gemma 4 E2B and TurboQuant
        self.model_name = "gemma-4-E2B-it"
        self.provider_name = "llama.cpp + TurboQuant (3-bit/4-bit KV)"
        self.engine_port, self.externally_managed = _provider_runtime_info("turbo")
        from rlm_optimized.llamacpp_client import LlamaCppClient

        self.engine.client = LlamaCppClient(
            base_url="http://localhost:8080/v1", model=self.model_name
        )

        # 2. Terminate existing engine processes
        try:
            subprocess.run(["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL)
        except Exception:
            pass

        # 3. Re-launch local server
        self.on_start_engine_btn()
        self.update_status_bar()
        self.update_sidebar_meta()

    @on(Button.Pressed, "#kill-session-btn")
    def on_kill_session_btn(self) -> None:
        container = self.query_one("#chat-container")
        try:
            subprocess.run(["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL)
        except Exception:
            pass
        self.engine.sandbox.reset()
        self._is_running = False
        self._set_input_enabled(True)
        self._agent_state = "IDLE"
        self.update_status_bar()
        self.update_sidebar_meta()
        self.notify("Session killed, REPL memory reset", severity="warning", timeout=3)

    # NOTE: The model badge button click is handled by on_model_badge_clicked
    # above (bound to #input-model-badge). Ctrl+M binding also works via
    # action_select_model in the BINDINGS list.

    # ── Approval Modal ──────────────────────────────────────────────────

    async def _handle_approval(self, tool_name: str, risk: str, args: dict) -> bool:
        diff_entries = None
        diff_path = ""
        self._capture_prewrite_snapshot(tool_name, args)
        try:
            snapshot = None
            path = str(args.get("path") or args.get("file_path") or "")
            if path and os.path.isabs(path):
                snapshot = self._prewrite_snapshots.get(path)
            preview = build_diff_preview(
                tool_name, args, self.engine.project_root, old_text=snapshot
            )
            if preview is not None:
                _old, _new, diff_path, diff_entries = preview
        except Exception:
            pass
        return await self.push_screen_wait(
            ApprovalModal(
                tool_name,
                risk,
                args,
                diff_entries=diff_entries,
                diff_path=diff_path,
            )
        )

    def _capture_prewrite_snapshot(self, tool_name: str, args: dict) -> None:
        """Snapshot file contents *before* a diffable write executes.

        ``_handle_step`` runs after the write has landed, so reading the file
        there would show an empty diff. Capture the prior content here (the
        engine always routes CONFIRM/REVIEW file writes through approval).
        """
        if not isinstance(args, dict):
            return
        path = str(args.get("path") or args.get("file_path") or "")
        if (
            not path
            or not os.path.isabs(path)
            or tool_name not in ("WRITE_FILE", "EDIT_FILE", "CODE_FILE_WRITE")
        ):
            return
        if path in self._prewrite_snapshots:
            return
        old = ""
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    old = f.read()
        except OSError:
            old = ""
        self._prewrite_snapshots[path] = old

    # ── Actions ─────────────────────────────────────────────────────────

    def update_status_bar(self) -> None:
        """Consolidated Phase-4 status bar (state · model · context gauge · tps · tokens · errors · git)."""
        try:
            bar = self.query_one("#status-bar", StatusBar)
        except Exception:
            return
        tokens, ctx_max, pct = self._context_usage()
        try:
            server_online = is_port_in_use(self.engine_port)
        except Exception:
            server_online = False
        errors = sum(
            1
            for ev in getattr(self, "_agent_events", [])
            if ev.get("state") == "TOOL_DENIED"
            or "ERROR" in str(ev.get("state", "")).upper()
        )
        bar.update_status(
            state=getattr(self, "_agent_state", "IDLE"),
            model=self.model_name,
            pct=pct,
            tokens=tokens,
            ctx_max=ctx_max,
            tps=getattr(self, "_live_tps", 0.0),
            errors=errors,
            branch=self._git_branch(),
            port=self.engine_port,
            server_online=server_online,
            is_running=getattr(self, "_is_running", False),
        )

    def _context_usage(self) -> tuple[int, int, float]:
        mem = getattr(self.engine, "_memory", None)
        if mem and hasattr(mem, "total_tokens") and mem.total_tokens > 0:
            tokens_est = mem.total_tokens
        else:
            tokens_est = getattr(self.engine, "_total_llm_calls", 0) * 450
        ctx_max = CTX_SIZE
        pct = min(100.0, (tokens_est / ctx_max) * 100) if ctx_max > 0 else 0.0
        return int(tokens_est), ctx_max, pct

    def _git_branch(self) -> str:
        try:
            proc = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.engine.project_root,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            name = proc.stdout.strip()
            return name if proc.returncode == 0 and name else ""
        except Exception:
            return ""

    def _refresh_git_tree(self) -> None:
        """Repoint the file tree at the engine root and refresh git status."""
        try:
            tree = self.query_one("#file-tree", GitFileTree)
            tree.path = self.engine.project_root
            tree.refresh_git()
            tree.reload()
        except Exception:
            pass

    def action_command_palette(self) -> None:
        def _on_result(result: Optional[PaletteResult]) -> None:
            if result is None:
                return
            if result.kind == "action":
                try:
                    self.run_action(result.value)
                except Exception:
                    self.notify(
                        f"No handler for '{result.value}'",
                        severity="warning",
                        timeout=2,
                    )
            elif result.kind == "slash":
                asyncio.ensure_future(self._handle_slash_command(result.value))
            elif result.kind == "file":
                self.open_file_tab(result.value)

        self.push_screen(
            CommandPalette(self.engine.project_root, bindings=self.BINDINGS),
            _on_result,
        )

    def action_toggle_status_modal(self) -> None:
        meta_sum = self._build_meta_text()
        self.push_screen(
            AgentStatusModal(self._agent_state, self._agent_events, meta_sum)
        )

    def action_open_folder_picker(self) -> None:
        def _on_picker_result(chosen_dir: Optional[str]) -> None:
            if chosen_dir and os.path.isdir(chosen_dir):
                self.engine.set_project_root(chosen_dir)
                os.chdir(chosen_dir)
                save_last_state({"last_workdir": chosen_dir})
                self.update_status_bar()
                self._refresh_git_tree()
                self.notify(
                    f"Working directory set to {escape(str(chosen_dir))}",
                    severity="information",
                    timeout=2,
                )

        self.push_screen(FolderPickerModal(self.engine.project_root), _on_picker_result)

    def action_toggle_sidebar(self) -> None:
        try:
            sidebar = self.query_one("#explorer-sidebar")
            self._show_sidebar = not self._show_sidebar
            sidebar.display = self._show_sidebar
        except Exception:
            pass

    def action_cycle_theme(self) -> None:
        themes = [
            "torchlight",
            "textual-dark",
            "textual-light",
            "nord",
            "gruvbox",
            "solarized-light",
            "solarized-dark",
        ]
        idx = themes.index(self.theme) if self.theme in themes else 0
        self.theme = themes[(idx + 1) % len(themes)]
        self.notify(f"Theme: {self.theme}", severity="information", timeout=2)

    def action_reset_session(self) -> None:
        self.engine.sandbox.reset()
        self.notify("Python REPL state reset", severity="information", timeout=2)

    def action_clear(self) -> None:
        container = self.query_one("#chat-container")
        container.remove_children()
        if self._trajectory_rail is not None:
            self._trajectory_rail.clear()

    def action_compact_context(self) -> None:
        """Manually trigger memory context compaction."""
        mem = getattr(self.engine, "_memory", None)
        if not mem:
            self.notify(
                "No active memory context to compact", severity="warning", timeout=3
            )
            return
        tb, ta, tf = self.engine.compact_context(mem, force=True)
        self.update_status_bar()
        self.update_sidebar_meta()
        if tf > 0:
            self.notify(
                f"Context compacted: {tb:,} → {ta:,} tokens ({tf:,} tokens freed)",
                severity="information",
                timeout=4,
            )
        else:
            self.notify(
                f"Context already minimal ({ta:,} tokens)",
                severity="information",
                timeout=3,
            )


def create_client(args):
    provider = args.provider
    raw_model = args.model if args.model != MODEL_NAME else MODEL_NAME
    model = normalize_model_name(raw_model, provider=provider)

    if provider in ("llama-cpp", "turbo", "turboquant"):
        from rlm_optimized.llamacpp_client import LlamaCppClient

        base_url = args.base_url or "http://localhost:8080/v1"
        return (
            LlamaCppClient(base_url=base_url, model=model),
            model,
            "llama.cpp + TurboQuant (3-bit/4-bit KV)",
        )
    elif provider == "ollama":
        from rlm_optimized.ollama_client import OllamaClient

        return OllamaClient(model=model), model, "Ollama (local)"
    elif provider == "mlx":
        from rlm_optimized.cloud_client import CloudClient

        base_url = args.base_url or "http://localhost:8080/v1"
        client = CloudClient(
            provider="mlx",
            model=model,
            base_url=base_url,
            api_key=args.api_key or "not-needed",
        )
        return client, client.model, "Apple MLX (Metal GPU)"
    elif provider == "lmstudio":
        from rlm_optimized.cloud_client import CloudClient

        base_url = args.base_url or LMSTUDIO_BASE_URL
        # Don't run the qwen/gemma alias rewriter on LM Studio ids — LM Studio
        # model ids must match exactly what's loaded, and normalize_model_name()
        # would mangle any id that merely contains a substring like "qwen".
        explicit_model = args.model if args.model != MODEL_NAME else ""
        chosen_model = explicit_model
        if not chosen_model:
            live_models = fetch_provider_models(base_url)
            chosen_model = live_models[0] if live_models else "local-model"
        client = CloudClient(
            provider=None,
            model=chosen_model,
            base_url=base_url,
            api_key=args.api_key or LMSTUDIO_API_KEY,
        )
        return client, client.model, "LM Studio (local)"
    else:
        from rlm_optimized.cloud_client import CloudClient

        client = CloudClient(
            provider=provider if provider != "cloud" else None,
            model=model,
            base_url=args.base_url,
            api_key=args.api_key,
        )
        return client, client.model, f"{provider} (cloud)"


def main():
    parser = argparse.ArgumentParser(description="Torchlight Agent — Codex IDE TUI")
    parser.add_argument("--model", type=str, default=MODEL_NAME)
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        choices=[
            "ollama",
            "turbo",
            "turboquant",
            "llama-cpp",
            "mlx",
            "lmstudio",
            "groq",
            "together",
            "openrouter",
            "openai",
            "gemini",
            "cloud",
        ],
    )
    parser.add_argument("--depth", type=int, default=MAX_RECURSION_DEPTH)
    parser.add_argument(
        "--workdir", "-w", type=str, default=None, help="Set initial working directory"
    )
    parser.add_argument("--base-url", type=str, default=None)
    parser.add_argument("--api-key", type=str, default=None)
    args = parser.parse_args()

    # If the user didn't explicitly pass --provider, don't silently fall back to
    # launching a separate llama-cpp server on port 8080 with the hardcoded
    # default model. Check whether LM Studio already has a model loaded and
    # prefer that — this is what fetch_provider_models()/the lmstudio branch
    # below was already built to do, it just never used to get called at
    # startup unless --provider lmstudio was passed by hand.
    if args.provider is None:
        if fetch_provider_models(LMSTUDIO_BASE_URL):
            args.provider = "lmstudio"
        else:
            args.provider = PROVIDER

    try:
        client, model_name, provider_name = create_client(args)
    except Exception as e:
        print(f"[ERROR] Setup failed: {e}")
        sys.exit(1)

    if args.workdir:
        project_root = os.path.abspath(os.path.expanduser(args.workdir))
        if os.path.isdir(project_root):
            os.chdir(project_root)
            save_last_state({"last_workdir": project_root})
        else:
            print(f"[ERROR] Specified workdir does not exist: {args.workdir}")
            sys.exit(1)
    else:
        last_state = load_last_state()
        saved_workdir = last_state.get("last_workdir")
        if saved_workdir and os.path.isdir(saved_workdir):
            project_root = saved_workdir
            os.chdir(project_root)
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    engine = RLMEngineOptimized(
        client=client,
        max_depth=args.depth,
        project_root=project_root,
    )

    engine_port, externally_managed = _provider_runtime_info(args.provider)
    app = TorchlightApp(
        engine,
        model_name,
        provider_name,
        engine_port=engine_port,
        externally_managed=externally_managed,
    )
    app.run()


if __name__ == "__main__":
    main()
