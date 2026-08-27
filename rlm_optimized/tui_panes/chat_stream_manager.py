"""Chat stream buffer, token rendering, step dispatch, and copy actions mixin."""

from __future__ import annotations

import asyncio
import os
import re
import time
from typing import Any, Dict, List, Optional

from rich.markup import escape
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from textual import events, on, work
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Collapsible, Markdown, Static, TextArea

from core.prompts.system import sanitize_assistant_text
from core.tools.classification import AUTO, CONFIRM, REVIEW
from rlm_optimized.config import CTX_SIZE, is_port_in_use
from rlm_optimized.rlm_engine_optimized import Step
from rlm_optimized.tui_widgets.center_empty_state import CenterEmptyState
from rlm_optimized.tui_widgets.diff_view import DiffView, build_diff_preview
from rlm_optimized.tui_widgets.modals import AskUserModal, CopySelectionModal
from rlm_optimized.tui_widgets.thinking_block import thinking_block
from rlm_optimized.tui_widgets.tool_card import ToolCallCard
from rlm_optimized.tui_widgets.trajectory_rail import TrajectoryRail
from rlm_optimized.tui_widgets.transcript import (
    MessageCard,
    StreamingView,
    card_meta_for,
    estimate_token_count,
    truncate_output,
)
from rlm_optimized.utils import copy_to_clipboard


