"""File and Directory Interaction Modals for Torchlight TUI.

Provides:
  - FolderPickerModal: Visual computer-wide directory picker with quick jump bookmarks.
  - CopySelectionModal: Interactive dialog to select and copy specific conversation turns.
  - FileActionModal: Context menu modal for opening in editor / system app / copying path.
"""

from __future__ import annotations

import os
from typing import Optional, Union

from rich.markup import escape
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Input, Label, Static


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
