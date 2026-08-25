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
from typing import Optional, Union
import hashlib

from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.message import Message
from textual import events, on
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
    Select,
    TabbedContent,
    TabPane,
    Switch,
    RadioSet,
    RadioButton,
    Checkbox,
)

try:
    from textual.widgets import Collapsible
except ImportError:
    Collapsible = None
from textual.screen import ModalScreen
from textual.theme import Theme
from textual.binding import Binding
from textual import events, on, work

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
from core.prompts.system import sanitize_assistant_text
from rlm_optimized.memory_monitor import format_memory_status, is_memory_safe
from rlm_optimized.tui_widgets.format import (
    build_agent_memory_scratchpad_text,
    build_plan_overview_text,
    build_plan_text,
    build_skills_overview_text,
    build_task_checklist_text,
    import_skill_file,
)
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
    AttachContextModal,
)
from rlm_optimized.tui_widgets.file_tree import GitFileTree
from rlm_optimized.tui_widgets.center_empty_state import (
    CenterEmptyState,
    STATE_DISCONNECTED,
    STATE_IDLE,
    STATE_WORKING,
)
from rlm_optimized.tui_widgets.connection_pill import ConnectionPill

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


class AgentMemoryWidget(VerticalScroll):
    """Displays the live L0 Agent Brain Scratchpad in UI/UX Pro format with scrollbars."""

    DEFAULT_CSS = """
    AgentMemoryWidget {
        height: auto;
        max-height: 28;
        min-height: 8;
        overflow-x: auto;
        overflow-y: auto;
        scrollbar-size-vertical: 1;
        scrollbar-size-horizontal: 1;
        scrollbar-background: transparent;
        scrollbar-background-hover: transparent;
        scrollbar-background-active: transparent;
        scrollbar-color: $panel;
        scrollbar-color-hover: $primary;
        scrollbar-color-active: $accent;
        color: $foreground;
        background: $background;
        border: solid $panel;
        padding: 0 1;
        margin-top: 1;
        margin-bottom: 1;
    }
    AgentMemoryWidget > #agent-memory-text {
        width: auto;
        min-width: 100%;
        height: auto;
        color: $foreground;
    }
    """

    _last_markup: str = ""

    def compose(self) -> ComposeResult:
        yield Static("", id="agent-memory-text")

    def update(self, renderable: Any = "") -> None:
        """Update the inner static widget content."""
        self._last_markup = str(renderable) if renderable else ""
        try:
            text_w = self.query_one("#agent-memory-text", Static)
            text_w.update(renderable)
        except Exception:
            pass

    def on_mount(self) -> None:
        self.update_memory()
        app = getattr(self, "app", None)
        if app and not getattr(app, "_is_test_env", False):
            self.set_interval(2.0, self.update_memory)

    def update_memory(self) -> None:
        try:
            app = getattr(self, "_app", None)
            if app is None:
                try:
                    app = self.app
                except Exception:
                    app = None
            mem = None
            proj_root = None
            is_goal = False
            if app and hasattr(app, "engine"):
                mem = getattr(app.engine, "memory", None)
                proj_root = getattr(app.engine, "project_root", None)
            if app and hasattr(app, "_is_goal_mode"):
                try:
                    is_goal = app._is_goal_mode()
                except Exception:
                    pass

            markup = build_agent_memory_scratchpad_text(
                mem=mem,
                project_root=proj_root,
                is_goal=is_goal,
            )
            if markup != self._last_markup:
                self._last_markup = markup
                try:
                    text_w = self.query_one("#agent-memory-text", Static)
                    text_w.update(markup)
                except Exception:
                    pass
                return
        except Exception:
            pass
        if not self._last_markup:
            fallback = build_agent_memory_scratchpad_text(None)
            self._last_markup = fallback
            try:
                text_w = self.query_one("#agent-memory-text", Static)
                text_w.update(fallback)
            except Exception:
                pass


# ── Approval Modal ──────────────────────────────────────────────────────


class ApprovalModal(ModalScreen[Union[bool, str]]):
    """Production-grade modal dialog for tool & file modification approval."""

    BINDINGS = [
        ("y", "allow", "Allow"),
        ("Y", "allow", "Allow"),
        ("enter", "allow", "Allow"),
        ("a", "always_allow", "Always Allow"),
        ("A", "always_allow", "Always Allow"),
        ("n", "deny", "Deny"),
        ("N", "deny", "Deny"),
        ("escape", "deny", "Deny"),
    ]

    DEFAULT_CSS = """
    ApprovalModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #approval-dialog {
        width: 90%;
        max-width: 84;
        max-height: 85%;
        border: round $primary;
        background: $surface;
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
        background: $background;
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
        background: $background;
        padding: 1;
    }
    #approval-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    #approval-buttons Button {
        margin: 0 1;
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
        risk_label = (
            f"RISK LEVEL: {self.risk.upper()}" if self.risk else "RISK LEVEL: CONFIRM"
        )

        with Vertical(id="approval-dialog"):
            yield Static(
                f"[{risk_label}]\nModification requires manual operational validation.",
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
                    f"DIFF PREVIEW -- {escape(self.diff_path or 'file')}",
                    id="approval-diff-label",
                )
                yield Static(
                    diff_markup(self.diff_entries, max_lines=120),
                    id="approval-diff",
                )
            with Horizontal(id="approval-buttons"):
                yield Button("APPROVE (Enter / Y)", variant="success", id="allow-btn")
                yield Button("REJECT (Esc / N)", variant="error", id="deny-btn")
                yield Button("ALWAYS ALLOW (A)", variant="warning", id="always-btn")

            yield Static(
                "[dim]Press Enter / Y to approve, N or Esc to reject, A for session auto-approve[/dim]",
                id="approval-hint",
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

    def action_always_allow(self) -> None:
        self.dismiss("always")

    @on(Button.Pressed, "#allow-btn")
    def on_allow(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#deny-btn")
    def on_deny(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#always-btn")
    def on_always(self) -> None:
        self.dismiss("always")


# ── Ask User Interactive Review Modal ───────────────────────────────────────────


class AskUserModal(ModalScreen[str]):
    """Interactive modal dialog for structured user review options and custom input."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+enter", "submit", "Submit"),
    ]

    DEFAULT_CSS = """
    AskUserModal {
        align: center middle;
        background: #0d1117;
    }
    #ask-dialog {
        width: 90%;
        max-width: 86;
        max-height: 85%;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }
    #ask-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    .ask-question-header {
        color: $foreground;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }
    #ask-options-container {
        max-height: 18;
        overflow-y: auto;
        border: solid $panel;
        background: $background;
        padding: 1;
        margin-bottom: 1;
    }
    .ask-q-group {
        margin-bottom: 1;
    }
    #ask-custom-label {
        color: $text-muted;
        margin-top: 1;
        margin-bottom: 0;
    }
    #ask-custom-input {
        margin-bottom: 1;
    }
    #ask-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    #ask-buttons Button {
        border: none;
        padding: 0 1;
        height: 3;
        margin: 0 1;
        min-width: 18;
    }
    """

    def __init__(
        self,
        question: str = "",
        options: Optional[list[str]] = None,
        is_multi_select: bool = False,
        allow_custom_input: bool = True,
        questions: Optional[list[dict]] = None,
    ) -> None:
        super().__init__()
        if questions and isinstance(questions, list):
            self.questions = questions
        elif question or options:
            self.questions = [
                {
                    "question": question or "Agent requested input:",
                    "options": options or [],
                    "is_multi_select": is_multi_select,
                    "allow_custom_input": allow_custom_input,
                }
            ]
        else:
            self.questions = []
        self.allow_custom_input = allow_custom_input

    def compose(self) -> ComposeResult:
        with Vertical(id="ask-dialog"):
            yield Label("❓ Agent Question / Plan Review", id="ask-title")

            if self.questions:
                with VerticalScroll(id="ask-options-container"):
                    for q_idx, q_data in enumerate(self.questions):
                        q_text = q_data.get("question", f"Question {q_idx + 1}")
                        yield Label(f"❓ {q_text}", classes="ask-question-header")
                        q_opts = q_data.get("options", [])
                        is_multi = bool(q_data.get("is_multi_select", False))
                        if q_opts:
                            if not is_multi:
                                with RadioSet(id=f"ask-radioset-{q_idx}", classes="ask-q-group"):
                                    for opt_idx, opt in enumerate(q_opts):
                                        yield RadioButton(opt, value=(opt_idx == 0), id=f"ask-radio-{q_idx}-{opt_idx}")
                            else:
                                with Vertical(id=f"ask-checkgroup-{q_idx}", classes="ask-q-group"):
                                    for opt_idx, opt in enumerate(q_opts):
                                        yield Checkbox(opt, value=(opt_idx == 0), id=f"ask-check-{q_idx}-{opt_idx}")

            if self.allow_custom_input:
                yield Label("Custom input / additional feedback (optional):", id="ask-custom-label")
                yield Input(placeholder="Type your response here...", id="ask-custom-input")

            with Horizontal(id="ask-buttons"):
                yield Button("Submit [Enter]", variant="primary", id="ask-submit-btn")
                yield Button("Dismiss [Esc]", variant="default", id="ask-cancel-btn")

    def action_cancel(self) -> None:
        self.dismiss("User dismissed prompt without input.")

    def action_submit(self) -> None:
        self._perform_submit()

    @on(Button.Pressed, "#ask-cancel-btn")
    def on_cancel_btn(self) -> None:
        self.dismiss("User dismissed prompt without input.")

    @on(Button.Pressed, "#ask-submit-btn")
    def on_submit_btn(self) -> None:
        self._perform_submit()

    @on(Input.Submitted, "#ask-custom-input")
    def on_input_submitted(self) -> None:
        self._perform_submit()

    def _perform_submit(self) -> None:
        results = []
        is_single = len(self.questions) == 1
        for q_idx, q_data in enumerate(self.questions):
            q_text = q_data.get("question", f"Question {q_idx + 1}")
            q_opts = q_data.get("options", [])
            is_multi = bool(q_data.get("is_multi_select", False))
            selected: list[str] = []
            if q_opts:
                if not is_multi:
                    try:
                        radio_set = self.query_one(f"#ask-radioset-{q_idx}", RadioSet)
                        if radio_set.pressed_button:
                            selected.append(str(radio_set.pressed_button.label))
                    except Exception:
                        pass
                else:
                    for opt_idx, opt in enumerate(q_opts):
                        try:
                            cb = self.query_one(f"#ask-check-{q_idx}-{opt_idx}", Checkbox)
                            if cb.value:
                                selected.append(opt)
                        except Exception:
                            pass
            if selected:
                sel_str = selected[0] if not is_multi else ", ".join(selected)
                if is_single:
                    results.append(f"Selected: {sel_str}")
                else:
                    results.append(f"{q_text}: Selected: {sel_str}")

        custom_text = ""
        if self.allow_custom_input:
            try:
                inp = self.query_one("#ask-custom-input", Input)
                custom_text = inp.value.strip()
            except Exception:
                pass

        if custom_text:
            results.append(f"Custom Input: {custom_text}")

        final_ans = "\n".join(results) if results else "User confirmed."
        self.dismiss(final_ans)


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
        width: 92%;
        max-width: 86;
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


# ── Skill Upload / Import Modal ──────────────────────────────────────────


