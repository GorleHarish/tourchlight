"""
Torchlight Agent — Codex / Tiny-Brain 2 Style IDE TUI (Textual)
Full-featured IDE coding agent experience with sidebar, file tree, memory meter, and modal approvals.
"""
from __future__ import annotations
import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Vertical, Horizontal, Container
from textual.widgets import Header, Footer, Static, Input, Button, Label, DirectoryTree, ProgressBar, TextArea
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
    MODEL_NAME, MAX_RECURSION_DEPTH, PROVIDER,
    CHIP_NAME, TOTAL_RAM_GB, IS_8GB_DEVICE, CTX_SIZE,
    normalize_model_name, list_available_models, is_port_in_use,
    LMSTUDIO_BASE_URL, LMSTUDIO_API_KEY, fetch_provider_models,
)
from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized, Step
from core.tools.classification import CONFIRM, REVIEW
from rlm_optimized.memory_monitor import format_memory_status, is_memory_safe

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
    """Modal dialog for tool & file modification approval."""

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
    }
    #approval-tool {
        margin-bottom: 1;
        color: $foreground;
    }
    #approval-args {
        color: $success;
        max-height: 14;
        overflow-y: auto;
    }
    #approval-hint {
        text-align: center;
        color: $foreground-muted;
        margin-top: 1;
    }
    """

    def __init__(self, tool_name: str, risk: str, tool_args: dict):
        super().__init__()
        self.tool_name = tool_name
        self.risk = risk
        self.tool_args = tool_args

    def compose(self) -> ComposeResult:
        risk_icon = "🛑" if self.risk == REVIEW else "⚠️ "
        risk_label = "CRITICAL / DESTRUCTIVE OPERATIONAL REVIEW" if self.risk == REVIEW else "CONFIRM ACTION PERMISSION"

        with Vertical(id="approval-dialog"):
            yield Static(f"{risk_icon} {risk_label}", id="approval-title")
            yield Static(f"Action: [bold bright_blue]{escape(self.tool_name)}[/]", id="approval-tool")
            
            display_args = dict(self.tool_args) if self.tool_args else {}
            if self.tool_name == "WRITE_FILE" and "content" in display_args:
                display_args["content"] = f"... [{len(str(display_args['content']))} chars of code hidden]"
            elif self.tool_name == "EDIT_FILE":
                if "old_text" in display_args:
                    display_args["old_text"] = f"... [{len(str(display_args['old_text']))} chars hidden]"
                if "new_text" in display_args:
                    display_args["new_text"] = f"... [{len(str(display_args['new_text']))} chars hidden]"
                    
            args_str = json.dumps(display_args, indent=2)
            if len(args_str) > 4000:
                args_str = args_str[:4000] + "\n... [Arguments Truncated]"
            yield Static(escape(args_str), id="approval-args")
            with Horizontal(id="approval-buttons"):
                yield Button("✅ Allow (Y)", variant="success", id="allow-btn")
                yield Button("❌ Deny (N)", variant="error", id="deny-btn")
            yield Static("[dim]Press Y to allow, N or Esc to deny[/]", id="approval-hint")

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
            yield Static("📂 Select Working Directory Folder (Computer Wide)", id="picker-title")
            with Horizontal(id="picker-jumps"):
                yield Button("💻 Root (/)", variant="default", id="jump-root")
                yield Button("🏠 Home (~)", variant="default", id="jump-home")
                yield Button("🖥️ Desktop", variant="default", id="jump-desktop")
                yield Button("📁 Current", variant="default", id="jump-current")
            yield Input(placeholder="Or type/paste path directly...", value=self.selected_path, id="picker-input")
            yield Static(f"Selected: {escape(self.selected_path)}", id="picker-path")
            yield DirectoryTree(self.root_path, id="picker-tree")
            with Horizontal(id="picker-buttons"):
                yield Button("✅ Select This Folder", variant="success", id="select-folder-btn")
                yield Button("❌ Cancel", variant="error", id="cancel-folder-btn")

    @on(Input.Submitted, "#picker-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        target = os.path.abspath(os.path.expanduser(event.value.strip()))
        if os.path.isdir(target):
            self.selected_path = target
            self.query_one("#picker-path", Static).update(f"Selected: [bold green]{escape(self.selected_path)}[/]")
            try:
                tree = self.query_one("#picker-tree", DirectoryTree)
                tree.path = target
            except Exception:
                pass
        else:
            self.query_one("#picker-path", Static).update(f"[bold red]Invalid directory:[/] {escape(target)}")

    @on(DirectoryTree.DirectorySelected, "#picker-tree")
    def on_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        self.selected_path = str(event.path)
        try:
            self.query_one("#picker-path", Static).update(f"Selected: [bold green]{escape(self.selected_path)}[/]")
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
                self.query_one("#picker-path", Static).update(f"Selected: [bold green]{escape(self.selected_path)}[/]")
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
            self.models.append({
                "name": f"LM Studio: {model_id}",
                "id": model_id,
                "provider": "lmstudio",
            })

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
                        classes="model-card"
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
                    yield Static("[dim italic]No conversation turns available to select.[/]")
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
                            classes="copy-item-card"
                        )
                        yield Button(f"Copy {role_icon} Turn #{len(self.history) - idx}", id=btn_id, variant="primary")
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
                id="mode-desc"
            )
            yield Static(
                "💡 Tooltip: Goal Mode initializes .torchlight/goal_spec.json and .torchlight/tasks.md "
                "to track multi-epoch sub-tasks across context resets and enforce verification gates.",
                id="mode-tooltip"
            )
            with Horizontal():
                yield Button("💬 Chat Mode (Lightweight)", id="select-chat-btn", variant="primary", classes="mode-btn")
                yield Button("🎯 Goal Mode (Harness)", id="select-goal-btn", variant="success", classes="mode-btn")
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
            yield Static("📡 Background Agent Action Telemetry & Live Inspector", id="status-title")
            with Horizontal(id="status-metrics-row"):
                yield Static(f"Current State:\n[bold cyan]{escape(self.current_state)}[/]", classes="metric-badge")
                yield Static(f"Total Events Logged:\n[bold yellow]{len(self.events)}[/]", classes="metric-badge")
                yield Static(f"System Context:\n[dim]{escape(self.meta_summary.splitlines()[0]) if self.meta_summary else ''}[/]", classes="metric-badge")
            yield Static("📜 Real-Time Agent Action Log:", classes="sidebar-section-title")
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
                        yield Static(f"🎯 Autonomous Goal: [bold cyan]{escape(title)}[/] ({pct:.0f}% - {ver}/{tot} Verified)", classes="status-log-entry")
                        for t in tasks:
                            st = t.get("status", "pending")
                            badge = "[bold green]✓ VERIFIED[/]" if st == "verified" else "[bold cyan]● RUNNING[/]" if st == "in_progress" else "[bold red]✗ FAILED[/]" if st == "failed" else "[yellow]⏳ PENDING[/]"
                            yield Static(f"  {badge} [bold]{escape(str(t.get('id')))}[/bold]: {escape(str(t.get('description')))} (Attempts: {t.get('attempts',0)}/{t.get('max_attempts',3)})", classes="status-log-entry")
                except Exception:
                    pass

                if not self.events:
                    yield Static("[dim italic]No agent background activity recorded yet.[/]")
                else:
                    for ev in reversed(self.events):
                        ts = ev.get("time", "")
                        state = ev.get("state", "INFO")
                        det = json.dumps(ev.get("details", {}))
                        if len(det) > 1000:
                            det = det[:1000] + " ...[Truncated]"
                        badge_style = "bold green" if state in ("IDLE", "TOOL_DONE") else "bold cyan" if "TOOL" in state else "bold yellow"
                        yield Static(
                            f"[{ts}] [{badge_style}]{state}[/]\n"
                            f"[dim]{escape(det)}[/]",
                            classes="status-log-entry"
                        )
            with Horizontal(id="status-buttons"):
                yield Button("🧹 Clear Logs (C)", variant="warning", id="clear-status-btn")
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
            yield Static("⌨️ Torchlight Codex - Shortcuts & Slash Commands", id="help-title")
            help_md = """
