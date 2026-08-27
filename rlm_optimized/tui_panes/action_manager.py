"""Command palette actions, context chips, layout resizing, theme switching, and session resets."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Optional

from textual import events, on
from textual.containers import Container, Horizontal
from rich.markup import escape
from textual.widgets import Button, Static

from core.utils.image_utils import save_clipboard_image
from rlm_optimized.utils import save_last_state
from rlm_optimized.tui_widgets.transcript import TranscriptView
from rlm_optimized.tui_widgets.command_palette import (
    AttachContextModal,
    CommandPalette,
    PaletteResult,
)
from rlm_optimized.tui_widgets.modals import AgentMemoryWidget, AgentStatusModal, FolderPickerModal


class ActionManagerMixin:
    """Mixin providing keyboard shortcut actions, pane resizing, context chips, and session controls."""

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
