"""Slash command parsing and execution service for Torchlight TUI."""

from __future__ import annotations

from typing import Any, Callable, Coroutine, Optional, Union


class SlashCommandDispatcher:
    """Registry and dispatcher for interactive user slash commands in TUI."""

    def __init__(self, app: Any):
        self.app = app

    async def dispatch(self, cmd_text: str) -> bool:
        """Parse and execute a slash command. Returns True if handled, False otherwise."""
        trimmed = cmd_text.strip()
        if not trimmed.startswith("/"):
            return False

        parts = trimmed.split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/help":
            await self._cmd_help()
            return True
        elif cmd in ("/paste", "/paste-image", "/pasteimage"):
            self.app.action_paste_image()
            return True
        elif cmd == "/image":
            await self._cmd_image(arg)
            return True
        elif cmd == "/start":
            self.app._start_engine(force_restart=False)
            return True
        elif cmd == "/stop":
            self.app.on_stop_engine_btn()
            return True
        elif cmd == "/restart":
            self.app.on_restart_engine_btn()
            return True
        elif cmd == "/kill":
            self.app.on_kill_session_btn()
            return True
        elif cmd == "/cd":
            self._cmd_cd(arg)
            return True
        elif cmd == "/model":
            self._cmd_model(arg)
            return True
        elif cmd == "/models":
            self.app.action_select_model()
            return True
        elif cmd == "/index":
            self.app._start_ast_indexing()
            return True
        elif cmd in ("/clear", "/reset"):
            self.app.action_clear()
            return True
        elif cmd == "/status":
            self.app.action_toggle_status_modal()
            return True
        elif cmd in ("/new", "/wipe"):
            self.app.action_wipe_session()
            return True
        elif cmd in ("/compact", "/compress"):
            self.app.action_compact_context()
            return True
        elif cmd == "/mode":
            self._cmd_mode(arg)
            return True
        elif cmd in ("/breakdown", "/tokens"):
            self.app.on_toggle_breakdown_btn()
            return True
        else:
            return False

    async def _cmd_help(self) -> None:
        from rich.markdown import Markdown
        from rich.panel import Panel
        from textual.widgets import Static

        container = self.app.query_one("#chat-container")
        help_md = """### Commands
- `/image <path> [prompt]` -- Inspect image with vision LLM
- `/paste` -- Paste image from clipboard into chat context
- `/start` / `/restart` / `/stop` -- Engine server control
- `/kill` -- Kill session & reset REPL
- `/cd <path>` -- Change working directory
- `/model <name>` -- Switch model
- `/models` -- Open visual model picker
- `/mode [code|plan|chat|goal|unified]` -- Switch execution mode
- `/breakdown` -- Toggle live token breakdown HUD
- `/index` -- Build AST knowledge graph
- `/clear` -- Clear chat
- `/compact` -- Manually compact context memory
- `/status` -- Open telemetry modal
- `/help` -- Show shortcuts guide
"""
        container.mount(
            Static(Panel(Markdown(help_md), title="Help", border_style="yellow"))
        )
        self.app._scroll_chat_to_end()

    async def _cmd_image(self, arg: str) -> None:
        import os
        from rich.markup import escape
        from rich.panel import Panel
        from textual.widgets import Static
        from core.utils.image_utils import get_image_metadata
        from rlm_optimized.tui_widgets.transcript import MessageCard

        container = self.app.query_one("#chat-container")
        if not arg:
            self.app.notify(
                "Usage: /image <path/to/image.png> [optional instruction]",
                severity="warning",
                timeout=4,
            )
            return

        arg_parts = arg.split(maxsplit=1)
        img_path = arg_parts[0].strip()
        prompt_text = (
            arg_parts[1].strip()
            if len(arg_parts) > 1
            else f"Inspect and analyze image: {img_path}"
        )

        full_p = (
            os.path.join(self.app.project_root, img_path)
            if not os.path.isabs(img_path)
            else img_path
        )
        if not os.path.exists(full_p):
            self.app.notify(
                f"Image not found: {img_path}", severity="error", timeout=4
            )
            return

        meta = get_image_metadata(full_p, project_root=self.app.project_root)
        dim_str = f"{meta['width']}x{meta['height']}" if meta.get("width") else "dynamic"
        self.app.notify(
            f"[IMG] Attached {img_path} ({dim_str}, {meta.get('size_kb')} KB)",
            severity="information",
            timeout=3,
        )
        task_text = f"{prompt_text} @{img_path}"
        self.app._chat_history.append({"role": "user", "content": task_text})
        if hasattr(container, "append_card"):
            container.append_card(
                MessageCard(
                    task_text,
                    role="user",
                    images=[full_p],
                    project_root=self.app.project_root,
                )
            )
        else:
            self.app._safe_mount(
                container,
                Static(
                    Panel(
                        escape(task_text),
                        title="You",
                        border_style="bright_blue",
                    )
                ),
            )
        self.app._scroll_chat_to_end()
        self.app._run_agent(task_text, images=[full_p])

    def _cmd_cd(self, arg: str) -> None:
        import os
        from rich.markup import escape

        if not arg:
            self.app.notify("Usage: /cd <directory_path>", severity="warning", timeout=3)
            return
        target = os.path.abspath(os.path.expanduser(arg))
        if not os.path.isdir(target):
            self.app.notify(f"Directory not found: {escape(target)}", severity="error", timeout=3)
            return
        os.chdir(target)
        if hasattr(self.app, "engine"):
            self.app.engine.project_root = target
        self.app._refresh_git_tree()
        self.app.update_status_bar()
        self.app.update_sidebar_meta()
        self.app.notify(f"Changed directory to {escape(target)}", severity="information", timeout=2)

    def _cmd_model(self, arg: str) -> None:
        from rich.markup import escape
        from rlm_optimized.config import normalize_model_name

        if not arg:
            self.app.notify("Usage: /model <model_name>", severity="warning", timeout=3)
            return
        norm_name = normalize_model_name(arg)
        self.app._load_selected_model(norm_name)
        self.app.notify(f"Switched model to {escape(norm_name)}", severity="information", timeout=2)

    def _cmd_mode(self, arg: str) -> None:
        from rich.markup import escape

        valid_modes = ["code", "plan", "chat", "goal", "unified"]
        if not arg:
            curr = self.app._get_current_mode_val() if hasattr(self.app, "_get_current_mode_val") else "unified"
            self.app.notify(f"Current mode: [bold]{curr}[/]. Usage: /mode [code|plan|chat|goal|unified]", severity="information", timeout=4)
            return
        target_mode = arg.lower()
        if target_mode not in valid_modes:
            self.app.notify(f"Invalid mode '{escape(target_mode)}'. Options: {', '.join(valid_modes)}", severity="error", timeout=3)
            return
        self.app.set_mode(target_mode)