### ⌨️ Keyboard Shortcuts
- **Enter** — Send prompt
- **Shift+Enter** — New line in prompt (multi-line input)
- **Ctrl+B** — Toggle Sidebar
- **Ctrl+T** — Cycle Theme
- **Ctrl+M** — Select Active Model
- **Ctrl+O** — Change Working Directory (Computer Wide)
- **Ctrl+H** — Open Shortcuts & Help Modal
- **Ctrl+A** — Open Telemetry & Status
- **Ctrl+X** — Copy Selection
- **Ctrl+Y** — Copy Entire Chat History
- **Ctrl+K** — Copy Last Response
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
        Binding("ctrl+k", "copy_last", "Copy Last", show=True),
        Binding("ctrl+o", "open_folder", "Open Folder", show=True),
        Binding("ctrl+m", "select_model", "Select Model", show=True),
        Binding("ctrl+g", "select_mode", "Session Mode", show=True),
        Binding("ctrl+b", "toggle_sidebar", "Toggle Sidebar", show=True),
        Binding("ctrl+t", "cycle_theme", "Theme", show=True),
        Binding("ctrl+p", "compact_context", "Compact Context", show=True),
        Binding("ctrl+r", "reset_session", "Reset REPL", show=False),
        Binding("ctrl+l", "clear", "Clear Chat", show=False),
        Binding("ctrl+c", "quit", "Quit", show=True),
    ]

    def __init__(self, engine: RLMEngineOptimized,
                 model_name: str = "", provider_name: str = "",
                 engine_port: int = 8080, externally_managed: bool = False):
        super().__init__()
        self.engine = engine
        self.model_name = model_name
        self.provider_name = provider_name
        self.engine_port = engine_port
        self.externally_managed = externally_managed
        self._streaming_text = ""
        self._streaming_widget: Optional[Static] = None
        self._is_running = False
        self._show_sidebar = True
        self._chat_history: list = []
        self._agent_state: str = "IDLE"
        self._agent_events: list[dict] = []
        self._server_starting: bool = False

    def _handle_status_change(self, payload: dict) -> None:
        import datetime
        state = payload.get("state", "IDLE")
        details = payload.get("details", {})
        self._agent_state = state
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._agent_events.append({
            "time": ts,
            "state": state,
            "details": details,
        })
        if len(self._agent_events) > 200:
            self._agent_events.pop(0)

        if state == "REFINED":
            flaws = details.get("flaws", [])
            tool_name = details.get("tool_name", "")
            target = f" for {escape(tool_name)}" if tool_name else ""
            escaped_flaws = [escape(f) for f in flaws]
            flaw_str = f" [dim](Fixed: {', '.join(escaped_flaws)})[/dim]" if flaws else ""
            try:
                container = self.query_one("#chat-container")
                self._safe_mount(container, Static(f" [bold green]✨ Refined proposal{target}[/bold green]{flaw_str}"))
            except Exception:
                pass

        try:
            self.call_after_refresh(self.update_status_bar)
        except Exception:
            self.update_status_bar()


    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body-container"):
            with Vertical(id="sidebar"):
                yield Static("Engine Control", classes="sidebar-section-title")
                with Horizontal(id="engine-btn-bar-1"):
                    yield Button("Start", id="start-engine-btn", variant="success")
                    yield Button("Restart", id="restart-engine-btn", variant="warning")
                    yield Button("Stop", id="stop-engine-btn", variant="error")
                with Horizontal(id="engine-btn-bar-2"):
                    yield Button("Kill Session", id="kill-session-btn", variant="error")
                yield Static(classes="sidebar-divider")
                yield Static("Workspace Explorer", classes="sidebar-section-title")
                yield DirectoryTree(self.engine.project_root, id="file-tree")
                yield Static(classes="sidebar-divider")
                if Collapsible is not None:
                    yield Collapsible(
                        Static(self._build_meta_text(), id="meta-panel"),
                        title="⚙️ System Status",
                        collapsed=True,
                        id="meta-collapsible"
                    )
                else:
                    yield Static("System Status", classes="sidebar-section-title")
                    yield Static(self._build_meta_text(), id="meta-panel")
                yield Static(classes="sidebar-divider")
                yield Static("📋 Implementation Plan", classes="sidebar-section-title")
                yield Static(self._build_plan_text(), id="plan-panel")
            with Vertical(id="chat-pane"):
                yield Horizontal(
                    Static("", id="status-left"),
                    Button("⌨️ Shortcuts & Help", id="help-btn", variant="default"),
                    id="status-bar",
                )
                yield VerticalScroll(id="chat-container")
                with Vertical(id="input-area"):
                    with Horizontal(id="input-header-bar"):
                        yield Button(
                            f"🤖 {escape(self.model_name)} ▾",
                            id="input-model-badge",
                            variant="default"
                        )
                        yield Button(
                            "🗜️ Compact",
                            id="compact-btn",
                            variant="default"
                        )
                        yield Static(
                            self._build_context_progress_text(),
                            id="context-progress-badge"
                        )
                    with Horizontal(id="input-row"):
                        yield TextArea(
                            "",
                            id="user-input",
                            language=None,
                            show_line_numbers=False,
                            soft_wrap=True,
                            tab_behavior="indent",
                        )
                        yield Button("Send", id="send-btn", variant="primary")
                        yield Static("", id="input-spinner")
        yield Footer()

    def _build_plan_text(self) -> str:
        project_root = getattr(self.engine, "project_root", os.getcwd())
        plan_path = os.path.join(project_root, "implementation_plan.md")
        alt_tasks_path = os.path.join(project_root, ".torchlight", "tasks.md")
        alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")

        target_file = None
        file_type = None

        if os.path.exists(plan_path):
            target_file = plan_path
            file_type = "markdown"
        elif os.path.exists(alt_tasks_path):
            target_file = alt_tasks_path
            file_type = "markdown"
        elif os.path.exists(alt_goal_path):
            target_file = alt_goal_path
            file_type = "json"
        else:
            return "[dim]No active implementation_plan.md[/dim]"

        try:
            if file_type == "json":
                with open(target_file, "r", encoding="utf-8") as f:
                    goal_data = json.load(f)
                goal_title = goal_data.get("title", "Autonomous Goal")
                raw_tasks = goal_data.get("tasks", [])
                tasks = [f"[bold cyan]📌 {escape(goal_title)}[/bold cyan]"]
                completed = 0
                for t in raw_tasks:
                    st = t.get("status", "pending")
                    desc = escape(str(t.get("description") or t.get("id") or "Task"))
                    if st in ("verified", "completed"):
                        completed += 1
                        tasks.append(f"[bold green]✅ {desc}[/bold green]")
                    elif st == "in_progress":
                        tasks.append(f"[bold cyan]● {desc}[/bold cyan]")
                    else:
                        tasks.append(f"[yellow]⏳ {desc}[/yellow]")
                total = len(raw_tasks)
            else:
                with open(target_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                tasks = []
                completed = 0
                total = 0
                import re
                chk_regex = re.compile(r"^(?:[-*+>]|\d+[\.\)])?\s*\[([ xX/\-v✓~])\]\s*(.*)$")

                for line in lines:
                    stripped = line.strip()
                    m = chk_regex.match(stripped)
                    if m:
                        state, task_raw = m.group(1), m.group(2).strip()
                        if task_raw.lower().startswith("progress:"):
                            continue
                        total += 1
                        task_text = escape(task_raw)
                        if state in ("x", "X", "v", "✓"):
                            completed += 1
                            tasks.append(f"[bold green]✅ {task_text}[/bold green]")
                        elif state in ("/", "-", "~"):
                            tasks.append(f"[bold cyan]● {task_text}[/bold cyan]")
                        else:
                            tasks.append(f"[yellow]⏳ {task_text}[/yellow]")
                    elif stripped.startswith("#"):
                        title = escape(stripped.lstrip("#").strip())
                        if title and not title.lower().startswith("implementation plan"):
                            tasks.append(f"[bold cyan]📌 {title}[/bold cyan]")

            if total == 0:
                basename = os.path.basename(target_file)
                return f"[dim]{basename} exists (0 tasks)[/dim]"

            pct = int((completed / total) * 100) if total > 0 else 0
            bar_width = 10
            filled = min(bar_width, int(round((pct / 100.0) * bar_width)))
            bar = "█" * filled + "░" * (bar_width - filled)

            header = f"[bold white]Progress:[/] [{bar}] [bold green]{pct}%[/] [dim]({completed}/{total})[/dim]"
            body = "\n".join(tasks[:12])
            if len(tasks) > 12:
                body += f"\n[dim]...+{len(tasks)-12} more[/dim]"

            return f"{header}\n\n{body}"
        except Exception:
            return "[dim red]Error reading plan file[/dim red]"

    def _build_context_progress_text(self) -> str:
        mem = getattr(self.engine, "_memory", None)
        if mem and hasattr(mem, "total_tokens") and mem.total_tokens > 0:
            tokens_est = mem.total_tokens
        else:
            tokens_est = getattr(self.engine, "_total_llm_calls", 0) * 450
            
        ctx_max = CTX_SIZE
        pct = min(100, int((tokens_est / ctx_max) * 100)) if ctx_max > 0 else 0
        bar_width = 10
        filled = min(bar_width, int(round((pct / 100.0) * bar_width)))
        bar = "█" * filled + "░" * (bar_width - filled)

        if pct < 50:
            color = "green"
        elif pct < 75:
            color = "yellow"
        else:
            color = "red"

        return f"[dim]Context:[/] [{color}]{bar}[/{color}] [bold {color}]{pct}%[/bold {color}] [dim]({tokens_est:,}/{ctx_max:,})[/dim]"

    def _build_meta_text(self) -> str:
        mem = getattr(self.engine, "_memory", None)
        if mem and hasattr(mem, "total_tokens") and mem.total_tokens > 0:
            tokens_est = mem.total_tokens
        else:
            tokens_est = getattr(self.engine, "_total_llm_calls", 0) * 450

        server_status_str = getattr(self, "engine_server_status", "● Active")
        if "Offline" in server_status_str or "Error" in server_status_str or "404" in server_status_str:
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
            mp = self.query_one("#meta-panel")
            mp.update(self._build_meta_text())
        except Exception:
            pass
        try:
            pp = self.query_one("#plan-panel")
            pp.update(self._build_plan_text())
        except Exception:
            pass
        try:
            cp = self.query_one("#context-progress-badge")
            cp.update(self._build_context_progress_text())
        except Exception:
            pass
        try:
            mb = self.query_one("#input-model-badge", Button)
            mb.label = f"🤖 {self.model_name} ▾"
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
        container = self.query_one("#chat-container")
        self._safe_mount(container, Static(Panel(
            escape(user_text),
            title="You",
            border_style="bright_blue",
        )))

        self._run_agent(user_text)

    @on(Button.Pressed, "#send-btn")
    async def on_send_button(self) -> None:
        if self._is_running:
            self.stop_current_agent()
            return
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
                btn.label = "⏹ Stop"
                btn.variant = "error"
                btn.disabled = False
                spinner.update("[bold cyan]●[/]")
            else:
                btn.label = "Send"
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
            self.theme = "torchlight"
        except Exception:
            try:
                self.theme = "textual-dark"
            except Exception:
                pass

        try:
            container = self.query_one("#chat-container")

            # Welcome banner - 3-step quick start
            container.mount(Static(Panel(
                "[bold cyan]Torchlight Codex IDE[/]\n\n"
                "[bold white]1.[/] Check engine status in sidebar (green = ready)\n"
                "[bold white]2.[/] Pick a model with [bold yellow]Ctrl+M[/] or use the default\n"
                "[bold white]3.[/] Type your task below and press [bold yellow]Send[/] or Enter\n\n"
                "[dim]Press Ctrl+B for sidebar | Ctrl+T for theme | /help for commands[/]",
                title="Welcome",
                border_style="cyan",
            )))

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
            self.set_interval(3.0, self._auto_refresh_engine_status)
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
            sidebar = self.query_one("#sidebar")
            if w < 80:
                sidebar.display = False
                self._show_sidebar = False
            elif self._show_sidebar:
                sidebar.display = True
        except Exception:
            pass

    def on_resize(self) -> None:
        self._apply_responsive_layout()

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

        # Handle Slash Commands
        if user_text.startswith("/"):
            await self._handle_slash_command(user_text)
            return

        # Show user message
        self._chat_history.append({"role": "user", "content": user_text})
        container = self.query_one("#chat-container")
        self._safe_mount(container, Static(Panel(
            escape(user_text),
            title="You",
            border_style="bright_blue",
        )))

        # Run agent
        self._run_agent(user_text)

    @on(Button.Pressed, "#send-btn")
    async def on_send_button(self) -> None:
        if self._is_running:
            self.stop_current_agent()
            return
        await self._submit_user_input()

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

    def _set_input_enabled(self, enabled: bool) -> None:
        try:
            inp = self.query_one("#user-input", TextArea)
            btn = self.query_one("#send-btn")
            spinner = self.query_one("#input-spinner")
            inp.disabled = not enabled
            btn.disabled = not enabled
            if not enabled:
                spinner.update("[bold cyan]>[/]")
            else:
                spinner.update("")
        except Exception:
            pass

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
            container.mount(Static(Panel(Markdown(help_md), title="Help", border_style="yellow")))

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
                    new_mode = ExecutionMode.GOAL if m_str == "goal" else ExecutionMode.CHAT
                    if hasattr(self.engine.memory.state, "execution_mode"):
                        self.engine.memory.state.execution_mode = new_mode
                    if m_str == "goal":
                        try:
                            from core.execution.autonomous_harness import AutonomousHarness
                            harness = AutonomousHarness(project_root=self.engine.project_root, memory=self.engine.memory)
                            harness.ensure_goal_spec_initialized()
                        except Exception:
                            pass
                        self.notify("Switched to Goal Mode (Task Graph initialized in .torchlight/tasks.md)", severity="success", timeout=3)
                    else:
                        self.notify("Switched to Chat Mode (Lightweight Q&A)", severity="information", timeout=3)
                    self.update_status_bar()
                else:
                    self.notify("Usage: /mode chat or /mode goal", severity="warning", timeout=3)


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
                tree = self.query_one("#file-tree", DirectoryTree)
                tree.path = target_path
                self.notify(f"Directory changed to {target_path}", severity="information", timeout=2)
            else:
                self.notify(f"Directory not found: {arg}", severity="error", timeout=3)

        elif cmd in ("/index", "/reindex"):
            self._start_ast_indexing()

        elif cmd == "/model":
            if not arg:
                self.notify(f"Current model: {escape(self.model_name)}. Usage: /model <name>", severity="information", timeout=3)
            else:
                normalized = normalize_model_name(arg)
                self.model_name = normalized
                if hasattr(self.engine.client, "model"):
                    self.engine.client.model = normalized
                self.update_status_bar()
                self.update_sidebar_meta()
                self.notify(f"Switched model to {escape(normalized)}", severity="information", timeout=2)

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
            tree = self.query_one("#file-tree", DirectoryTree)
            tree.path = self.engine.project_root
            self.notify("File tree refreshed", severity="information", timeout=2)

        else:
            self.notify(f"Unknown command: {cmd}. Type /help for list.", severity="error", timeout=3)

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
        self._is_running = True
        self._set_input_enabled(False)
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
                connection_failed = "connection refused" in err_msg or "connection error" in err_msg
                if connection_failed and port > 0 and self.externally_managed:
                    raise ConnectionError(
                        f"Could not reach {self.provider_name} on port {port}. "
                        f"Make sure it's running (for LM Studio: open the app, load a model, "
                        f"and start its Local Server), then try again."
                    ) from first_err
                if connection_failed and port > 0 and not is_port_in_use(port):
                    self._remove_streaming()
                    self.notify(f"Server refused on port {port}, auto-starting engine...", severity="warning", timeout=3)
                    self.on_start_engine_btn()

                    # Wait up to 10 seconds for the port to become ready
                    server_ready = False
                    for _ in range(10):
                        await asyncio.sleep(1)
                        if is_port_in_use(port):
                            server_ready = True
                            break

                    if server_ready:
                        self.notify(f"Engine active on port {port}, retrying task...", severity="information", timeout=2)
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

            container.mount(Static(
                f"  [dim]── ✓ {result.total_llm_calls} LLM call(s), "
                f"{len(result.steps)} step(s) ──[/]",
                classes="step-status",
            ))
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

    def _ensure_streaming_widget(self) -> Static:
        if getattr(self, "_streaming_widget", None) is None:
            self._streaming_text_widget = Static("", classes="stream-text")
            if Collapsible is not None:
                self._streaming_widget = Collapsible(self._streaming_text_widget, title="💭 Thinking...", collapsed=False)
            else:
                self._streaming_widget = self._streaming_text_widget
            container = self.query_one("#chat-container")
            container.mount(self._streaming_widget)
            self.call_after_refresh(self._scroll_chat_to_end)
        return getattr(self, "_streaming_text_widget", self._streaming_widget)

    def _append_token(self, chunk: str) -> None:
        self._streaming_text += chunk
        try:
            widget = self._ensure_streaming_widget()
            display_text = self._streaming_text
            is_preparing = False

            if "<TOOL" in display_text:
                display_text = display_text.split("<TOOL")[0].strip()
                is_preparing = True
            elif "<tool_call>" in display_text:
                display_text = display_text.split("<tool_call>")[0].strip()
                is_preparing = True

            if len(display_text) > 4000:
                display_text = "... [truncated streaming] ...\n" + display_text[-4000:]

            escaped = escape(display_text)
            if is_preparing:
                if escaped:
                    escaped += "\n\n"
                escaped += "[dim cyan]⚡ Preparing tool action...[/dim cyan]"

            widget.update(escaped)
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
            self._streaming_text_widget = None
        self._streaming_text = ""

    # ── Step Display ────────────────────────────────────────────────────

    def _handle_step(self, step: Step) -> None:
        container = self.query_one("#chat-container")
        self._remove_streaming()

        try:
            has_thinking = bool(step.thinking and step.thinking.strip() not in ("(forced)", ""))
            trimmed_thinking = ""
            if has_thinking:
                trimmed_thinking = step.thinking.strip()
                if len(trimmed_thinking) > 15000:
                    trimmed_thinking = trimmed_thinking[:15000] + "\n... [Reasoning Truncated]"

            # Tool execution - Single Unified Card (with embedded Rationale if present)
            if step.action == "tool":
                label = step.tool_name or "TOOL"
                display_args = dict(step.tool_args) if isinstance(step.tool_args, dict) else {}

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
                    display_args["content"] = f"... [{len(str(display_args['content']))} chars of code hidden]"
                elif label == "EDIT_FILE":
                    if "old_text" in display_args:
                        display_args["old_text"] = f"... [{len(str(display_args['old_text']))} chars hidden]"
                    if "new_text" in display_args:
                        display_args["new_text"] = f"... [{len(str(display_args['new_text']))} chars hidden]"

                args_str = json.dumps(display_args, indent=2) if display_args else ""
                if len(args_str) > 4000:
                    args_str = args_str[:4000] + "\n... [Arguments Truncated for UI Performance]"

                res_raw = step.result or ""
                denied = "denied" in res_raw.lower()
                is_err = (
                    res_raw.startswith("Error")
                    or res_raw.startswith("❌")
                    or ("requires" in res_raw.lower() and "block" in res_raw.lower())
                    or ("failed" in res_raw.lower() and "error" in res_raw.lower())
                )

                if denied:
                    badge_icon = "⚠️"
                    badge_style = "yellow"
                    status_str = " (Denied)"
                elif is_err:
                    badge_icon = "❌"
                    badge_style = "red"
                    status_str = " (Failed)"
                else:
                    badge_icon = "✓"
                    badge_style = "green"
                    status_str = ""

                escaped_label = escape(label)
                escaped_target = escape(target_name)
                card_icon = "✏️" if label in ("WRITE_FILE", "EDIT_FILE") else "🔧"
                card_title = f"{badge_icon} {card_icon} {escaped_label}"
                if escaped_target:
                    card_title += f" [cyan]{escaped_target}[/cyan]"
                card_title += status_str

                body_parts = []
                if trimmed_thinking:
                    body_parts.append(f"[dim magenta]💭 Rationale:[/dim magenta]\n[dim]{escape(trimmed_thinking)}[/dim]")
                if args_str:
                    body_parts.append(f"[dim]Args:[/dim]\n[dim]{escape(args_str)}[/dim]")
                if res_raw:
                    display_result = res_raw
                    if len(display_result) > 15000:
                        display_result = display_result[:15000] + "\n... [Output Truncated for UI Performance]"
                    body_parts.append(f"[bold]Result:[/bold]\n{escape(display_result)}")

                combined_body = "\n\n".join(body_parts) if body_parts else "[dim]No arguments or output[/dim]"

                if Collapsible is not None:
                    is_collapsed = not (is_err or denied)
                    self._safe_mount(container, Collapsible(
                        Static(combined_body, classes="stream-text"),
                        title=card_title,
                        collapsed=is_collapsed
                    ))
                else:
                    self._safe_mount(container, Static(Panel(
                        combined_body,
                        title=card_title,
                        border_style=badge_style,
                    )))

                if step.tool_name in ("WRITE_FILE", "EDIT_FILE") and step.result and not (is_err or denied):
                    try:
                        tree = self.query_one("#file-tree", DirectoryTree)
                        tree.reload()
                    except Exception:
                        pass
                    self._start_ast_indexing()
                    self.update_sidebar_meta()

            else:
                # Standalone Reasoning (for non-tool steps)
                if has_thinking:
                    escaped_thinking = escape(trimmed_thinking)
                    step_title = f"💭 Step {step.step_number} Reasoning" if getattr(step, "step_number", None) else "💭 Reasoning"
                    if Collapsible is not None:
                        self._safe_mount(container, Collapsible(
                            Static(escaped_thinking, classes="stream-text"),
                            title=step_title,
                            collapsed=True
                        ))
                    else:
                        self._safe_mount(container, Static(Panel(
                            escaped_thinking,
                            title=step_title,
                            border_style="dim magenta",
                        )))

                # Code execution
                if step.action == "code":
                    display_content = step.content
                    if len(display_content) > 10000:
                        display_content = display_content[:10000] + "\n\n... [Output Truncated for UI Performance]"
                    self._safe_mount(container, Static(Panel(
                        Syntax(display_content, "python", theme="monokai", line_numbers=True),
                        title="⚡ Code Execution",
                        border_style="cyan",
                    )))
                    if step.result:
                        display_result = step.result
                        if len(display_result) > 10000:
                            display_result = display_result[:10000] + "\n... [Truncated]"
                        style = "red" if step.result.startswith("ERROR") else "green"
                        self._safe_mount(container, Static(Panel(
                            Text(display_result),
                            title="📤 Output",
                            border_style=style,
                        )))

                # Final answer
                elif step.action == "final_answer":
                    display_content = step.content
                    if len(display_content) > 15000:
                        display_content = display_content[:15000] + "\n\n... [Output Truncated for UI Performance]"
                    try:
                        content = Markdown(display_content)
                    except Exception:
                        content = Text(display_content)
                    self._safe_mount(container, Static(Panel(
                        content,
                        title="✅ Final Answer",
                        border_style="bold green",
                    )))
                    self._chat_history.append({"role": "assistant", "content": step.content})

                # Sub-queries
                elif step.action == "sub_queries":
                    display_content = step.content
                    if len(display_content) > 10000:
                        display_content = display_content[:10000] + "\n... [Truncated]"
                    self._safe_mount(container, Static(Panel(
                        escape(display_content),
                        title="🔄 Sub-Queries",
                        border_style="yellow",
                    )))
                    if step.result and step.result != "DEPTH LIMIT REACHED":
                        self._safe_mount(container, Static(Panel(
                            escape(step.result[:2000]),
                            title="📥 Sub-Query Results",
                            border_style="dim green",
                        )))
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
            self.notify("Chat transcript copied to clipboard", severity="information", timeout=2)
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
            self.notify("Last response copied to clipboard", severity="information", timeout=2)
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
                self.notify("Selected text copied to clipboard", severity="information", timeout=2)
            else:
                self.notify("Failed to copy selection", severity="error", timeout=3)
            return

        # 2. If no text highlighted on screen, present turn selection modal
        def _on_turn_selected(content: Optional[str]):
            if content:
                if copy_to_clipboard(content):
                    self.notify("Turn copied to clipboard", severity="information", timeout=2)
                else:
                    self.notify("Failed to copy turn", severity="error", timeout=3)

    def action_select_mode(self) -> None:
        def _on_mode_selected(selected_mode: Optional[str]):
            if selected_mode:
                mem = getattr(self.engine, "memory", None)
                from core.memory.models import ExecutionMode
                new_mode = ExecutionMode.GOAL if selected_mode == "goal" else ExecutionMode.CHAT
                if mem and hasattr(mem, "state") and hasattr(mem.state, "execution_mode"):
                    mem.state.execution_mode = new_mode
                
                if selected_mode == "goal":
                    try:
                        from core.execution.autonomous_harness import AutonomousHarness
                        harness = AutonomousHarness(project_root=self.engine.project_root, memory=mem)
                        harness.ensure_goal_spec_initialized()
                    except Exception:
                        pass
                    self.notify("Switched to Goal Mode (Task Graph in .torchlight/tasks.md)", severity="success", timeout=3)
                else:
                    self.notify("Switched to Chat Mode (Lightweight Q&A)", severity="information", timeout=3)
                self.update_status_bar()

        mem = getattr(self.engine, "memory", None)
        current_m = getattr(getattr(mem, "state", None), "execution_mode", "chat")
        m_str = current_m.value if hasattr(current_m, "value") else str(current_m or "chat")
        self.push_screen(SessionModePickerModal(m_str), _on_mode_selected)


    def action_select_model(self) -> None:
        def _on_model_picked(selected: Optional[dict]):
            if selected:
                new_model = selected["id"]
                new_provider = selected["provider"]
                self.notify(f"Switching to {selected['name']}...", severity="information", timeout=3)

                # 1. Kill old server processes
                try:
                    subprocess.run(["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL)
                    subprocess.run(["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL)
                except Exception:
                    pass

                # 2. Update model and provider names
                self.model_name = new_model
                self.provider_name = selected["name"]

                # 3. Re-instantiate engine client
                if new_provider in ("llama-cpp", "turbo", "turboquant"):
                    from rlm_optimized.llamacpp_client import LlamaCppClient
                    self.engine.client = LlamaCppClient(base_url="http://localhost:8080/v1", model=new_model)
                elif new_provider == "mlx":
                    from rlm_optimized.cloud_client import CloudClient
                    self.engine.client = CloudClient(provider="mlx", model=new_model, base_url="http://localhost:8080/v1", api_key="not-needed")
                elif new_provider == "ollama":
                    from rlm_optimized.ollama_client import OllamaClient
                    self.engine.client = OllamaClient(model=new_model)
                elif new_provider == "lmstudio":
                    from rlm_optimized.cloud_client import CloudClient
                    self.engine.client = CloudClient(provider=None, model=new_model, base_url=LMSTUDIO_BASE_URL, api_key=LMSTUDIO_API_KEY)
                else:
                    from rlm_optimized.cloud_client import CloudClient
                    self.engine.client = CloudClient(provider=new_provider, model=new_model)

                # 4. Update tracked port / management mode for the new provider
                self.engine_port, self.externally_managed = _provider_runtime_info(new_provider)

                # 5. Launch new background server if local
                if new_provider in ("llama-cpp", "turbo", "turboquant", "mlx"):
                    self.on_start_engine_btn()

                self.notify(f"Switched to {selected['name']}", severity="information", timeout=2)
                self.update_status_bar()
                self.update_sidebar_meta()

        self.push_screen(ModelPickerModal(), _on_model_picked)

    def action_open_folder(self) -> None:
        def _on_folder_picked(path: Optional[str]):
            if path and os.path.exists(path):
                self.engine.set_project_root(path)
                tree = self.query_one("#file-tree", DirectoryTree)
                tree.path = path
                tree.reload()
                self.notify(f"Workspace set to {path}", severity="information", timeout=2)
                self.update_sidebar_meta()
        self.push_screen(FolderPickerModal(initial_path=self.engine.project_root), _on_folder_picked)

    @work(thread=True)
    def _start_ast_indexing(self) -> None:
        """Build the AST knowledge graph for the current project_root in a
        background thread (blocking: walks all files + runs embeddings)."""
        container = self.query_one("#chat-container")
        target = self.engine.project_root
        
        def mount_static(msg: str):
            container.mount(Static(msg))
            
        self.call_from_thread(
            mount_static,
            f"  [bold yellow]🧠 Indexing AST knowledge graph for {target} ... this may take a while.[/]"
        )
        try:
            from rlm_optimized.ast_indexer import index_directory
            index_directory(target)
            self.call_from_thread(
                mount_static,
                f"  [bold green]✓ AST knowledge graph indexed for {target}[/]"
            )
        except ImportError as e:
            self.call_from_thread(
                mount_static,
                f"  [bold red]✗ Missing dependency for indexing: {e}. Run `pip install kuzu sentence-transformers`.[/]"
            )
        except Exception as e:
            self.call_from_thread(
                mount_static,
                f"  [bold red]✗ Indexing failed:[/] {escape(str(e))}"
            )

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
                        f"  [bold green]Connected to {self.provider_name} ({self.model_name}) on port {port}[/]\n"
                    )
                self.notify(f"Engine server active on port {port}", severity="information", timeout=2)
                return

        self._server_starting = False
        self._last_server_online = False
        self.update_status_bar()
        self.update_sidebar_meta()
        self.notify(f"Engine server failed to bind to port {port} within 15 seconds", severity="error", timeout=5)

    @on(Button.Pressed, "#start-engine-btn")
    def on_start_engine_btn(self) -> None:
        container = self.query_one("#chat-container")

        if self.engine_port <= 0:
            self.notify(f"{self.provider_name} is a cloud provider, nothing to start locally", severity="information", timeout=2)
            self.update_status_bar()
            self.update_sidebar_meta()
            return

        if is_port_in_use(self.engine_port):
            self._server_starting = False
            self.notify(f"Engine server already active on port {self.engine_port}", severity="information", timeout=2)
            self.update_status_bar()
            self.update_sidebar_meta()
            return

        if self.externally_managed:
            self.notify(f"{self.provider_name} offline on port {self.engine_port}. Start it yourself, then retry.", severity="warning", timeout=5)
            self.update_status_bar()
            self.update_sidebar_meta()
            return

        self._server_starting = True
        self.notify(f"Launching local engine on port {self.engine_port}...", severity="information", timeout=3)
        if hasattr(self, "_conn_banner_widget") and self._conn_banner_widget:
            self._conn_banner_widget.update(f"  [bold yellow]Starting local engine server ({self.model_name})...[/]\n")
        self.update_status_bar()
        self.update_sidebar_meta()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        provider_str = getattr(self, "provider_name", "").lower()
        script_name = "start_mlx_server.sh" if "mlx" in provider_str else "start_optimized_local.sh"
        target_script = os.path.join(script_dir, script_name)

        if not os.path.exists(target_script):
            target_script = os.path.abspath(os.path.join(self.engine.project_root, "rlm_optimized", script_name))

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
                    start_new_session=True
                )
                self._poll_server_launch()
            except Exception as e:
                self._server_starting = False
                self.notify(f"Failed to launch server: {escape(str(e))}", severity="error", timeout=5)
                self.update_status_bar()
                self.update_sidebar_meta()
        else:
            self._server_starting = False
            self.notify(f"Server launch script not found: {target_script}", severity="error", timeout=5)
            self.update_status_bar()
            self.update_sidebar_meta()

    @on(Button.Pressed, "#stop-engine-btn")
    def on_stop_engine_btn(self) -> None:
        if self.externally_managed:
            self.notify(f"{self.provider_name} is managed externally, stop it from its own app", severity="information", timeout=3)
            return
        try:
            subprocess.run(["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL)
            self.notify("Engine server stopped", severity="warning", timeout=2)
        except Exception as e:
            self.notify(f"Failed to stop server: {escape(str(e))}", severity="error", timeout=5)

    @on(Button.Pressed, "#restart-engine-btn")
    def on_restart_engine_btn(self) -> None:
        if self.externally_managed:
            self.notify(f"Re-checking connection to {self.provider_name}...", severity="information", timeout=2)
            self.update_status_bar()
            self.update_sidebar_meta()
            return

        self.notify("Restarting with defaults (gemma 4 E2B + TurboQuant)...", severity="information", timeout=3)

        # 1. Reset defaults to gemma 4 E2B and TurboQuant
        self.model_name = "gemma-4-E2B-it"
        self.provider_name = "llama.cpp + TurboQuant (3-bit/4-bit KV)"
        self.engine_port, self.externally_managed = _provider_runtime_info("turbo")
        from rlm_optimized.llamacpp_client import LlamaCppClient
        self.engine.client = LlamaCppClient(base_url="http://localhost:8080/v1", model=self.model_name)

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
        return await self.push_screen_wait(
            ApprovalModal(tool_name, risk, args)
        )

    # ── Actions ─────────────────────────────────────────────────────────

    def update_status_bar(self) -> None:
        try:
            sl = self.query_one("#status-left")
            sr = self.query_one("#status-right")
            state_badges = {
                "IDLE": "[bold green]IDLE[/]",
                "THINKING": "[bold magenta]THINKING...[/]",
                "CRITIQUING": "[bold yellow]🔍 CRITIQUING...[/]",
                "REFINED": "[bold green]✨ REFINED[/]",
                "TOOL": "[bold cyan]EXECUTING TOOL[/]",
                "TOOL_DONE": "[bold green]TOOL DONE[/]",
                "TOOL_DENIED": "[bold red]TOOL DENIED[/]",
                "WAITING_APPROVAL": "[bold yellow]WAITING APPROVAL[/]",
                "SUBAGENT": "[bold purple]SUBAGENT[/]",
            }
            badge = state_badges.get(getattr(self, "_agent_state", "IDLE"), f"[bold cyan]{getattr(self, '_agent_state', 'IDLE')}[/]")
            if self.engine_port <= 0:
                srv_badge = "[bold green]CLOUD[/]"
            else:
                server_online = is_port_in_use(self.engine_port)
                srv_badge = (
                    f"[bold green]ON:{self.engine_port}[/]" if server_online
                    else f"[bold red]OFF:{self.engine_port}[/]"
                )
            sl.update(f" {badge} | {srv_badge}")
            sr.update(
                f"[bold cyan]{escape(self.model_name)}[/] | "
                f"[dim]{CTX_SIZE:,} ctx[/] | "
                f"[yellow]{escape(os.path.basename(self.engine.project_root))}[/] "
            )
        except Exception:
            pass

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
                tree = self.query_one("#file-tree", DirectoryTree)
                tree.path = chosen_dir
                self.notify(f"Working directory set to {escape(str(chosen_dir))}", severity="information", timeout=2)

        self.push_screen(FolderPickerModal(self.engine.project_root), _on_picker_result)

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        self._show_sidebar = not self._show_sidebar
        sidebar.display = self._show_sidebar

    def action_cycle_theme(self) -> None:
        themes = ["torchlight", "textual-dark", "textual-light", "nord", "gruvbox", "solarized-light", "solarized-dark"]
        idx = themes.index(self.theme) if self.theme in themes else 0
        self.theme = themes[(idx + 1) % len(themes)]
        self.notify(f"Theme: {self.theme}", severity="information", timeout=2)

    def action_reset_session(self) -> None:
        self.engine.sandbox.reset()
        self.notify("Python REPL state reset", severity="information", timeout=2)

    def action_clear(self) -> None:
        container = self.query_one("#chat-container")
        container.remove_children()

    def action_compact_context(self) -> None:
        """Manually trigger memory context compaction."""
        mem = getattr(self.engine, "_memory", None)
        if not mem:
            self.notify("No active memory context to compact", severity="warning", timeout=3)
            return
        tb, ta, tf = self.engine.compact_context(mem, force=True)
        self.update_status_bar()
        self.update_sidebar_meta()
        if tf > 0:
            self.notify(f"Context compacted: {tb:,} → {ta:,} tokens ({tf:,} tokens freed)", severity="information", timeout=4)
        else:
            self.notify(f"Context already minimal ({ta:,} tokens)", severity="information", timeout=3)


def create_client(args):
    provider = args.provider
    raw_model = args.model if args.model != MODEL_NAME else MODEL_NAME
    model = normalize_model_name(raw_model, provider=provider)

    if provider in ("llama-cpp", "turbo", "turboquant"):
        from rlm_optimized.llamacpp_client import LlamaCppClient
        base_url = args.base_url or "http://localhost:8080/v1"
        return LlamaCppClient(base_url=base_url, model=model), model, "llama.cpp + TurboQuant (3-bit/4-bit KV)"
    elif provider == "ollama":
        from rlm_optimized.ollama_client import OllamaClient
        return OllamaClient(model=model), model, "Ollama (local)"
    elif provider == "mlx":
        from rlm_optimized.cloud_client import CloudClient
        base_url = args.base_url or "http://localhost:8080/v1"
        client = CloudClient(provider="mlx", model=model, base_url=base_url, api_key=args.api_key or "not-needed")
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
        client = CloudClient(provider=None, model=chosen_model, base_url=base_url, api_key=args.api_key or LMSTUDIO_API_KEY)
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
    parser.add_argument("--provider", type=str, default=None,
                        choices=["ollama", "turbo", "turboquant", "llama-cpp", "mlx", "lmstudio", "groq", "together", "openrouter", "openai", "gemini", "cloud"])
    parser.add_argument("--depth", type=int, default=MAX_RECURSION_DEPTH)
    parser.add_argument("--workdir", "-w", type=str, default=None, help="Set initial working directory")
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
    app = TorchlightApp(engine, model_name, provider_name, engine_port=engine_port, externally_managed=externally_managed)
    app.run()


if __name__ == "__main__":
    main()