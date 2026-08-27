"""Tool execution, tiered approval prompts, and autonomous harness steps for CLI session."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
import time
from typing import Any, Callable, Optional
from rich.console import Console

from core.tools.registry import get_tool_registry
from core.tools.classification import AUTO, CONFIRM, REVIEW
from context_manager.cli.dashboard import ContextDashboard, ActionTracker

console = Console()
dashboard = ContextDashboard()
_core_reg = get_tool_registry()

_TOOL_KIND: dict[str, str] = {
    "READ_FILE": "read_file",
    "WRITE_FILE": "write_file",
    "RUN_COMMAND": "run_command",
    "WEB_SEARCH": "web_search",
    "WEB_FETCH": "web_fetch",
    "DOC_SEARCH": "doc_search",
    "WEB_VERIFY": "web_verify",
    "SAVE_MEMORY": "save_memory",
}


def _tool_kind(name: str) -> str:
    return _TOOL_KIND.get(name.upper(), "default")


def _tool_label(name: str, params: dict) -> str:
    name_u = name.upper()
    args = list(params.values())
    first = str(args[0])[:60] if args else ""
    if name_u == "READ_FILE":
        return f"Reading  {first}"
    if name_u == "WRITE_FILE":
        return f"Writing  {first}"
    if name_u == "RUN_COMMAND":
        return f"Running  {first}"
    if name_u == "WEB_SEARCH":
        return f'Searching  "{first}"'
    if name_u == "WEB_FETCH":
        return f"Fetching  {first}"
    if name_u == "DOC_SEARCH":
        return f'Doc search  "{first}"'
    if name_u == "WEB_VERIFY":
        lang = str(args[1])[:12] if len(args) > 1 else "code"
        return f"Verifying {lang}  {first[:40]}"
    if name_u == "SAVE_MEMORY":
        return f'Saving memory  "{first[:40]}"'
    return f"{name}  {first}"


def _risk_tier(name: str, params: dict) -> str:
    name_u = name.upper()
    args = [str(v) for v in params.values()]
    tool = _core_reg.get(name_u)
    if tool:
        return _core_reg.risk_level_for(name_u, args)
    return CONFIRM


class ToolExecutorMixin:
    """Provides tool execution with approval tiers and self-healing error recovery."""

    async def _execute_tool_with_approval(
        self,
        name: str,
        params: dict,
        tracker: ActionTracker,
    ) -> Optional[str]:
        tier = _risk_tier(name, params)
        kind = _tool_kind(name)
        label = _tool_label(name, params)
        act = tracker.start(kind, label)

        # ── TrajectoryLock Deduplication Check ────────────────────────
        _READ_ONLY_TOOLS = {
            "READ_FILE", "READ_SYMBOLS", "LIST_DIR", "GREP", "SEARCH_AST",
            "INSPECT_WEB", "PLAY_AND_VERIFY_GAME", "WEB_SEARCH", "WEB_FETCH",
            "DOC_SEARCH", "WEB_VERIFY", "GIT", "FORMAT_CODE", "VERIFY", "ASK_USER",
        }
        is_read_only = (name or "").upper() in _READ_ONLY_TOOLS

        if getattr(self, "trajectory_lock", None):
            is_dup, dup_count, hint = self.trajectory_lock.is_duplicate(name, params, is_read_only=is_read_only)
            if is_dup:
                t_path = (
                    str(
                        params.get("path")
                        or params.get("file")
                        or params.get("target")
                        or params.get("filename")
                        or ""
                    )
                    if isinstance(params, dict)
                    else ""
                )
                if t_path and (name or "").upper() in ("READ_FILE", "READ", "EDIT_FILE", "EDIT", "WRITE_FILE", "WRITE"):
                    from core.tools.implementations import tool_read_file_impl
                    proj_root = getattr(self, "project_root", os.getcwd())
                    file_preview = tool_read_file_impl({"path": t_path}, proj_root)
                    if file_preview and (file_preview.startswith("File not found") or not os.path.exists(os.path.join(proj_root, t_path))):
                        hint = (
                            f"⛔ [FILE NOT FOUND]: '{t_path}' does not exist on disk.\n"
                            f"Next required action: Create this file now by emitting WRITE_FILE:\n"
                            f'<tool_call>{{"name": "WRITE_FILE", "arguments": {{"path": "{t_path}", "content": "// Initial code implementation\\n"}}}}</tool_call>'
                        )
                    elif file_preview and not file_preview.startswith("Error"):
                        lines_list = file_preview.splitlines()
                        tot_lines = len(lines_list)
                        if tot_lines > 80:
                            preview_body = "\n".join(lines_list[:80]) + f"\n... [{tot_lines - 80} more lines in file]"
                        else:
                            preview_body = file_preview
                        hint = (
                            f"⛔ [DUPLICATE {name.upper()} BLOCKED]: Repeated call on '{t_path}' halted.\n"
                            f"Here is the CURRENT FILE CONTENT of '{t_path}' directly from disk (lines 1–{tot_lines}):\n\n"
                            f"```\n{preview_body}\n```\n\n"
                            f"Next required action: Inspect the actual lines above and submit your edit using exact old_text:\n"
                            f'<tool_call>{{"name": "EDIT_FILE", "arguments": {{"path": "{t_path}", "old_text": "...", "new_text": "..."}}}}</tool_call>'
                        )
                self._params.temperature = min(0.9, self._params.temperature + 0.3)
                out = hint or f"STOP: You just repeated the exact same '{name}' call. Try a DIFFERENT tool or approach."
                if hasattr(self.memory, "state") and self.memory.state and hasattr(self.memory.state, "tried_and_failed"):
                    entry = f"Duplicate {name.upper()} call blocked ({dup_count}x)"
                    if entry not in self.memory.state.tried_and_failed:
                        self.memory.state.tried_and_failed.append(entry)
                self.memory.add_tool_result(out, tool_name=name)
                tracker.finish(act, ok=False)
                return out
            else:
                self.trajectory_lock.register(name, params)
        else:
            # No trajectory lock available - skip deduplication
            pass

        # ── Code Mode Guard: Check for implementation plan before modifying code ──
        if (self.mode == "code" or getattr(self, "_current_phase", "code") == "code") and name.upper() in ("WRITE_FILE", "EDIT_FILE"):
            fpath = params.get("path") or params.get("file") or ""
            base_p = os.path.basename(str(fpath)).lower()
            norm_p = os.path.normpath(str(fpath))
            is_plan_target = (
                base_p in ("implementation_plan.md", "plan.md")
                or norm_p == "implementation_plan.md"
                or str(fpath).lower().endswith("implementation_plan.md")
                or norm_p.startswith(".torchlight")
            )
            plan_file = os.path.join(self.project_path, "implementation_plan.md")
            if not os.path.exists(plan_file) and not is_plan_target:
                out = (
                    "❌ [CODE MODE GUARD — MISSING IMPLEMENTATION PLAN] 'implementation_plan.md' does not exist in the workspace. "
                    "In Code Mode, you must check for an implementation plan first before modifying code files. "
                    "Please conclude with <FINAL_ANSWER> asking the user to switch to Plan Mode (`/mode plan` or `context plan`) to formulate and approve the plan first."
                )
                self.memory.add_tool_result(out, tool_name=name)
                tracker.finish(act, ok=False)
                return out

        if tier == AUTO:
            try:
                result = await self.skills.execute_skill(name, params)
                ok = result.success
                out = (
                    f"Result of {name}:\n{result.output}"
                    if ok
                    else f"Error in {name}:\n{result.error}"
                )

                # Agentic Self-Correction Hints
                if not ok:
                    self._event_lock_phase("tool_error", name)
                    if "No such file" in result.error:
                        out += '\n💡 HINT: Use DOC_SEARCH("filename") or RUN_COMMAND("find . -name \'...\' ") to locate it.'
                    elif "Permission denied" in result.error:
                        out += "\n💡 HINT: Check file permissions or use 'ls -la' to inspect the directory."
                    elif "not enough arguments" in result.error.lower():
                        out += f"\n💡 HINT: Check the signature of {name} in the system prompt."

                tracker.finish(act, ok=ok)
                self._notify_file_touched(name, out)
                tool_images = None
                if ok and name.upper() == "VIEW_IMAGE":
                    img_p = (
                        params.get("path")
                        or params.get("file")
                        or params.get("image")
                    )
                    if img_p:
                        tool_images = [img_p]
                elif ok and name.upper() == "INSPECT_WEB":
                    m_shot = re.search(r"\*\*Screenshot Saved:\*\*\s*`([^`]+)`", out)
                    if m_shot:
                        tool_images = [m_shot.group(1)]

                self.memory.add_tool_result(out, tool_name=name, images=tool_images)
                if getattr(self, "trajectory_lock", None):
                    self.trajectory_lock.record_output(name, params, out)

                # Pin file content after READ_FILE so it survives compression
                if ok and name.upper() == "READ_FILE":
                    fpath = params.get("path", "")
                    if fpath:
                        if hasattr(self.memory, "record_file_read"):
                            self.memory.record_file_read(fpath)
                        if result.output:
                            self.memory.pin_file(fpath, result.output)
                elif ok and name.upper() in ("EDIT_FILE", "WRITE_FILE"):
                    self._event_lock_phase("file_edit", name)
                    fpath = params.get("path") or params.get("file")
                    if fpath:
                        if "implementation_plan" in str(fpath).lower():
                            self._plan_updated_this_turn = True
                        added = 0
                        deleted = 0
                        diff_m = re.search(r"\(\+(\d+),\s*[-–](\d+)\)", result.output or "")
                        if diff_m:
                            added = int(diff_m.group(1))
                            deleted = int(diff_m.group(2))
                        new_content = None
                        full_p = os.path.join(self.project_root, fpath) if not os.path.isabs(fpath) else fpath
                        if os.path.exists(full_p):
                            try:
                                with open(full_p, "r", encoding="utf-8") as _f:
                                    new_content = _f.read()
                            except Exception:
                                pass
                        if hasattr(self.memory, "record_file_modified"):
                            self.memory.record_file_modified(
                                fpath,
                                added=added,
                                deleted=deleted,
                                new_content=new_content,
                            )
                        self.memory.refresh_pin(fpath, self.project_root)
                        try:
                            from core.tools.task_helpers import auto_mark_task_completed_by_file

                            has_failing = bool(
                                self._feedback_loop
                                and getattr(self._feedback_loop, "has_failing_tests", False)
                            )
                            auto_mark_task_completed_by_file(
                                self.project_root,
                                str(fpath),
                                verified=not has_failing,
                            )
                        except Exception:
                            pass
                    elif name.upper() in ("RUN_COMMAND", "BASH", "SHELL"):
                        cmd = params.get("command") or params.get("cmd")
                        if cmd:
                            try:
                                from core.tools.task_helpers import auto_mark_task_completed_by_command

                                auto_mark_task_completed_by_command(
                                    self.project_root,
                                    str(cmd),
                                    return_code=0 if ok else 1,
                                )
                            except Exception:
                                pass

                # Execution feedback: auto-run tests or web inspector after code changes
                test_result = self._feedback_loop.on_tool_executed(name, params, result.output)
                if test_result:
                    # Add test or web feedback to memory context
                    feedback = self._feedback_loop.build_feedback_context()
                    if feedback:
                        self.memory.add_tool_result(feedback, tool_name="TEST_FEEDBACK")

                return out
            except Exception as e:
                tracker.finish(act, ok=False)
                err = f"Error in {name}: {e}"
                self.memory.add_tool_result(err, tool_name=name)
                dashboard.print_error(err)
                return f"❌ System Error executing {name}: {e}"

        if tier == CONFIRM:
            args_preview = json.dumps(list(params.values()))[:120]
            tracker._refresh()
            confirmed = typer.confirm(
                f"\n  [cyan]▶[/cyan] {name}({args_preview})  — approve?",
                default=True,
            )
            if confirmed:
                try:
                    result = await self.skills.execute_skill(name, params)
                    ok = result.success
                    out = (
                        f"Result of {name}:\n{result.output}"
                        if ok
                        else f"Error in {name}:\n{result.error}"
                    )
                    tracker.finish(act, ok=ok)
                    self._notify_file_touched(name, out)
                    self.memory.add_tool_result(out, tool_name=name)

                    # Pin file content after READ_FILE so it survives compression
                    if ok and name.upper() == "READ_FILE":
                        fpath = params.get("path", "")
                        if fpath and result.output:
                            self.memory.pin_file(fpath, result.output)
                    elif ok and name.upper() in ("EDIT_FILE", "WRITE_FILE"):
                        fpath = params.get("path") or params.get("file")
                        if fpath:
                            if "implementation_plan" in str(fpath).lower():
                                self._plan_updated_this_turn = True
                            self.memory.refresh_pin(fpath, self.project_root)
                            try:
                                from core.tools.task_helpers import auto_mark_task_completed_by_file

                                has_failing = bool(
                                    self._feedback_loop
                                    and getattr(self._feedback_loop, "has_failing_tests", False)
                                )
                                auto_mark_task_completed_by_file(
                                    self.project_root,
                                    str(fpath),
                                    verified=not has_failing,
                                )
                            except Exception:
                                pass
                    elif ok and name.upper() in ("RUN_COMMAND", "BASH", "SHELL"):
                        cmd = params.get("command") or params.get("cmd")
                        if cmd:
                            try:
                                from core.tools.task_helpers import auto_mark_task_completed_by_command

                                auto_mark_task_completed_by_command(
                                    self.project_root,
                                    str(cmd),
                                    return_code=0,
                                )
                            except Exception:
                                pass

                    # Execution feedback: auto-run tests after code changes
                    test_result = self._feedback_loop.on_tool_executed(name, params, result.output)
                    if test_result and not test_result.all_passed:
                        feedback = self._feedback_loop.build_feedback_context()
                        if feedback:
                            self.memory.add_tool_result(feedback, tool_name="TEST_FEEDBACK")

                    return out
                except Exception as e:
                    tracker.finish(act, ok=False)
                    err = f"Error in {name}: {e}"
                    self.memory.add_tool_result(err, tool_name=name)
                    dashboard.print_error(err)
                    return None
            else:
                tracker.finish(act, ok=False)
                msg = f"User denied execution of {name}."
                self.memory.add_tool_result(msg, tool_name=name)
                dashboard.print_warning(f"Skipped {name}")
                return None

        if tier == REVIEW:
            args_preview = json.dumps(list(params.values()))[:120]
            tracker._refresh()
            console.print(
                f"\n  [bold red]⚠  DESTRUCTIVE:[/bold red] {name}({args_preview})\n"
                f"  [red]This cannot be undone.[/red]"
            )
            confirmed = typer.confirm("  Execute anyway?", default=False)
            if confirmed:
                try:
                    result = await self.skills.execute_skill(name, params)
                    ok = result.success
                    out = (
                        f"Result of {name}:\n{result.output}"
                        if ok
                        else f"Error in {name}:\n{result.error}"
                    )
                    tracker.finish(act, ok=ok)
                    self._notify_file_touched(name, out)
                    self.memory.add_tool_result(out, tool_name=name)

                    # Pin file content after READ_FILE so it survives compression
                    if ok and name.upper() == "READ_FILE":
                        fpath = params.get("path", "")
                        if fpath and result.output:
                            self.memory.pin_file(fpath, result.output)
                    elif ok and name.upper() in ("EDIT_FILE", "WRITE_FILE"):
                        fpath = params.get("path") or params.get("file")
                        if fpath:
                            self.memory.refresh_pin(fpath, self.project_root)

                    # Execution feedback: auto-run tests after code changes
                    test_result = self._feedback_loop.on_tool_executed(name, params, result.output)
                    if test_result and not test_result.all_passed:
                        feedback = self._feedback_loop.build_feedback_context()
                        if feedback:
                            self.memory.add_tool_result(feedback, tool_name="TEST_FEEDBACK")

                    return out
                except Exception as e:
                    tracker.finish(act, ok=False)
                    err = f"Error in {name}: {e}"
                    self.memory.add_tool_result(err, tool_name=name)
                    dashboard.print_error(err)
                    return None
            else:
                tracker.finish(act, ok=False)
                msg = f"User denied execution of {name} (REVIEW tier)."
                self.memory.add_tool_result(msg, tool_name=name)
                dashboard.print_warning(f"Cancelled {name}")
                return None

        return None

    async def _verify_and_refine_if_needed(
        self, proposal: str, user_task: str, phase_name: str = "code"
    ) -> str:
        """Run out-of-band DebateVerifier pass if candidate proposal needs verification."""
        if not hasattr(self, "debate_verifier") or not self.debate_verifier:
            return proposal

        parsed_skills = self.skills.parse_skills(proposal) if hasattr(self, "skills") else []
        first_tool = parsed_skills[0][0] if parsed_skills else None

        if self.debate_verifier.should_debate(tool_name=first_tool, phase=phase_name):
            dashboard.print_critique_start(tool_name=first_tool)
            try:
                refined_output, critique_res = await self.debate_verifier.verify_and_refine(
                    proposal=proposal,
                    task_context=user_task,
                    tool_name=first_tool,
                    phase=phase_name,
                )
                if critique_res.has_flaws and refined_output != proposal:
                    dashboard.print_refined(flaws=critique_res.flaws, tool_name=first_tool)
                    return refined_output
            except Exception as verifier_err:
                pass
        return proposal

    def _harness_step_fn(self, task: str, depth: int = 0) -> bool:
        """
        Step function for AutonomousHarness - executes a single task iteration.
        Returns True if task completed (final answer), False if needs more steps.
        """
        # This is a synchronous wrapper - we need to run async code
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Can't run async in running loop, create a task instead
                # For now, return False to indicate not complete
                return False
            else:
                return loop.run_until_complete(self._harness_step_async(task, depth))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self._harness_step_async(task, depth))

    async def _harness_step_async(self, task: str, depth: int = 0) -> bool:
        """Async implementation of harness step function."""
        # Generate response for the task
        self.memory.add_user_message(task)

        # Detect phase
        self._update_params(task)

        if self.memory.should_compress():
            await self._compress_context()

        response = await self._generate_streaming_response(task)
        response = await self._verify_and_refine_if_needed(
            response, user_task=task, phase_name=self._current_phase
        )
        self.memory.add_assistant_message(response)

        # Check for final answer
        if "<FINAL_ANSWER>" in response:
            return True

        # Process tool calls
        parsed_skills = self.skills.parse_skills(response)
        for name, params in parsed_skills:
            await self._execute_tool_with_approval(name, params, None)

        # Check again after tools
        self._update_params(task, response)
        response2 = await self._generate_streaming_response("")
        response2 = await self._verify_and_refine_if_needed(
            response2, user_task=task, phase_name=self._current_phase
        )
        self.memory.add_assistant_message(response2)

        return "<FINAL_ANSWER>" in response2

    # ── Main chat loop ────────────────────────────────────────────────────────
