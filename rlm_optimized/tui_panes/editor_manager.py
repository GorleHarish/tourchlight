"""Editor tab manager, split pane viewers, and file interaction mixin."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from rich.markup import escape
from rich.syntax import Syntax
from textual import events, on
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DirectoryTree, Label, Markdown, OptionList, Static, Tree

from core.utils.image_utils import is_image_file
from rlm_optimized.tui_widgets.center_empty_state import (
    CenterEmptyState,
    STATE_DISCONNECTED,
    STATE_IDLE,
    STATE_WORKING,
)
from rlm_optimized.tui_widgets.diff_view import DiffView
from rlm_optimized.tui_widgets.editor_pane import EditorTab
from rlm_optimized.tui_widgets.file_tree import GitFileTree
from rlm_optimized.tui_widgets.image_viewer import BinaryFileViewer, ImageViewer
from rlm_optimized.tui_widgets.modals import FileActionModal
from rlm_optimized.utils import copy_to_clipboard


class EditorManagerMixin:
    """Mixin providing tabbed editor management, syntax rendering, and file action menus."""

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
