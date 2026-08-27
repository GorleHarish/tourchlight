"""CLI interactive slash commands, parameters configuration, and help display."""

from __future__ import annotations

import os
from typing import Optional
from rich.console import Console

from core.api.base import InferenceParams, PRESETS
from core.prompts.system import get_phase_system_prompt, sanitize_assistant_text
from context_manager.cli.dashboard import ContextDashboard, ActionTracker

try:
    from core.memory.models import ExecutionMode
except ImportError:
    from ...memory.models import ExecutionMode


console = Console()
dashboard = ContextDashboard()


class CommandDispatcherMixin:
    """Provides slash command handling and CLI help formatting for StreamingChatSession."""

    async def _handle_command(self, cmd: str):
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if command == "/help":
            self._print_help()
        elif command == "/status":
            dashboard.show_snapshot(self.memory.get_snapshot())
        elif command == "/stream":
            self.stream_enabled = not self.stream_enabled
            dashboard.print_info(f"Streaming {'enabled' if self.stream_enabled else 'disabled'}")
        elif command in ("/compress", "/compact"):
            tb, ta, tf = await self._compress_context(force=True)
            dashboard.print_success(
                f"Context manually compressed: {tb:,} → {ta:,} tokens ({tf:,} tokens freed)"
            )
        elif command in ("/clear", "/reset", "/new", "/wipe"):
            self.memory.clear()
            dashboard.print_success("Session context wiped — all memory cleared")
        elif command == "/tokens":
            dashboard.print_info(
                f"Current tokens: {self.memory.total_tokens:,} / {self.max_tokens:,}"
            )
        elif command in ("/quit", "/exit"):
            raise KeyboardInterrupt
        elif command in ("/paste", "/paste-image"):
            from core.utils.image_utils import save_clipboard_image
            saved_p = save_clipboard_image(self.project_root)
            if not saved_p:
                dashboard.print_warning("No image found on clipboard.")
            else:
                rel_p = os.path.relpath(saved_p, self.project_root)
                arg = f"{rel_p} {arg}".strip()
                command = "/image"
        if command == "/image":
            if not arg.strip():
                dashboard.print_warning("Usage: /image <path/to/image.png> [optional question/instruction]")
            else:
                arg_parts = arg.strip().split(maxsplit=1)
                img_path = arg_parts[0]
                img_prompt = arg_parts[1] if len(arg_parts) > 1 else f"Inspect and analyze image: {img_path}"
                from core.utils.image_utils import is_image_file, get_image_metadata
                full_p = os.path.join(self.project_root, img_path) if not os.path.isabs(img_path) else img_path
                if not os.path.exists(full_p):
                    dashboard.print_error(f"Image not found: {img_path}")
                else:
                    meta = get_image_metadata(full_p, project_root=self.project_root)
                    dashboard.print_info(f"[IMG] Attached image: {img_path} ({meta.get('width')}x{meta.get('height')} {meta.get('format')}, {meta.get('size_kb')} KB)")
                    self.memory.add_user_message(img_prompt, images=[img_path])
                    if getattr(self, "trajectory_lock", None):
                        self.trajectory_lock.reset()
                    self._update_params(img_prompt)
                    tracker = dashboard.action_tracker()
                    with tracker:
                        if self.memory.should_compress():
                            act = tracker.start("compress", "Compressing context...")
                            await self._compress_context()
                            tracker.finish(act)
                        think_act = tracker.start("thinking", "Inspecting image...")
                        try:
                            if self.stream_enabled:
                                response = await self._generate_streaming_response(img_prompt)
                            else:
                                response = await self._generate_response(img_prompt)
                        except RuntimeError as e:
                            tracker.finish(think_act, ok=False)
                            dashboard.print_error(str(e))
                            return
                        tracker.finish(think_act)
                        response = await self._verify_and_refine_if_needed(
                            response, user_task=img_prompt, phase_name=self._current_phase
                        )
                        self.memory.add_assistant_message(response)
                    dashboard.print_response(sanitize_assistant_text(response))
                    dashboard.show_snapshot(self.memory.get_snapshot())
        elif command == "/save":
            from ..memory.persistence import SessionPersistence

            persistence = SessionPersistence()
            name = arg.strip() if arg else None
            path = persistence.save_session(self.memory, session_name=name)
            dashboard.print_success(f"Session saved: {path}")
        elif command in ("/params", "/phase", "/profile"):
            await self._handle_params_command(arg.strip())
        elif command == "/reindex":
            self._rebuild_index()
            dashboard.print_success("Flashlight index rebuilt.")
        elif command == "/beam":
            query = arg.strip() or typer.prompt("Query for beam preview")
            self._flash_preview(query)
        elif command == "/mode":
            mode_arg = arg.strip().lower()
            if mode_arg in ("code", "chat", "goal", "plan", "unified"):
                self.mode = mode_arg
                if hasattr(self.memory.state, "execution_mode"):
                    try:
                        new_mode = ExecutionMode(mode_arg)
                    except ValueError:
                        new_mode = ExecutionMode.UNIFIED
                    self.memory.state.execution_mode = new_mode



                if mode_arg == "code":
                    if not self._params_locked:
                        self._current_phase = "code"
                        self._params = PRESETS["code"]
                        self._phase_lock = "code"
                        self._phase_lock_turns = 0
                    dashboard.print_success(
                        "Switched to Code Mode (Surgical coding & task execution)"
                    )
                elif mode_arg == "goal":
                    # Goal mode is a coding workflow — align with the TUI engine
                    # (goal → code phase) so the full tool whitelist stays available.
                    # Explicit /params locks are left untouched.
                    if not self._params_locked:
                        self._current_phase = "code"
                        self._params = PRESETS["code"]
                        self._phase_lock = "code"
                        self._phase_lock_turns = 0
                    if AutonomousHarness:
                        harness = getattr(self, "harness", None) or AutonomousHarness(
                            project_root=self.project_path,
                            memory=self.memory,
                            llm_engine_step_fn=self._harness_step_fn,
                        )
                        self.harness = harness
                        success = harness.ensure_goal_spec_initialized()
                        if success:
                            dashboard.print_success(
                                "Switched to Goal Mode (Task Graph initialized in .torchlight/tasks.md)"
                            )
                        else:
                            dashboard.print_warning(
                                "Switched to Goal Mode but task graph initialization failed"
                            )
                    else:
                        dashboard.print_success("Switched to Goal Mode (harness unavailable)")
                elif mode_arg == "plan":
                    if not self._params_locked:
                        self._current_phase = "plan"
                        self._params = PRESETS["plan"]
                        self._phase_lock = "plan"
                        self._phase_lock_turns = 0
                    dashboard.print_success(
                        "Switched to Plan Mode (Brainstorm & maintain implementation_plan.md)"
                    )
                elif mode_arg == "unified":
                    self._phase_lock = None
                    self._phase_lock_turns = 0
                    dashboard.print_success("Switched to Unified Mode (Dynamic Phase Auto-Detection)")
                else:
                    if not self._params_locked:
                        self._current_phase = "chat"
                        self._params = PRESETS["chat"]
                        self._phase_lock = "chat"
                        self._phase_lock_turns = 0
                    dashboard.print_success(
                        "Switched to Chat Mode (Lightweight Q&A & ad-hoc code edits)"
                    )

            else:
                current_label = (
                    "💻 Code Mode (Surgical coding & task execution)"
                    if self.mode == "code"
                    else "🎯 Goal Mode (Task tracking in .torchlight/tasks.md)"
                    if self.mode == "goal"
                    else "📋 Plan Mode (Brainstorm & maintain implementation_plan.md)"
                    if self.mode == "plan"
                    else "⚡ Unified Mode (Dynamic Phase Auto-Detection)"
                    if self.mode == "unified"
                    else "💬 Chat Mode (Lightweight Q&A)"
                )
                console.print(f"[bold cyan]Current Mode:[/bold cyan] {current_label}")
                console.print(
                    "[dim]Usage: /mode code  (Code & Tasks) | /mode plan  (Brainstorm & Plan) | /mode chat  (Lightweight Q&A) | /mode goal  (Harness) | /mode unified (Dynamic)[/dim]"
                )


        elif command in ("/tasks", "/goal", "/subagents"):
            if AutonomousHarness:
                harness = getattr(self, "harness", None) or AutonomousHarness(
                    project_root=self.project_path, memory=self.memory
                )
                self.harness = harness
                harness.ensure_goal_spec_initialized()
                summary = harness.get_status_summary()
                dashboard.show_task_progress(summary)
            else:
                dashboard.print_warning("AutonomousHarness is not available.")

        elif command == "/files":
            if self._index is None:
                dashboard.print_warning("Flashlight not initialised.")
            else:
                for rel, entry in sorted(self._index.files.items()):
                    sym_names = ", ".join(s[0] for s in entry.symbols[:5])
                    suffix = f"  [dim]→ {sym_names}[/dim]" if sym_names else ""
                    console.print(f"  [cyan]{rel}[/cyan]  [{entry.size} lines]{suffix}")
        else:
            dashboard.print_warning(f"Unknown command: {command}")

    async def _handle_params_command(self, arg: str) -> None:
        """
        /params                    — show current params
        /params auto               — re-enable auto phase-detection
        /params code|plan|troubleshoot|chat  — lock to a preset
        /params temp=0.2 top_k=30  — set individual values (space-separated key=value)
        """
        import re as _re

        if not arg or arg == "show":
            lock_note = " (locked 🔒)" if self._params_locked else " (auto)"
            console.print(
                f"[bold cyan]Inference params[/bold cyan] — "
                f"phase: [bold]{self._current_phase}[/bold]{lock_note}\n"
                f"  {self._params.describe()}\n"
                f"\n[dim]Presets: code  plan  troubleshoot  chat[/dim]\n"
                f"[dim]Usage:   /params code          — lock to preset[/dim]\n"
                f"[dim]         /params auto          — resume auto-detect[/dim]\n"
                f"[dim]         /params temp=0.2      — set individual field[/dim]"
            )
            return

        if arg == "auto":
            self._params_locked = False
            dashboard.print_success("Auto phase-detection re-enabled.")
            return

        if arg == "debug":
            arg = "troubleshoot"

        # Named preset
        if arg in PRESETS:
            self._params = PRESETS[arg]
            self._current_phase = arg
            self._params_locked = True
            dashboard.print_success(f"Locked to preset '{arg}': {self._params.describe()}")
            return

        # Key=value overrides  e.g.  /params temp=0.15 top_k=25 rep=1.05 repetition_penalty=1.08
        kv_pairs = _re.findall(r"([\w_]+)=([\d.]+)", arg)
        if kv_pairs:
            for key, val in kv_pairs:
                # Normalise aliases
                key = {
                    "temp": "temperature",
                    "rep": "repeat_penalty",
                    "repeat": "repeat_penalty",
                    "repetition": "repeat_penalty",
                    "repetition_penalty": "repeat_penalty",
                    "rep_pen": "repeat_penalty",
                }.get(key.lower(), key)
                if hasattr(self._params, key):
                    field_type = type(getattr(self._params, key))
                    try:
                        setattr(self._params, key, field_type(val))
                        if key in ("repeat_penalty", "repetition_penalty"):
                            self._params.repeat_penalty = float(val)
                            self._params.repetition_penalty = float(val)
                    except (ValueError, TypeError) as e:
                        dashboard.print_warning(f"Bad value for {key}: {e}")
                else:
                    dashboard.print_warning(f"Unknown param: {key}")
            self._params_locked = True
            dashboard.print_success(f"Params updated (locked): {self._params.describe()}")
            return

        dashboard.print_warning(
            f"Unknown /params arg '{arg}'. "
            "Use: auto | code | plan | troubleshoot | chat | key=value (e.g. temp=0.2 rep=1.05)"
        )

    def _print_help(self):
        small = self.max_tokens <= _SMALL_CTX
        mode = (
            f"[yellow]small-ctx ({self.max_tokens} tok)[/yellow]"
            if small
            else f"[green]full ({self.max_tokens} tok)[/green]"
        )
        help_text = f"""
    [bold]Context mode:[/bold] {mode}
    {"[yellow]Skills prompts skipped, beam=1×50L to fit 4k window[/yellow]" if small else ""}

    [bold]Commands:[/bold]
      /help        — this help
      /status      — context statistics
      /tasks       — show sub-agent goal & task progress telemetry
      /image <p>   — attach image file for visual analysis (Gemma 3 / Vision LLMs)
      /paste       — paste image from clipboard into chat context
      /stream      — toggle streaming
      /compress, /compact — compress context manually now
      /clear, /new, /wipe — wipe all context and start fresh
      /tokens      — show token usage
      /save [name] — save session
      /quit        — exit

    [bold]Inference params:[/bold]
      /params                     — show current settings + active phase
      /params code                — lock to coding preset (temp=0.1, top_k=20)
      /params plan                — lock to planning preset (temp=0.4, top_k=40)
      /params troubleshoot        — lock to troubleshoot preset (temp=0.3, top_k=35)
      /params chat                — lock to chat preset (temp=0.7, top_k=50)
      /params auto                — resume auto phase-detection
      /params temp=0.2 top_k=25  — override individual fields (stays locked)

    [bold]Flashlight:[/bold]
      /reindex     — rescan project
      /beam <q>    — preview beam for query
      /files       — list indexed files

    [bold]Approval tiers:[/bold]
      AUTO    — runs immediately (READ_FILE, VIEW_IMAGE, WEB_*, DOC_*, SAVE_MEMORY, safe shell)
      CONFIRM — shows preview, one keypress (WRITE_FILE, pip/npm install, scripts)
      REVIEW  — destructive warning, default=No (rm, git push, git commit, sudo)
    """
        console.print(Panel(help_text, title="Help"))
