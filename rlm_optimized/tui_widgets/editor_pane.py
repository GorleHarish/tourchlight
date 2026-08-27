"""Editor Pane and Resizer Widgets for Torchlight TUI.

Provides:
  - PaneResizer: Interactive splitter bar to resize adjacent left/right side panes.
  - EditorTab: Tab widget for multi-file code editing/viewing with active/dirty states.
"""

from __future__ import annotations

from textual import events
from textual.message import Message
from textual.widgets import Static

from core.utils.image_utils import is_image_file


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
        self.target_pane = target_pane  # "left", "editor", or "right"
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
