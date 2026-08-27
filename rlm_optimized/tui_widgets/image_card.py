"""Image attachment preview card widget for the Torchlight TUI."""

from __future__ import annotations

import os
from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static


class ImageAttachmentCard(Container):
    """Visual card displaying image metadata and a 24-bit ANSI terminal color preview."""

    DEFAULT_CSS = """
    ImageAttachmentCard {
        height: auto;
        margin: 1 0;
        padding: 0;
        border: solid $panel;
        border-left: solid $accent;
        background: $background;
    }

    ImageAttachmentCard > Horizontal.image-card-header {
        height: 1;
        align: left middle;
        padding: 0 1;
        background: $panel;
        border-bottom: solid $panel;
    }

    Static.image-card-title {
        width: 1fr;
        color: $text;
        text-style: bold;
    }

    Static.image-card-meta {
        width: auto;
        color: $foreground-muted;
    }

    Static.image-card-btn {
        width: auto;
        min-width: 3;
        color: $text-muted;
        background: $surface;
        margin: 0 0 0 1;
        padding: 0 1;
        text-align: center;
    }

    Static.image-card-btn:hover {
        background: $accent;
        color: $background;
        text-style: bold;
    }

    .image-preview-box {
        height: auto;
        padding: 1;
        align: center middle;
        background: $background;
    }
    """

    def __init__(
        self,
        image_path: str,
        project_root: str = ".",
        classes: str | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(classes=classes, id=id)
        self._image_path = image_path
        self._project_root = project_root

    @property
    def full_path(self) -> str:
        p = self._image_path
        if not os.path.isabs(p):
            return os.path.join(self._project_root, p)
        return p

    def compose(self) -> ComposeResult:
        from core.utils.image_utils import (
            get_image_metadata,
            generate_ansi_image_preview,
        )

        p = self._image_path
        full_p = self.full_path

        meta = (
            get_image_metadata(full_p, project_root=self._project_root)
            if os.path.exists(full_p)
            else {}
        )
        w = meta.get("width")
        h = meta.get("height")
        dim_str = (
            f"{w}x{h} {meta.get('format', 'IMG')}"
            if w and h
            else meta.get("format", "IMG")
        )
        size_str = f"{meta.get('size_kb', 0)} KB"

        with Horizontal(classes="image-card-header"):
            yield Static(f"[IMG] {os.path.basename(p)}", classes="image-card-title")
            yield Static(f"{dim_str} · {size_str}", classes="image-card-meta")
            open_btn = Static("🚀", classes="image-card-btn image-card-open", markup=False)
            open_btn.tooltip = "Open with default system application"
            yield open_btn
            tab_btn = Static("👁", classes="image-card-btn image-card-tab", markup=False)
            tab_btn.tooltip = "Open in Editor Split View"
            yield tab_btn
            copy_btn = Static("❐", classes="image-card-btn image-card-copy", markup=False)
            copy_btn.tooltip = "Copy image path"
            yield copy_btn

        # Generate 24-bit ANSI terminal color preview
        preview_text = generate_ansi_image_preview(
            full_p, max_width=44, max_height=14, project_root=self._project_root
        )
        if preview_text:
            yield Static(preview_text, classes="image-preview-box")
        else:
            yield Static(f"[dim]Attached Image: {p}[/dim]", classes="image-preview-box")

    @on(events.Click, ".image-card-open")
    def on_open_click(self, event: events.Click) -> None:
        event.stop()
        self.action_open_system()

    @on(events.Click, ".image-card-copy")
    def on_copy_click(self, event: events.Click) -> None:
        event.stop()
        self.action_copy_path()

    @on(events.Click, ".image-card-tab")
    def on_tab_click(self, event: events.Click) -> None:
        event.stop()
        self.action_open_tab()

    @on(events.Click, ".image-card-title")
    def on_title_click(self, event: events.Click) -> None:
        event.stop()
        self.action_open_tab()

    def action_open_system(self) -> None:
        from rlm_optimized.tui_widgets.image_viewer import open_file_in_system_app

        full_p = self.full_path
        filename = os.path.basename(full_p)
        if open_file_in_system_app(full_p):
            self.notify(f"🚀 Opened {filename} with default app", timeout=2)
        else:
            self.notify(f"Could not open {filename}", severity="error", timeout=3)

    def action_copy_path(self) -> None:
        full_p = self.full_path
        filename = os.path.basename(full_p)
        try:
            from rlm_optimized.tui_app import copy_to_clipboard

            if copy_to_clipboard(full_p):
                self.notify(f"📋 Copied path: {filename}", timeout=2)
            else:
                self.notify(f"Path: {full_p}", timeout=4)
        except Exception:
            self.notify(f"Path: {full_p}", timeout=4)

    def action_open_tab(self) -> None:
        if self.app and hasattr(self.app, "open_file_tab"):
            self.app.open_file_tab(self.full_path)
            self.notify(f"Opened {os.path.basename(self.full_path)} in editor", timeout=1.5)