class SkillUploadModal(ModalScreen[Optional[dict]]):
    """Modal dialog for importing external skill files/folders into the project workspace."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    SkillUploadModal {
        align: center middle;
        background: #0d1117;
    }
    #skill-dialog {
        width: 92%;
        max-width: 90;
        height: 88%;
        max-height: 32;
        border: solid $panel;
        border-left: solid $accent;
        background: $surface;
        padding: 1 2;
    }
    #skill-dialog-title {
        text-style: bold;
        color: $accent;
        height: 1;
        margin-bottom: 1;
    }
    #skill-detected-bar {
        height: 3;
        align: left middle;
        margin-bottom: 1;
    }
    .skill-detected-label {
        color: $warning;
        text-style: bold;
        padding-top: 1;
        margin-right: 1;
    }
    #skill-detected-bar Button {
        margin-right: 1;
        border: none;
        padding: 0 1;
        height: 3;
    }
    #skill-upload-jumps {
        height: 3;
        margin-bottom: 1;
    }
    #skill-upload-jumps Button {
        margin-right: 1;
        border: none;
        padding: 0 1;
        height: 3;
    }
    #skill-picker-tree {
        height: 1fr;
        min-height: 4;
        margin-bottom: 1;
        border: solid $panel;
        background: $background;
    }
    #skill-inputs-row {
        height: 3;
        margin-bottom: 1;
    }
    #skill-src-input {
        width: 60%;
        margin-right: 1;
    }
    #skill-custom-name-input {
        width: 40%;
    }
    #skill-dest-preview {
        color: $success;
        height: 1;
        margin-bottom: 1;
    }
    #skill-upload-actions {
        height: 3;
        align: right middle;
    }
    #skill-upload-actions Button {
        margin-left: 1;
        border: none;
        padding: 0 1;
        height: 3;
    }
    """

    def __init__(self, workspace_root: Optional[str] = None):
        super().__init__()
        self.workspace_root = workspace_root or os.getcwd()
        desktop = os.path.expanduser("~/Desktop")
        self.current_tree_path = desktop if os.path.exists(desktop) else self.workspace_root
        self.candidates = self._find_candidates()

    def _find_candidates(self) -> list[tuple[str, str, str]]:
        candidates = []
        seen = set()
        search_dirs = [
            os.path.expanduser("~/Desktop"),
            self.workspace_root,
            os.path.expanduser("~/Downloads"),
        ]
        for d in search_dirs:
            if not os.path.isdir(d):
                continue
            try:
                for item in sorted(os.listdir(d)):
                    p = os.path.join(d, item)
                    if p in seen or item.startswith("."):
                        continue
                    if os.path.isfile(p) and (p.endswith(".md") or p.endswith(".py")):
                        try:
                            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                                head = f.read(1024)
                            if "name:" in head or "SKILL" in item.upper() or "skill" in item.lower():
                                seen.add(p)
                                icon = "📄"
                                for line in head.splitlines()[:15]:
                                    if line.strip().startswith("icon:"):
                                        icon = line.split(":", 1)[1].strip()
                                        break
                                candidates.append((item, p, icon))
                        except Exception:
                            pass
                    elif os.path.isdir(p):
                        skill_md = os.path.join(p, "SKILL.md")
                        if not os.path.isfile(skill_md):
                            skill_md = os.path.join(p, "skill.md")
                        if os.path.isfile(skill_md):
                            seen.add(p)
                            icon = "📁"
                            try:
                                with open(skill_md, "r", encoding="utf-8", errors="ignore") as f:
                                    for line in f.read(1024).splitlines()[:15]:
                                        if line.strip().startswith("icon:"):
                                            icon = line.split(":", 1)[1].strip()
                                            break
                            except Exception:
                                pass
                            candidates.append((item, p, icon))
            except Exception:
                pass
        return candidates[:6]

    def compose(self) -> ComposeResult:
        with Vertical(id="skill-dialog"):
            yield Static("📥 Import External Skill into Workspace", id="skill-dialog-title")

            if self.candidates:
                with Horizontal(id="skill-detected-bar"):
                    yield Static("Detected:", classes="skill-detected-label")
                    for idx, (label, full_p, icon) in enumerate(self.candidates):
                        btn = Button(f"{icon} {label}", id=f"cand-{idx}", variant="primary")
                        btn.tooltip = full_p
                        yield btn

            with Horizontal(id="skill-upload-jumps"):
                yield Button("🖥️ Desktop", id="skill-jump-desktop", variant="default")
                yield Button("🏠 Home", id="skill-jump-home", variant="default")
                yield Button("📥 Downloads", id="skill-jump-downloads", variant="default")
                yield Button("📁 Workspace", id="skill-jump-workspace", variant="default")
                yield Button("💻 Root (/)", id="skill-jump-root", variant="default")

            yield DirectoryTree(self.current_tree_path, id="skill-picker-tree")

            with Horizontal(id="skill-inputs-row"):
                yield Input(
                    placeholder="Source path (click file in tree or paste)...",
                    id="skill-src-input",
                )
                yield Input(
                    placeholder="Custom name (optional)...",
                    id="skill-custom-name-input",
                )

            yield Static("Destination: [dim].agents/skills/<skill_name>/SKILL.md[/dim]", id="skill-dest-preview")

            with Horizontal(id="skill-upload-actions"):
                yield Button("✅ Import & Install Selected Skill", id="skill-confirm-btn", variant="success")
                yield Button("❌ Cancel", id="skill-cancel-btn", variant="error")

    @on(Button.Pressed)
    def on_button_pressed_handler(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("cand-"):
            try:
                idx = int(btn_id.split("-")[1])
                _, full_path, _ = self.candidates[idx]
                self._select_path(full_path)
            except Exception:
                pass

    @on(DirectoryTree.FileSelected, "#skill-picker-tree")
    @on(DirectoryTree.DirectorySelected, "#skill-picker-tree")
    def on_tree_selected(self, event: Union[DirectoryTree.FileSelected, DirectoryTree.DirectorySelected]) -> None:
        self._select_path(str(event.path))

    def _select_path(self, target_path: str) -> None:
        self.query_one("#skill-src-input", Input).value = target_path
        self._update_preview(target_path)

    def _update_preview(self, src: str) -> None:
        custom = self.query_one("#skill-custom-name-input", Input).value.strip()
        if custom:
            slug = re.sub(r"[^a-z0-9_]+", "_", custom.lower()).strip("_")
        elif src:
            p = Path(os.path.expanduser(src))
            slug = re.sub(r"[^a-z0-9_]+", "_", p.stem.lower()).strip("_")
        else:
            slug = "<skill_name>"

        preview = self.query_one("#skill-dest-preview", Static)
        if src.endswith(".py"):
            preview.update(f"Destination: [bold green].agents/skills/{slug}.py[/bold green]")
        else:
            preview.update(f"Destination: [bold green].agents/skills/{slug}/SKILL.md[/bold green]")

    @on(Input.Changed, "#skill-src-input")
    @on(Input.Changed, "#skill-custom-name-input")
    def on_inputs_changed(self) -> None:
        src = self.query_one("#skill-src-input", Input).value.strip()
        self._update_preview(src)

    def _set_tree_dir(self, target_dir: str) -> None:
        p = os.path.abspath(os.path.expanduser(target_dir))
        if os.path.isdir(p):
            self.current_tree_path = p
            try:
                tree = self.query_one("#skill-picker-tree", DirectoryTree)
                tree.path = p
            except Exception:
                pass

    @on(Button.Pressed, "#skill-jump-desktop")
    def on_jump_desktop(self) -> None:
        self._set_tree_dir(os.path.expanduser("~/Desktop"))

    @on(Button.Pressed, "#skill-jump-home")
    def on_jump_home(self) -> None:
        self._set_tree_dir(os.path.expanduser("~"))

    @on(Button.Pressed, "#skill-jump-downloads")
    def on_jump_downloads(self) -> None:
        self._set_tree_dir(os.path.expanduser("~/Downloads"))

    @on(Button.Pressed, "#skill-jump-workspace")
    def on_jump_workspace(self) -> None:
        self._set_tree_dir(self.workspace_root)

    @on(Button.Pressed, "#skill-jump-root")
    def on_jump_root(self) -> None:
        self._set_tree_dir("/")

    @on(Button.Pressed, "#skill-confirm-btn")
    def on_confirm(self) -> None:
        src = self.query_one("#skill-src-input", Input).value.strip()
        custom = self.query_one("#skill-custom-name-input", Input).value.strip()
        if not src:
            self.query_one("#skill-dest-preview", Static).update("[bold red]Please select or enter a valid source path.[/bold red]")
            return
        self.dismiss({"source_path": src, "custom_name": custom})

    @on(Button.Pressed, "#skill-cancel-btn")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ── Copy Selection Modal ──────────────────────────────────────────────────


class CopySelectionModal(ModalScreen[Optional[str]]):
    """Modal dialog to select and copy specific messages, code blocks, or text turns."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    CopySelectionModal {
        align: center middle;
    }
    #copy-dialog {
        width: 90%;
        max-width: 84;
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
        width: 90%;
        max-width: 74;
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
            yield Static("Select Torchlight Execution Mode", id="mode-title")
            yield Static(
                "Choose the operation mode for your session:\n\n"
                "• Code Mode: Direct surgical coding & task execution. Implements pending tasks from implementation_plan.md in source files.\n"
                "• Plan Mode: Brainstorm architecture, steps, & process. Writes/updates implementation_plan.md.\n"
                "• Chat Mode: Fast, lightweight Q&A. No disk task tracking files created.\n"
                "• Goal Mode: Continuous autonomous harness with disk-backed task graph (.torchlight/tasks.md).\n"
                "• Unified Mode: Dynamic phase auto-detection with full developer toolset.",
                id="mode-desc",
            )
            yield Static(
                "Tooltip: Plan Mode helps you brainstorm and maintain implementation_plan.md before coding. "
                "Code Mode executes pending tasks directly in source code files.",
                id="mode-tooltip",
            )
            with Horizontal():
                yield Button(
                    "Code Mode",
                    id="select-code-btn",
                    variant="primary",
                    classes="mode-btn",
                )
                yield Button(
                    "Plan Mode",
                    id="select-plan-btn",
                    variant="primary",
                    classes="mode-btn",
                )
                yield Button(
                    "Chat Mode",
                    id="select-chat-btn",
                    variant="default",
                    classes="mode-btn",
                )
                yield Button(
                    "Goal Mode",
                    id="select-goal-btn",
                    variant="success",
                    classes="mode-btn",
                )
                yield Button(
                    "Unified Mode",
                    id="select-unified-btn",
                    variant="warning",
                    classes="mode-btn",
                )
            yield Button("Cancel", id="cancel-mode-btn", variant="default")

    @on(Button.Pressed, "#select-code-btn")
    def select_code(self) -> None:
        self.dismiss("code")

    @on(Button.Pressed, "#select-chat-btn")
    def select_chat(self) -> None:
        self.dismiss("chat")

    @on(Button.Pressed, "#select-plan-btn")
    def select_plan(self) -> None:
        self.dismiss("plan")

    @on(Button.Pressed, "#select-goal-btn")
    def select_goal(self) -> None:
        self.dismiss("goal")

    @on(Button.Pressed, "#select-unified-btn")
    def select_unified(self) -> None:
        self.dismiss("unified")

    @on(Button.Pressed, "#cancel-mode-btn")
    def cancel_btn(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)





# ── Engine & TurboQuant Selector Modal ───────────────────────────────────


class EngineConfigModal(ModalScreen[Optional[dict]]):
    """Modal dialog for selecting Inference Engine and TurboQuant KV Cache mode."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    EngineConfigModal {
        align: center middle;
        background: #0d1117;
    }
    #engine-dialog {
        width: 90%;
        max-width: 76;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: solid $accent;
        padding: 1 2;
    }
    #engine-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #engine-desc {
        margin-bottom: 1;
    }
    #engine-info-box {
        background: $boost;
        color: $text-muted;
        padding: 1;
        margin: 1 0;
        border: solid $panel;
    }
    .engine-field-label {
        color: $text;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }
    #engine-backend-select, #engine-kv-select, #engine-model-select {
        width: 1fr;
        height: 1;
        margin-bottom: 1;
        border: none;
    }
    .engine-btn-row {
        height: 3;
        margin-top: 1;
        align: right middle;
    }
    .engine-modal-btn {
        border: none;
        padding: 0 2;
        height: 3;
        margin-left: 1;
    }
    """

    def __init__(
        self,
        current_engine: str = "llama.cpp",
        current_kv_mode: str = "turbo3",
        current_model: str = "",
    ):
        super().__init__()
        self.current_engine = current_engine or "llama.cpp"
        self.current_kv_mode = current_kv_mode or "turbo3"
        self.current_model = current_model or ""

    def _get_model_options_for_engine(self, engine: str) -> list[tuple[str, str]]:
        """Get model choices tailored to the selected inference backend."""
        from pathlib import Path
        options = []
        workspace = Path(__file__).parent.parent.resolve()
        models_dir = workspace / "models"
        engine_str = (engine or "llama.cpp").lower()

        if "mlx" in engine_str:
            from rlm_optimized.config import is_valid_mlx_directory
            # 1. ./models directory MLX model folders ONLY
            if models_dir.exists():
                for item in sorted(models_dir.iterdir()):
                    if is_valid_mlx_directory(str(item)):
                        options.append((item.name, str(item.resolve())))

            # 2. ~/.cache/huggingface/hub snapshots (verified complete only)
            hf_dir = Path.home() / ".cache" / "huggingface" / "hub"
            if hf_dir.exists():
                for item in sorted(hf_dir.glob("models--*mlx*")):
                    snaps_dir = item / "snapshots"
                    if snaps_dir.exists():
                        for snap in snaps_dir.iterdir():
                            if is_valid_mlx_directory(str(snap)):
                                clean_name = item.name.replace("models--mlx-community--", "").replace("models--", "")
                                if not any(clean_name in opt[0] or opt[1] == str(snap.resolve()) for opt in options):
                                    options.append((f"{clean_name} (HuggingFace)", str(snap.resolve())))
                                break

            # 3. Ensure popular MLX Coder, Gemma, and Reasoning models are available
            if not any("DeepSeek-R1" in opt[0] for opt in options):
                options.append(("DeepSeek-R1-Distill-Qwen-7B-4bit (MLX)", "mlx-community/DeepSeek-R1-Distill-Qwen-7B-4bit"))
            if not any("Qwen2.5-Coder-3B" in opt[0] for opt in options):
                options.append(("Qwen2.5-Coder-3B-Instruct-4bit (MLX)", "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"))
            if not any("Qwen2.5-Coder-7B" in opt[0] for opt in options):
                options.append(("Qwen2.5-Coder-7B-Instruct-4bit (MLX)", "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"))
            if not any("gemma-4-e4b" in opt[1].lower() for opt in options):
                options.append(("Gemma 4 E4B (MLX)", "mlx-community/gemma-4-E4B-it-4bit"))
            if not any("gemma-4-e2b" in opt[1].lower() for opt in options):
                options.append(("Gemma 4 E2B (MLX)", "mlx-community/gemma-4-E2B-it-4bit"))
            if not any("gemma-2-2b" in opt[1].lower() for opt in options):
                options.append(("Gemma 2 2B (MLX)", "mlx-community/gemma-2-2b-it-4bit"))

        elif "lmstudio" in engine_str:
            try:
                from rlm_optimized.config import fetch_provider_models, LMSTUDIO_BASE_URL
                lm_models = fetch_provider_models(LMSTUDIO_BASE_URL)
                for m_id in lm_models:
                    options.append((f"{m_id} (LM Studio)", m_id))
            except Exception:
                pass
            lmstudio_dir = Path.home() / ".lmstudio" / "models"
            if lmstudio_dir.exists():
                for gguf in sorted(lmstudio_dir.rglob("*.gguf")):
                    sz_mb = gguf.stat().st_size / (1024 * 1024)
                    options.append((f"{gguf.name} ({sz_mb:.0f}MB LMStudio)", str(gguf.resolve())))

        elif "ollama" in engine_str:
            try:
                from rlm_optimized.config import fetch_provider_models
                ol_models = fetch_provider_models("http://localhost:11434/v1")
                for m_id in ol_models:
                    options.append((f"{m_id} (Ollama)", m_id))
            except Exception:
                pass

        else:
            # 1. ./models directory GGUF models
            if models_dir.exists():
                for item in sorted(models_dir.iterdir()):
                    if item.is_file() and item.suffix == ".gguf":
                        sz_mb = item.stat().st_size / (1024 * 1024)
                        options.append((f"{item.name} ({sz_mb:.0f}MB)", str(item.resolve())))

            # 2. ~/.lmstudio/models GGUF models
            lmstudio_dir = Path.home() / ".lmstudio" / "models"
            if lmstudio_dir.exists():
                for gguf in sorted(lmstudio_dir.rglob("*.gguf")):
                    sz_mb = gguf.stat().st_size / (1024 * 1024)
                    if not any(opt[1] == str(gguf.resolve()) for opt in options):
                        options.append((f"{gguf.name} ({sz_mb:.0f}MB LMStudio)", str(gguf.resolve())))

        if not options:
            if "mlx" in engine_str:
                options = [
                    ("Gemma 4 E2B (MLX)", "mlx-community/gemma-4-E2B-it-4bit"),
                    ("Gemma 4 E4B (MLX)", "mlx-community/gemma-4-E4B-it-4bit"),
                    ("Qwen 2.5 Coder 3B (MLX)", "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"),
                ]
            else:
                options = [
                    ("Gemma 4 E2B (Auto-Download)", "gemma-4-E2B-it-Q4_K_M.gguf"),
                    ("Gemma 4 E4B (Auto-Download)", "gemma-4-E4B-it-Q4_K_M.gguf"),
                    ("Qwen 2.5 Coder 3B (Auto-Download)", "qwen2.5-coder-3b-instruct-q4_k_m.gguf"),
                ]
        return options

    def compose(self) -> ComposeResult:
        engine_options = [
            ("llama.cpp (Metal Shading Language + TurboQuant)", "llama.cpp"),
            ("Apple MLX (Native Metal Array Engine)", "mlx"),
            ("LM Studio (Local REST API Server)", "lmstudio"),
            ("Ollama (Local REST API Server)", "ollama"),
        ]

        kv_options = [
            ("turbo3 (3-bit TurboQuant — ~75% KV Memory Reduction)", "turbo3"),
            ("turbo4 (4-bit TurboQuant — Balanced Speed & Precision)", "turbo4"),
            ("f16 (Standard Baseline — Without TurboQuant)", "f16"),
        ]

        model_options = self._get_model_options_for_engine(self.current_engine)
        initial_model_val = self.current_model
        if not any(o[1] == initial_model_val for o in model_options):
            initial_model_val = model_options[0][1]

        with Vertical(id="engine-dialog"):
            yield Static("⚡ Inference Engine & TurboQuant Setup", id="engine-title")
            yield Static(
                "Configure your target execution backend and KV cache quantization scheme.\n"
                "• [bold]llama.cpp[/bold]: Ultra-low memory overhead (~150MB base) with hand-crafted Metal LUT shaders.\n"
                "• [bold]Apple MLX[/bold]: Python-native array execution with high generation throughput on M-series chips.\n"
                "• [bold]TurboQuant[/bold]: Compresses KV cache down to 3-bit / 4-bit, enabling 16k–32k context on 8GB/16GB Macs.",
                id="engine-desc",
            )
            yield Static(
                "💡 Tip: Select 'turbo3' or 'turbo4' for long multi-file coding sessions without swapping, "
                "or 'f16' for standard unquantized floating point operations.",
                id="engine-info-box",
            )

            yield Static("Select Inference Backend Engine:", classes="engine-field-label")
            yield Select(
                engine_options,
                value=self.current_engine if any(o[1] == self.current_engine for o in engine_options) else "llama.cpp",
                id="engine-backend-select",
                allow_blank=False,
            )

            yield Static("Select Model for Coding Agent:", classes="engine-field-label")
            yield Select(
                model_options,
                value=initial_model_val,
                id="engine-model-select",
                allow_blank=False,
            )

            yield Static("Select TurboQuant KV Cache Compression Mode:", classes="engine-field-label")
            yield Select(
                kv_options,
                value=self.current_kv_mode if any(o[1] == self.current_kv_mode for o in kv_options) else "turbo3",
                id="engine-kv-select",
                allow_blank=False,
            )

            with Horizontal(classes="engine-btn-row"):
                yield Button("Cancel", id="cancel-engine-btn", classes="engine-modal-btn")
                yield Button(
                    "Apply Engine Settings",
                    id="apply-engine-btn",
                    variant="primary",
                    classes="engine-modal-btn",
                )

    @on(Select.Changed, "#engine-backend-select")
    def on_engine_changed(self, event: Select.Changed) -> None:
        try:
            model_dropdown = self.query_one("#engine-model-select", Select)
            opts = self._get_model_options_for_engine(str(event.value))
            model_dropdown.set_options(opts)
            if opts:
                model_dropdown.value = opts[0][1]
        except Exception:
            pass

    @on(Button.Pressed, "#apply-engine-btn")
    def on_apply(self) -> None:
        try:
            eng = self.query_one("#engine-backend-select", Select).value
            model = self.query_one("#engine-model-select", Select).value
            kv = self.query_one("#engine-kv-select", Select).value
            self.dismiss({"engine": eng, "model": model, "kv_mode": kv})
        except Exception:
            self.dismiss(None)

    @on(Button.Pressed, "#cancel-engine-btn")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ── File Action Modal (OS Tool Selector) ────────────────────────────────


class FileActionModal(ModalScreen[str]):
    """Clean, minimalist modal dialog presenting file options (right-click context menu)."""

    BINDINGS = [
        ("escape", "action_cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    FileActionModal {
        align: center middle;
        background: #0d1117;
    }
    #file-action-dialog {
        width: 90%;
        max-width: 52;
        height: auto;
        padding: 1 2;
        background: #161b22;
        border: solid #30363d;
    }
    .file-action-title {
        text-align: center;
        margin-bottom: 1;
        color: #e6edf3;
    }
    .file-action-btn {
        width: 100%;
        height: 3;
        margin-top: 1;
        background: #21262d;
        color: #c9d1d9;
        border: none;
        padding: 0 1;
        text-align: center;
    }
    .file-action-btn:hover {
        background: #30363d;
        color: #ffffff;
        text-style: bold;
    }
    .file-action-btn:focus {
        background: #30363d;
        color: #ffffff;
        border: none;
    }
    """

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = os.path.abspath(file_path)
        self.filename = os.path.basename(self.file_path)

    def compose(self) -> ComposeResult:
        with Vertical(id="file-action-dialog"):
            yield Static(
                f"[bold]{escape(self.filename)}[/bold]\n"
                f"[dim]{escape(self.file_path)}[/dim]",
                classes="file-action-title",
            )
            yield Button(
                "Open with System Default App",
                id="act-open-system",
                variant="default",
                classes="file-action-btn",
            )
            yield Button(
                "Open in VS Code / Editor",
                id="act-open-code",
                variant="default",
                classes="file-action-btn",
            )
            yield Button(
                "Copy Absolute File Path",
                id="act-copy-path",
                variant="default",
                classes="file-action-btn",
            )
            yield Button(
                "Cancel", id="act-cancel", variant="default", classes="file-action-btn"
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
        width: 92%;
        max-width: 88;
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


class TaskManagerModal(ModalScreen[None]):
    """Modal dialog for interactive workspace task management & inspection."""

    BINDINGS = [
        ("escape", "dismiss_modal", "Close"),
        ("c", "mark_completed", "Complete Task"),
        ("s", "mark_skipped", "Skip Task"),
        ("r", "refresh_view", "Refresh"),
    ]

    DEFAULT_CSS = """
    TaskManagerModal {
        align: center middle;
    }
    #task-manager-dialog {
        width: 90%;
        max-width: 80;
        height: 70%;
        background: $surface;
        border: solid $accent;
        padding: 1 2;
    }
    """

    def __init__(self, project_root: str):
        super().__init__()
        self.project_root = project_root

    def compose(self) -> ComposeResult:
        from rlm_optimized.tui_widgets.task_tree import TaskTreeWidget

        with VerticalScroll(id="task-manager-dialog"):
            yield Static(
                "[bold cyan]📋 Workspace Task Manager[/] [dim](Press [C] Complete, [S] Skip, [Esc] Close)[/]\n"
            )
            yield TaskTreeWidget(self.project_root, id="modal-task-tree")

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    def action_mark_completed(self) -> None:
        from core.tools.task_helpers import (
            get_active_task_description,
            mark_task_status,
        )

        active_desc = get_active_task_description(self.project_root)
        if active_desc:
            mark_task_status(self.project_root, active_desc, status="completed")
            self.action_refresh_view()

    def action_mark_skipped(self) -> None:
        from core.tools.task_helpers import (
            get_active_task_description,
            mark_task_status,
        )

        active_desc = get_active_task_description(self.project_root)
        if active_desc:
            mark_task_status(self.project_root, active_desc, status="skipped")
            self.action_refresh_view()

    def action_refresh_view(self) -> None:
        try:
            from rlm_optimized.tui_widgets.task_tree import TaskTreeWidget

            tree = self.query_one("#modal-task-tree", TaskTreeWidget)
            tree.update_tasks(self.project_root)
        except Exception:  # noqa: BLE001, S110
            pass


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
        width: 90%;
        max-width: 76;
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
- **Ctrl+L** — Wipe Session Context (Start Fresh)
- **Ctrl+B** — Toggle Sidebar
- **Ctrl+T** — Cycle Theme
- **Ctrl+O** — Change Working Directory (Computer Wide)
- **Ctrl+H** — Open Shortcuts & Help Modal
- **Ctrl+A** — Open Telemetry & Status
- **Ctrl+X** — Copy Selection
- **Ctrl+Y** — Copy Entire Chat History
- **Ctrl+E** — Copy Last Response
- **Ctrl+C** — Quit Application

### 🛠️ Slash Commands
- `/new` / `/wipe` / `/clear` — Completely wipe session context & start fresh
- `/compact` / `/compress` — Manually compact context memory
- `/start` / `/restart` / `/stop` — Engine server control
- `/model <name>` — Switch active model
- `/cd <path>` — Change directory
- `/index` — Build AST Knowledge Graph
- `/status` — Open telemetry modal
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


class PaneResizer(Static):
    """Interactive splitter bar to resize the left/right side panes.

    Drag the bar horizontally to resize; a click without dragging nudges the
    adjacent pane by 2 columns (left click expands, right click shrinks).
    """

    DEFAULT_CSS = """
    PaneResizer {
        width: 1;
        height: 100%;
        background: $panel;
        color: $text-muted;
        content-align: center middle;
    }
    PaneResizer:hover {
        background: $primary;
        color: $text-primary;
    }
    """

    MIN_WIDTH = 14
    MAX_WIDTH = 60

    def __init__(self, target_pane: str, id: str | None = None) -> None:
        super().__init__("│", id=id)
        self.target_pane = target_pane  # "left" or "right"
        self._dragging = False
        self._drag_moved = False

    def _clamp(self, width: int) -> int:
        if self.target_pane == "editor":
            return max(20, min(140, width))
        return max(self.MIN_WIDTH, min(self.MAX_WIDTH, width))

    def _expand(self) -> None:
        if self.target_pane == "left":
            self.app.action_expand_left_pane()
        elif self.target_pane == "editor":
            self.app.action_expand_editor_pane()
        else:
            self.app.action_expand_right_pane()

    def _shrink(self) -> None:
        if self.target_pane == "left":
            self.app.action_shrink_left_pane()
        elif self.target_pane == "editor":
            self.app.action_shrink_editor_pane()
        else:
            self.app.action_shrink_right_pane()

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button == 1:
            self._dragging = True
            self._drag_moved = False
            self.capture_mouse()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if not self._dragging or not event.delta_x:
            return
        self._drag_moved = True
        if self.target_pane == "left":
            width = getattr(self.app, "left_pane_width", 24) + event.delta_x
            width = self._clamp(width)
            self.app.left_pane_width = width
        elif self.target_pane == "editor":
            width = getattr(self.app, "editor_pane_width", 50) + event.delta_x
            width = self._clamp(width)
            self.app.editor_pane_width = width
        else:
            width = getattr(self.app, "right_pane_width", 30) - event.delta_x
            width = self._clamp(width)
            self.app.right_pane_width = width
        self.app._apply_pane_widths()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self._dragging:
            self._dragging = False
            self.release_mouse()

    def on_click(self, event: events.Click) -> None:
        if self._drag_moved:
            self._drag_moved = False
            return  # already resized by the preceding drag
        if event.button == 1:
            self._expand()
        elif event.button in (2, 3):
            self._shrink()


class EditorTab(Static):
    """Clean single-line tab widget displaying file name with close button."""

    DEFAULT_CSS = """
    EditorTab {
        height: 1;
        min-height: 1;
        max-height: 1;
        width: auto;
        min-width: 6;
        background: $surface;
        color: $foreground-muted;
        padding: 0 1;
        margin: 0 1 0 0;
        border: none;
    }
    EditorTab.-active {
        background: $background;
        color: $primary;
        text-style: bold;
    }
    EditorTab:hover {
        background: $panel;
        color: $foreground;
    }
    """

    class TabSelected(Message):
        """Emitted when tab is clicked to switch active file."""

        def __init__(self, file_path: str) -> None:
            self.file_path = file_path
            super().__init__()

    class TabClosed(Message):
        """Emitted when tab close button '×' is clicked."""

        def __init__(self, file_path: str) -> None:
            self.file_path = file_path
            super().__init__()

    class TabRightClicked(Message):
        """Emitted when tab is right-clicked."""

        def __init__(self, file_path: str) -> None:
            self.file_path = file_path
            super().__init__()

    def __init__(
        self,
        file_path: str,
        filename: str,
        is_active: bool = False,
        dirty: bool = False,
        **kwargs,
    ) -> None:
        self.file_path = file_path
        self.filename = filename
        self.is_active = is_active
        self.dirty = dirty
        classes = "-active" if is_active else ""
        super().__init__(self._build_label(), classes=classes, **kwargs)

    def _build_label(self) -> str:
        from core.utils.image_utils import is_image_file

        icon = "🖼 " if is_image_file(self.file_path) else ""
        dot = "● " if self.dirty else ""
        return f"{dot}{icon}{self.filename}  ×"

    def update_tab(self, is_active: bool, dirty: bool) -> None:
        self.is_active = is_active
        self.dirty = dirty
        if is_active:
            self.add_class("-active")
        else:
            self.remove_class("-active")
        self.update(self._build_label())

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button in (2, 3):
            event.stop()
            self.post_message(self.TabRightClicked(self.file_path))

    def on_click(self, event: events.Click) -> None:
        event.stop()
        if event.button in (2, 3):
            self.post_message(self.TabRightClicked(self.file_path))
            return

        label_len = len(self._build_label())
        # The '×' is located near the right edge of the label
        if event.x >= label_len - 2:
            self.post_message(self.TabClosed(self.file_path))
        else:
            self.post_message(self.TabSelected(self.file_path))


class TorchlightApp(App):
    """Codex / Tiny-Brain 2 Style Agent IDE TUI."""

    TITLE = "Torchlight Codex IDE"
    SUB_TITLE = "Autonomous Agent TUI"
    CSS_PATH = "tui_app.tcss"

    BINDINGS = [
        Binding("ctrl+p", "command_palette", "Command Palette", show=False),
        Binding("ctrl+h", "show_help", "Help", show=True),
        Binding("ctrl+g", "select_mode", "Mode", show=False),
        Binding("ctrl+b", "toggle_left_sidebar", "Left Sidebar", show=True),
        Binding("ctrl+r", "toggle_right_sidebar", "Right Sidebar", show=True),
        Binding("ctrl+shift+left", "shrink_left_pane", "Shrink Left Pane", show=False),
        Binding("ctrl+shift+right", "expand_left_pane", "Expand Left Pane", show=False),
        Binding("alt+shift+left", "shrink_right_pane", "Shrink Right Pane", show=False),
        Binding(
            "alt+shift+right", "expand_right_pane", "Expand Right Pane", show=False
        ),
        Binding("ctrl+t", "cycle_theme", "Theme", show=False),
        Binding("ctrl+n", "compact_context", "Compact Context", show=True),
        Binding("ctrl+o", "open_folder", "Open Folder", show=False),
        Binding("ctrl+u", "attach_context", "Attach Context", show=True),
        Binding("ctrl+v", "paste_image", "Paste Image", show=False),
        Binding("ctrl+k", "task_manager", "Tasks", show=True),
        Binding("ctrl+a", "toggle_status_modal", "Agent Telemetry", show=False),
        Binding("ctrl+x", "copy_selection", "Copy Selection", show=False),
        Binding("ctrl+y", "copy_chat", "Copy Chat", show=False),
        Binding("ctrl+e", "copy_last", "Copy Last", show=False),
        Binding("ctrl+l", "wipe_session", "Wipe Session Context", show=True),
        Binding("ctrl+w", "wipe_session", "New Session", show=False),
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+\\", "toggle_editor_split", "Editor Split", show=False),
        Binding("ctrl+shift+e", "engine_config", "Engine & TurboQuant", show=False),
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
        self._show_plan_sidebar = True
        self.left_pane_width: int = 24
        self.right_pane_width: int = 30
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
        self._editor_split_refresh_pending = False
        self._token_throttle_last: float = 0.0
        self._token_throttle_interval: float = 0.03
        self._file_tree: Optional[GitFileTree] = None
        self._user_input: Optional[PromptTextArea] = None
        self._status_bar: Optional[StatusBar] = None
        # UX Overhaul v2 — new widgets
        self._connection_pill: Optional[ConnectionPill] = None
        self._center_empty_state: Optional[CenterEmptyState] = None
        self._model_connected: bool = False  # tracks live connection state

    @property
    def project_root(self) -> str:
        """Return the current project root path from engine or working directory."""
        if hasattr(self, "engine") and getattr(self.engine, "project_root", None):
            return self.engine.project_root
        return os.getcwd()

    @property
    def _is_test_env(self) -> bool:
        import sys

        return (
            getattr(self, "is_headless", False)
            or getattr(self, "_test_runner", None) is not None
            or "pytest" in sys.modules
        )

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

        # Mirror tool events into the Output tab
        try:
            tool_name = details.get("tool_name", "")
            path_hint = details.get("path", details.get("file_path", ""))
            if state == "TOOL":
                label = f"[{ts}] ▶ {tool_name}"
                if path_hint:
                    label += f"  →  {path_hint}"
                self.append_output_log(label, severity="tool")
            elif state == "TOOL_DONE":
                self.append_output_log(f"[{ts}] ✓ {tool_name} done", severity="info")
            elif state == "TOOL_DENIED":
                self.append_output_log(f"[{ts}] ✗ {tool_name} denied", severity="error")
            elif state == "WAITING_APPROVAL":
                self.append_output_log(
                    f"[{ts}] ⏸ Waiting approval: {tool_name}", severity="tool"
                )
        except Exception:
            pass

        try:
            self.call_after_refresh(self.update_status_bar)
        except Exception:
            self.update_status_bar()

        try:
            memory_widget = self.query_one("#agent-memory-panel", AgentMemoryWidget)
            self.call_after_refresh(memory_widget.update_memory)
        except Exception:
            pass

    def _handle_tasks_changed(self, snapshot: dict) -> None:
        """Realtime task-state updates surfaced to the Output log."""
        try:
            import datetime as _dt

            ts = _dt.datetime.now().strftime("%H:%M:%S")
            pending = snapshot.get("pending", [])
            done = snapshot.get("completed", 0)
            running = snapshot.get("in_progress", 0)
            label = (
                f"[{ts}] 📋 Tasks: {done} done, {running} running, "
                f"{len(pending)} pending"
            )
            self.append_output_log(label, severity="info")
            for p in pending[:3]:
                self.append_output_log(f"[{ts}]   ⏳ {p}", severity="info")
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        # Top HUD Header
        with Horizontal(id="top-hud-header"):
            yield Static("⚡ TORCHLIGHT CODEX", id="hud-title")
            yield Static("", id="hud-spacer")
            # Connection pill — replaces both the red error banner and Load Model btn
            self._connection_pill = ConnectionPill(
                connected=False,
                model_name=self.model_name,
                id="connection-pill",
            )
            yield self._connection_pill
            mode_lbl = self._get_active_mode_label()
            mode_cls = (
                "mode-badge-goal"
                if "GOAL" in mode_lbl
                else "mode-badge-plan"
                if "PLAN" in mode_lbl
                else "mode-badge-unified"
                if "UNIFIED" in mode_lbl
                else "mode-badge-chat"
            )
            yield Button(
                f"MODE: {mode_lbl}",
                id="mode-toggle-btn",
                classes=mode_cls,
            )

            yield Button(
                "⚡ Wipe",
                id="wipe-context-btn",
                variant="error",
                tooltip="Completely wipe session context & start fresh (Ctrl+L or /new)",
            )
            yield Button(
                "Compact",
                id="compact-btn",
                variant="warning",
                tooltip="Manually compact context memory (Ctrl+N or /compact)",
            )
            yield Button(
                "Help",
                id="help-btn",
                variant="default",
                tooltip="Shortcuts & Command Help (Ctrl+H)",
            )

        with Horizontal(id="main-ide-container"):
            # 1. Left Explorer Sidebar (Files)
            with Vertical(id="explorer-sidebar"):
                yield Static(
                    "EXPLORER / BLUEPRINT WORKSPACE", classes="panel-header-title"
                )
                if getattr(self, "_test_runner", False):
                    yield Static("[dim]Workspace tree[/dim]", id="file-tree")
                else:
                    try:
                        p = self.engine.project_root if (hasattr(self, "engine") and getattr(self.engine, "project_root", None) and os.path.exists(self.engine.project_root)) else "."
                        self._file_tree = GitFileTree(p, id="file-tree")
                        yield self._file_tree
                    except Exception:
                        yield Static("[dim]Workspace tree unavailable[/dim]", id="file-tree")
            yield PaneResizer("left", id="resizer-left")

            # 2. Tabbed Editor Split Pane (Hidden by default when no tabs open to maintain a clean 3-panel layout)
            editor_pane = Vertical(id="editor-split-pane")
            editor_pane.display = bool(self._open_tabs)
            with editor_pane:
                with Horizontal(id="tab-bar-header"):
                    with Horizontal(id="tab-buttons-container"):
                        pass
                    yield Button(
                        "≡",
                        id="toggle-split-btn",
                        classes="tab-close-btn",
                    )
                with Vertical(id="editor-content-area"):
                    self._center_empty_state = CenterEmptyState(
                        state=STATE_DISCONNECTED,
                        id="center-empty-state",
                    )
                    yield self._center_empty_state
            resizer_editor = PaneResizer("editor", id="resizer-editor")
            resizer_editor.display = bool(self._open_tabs)
            yield resizer_editor

            # 3. Main Center Area: Agent Terminal, Reasoning Trajectory & Logs
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
                    yield Horizontal(id="context-chips-bar")
                    with Vertical(id="user-input-card"):
                        self._user_input = PromptTextArea(
                            id="user-input",
                            language=None,
                            show_line_numbers=False,
                            soft_wrap=True,
                            tab_behavior="indent",
                            suggestion_callback=self._on_suggestion_matches,
                        )
                        yield self._user_input
                        with Horizontal(id="input-toolbar"):
                            with Horizontal(id="toolbar-left-controls"):
                                yield Button(
                                    "+",
                                    id="attach-context-btn",
                                    tooltip="Attach Context (Ctrl+U)",
                                )
                                mode_opts = self._get_mode_select_options()
                                initial_mode = self._get_current_mode_val()
                                yield Select(
                                    mode_opts,
                                    value=initial_mode,
                                    allow_blank=False,
                                    id="mode-select-dropdown",
                                    tooltip="Select Execution Mode (Unified / Goal / Chat)",
                                )
                                model_opts = self._get_model_select_options()
                                matching_val = next(
                                    (
                                        m[1]
                                        for m in model_opts
                                        if m[1] == self.model_name
                                        or normalize_model_name(m[1]) == normalize_model_name(self.model_name)
                                        or m[1] in self.model_name
                                        or self.model_name in m[1]
                                    ),
                                    None,
                                )
                                initial_val = (
                                    matching_val
                                    if matching_val is not None
                                    else (model_opts[0][1] if model_opts else self.model_name)
                                )
                                yield Select(
                                    model_opts,
                                    value=initial_val,
                                    allow_blank=False,
                                    id="model-select-dropdown",
                                    tooltip="Select Model & Engine",
                                )
                                yield Button(
                                    "UNLOAD" if self._is_model_connected() else "LOAD",
                                    id="model-toggle-btn",
                                    variant="error" if self._is_model_connected() else "primary",
                                    tooltip="Load or Unload selected model",
                                )
                            with Horizontal(id="toolbar-right-actions"):
                                yield Static("", id="input-spinner")
                                yield Button(
                                    "SEND ↗",
                                    id="send-btn",
                                    variant="primary",
                                    disabled=False,
                                    tooltip="Send message (Enter or Ctrl+Enter)",
                                )
                    yield ListView(id="input-suggestions")

            yield PaneResizer("right", id="resizer-right")

            # 4. Right Sidebar: 3-tab IA (Agent / Plan / Output)
            with Vertical(id="plan-sidebar"):
                with TabbedContent():
                    # ── Tab: Agent ─────────────────────────────────────
                    with TabPane("Agent", id="tab-agent"):
                        with VerticalScroll(id="agent-tab-scroll"):
                            yield Static(
                                "CONNECTION",
                                classes="sidebar-section-title",
                            )
                            yield Static("", id="agent-tab-conn-status")
                            yield Static(
                                "MODEL INFO",
                                classes="sidebar-section-title",
                            )
                            yield Static("", id="agent-tab-model-info")
                            yield Static(
                                "CONTEXT USAGE",
                                classes="sidebar-section-title",
                            )
                            yield Static("", id="agent-tab-context-bar")
                            with Horizontal(id="agent-tab-context-actions"):
                                yield Button(
                                    "🧹 Compact",
                                    id="agent-compact-btn",
                                    variant="warning",
                                    tooltip="Manually compact context memory (Ctrl+N)",
                                )
                                yield Button(
                                    "⚡ Wipe",
                                    id="agent-wipe-btn",
                                    variant="error",
                                    tooltip="Completely wipe session context & start fresh (Ctrl+L)",
                                )
                                yield Button(
                                    "▸ Breakdown",
                                    id="toggle-breakdown-btn",
                                    classes="sidebar-toggle-btn",
                                    tooltip="Toggle detailed context breakdown",
                                )
                            yield Static("", id="agent-tab-ctx-breakdown")
                            yield Static(
                                "WORKING MEMORY",
                                classes="sidebar-section-title",
                            )
                            yield AgentMemoryWidget(id="agent-memory-panel")
                    # ── Tab: Plan ──────────────────────────────────────
                    with TabPane("Plan", id="tab-tasks"):
                        with VerticalScroll(id="plan-scroll"):
                            yield Static(
                                self._build_plan_text(),
                                id="plan-panel",
                            )
                    # ── Tab: Output ────────────────────────────────────
                    with TabPane("Output", id="tab-output"):
                        with VerticalScroll(id="output-log-scroll"):
                            yield Static(
                                "[dim]Tool output and agent traces will appear here.[/dim]",
                                id="output-log-content",
                            )
                    # ── Tab: Skills ────────────────────────────────────
                    with TabPane("Skills", id="tab-skills"):
                        with VerticalScroll(id="skills-tab-scroll"):
                            yield Static(
                                "SKILL ACTIONS",
                                classes="sidebar-section-title",
                            )
                            with Horizontal(id="skills-action-bar"):
                                yield Button(
                                    "Import Skill",
                                    id="upload-skill-btn",
                                    variant="primary",
                                    tooltip="Import external SKILL.md or .py into workspace",
                                )
                                yield Button(
                                    "Refresh",
                                    id="refresh-skills-btn",
                                    variant="default",
                                    tooltip="Reload skills from workspace and global directories",
                                )
                            yield Static("", id="skills-status-msg")
                            yield Static(
                                "AVAILABLE SKILLS",
                                classes="sidebar-section-title",
                            )
                            yield Static(
                                self._build_skills_text(),
                                id="skills-list-panel",
                            )
                    # ── Tab: Model & Engine ────────────────────────────
                    with TabPane("Model", id="tab-engine-model"):
                        with VerticalScroll(id="engine-tab-scroll"):
                            raw_p = (getattr(self, "provider_name", "llama.cpp") or "llama.cpp").lower()
                            if "mlx" in raw_p:
                                engine_init = "mlx"
                            elif "lmstudio" in raw_p:
                                engine_init = "lmstudio"
                            elif "ollama" in raw_p:
                                engine_init = "ollama"
                            else:
                                engine_init = "llama.cpp"

                            raw_kv = (getattr(self, "kv_cache_mode", "turbo3") or "turbo3").lower()
                            kv_init = raw_kv if raw_kv in ("turbo3", "turbo4", "f16") else "turbo3"

                            raw_ctx = getattr(self, "context_window_size", 12288) or 12288
                            ctx_init = raw_ctx if raw_ctx in (4096, 8192, 12288, 16384, 32768) else 12288

                            yield Static(
                                "INFERENCE ENGINE",
                                classes="sidebar-section-title",
                            )
                            yield Select(
                                [
                                    ("llama.cpp (Metal + TurboQuant)", "llama.cpp"),
                                    ("Apple MLX (Native Metal)", "mlx"),
                                    ("LM Studio (Local REST API)", "lmstudio"),
                                    ("Ollama (Local REST API)", "ollama"),
                                ],
                                value=engine_init,
                                id="sidebar-engine-select",
                                allow_blank=False,
                                tooltip="Select LLM inference execution backend",
                            )
                            yield Static(
                                "KV CACHE (TurboQuant)",
                                classes="sidebar-section-title",
                            )
                            yield Select(
                                [
                                    ("turbo3 (3-bit TurboQuant — ~75% Mem)", "turbo3"),
                                    ("turbo4 (4-bit TurboQuant — Balanced)", "turbo4"),
                                    ("f16 (Standard / No TurboQuant)", "f16"),
                                ],
                                value=kv_init,
                                id="sidebar-kv-select",
                                allow_blank=False,
                                tooltip="Select KV cache quantization mode",
                            )

                            yield Button(
                                "Apply & Restart Engine",
                                id="sidebar-apply-engine-btn",
                                variant="primary",
                                tooltip="Apply engine & parameter changes and restart local backend",
                            )
                            yield Static("", id="sidebar-engine-status-msg")

        # Bottom Telemetry — single clean StatusBar (context-meter-bar removed)
        with Vertical(id="telemetry-bar"):
            self._status_bar = StatusBar(id="status-bar")
            yield self._status_bar

        # Bottom Navigation Dock
        with Horizontal(id="bottom-nav-dock"):
            yield Button(
                "📄 SHELL",
                id="dock-btn-shell",
                classes="nav-dock-btn nav-dock-btn-active",
            )
            yield Button(
                "📖 CONTEXT",
                id="dock-btn-context",
                classes="nav-dock-btn",
            )
            yield Button(
                "📋 LOGS",
                id="dock-btn-goal",
                classes="nav-dock-btn",
            )
            yield Button(
                "⚙️ SYS",
                id="dock-btn-sys",
                classes="nav-dock-btn",
            )

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

            if abs_path not in self._open_tabs:
                self._open_tabs[abs_path] = {"dirty": False, "filename": filename}
            self._active_tab_path = abs_path
            # Hide empty state when a file is open
            self._set_center_empty_state_visible(False)
            self._refresh_editor_split_view()
        except Exception as e:
            try:
                self.notify(f"Error opening file: {e}", severity="warning", timeout=2)
            except Exception:
                pass

    def show_file_actions(self, file_path: str) -> None:
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
            try:
                self.notify(f"File action error: {e}", severity="warning", timeout=2)
            except Exception:
                pass

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
        self._do_refresh_editor_split_view()

    def _do_refresh_editor_split_view(self) -> None:
        self._editor_split_refresh_pending = False
        try:
            tab_container = self.query_one("#tab-buttons-container")
            content_area = self.query_one("#editor-content-area")
        except Exception:
            return

        try:
            editor_pane = self.query_one("#editor-split-pane")
            is_visible = bool(self._open_tabs)
            editor_pane.display = is_visible
            try:
                resizer_editor = self.query_one("#resizer-editor")
                resizer_editor.display = is_visible
            except Exception:
                pass
        except Exception:
            pass

        if not self._open_tabs:
            return

        current_hashes = {self._get_tab_hash(p) for p in self._open_tabs}
        valid_ids = {f"tab_{h}" for h in current_hashes}
        for child in list(tab_container.children):
            if child.id and child.id not in valid_ids:
                child.remove()

        existing_tab_ids = {c.id for c in tab_container.children if c.id}

        for path, meta in self._open_tabs.items():
            filename = meta.get("filename", os.path.basename(path))
            h = self._get_tab_hash(path)
            is_active = path == self._active_tab_path
            dirty = meta.get("dirty", False)
            tab_id = f"tab_{h}"

            if tab_id in existing_tab_ids:
                try:
                    tab_w = tab_container.query_one(f"#{tab_id}", EditorTab)
                    tab_w.update_tab(is_active=is_active, dirty=dirty)
                except Exception:
                    pass
            else:
                tab_w = EditorTab(
                    file_path=path,
                    filename=filename,
                    is_active=is_active,
                    dirty=dirty,
                    id=tab_id,
                )
                tab_container.mount(tab_w)

        if self._active_tab_path and self._active_tab_path in self._open_tabs:
            from core.utils.image_utils import is_image_file
            from rlm_optimized.tui_widgets.image_viewer import ImageViewer, BinaryFileViewer

            if is_image_file(self._active_tab_path):
                existing_iv = None
                try:
                    existing_iv = content_area.query_one("#active-image-viewer", ImageViewer)
                except Exception:
                    pass

                if existing_iv is not None and getattr(existing_iv, "_image_path", None) == self._active_tab_path:
                    pass
                else:
                    content_area.remove_children()
                    viewer = ImageViewer(
                        image_path=self._active_tab_path,
                        project_root=self.engine.project_root,
                        id="active-image-viewer",
                    )
                    content_area.mount(viewer)
                return

            # Check if file is a non-image binary file
            is_binary = False
            try:
                with open(self._active_tab_path, "rb") as bf:
                    chunk = bf.read(1024)
                    if b"\x00" in chunk:
                        is_binary = True
            except OSError:
                pass

            if is_binary:
                existing_bv = None
                try:
                    existing_bv = content_area.query_one("#active-binary-viewer", BinaryFileViewer)
                except Exception:
                    pass

                if existing_bv is not None and getattr(existing_bv, "_file_path", None) == self._active_tab_path:
                    pass
                else:
                    content_area.remove_children()
                    viewer = BinaryFileViewer(
                        file_path=self._active_tab_path,
                        id="active-binary-viewer",
                    )
                    content_area.mount(viewer)
                return

            try:
                with open(
                    self._active_tab_path, "r", encoding="utf-8", errors="replace"
                ) as f:
                    content = f.read()
            except OSError:
                content = ""

            ext = os.path.splitext(self._active_tab_path)[1].lstrip(".")
            lang_map = {
                "py": "python",
                "js": "javascript",
                "ts": "typescript",
                "tsx": "typescript",
                "jsx": "javascript",
                "go": "go",
                "rs": "rust",
                "rb": "ruby",
                "c": "c",
                "h": "c",
                "cpp": "cpp",
                "hpp": "cpp",
                "java": "java",
                "cfg": "ini",
                "toml": "toml",
                "yaml": "yaml",
                "yml": "yaml",
                "json": "json",
                "md": "markdown",
                "html": "html",
                "css": "css",
                "sh": "bash",
                "bash": "bash",
                "zsh": "bash",
            }
            language = lang_map.get(ext, "text")

            try:
                from rich.syntax import Syntax

                txt = Syntax(content, language, line_numbers=True, theme="monokai")
            except Exception:
                txt = content
            try:
                editor_view = content_area.query_one("#active-editor-view", Static)
                editor_view.update(txt)
            except Exception:
                content_area.remove_children()
                editor = Static(
                    txt,
                    id="active-editor-view",
                    classes="editor-view",
                )
                content_area.mount(editor)
        else:
            # Mount center empty state when no files are open
            is_online = getattr(self, "_last_server_online", False)
            st = STATE_IDLE if is_online else STATE_DISCONNECTED
            if (
                self._center_empty_state is None
                or not self._center_empty_state.is_attached
            ):
                self._center_empty_state = CenterEmptyState(
                    state=st,
                    id="center-empty-state",
                )
            content_area.mount(self._center_empty_state)
            self._center_empty_state.set_connection_state(
                st,
                model_name=self.model_name if is_online else "",
            )
            self._center_empty_state.display = True

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

    @on(GitFileTree.FileRightClicked)
    def on_file_right_clicked(self, event: GitFileTree.FileRightClicked) -> None:
        path = getattr(event, "path", None)
        if path:
            abs_path = os.path.abspath(str(path))
            if os.path.isfile(abs_path):
                self.show_file_actions(abs_path)

    @on(EditorTab.TabSelected)
    def on_editor_tab_selected(self, event: EditorTab.TabSelected) -> None:
        self.open_file_tab(event.file_path)

    @on(EditorTab.TabClosed)
    def on_editor_tab_closed(self, event: EditorTab.TabClosed) -> None:
        self.close_file_tab(event.file_path)

    @on(EditorTab.TabRightClicked)
    def on_editor_tab_right_clicked(self, event: EditorTab.TabRightClicked) -> None:
        self.show_file_actions(event.file_path)

    @on(events.MouseDown)
    def on_app_mouse_down(self, event: events.MouseDown) -> None:
        if event.button in (2, 3):  # Secondary / Right click
            widget = getattr(event, "widget", None)
            if widget and hasattr(widget, "id") and widget.id:
                btn_id = widget.id
                if btn_id.startswith("tab_") or btn_id.startswith("tsel_") or btn_id.startswith("tcls_"):
                    h_target = btn_id.split("_", 1)[1]
                    for path in self._open_tabs.keys():
                        if self._get_tab_hash(path) == h_target:
                            event.stop()
                            self.show_file_actions(path)
                            return
                elif btn_id == "active-editor-view" and self._active_tab_path:
                    event.stop()
                    self.show_file_actions(self._active_tab_path)
                    return

    @on(events.Click)
    def on_app_mouse_click(self, event: events.Click) -> None:
        if event.button in (2, 3):  # Secondary / Right click
            widget = getattr(event, "widget", None)
            if widget and hasattr(widget, "id") and widget.id:
                btn_id = widget.id
                if btn_id.startswith("tab_") or btn_id.startswith("tsel_") or btn_id.startswith("tcls_"):
                    h_target = btn_id.split("_", 1)[1]
                    for path in self._open_tabs.keys():
                        if self._get_tab_hash(path) == h_target:
                            event.stop()
                            self.show_file_actions(path)
                            return
                elif btn_id == "active-editor-view" and self._active_tab_path:
                    event.stop()
                    self.show_file_actions(self._active_tab_path)
                    return

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
                import time as _t
                now_sys = _t.time()
                if now_sys - getattr(self, "_vm_stat_ts", 0.0) < 5.0 and hasattr(self, "_vm_stat_ram_pct"):
                    ram_pct = self._vm_stat_ram_pct
                else:
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
                    self._vm_stat_ts = now_sys
                    self._vm_stat_ram_pct = ram_pct
            except Exception:
                ram_pct = 0

        # Context Token Calculation
        tokens_est = self._live_context_tokens()

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

        is_engine_ready = self.engine_port <= 0 or getattr(
            self, "_last_server_online", False
        )
        status_badge = (
            "[bold green]● ENGINE READY[/bold green]"
            if is_engine_ready
            else "[bold red]○ ENGINE OFFLINE (Port 1234)[/bold red]"
        )

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

    def _is_goal_mode(self) -> bool:
        mode = getattr(self.engine, "execution_mode", "chat")
        if hasattr(mode, "value"):
            mode = mode.value
        return str(mode).lower() == "goal"

    def _build_plan_overview_text(self) -> str:
        import time as _t
        now = _t.time()
        if now - getattr(self, "_plan_overview_ts", 0.0) < 2.0 and hasattr(self, "_plan_overview_cache"):
            return self._plan_overview_cache
        project_root = getattr(self.engine, "project_root", os.getcwd())
        res = build_plan_overview_text(project_root, self._is_goal_mode(), mode=self._get_current_mode_val())
        self._plan_overview_ts = now
        self._plan_overview_cache = res
        return res

    def _build_task_checklist_text(self) -> str:
        import time as _t
        now = _t.time()
        if now - getattr(self, "_task_checklist_ts", 0.0) < 2.0 and hasattr(self, "_task_checklist_cache"):
            return self._task_checklist_cache
        project_root = getattr(self.engine, "project_root", os.getcwd())
        res = build_task_checklist_text(project_root, self._is_goal_mode())
        self._task_checklist_ts = now
        self._task_checklist_cache = res
        return res

    def _build_plan_text(self) -> str:
        import time as _t
        now = _t.time()
        if now - getattr(self, "_plan_text_ts", 0.0) < 2.0 and hasattr(self, "_plan_text_cache"):
            return self._plan_text_cache
        project_root = getattr(self.engine, "project_root", os.getcwd())
        res = build_plan_text(project_root, self._is_goal_mode(), mode=self._get_current_mode_val())
        self._plan_text_ts = now
        self._plan_text_cache = res
        return res

    def _build_skills_text(self, reload: bool = False) -> str:
        import time as _t
        now = _t.time()
        if not reload and now - getattr(self, "_skills_text_ts", 0.0) < 2.0 and hasattr(self, "_skills_text_cache"):
            return self._skills_text_cache
        project_root = getattr(self.engine, "project_root", os.getcwd())
        res = build_skills_overview_text(project_root, reload=reload)
        self._skills_text_ts = now
        self._skills_text_cache = res
        return res

    def _build_context_progress_text(self) -> str:
        tokens_est = self._live_context_tokens()

        ctx_max = CTX_SIZE
        pct = min(100, int((tokens_est / ctx_max) * 100)) if ctx_max > 0 else 0
        bar_width = 24
        filled = min(bar_width, int(round((pct / 100.0) * bar_width)))
        bar = "█" * filled + "░" * (bar_width - filled)

        state_str = getattr(self, "_agent_state", "READY")

        tps_val = getattr(self, "_live_tps", 0.0)
        tps_str = (
            f"{tps_val:.1f} t/s"
            if tps_val > 0
            else ("0.0 t/s" if not self._is_running else "t/s...")
        )

        return (
            f"[bold cyan]> SYSTEM:[/] [bold green]{state_str}[/bold green]  │  "
            f"[bold cyan]LIFECYCLE:[/] [bold green]⚡ ADAPTIVE[/bold green]  │  "
            f"[bold cyan]CONTEXT:[/] [{bar}] [bold yellow]{pct}%[/bold yellow] [dim]({tokens_est:,}/{ctx_max:,})[/dim]  │  "
            f"[bold cyan]SPEED:[/] [bold green]⚡ {tps_str}[/bold green]"
        )

    def _build_meta_text(self) -> str:
        mem = getattr(self.engine, "_memory", None)
        tokens_est = self._live_context_tokens()

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
            po = self.query_one("#plan-overview-panel", Static)
            po.update(self._build_plan_overview_text())
        except Exception:
            pass
        try:
            pt = self.query_one("#task-checklist-panel", Static)
            pt.update(self._build_task_checklist_text())
        except Exception:
            pass
        try:
            pp = self.query_one("#plan-panel", Static)
            pp.update(self._build_plan_text())
        except Exception:
            pass
        try:
            sp = self.query_one("#skills-list-panel", Static)
            sp.update(self._build_skills_text())
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
            label = self._get_active_mode_label()
            mtb = self.query_one("#mode-toggle-btn", Button)
            mtb.label = f"MODE: {label}"
            mtb.remove_class("mode-badge-chat")
            mtb.remove_class("mode-badge-goal")
            mtb.remove_class("mode-badge-plan")
            mtb.remove_class("mode-badge-unified")
            if "GOAL" in label:
                mtb.add_class("mode-badge-goal")
            elif "PLAN" in label:
                mtb.add_class("mode-badge-plan")
            elif "UNIFIED" in label:
                mtb.add_class("mode-badge-unified")
            else:
                mtb.add_class("mode-badge-chat")

        except Exception:
            pass

        try:
            msd = self.query_one("#mode-select-dropdown", Select)
            curr_val = self._get_current_mode_val()
            if msd.value != curr_val:
                msd.value = curr_val
        except Exception:
            pass

    def action_show_help(self) -> None:
        self.push_screen(ShortcutsHelpModal())

    @on(Button.Pressed, "#help-btn")
    def on_help_pressed(self) -> None:
        self.action_show_help()

    @on(Button.Pressed, "#upload-skill-btn")
    def on_upload_skill_pressed(self) -> None:
        project_root = getattr(self.engine, "project_root", os.getcwd())

        def on_modal_result(result: Optional[dict]) -> None:
            if not result or not result.get("source_path"):
                return
            src = result["source_path"]
            custom = result.get("custom_name")
            ok, msg = import_skill_file(src, custom_name=custom, workspace_root=project_root)
            try:
                status_widget = self.query_one("#skills-status-msg", Static)
                if ok:
                    status_widget.update(f"[bold green]✓ {escape(msg)}[/bold green]")
                    self.notify(msg, title="Skill Imported", severity="information")
                else:
                    status_widget.update(f"[bold red]✗ {escape(msg)}[/bold red]")
                    self.notify(msg, title="Import Failed", severity="error")
            except Exception:
                pass

            try:
                sp = self.query_one("#skills-list-panel", Static)
                sp.update(self._build_skills_text(reload=True))
            except Exception:
                pass

        self.push_screen(SkillUploadModal(workspace_root=project_root), on_modal_result)

    @on(Button.Pressed, "#refresh-skills-btn")
    def on_refresh_skills_pressed(self) -> None:
        try:
            sp = self.query_one("#skills-list-panel", Static)
            sp.update(self._build_skills_text(reload=True))
            status_widget = self.query_one("#skills-status-msg", Static)
            status_widget.update("[bold cyan]✓ Refreshed skill registry[/bold cyan]")
            self.notify("Skill list refreshed", title="Skills", severity="information")
        except Exception:
            pass

    @on(Button.Pressed, "#input-model-badge")
    def on_model_badge_clicked(self) -> None:
        self.action_select_model()

    @on(Button.Pressed, "#wipe-context-btn, #agent-wipe-btn")
    def on_wipe_context_btn_clicked(self) -> None:
        self.action_wipe_session()

    @on(Button.Pressed, "#compact-btn, #health-compact-btn, #agent-compact-btn")
    def on_compact_btn_clicked(self) -> None:
        self.action_compact_context()

    @on(Button.Pressed, "#mode-toggle-btn, #mode-select-btn")
    def on_mode_toggle_pressed(self) -> None:
        self.action_select_mode()

    @on(Button.Pressed, "#toggle-breakdown-btn")
    def on_toggle_breakdown_btn(self, event: Button.Pressed) -> None:
        event.stop()
        self._show_ctx_breakdown = not getattr(self, "_show_ctx_breakdown", False)
        btn = self.query_one("#toggle-breakdown-btn", Button)
        try:
            bd_widget = self.query_one("#agent-tab-ctx-breakdown", Static)
            if self._show_ctx_breakdown:
                btn.label = "▾ Breakdown"
                bd_widget.display = True
                breakdown_text = self._context_section_breakdown()
                bd_widget.update(breakdown_text)
            else:
                btn.label = "▸ Breakdown"
                bd_widget.display = False
                bd_widget.update("")
        except Exception:
            pass

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

        if getattr(self, "_server_starting", False):
            self.notify(
                "Server is currently starting. Please wait...",
                severity="warning",
                timeout=3,
            )
            return

        if not self.model_name or self.model_name == "local-model":
            self.notify(
                "No model selected. Please select a model first.", severity="error"
            )
            self.action_select_model()
            return

        if self.engine_port > 0 and not is_port_in_use(self.engine_port):
            if self.externally_managed:
                self.notify(
                    f"{escape(self.provider_name)} is offline on port {self.engine_port}. Please start it and try again.",
                    severity="error",
                )
            else:
                self.notify(
                    f"Model '{escape(self.model_name)}' is not loaded. Please click '⚡ Start Engine' in the top bar.",
                    severity="error",
                )
            return

        inp.clear()

        # Gather chips if any
        try:
            chips_bar = self.query_one("#context-chips-bar", Horizontal)
            context_files = []
            for btn in chips_bar.query(".context-chip"):
                filepath = getattr(
                    btn, "_filepath", getattr(btn, "tooltip", None)
                ) or btn.label.plain.replace("✕", "").replace("[IMG]", "").strip().lstrip("@")
                if filepath:
                    clean_fp = filepath.strip().lstrip("@")
                    context_files.append(clean_fp)

            # Append context to task if not already inline (without @ prefix)
            if context_files:
                for cf in context_files:
                    if cf not in user_text and f"@{cf}" not in user_text:
                        user_text = f"{user_text} {cf}".strip()

            # Remove chips after submission
            for btn in chips_bar.query(Button):
                btn.remove()
            chips_bar.remove_class("has-chips")
        except Exception:
            pass

        # Add a visual separator if this isn't the first turn and the last step wasn't a separator
        if self._chat_history and self._chat_history[-1]["role"] != "system":
            try:
                container = self.query_one("#chat-container")
                if container.children:
                    self._safe_mount(
                        container, Static("─" * 40, classes="turn-separator")
                    )
            except Exception:
                pass

        if user_text.startswith("/"):
            await self._handle_slash_command(user_text)
            return

        self._chat_history.append({"role": "user", "content": user_text})
        try:
            container = self.query_one("#chat-container")
            if hasattr(container, "append_card"):
                container.append_card(
                    MessageCard(
                        user_text, role="user", project_root=self.project_root
                    )
                )
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
        if getattr(self, "_server_starting", False):
            self.notify(
                "Server is currently starting. Please wait...",
                severity="warning",
                timeout=3,
            )
            return
        if (
            not getattr(self, "_model_connected", False)
            or not self.model_name
            or self.model_name == "local-model"
        ):
            selected = self.model_name
            try:
                dropdown = self.query_one("#model-select-dropdown", Select)
                if dropdown.value:
                    selected = str(dropdown.value)
            except Exception:
                pass
            self._load_selected_model(selected, auto_start=True)
            return
        await self._submit_user_input()

    async def _do_send(self) -> None:
        """Programmatic send — called by ctrl+enter binding."""
        if self._is_running:
            self.stop_current_agent()
            return
        if getattr(self, "_server_starting", False):
            self.notify(
                "Server is currently starting. Please wait...",
                severity="warning",
                timeout=3,
            )
            return
        if (
            not getattr(self, "_model_connected", False)
            or not self.model_name
            or self.model_name == "local-model"
        ):
            selected = self.model_name
            try:
                dropdown = self.query_one("#model-select-dropdown", Select)
                if dropdown.value:
                    selected = str(dropdown.value)
            except Exception:
                pass
            self._load_selected_model(selected, auto_start=True)
            return
        await self._submit_user_input()

    @on(PromptTextArea.ContextFileAttached)
    def _on_context_file_attached(
        self, event: PromptTextArea.ContextFileAttached
    ) -> None:
        self._add_context_chip(event.filepath)
        from core.utils.image_utils import is_image_file

        if is_image_file(event.filepath):
            filename = os.path.basename(event.filepath)
            self.notify(f"🖼 Attached image: {filename}", severity="information", timeout=2)
        self.set_focus(event.text_area)

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
        if getattr(self, "_server_starting", False):
            self.notify(
                "Server is currently starting. Please wait...",
                severity="warning",
                timeout=3,
            )
            return
        if (
            not getattr(self, "_model_connected", False)
            or not self.model_name
            or self.model_name == "local-model"
        ):
            self.action_select_model()
            return
        await self._submit_user_input()

    def action_task_manager(self) -> None:
        """Open the interactive Task Manager modal screen."""
        self.push_screen(TaskManagerModal(self.project_root))

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

    def _update_running_indicator(self) -> None:
        """Keep input spinner clean and minimal while directing elapsed time
        and live TPS metrics to the top HUD header."""
        if not getattr(self, "_is_running", False):
            return
        import time

        start = getattr(self, "_stream_start_time", None)
        elapsed_str = ""
        if start:
            elapsed = max(0, int(time.time() - start))
            m, s = divmod(elapsed, 60)
            elapsed_str = f"{m:02d}:{s:02d}"

        # 1. Keep input spinner clean and minimal (fixed pulsing dot, zero layout shift)
        try:
            spinner = self.query_one("#input-spinner")
            spinner.update("[bold cyan]●[/]")
        except Exception:
            pass

        # 2. Render execution elapsed time and TPS cleanly in top HUD
        try:
            tps_val = getattr(self, "_live_tps", 0.0)
            tps_str = f"{tps_val:.1f} t/s" if tps_val > 0 else "calculating..."
            hud_text = f"TPS: {tps_str}"
            if elapsed_str:
                hud_text += f" ({elapsed_str})"
            self.query_one("#hud-epoch").update(hud_text)
        except Exception:
            pass

    def _set_input_enabled(self, enabled: bool) -> None:
        try:
            inp = self.query_one("#user-input", TextArea)
            btn = self.query_one("#send-btn", Button)
            spinner = self.query_one("#input-spinner")
            inp.disabled = not enabled if self._is_running else False
            if self._is_running:
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
        try:
            self.update_status_bar()
            self._update_running_indicator()

            if getattr(self, "_server_starting", False):
                return

            if self.engine_port <= 0:
                if not getattr(self, "_model_connected", False):
                    self._update_connection_state(True)
                return

            is_online = is_port_in_use(self.engine_port)
            if (
                getattr(self, "_last_server_online", None) != is_online
                or getattr(self, "_model_connected", False) != is_online
            ):
                self._last_server_online = is_online
                self._update_connection_state(is_online)
        except Exception:
            pass

    def _update_connection_state(self, is_online: bool) -> None:
        """Sync all connection-dependent UI elements.

        Called on server status change (and once at mount).
        Updates:
          - ConnectionPill label/color in the header
          - SEND button enabled/disabled
          - CenterEmptyState state (disconnected vs idle)
          - Agent tab connection status label
          - Clears legacy conn-banner if it exists
        """
        self._model_connected = is_online

        # 1. Connection Pill
        try:
            if self._connection_pill is not None:
                self._connection_pill.set_connected(is_online, self.model_name)
        except Exception:
            try:
                pill = self.query_one("#connection-pill", ConnectionPill)
                pill.set_connected(is_online, self.model_name)
            except Exception:
                pass

        # 2. SEND button & LOAD toggle button
        try:
            send_btn = self.query_one("#send-btn", Button)
            send_btn.disabled = False
            send_btn.tooltip = (
                None if is_online else "Click to load selected model"
            )
        except Exception:
            pass

        try:
            toggle_btn = self.query_one("#model-toggle-btn", Button)
            toggle_btn.label = "UNLOAD" if is_online else "LOAD"
            toggle_btn.variant = "error" if is_online else "primary"
        except Exception:
            pass

        # 3. CenterEmptyState
        try:
            ces = self.query_one("#center-empty-state", CenterEmptyState)
            new_state = STATE_IDLE if is_online else STATE_DISCONNECTED
            ces.set_connection_state(
                new_state, model_name=self.model_name if is_online else ""
            )
        except Exception:
            pass

        # 4. Agent tab — connection status label
        try:
            conn_status = self.query_one("#agent-tab-conn-status", Static)
            if is_online:
                conn_status.update(
                    f"[bold green]Connected[/]\n"
                    f"[dim]{escape(self.provider_name)} · port {self.engine_port}[/]"
                )
            else:
                conn_status.update(
                    f"[dim]Offline[/]\n[dim]Select model from toolbar to connect[/]"
                )
            model_info = self.query_one("#agent-tab-model-info", Static)
            if is_online and self.model_name:
                model_info.update(
                    f"[bold]{escape(self.model_name)}[/]\n"
                    f"[dim]CTX: {CTX_SIZE:,} tokens[/]"
                                    )
            else:
                model_info.update("[dim]No model loaded[/]")
        except Exception:
            pass

    def on_mount(self) -> None:
        try:
            # Sync the saved mode into the engine's memory so it takes effect immediately for new sessions
            if hasattr(self, "engine") and getattr(self.engine, "memory", None):
                from core.memory.models import ExecutionMode
                try:
                    self.engine.memory.state.execution_mode = ExecutionMode(self.engine.execution_mode)
                except Exception:
                    pass
        except Exception:
            pass

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
            if not self._is_test_env:
                self.set_interval(2.0, self.update_sidebar_meta)
        except Exception:
            pass

        try:
            self.call_after_refresh(self._refresh_editor_split_view)
        except Exception:
            pass

        try:
            container = self.query_one("#chat-container")
            # Minimal welcome into the chat transcript — not an error banner
            container.mount(
                Static(
                    "[dim]⚡ Torchlight Codex ready. Type a message or select a model from toolbar.[/dim]"
                )
            )
        except Exception:
            pass

        # Determine initial connection state and sync all UI
        try:
            if self.engine_port <= 0:
                is_online = True  # cloud provider
                self._last_server_online = True
            else:
                is_online = is_port_in_use(self.engine_port)
                self._last_server_online = is_online
        except Exception:
            is_online = False
            self._last_server_online = False

        # Run the unified connection sync (pill + SEND + empty state + agent tab)
        try:
            self.call_after_refresh(lambda: self._update_connection_state(is_online))
        except Exception:
            self._update_connection_state(is_online)

        try:
            if not self._is_test_env:
                self.set_interval(2.0, self._auto_refresh_engine_status)
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
            screen = self.screen or self.query_one("Screen")
            screen.set_class(w < 80, "narrow-terminal")
            screen.set_class(w < 50, "very-narrow-terminal")
            screen.set_class(h < 24, "short-terminal")
        except Exception:
            pass

    # ── New UX Helpers (v2 Overhaul) ────────────────────────────────────

    def append_output_log(self, text: str, severity: str = "info") -> None:
        """Append a line to the Output tab's RichLog.

        severity: 'info' | 'tool' | 'error'
        """
        try:
            log_widget = self.query_one("#output-log-content", Static)
            color = {
                "tool": "cyan",
                "error": "red",
                "info": "dim",
            }.get(severity, "dim")
            from rich.markup import escape as _esc
            import collections

            if not hasattr(self, "_output_log_deque"):
                self._output_log_deque = collections.deque(maxlen=200)

            self._output_log_deque.append(f"[{color}]{_esc(text)}[/]")
            log_widget.update("\n".join(self._output_log_deque))
        except Exception:
            pass

    def update_agent_tab_context(self) -> None:
        """Update the context usage bar and per-section breakdown in the Agent tab."""
        try:
            tokens_est = self._live_context_tokens()

            ctx_max = CTX_SIZE
            pct = min(100, int((tokens_est / ctx_max) * 100)) if ctx_max > 0 else 0
            bar_width = 18
            filled = min(bar_width, round((pct / 100.0) * bar_width))
            bar = "#" * filled + "-" * (bar_width - filled)
            color = "green" if pct < 50 else "yellow" if pct < 75 else "red"

            ctx_widget = self.query_one("#agent-tab-context-bar", Static)
            ctx_widget.update(
                f"[bold {color}][{bar}][/] [dim]{pct}%[/]\n"
                f"[dim]{tokens_est:,} / {ctx_max:,} tokens[/]"
            )
        except Exception:
            pass

        # Per-section breakdown (only computed and updated when expanded)
        if getattr(self, "_show_ctx_breakdown", False):
            try:
                now = __import__("time").monotonic()
                if now - getattr(self, "_ctx_breakdown_ts", 0.0) >= 2.0:
                    self._ctx_breakdown_ts = now
                    breakdown_text = self._context_section_breakdown()
                    bd_widget = self.query_one("#agent-tab-ctx-breakdown", Static)
                    bd_widget.update(breakdown_text)
            except Exception:
                pass

    def _set_center_empty_state_visible(self, visible: bool) -> None:
        """Show or hide the center empty state (hide when a file is open)."""
        try:
            ces = self.query_one("#center-empty-state", CenterEmptyState)
            ces.display = visible
        except Exception:
            pass

    def on_resize(self, event=None) -> None:
        self._apply_responsive_layout()

    async def on_key(self, event) -> None:
        """Global key bindings that aren't caught by specific widgets.

        Key contract (confirmed):
          enter       → insert newline in TextArea (default behavior)
          ctrl+enter  → send the current message
        """
        # ctrl+enter → send (enter=newline is handled naturally by TextArea)
        if event.key == "ctrl+j" or event.key == "ctrl+enter":
            # Check that focus is in the user input
            try:
                focused = self.focused
                if focused and focused.id == "user-input":
                    await self._do_send()
                    event.prevent_default()
                    event.stop()
                    return
            except Exception:
                pass

        if event.key in ("left", "right") and self._open_tabs:
            pane_visible = True
            try:
                editor_pane = self.query_one("#editor-split-pane")
                pane_visible = editor_pane.display
            except Exception:
                pane_visible = True
            if not pane_visible:
                return

            paths = list(self._open_tabs.keys())
            if not paths:
                return
            current_idx = (
                paths.index(self._active_tab_path)
                if self._active_tab_path in paths
                else -1
            )
            if event.key == "left":
                new_idx = (current_idx - 1) % len(paths)
            else:
                new_idx = (current_idx + 1) % len(paths)
            self._active_tab_path = paths[new_idx]
            self._refresh_editor_split_view()
            event.prevent_default()
            event.stop()

    # ── Slash Command Handler ───────────────────────────────────────────

    async def _handle_slash_command(self, cmd_text: str) -> None:
        container = self.query_one("#chat-container")
        parts = cmd_text.split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/help":
            help_md = """### Commands
- `/image <path> [prompt]` -- Inspect image with vision LLM (Gemma 3 / Qwen VL)
- `/paste` -- Paste image from clipboard into chat context
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

        elif cmd in ("/paste", "/paste-image", "/pasteimage"):
            self.action_paste_image()

        elif cmd == "/image":
            if not arg:
                self.notify(
                    "Usage: /image <path/to/image.png> [optional instruction]",
                    severity="warning",
                    timeout=4,
                )
            else:
                arg_parts = arg.split(maxsplit=1)
                img_path = arg_parts[0].strip()
                prompt_text = (
                    arg_parts[1].strip()
                    if len(arg_parts) > 1
                    else f"Inspect and analyze image: {img_path}"
                )
                from core.utils.image_utils import is_image_file, get_image_metadata

                full_p = (
                    os.path.join(self.project_root, img_path)
                    if not os.path.isabs(img_path)
                    else img_path
                )
                if not os.path.exists(full_p):
                    self.notify(
                        f"Image not found: {img_path}", severity="error", timeout=4
                    )
                else:
                    meta = get_image_metadata(full_p, project_root=self.project_root)
                    dim_str = (
                        f"{meta['width']}x{meta['height']}"
                        if meta.get("width")
                        else "dynamic"
                    )
                    self.notify(
                        f"[IMG] Attached {img_path} ({dim_str}, {meta.get('size_kb')} KB)",
                        severity="information",
                        timeout=3,
                    )
                    task_text = f"{prompt_text} @{img_path}"
                    self._chat_history.append({"role": "user", "content": task_text})
                    try:
                        if hasattr(container, "append_card"):
                            container.append_card(
                                MessageCard(
                                    task_text,
                                    role="user",
                                    images=[full_p],
                                    project_root=self.project_root,
                                )
                            )
                        else:
                            self._safe_mount(
                                container,
                                Static(
                                    Panel(
                                        escape(task_text),
                                        title="You",
                                        border_style="bright_blue",
                                    )
                                ),
                            )
                    except Exception:
                        pass
                    self._run_agent(task_text)

        elif cmd in ("/start", "/startengine"):
            self.on_start_engine_btn()

        elif cmd in ("/restart", "/restartengine"):
            self.on_restart_engine_btn()

        elif cmd in ("/stop", "/terminate", "/stopengine"):
            self.on_stop_engine_btn()

        elif cmd in ("/kill", "/killsession", "/kill-session"):
            self.on_kill_session_btn()

        elif cmd in ("/engine", "/provider", "/turboquant", "/kv"):
            self.action_engine_config()

        elif cmd in ("/select", "/copyselect", "/copyselection"):
            self.action_copy_selection()

        elif cmd in ("/status", "/telemetry"):
            self.action_toggle_status_modal()

        elif cmd == "/mode":
            if not arg:
                self.action_select_mode()
            else:
                self.set_mode(arg.lower().strip())

        elif cmd in ("/phase", "/params"):
            if not arg or arg == "show":
                curr_p = getattr(self.engine, "_current_phase", "code")
                is_l = getattr(self.engine, "_params_locked", False)
                lock_st = " 🔒 (locked)" if is_l else " 🔓 (auto)"
                self.notify(
                    f"Current Phase: {curr_p}{lock_st}\nUsage: /phase code | /phase plan | /phase troubleshoot | /phase chat | /phase auto",
                    severity="information",
                    timeout=5,
                )
            else:
                p_arg = arg.lower().strip()
                if hasattr(self.engine, "lock_phase"):
                    ok = self.engine.lock_phase(p_arg)
                    if ok:
                        if p_arg in ("auto", "unlock", "reset"):
                            self.notify(
                                "Phase lock removed — auto phase detection enabled 🔓",
                                severity="success",
                                timeout=3,
                            )
                        else:
                            self.notify(
                                f"Phase locked to '{p_arg}' 🔒",
                                severity="success",
                                timeout=3,
                            )
                    else:
                        self.notify(
                            "Usage: /phase code | /phase plan | /phase troubleshoot | /phase chat | /phase auto",
                            severity="warning",
                            timeout=4,
                        )
                else:
                    self.notify(
                        "Phase locking unavailable", severity="error", timeout=3
                    )

        elif cmd in ("/cd", "/workdir", "/open", "/browse"):
            if not arg:
                self.action_open_folder_picker()
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
                provider = getattr(self, "provider_name", "")
                normalized = normalize_model_name(arg, provider=provider)
                self.model_name = normalized
                if hasattr(self.engine.client, "model"):
                    self.engine.client.model = normalized
                save_last_state(
                    {
                        "last_model": normalized,
                        "last_provider": getattr(
                            self.engine.client, "_provider", "custom"
                        ),
                        "last_provider_name": provider,
                    }
                )
                self.update_status_bar()
                self.update_sidebar_meta()
                self.notify(
                    f"Switched model to {escape(normalized)}",
                    severity="information",
                    timeout=2,
                )

        elif cmd in ("/compress", "/compact"):
            self.action_compact_context()

        elif cmd in ("/clear", "/cls", "/reset", "/new", "/wipe"):
            self.action_wipe_session()

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
                if hasattr(container, "append_card"):
                    container.append_card(widget, scroll=True)
                else:
                    container.mount(widget)
                    if len(container.children) > 35:
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
        self.engine.ask_user_fn = self._handle_ask_user
        self.engine.on_token = self._append_token
        self.engine.on_status_change = self._handle_status_change
        self.engine.on_tasks_changed = self._handle_tasks_changed
        if getattr(self.engine, "feedback_loop", None):
            self.engine.feedback_loop.set_event_callback(self._handle_test_event)

        # Sync execution_mode from memory state into the engine
        # so solve_async selects the correct system prompt.
        _mem = getattr(self.engine, "memory", None)
        if _mem and hasattr(_mem, "state") and hasattr(_mem.state, "execution_mode"):
            _em = _mem.state.execution_mode
            self.engine.execution_mode = (
                _em.value if hasattr(_em, "value") else str(_em)
            )

        # Register callback to sync engine mode changes back to memory
        def _on_mode_change(new_mode: str):
            if (
                _mem
                and hasattr(_mem, "state")
                and hasattr(_mem.state, "execution_mode")
            ):
                from core.memory.models import ExecutionMode

                try:
                    _mem.state.execution_mode = ExecutionMode(new_mode)
                except ValueError:
                    pass

        self.engine.set_execution_mode_callback(_on_mode_change)

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

            # If in Goal Mode and tasks remain pending, continuously execute micro-epochs
            if getattr(self.engine, "execution_mode", "unified") == "goal":
                from core.tools.task_helpers import get_workspace_pending_tasks

                max_goal_epochs = 25
                max_attempts_per_task = 3
                epoch_count = 0
                task_attempts: dict[str, int] = {}

                while (
                    not getattr(self, "_is_cancelled", False)
                    and epoch_count < max_goal_epochs
                ):
                    pending_tasks = get_workspace_pending_tasks(
                        self.engine.project_root
                    )
                    if not pending_tasks:
                        break

                    next_task = pending_tasks[0]
                    current_attempt = task_attempts.get(next_task, 0) + 1
                    task_attempts[next_task] = current_attempt
                    epoch_count += 1

                    self._remove_streaming()
                    attempt_suffix = (
                        f" [dim](Attempt {current_attempt}/{max_attempts_per_task})[/]"
                        if current_attempt > 1
                        else ""
                    )
                    container.mount(
                        Static(
                            f"\n  [bold cyan]🎯 Goal Epoch {epoch_count}:[/] [bold white]{escape(next_task)}[/]{attempt_suffix}",
                            classes="step-status",
                        )
                    )
                    self.call_after_refresh(self._scroll_chat_to_end)

                    # Flush conversation turn memory to avoid context overflow while preserving project state
                    if hasattr(self.engine, "_memory") and self.engine._memory:
                        if hasattr(self.engine._memory, "clear"):
                            self.engine._memory.clear()
                    if hasattr(self.engine, "_messages"):
                        self.engine._messages = None

                    self._streaming_text = ""
                    self._ensure_streaming_widget()

                    # List existing workspace files to prevent hallucinating extra folders like src/
                    existing_files = []
                    try:
                        for f in os.listdir(self.engine.project_root):
                            if not f.startswith(".") and not f.startswith("__") and f not in ("node_modules", "venv", ".venv", "graphify-out"):
                                existing_files.append(f)
                    except Exception:
                        pass
                    files_context = (
                        f"\nExisting workspace files: {', '.join(sorted(existing_files))}\n"
                        "Target existing files directly at project root before creating new subdirectories."
                        if existing_files
                        else ""
                    )

                    epoch_prompt = (
                        f"Goal Sub-Task ({epoch_count}): {next_task}\n"
                        f"Execute the required tool calls (READ_FILE, EDIT_FILE, WRITE_FILE, RUN_COMMAND, INSPECT_WEB) "
                        f"to complete this task and verify it.{files_context}"
                    )
                    sub_result = await self.engine.solve_async(epoch_prompt)
                    result.total_llm_calls += sub_result.total_llm_calls
                    result.steps.extend(sub_result.steps)

                    # If the epoch produced successful file modifications and no failing tests, mark subtask completed
                    has_successful_edits = any(
                        s.tool_name in ("WRITE_FILE", "EDIT_FILE")
                        and getattr(s, "result", "")
                        and not str(s.result).startswith("❌")
                        and not str(s.result).startswith("⛔")
                        and not str(s.result).startswith("Edit failed")
                        for s in sub_result.steps
                    )
                    has_failing_tests = bool(
                        getattr(self.engine.feedback_loop, "has_failing_tests", False)
                    )
                    if has_successful_edits and not has_failing_tests:
                        from core.tools.task_helpers import mark_task_status
                        mark_task_status(
                            self.engine.project_root, next_task, status="completed"
                        )
                        self._notify_tasks_changed({"reason": "epoch_completion"})

                    new_pending = get_workspace_pending_tasks(
                        self.engine.project_root
                    )
                    # If the task did not advance after max attempts, break to allow manual inspection
                    if (
                        len(new_pending) >= len(pending_tasks)
                        and new_pending[0] == next_task
                        and task_attempts[next_task] >= max_attempts_per_task
                    ):
                        container.mount(
                            Static(
                                f"  [yellow]⚠ Sub-task stalled after {max_attempts_per_task} attempts: '{escape(next_task)}'[/]",
                                classes="step-status",
                            )
                        )
                        break

                remaining_after_loop = get_workspace_pending_tasks(
                    self.engine.project_root
                )
                if remaining_after_loop and epoch_count >= max_goal_epochs:
                    container.mount(
                        Static(
                            f"\n  [bold yellow]── 🎯 Goal Epoch limit reached ({max_goal_epochs} epochs). {len(remaining_after_loop)} pending task(s) remaining. Submit prompt to continue. ──[/]",
                            classes="step-status",
                        )
                    )

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

            # If in Plan Mode and the answer or implementation_plan.md contains open review questions, auto-launch AskUserModal
            current_mode = getattr(self.engine, "execution_mode", "unified")
            if current_mode == "plan" or getattr(self.engine, "_current_phase", "") == "plan":
                try:
                    from core.utils.plan_utils import parse_plan_review_questions

                    plan_text = result.answer or ""
                    plan_file = os.path.join(self.project_root, "implementation_plan.md")
                    if not plan_text and os.path.exists(plan_file):
                        with open(plan_file, "r", encoding="utf-8") as pf:
                            plan_text = pf.read()
                    review_questions = parse_plan_review_questions(plan_text)
                    if review_questions:
                        user_selection = await self.push_screen_wait(
                            AskUserModal(questions=review_questions)
                        )
                        if user_selection and user_selection != "User dismissed prompt without input.":
                            self.notify(
                                f"Review choices recorded: {user_selection[:60]}",
                                severity="information",
                                timeout=4,
                            )
                            try:
                                user_input = self.query_one("#user-input", TextArea)
                                user_input.text = f"Confirmed: {user_selection}. Proceed with implementation."
                            except Exception:
                                pass
                except Exception:
                    pass

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
            self._stream_token_count = 0
            self.update_status_bar()
            try:
                self.set_focus(self.query_one("#user-input", TextArea))
            except Exception:
                pass

    # ── Token Streaming ─────────────────────────────────────────────────

    def _ensure_streaming_widget(self) -> StreamingView:
        if getattr(self, "_streaming_widget", None) is None:
            active_phase = getattr(self, "mode", None) or getattr(getattr(self, "engine", None), "_current_phase", "chat")
            self._streaming_view = StreamingView(phase=active_phase)
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

        # Keep the status-bar context gauge climbing during generation (throttled to 1.0s)
        try:
            if now - getattr(self, "_last_status_refresh_ts", 0.0) > 1.0:
                self._last_status_refresh_ts = now
                self.call_after_refresh(self.update_status_bar)
        except Exception:
            pass

        # Adaptive throttle interval based on TPS
        throttle_interval = 0.045 if getattr(self, "_live_tps", 0.0) > 60 else getattr(self, "_token_throttle_interval", 0.033)
        throttled = (now - getattr(self, "_token_throttle_last", 0.0)) < throttle_interval

        if throttled:
            if not getattr(self, "_flush_pending", False):
                self._flush_pending = True
                self.call_after_refresh(self._flush_streaming_widget)
            return

        self._flush_pending = False
        self._token_throttle_last = now
        self._render_streaming_update()

    def _render_streaming_update(self) -> None:
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

            display_text = sanitize_assistant_text(display_text)
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
            if not getattr(self, "_scroll_pending", False):
                self._scroll_pending = True
                self.call_after_refresh(self._do_scroll_chat_to_end)
        except Exception:
            pass

    def _do_scroll_chat_to_end(self) -> None:
        self._scroll_pending = False
        self._scroll_chat_to_end()

    def _flush_streaming_widget(self) -> None:
        """Apply any pending streaming text that was throttled."""
        self._flush_pending = False
        if self._streaming_view is None:
            return
        self._render_streaming_update()

    def _remove_streaming(self) -> None:
        self._flush_pending = False
        self._scroll_pending = False
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
        self._remove_streaming()
        try:
            container = self.query_one("#chat-container")
        except Exception:
            container = None

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
                card = None
                if (
                    self._pending_tool_card is not None
                    and getattr(self, "_pending_tool_name", None) == label
                ):
                    card = self._pending_tool_card
                elif self._pending_tool_card is not None:
                    try:
                        self._pending_tool_card.remove()
                    except Exception:
                        pass

                self._pending_tool_card = None
                self._pending_tool_name = None
                if card is None:
                    if self._trajectory_rail is not None:
                        self._trajectory_rail.add_pending(label)
                    try:
                        card = ToolCallCard(
                            label, args=display_args, target=target_name
                        )
                    except Exception:
                        card = None
                    if card is not None:
                        if hasattr(container, "append_card"):
                            container.append_card(card, scroll=True)
                        else:
                            self._safe_mount(container, card)
                if self._trajectory_rail is not None:
                    self._trajectory_rail.complete(status)
                if card is not None:
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
                    step.tool_name in ("WRITE_FILE", "EDIT_FILE", "CODE_FILE_WRITE")
                    and step.result
                    and not (is_err or denied)
                ):
                    try:
                        self._refresh_git_tree()
                    except Exception:
                        pass
                    try:
                        if self.is_running:
                            self._start_ast_indexing()
                    except Exception:
                        pass
                    try:
                        self.update_sidebar_meta()
                    except Exception:
                        pass
                    try:
                        step_args = (
                            dict(step.tool_args)
                            if isinstance(step.tool_args, dict)
                            else {}
                        )
                        wp = str(
                            step_args.get("path") or step_args.get("file_path") or ""
                        )
                        if wp and os.path.isabs(wp) and wp in self._open_tabs:
                            self._open_tabs[wp]["dirty"] = True
                            self._refresh_editor_split_view()
                    except Exception:
                        pass

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

                # Rejected Final Answer / Verification Gate Interception
                elif step.action == "rejected_final_answer":
                    raw_res = step.result or "Advancing to next task."
                    first_line = raw_res.splitlines()[0] if raw_res else "Advancing to next task"
                    clean_label = first_line.replace("❌ [VERIFICATION GATE REJECTION — ", "").replace("❌ [VERIFICATION GATE REJECTION]", "").rstrip("]")
                    if not clean_label.strip():
                        clean_label = "Advancing to next task"
                    self._safe_mount(
                        container,
                        Static(
                            f"  [bold cyan]🔄 Auto-Advancing:[/] [dim]{escape(clean_label)} (Turn {step.step_number})[/]",
                            classes="step-status",
                        ),
                    )

                # Final answer
                elif step.action == "final_answer":
                    display_content = sanitize_assistant_text(step.content) if step.content else ""
                    if not display_content.strip():
                        if step.result and step.result.strip():
                            display_content = step.result.strip()
                        else:
                            try:
                                from core.tools.task_helpers import get_workspace_pending_tasks
                                pending = (
                                    get_workspace_pending_tasks(self.engine.project_root)
                                    if getattr(self, "engine", None)
                                    else []
                                )
                                if pending:
                                    display_content = f"Turn completed. Next pending task: **{pending[0]}**."
                                else:
                                    display_content = "Turn completed."
                            except Exception:
                                display_content = "Turn completed."

                    if len(display_content) > 15000:
                        display_content = (
                            display_content[:15000]
                            + "\n\n... [Output Truncated for UI Performance]"
                        )
                    duration_str = None
                    if getattr(self, "_stream_start_time", None):
                        import time

                        elapsed = max(0.0, time.time() - self._stream_start_time)
                        duration_str = f"{elapsed:.1f}s"
                    self._safe_mount(
                        container,
                        MessageCard(
                            display_content,
                            role="final",
                            meta=card_meta_for(display_content),
                            duration=duration_str,
                        ),
                    )
                    self._chat_history.append(
                        {"role": "assistant", "content": step.content or display_content}
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
            try:
                self._ensure_streaming_widget()
            except Exception:
                pass

    def _handle_test_event(self, event_type: str, data: dict) -> None:
        """Thread-safe handler for test lifecycle events from feedback loop."""
        try:
            self.call_from_thread(self._process_test_event, event_type, data)
        except Exception:
            self._process_test_event(event_type, data)

    def _process_test_event(self, event_type: str, data: dict) -> None:
        if event_type == "test_started":
            cmd = data.get("command", "tests")
            if self._status_bar:
                self._status_bar.update_status(test_status=f"[bold cyan]🧪 {escape(str(cmd))}...[/]")
        elif event_type == "test_completed":
            passed = data.get("passed", 0)
            failed = data.get("failed", 0)
            dur = data.get("duration_ms", 0.0)
            all_passed = bool(data.get("all_passed", False))
            if self._status_bar:
                if all_passed:
                    status_txt = f"[bold green]✓ {passed} tests ({dur:.0f}ms)[/]"
                else:
                    status_txt = f"[bold red]❌ {failed} failed[/]"
                self._status_bar.update_status(test_status=status_txt)

            # Mount TestVerificationCard in chat container if tests actually ran
            if data.get("command"):
                try:
                    container = self.query_one("#chat-container")
                    from rlm_optimized.tui_widgets.tool_card import TestVerificationCard

                    card = TestVerificationCard(data)
                    self._safe_mount(container, card)
                    self.call_after_refresh(self._scroll_chat_to_end)
                except Exception:
                    pass

            # Stream into Output Tab
            try:
                out_widget = self.query_one("#output-log-content")
                stdout = (data.get("stdout") or "").strip()
                stderr = (data.get("stderr") or "").strip()
                if stdout:
                    out_widget.update(f"[bold cyan]── Test Verification Output ──[/]\n{escape(stdout)}")
                elif stderr:
                    out_widget.update(f"[bold red]── Test Verification Errors ──[/]\n{escape(stderr)}")
            except Exception:
                pass

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

    def set_mode(self, mode_str: str) -> None:
        m_str = mode_str.lower().strip()
        if m_str in ("code", "chat", "goal", "plan", "unified"):
            from core.memory.models import ExecutionMode

            if m_str == "code":
                new_mode = ExecutionMode.CODE
            elif m_str == "goal":
                new_mode = ExecutionMode.GOAL
            elif m_str == "plan":
                new_mode = ExecutionMode.PLAN
            elif m_str == "unified":
                new_mode = ExecutionMode.UNIFIED
            else:
                new_mode = ExecutionMode.CHAT

            mem = getattr(self.engine, "memory", None)
            if (
                mem
                and hasattr(mem, "state")
                and hasattr(mem.state, "execution_mode")
            ):
                mem.state.execution_mode = new_mode

            self.engine.execution_mode = m_str
            save_last_state({"last_execution_mode": m_str})

            if m_str == "code":
                self.notify(
                    "Switched to Code Mode (Surgical coding & task execution)",
                    severity="success",
                    timeout=3,
                )
            elif m_str == "goal":
                try:
                    from core.execution.autonomous_harness import AutonomousHarness

                    harness = AutonomousHarness(
                        project_root=self.engine.project_root, memory=mem
                    )
                    success = harness.ensure_goal_spec_initialized()
                    if not success:
                        self.notify(
                            "Failed to initialize Goal Mode task graph",
                            severity="error",
                            timeout=5,
                        )
                        return
                except Exception as e:
                    self.notify(
                        f"Failed to initialize Goal Mode: {e}",
                        severity="error",
                        timeout=5,
                    )
                    return
                self.notify(
                    "Switched to Goal Mode (Task Graph in .torchlight/tasks.md)",
                    severity="success",
                    timeout=3,
                )
            elif m_str == "plan":
                self.notify(
                    "Switched to Plan Mode (Brainstorm & maintain implementation_plan.md)",
                    severity="success",
                    timeout=3,
                )
            elif m_str == "unified":
                self.notify(
                    "Switched to Unified Mode (Dynamic Phase & Toolset)",
                    severity="success",
                    timeout=3,
                )
            else:
                self.notify(
                    "Switched to Chat Mode (Lightweight Q&A)",
                    severity="information",
                    timeout=3,
                )
            self.update_sidebar_meta()
            self.update_status_bar()
        else:
            self.notify(
                f"Unknown mode: {mode_str}. Options: code, plan, chat, goal, unified.",
                severity="error",
                timeout=3,
            )

    def action_select_mode(self) -> None:
        def _on_mode_selected(selected_mode: Optional[str]):
            if selected_mode:
                self.set_mode(selected_mode)

        m_str = self._get_current_mode_val()
        self.push_screen(SessionModePickerModal(m_str), _on_mode_selected)

    def _get_active_mode_label(self) -> str:
        current_m = getattr(self.engine, "execution_mode", None) if hasattr(self, "engine") else None
        if not current_m:
            mem = getattr(self.engine, "memory", None) if hasattr(self, "engine") else None
            current_m = getattr(getattr(mem, "state", None), "execution_mode", "unified")
        m_str = (
            current_m.value if hasattr(current_m, "value") else str(current_m or "unified")
        )
        if "code" in m_str.lower():
            return "CODE"
        elif "goal" in m_str.lower():
            return "GOAL"
        elif "plan" in m_str.lower():
            return "PLAN"
        elif "unified" in m_str.lower():
            return "UNIFIED"
        return "CHAT"

    def _get_current_mode_val(self) -> str:
        current_m = getattr(self.engine, "execution_mode", None) if hasattr(self, "engine") else None
        if not current_m:
            mem = getattr(self.engine, "memory", None) if hasattr(self, "engine") else None
            current_m = getattr(getattr(mem, "state", None), "execution_mode", "unified")
        m_str = (
            current_m.value if hasattr(current_m, "value") else str(current_m or "unified")
        )
        m_lower = m_str.lower()
        if "code" in m_lower:
            return "code"
        elif "goal" in m_lower:
            return "goal"
        elif "plan" in m_lower:
            return "plan"
        elif "unified" in m_lower:
            return "unified"
        return "chat"

    def _get_mode_select_options(self) -> list[tuple[str, str]]:
        return [
            ("Mode: Code", "code"),
            ("Mode: Plan", "plan"),
            ("Mode: Chat", "chat"),
            ("Mode: Goal", "goal"),
            ("Mode: Unified", "unified"),
        ]


    @on(Select.Changed, "#mode-select-dropdown")
    def _on_mode_select_changed(self, event: Select.Changed) -> None:
        if event.value:
            self.set_mode(str(event.value))

    def _get_models_for_engine(self, engine: str = "") -> list[tuple[str, str]]:
        """Get model choices strictly tailored ONLY to the selected inference backend."""
        from pathlib import Path
        options = []
        workspace = Path(self.engine.project_root if hasattr(self, "engine") and self.engine else os.getcwd()).resolve()
        models_dir = workspace / "models"
        engine_str = (engine or getattr(self, "provider_name", "llama.cpp") or "llama.cpp").lower()

        if "mlx" in engine_str:
            from rlm_optimized.config import is_valid_mlx_directory
            # 1. ./models directory MLX model folders ONLY
            if models_dir.exists():
                for item in sorted(models_dir.iterdir()):
                    if is_valid_mlx_directory(str(item)):
                        options.append((item.name, str(item.resolve())))

            # 2. ~/.cache/huggingface/hub snapshots for MLX models ONLY (verified complete)
            hf_dir = Path.home() / ".cache" / "huggingface" / "hub"
            if hf_dir.exists():
                for item in sorted(hf_dir.glob("models--*mlx*")):
                    snaps_dir = item / "snapshots"
                    if snaps_dir.exists():
                        for snap in snaps_dir.iterdir():
                            if is_valid_mlx_directory(str(snap)):
                                clean_name = item.name.replace("models--mlx-community--", "").replace("models--", "")
                                if not any(opt[0] == clean_name or opt[1] == str(snap.resolve()) for opt in options):
                                    options.append((clean_name, str(snap.resolve())))
                                break
            # 3. Ensure popular MLX Coder, Gemma, and Reasoning models are available
            if not any("DeepSeek-R1" in opt[0] for opt in options):
                options.append(("DeepSeek-R1-Distill-Qwen-7B-4bit", "mlx-community/DeepSeek-R1-Distill-Qwen-7B-4bit"))
            if not any("Qwen2.5-Coder-3B" in opt[0] for opt in options):
                options.append(("Qwen2.5-Coder-3B-Instruct-4bit", "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"))
            if not any("Qwen2.5-Coder-7B" in opt[0] for opt in options):
                options.append(("Qwen2.5-Coder-7B-Instruct-4bit", "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"))
            if not any("gemma-4-e4b" in opt[1].lower() for opt in options):
                options.append(("Gemma 4 E4B (MLX)", "mlx-community/gemma-4-E4B-it-4bit"))
            if not any("gemma-4-e2b" in opt[1].lower() for opt in options):
                options.append(("Gemma 4 E2B (MLX)", "mlx-community/gemma-4-E2B-it-4bit"))
            if not any("gemma-2-2b" in opt[1].lower() for opt in options):
                options.append(("Gemma 2 2B (MLX)", "mlx-community/gemma-2-2b-it-4bit"))

            if not options:
                options = [("Qwen2.5-Coder-3B-Instruct-4bit", "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit")]

        elif "lmstudio" in engine_str:
            # ONLY LM Studio models
            try:
                from rlm_optimized.config import fetch_provider_models, LMSTUDIO_BASE_URL
                lm_models = fetch_provider_models(LMSTUDIO_BASE_URL)
                for m_id in lm_models:
                    options.append((f"{m_id} (LM Studio)", m_id))
            except Exception:
                pass
            if not options:
                lmstudio_dir = Path.home() / ".lmstudio" / "models"
                if lmstudio_dir.exists():
                    for gguf in sorted(lmstudio_dir.rglob("*.gguf")):
                        sz_mb = gguf.stat().st_size / (1024 * 1024)
                        options.append((f"{gguf.name} ({sz_mb:.0f}MB)", str(gguf.resolve())))
            if not options:
                options = [("No LM Studio models found (check port 1234)", "lmstudio-default")]

        elif "ollama" in engine_str:
            # ONLY Ollama models
            try:
                from rlm_optimized.config import fetch_provider_models
                ol_models = fetch_provider_models("http://localhost:11434/v1")
                for m_id in ol_models:
                    options.append((f"{m_id} (Ollama)", m_id))
            except Exception:
                pass
            if not options:
                options = [("No Ollama models found (check port 11434)", "ollama-default")]

        else:
            # llama.cpp / TurboQuant — ONLY .gguf model files
            if models_dir.exists():
                for item in sorted(models_dir.iterdir()):
                    if item.is_file() and item.suffix == ".gguf":
                        sz_mb = item.stat().st_size / (1024 * 1024)
                        options.append((f"{item.name} ({sz_mb:.0f}MB)", str(item.resolve())))

            lmstudio_dir = Path.home() / ".lmstudio" / "models"
            if lmstudio_dir.exists():
                for gguf in sorted(lmstudio_dir.rglob("*.gguf")):
                    sz_mb = gguf.stat().st_size / (1024 * 1024)
                    if not any(opt[1] == str(gguf.resolve()) for opt in options):
                        options.append((f"{gguf.name} ({sz_mb:.0f}MB)", str(gguf.resolve())))

            if not options:
                options = [("qwen2.5-coder-3b-instruct-q4_k_m.gguf", "models/qwen2.5-coder-3b-instruct-q4_k_m.gguf")]

        curr_m = getattr(self, "model_name", "")
        if curr_m and curr_m != "default":
            matching_idx = next(
                (i for i, opt in enumerate(options) if opt[1] == curr_m or curr_m in opt[1] or opt[1] in curr_m),
                None,
            )
            if matching_idx is not None:
                matched_item = options.pop(matching_idx)
                val = curr_m if curr_m == matched_item[1] or curr_m in matched_item[1] else matched_item[1]
                options.insert(0, (matched_item[0], val))
            elif (("mlx" in engine_str and ("mlx" in curr_m.lower() or "safetensors" in curr_m.lower())) or 
                  ("llama" in engine_str and ("gguf" in curr_m.lower() or "qwen" in curr_m.lower() or "gemma" in curr_m.lower()))):
                options.insert(0, (curr_m, curr_m))

        return options

    def _populate_supported_models_near_chat(self, engine: str) -> None:
        """Populate the model dropdown near chat toolbar based strictly on selected backend engine."""
        try:
            dropdown = self.query_one("#model-select-dropdown", Select)
            options = self._get_models_for_engine(engine)
            dropdown.set_options(options)
            if options:
                curr = self.model_name
                matching = next(
                    (opt[1] for opt in options if opt[1] == curr or (curr and curr in opt[1]) or (curr and opt[1] in curr)),
                    None,
                )
                if matching is not None:
                    dropdown.value = matching
                    self.model_name = matching
                else:
                    dropdown.value = options[0][1]
                    self.model_name = options[0][1]
            self.update_sidebar_meta()
            self.update_status_bar()
        except Exception:
            pass

    @on(Select.Changed, "#sidebar-engine-select")
    def _on_sidebar_engine_changed(self, event: Select.Changed) -> None:
        if event.value:
            new_engine = str(event.value)
            self.provider_name = new_engine
            self.engine_provider = new_engine
            os.environ["PROVIDER"] = new_engine
            self._populate_supported_models_near_chat(new_engine)
            self.notify(
                f"Switched engine to: {new_engine.upper()}",
                severity="information",
                timeout=2,
            )
            self.update_sidebar_meta()

    @on(Button.Pressed, "#sidebar-apply-engine-btn")
    def _on_sidebar_apply_engine_pressed(self) -> None:
        try:
            eng = str(self.query_one("#sidebar-engine-select", Select).value)
            kv = str(self.query_one("#sidebar-kv-select", Select).value)
            try:
                ctx = int(self.query_one("#sidebar-ctx-select", Select).value)
                temp = float(self.query_one("#sidebar-temp-select", Select).value)
                rep_pen = float(self.query_one("#sidebar-rep-select", Select).value)
                threads = int(self.query_one("#sidebar-threads-select", Select).value)
            except Exception:
                ctx = 12288
                temp = 0.1
                rep_pen = 1.08
                threads = 4

            self.provider_name = eng
            self.engine_provider = eng
            self.kv_cache_mode = kv
            self.context_window_size = ctx

            os.environ["PROVIDER"] = eng
            if eng in ("llama.cpp", "llama-cpp", "turbo", "turboquant"):
                os.environ["KV_CACHE_COMPRESSION"] = kv
                save_last_state({"last_kv_cache_mode": kv})
            os.environ["RLM_CTX_SIZE"] = str(ctx)
            os.environ["THREADS"] = str(threads)
            os.environ["TEMPERATURE"] = str(temp)
            os.environ["REPEAT_PENALTY"] = str(rep_pen)
            os.environ["REPETITION_PENALTY"] = str(rep_pen)

            if hasattr(self, "engine") and self.engine and hasattr(self.engine, "client") and self.engine.client:
                if hasattr(self.engine.client, "temperature"):
                    self.engine.client.temperature = temp
                if hasattr(self.engine.client, "repeat_penalty"):
                    self.engine.client.repeat_penalty = rep_pen
                if hasattr(self.engine.client, "repetition_penalty"):
                    self.engine.client.repetition_penalty = rep_pen

            self._populate_supported_models_near_chat(eng)

            # Re-instantiate engine client matching the newly applied engine & model
            self._load_selected_model(self.model_name, auto_start=False)

            status_msg = self.query_one("#sidebar-engine-status-msg", Static)
            status_msg.update(f"[green]✓ Applied {eng.upper()} ({kv}) @ {ctx} ctx | rep={rep_pen}[/green]")

            self.notify(
                f"Applied: {eng.upper()} ({kv}, {ctx} ctx, rep={rep_pen}, {threads} thr)",
                severity="information",
                timeout=3,
            )
            self.update_sidebar_meta()
            self.update_status_bar()
            if not self.externally_managed:
                self._start_engine(force_restart=True)
        except Exception as e:
            self.notify(f"Error applying engine settings: {e}", severity="error", timeout=4)

    def _get_model_select_options(self) -> list[tuple[str, str]]:
        """Return all available models across MLX, TurboQuant GGUF, LM Studio, and Ollama."""
        from rlm_optimized.config import list_available_models, format_model_display_name
        options: list[tuple[str, str]] = []
        seen_ids: set[str] = set()
        try:
            available = list_available_models()
            for m in available:
                m_id = m.get("id", "")
                if not m_id or m_id in seen_ids:
                    continue
                seen_ids.add(m_id)
                label = m.get("name") or format_model_display_name(m_id, provider=m.get("provider", ""))
                options.append((label, m_id))
        except Exception:
            pass

        if not options:
            return self._get_models_for_engine(getattr(self, "provider_name", "llama.cpp"))

        curr = getattr(self, "model_name", "")
        if curr and curr != "default":
            matching_idx = next(
                (i for i, opt in enumerate(options) if opt[1] == curr or curr in opt[1] or opt[1] in curr),
                None,
            )
            if matching_idx is not None:
                matched_item = options.pop(matching_idx)
                options.insert(0, matched_item)

        return options

    def _is_model_connected(self) -> bool:
        try:
            from rlm_optimized.llamacpp_client import is_port_in_use

            return is_port_in_use(self.engine_port) or getattr(
                self, "_last_server_online", False
            )
        except Exception:
            return False

    @on(Select.Changed, "#model-select-dropdown")
    def _on_model_select_changed(self, event: Select.Changed) -> None:
        if event.value:
            new_model = str(event.value)
            if new_model != self.model_name:
                self._load_selected_model(new_model, auto_start=True)

    def _get_draft_model_select_options(self) -> list[tuple[str, str]]:
        options = []
        try:
            from rlm_optimized.config import list_available_draft_models

            drafts = list_available_draft_models(target_model=self.model_name)
            for d in drafts:
                label = str(d.get("name", d.get("id", "")))
                options.append((label, d["id"]))
        except Exception:
            options = [("None (Disabled)", "none"), ("Auto-Match Draft", "auto")]
        return options or [("None (Disabled)", "none")]

    @on(Button.Pressed, "#model-toggle-btn")
    def _on_model_toggle_pressed(self, event: Button.Pressed) -> None:
        btn_label = str(event.button.label).strip().upper()
        if btn_label == "UNLOAD" or self._is_model_connected():
            try:
                subprocess.run(
                    ["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL
                )
                subprocess.run(
                    ["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL
                )
            except Exception:
                pass
            self._last_server_online = False
            self._server_starting = False
            self._update_connection_state(False)
            self.notify(
                "Model unloaded & engine stopped",
                severity="information",
                timeout=2,
            )
            self._set_input_enabled(True)
        else:
            selected_model = self.model_name
            try:
                dropdown = self.query_one("#model-select-dropdown", Select)
                if dropdown.value:
                    selected_model = str(dropdown.value)
            except Exception:
                pass
            self._load_selected_model(selected_model, auto_start=True)

    def _load_selected_model(
        self, model_id: str, auto_start: bool = True
    ) -> None:
        """Unified model loader: configures provider, client, port runtime, and starts backend engine if auto_start=True."""
        if not model_id:
            return

        # Base provider detection from current active engine / state
        current_eng = getattr(self, "engine_provider", getattr(self, "provider_name", "turbo"))
        if current_eng in ("llama.cpp", "llama-cpp"):
            current_eng = "turbo"
        provider = current_eng or "turbo"
        name = model_id

        try:
            from rlm_optimized.config import (
                list_available_models,
                fetch_provider_models,
                format_model_display_name,
                LMSTUDIO_BASE_URL,
            )

            models = list_available_models()

            # Only query the provider that the detected engine actually uses,
            # instead of hitting all three servers (up to 6s timeout if all down).
            if provider == "lmstudio":
                lm_models = fetch_provider_models(LMSTUDIO_BASE_URL)
                for m_id in lm_models:
                    if not any(m["id"] == m_id for m in models):
                        models.append({"id": m_id, "name": f"{m_id} (LM Studio)", "provider": "lmstudio"})
            elif provider == "ollama":
                ollama_models = fetch_provider_models("http://localhost:11434/v1")
                for m_id in ollama_models:
                    if not any(m["id"] == m_id for m in models):
                        models.append({"id": m_id, "name": f"{m_id} (Ollama)", "provider": "ollama"})
            elif provider in ("llama-cpp", "turbo", "turboquant"):
                # Not "mlx": mlx_lm's /v1/models lists every MLX-ish repo in the
                # HF cache, not the loaded model, so it injects unrelated models.
                local_8080 = fetch_provider_models("http://localhost:8080/v1")
                for m_id in local_8080:
                    if not any(m["id"] == m_id for m in models):
                        p = "mlx" if ("mlx" in m_id.lower() or "deepseek" in m_id.lower() or "safetensors" in m_id.lower()) else "turbo"
                        models.append({"id": m_id, "name": f"{m_id} (Local Server)", "provider": p})

            for m in models:
                if m["id"] == model_id or m.get("id", "").lower() == model_id.lower():
                    provider = m.get("provider", provider)
                    name = m.get("name", model_id)
                    break
        except Exception:
            pass

        # Enhanced provider detection
        m_lower = model_id.lower()
        if (os.path.isdir(model_id) and os.path.exists(os.path.join(model_id, "config.json"))) or "safetensors" in m_lower or "snapshots" in m_lower:
            provider = "mlx"
        elif "mlx" in m_lower or model_id.startswith("mlx-community/"):
            provider = "mlx"
        elif ("deepseek" in m_lower or "r1" in m_lower) and not model_id.endswith(".gguf"):
            provider = "mlx"
        elif model_id.endswith(".gguf"):
            if provider == "lmstudio" or "lmstudio" in m_lower:
                provider = "lmstudio"
            else:
                provider = "turbo"
        elif "gemini" in m_lower:
            provider = "gemini"
        elif "ollama" in m_lower or ":" in model_id:
            provider = "ollama"
        elif "groq" in m_lower:
            provider = "groq"
        elif "together" in m_lower:
            provider = "together"
        elif "openrouter" in m_lower:
            provider = "openrouter"
        elif "openai" in m_lower or "gpt" in m_lower:
            provider = "openai"
        elif current_eng == "mlx" and not model_id.endswith(".gguf"):
            provider = "mlx"

        # Kill old server processes only when actively starting a model
        if auto_start:
            try:
                subprocess.run(
                    ["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL
                )
                subprocess.run(
                    ["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL
                )
                time.sleep(0.3)
            except Exception:
                pass

        save_last_state(
            {
                "last_model": model_id,
                "last_provider": provider,
                "last_provider_name": name,
            }
        )

        self.model_name = model_id
        self.provider_name = provider
        self.engine_provider = provider

        # 2. Re-instantiate engine client
        if provider in ("llama-cpp", "turbo", "turboquant"):
            from rlm_optimized.llamacpp_client import LlamaCppClient

            self.engine.client = LlamaCppClient(
                base_url="http://localhost:8080/v1", model=model_id
            )
        elif provider == "mlx":
            from rlm_optimized.cloud_client import CloudClient

            self.engine.client = CloudClient(
                provider="mlx",
                model=model_id,
                base_url="http://localhost:8080/v1",
                api_key="not-needed",
            )
        elif provider == "ollama":
            from rlm_optimized.ollama_client import OllamaClient

            self.engine.client = OllamaClient(model=model_id)
        elif provider == "lmstudio":
            from rlm_optimized.cloud_client import CloudClient
            from rlm_optimized.config import LMSTUDIO_BASE_URL, LMSTUDIO_API_KEY

            self.engine.client = CloudClient(
                provider=None,
                model=model_id,
                base_url=LMSTUDIO_BASE_URL,
                api_key=LMSTUDIO_API_KEY,
            )
        else:
            from rlm_optimized.cloud_client import CloudClient

            self.engine.client = CloudClient(provider=provider, model=model_id)

        # 3. Update engine port & runtime info
        self.engine_port, self.externally_managed = _provider_runtime_info(
            provider
        )

        # 4. Launch engine server if auto_start requested
        if auto_start:
            if self.engine_port <= 0:
                self._update_connection_state(True)
                self.notify(
                    f"Connected to {escape(name)}.",
                    severity="information",
                    timeout=3,
                )
            elif not self.externally_managed:
                self._start_engine(force_restart=True)
            else:
                if is_port_in_use(self.engine_port):
                    self._update_connection_state(True)
                    self.notify(
                        f"Connected to {escape(name)}.",
                        severity="information",
                        timeout=3,
                    )
                else:
                    self._update_connection_state(False)
                    self.notify(
                        f"Switched to {escape(name)}. Start service on port {self.engine_port}.",
                        severity="warning",
                        timeout=5,
                    )
        self.update_status_bar()
        self.update_sidebar_meta()

    def action_select_model(self) -> None:
        """Focus and open the model select dropdown (model badge click / toolbar)."""
        try:
            dropdown = self.query_one("#model-select-dropdown", Select)
            self.set_focus(dropdown)
            # Dynamically refresh model list so any new live models are immediately selectable
            current_val = dropdown.value
            options = self._get_model_select_options()
            dropdown.set_options(options)
            if current_val:
                dropdown.value = current_val
            dropdown.action_show_overlay()
        except Exception:
            pass


    def action_engine_config(self) -> None:
        """Open the Inference Engine & TurboQuant configuration modal."""
        def _on_engine_applied(result: Optional[dict]):
            if result:
                selected_engine = result.get("engine", "llama.cpp")
                selected_kv = result.get("kv_mode", "turbo3")
                selected_model = result.get("model", "")

                self.provider_name = selected_engine
                self.engine_provider = selected_engine
                self.kv_cache_mode = selected_kv
                if selected_model:
                    self.model_name = selected_model

                os.environ["KV_CACHE_COMPRESSION"] = selected_kv
                save_last_state({"last_kv_cache_mode": selected_kv})
                os.environ["PROVIDER"] = selected_engine

                self.notify(
                    f"⚡ Engine: {selected_engine.upper()} | Model: {os.path.basename(self.model_name)} | KV: {selected_kv}",
                    severity="information",
                    timeout=3,
                )
                self.update_sidebar_meta()
                self.update_status_bar()
                if not self.externally_managed:
                    self._start_engine(force_restart=True)

        self.push_screen(
            EngineConfigModal(
                current_engine=getattr(self, "provider_name", "llama.cpp"),
                current_kv_mode=getattr(self, "kv_cache_mode", "turbo3"),
                current_model=self.model_name,
            ),
            _on_engine_applied,
        )

    def action_open_folder(self) -> None:
        # Same thing as /cd with no argument. This used to be a separate copy that
        # forgot to os.chdir() and to persist last_workdir, so a workspace picked
        # with ctrl+o was silently lost on the next launch.
        self.action_open_folder_picker()

    @work(exclusive=True, group="ast_indexer", thread=True)
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
                self._update_connection_state(True)
                self.update_status_bar()
                self.update_sidebar_meta()
                self.notify(
                    f"Engine server active on port {port}",
                    severity="information",
                    timeout=2,
                )
                return

        self._server_starting = False
        self._last_server_online = False
        self._update_connection_state(False)
        self.update_status_bar()
        self.update_sidebar_meta()
        self.notify(
            f"Engine server failed to bind to port {port} within 15 seconds",
            severity="error",
            timeout=5,
        )

    @on(Button.Pressed, "#toggle-engine-btn")
    def on_toggle_engine_btn(self) -> None:
        # toggle-engine-btn was removed from the input bar in v2 UX overhaul.
        # If somehow triggered (e.g. from a slash command), redirect to model picker.
        self.action_select_model()

    @on(Button.Pressed, "#start-engine-btn")
    def on_start_engine_btn(self) -> None:
        self._start_engine(force_restart=False)

    def _start_engine(self, force_restart: bool = False) -> None:
        container = self.query_one("#chat-container")

        if self.engine_port <= 0:
            self.notify(
                f"{escape(self.provider_name)} is a cloud provider, nothing to start locally",
                severity="information",
                timeout=2,
            )
            self.update_status_bar()
            self.update_sidebar_meta()
            return

        if not force_restart and is_port_in_use(self.engine_port):
            self._server_starting = False
            self._last_server_online = True
            self._update_connection_state(True)
            self.notify(
                f"Connected to {escape(self.provider_name)} on port {self.engine_port}",
                severity="information",
                timeout=2,
            )
            self.update_status_bar()
            self.update_sidebar_meta()
            return

        if self.externally_managed:
            self.notify(
                f"{escape(self.provider_name)} offline on port {self.engine_port}. Start it yourself, then retry.",
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
                f"  [bold yellow]Starting local engine server ({escape(self.model_name)})...[/]\n"
            )
        self.update_status_bar()
        self.update_sidebar_meta()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        provider_str = getattr(self, "engine_provider", getattr(self, "provider_name", "")).lower()
        model_str = getattr(self, "model_name", "").lower()
        is_mlx = (
            "mlx" in provider_str
            or "mlx" in model_str
            or (isinstance(self.model_name, str) and os.path.isdir(self.model_name) and os.path.exists(os.path.join(self.model_name, "config.json")))
            or (isinstance(self.model_name, str) and ("deepseek" in model_str or "r1" in model_str) and not self.model_name.endswith(".gguf"))
        )
        script_name = (
            "start_mlx_server.sh"
            if is_mlx
            else "start_optimized_local.sh"
        )
        target_script = os.path.join(script_dir, script_name)

        if not os.path.exists(target_script):
            target_script = os.path.abspath(
                os.path.join(self.engine.project_root, "rlm_optimized", script_name)
            )

        if os.path.exists(target_script):
            try:
                # Terminate any previously running server processes to ensure the new model loads
                try:
                    subprocess.run(
                        ["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL
                    )
                    subprocess.run(
                        ["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL
                    )
                    time.sleep(0.5)
                except Exception:
                    pass

                log_dir = os.path.join(self.engine.project_root, ".torchlight")
                os.makedirs(log_dir, exist_ok=True)
                server_log_path = os.path.join(log_dir, "llama_server.log")
                server_log_file = open(server_log_path, "a", encoding="utf-8")

                env = os.environ.copy()
                env["PORT"] = str(self.engine_port)
                env["KV_CACHE_COMPRESSION"] = getattr(self, "kv_cache_mode", "turbo3")
                draft_arg = getattr(self, "draft_model_name", "none") or "none"
                if draft_arg != "none":
                    env["DRAFT_MODEL"] = draft_arg
                    env["DRAFT_MAX"] = str(getattr(self, "draft_max_tokens", 8))

                subprocess.Popen(
                    [target_script, self.model_name, draft_arg],
                    cwd=os.path.dirname(target_script),
                    stdout=server_log_file,
                    stderr=server_log_file,
                    start_new_session=True,
                    env=env,
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
        self._start_engine(force_restart=True)
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
    # above (bound to #input-model-badge) which focuses the toolbar model dropdown.

    # ── Approval Modal ──────────────────────────────────────────────────

    async def _handle_approval(self, tool_name: str, risk: str, args: dict) -> bool:
        if getattr(self, "_auto_approve_session", False):
            return True
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
        res = await self.push_screen_wait(
            ApprovalModal(
                tool_name,
                risk,
                args,
                diff_entries=diff_entries,
                diff_path=diff_path,
            )
        )
        if res == "always":
            self._auto_approve_session = True
            self.notify(
                "Session auto-approval enabled for all tools",
                severity="information",
                timeout=3,
            )
            return True
        return bool(res)

    async def _handle_ask_user(self, args: dict) -> str:
        questions_list = args.get("questions")
        if isinstance(questions_list, list) and questions_list:
            res = await self.push_screen_wait(
                AskUserModal(
                    questions=questions_list,
                    allow_custom_input=bool(args.get("allow_custom_input", True)),
                )
            )
        else:
            question = args.get("question", "")
            options = args.get("options", [])
            is_multi = bool(args.get("is_multi_select", False))
            allow_custom = bool(args.get("allow_custom_input", True))
            res = await self.push_screen_wait(
                AskUserModal(
                    question=question,
                    options=options,
                    is_multi_select=is_multi,
                    allow_custom_input=allow_custom,
                )
            )
        return str(res or "No input provided.")

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
        task_prog = ""
        try:
            from core.tools.task_helpers import get_workspace_task_status_summary

            tsummary = get_workspace_task_status_summary(self.project_root)
            tot = tsummary.get("total_count", 0)
            comp = tsummary.get("completed_count", 0)
            cur = tsummary.get("current_task")
            if tot > 0:
                c_desc = (
                    cur["description"][:25] + "..."
                    if cur and len(cur["description"]) > 25
                    else (cur["description"] if cur else "")
                )
                task_prog = f"{comp}/{tot} {c_desc}".strip()
        except Exception:  # noqa: BLE001, S110
            pass

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
            task_progress=task_prog,
        )

        # Keep Agent tab context bar in sync
        try:
            self.update_agent_tab_context()
        except Exception:
            pass

    def _live_context_tokens(self) -> int:
        """Committed memory tokens plus in-flight streamed tokens for the context gauge.

        Memory only receives a message once the full LLM response is parsed, so the
        streamed tokens are added on top here to make the gauge climb during generation.
        """
        mem = getattr(self.engine, "_memory", None)
        if mem and hasattr(mem, "total_tokens") and isinstance(mem.total_tokens, (int, float)) and mem.total_tokens > 0:
            base = int(mem.total_tokens)
        else:
            calls = getattr(self.engine, "_total_llm_calls", 0)
            base = int(calls) * 450 if calls else 0
        return base + getattr(self, "_stream_token_count", 0)

    def _context_section_breakdown(self) -> str:
        """Estimate per-section token usage and return a Rich markup string.

        Sections estimated:
          System Prompt  — base phase prompt + tool syntax suffix
          Scratchpad/L0  — L0 working memory (task matrix, errors, decisions)
          Flashlight     — AST beam (0 if disabled / no recent query)
          Chat History   — all user+assistant messages in active context window
          Pins           — pinned file slices
          Streaming      — in-flight tokens being generated right now

        Returns compact multi-line Rich markup suitable for a narrow sidebar.
        """
        ctx_max = CTX_SIZE
        if ctx_max <= 0:
            return "[dim]N/A[/dim]"

        import time as _t
        now = _t.monotonic()
        cached_static = getattr(self, "_ctx_breakdown_cache", None)
        cached_ts = getattr(self, "_ctx_breakdown_cache_ts", 0.0)
        stream_tok = getattr(self, "_stream_token_count", 0)
        SPARK_WIDTH = 8

        if cached_static is not None and (now - cached_ts) < 2.0:
            if stream_tok > 0:
                pct = min(100.0, (stream_tok / ctx_max) * 100)
                filled = min(SPARK_WIDTH, round((pct / 100.0) * SPARK_WIDTH))
                spark = "▪" * filled + "·" * (SPARK_WIDTH - filled)
                stream_row = (
                    f"[dim]{'Streaming':<10}[/dim] "
                    f"[yellow]{spark}[/yellow] "
                    f"[bold]{stream_tok:>5,}[/bold] "
                    f"[dim]{pct:>4.1f}%[/dim]"
                )
                return cached_static + "\n" + stream_row
            return cached_static

        # ── Estimate each section (O(1) in memory) ───────────────────────────
        mem = getattr(self.engine, "_memory", None)

        # 1. System prompt: rough estimate based on phase
        phase = getattr(self.engine, "_current_phase", "code")
        _SYSTEM_SIZES = {"chat": 900, "plan": 1100, "code": 1050, "goal": 1000, "troubleshoot": 950}
        system_tok = _SYSTEM_SIZES.get(phase, 1000) + 300

        # 2. Scratchpad / L0 — fast memory estimate
        scratchpad_tok = getattr(mem, "_estimate_l0_tokens", lambda: 150)() if mem else 150
        if scratchpad_tok == 0:
            scratchpad_tok = 50

        # 3. Flashlight beam — estimate from last beam size
        beam_tok = getattr(self, "_last_beam_tokens", 0)
        if beam_tok == 0:
            beam_tok = 600 if ctx_max >= 8000 else 250

        # 4. Chat history — committed message tokens in memory
        chat_tok = getattr(mem, "_cached_msg_tokens", 0) if mem else 0

        # 5. Pinned files
        pinned_tok = getattr(mem, "_cached_pinned_tokens", 0) if mem else 0

        def _row(label: str, tok: int, color: str) -> str:
            pct = min(100.0, (tok / ctx_max) * 100)
            filled = min(SPARK_WIDTH, round((pct / 100.0) * SPARK_WIDTH))
            spark = "▪" * filled + "·" * (SPARK_WIDTH - filled)
            return (
                f"[dim]{label:<10}[/dim] "
                f"[{color}]{spark}[/{color}] "
                f"[bold]{tok:>5,}[/bold] "
                f"[dim]{pct:>4.1f}%[/dim]"
            )

        rows = [
            _row("System",     system_tok,     "blue"),
            _row("Scratchpad", scratchpad_tok, "cyan"),
            _row("Beam",       beam_tok,       "bright_cyan"),
            _row("Chat",       chat_tok,       "green"),
        ]
        if pinned_tok > 0:
            rows.append(_row("Pins", pinned_tok, "magenta"))

        static_rows = "\n".join(rows)
        self._ctx_breakdown_cache = static_rows
        self._ctx_breakdown_cache_ts = now

        if stream_tok > 0:
            pct = min(100.0, (stream_tok / ctx_max) * 100)
            filled = min(SPARK_WIDTH, round((pct / 100.0) * SPARK_WIDTH))
            spark = "▪" * filled + "·" * (SPARK_WIDTH - filled)
            stream_row = (
                f"[dim]{'Streaming':<10}[/dim] "
                f"[yellow]{spark}[/yellow] "
                f"[bold]{stream_tok:>5,}[/bold] "
                f"[dim]{pct:>4.1f}%[/dim]"
            )
            return static_rows + "\n" + stream_row

        return static_rows

    def _context_usage(self) -> tuple[int, int, float]:
        tokens_est = self._live_context_tokens()
        ctx_max = CTX_SIZE
        pct = min(100.0, (tokens_est / ctx_max) * 100) if ctx_max > 0 else 0.0
        return int(tokens_est), ctx_max, pct

    def _git_branch(self) -> str:
        try:
            head_file = os.path.join(self.engine.project_root, ".git", "HEAD")
            if os.path.exists(head_file):
                with open(head_file, "r", encoding="utf-8") as f:
                    ref = f.read().strip()
                if ref.startswith("ref: refs/heads/"):
                    return ref[16:]
                if len(ref) >= 7:
                    return ref[:7]
        except Exception:
            pass

        import time as _t
        now = _t.time()
        if now - getattr(self, "_git_branch_ts", 0.0) < 5.0 and hasattr(self, "_git_branch_cache"):
            return self._git_branch_cache
        try:
            proc = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.engine.project_root,
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            name = proc.stdout.strip()
            res = name if proc.returncode == 0 and name else ""
        except Exception:
            res = ""
        self._git_branch_ts = now
        self._git_branch_cache = res
        return res

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

    def action_attach_context(self) -> None:
        def _on_result(result: Optional[str]) -> None:
            if result is None:
                return
            if self._user_input is not None:
                self._add_context_chip(result)
                self.set_focus(self._user_input)

        self.push_screen(
            AttachContextModal(self.engine.project_root),
            _on_result,
        )

    def action_paste_image(self) -> None:
        from core.utils.image_utils import save_clipboard_image

        saved_p = save_clipboard_image(self.project_root)
        if saved_p:
            filename = os.path.basename(saved_p)
            self._add_context_chip(saved_p)
            self.notify(
                f"🖼 Attached clipboard image: {filename}",
                severity="information",
                timeout=3,
            )
            if self._user_input is not None:
                self.set_focus(self._user_input)
        else:
            self.notify("No image found on clipboard.", severity="warning", timeout=2)

    @on(Button.Pressed, "#attach-context-btn")
    def _on_attach_context_btn_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.action_attach_context()

    def _add_context_chip(self, filepath: str) -> None:
        if not filepath:
            return
        clean_path = filepath.strip().lstrip("@")
        chips_bar = self.query_one("#context-chips-bar", Horizontal)
        # Avoid duplicate chips
        existing_chips = [
            getattr(btn, "_filepath", getattr(btn, "tooltip", "")).strip().lstrip("@")
            for btn in chips_bar.query(".context-chip")
        ]
        if clean_path in existing_chips:
            return

        from core.utils.image_utils import is_image_file

        is_img = is_image_file(clean_path)
        icon_prefix = r"[bold green]\[IMG][/] " if is_img else ""
        chip_classes = "context-chip image-chip" if is_img else "context-chip"

        btn = Button(f"{icon_prefix}{clean_path} ✕", classes=chip_classes)
        # Store original path for submission reconstruction
        btn._filepath = clean_path
        btn.tooltip = clean_path
        chips_bar.mount(btn)
        chips_bar.add_class("has-chips")

    @on(Button.Pressed, ".context-chip")
    def _on_context_chip_pressed(self, event: Button.Pressed) -> None:
        btn = event.button
        btn.remove()
        chips_bar = self.query_one("#context-chips-bar", Horizontal)
        # Textual's remove() is async, so the button is still in the DOM during this handler.
        # If there's 1 or fewer chips left, it means the bar will be empty.
        if len(list(chips_bar.query(".context-chip"))) <= 1:
            chips_bar.remove_class("has-chips")
        self.set_focus(self._user_input)

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
                self.update_sidebar_meta()
                self.notify(
                    f"Working directory set to {escape(str(chosen_dir))}",
                    severity="information",
                    timeout=2,
                )

        self.push_screen(FolderPickerModal(self.engine.project_root), _on_picker_result)

    def action_toggle_sidebar(self) -> None:
        try:
            sb = self.query_one("#explorer-sidebar")
            resizer = self.query_one("#resizer-left")
            self._show_sidebar = not getattr(self, "_show_sidebar", True)
            sb.display = self._show_sidebar
            resizer.display = self._show_sidebar
        except Exception:
            pass

    def action_toggle_left_sidebar(self) -> None:
        self.action_toggle_sidebar()

    def action_toggle_editor_split(self) -> None:
        try:
            editor_pane = self.query_one("#editor-split-pane")
            editor_pane.display = not editor_pane.display
            try:
                resizer_editor = self.query_one("#resizer-editor")
                resizer_editor.display = editor_pane.display
            except Exception:
                pass
            status = "shown" if editor_pane.display else "hidden"
            self.notify(
                f"Editor split pane {status}", severity="information", timeout=2
            )
        except Exception:
            pass

    def action_toggle_right_sidebar(self) -> None:
        try:
            sb = self.query_one("#plan-sidebar")
            resizer = self.query_one("#resizer-right")
            self._show_plan_sidebar = not getattr(self, "_show_plan_sidebar", True)
            sb.display = self._show_plan_sidebar
            resizer.display = self._show_plan_sidebar
        except Exception:
            pass

    def action_expand_left_pane(self) -> None:
        self.left_pane_width = min(60, getattr(self, "left_pane_width", 24) + 2)
        self._apply_pane_widths()
        self.notify(f"Left Pane: {self.left_pane_width} cols", timeout=1)

    def action_shrink_left_pane(self) -> None:
        self.left_pane_width = max(14, getattr(self, "left_pane_width", 24) - 2)
        self._apply_pane_widths()
        self.notify(f"Left Pane: {self.left_pane_width} cols", timeout=1)

    def action_expand_editor_pane(self) -> None:
        self.editor_pane_width = min(140, getattr(self, "editor_pane_width", 50) + 4)
        self._apply_pane_widths()
        self.notify(f"Editor Pane: {self.editor_pane_width} cols", timeout=1)

    def action_shrink_editor_pane(self) -> None:
        self.editor_pane_width = max(20, getattr(self, "editor_pane_width", 50) - 4)
        self._apply_pane_widths()
        self.notify(f"Editor Pane: {self.editor_pane_width} cols", timeout=1)

    def action_expand_right_pane(self) -> None:
        self.right_pane_width = min(60, getattr(self, "right_pane_width", 30) + 2)
        self._apply_pane_widths()
        self.notify(f"Right Pane: {self.right_pane_width} cols", timeout=1)

    def action_shrink_right_pane(self) -> None:
        self.right_pane_width = max(16, getattr(self, "right_pane_width", 30) - 2)
        self._apply_pane_widths()
        self.notify(f"Right Pane: {self.right_pane_width} cols", timeout=1)

    def _apply_pane_widths(self) -> None:
        try:
            explorer = self.query_one("#explorer-sidebar")
            explorer.styles.width = getattr(self, "left_pane_width", 24)
        except Exception:
            pass

        try:
            editor = self.query_one("#editor-split-pane")
            if hasattr(self, "editor_pane_width") and self.editor_pane_width:
                editor.styles.width = self.editor_pane_width
        except Exception:
            pass

        try:
            plan = self.query_one("#plan-sidebar")
            plan.styles.width = getattr(self, "right_pane_width", 30)
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

    def action_wipe_session(self) -> None:
        """Completely wipe session context and memory, starting a clean fresh session."""
        if hasattr(self, "engine") and self.engine:
            self.engine.reset_session()

        try:
            container = self.query_one("#chat-container", TranscriptView)
            container.clear()
        except Exception:
            try:
                container = self.query_one("#chat-container")
                container.remove_children()
            except Exception:
                pass

        if self._trajectory_rail is not None:
            self._trajectory_rail.clear()

        # Update telemetry & memory widgets
        self.update_status_bar()
        self.update_sidebar_meta()
        try:
            mem_widget = self.query_one("#agent-memory-panel", AgentMemoryWidget)
            mem_widget.update_memory()
        except Exception:
            pass

        self.append_output_log(
            "⚡ Session context wiped — all memory, message history, and REPL state reset to clean slate.",
            severity="info",
        )
        self.notify(
            "✨ Session context wiped — fresh session started",
            title="Session Reset",
            severity="information",
            timeout=3,
        )

    def action_reset_session(self) -> None:
        self.action_wipe_session()

    def action_clear(self) -> None:
        self.action_wipe_session()

    def action_compact_context(self) -> None:
        """Manually trigger memory context compaction."""
        mem = getattr(self.engine, "_memory", None)
        if not mem or len(getattr(mem, "messages", [])) <= 1:
            self.notify(
                "No active memory context to compact (need at least 2 messages)",
                title="Context Compaction",
                severity="warning",
                timeout=3,
            )
            return
        tb, ta, tf = self.engine.compact_context(mem, force=True)
        self.update_status_bar()
        self.update_sidebar_meta()
        try:
            mem_widget = self.query_one("#agent-memory-panel", AgentMemoryWidget)
            mem_widget.update_memory()
        except Exception:
            pass

        if tf > 0:
            msg = f"Context compacted: {tb:,} → {ta:,} tokens ({tf:,} tokens freed)"
            self.append_output_log(f"🧹 {msg}", severity="info")
            self.notify(
                msg,
                title="Context Compacted",
                severity="information",
                timeout=4,
            )
        else:
            msg = f"Context already minimal ({ta:,} tokens)"
            self.notify(
                msg,
                title="Context Compacted",
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
    last_state = load_last_state()
    saved_provider = last_state.get("last_provider")
    saved_model = last_state.get("last_model")
    saved_mode = last_state.get("last_execution_mode", "plan")
    saved_kv = last_state.get("last_kv_cache_mode", "turbo3")
    
    os.environ["KV_CACHE_COMPRESSION"] = saved_kv

    if saved_model and args.model == MODEL_NAME:
        args.model = saved_model

    if args.provider is None:
        if saved_provider:
            args.provider = saved_provider
        elif fetch_provider_models(LMSTUDIO_BASE_URL):
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
        execution_mode=saved_mode,
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
