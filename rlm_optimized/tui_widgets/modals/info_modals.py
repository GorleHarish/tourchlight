"""Informational and Telemetry Modals for Torchlight TUI.

Provides:
  - AgentMemoryWidget: Live L0 Agent Brain Scratchpad view with scrollbars.
  - SkillUploadModal: Skill discovery and workspace installer dialog.
  - AgentStatusModal: Real-time agent action log and telemetry inspector.
  - TaskManagerModal: Interactive task tree and status manager.
  - ShortcutsHelpModal: Keyboard shortcuts and slash command guide.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional, Union

from rich.markdown import Markdown
from rich.markup import escape
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Input, Label, Static

from rlm_optimized.tui_widgets.format import (
    build_agent_memory_scratchpad_text,
)


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
