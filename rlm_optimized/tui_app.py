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
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
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
from rlm_optimized.tui_panes.editor_manager import EditorManagerMixin
from rlm_optimized.tui_panes.inspector_manager import InspectorManagerMixin
from rlm_optimized.tui_panes.chat_stream_manager import ChatStreamManagerMixin
from rlm_optimized.tui_panes.engine_lifecycle_manager import EngineLifecycleMixin
from rlm_optimized.tui_panes.action_manager import ActionManagerMixin
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


from textual.theme import Theme

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
)

_MATRIX_PHOSPHOR_THEME = Theme(
    name="matrix-phosphor",
    primary="#00ff66",
    accent="#00cc55",
    foreground="#00ff66",
    background="#0d1117",
    surface="#002200",
    panel="#003300",
    success="#00ff66",
    warning="#ffcc00",
    error="#ff3333",
    dark=True,
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
)

from rlm_optimized.tui_widgets.editor_pane import EditorTab, PaneResizer
from rlm_optimized.tui_widgets.modals import (
    AgentMemoryWidget,
    AgentStatusModal,
    ApprovalModal,
    AskUserModal,
    CopySelectionModal,
    EngineConfigModal,
    FileActionModal,
    FolderPickerModal,
    SessionModePickerModal,
    ShortcutsHelpModal,
    SkillUploadModal,
    TaskManagerModal,
)


class TorchlightApp(
    EditorManagerMixin,
    InspectorManagerMixin,
    ChatStreamManagerMixin,
    EngineLifecycleMixin,
    ActionManagerMixin,
    App,
):
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

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _register_mixin_handlers_and_bindings(cls)

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
                        mode_opts = self._get_mode_select_options()
                        initial_mode = self._get_current_mode_val()
                        self._user_input = PromptTextArea(
                            id="user-input",
                            language=None,
                            show_line_numbers=False,
                            soft_wrap=True,
                            tab_behavior="indent",
                            suggestion_callback=self._on_suggestion_matches,
                        )
                        self._user_input.set_mode_placeholder(initial_mode)
                        yield self._user_input
                        with Horizontal(id="input-toolbar"):
                            with Horizontal(id="toolbar-left-controls"):
                                yield Button(
                                    "+",
                                    id="attach-context-btn",
                                    tooltip="Attach Context (Ctrl+U)",
                                )
                                yield Select(
                                    mode_opts,
                                    value=initial_mode,
                                    allow_blank=False,
                                    id="mode-select-dropdown",
                                    tooltip="Select Execution Mode (Unified / Goal / Chat) — Cycle with Shift+Tab",
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

        if hasattr(inp, "record_history"):
            inp.record_history(user_text)
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
        is_conn = getattr(self, "_model_connected", False) or self._is_model_connected()
        if is_conn:
            self._model_connected = True
        else:
            selected = self.model_name
            try:
                dropdown = self.query_one("#model-select-dropdown", Select)
                if dropdown.value:
                    selected = str(dropdown.value)
            except Exception:
                pass
            if not selected or selected == "local-model":
                self.action_select_model()
                return
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
        is_conn = getattr(self, "_model_connected", False) or self._is_model_connected()
        if is_conn:
            self._model_connected = True
        else:
            selected = self.model_name
            try:
                dropdown = self.query_one("#model-select-dropdown", Select)
                if dropdown.value:
                    selected = str(dropdown.value)
            except Exception:
                pass
            if not selected or selected == "local-model":
                self.action_select_model()
                return
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


def _register_mixin_handlers_and_bindings(cls: type) -> None:
    """Collect and register all @on message handlers and BINDINGS from mixins in MRO."""
    handlers = dict(getattr(cls, "_decorated_handlers", {}))
    for base in cls.__mro__:
        for name, value in base.__dict__.items():
            if callable(value) and hasattr(value, "_textual_on"):
                textual_on = getattr(value, "_textual_on")
                for message_type, selectors in textual_on:
                    handlers.setdefault(message_type, [])
                    if not any(h[0] == value for h in handlers[message_type]):
                        handlers[message_type].append((value, selectors))
    cls._decorated_handlers = handlers

    all_bindings = list(getattr(cls, "BINDINGS", []))
    for base in cls.__mro__:
        if base is not cls and hasattr(base, "BINDINGS"):
            base_bindings = getattr(base, "BINDINGS")
            if isinstance(base_bindings, (list, tuple)):
                for b in base_bindings:
                    if b not in all_bindings:
                        all_bindings.append(b)
    cls.BINDINGS = all_bindings
    if hasattr(cls, "_merge_bindings"):
        cls._merged_bindings = cls._merge_bindings()


_register_mixin_handlers_and_bindings(TorchlightApp)


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
