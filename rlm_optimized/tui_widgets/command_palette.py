"""Command palette + slash-command autocomplete for the Torchlight TUI.

Phase 4:
* ``CommandPalette`` — a ``Ctrl+P`` modal that fuzzy-searches app bindings,
  slash commands, and project files (Enter runs, Esc closes).
* ``PromptTextArea`` — a ``TextArea`` subclass that turns Enter into a submit
  (the stock widget consumes Enter to insert a newline, so it never reached
  ``App.on_key``) and drives a suggestion ``ListView`` below the input as the
  user types ``/command`` or ``@file`` fragments (Enter/Tab accept, Esc
  dismisses).

The fuzzy matcher and item builders are pure helpers (no Textual imports) so
they are trivially unit-testable. All layout uses DEFAULT_CSS + theme vars.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar, NamedTuple, Optional

from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static, TextArea

from rlm_optimized.tui_widgets.file_tree import _should_skip_dir


def slash_command_list() -> list[tuple[str, str, str]]:
    """(command, usage, description) triples mirrored from ``_handle_slash_command``."""
    return [
        ("/help", "/help", "Show shortcuts & command cheat sheet"),
        ("/image", "/image <path> [prompt]", "Attach image for vision model inspection"),
        ("/paste", "/paste", "Paste image from clipboard into chat context"),
        ("/start", "/start", "Start the engine server"),
        ("/restart", "/restart", "Restart the engine server"),
        ("/stop", "/stop", "Stop the engine server"),
        ("/kill", "/kill", "Kill session & reset REPL"),
        ("/cd", "/cd <path>", "Change working directory"),
        ("/model", "/model <name>", "Switch active model"),
        ("/index", "/index", "Build AST knowledge graph"),
        ("/status", "/status", "Open telemetry modal"),
        ("/mode", "/mode [chat|goal]", "Switch session mode"),
        ("/phase", "/phase [code|plan|debug|chat|auto]", "Lock profile/phase mode"),
        ("/engine", "/engine", "Open model/provider picker"),
        ("/speculative", "/speculative [draft_model]", "Configure speculative draft model (⚡ acceleration)"),
        ("/draft", "/draft [model]", "Switch speculative draft model"),
        ("/select", "/select", "Copy selection"),
        ("/copy", "/copy", "Copy entire chat history"),
        ("/copylast", "/copylast", "Copy last response"),
        ("/compact", "/compact", "Manually compact context memory"),
        ("/compress", "/compress", "Manually compact context memory"),
        ("/wipe", "/wipe", "Completely wipe session context & start fresh"),
        ("/new", "/new", "Wipe session context & start new session"),
        ("/clear", "/clear", "Clear chat & wipe session context"),
        ("/reset", "/reset", "Reset session context and Python sandbox"),
    ]


def _fuzzy_score(query: str, label: str) -> int:
    """Rank ``query`` against ``label``; 0 means no match.

    Prefix matches beat substring matches, which beat loose subsequence
    matches; shorter labels win within a tier.
    """
    if not query:
        return 1
    if label.startswith(query):
        return 10000 - len(label)
    pos = label.find(query)
    if pos >= 0:
        return 5000 - pos - len(label)
    it = iter(label)
    if all(ch in it for ch in query):
        return 1000 - len(label)
    return 0


def fuzzy_filter(
    query: str, items: list[tuple[str, str, str, str]]
) -> list[tuple[str, str, str, str]]:
    """Filter ``(label, detail, kind, value)`` items by fuzzy score, best first."""
    q = query.strip().lower()
    scored: list[tuple[int, tuple[str, str, str, str]]] = []
    for item in items:
        score = _fuzzy_score(q, item[0].lower())
        if score:
            scored.append((score, item))
    scored.sort(key=lambda t: (-t[0], t[1][0].lower()))
    return [item for _, item in scored]


def iter_project_files(root: str | Path, max_files: int = 200) -> list[str]:
    """Relative path strings under ``root``, dot/vendor dirs excluded, capped."""
    result: list[str] = []
    root_path = Path(root)
    try:
        for dirpath, dirnames, filenames in os.walk(root_path):
            dirnames[:] = sorted(d for d in dirnames if not _should_skip_dir(d))
            for fname in sorted(filenames):
                rel = os.path.relpath(os.path.join(dirpath, fname), root_path)
                result.append(rel)
                if len(result) >= max_files:
                    return result
    except OSError:
        pass
    return result


def match_prompt_suggestions(
    text: str,
    slash_commands: list[tuple[str, str, str]],
    file_paths: list[str],
    max_results: int = 8,
) -> list[str]:
    """Suggest completions for a single-token ``/cmd`` or ``@file`` prefix."""
    if not text or " " in text:
        return []
    if text.startswith("/"):
        return [
            cmd
            for cmd, _usage, _desc in slash_commands
            if cmd.startswith(text) and cmd != text
        ][:max_results]
    if text.startswith("@"):
        q = text[1:].lower()
        return [
            f"@{p}" for p in file_paths if p.lower().startswith(q) and p.lower() != q
        ][:max_results]
    return []


def build_palette_items(
    bindings: list[Binding],
    slash_commands: list[tuple[str, str, str]],
    files: list[str],
) -> list[tuple[str, str, str, str]]:
    """Build ``(label, detail, kind, value)`` entries for the palette."""
    items: list[tuple[str, str, str, str]] = []
    for b in bindings:
        if not getattr(b, "show", True):
            continue
        items.append(
            (
                f"{b.key}  {b.description}",
                f"action · {b.action}",
                "action",
                b.action,
            )
        )
    for cmd, usage, desc in slash_commands:
        items.append((usage, desc, "slash", cmd))
    for rel in files:
        items.append((f"@ {rel}", "open file", "file", rel))
    return items


MODE_PLACEHOLDERS: dict[str, str] = {
    "chat": "Ask anything about the codebase... (@file to attach, /help)",
    "plan": "Describe feature or architecture to plan... (@file to attach, /help)",
    "code": "Describe code to implement or debug... (@file to attach, /help)",
    "goal": "Define a high-level goal to execute autonomously... (@file to attach, /help)",
    "unified": "Ask a question, plan a feature, or describe code changes... (@file, /help)",
}


class PromptTextArea(TextArea):
    """TextArea whose Enter submits instead of inserting a newline.

    Hooks ``update_suggestion()`` (fired after every edit) to compute slash /
    ``@file`` completions and push them through ``suggestion_callback`` so the
    app can render a ``ListView`` beneath the input. Enter/Tab accept the top
    suggestion when visible, otherwise Enter posts ``SubmitRequested``.
    """

    class SubmitRequested(Message):
        """Posted when the user presses Enter with no active suggestion."""

        def __init__(self, text_area: "PromptTextArea") -> None:
            super().__init__()
            self.text_area = text_area

        @property
        def control(self) -> "PromptTextArea | None":
            return self.text_area

    class ContextFileAttached(Message):
        """Posted when the user accepts an @file suggestion."""

        def __init__(self, text_area: "PromptTextArea", filepath: str) -> None:
            super().__init__()
            self.text_area = text_area
            self.filepath = filepath

    def __init__(
        self,
        *,
        slash_commands: list[tuple[str, str, str]] | None = None,
        file_paths: list[str] | None = None,
        suggestion_callback: Callable[[list[str]], None] | None = None,
        highlight_callback: Callable[[int], None] | None = None,
        placeholder: str | None = None,
        **kwargs,
    ) -> None:
        if placeholder is None:
            placeholder = MODE_PLACEHOLDERS["unified"]
        super().__init__(placeholder=placeholder, **kwargs)
        self._slash_commands = slash_commands or slash_command_list()
        self._file_paths = file_paths or []
        self._suggestion_callback = suggestion_callback
        self._highlight_callback = highlight_callback
        self._matches: list[str] = []
        self.highlight_index = 0
        self._history: list[str] = []
        self._history_index = -1
        self._temp_draft = ""

    def set_mode_placeholder(self, mode: str) -> None:
        """Update placeholder text based on the active execution mode."""
        m = (mode or "unified").lower().strip()
        self.placeholder = MODE_PLACEHOLDERS.get(m, MODE_PLACEHOLDERS["unified"])

    def record_history(self, text: str) -> None:
        """Record submitted prompt in session history."""
        clean = (text or "").strip()
        if clean and (not self._history or self._history[-1] != clean):
            self._history.append(clean)
        self._history_index = -1
        self._temp_draft = ""

    @property
    def suggestions_visible(self) -> bool:
        return bool(self._matches)

    @property
    def matches(self) -> list[str]:
        return list(self._matches)

    def update_suggestion(self) -> None:
        self._matches = match_prompt_suggestions(
            self.text, self._slash_commands, self._file_paths
        )
        self.highlight_index = 0
        if self._suggestion_callback:
            self._suggestion_callback(self._matches)

    def set_highlight(self, index: int) -> None:
        if not self._matches:
            self.highlight_index = 0
            return
        self.highlight_index = max(0, min(index, len(self._matches) - 1))
        if self._highlight_callback:
            self._highlight_callback(self.highlight_index)

    def _notify_highlight(self) -> None:
        if self._highlight_callback:
            self._highlight_callback(self.highlight_index)

    def accept_suggestion(self) -> None:
        if not self._matches:
            return
        match = self._matches[min(self.highlight_index, len(self._matches) - 1)]
        if match.startswith("@"):
            filepath = match[1:].strip()
            if " " in self.text:
                head, _sep, _tail = self.text.rpartition(" ")
                self.load_text(f"{head} ")
            else:
                self.load_text("")
            self.move_cursor(self.document.end)
            self.post_message(self.ContextFileAttached(self, filepath))
        else:
            if " " in self.text:
                head, _sep, _tail = self.text.rpartition(" ")
                self.load_text(f"{head} {match}")
            else:
                self.load_text(match)
            self.move_cursor(self.document.end)
        self._matches = []
        self.highlight_index = 0
        if self._suggestion_callback:
            self._suggestion_callback([])

    def dismiss_suggestion(self) -> None:
        self._matches = []
        self.highlight_index = 0
        if self._suggestion_callback:
            self._suggestion_callback([])

    def _get_project_root(self) -> str:
        if self.app and hasattr(self.app, "project_root"):
            return str(self.app.project_root)
        if self.app and hasattr(self.app, "engine") and hasattr(self.app.engine, "project_root"):
            return str(self.app.engine.project_root)
        return "."

    def on_paste(self, event: events.Paste) -> None:
        text = (event.text or "").strip()
        clean = text.strip("'\"")
        if clean.startswith("file://"):
            clean = clean[7:]
        from core.utils.image_utils import is_image_file, save_clipboard_image
        if clean and is_image_file(clean):
            event.stop()
            event.prevent_default()
            self.post_message(self.ContextFileAttached(self, clean))
            return

        # Check if system clipboard has an image
        root = self._get_project_root()
        saved_p = save_clipboard_image(root)
        if saved_p:
            event.stop()
            event.prevent_default()
            self.post_message(self.ContextFileAttached(self, saved_p))
            return

    async def _on_key(self, event) -> None:
        key = event.key

        if key in ("ctrl+v", "cmd+v", "ctrl+shift+v"):
            from core.utils.image_utils import save_clipboard_image

            root = self._get_project_root()
            saved_p = save_clipboard_image(root)
            if saved_p:
                event.stop()
                event.prevent_default()
                self.post_message(self.ContextFileAttached(self, saved_p))
                return

        # Shift+Tab or Ctrl+M: Instant in-place mode cycling
        if key in ("shift+tab", "ctrl+m"):
            event.stop()
            event.prevent_default()
            if self.app and hasattr(self.app, "set_mode") and hasattr(self.app, "_get_current_mode_val"):
                modes = ["unified", "chat", "plan", "code", "goal"]
                curr = str(self.app._get_current_mode_val()).lower().strip()
                idx = (modes.index(curr) + 1) % len(modes) if curr in modes else 0
                next_mode = modes[idx]
                self.app.set_mode(next_mode)
                self.set_mode_placeholder(next_mode)
            return

        if key in ("ctrl+s", "alt+enter"):
            event.stop()
            event.prevent_default()
            self.record_history(self.text)
            self.post_message(self.SubmitRequested(self))
            return

        if key == "enter":
            if self._matches:
                event.stop()
                event.prevent_default()
                self.accept_suggestion()
                return
            # Let the default TextArea handle the newline and indentation
            await super()._on_key(event)
            return
        if key == "tab":
            event.stop()
            event.prevent_default()
            if self._matches:
                self.accept_suggestion()
            else:
                await super()._on_key(event)
            return
        if key == "escape":
            event.stop()
            event.prevent_default()
            if self._matches:
                self.dismiss_suggestion()
            else:
                await super()._on_key(event)
            return
        if key == "up":
            if self._matches:
                event.stop()
                event.prevent_default()
                self.set_highlight(self.highlight_index - 1)
                return
            if not self.text.strip() or self._history_index != -1:
                # History recall
                if self._history:
                    if self._history_index == -1:
                        self._temp_draft = self.text
                        self._history_index = len(self._history) - 1
                    elif self._history_index > 0:
                        self._history_index -= 1
                    event.stop()
                    event.prevent_default()
                    self.load_text(self._history[self._history_index])
                    self.move_cursor(self.document.end)
                    return
        if key == "down":
            if self._matches:
                event.stop()
                event.prevent_default()
                self.set_highlight(self.highlight_index + 1)
                return
            if self._history_index != -1:
                event.stop()
                event.prevent_default()
                if self._history_index < len(self._history) - 1:
                    self._history_index += 1
                    self.load_text(self._history[self._history_index])
                else:
                    self._history_index = -1
                    self.load_text(self._temp_draft)
                self.move_cursor(self.document.end)
                return
        await super()._on_key(event)


class PaletteResult(NamedTuple):
    kind: str
    value: str
    label: str
    detail: str = ""


class CommandPalette(ModalScreen[Optional[PaletteResult]]):  # noqa: UP045 - 3.9 runtime base
    """Ctrl+P modal: fuzzy-search actions, slash commands, and files."""

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("escape", "cancel", "Cancel"),
        ("enter", "select", "Run"),
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("home", "scroll_home", "Top"),
        ("end", "scroll_end", "Bottom"),
    ]

    DEFAULT_CSS = """
    CommandPalette {
        align: center middle;
    }
    #palette-dialog {
        width: 70;
        max-width: 92%;
        height: auto;
        max-height: 60%;
        background: $surface;
        border: heavy $primary;
        padding: 1 2;
    }
    #palette-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    #palette-input {
        border: tall $panel;
        background: $background;
        color: $foreground;
    }
    #palette-input:focus {
        border: tall $accent;
    }
    #palette-list {
        height: auto;
        max-height: 20;
        background: $background;
        margin-top: 1;
        border: solid $panel;
    }
    #palette-hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        project_root: str | Path,
        bindings: list[Binding] | None = None,
    ) -> None:
        super().__init__()
        files = iter_project_files(project_root)
        self._all_items = build_palette_items(
            bindings or [], slash_command_list(), files
        )
        self._filtered = self._all_items
        self._index = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-dialog"):
            yield Label("⌨️ Command Palette", id="palette-title")
            yield Input(
                placeholder="Type a command, shortcut, or file name…",
                id="palette-input",
            )
            yield ListView(id="palette-list")
            yield Static(
                f"[dim]{len(self._all_items)} items · ↑/↓ navigate · Enter run · Esc close[/]",
                id="palette-hint",
            )

    def on_mount(self) -> None:
        self._refresh("")
        try:
            self.set_focus(self.query_one("#palette-input", Input))
        except Exception:  # noqa: BLE001, S110
            pass

    @on(Input.Changed, "#palette-input")
    def on_palette_input(self, event: Input.Changed) -> None:
        self._refresh(event.value)

    @on(Input.Submitted, "#palette-input")
    def on_palette_submit(self, event: Input.Submitted) -> None:
        self.action_select()

    @on(ListView.Selected, "#palette-list")
    def on_palette_selected(self, event: ListView.Selected) -> None:
        if event.index is not None:
            self._index = event.index
        self.action_select()

    def _refresh(self, query: str) -> None:
        self._filtered = fuzzy_filter(query, self._all_items)
        lv = self.query_one("#palette-list", ListView)
        lv.clear()
        for label, _detail, _kind, _value in self._filtered:
            lv.append(ListItem(Label(label)))
        self._index = 0
        if self._filtered:
            lv.index = 0

    def _sync_index(self) -> None:
        try:
            lv = self.query_one("#palette-list", ListView)
            lv.index = self._index
        except Exception:  # noqa: BLE001, S110
            pass

    @on(ListView.Highlighted, "#palette-list")
    def on_highlighted(self, event: ListView.Highlighted) -> None:
        idx = event.list_view.index
        if idx is not None:
            self._index = idx

    def action_cursor_up(self) -> None:
        if not self._filtered:
            return
        self._index = (self._index - 1) % len(self._filtered)
        self._sync_index()

    def action_cursor_down(self) -> None:
        if not self._filtered:
            return
        self._index = (self._index + 1) % len(self._filtered)
        self._sync_index()

    def action_scroll_home(self) -> None:
        if not self._filtered:
            return
        self._index = 0
        self._sync_index()

    def action_scroll_end(self) -> None:
        if not self._filtered:
            return
        self._index = len(self._filtered) - 1
        self._sync_index()

    def action_select(self) -> None:
        if not self._filtered:
            return
        idx = min(self._index, len(self._filtered) - 1)
        label, detail, kind, value = self._filtered[idx]
        self.dismiss(PaletteResult(kind=kind, value=value, label=label, detail=detail))

    def action_cancel(self) -> None:
        self.dismiss(None)