class ChatStreamManagerMixin:
    """Mixin providing live token stream rendering, pending tool cards, and chat event dispatch."""

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

    def _safe_mount(self, container, widget) -> None:
        """Mount a widget defensively and scroll safely after layout pass."""
        try:
            if not container.is_attached:
                container = self.query_one("#chat-container")
            if container.is_attached:
                if hasattr(container, "append_card"):
                    container.append_card(widget, scroll=True)
                else:
                    container.mount(widget)
                    if len(container.children) > 35:
                        try:
                            container.children[0].remove()
                        except Exception:
                            pass
                    self.call_after_refresh(self._scroll_chat_to_end)
        except Exception:
            pass

    def _scroll_chat_to_end(self) -> None:
        try:
            container = self.query_one("#chat-container")
            if container.is_attached:
                container.scroll_end(animate=False)
        except Exception:
            pass

    @work(exclusive=True, group="agent")
    async def _run_agent(self, task: str) -> None:
        import time

        self._is_running = True
        self._set_input_enabled(False)
        self._stream_start_time = time.time()
        self._first_token_time = None
        self._stream_token_count = 0
        container = self.query_one("#chat-container")

        self.engine.on_step = self._handle_step
        self.engine.approval_fn = self._handle_approval
        self.engine.ask_user_fn = self._handle_ask_user
        self.engine.on_token = self._append_token
        self.engine.on_status_change = self._handle_status_change
        self.engine.on_tasks_changed = self._handle_tasks_changed
        if getattr(self.engine, "feedback_loop", None):
            self.engine.feedback_loop.set_event_callback(self._handle_test_event)

        # Sync execution_mode from memory state into the engine
        # so solve_async selects the correct system prompt.
        _mem = getattr(self.engine, "memory", None)
        if _mem and hasattr(_mem, "state") and hasattr(_mem.state, "execution_mode"):
            _em = _mem.state.execution_mode
            self.engine.execution_mode = (
                _em.value if hasattr(_em, "value") else str(_em)
            )

        # Register callback to sync engine mode changes back to memory
        def _on_mode_change(new_mode: str):
            if (
                _mem
                and hasattr(_mem, "state")
                and hasattr(_mem.state, "execution_mode")
            ):
                from core.memory.models import ExecutionMode

                try:
                    _mem.state.execution_mode = ExecutionMode(new_mode)
                except ValueError:
                    pass

        self.engine.set_execution_mode_callback(_on_mode_change)

        self._streaming_text = ""
        self._ensure_streaming_widget()

        try:
            try:
                result = await self.engine.solve_async(task)
            except Exception as first_err:
                err_msg = str(first_err).lower()
                port = self.engine_port
                connection_failed = (
                    "connection refused" in err_msg or "connection error" in err_msg
                )
                if connection_failed and port > 0 and self.externally_managed:
                    raise ConnectionError(
                        f"Could not reach {self.provider_name} on port {port}. "
                        f"Make sure it's running (for LM Studio: open the app, load a model, "
                        f"and start its Local Server), then try again."
                    ) from first_err
                if connection_failed and port > 0 and not is_port_in_use(port):
                    self._remove_streaming()
                    self.notify(
                        f"Server refused on port {port}, auto-starting engine...",
                        severity="warning",
                        timeout=3,
                    )
                    self.on_start_engine_btn()

                    # Wait up to 10 seconds for the port to become ready
                    server_ready = False
                    for _ in range(10):
                        await asyncio.sleep(1)
                        if is_port_in_use(port):
                            server_ready = True
                            break

                    if server_ready:
                        self.notify(
                            f"Engine active on port {port}, retrying task...",
                            severity="information",
                            timeout=2,
                        )
                        self._streaming_text = ""
                        self._ensure_streaming_widget()
                        result = await self.engine.solve_async(task)
                    else:
                        raise ConnectionError(
                            f"Could not auto-start local engine server on port {port}. "
                            "Please click Start in sidebar or run ./rlm_optimized/start_optimized_local.sh"
                        ) from first_err
                else:
                    raise first_err

            # If in Goal Mode and tasks remain pending, continuously execute micro-epochs
            if getattr(self.engine, "execution_mode", "unified") == "goal":
                from core.tools.task_helpers import get_workspace_pending_tasks

                max_goal_epochs = 25
                max_attempts_per_task = 3
                epoch_count = 0
                task_attempts: dict[str, int] = {}

                while (
                    not getattr(self, "_is_cancelled", False)
                    and epoch_count < max_goal_epochs
                ):
                    pending_tasks = get_workspace_pending_tasks(
                        self.engine.project_root
                    )
                    if not pending_tasks:
                        break

                    next_task = pending_tasks[0]
                    current_attempt = task_attempts.get(next_task, 0) + 1
                    task_attempts[next_task] = current_attempt
                    epoch_count += 1

                    self._remove_streaming()
                    attempt_suffix = (
                        f" [dim](Attempt {current_attempt}/{max_attempts_per_task})[/]"
                        if current_attempt > 1
                        else ""
                    )
                    container.mount(
                        Static(
                            f"\n  [bold cyan]🎯 Goal Epoch {epoch_count}:[/] [bold white]{escape(next_task)}[/]{attempt_suffix}",
                            classes="step-status",
                        )
                    )
                    self.call_after_refresh(self._scroll_chat_to_end)

                    # Flush conversation turn memory to avoid context overflow while preserving project state
                    if hasattr(self.engine, "_memory") and self.engine._memory:
                        if hasattr(self.engine._memory, "clear"):
                            self.engine._memory.clear()
                    if hasattr(self.engine, "_messages"):
                        self.engine._messages = None

                    self._streaming_text = ""
                    self._ensure_streaming_widget()

                    # List existing workspace files to prevent hallucinating extra folders like src/
                    existing_files = []
                    try:
                        for f in os.listdir(self.engine.project_root):
                            if not f.startswith(".") and not f.startswith("__") and f not in ("node_modules", "venv", ".venv", "graphify-out"):
                                existing_files.append(f)
                    except Exception:
                        pass
                    files_context = (
                        f"\nExisting workspace files: {', '.join(sorted(existing_files))}\n"
                        "Target existing files directly at project root before creating new subdirectories."
                        if existing_files
                        else ""
                    )

                    epoch_prompt = (
                        f"Goal Sub-Task ({epoch_count}): {next_task}\n"
                        f"Execute the required tool calls (READ_FILE, EDIT_FILE, WRITE_FILE, RUN_COMMAND, INSPECT_WEB) "
                        f"to complete this task and verify it.{files_context}"
                    )
                    sub_result = await self.engine.solve_async(epoch_prompt)
                    result.total_llm_calls += sub_result.total_llm_calls
                    result.steps.extend(sub_result.steps)

                    # If the epoch produced successful file modifications and no failing tests, mark subtask completed
                    has_successful_edits = any(
                        s.tool_name in ("WRITE_FILE", "EDIT_FILE")
                        and getattr(s, "result", "")
                        and not str(s.result).startswith("❌")
                        and not str(s.result).startswith("⛔")
                        and not str(s.result).startswith("Edit failed")
                        for s in sub_result.steps
                    )
                    has_failing_tests = bool(
                        getattr(self.engine.feedback_loop, "has_failing_tests", False)
                    )
                    if has_successful_edits and not has_failing_tests:
                        from core.tools.task_helpers import mark_task_status
                        mark_task_status(
                            self.engine.project_root, next_task, status="completed"
                        )
                        self._notify_tasks_changed({"reason": "epoch_completion"})

                    new_pending = get_workspace_pending_tasks(
                        self.engine.project_root
                    )
                    # If the task did not advance after max attempts, break to allow manual inspection
                    if (
                        len(new_pending) >= len(pending_tasks)
                        and new_pending[0] == next_task
                        and task_attempts[next_task] >= max_attempts_per_task
                    ):
                        container.mount(
                            Static(
                                f"  [yellow]⚠ Sub-task stalled after {max_attempts_per_task} attempts: '{escape(next_task)}'[/]",
                                classes="step-status",
                            )
                        )
                        break

                remaining_after_loop = get_workspace_pending_tasks(
                    self.engine.project_root
                )
                if remaining_after_loop and epoch_count >= max_goal_epochs:
                    container.mount(
                        Static(
                            f"\n  [bold yellow]── 🎯 Goal Epoch limit reached ({max_goal_epochs} epochs). {len(remaining_after_loop)} pending task(s) remaining. Submit prompt to continue. ──[/]",
                            classes="step-status",
                        )
                    )

            self._remove_streaming()
            self.update_sidebar_meta()

            container.mount(
                Static(
                    f"  [dim]── ✓ {result.total_llm_calls} LLM call(s), "
                    f"{len(result.steps)} step(s) ──[/]",
                    classes="step-status",
                )
            )
            self.call_after_refresh(self._scroll_chat_to_end)

            # If in Plan Mode and the answer or implementation_plan.md contains open review questions, auto-launch AskUserModal
            current_mode = getattr(self.engine, "execution_mode", "unified")
            if current_mode == "plan" or getattr(self.engine, "_current_phase", "") == "plan":
                try:
                    from core.utils.plan_utils import parse_plan_review_questions

                    plan_text = result.answer or ""
                    plan_file = os.path.join(self.project_root, "implementation_plan.md")
                    if not plan_text and os.path.exists(plan_file):
                        with open(plan_file, "r", encoding="utf-8") as pf:
                            plan_text = pf.read()
                    review_questions = parse_plan_review_questions(plan_text)
                    if review_questions:
                        user_selection = await self.push_screen_wait(
                            AskUserModal(questions=review_questions)
                        )
                        if user_selection and user_selection != "User dismissed prompt without input.":
                            self.notify(
                                f"Review choices recorded: {user_selection[:60]}",
                                severity="information",
                                timeout=4,
                            )
                            try:
                                user_input = self.query_one("#user-input", TextArea)
                                user_input.text = f"Confirmed: {user_selection}. Proceed with implementation."
                            except Exception:
                                pass
                except Exception:
                    pass

        except asyncio.CancelledError:
            self._remove_streaming()
            self._safe_mount(container, Static("[yellow]  ⚠ Agent task cancelled[/]"))
        except Exception as e:
            self._remove_streaming()
            raw_err = str(e)
            if len(raw_err) > 500:
                raw_err = raw_err[:500] + "... [truncated]"
            err_str = escape(raw_err)
            self._safe_mount(container, Static(f"  [bold red]Error:[/] {err_str}"))
        finally:
            self._is_running = False
            self._set_input_enabled(True)
            self._agent_state = "IDLE"
            self._stream_token_count = 0
            self.update_status_bar()
            try:
                self.set_focus(self.query_one("#user-input", TextArea))
            except Exception:
                pass

    # ── Token Streaming ─────────────────────────────────────────────────

    def _ensure_streaming_widget(self) -> StreamingView:
        if getattr(self, "_streaming_widget", None) is None:
            active_phase = getattr(self, "mode", None) or getattr(getattr(self, "engine", None), "_current_phase", "chat")
            self._streaming_view = StreamingView(phase=active_phase)
            if Collapsible is not None:
                self._streaming_widget = Collapsible(
                    self._streaming_view, title="💭 Thinking...", collapsed=False
                )
            else:
                self._streaming_widget = self._streaming_view
            container = self.query_one("#chat-container")
            container.mount(self._streaming_widget)
            self.call_after_refresh(self._scroll_chat_to_end)
        return self._streaming_view

    def _ensure_pending_tool_card(self, tool_name: str, target: str = "") -> None:
        """Mount a running ToolCallCard for a streamed ``<tool_call>`` marker.

        Kept as a single in-flight card: the next tool ``Step`` completes it
        (via ``_handle_step``) instead of stacking "Preparing..." strings.
        """
        if self._pending_tool_card is not None:
            return
        try:
            container = self.query_one("#chat-container")
        except Exception:
            return
        card = ToolCallCard(tool_name, target=target)
        self._pending_tool_card = card
        self._pending_tool_name = tool_name
        if self._trajectory_rail is not None:
            self._trajectory_rail.add_pending(tool_name)
        if hasattr(container, "append_card"):
            container.append_card(card, scroll=True)
        else:
            self._safe_mount(container, card)

    def _append_token(self, chunk: str) -> None:
        import time

        self._streaming_text += chunk
        now = time.time()
        if self._first_token_time is None and self._stream_start_time:
            self._first_token_time = now
            self._live_latency_ms = max(
                1.0, (self._first_token_time - self._stream_start_time) * 1000.0
            )

        self._stream_token_count += max(1, len(chunk) // 3)
        if self._first_token_time and (now - self._first_token_time) > 0.05:
            self._live_tps = self._stream_token_count / (now - self._first_token_time)

        # Keep the status-bar context gauge climbing during generation (throttled to 1.0s)
        try:
            if now - getattr(self, "_last_status_refresh_ts", 0.0) > 1.0:
                self._last_status_refresh_ts = now
                self.call_after_refresh(self.update_status_bar)
        except Exception:
            pass

        # Adaptive throttle interval based on TPS
        throttle_interval = 0.045 if getattr(self, "_live_tps", 0.0) > 60 else getattr(self, "_token_throttle_interval", 0.033)
        throttled = (now - getattr(self, "_token_throttle_last", 0.0)) < throttle_interval

        if throttled:
            if not getattr(self, "_flush_pending", False):
                self._flush_pending = True
                self.call_after_refresh(self._flush_streaming_widget)
            return

        self._flush_pending = False
        self._token_throttle_last = now
        self._render_streaming_update()

    def _render_streaming_update(self) -> None:
        try:
            widget = self._ensure_streaming_widget()
            display_text = self._streaming_text

            if "<tool_call>" in display_text.lower():
                parts = re.split(r"<tool_call>", display_text, flags=re.IGNORECASE)
                display_text = parts[0].strip()
                raw_payload = parts[1] if len(parts) > 1 else ""
                try:
                    name_match = re.search(r'"name"\s*:\s*"([^"]+)"', raw_payload)
                    if name_match:
                        t_name = name_match.group(1)
                        target_match = re.search(
                            r'"(?:path|file|file_path|cmd|command|pattern|query)"\s*:\s*"([^"]+)"',
                            raw_payload,
                        )
                        target_str = target_match.group(1) if target_match else ""
                        self._ensure_pending_tool_card(t_name, target_str)
                except Exception:
                    pass

            display_text = sanitize_assistant_text(display_text)
            if len(display_text) > 4000:
                display_text = "... [truncated streaming] ...\n" + display_text[-4000:]

            escaped = escape(display_text)
            widget.update_markup(escaped)

            meta_parts = []
            if self._live_tps > 0:
                meta_parts.append(f"{self._live_tps:.1f} tps")
            meta_parts.append(f"{self._stream_token_count:,} tok")
            if self._live_latency_ms > 0:
                meta_parts.append(f"{self._live_latency_ms:.0f}ms")
            widget.set_meta(" · ".join(meta_parts))

            if self._pending_tool_card is not None:
                self._pending_tool_card.update_running()
            if not getattr(self, "_scroll_pending", False):
                self._scroll_pending = True
                self.call_after_refresh(self._do_scroll_chat_to_end)
        except Exception:
            pass

    def _do_scroll_chat_to_end(self) -> None:
        self._scroll_pending = False
        self._scroll_chat_to_end()

    def _flush_streaming_widget(self) -> None:
        """Apply any pending streaming text that was throttled."""
        self._flush_pending = False
        if self._streaming_view is None:
            return
        self._render_streaming_update()

    def _remove_streaming(self) -> None:
        self._flush_pending = False
        self._scroll_pending = False
        if getattr(self, "_streaming_widget", None) is not None:
            try:
                self._streaming_widget.remove()
            except Exception:
                pass
            self._streaming_widget = None
            self._streaming_view = None
        self._streaming_text = ""

    # ── Step Display ────────────────────────────────────────────────────

    def _handle_step(self, step: Step) -> None:
        self._remove_streaming()
        try:
            container = self.query_one("#chat-container")
        except Exception:
            container = None

        try:
            has_thinking = bool(
                step.thinking and step.thinking.strip() not in ("(forced)", "")
            )
            trimmed_thinking = ""
            if has_thinking:
                trimmed_thinking = step.thinking.strip()
                if len(trimmed_thinking) > 15000:
                    trimmed_thinking = (
                        trimmed_thinking[:15000] + "\n... [Reasoning Truncated]"
                    )

            # Tool execution - Single Unified Card (with embedded Rationale if present)
            if step.action == "tool":
                label = step.tool_name or "TOOL"
                display_args = (
                    dict(step.tool_args) if isinstance(step.tool_args, dict) else {}
                )

                target_name = ""
                if "path" in display_args:
                    target_name = str(display_args["path"])
                elif "file_path" in display_args:
                    target_name = str(display_args["file_path"])
                elif "command" in display_args:
                    target_name = str(display_args["command"])
                elif "query" in display_args:
                    target_name = str(display_args["query"])

                if label == "WRITE_FILE" and "content" in display_args:
                    display_args["content"] = (
                        f"... [{len(str(display_args['content']))} chars of code hidden]"
                    )
                elif label == "EDIT_FILE":
                    if "old_text" in display_args:
                        display_args["old_text"] = (
                            f"... [{len(str(display_args['old_text']))} chars hidden]"
                        )
                    if "new_text" in display_args:
                        display_args["new_text"] = (
                            f"... [{len(str(display_args['new_text']))} chars hidden]"
                        )

                res_raw = step.result or ""
                denied = "denied" in res_raw.lower()
                is_err = (
                    res_raw.startswith("Error")
                    or res_raw.startswith("❌")
                    or ("requires" in res_raw.lower() and "block" in res_raw.lower())
                    or ("failed" in res_raw.lower() and "error" in res_raw.lower())
                )
                if denied:
                    status = "denied"
                elif is_err:
                    status = "error"
                else:
                    status = "ok"

                # Complete the pending card created while streaming, or mount a
                # fresh completed card (engines that don't stream markers).
                card = None
                if (
                    self._pending_tool_card is not None
                    and getattr(self, "_pending_tool_name", None) == label
                ):
                    card = self._pending_tool_card
                elif self._pending_tool_card is not None:
                    try:
                        self._pending_tool_card.remove()
                    except Exception:
                        pass

                self._pending_tool_card = None
                self._pending_tool_name = None
                if card is None:
                    if self._trajectory_rail is not None:
                        self._trajectory_rail.add_pending(label)
                    try:
                        card = ToolCallCard(
                            label, args=display_args, target=target_name
                        )
                    except Exception:
                        card = None
                    if card is not None:
                        if hasattr(container, "append_card"):
                            container.append_card(card, scroll=True)
                        else:
                            self._safe_mount(container, card)
                if self._trajectory_rail is not None:
                    self._trajectory_rail.complete(status)
                if card is not None:
                    card.complete(
                        result=res_raw,
                        args=display_args,
                        thinking=trimmed_thinking,
                        status=status,
                    )

                # Phase 3: inline diff for successful file writes/edits.
                # Computed client-side from disk — zero LLM context overhead.
                if (
                    step.tool_name in ("WRITE_FILE", "EDIT_FILE", "CODE_FILE_WRITE")
                    and status == "ok"
                    and not is_err
                ):
                    try:
                        step_args = (
                            dict(step.tool_args)
                            if isinstance(step.tool_args, dict)
                            else {}
                        )
                        old_snapshot = None
                        step_path = str(
                            step_args.get("path") or step_args.get("file_path") or ""
                        )
                        if step_path and os.path.isabs(step_path):
                            old_snapshot = self._prewrite_snapshots.pop(step_path, None)
                        preview = build_diff_preview(
                            step.tool_name,
                            step_args,
                            self.engine.project_root,
                            old_text=old_snapshot,
                        )
                        if preview is not None:
                            path, _old, _new, entries = preview
                            if entries:
                                container.append_card(
                                    DiffView(entries, path=path), scroll=True
                                )
                    except Exception:
                        pass

                if (
                    step.tool_name in ("WRITE_FILE", "EDIT_FILE", "CODE_FILE_WRITE")
                    and step.result
                    and not (is_err or denied)
                ):
                    try:
                        self._refresh_git_tree()
                    except Exception:
                        pass
                    try:
                        if self.is_running:
                            self._start_ast_indexing()
                    except Exception:
                        pass
                    try:
                        self.update_sidebar_meta()
                    except Exception:
                        pass
                    try:
                        step_args = (
                            dict(step.tool_args)
                            if isinstance(step.tool_args, dict)
                            else {}
                        )
                        wp = str(
                            step_args.get("path") or step_args.get("file_path") or ""
                        )
                        if wp and os.path.isabs(wp) and wp in self._open_tabs:
                            self._open_tabs[wp]["dirty"] = True
                            self._refresh_editor_split_view()
                    except Exception:
                        pass

            else:
                # Standalone Reasoning (for non-tool steps)
                if has_thinking:
                    raw_check = trimmed_thinking.strip()
                    is_raw_dict = (
                        raw_check.startswith("{") and raw_check.endswith("}")
                    ) or (raw_check.startswith("(") and raw_check.endswith(")"))
                    if (
                        not is_raw_dict
                        and len(raw_check) > 5
                        and not raw_check.startswith("{'path'")
                    ):
                        escaped_thinking = escape(trimmed_thinking)
                        step_title = (
                            f"💭 Step {step.step_number} Reasoning"
                            if getattr(step, "step_number", None)
                            else "💭 Reasoning"
                        )
                        self._safe_mount(
                            container,
                            thinking_block(
                                step_title,
                                escaped_thinking,
                                collapsed=True,
                            ),
                        )

                # Code execution
                if step.action == "code":
                    display_content = step.content
                    if len(display_content) > 10000:
                        display_content = (
                            display_content[:10000]
                            + "\n\n... [Output Truncated for UI Performance]"
                        )
                    self._safe_mount(
                        container,
                        Static(
                            Panel(
                                Syntax(
                                    display_content,
                                    "python",
                                    theme="monokai",
                                    line_numbers=True,
                                ),
                                title="⚡ Code Execution",
                                border_style="cyan",
                            )
                        ),
                    )
                    if step.result:
                        display_result = step.result
                        if len(display_result) > 10000:
                            display_result = (
                                display_result[:10000] + "\n... [Truncated]"
                            )
                        style = "red" if step.result.startswith("ERROR") else "green"
                        self._safe_mount(
                            container,
                            Static(
                                Panel(
                                    Text(display_result),
                                    title="📤 Output",
                                    border_style=style,
                                )
                            ),
                        )

                # Rejected Final Answer / Verification Gate Interception
                elif step.action == "rejected_final_answer":
                    raw_res = step.result or "Advancing to next task."
                    first_line = raw_res.splitlines()[0] if raw_res else "Advancing to next task"
                    clean_label = first_line.replace("❌ [VERIFICATION GATE REJECTION — ", "").replace("❌ [VERIFICATION GATE REJECTION]", "").rstrip("]")
                    if not clean_label.strip():
                        clean_label = "Advancing to next task"
                    self._safe_mount(
                        container,
                        Static(
                            f"  [bold cyan]🔄 Auto-Advancing:[/] [dim]{escape(clean_label)} (Turn {step.step_number})[/]",
                            classes="step-status",
                        ),
                    )

                # Final answer
                elif step.action == "final_answer":
                    display_content = sanitize_assistant_text(step.content) if step.content else ""
                    if not display_content.strip():
                        if step.result and step.result.strip():
                            display_content = step.result.strip()
                        else:
                            try:
                                from core.tools.task_helpers import get_workspace_pending_tasks
                                pending = (
                                    get_workspace_pending_tasks(self.engine.project_root)
                                    if getattr(self, "engine", None)
                                    else []
                                )
                                if pending:
                                    display_content = f"Turn completed. Next pending task: **{pending[0]}**."
                                else:
                                    display_content = "Turn completed."
                            except Exception:
                                display_content = "Turn completed."

                    if len(display_content) > 15000:
                        display_content = (
                            display_content[:15000]
                            + "\n\n... [Output Truncated for UI Performance]"
                        )
                    duration_str = None
                    if getattr(self, "_stream_start_time", None):
                        import time

                        elapsed = max(0.0, time.time() - self._stream_start_time)
                        duration_str = f"{elapsed:.1f}s"
                    self._safe_mount(
                        container,
                        MessageCard(
                            display_content,
                            role="final",
                            meta=card_meta_for(display_content),
                            duration=duration_str,
                        ),
                    )
                    self._chat_history.append(
                        {"role": "assistant", "content": step.content or display_content}
                    )

                # Sub-queries
                elif step.action == "sub_queries":
                    display_content = step.content
                    if len(display_content) > 10000:
                        display_content = display_content[:10000] + "\n... [Truncated]"
                    self._safe_mount(
                        container,
                        Static(
                            Panel(
                                escape(display_content),
                                title="🔄 Sub-Queries",
                                border_style="yellow",
                            )
                        ),
                    )
                    if step.result and step.result != "DEPTH LIMIT REACHED":
                        self._safe_mount(
                            container,
                            Static(
                                Panel(
                                    escape(step.result[:2000]),
                                    title="📥 Sub-Query Results",
                                    border_style="dim green",
                                )
                            ),
                        )
        except Exception:
            pass

        # Update sidebar plan panel & metadata in real-time after every step
        try:
            self.update_sidebar_meta()
        except Exception:
            pass

        if step.action != "final_answer":
            try:
                self._ensure_streaming_widget()
            except Exception:
                pass

    def _handle_test_event(self, event_type: str, data: dict) -> None:
        """Thread-safe handler for test lifecycle events from feedback loop."""
        try:
            self.call_from_thread(self._process_test_event, event_type, data)
        except Exception:
            self._process_test_event(event_type, data)

    def _process_test_event(self, event_type: str, data: dict) -> None:
        if event_type == "test_started":
            cmd = data.get("command", "tests")
            if self._status_bar:
                self._status_bar.update_status(test_status=f"[bold cyan]🧪 {escape(str(cmd))}...[/]")
        elif event_type == "test_completed":
            passed = data.get("passed", 0)
            failed = data.get("failed", 0)
            dur = data.get("duration_ms", 0.0)
            all_passed = bool(data.get("all_passed", False))
            if self._status_bar:
                if all_passed:
                    status_txt = f"[bold green]✓ {passed} tests ({dur:.0f}ms)[/]"
                else:
                    status_txt = f"[bold red]❌ {failed} failed[/]"
                self._status_bar.update_status(test_status=status_txt)

            # Mount TestVerificationCard in chat container if tests actually ran
            if data.get("command"):
                try:
                    container = self.query_one("#chat-container")
                    from rlm_optimized.tui_widgets.tool_card import TestVerificationCard

                    card = TestVerificationCard(data)
                    self._safe_mount(container, card)
                    self.call_after_refresh(self._scroll_chat_to_end)
                except Exception:
                    pass

            # Stream into Output Tab
            try:
                out_widget = self.query_one("#output-log-content")
                stdout = (data.get("stdout") or "").strip()
                stderr = (data.get("stderr") or "").strip()
                if stdout:
                    out_widget.update(f"[bold cyan]── Test Verification Output ──[/]\n{escape(stdout)}")
                elif stderr:
                    out_widget.update(f"[bold red]── Test Verification Errors ──[/]\n{escape(stderr)}")
            except Exception:
                pass

    def action_copy_chat(self) -> None:
        if not self._chat_history:
            self.notify("No chat history to copy", severity="warning")
            return

        lines = []
        for item in self._chat_history:
            role_title = "You" if item["role"] == "user" else "Assistant"
            lines.append(f"### {role_title}\n\n{item['content']}\n")

        full_text = "\n".join(lines).strip()
        if copy_to_clipboard(full_text):
            self.notify(
                "Chat transcript copied to clipboard", severity="information", timeout=2
            )
        else:
            self.notify("Failed to copy to clipboard", severity="error", timeout=3)

    def action_copy_last(self) -> None:
        last_assistant = None
        for item in reversed(self._chat_history):
            if item["role"] == "assistant":
                last_assistant = item["content"]
                break
        if not last_assistant:
            self.notify("No assistant responses found to copy", severity="warning")
            return

        if copy_to_clipboard(last_assistant):
            self.notify(
                "Last response copied to clipboard", severity="information", timeout=2
            )
        else:
            self.notify("Failed to copy to clipboard", severity="error", timeout=3)

    def action_copy_selection(self) -> None:
        # 1. Try screen native selection text
        try:
            sel_text = self.screen.get_selected_text()
        except Exception:
            sel_text = None

        if sel_text and sel_text.strip():
            if copy_to_clipboard(sel_text.strip()):
                self.notify(
                    "Selected text copied to clipboard",
                    severity="information",
                    timeout=2,
                )
            else:
                self.notify("Failed to copy selection", severity="error", timeout=3)
            return

        def _on_turn_selected(content: Optional[str]):
            if content:
                if copy_to_clipboard(content):
                    self.notify(
                        "Turn copied to clipboard", severity="information", timeout=2
                    )
                else:
                    self.notify("Failed to copy turn", severity="error", timeout=3)

        self.push_screen(CopySelectionModal(self._chat_history), _on_turn_selected)
