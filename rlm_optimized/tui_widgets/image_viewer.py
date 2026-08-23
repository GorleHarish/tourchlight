"""
ImageViewer and BinaryFileViewer widgets for the Torchlight TUI.

Provides rich, non-gibberish terminal rendering of images (PNG, JPG, WEBP, GIF, SVG, etc.)
and binary files in the editor split pane, complete with metadata headers, 24-bit ANSI
half-block color previews, SVG source toggles, and system application launching.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional

from rich.markup import escape
from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Static


def open_file_in_system_app(file_path: str) -> bool:
    """Open a file with the operating system default application."""
    if not file_path:
        return False
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        return False
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", abs_path])
        elif sys.platform == "win32":
            os.startfile(abs_path)
        else:
            subprocess.Popen(["xdg-open", abs_path])
        return True
    except Exception:
        return False




class ImageViewer(VerticalScroll):
    """Rich image viewer widget for terminal editor split pane."""

    DEFAULT_CSS = """
    ImageViewer {
        height: 100%;
        width: 100%;
        background: $background;
        padding: 1;
        overflow-y: auto;
        overflow-x: auto;
    }

    .image-viewer-header-card {
        height: auto;
        width: 100%;
        background: $surface;
        border: solid $panel;
        padding: 1;
        margin-bottom: 1;
    }

    .image-viewer-title {
        color: $text;
        text-style: bold;
        margin-bottom: 0;
    }

    .image-viewer-meta {
        color: $foreground-muted;
        margin-top: 0;
    }

    .image-viewer-actions {
        height: auto;
        width: 100%;
        margin-top: 1;
        align: left middle;
    }

    .iv-action-btn {
        height: 3;
        min-height: 3;
        max-height: 3;
        margin-right: 1;
        margin-bottom: 1;
        background: $panel;
        color: $text;
        border: none;
        padding: 0 1;
        text-align: center;
    }

    .iv-action-btn:hover {
        background: $primary;
        color: $background;
        text-style: bold;
    }

    .image-preview-container {
        height: auto;
        width: 100%;
        min-height: 12;
        background: $surface;
        border: solid $panel;
        align: center middle;
        padding: 1;
    }

    .image-preview-render {
        width: auto;
        height: auto;
        content-align: center middle;
    }

    .image-fallback-box {
        width: 100%;
        height: auto;
        padding: 2;
        text-align: center;
        content-align: center middle;
        color: $foreground-muted;
    }

    .svg-source-view {
        width: 100%;
        height: auto;
        background: $background;
    }
    """

    def __init__(
        self,
        image_path: str,
        project_root: str = ".",
        classes: Optional[str] = None,
        id: Optional[str] = None,
    ) -> None:
        super().__init__(classes=classes, id=id)
        self._image_path = image_path
        self._project_root = project_root
        self._show_svg = False

    @property
    def full_path(self) -> str:
        p = self._image_path
        if not os.path.isabs(p):
            return os.path.join(self._project_root, p)
        return p

    def compose(self) -> ComposeResult:
        from core.utils.image_utils import (
            generate_ansi_image_preview,
            get_image_metadata,
        )

        full_p = self.full_path
        filename = os.path.basename(full_p)
        meta = (
            get_image_metadata(full_p, project_root=self._project_root)
            if os.path.exists(full_p)
            else {}
        )

        w = meta.get("width", 0)
        h = meta.get("height", 0)
        fmt = meta.get("format", "IMG")
        size_kb = meta.get("size_kb", 0)
        mime = meta.get("mime_type", "image/png")
        dim_str = f"{w} × {h} px" if w > 0 and h > 0 else "Vector / Scalable"

        is_svg = full_p.lower().endswith(".svg")

        with Vertical(classes="image-viewer-header-card"):
            yield Static(
                f"[bold cyan]🖼 {escape(filename)}[/bold cyan]",
                classes="image-viewer-title",
            )
            yield Static(
                f"[dim]{fmt} · {dim_str} · {size_kb} KB · {mime}\n{escape(full_p)}[/dim]",
                classes="image-viewer-meta",
            )

            with Horizontal(classes="image-viewer-actions"):
                yield Button(
                    "🚀 Open System App", id="iv-btn-system", classes="iv-action-btn"
                )
                yield Button(
                    "🔍 Vision (/image)", id="iv-btn-inspect", classes="iv-action-btn"
                )
                yield Button(
                    "📋 Copy Path", id="iv-btn-copy", classes="iv-action-btn"
                )
                if is_svg:
                    toggle_label = "📄 View XML" if not self._show_svg else "🖼 Preview"
                    yield Button(
                        toggle_label,
                        id="iv-btn-toggle-svg",
                        classes="iv-action-btn",
                    )

        with Container(classes="image-preview-container", id="iv-preview-box"):
            if is_svg and self._show_svg:
                try:
                    with open(full_p, "r", encoding="utf-8", errors="replace") as f:
                        svg_content = f.read()
                    from rich.syntax import Syntax

                    yield Static(
                        Syntax(svg_content, "xml", line_numbers=True, theme="monokai"),
                        classes="svg-source-view",
                    )
                except Exception as e:
                    yield Static(
                        f"[red]Error reading SVG: {escape(str(e))}[/red]",
                        classes="image-fallback-box",
                    )
            else:
                preview = generate_ansi_image_preview(
                    full_p, max_width=68, max_height=20, project_root=self._project_root
                )
                if preview:
                    yield Static(preview, classes="image-preview-render")
                else:
                    yield Static(
                        f"[bold yellow]Image Asset: {escape(filename)}[/bold yellow]\n\n"
                        f"[dim]Format: {fmt} ({dim_str}, {size_kb} KB)\n\n"
                        f"Terminal direct pixel preview is not supported for this format without Pillow.\n"
                        f"Click [bold]'Open System App'[/bold] above to view in high resolution.[/dim]",
                        classes="image-fallback-box",
                    )

    @on(Button.Pressed, "#iv-btn-system")
    def _on_system_open(self, event: Button.Pressed) -> None:
        event.stop()
        filename = os.path.basename(self.full_path)
        if open_file_in_system_app(self.full_path):
            self.notify(f"🚀 Opened {filename} with default app", timeout=2)
        else:
            self.notify(f"Could not open {filename}", severity="error", timeout=3)


    @on(Button.Pressed, "#iv-btn-inspect")
    def _on_inspect(self, event: Button.Pressed) -> None:
        event.stop()
        if self.app:
            try:
                user_input = getattr(self.app, "_user_input", None)
                if user_input is None:
                    user_input = self.app.query_one("#user-input")
                if user_input is not None:
                    cmd_text = f"/image {self.full_path} Analyze this image in detail"
                    if hasattr(user_input, "text"):
                        user_input.text = cmd_text
                    elif hasattr(user_input, "value"):
                        user_input.value = cmd_text
                    user_input.focus()
                    self.notify("Loaded /image command into prompt", timeout=2)
            except Exception:
                pass

    @on(Button.Pressed, "#iv-btn-copy")
    def _on_copy_path(self, event: Button.Pressed) -> None:
        event.stop()
        filename = os.path.basename(self.full_path)
        try:
            from rlm_optimized.tui_app import copy_to_clipboard

            if copy_to_clipboard(self.full_path):
                self.notify(f"📋 Copied path: {filename}", timeout=2)
            else:
                self.notify(f"Path: {self.full_path}", timeout=4)
        except Exception:
            self.notify(f"Path: {self.full_path}", timeout=4)

    @on(Button.Pressed, "#iv-btn-toggle-svg")
    def _on_toggle_svg(self, event: Button.Pressed) -> None:
        event.stop()
        self._show_svg = not self._show_svg
        self.refresh(recompose=True)


class BinaryFileViewer(VerticalScroll):
    """Viewer for non-image binary files in editor pane."""

    DEFAULT_CSS = """
    BinaryFileViewer {
        height: 100%;
        width: 100%;
        background: $background;
        padding: 1;
        overflow-y: auto;
    }

    .binary-viewer-card {
        height: auto;
        width: 100%;
        background: $surface;
        border: solid $panel;
        padding: 2;
        text-align: center;
        align: center middle;
    }

    .binary-viewer-title {
        color: $text;
        text-style: bold;
        margin-bottom: 1;
    }

    .binary-viewer-desc {
        color: $foreground-muted;
        margin-bottom: 2;
        text-align: center;
    }

    .binary-viewer-actions {
        height: auto;
        width: auto;
        align: center middle;
    }
    """

    def __init__(
        self,
        file_path: str,
        classes: Optional[str] = None,
        id: Optional[str] = None,
    ) -> None:
        super().__init__(classes=classes, id=id)
        self._file_path = os.path.abspath(file_path)

    def compose(self) -> ComposeResult:
        filename = os.path.basename(self._file_path)
        file_size = 0
        if os.path.exists(self._file_path):
            file_size = os.path.getsize(self._file_path)

        size_str = (
            f"{file_size / (1024 * 1024):.2f} MB"
            if file_size >= 1024 * 1024
            else f"{file_size / 1024:.1f} KB"
        )

        with Vertical(classes="binary-viewer-card"):
            yield Static(
                f"[bold yellow]📁 {escape(filename)}[/bold yellow]",
                classes="binary-viewer-title",
            )
            yield Static(
                f"[dim]Binary File · {size_str}\n{escape(self._file_path)}\n\n"
                f"Raw binary data cannot be displayed as text.\n"
                f"Use the buttons below to open with the default system application.[/dim]",
                classes="binary-viewer-desc",
            )
            with Horizontal(classes="binary-viewer-actions"):
                yield Button(
                    "🚀 Open System App", id="bin-btn-system", classes="iv-action-btn"
                )
                yield Button(
                    "📋 Copy Path", id="bin-btn-copy", classes="iv-action-btn"
                )

    @on(Button.Pressed, "#bin-btn-system")
    def _on_system_open(self, event: Button.Pressed) -> None:
        event.stop()
        filename = os.path.basename(self._file_path)
        if open_file_in_system_app(self._file_path):
            self.notify(f"🚀 Opened {filename} with default app", timeout=2)
        else:
            self.notify(f"Could not open {filename}", severity="error", timeout=3)

    @on(Button.Pressed, "#bin-btn-copy")
    def _on_copy_path(self, event: Button.Pressed) -> None:
        event.stop()
        filename = os.path.basename(self._file_path)
        try:
            from rlm_optimized.tui_app import copy_to_clipboard

            if copy_to_clipboard(self._file_path):
                self.notify(f"📋 Copied path: {filename}", timeout=2)
            else:
                self.notify(f"Path: {self._file_path}", timeout=4)
        except Exception:
            self.notify(f"Path: {self._file_path}", timeout=4)