class AttachContextModal(ModalScreen[Optional[str]]):
    """Ctrl+O modal: fuzzy-search files to attach to the prompt."""

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("escape", "cancel", "Cancel"),
        ("enter", "select", "Attach"),
        ("ctrl+v", "paste_image", "Paste Image"),
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("home", "scroll_home", "Top"),
        ("end", "scroll_end", "Bottom"),
    ]

    DEFAULT_CSS = CommandPalette.DEFAULT_CSS

    def __init__(
        self,
        project_root: str | Path,
    ) -> None:
        super().__init__()
        self._project_root = str(project_root)
        files = iter_project_files(project_root)
        self._all_items = [(f, "", "file", f) for f in files]
        self._filtered = self._all_items
        self._index = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-dialog"):
            yield Label("📎 Attach Context", id="palette-title")
            yield Input(
                placeholder="Fuzzy-search file to attach…",
                id="palette-input",
            )
            yield ListView(id="palette-list")
            yield Static(
                f"[dim]{len(self._all_items)} files · ↑/↓ navigate · Enter attach · Esc close[/]",
                id="palette-hint",
            )

    def on_mount(self) -> None:
        self._refresh("")
        try:
            self.set_focus(self.query_one("#palette-input", Input))
        except Exception:  # noqa: BLE001, S110
            pass

    @on(Input.Changed, "#palette-input")
    def on_palette_input(self, event: Input.Changed) -> None:
        self._refresh(event.value)

    @on(Input.Submitted, "#palette-input")
    def on_palette_submit(self, event: Input.Submitted) -> None:
        self.action_select()

    @on(ListView.Selected, "#palette-list")
    def on_palette_selected(self, event: ListView.Selected) -> None:
        if event.index is not None:
            self._index = event.index
        self.action_select()

    def _refresh(self, query: str) -> None:
        self._filtered = fuzzy_filter(query, self._all_items)
        lv = self.query_one("#palette-list", ListView)
        lv.clear()
        for label, _detail, _kind, _value in self._filtered:
            lv.append(ListItem(Label(label)))
        self._index = 0
        if self._filtered:
            lv.index = 0

    def _sync_index(self) -> None:
        try:
            lv = self.query_one("#palette-list", ListView)
            lv.index = self._index
        except Exception:  # noqa: BLE001, S110
            pass

    @on(ListView.Highlighted, "#palette-list")
    def on_highlighted(self, event: ListView.Highlighted) -> None:
        idx = event.list_view.index
        if idx is not None:
            self._index = idx

    def action_cursor_up(self) -> None:
        if not self._filtered:
            return
        self._index = (self._index - 1) % len(self._filtered)
        self._sync_index()

    def action_cursor_down(self) -> None:
        if not self._filtered:
            return
        self._index = (self._index + 1) % len(self._filtered)
        self._sync_index()

    def action_scroll_home(self) -> None:
        if not self._filtered:
            return
        self._index = 0
        self._sync_index()

    def action_scroll_end(self) -> None:
        if not self._filtered:
            return
        self._index = len(self._filtered) - 1
        self._sync_index()

    def action_select(self) -> None:
        if not self._filtered:
            return
        idx = min(self._index, len(self._filtered) - 1)
        _, _, _, value = self._filtered[idx]
        self.dismiss(value)

    def action_paste_image(self) -> None:
        from core.utils.image_utils import save_clipboard_image

        saved_p = save_clipboard_image(self._project_root)
        if saved_p:
            self.dismiss(saved_p)
        elif self.app:
            self.app.notify("No image found on clipboard.", severity="warning", timeout=2)

    def action_cancel(self) -> None:
        self.dismiss(None)
