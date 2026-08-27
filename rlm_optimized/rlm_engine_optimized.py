from __future__ import annotations

import asyncio
import collections
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from core.api.base import InferenceParams
from core.prompts.system import get_phase_system_prompt
from core.tools.classification import CONFIRM, REVIEW
from core.tools.dedup import TrajectoryLock, get_alternate_trajectory_hint
from core.tools.implementations import set_ctx_window
from core.tools.parser import (
    clean_and_parse_json as _clean_and_parse_json,
    extract_balanced_json_object as _extract_balanced_json_object,
    parse_tool_call_payload,
    repair_unclosed_tool_call_tag,
    strip_interleaved_prose,
    tolerant_json_repair as _tolerant_json_repair,
    unwrap_double_encoded_json,
)
from core.tools.registry import ToolResult, get_tool_registry
from rlm_optimized.config import (
    CTX_SIZE,
    IS_8GB_DEVICE,
    MAX_ITERATIONS_PER_LEVEL,
    MAX_RECURSION_DEPTH,
    MAX_THINKING_LOOPS,
)
from rlm_optimized.engine.models import SolveResult, Step
from rlm_optimized.engine.phase_detector import PhaseDetectorMixin
from rlm_optimized.engine.response_parser import (
    ResponseParserMixin,
    _looks_like_full_file,
    _looks_like_prose_or_outline,
    _trim_trailing_prose,
)
from rlm_optimized.engine.stream_handler import StreamHandlerMixin
from rlm_optimized.engine.verification_gate import VerificationGateMixin
from rlm_optimized.prompts import build_step_message
from rlm_optimized.repl_sandbox import REPLSandbox
from rlm_optimized.tool_schemas import validate_and_normalize_tool_call

try:
    from core.memory.token_counter import get_token_counter
except ImportError:
    pass

try:
    from core.compression.summarizer import ConversationSummarizer
    from core.memory.manager import MemoryConfig, TieredMemory
    from core.memory.models import ExecutionMode, FIXED_EXECUTION_MODES, Message, MessageRole
    from core.memory.persistence import ProjectMemory, ensure_project_initialized

    _summarizer = ConversationSummarizer()
except ImportError:
    _summarizer = None
    TieredMemory = None
    MemoryConfig = None
    ensure_project_initialized = None
    ExecutionMode = None
    FIXED_EXECUTION_MODES = frozenset({"plan", "code", "chat"})


try:
    from core.debate.verifier import DebateVerifier
except ImportError:
    DebateVerifier = None

class RLMEngineOptimized(
    PhaseDetectorMixin,
    StreamHandlerMixin,
    ResponseParserMixin,
    VerificationGateMixin,
):
    def __init__(
        self,
        client=None,
        on_step: Optional[Callable[[Step], None]] = None,
        max_depth: int = MAX_RECURSION_DEPTH,
        project_root: Optional[str] = None,
        approval_fn: Optional[Callable[[str, str, dict], bool]] = None,
        on_token: Optional[Callable[[str], None]] = None,
        on_status_change: Optional[Callable[[dict], None]] = None,
        on_tasks_changed: Optional[Callable[[dict], None]] = None,
        enable_debate: bool = False,
        debate_verifier: Optional[object] = None,
        execution_mode: Optional[str] = None,
    ):
        if client is None:
            from rlm_optimized.llamacpp_client import LlamaCppClient

            client = LlamaCppClient()
        self.client = client
        self.on_step = on_step
        self.on_token = on_token  # callback for each streaming token
        self.on_status_change = (
            on_status_change  # callback for real-time telemetry state
        )
        self.on_tasks_changed = on_tasks_changed  # callback for real-time task state
        self.project_root = project_root or os.getcwd()
        if ensure_project_initialized:
            ensure_project_initialized(self.project_root)
        set_ctx_window(CTX_SIZE)
        self.sandbox = REPLSandbox(project_root=self.project_root)
        self._total_llm_calls = 0
        self.sandbox.set_llm_query_fn(self._sandbox_llm_query)
        self.approval_fn = approval_fn  # fn(tool_name, risk, args) -> bool or async
        self._inline_code_counter = 0
        self._execution_mode = execution_mode or "unified"
        self._execution_mode_callback = None
        self._prompt_hash_ring = collections.deque(maxlen=5)

        if debate_verifier is not None:
            self.debate_verifier = debate_verifier
        elif DebateVerifier is not None and enable_debate:
            self.debate_verifier = DebateVerifier(self.client, enabled=enable_debate)
        else:
            self.debate_verifier = None

        self._memory = None
        try:
            from core.execution.feedback_loop import ExecutionFeedbackLoop

            self.feedback_loop = ExecutionFeedbackLoop(
                project_root=Path(self.project_root)
            )
        except Exception:
            self.feedback_loop = None

    @property
    def execution_mode(self) -> str:
        return self._execution_mode

    @execution_mode.setter
    def execution_mode(self, value) -> None:
        if hasattr(value, "value"):
            str_val = str(value.value).lower()
        else:
            str_val = str(value).lower()
        self._execution_mode = str_val
        # Sync to memory state if available
        mem = getattr(self, "memory", None)
        if mem and hasattr(mem, "state") and ExecutionMode is not None:
            try:
                mem.state.execution_mode = ExecutionMode(str_val)
            except ValueError:
                pass


        # When entering explicit fixed mode (plan, code, chat), lock the phase and calibrate inference params
        if str_val in FIXED_EXECUTION_MODES:
            self._current_phase = str_val
            if hasattr(self, "lock_phase"):
                self.lock_phase(str_val)
        elif str_val == "unified":
            if hasattr(self, "lock_phase"):
                self.lock_phase("auto")


        # Call callback if registered
        cb = getattr(self, "_execution_mode_callback", None)
        if cb:
            try:
                cb(str_val)
            except Exception:
                pass



    def set_execution_mode_callback(self, callback) -> None:
        """Register callback to be notified of execution mode changes."""
        self._execution_mode_callback = callback

    @property
    def memory(self):
        if self._memory is None and TieredMemory and MemoryConfig:
            try:
                from core.memory.persistence import ProjectMemory
                from rlm_optimized.config import CTX_SIZE, estimate_metadata_overhead

                pm = ProjectMemory(Path(self.project_root))
                self._memory = TieredMemory(
                    config=MemoryConfig.auto_tune(
                        max_tokens=CTX_SIZE,
                        metadata_overhead=estimate_metadata_overhead(ctx_size=CTX_SIZE),
                    ),
                    project_memory=pm,
                )
            except Exception:
                pass
        return self._memory

    @memory.setter
    def memory(self, val) -> None:
        self._memory = val

    def set_project_root(self, project_root: str) -> None:
        """Switch the active workspace, keeping the sandbox's AST-graph
        lookups (get_project_structure/semantic_search/etc.) in sync so
        they can't silently query a stale or wrong-project graph."""
        self.project_root = project_root
        if ensure_project_initialized:
            ensure_project_initialized(self.project_root)
        self.sandbox.set_project_root(project_root)
        if self.feedback_loop:
            self.feedback_loop.project_root = Path(project_root).resolve()

    def _notify_status(self, state: str, details: Optional[dict] = None) -> None:
        """Notify listeners of real-time background status and action telemetry."""
        if self.on_status_change:
            try:
                payload = {
                    "state": state,
                    "details": details or {},
                    "total_llm_calls": self._total_llm_calls,
                }
                self.on_status_change(payload)
            except Exception:
                pass

    def _notify_tasks_changed(self, details: Optional[dict] = None) -> None:
        """Notify listeners (dashboard/TUI) that task state changed after a tool call."""
        snapshot = {"pending": [], "in_progress": 0, "completed": 0, "skipped": 0}
        try:
            from core.tools.task_helpers import get_workspace_pending_tasks

            snapshot["pending"] = get_workspace_pending_tasks(self.project_root)[:5]
            goal_path = os.path.join(self.project_root, ".torchlight", "goal_spec.json")
            if os.path.exists(goal_path):
                import json as _json

                with open(goal_path, "r", encoding="utf-8") as f:
                    gdata = _json.load(f)
                for t in gdata.get("tasks", []):
                    st = t.get("status", "pending")
                    if st in ("completed", "verified"):
                        snapshot["completed"] += 1
                    elif st in ("in_progress", "active"):
                        snapshot["in_progress"] += 1
                    elif st in ("skipped", "skip"):
                        snapshot["skipped"] += 1
        except Exception:
            pass
        if details:
            snapshot.update(details)
        if self.on_tasks_changed:
            try:
                self.on_tasks_changed(snapshot)
            except Exception:
                pass
        self._notify_status("TASKS_CHANGED", snapshot)

    def _sandbox_llm_query(self, prompt: str) -> str:
        return self.client.query(prompt)

    def reset_session(self) -> None:
        """Completely wipes session context like a brand new session."""
        self._memory = None
        self._messages = None
        self._current_phase = None
        self._total_llm_calls = 0
        self._final_answer_rejections = 0
        self._inline_code_counter = 0
        if hasattr(self, "_prompt_hash_ring") and self._prompt_hash_ring:
            self._prompt_hash_ring.clear()
        if hasattr(self, "sandbox") and self.sandbox:
            self.sandbox.reset()
        if hasattr(self, "recovery_engine") and self.recovery_engine:
            self.recovery_engine.reset()

    def compact_context(self, memory=None, force: bool = True) -> tuple[int, int, int]:
        """Manually compact context memory and return (before, after, freed)."""
        target_mem = memory or getattr(self, "_memory", None)
        if target_mem is not None and hasattr(target_mem, "compress_recent"):
            before = getattr(target_mem, "total_tokens", 0)
            summarizer_fn = _summarizer.simple_summarize if _summarizer else None
            target_mem.compress_recent(
                summarizer_fn=summarizer_fn, preserve_first=1, force=force
            )
            after = getattr(target_mem, "total_tokens", 0)
            return before, after, max(0, before - after)
        elif getattr(self, "_messages", None):
            msgs = self._messages
            before = sum(len(m.get("content", "")) // 4 for m in msgs)
            if len(msgs) > 2:
                sys_msg = msgs[0] if msgs[0].get("role") == "system" else None
                recent = msgs[-1:]
                older = msgs[1:-1] if sys_msg else msgs[:-1]
                summary = f"[Context compacted. {len(older)} turns omitted to save memory.]"
                new_msgs = ([sys_msg] if sys_msg else []) + [{"role": "system", "content": summary}] + recent
                self._messages = new_msgs
            after = sum(len(m.get("content", "")) // 4 for m in self._messages)
            return before, after, max(0, before - after)
        return 0, 0, 0

    def _is_vision_supported(self) -> bool:
        """Check if active LLM client or server supports multimodal image inputs."""
        if self.client is None:
            return True
        if hasattr(self.client, "_server_supports_vision"):
            return bool(self.client._server_supports_vision)
        if hasattr(self.client, "is_vision"):
            return bool(self.client.is_vision)
        if hasattr(self.client, "traits") and isinstance(self.client.traits, dict):
            return bool(self.client.traits.get("is_vision", False))
        return True

    async def solve_async(
        self,
        task: str,
        depth: int = 0,
        phase: Optional[str] = None,
        images: Optional[list[str]] = None,
    ) -> SolveResult:
        result = SolveResult(answer="", depth=depth)
        self._total_llm_calls = 0
        self._final_answer_rejections = 0
        if hasattr(self, "recovery_engine") and self.recovery_engine:
            self.recovery_engine.reset()

        # Extract image references from task text if not explicitly passed
        from core.utils.image_utils import extract_image_paths_from_text

        img_list = list(images) if images else []
        if not img_list and task:
            img_list = extract_image_paths_from_text(task)

        # Determine effective phase: explicit param > execution_mode > "code" default
        if self.execution_mode in FIXED_EXECUTION_MODES:
            phase = self.execution_mode
        elif phase is None:
            if self.execution_mode == "goal":
                phase = self._detect_phase(task)
            elif self.execution_mode == "unified":
                phase = self._detect_phase(task)
            else:
                phase = "code"

        self._current_phase = phase



        # ── Fix: Inject pending task context for Code Mode continuation commands ──
        # Qwen 3B cannot infer what task to work on from a vague "continue"
        # message. We inject the actual next pending task + target file + tool
        # template so the model emits a <tool_call> on Turn 1.
        _CONTINUATION_KWS = (
            "continue", "proceed", "carry on", "next", "resume",
            "building", "build", "keep going", "go ahead", "start",
        )
        if phase == "code" and any(kw in task.lower() for kw in _CONTINUATION_KWS):
            try:
                from core.tools.task_helpers import get_workspace_pending_tasks

                _pending = (
                    get_workspace_pending_tasks(self.project_root)
                    if self.project_root
                    else []
                )
                if _pending:
                    _next_task = _pending[0]
                    _fm = re.search(
                        r"([a-zA-Z0-9_\-\.\/]+\.(?:html|css|js|py|ts|jsx|tsx|json|go|rs))",
                        _next_task,
                    )
                    _target_file = _fm.group(1) if _fm else None
                    _target_exists = (
                        os.path.exists(os.path.join(self.project_root, _target_file))
                        if _target_file and self.project_root
                        else False
                    )

                    if _target_file and _target_exists:
                        _tool_tmpl = f'<tool_call>{{"name": "EDIT_FILE", "arguments": {{"path": "{_target_file}", "old_text": "...", "new_text": "..."}}}}</tool_call>'
                    elif _target_file:
                        _tool_tmpl = f'<tool_call>{{"name": "WRITE_FILE", "arguments": {{"path": "{_target_file}", "content": "..."}}}}</tool_call>'
                    else:
                        _tool_tmpl = '<tool_call>{"name": "READ_FILE", "arguments": {"path": "implementation_plan.md"}}</tool_call>'

                    task = (
                        f"[CODE MODE: EXECUTE TASK DIRECTLY]\n"
                        f"Active Task: {_next_task}\n"
                        + (f"Target file: {_target_file}\n" if _target_file else "")
                        + f"You MUST write the full implementation now. Start your response immediately with:\n{_tool_tmpl}\n"
                        f"Do NOT output conversational text, explanations, or questions."
                    )
            except Exception:
                pass

        if TieredMemory and MemoryConfig:
            from .config import CTX_SIZE, estimate_metadata_overhead
            from pathlib import Path
            from core.memory.persistence import ProjectMemory

            if getattr(self, "_memory", None) is None:
                pm = ProjectMemory(Path(self.project_root))
                memory = TieredMemory(
                    config=MemoryConfig.auto_tune(
                        max_tokens=CTX_SIZE,
                        metadata_overhead=estimate_metadata_overhead(ctx_size=CTX_SIZE),
                    ),
                    project_memory=pm,
                )
                memory.add_system_message(get_phase_system_prompt(phase))
                self._memory = memory
            else:
                if hasattr(self._memory, "update_system_prompt"):
                    self._memory.update_system_prompt(get_phase_system_prompt(phase))

            self._memory.add_user_message(task, images=img_list if img_list else None)
            memory = self._memory
            use_memory = True
        else:
            from .config import CTX_SIZE

            if getattr(self, "_messages", None) is None:
                self._messages = [
                    {
                        "role": "system",
                        "content": get_phase_system_prompt(phase),
                    }
                ]
            if img_list and self._is_vision_supported():
                from core.utils.image_utils import format_openai_vision_content

                self._messages.append(
                    {
                        "role": "user",
                        "content": format_openai_vision_content(
                            task, img_list, project_root=self.project_root
                        ),
                    }
                )
            elif img_list:
                from core.utils.image_utils import format_image_text_summary

                summaries = [
                    format_image_text_summary(img, project_root=self.project_root)
                    for img in img_list
                ]
                notice = "\n".join(summaries)
                full_text = f"{task}\n\n{notice}".strip() if task else notice
                self._messages.append({"role": "user", "content": full_text})
            else:
                self._messages.append({"role": "user", "content": task})
            messages = self._messages
            use_memory = False

        sandbox_lock = asyncio.Lock()
        consecutive_thinking = 0  # Track loops with no action tag
        consecutive_code_errors = 0  # Track consecutive failed code executions
        last_code_output = None  # Track last successful CODE result

        # ── Consecutive duplicate tool call detection ─────────────────
        trajectory_lock = TrajectoryLock(window_size=5, max_duplicates=3)
        MAX_DUPLICATES = 3  # force-break after this many consecutive identical calls

        # ── REPL code duplicate detection & temperature recovery ──────
        _executed_code_payloads: set[str] = set()
        initial_temp = getattr(self.client, "temperature", 0.1)

        for iteration in range(MAX_ITERATIONS_PER_LEVEL):
            self._total_llm_calls += 1
            if use_memory:
                if memory.should_compress():
                    self._notify_status(
                        "THINKING", {"depth": depth, "status": "compacting context"}
                    )
                    summarizer_fn = (
                        _summarizer.simple_summarize if _summarizer else None
                    )
                    memory.compress_recent(
                        summarizer_fn=summarizer_fn, preserve_first=2, force=True
                    )
                context = memory.get_context_for_llm(
                    project_root=self.project_root,
                    vision_supported=self._is_vision_supported(),
                )
            else:
                context = messages

            self._notify_status(
                "THINKING", {"depth": depth, "iteration": iteration + 1}
            )
            try:
                response = await self._stream_llm(context)
            except Exception as llm_err:
                err_str = str(llm_err).lower()
                is_ctx_err = any(
                    k in err_str
                    for k in (
                        "context",
                        "prompt",
                        "too long",
                        "length",
                        "token",
                        "overflow",
                        "400",
                        "limit",
                    )
                )
                is_img_err = "image input is not supported" in err_str or "mmproj" in err_str
                if is_img_err:
                    if hasattr(self.client, "_server_supports_vision"):
                        self.client._server_supports_vision = False
                    if hasattr(self.client, "is_vision"):
                        self.client.is_vision = False
                    if use_memory:
                        context = memory.get_context_for_llm(
                            project_root=self.project_root,
                            vision_supported=False,
                        )
                    else:
                        flat_messages = []
                        for m in messages:
                            c = m.get("content")
                            if isinstance(c, list):
                                parts = [
                                    p.get("text", "")
                                    for p in c
                                    if isinstance(p, dict) and p.get("type") == "text"
                                ]
                                flat_messages.append(
                                    {
                                        "role": m.get("role", "user"),
                                        "content": "\n".join(parts),
                                    }
                                )
                            else:
                                flat_messages.append(m)
                        context = flat_messages
                    response = await self._stream_llm_with_retry(context)
                elif is_ctx_err and use_memory:
                    self._notify_status(
                        "THINKING",
                        {
                            "depth": depth,
                            "status": "context overflow detected — force compacting context",
                        },
                    )
                    self.compact_context(memory=memory, force=True)
                    context = memory.get_context_for_llm(
                        project_root=self.project_root,
                        vision_supported=self._is_vision_supported(),
                    )
                    response = await self._stream_llm_with_retry(context)
                elif self._is_transient_llm_error(err_str):
                    # Timeout / connection stall — retry with backoff instead of
                    # killing the whole solve loop on a transient server blip.
                    response = await self._stream_llm_with_retry(context)
                else:
                    raise llm_err
            action, thinking, content, extra_queries, tool_name, tool_args = (
                self._parse_response(response)
            )

            # ── Debate & Self-Critique Verification Pass ──
            if self.debate_verifier:
                phase_name = "plan" if action in ("thinking", "plan") else phase
                if self.debate_verifier.should_debate(
                    tool_name=tool_name, phase=phase_name
                ):
                    self._notify_status(
                        "CRITIQUING", {"tool_name": tool_name, "action": action}
                    )
                    try:
                        (
                            refined_response,
                            critique_res,
                        ) = await self.debate_verifier.verify_and_refine(
                            proposal=response,
                            task_context=task,
                            tool_name=tool_name,
                            phase=phase_name,
                        )
                        if critique_res.has_flaws and refined_response != response:
                            response = refined_response
                            (
                                action,
                                thinking,
                                content,
                                extra_queries,
                                tool_name,
                                tool_args,
                            ) = self._parse_response(response)
                            self._notify_status(
                                "REFINED",
                                {"tool_name": tool_name, "flaws": critique_res.flaws},
                            )
                    except Exception as verifier_err:
                        print(
                            f"[RLMEngine] Debate verifier bypassed due to error: {verifier_err}"
                        )

            # ── Pre-compute final-answer rejection so Step reflects effective action ──
            rejection_reason = None
            has_failing = False
            pending_tasks: list = []
            executed_tools: int = 0
            if action == "final_answer":
                try:
                    pending_verified = await asyncio.to_thread(
                        self.feedback_loop.verify_pending_changes
                    )
                    has_failing = (not pending_verified) or bool(
                        getattr(self.feedback_loop, "has_failing_tests", False)
                    )
                except Exception:
                    has_failing = bool(
                        getattr(self.feedback_loop, "has_failing_tests", False)
                    )

                is_plan_mode = (getattr(self, "execution_mode", "unified") == "plan" or phase == "plan")
                is_chat_mode = (getattr(self, "execution_mode", "unified") == "chat" or phase == "chat")
                if is_plan_mode or is_chat_mode:
                    has_failing = False

                is_goal_mode = (getattr(self, "execution_mode", "unified") == "goal")
                max_gate_rejections = 10 if is_goal_mode else 6

                if (
                    iteration < MAX_ITERATIONS_PER_LEVEL - 2
                    and getattr(self, "_final_answer_rejections", 0) < max_gate_rejections
                ):
                    # 1. Check for failing post-edit tests
                    if has_failing:
                        fb_ctx = self.feedback_loop.build_feedback_context()
                        rejection_reason = f"❌ [VERIFICATION GATE REJECTION]\nPost-edit tests are currently FAILING. You cannot yield a final answer until tests pass.\n\n{fb_ctx}\n\nDo not yield <FINAL_ANSWER>. Use tools (READ_FILE, EDIT_FILE, GREP, SEARCH_AST, RUN_COMMAND, INSPECT_WEB) to debug and resolve the failure."

                    # 2. Check for pending goal sub-tasks or zero tool executions before final answer
                    else:
                        try:
                            from core.tools.task_helpers import (
                                get_workspace_pending_tasks,
                            )

                            pending_tasks = get_workspace_pending_tasks(
                                self.project_root
                            )
                            executed_tools = sum(
                                1
                                for s in result.steps
                                if s.tool_name or s.action in ("tool", "code")
                            )

                            is_info_query = any(
                                q_kw in task.lower()
                                for q_kw in [
                                    "explain",
                                    "why ",
                                    "what is",
                                    "what are",
                                    "how to",
                                    "how do",
                                    "how does",
                                    "describe",
                                    "tell me",
                                    "difference between",
                                    "help me understand",
                                ]
                            )
                            if phase == "chat" and not any(
                                r_kw in task.lower()
                                for r_kw in ["resume", "continue", "proceed", "carry on", "pick up", "finish"]
                            ):
                                is_info_query = True

                            is_resume_or_action_query = any(
                                kw in task.lower()
                                for kw in [
                                    "add",
                                    "create",
                                    "fix",
                                    "write",
                                    "update",
                                    "modify",
                                    "implement",
                                    "build",
                                    "run",
                                    "delete",
                                    "remove",
                                    "change",
                                    "refactor",
                                    "resume",
                                    "continue",
                                    "proceed",
                                    "carry on",
                                    "pick up",
                                    "finish",
                                    "complete",
                                ]
                            )

                            current_exec_mode = getattr(self, "execution_mode", "unified")
                            plan_file = os.path.join(self.project_root, "implementation_plan.md")
                            plan_exists = os.path.exists(plan_file)
                            plan_written_this_turn = any(
                                (s.tool_name in ("WRITE_FILE", "EDIT_FILE") and "implementation_plan.md" in str(s.tool_args))
                                for s in result.steps
                            )

                            if is_goal_mode or phase == "goal":
                                if not plan_exists and not plan_written_this_turn and not pending_tasks:
                                    rejection_reason = (
                                        "❌ [VERIFICATION GATE REJECTION — MISSING PLAN]\n"
                                        "You are in Goal Mode, but 'implementation_plan.md' has not been created yet and no tasks are tracked.\n"
                                        "You MUST first inspect the workspace (using LIST_DIR, SEARCH_AST, READ_FILE) and create 'implementation_plan.md' with actionable checkbox tasks (`- [ ]`) via WRITE_FILE before yielding <FINAL_ANSWER>."
                                    )
                                elif pending_tasks:
                                    next_t = pending_tasks[0]
                                    task_descs = [f"- {t}" for t in pending_tasks[:3]]
                                    rejection_reason = (
                                        "❌ [VERIFICATION GATE REJECTION — GOAL INCOMPLETE]\n"
                                        f"Task '{next_t}' is still PENDING.\n"
                                        "The following tasks in the implementation plan are still PENDING or IN_PROGRESS:\n"
                                        + "\n".join(task_descs)
                                        + f"\n\nWriting implementation_plan.md is only the planning step. Do not yield <FINAL_ANSWER>. Continue executing tool calls (READ_FILE, EDIT_FILE, WRITE_FILE, SEARCH_AST, RUN_COMMAND) to complete task '{next_t}' and remaining tasks."
                                    )
                                elif executed_tools == 0 and not is_info_query:
                                    rejection_reason = (
                                        "❌ [VERIFICATION GATE REJECTION]\n"
                                        "You yielded <FINAL_ANSWER> without executing any tools. You MUST execute tool calls (e.g. LIST_DIR, SEARCH_AST, READ_FILE, EDIT_FILE, WRITE_FILE, RUN_COMMAND) to inspect the workspace and perform the requested changes before yielding <FINAL_ANSWER>."
                                    )
                            elif current_exec_mode == "plan" or phase == "plan":
                                if not plan_written_this_turn:
                                    if "- [ ]" in content or any(kw in content.lower() for kw in ("proposed changes", "implementation plan", "phase 1")):
                                        try:
                                            clean_save = re.sub(r"</?FINAL_ANSWER>", "", content).strip()
                                            with open(plan_file, "w", encoding="utf-8") as pf:
                                                pf.write(clean_save)
                                            plan_exists = True
                                            plan_written_this_turn = True
                                        except Exception:
                                            pass
                                if not plan_written_this_turn:
                                    rejection_reason = (
                                        "❌ [VERIFICATION GATE REJECTION — PLAN NOT SAVED]\n"
                                        "You are in Plan Mode, but 'implementation_plan.md' has not been written or updated during this turn.\n"
                                        "You MUST first inspect the workspace (using LIST_DIR, SEARCH_AST, READ_FILE) and save 'implementation_plan.md' with brainstormed steps and actionable checkbox tasks (`- [ ]`) via WRITE_FILE before yielding <FINAL_ANSWER>."
                                    )
                            elif current_exec_mode != "chat":
                                if pending_tasks:
                                    next_t = pending_tasks[0]
                                    file_m = re.search(
                                        r"([a-zA-Z0-9_\-\.\/]+\.(?:html|css|js|py|ts|jsx|tsx|json|md|go|rs))",
                                        next_t,
                                    )
                                    target_p = file_m.group(1) if file_m else "index.html"
                                    target_exists = (
                                        os.path.exists(os.path.join(self.project_root, target_p))
                                        if self.project_root
                                        else False
                                    )
                                    if target_exists:
                                        action_template = f'<tool_call>{{"name": "EDIT_FILE", "arguments": {{"path": "{target_p}", "old_text": "...", "new_text": "..."}}}}</tool_call>'
                                    else:
                                        action_template = f'<tool_call>{{"name": "WRITE_FILE", "arguments": {{"path": "{target_p}", "content": "..."}}}}</tool_call>'

                                    rejection_reason = (
                                        "❌ [VERIFICATION GATE REJECTION — TASK INCOMPLETE]\n"
                                        f"Task '{next_t}' is PENDING. Do NOT output conversational text or <FINAL_ANSWER>.\n"
                                        "You MUST output a valid <tool_call> tag right now to implement this task:\n"
                                        f"{action_template}"
                                    )
                                elif executed_tools == 0 and not is_info_query and is_resume_or_action_query:
                                    rejection_reason = (
                                        "❌ [VERIFICATION GATE REJECTION — TOOL CALL REQUIRED]\n"
                                        "You yielded conversational text or <FINAL_ANSWER> without executing any tools.\n"
                                        "You MUST emit a valid <tool_call> tag (e.g. <tool_call>{\"name\": \"READ_FILE\", \"arguments\": {\"path\": \"index.html\"}}</tool_call> or EDIT_FILE/WRITE_FILE/RUN_COMMAND) to perform the requested changes."
                                    )
                        except Exception:
                            pass

            step = Step(
                step_number=iteration + 1,
                depth=depth,
                action="rejected_final_answer" if rejection_reason else action,
                thinking=thinking,
                content=content,
                tool_name=tool_name,
                tool_args=tool_args,
            )

            # Reset thinking counter when model produces a non-thinking action
            if step.action not in ("thinking", "rejected_final_answer"):
                consecutive_thinking = 0

            if action == "final_answer":
                if rejection_reason:
                    self._final_answer_rejections = (
                        getattr(self, "_final_answer_rejections", 0) + 1
                    )
                    if self._final_answer_rejections >= max_gate_rejections:
                        # Mark remaining pending tasks in_progress so the state reflects
                        # active-but-unresolved work, and log the blocker for anti-looping.
                        try:
                            from core.tools.task_helpers import (
                                get_workspace_pending_tasks,
                                mark_task_in_progress,
                            )

                            pending = get_workspace_pending_tasks(self.project_root)
                            if pending:
                                mark_task_in_progress(self.project_root, pending[0])
                            self._notify_tasks_changed({"reason": "gate_escalation"})
                        except Exception:
                            pass
                        if hasattr(self, "memory") and self.memory:
                            try:
                                if hasattr(self.memory, "state") and hasattr(
                                    self.memory.state, "tried_and_failed"
                                ):
                                    blocker = f"FINAL_ANSWER blocked by verification gate after {max_gate_rejections} attempts"
                                    if (
                                        blocker
                                        not in self.memory.state.tried_and_failed
                                    ):
                                        self.memory.state.tried_and_failed.append(
                                            blocker
                                        )
                            except Exception:
                                pass
                        rejection_reason += (
                            "\n\n⚠️ [GATE ESCALATION] This is your final turn before acceptance. "
                            "Emit a tool call now to make progress, or conclude with <FINAL_ANSWER> explaining the exact blocker."
                        )
                    step.result = rejection_reason
                    result.steps.append(step)
                    if self.on_step:
                        self.on_step(step)

                    sanitized_response = response
                    if len(response) > 60 and (
                        "rejection" in response.lower()
                        or "pending task" in response.lower()
                        or "unresolvable" in response.lower()
                        or "known-good" in response.lower()
                        or response.strip().endswith("```json")
                        or response.strip().endswith("```")
                    ):
                        sanitized_response = "[Attempted conversational text without <tool_call>]"

                    if use_memory:
                        memory.add_assistant_message(sanitized_response)
                        memory.add_user_message(rejection_reason)
                    else:
                        messages.append({"role": "assistant", "content": sanitized_response})
                        messages.append({"role": "user", "content": rejection_reason})
                    continue

                # Gate exhausted or passed: if failures are still unresolved, surface
                # them so callers/users never see a clean success on broken work.
                if (
                    getattr(self, "_final_answer_rejections", 0) >= max_gate_rejections
                    and rejection_reason
                ):
                    if not content.startswith("[UNVERIFIED CHANGES]"):
                        content = f"[UNVERIFIED CHANGES]\n{content}"
                    result.gate_bypasses = getattr(self, "_final_answer_rejections", 0)

                if has_failing:
                    content = content + self._build_unresolved_failures_warning()

                quality_score = (0.5 if has_failing else 1.0) * (
                    0.5 if pending_tasks else 1.0
                )
                result.quality_score = quality_score

                step.result = content
                result.steps.append(step)
                if self.on_step:
                    self.on_step(step)
                result.answer = content
                result.total_llm_calls = self._total_llm_calls

                # ---- Summarize Session (Skip in chat/debug/troubleshoot modes to keep local inference responsive) ----
                is_interactive_quick_mode = (
                    getattr(self, "execution_mode", "unified") == "chat"
                    or phase in ("chat", "troubleshoot")
                )
                if not is_interactive_quick_mode:
                    try:
                        import datetime

                        loop = asyncio.get_running_loop()
                        summary_prompt = "Summarize the key actions taken and findings discovered during this task execution in exactly 3 concise bullet points. Focus on what was modified and what was learned."

                        summary_messages = (
                            memory.get_context_for_llm() if use_memory else messages.copy()
                        )
                        if len(summary_messages) > 4:
                            summary_messages = [summary_messages[0]] + summary_messages[-3:]
                        summary_messages.append(
                            {
                                "role": "assistant",
                                "content": f"<FINAL_ANSWER>{content}</FINAL_ANSWER>",
                            }
                        )
                        summary_messages.append({"role": "user", "content": summary_prompt})

                        def _call_summarize():
                            try:
                                return self.client.chat_with_history(
                                    summary_messages, use_grammar=False
                                )
                            except TypeError:
                                return self.client.chat_with_history(summary_messages)

                        async def _background_summarize():
                            try:
                                summary = await loop.run_in_executor(None, _call_summarize)
                                if hasattr(self, "_repair_stop_tokens"):
                                    summary = self._repair_stop_tokens(summary)

                                history_file = os.path.join(
                                    self.project_root, ".torchlight_history.log"
                                )
                                with open(history_file, "a", encoding="utf-8") as f:
                                    f.write(
                                        f"\n--- Session Summary ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---\n"
                                    )
                                    f.write(summary.strip() + "\n")

                                from pathlib import Path
                                from core.memory.persistence import ProjectMemory

                                pm = ProjectMemory(Path(self.project_root))
                                pm.update(
                                    f"Session on {datetime.datetime.now().strftime('%Y-%m-%d')}: {summary.strip()}"
                                )
                                if use_memory and memory:
                                    memory.persist_to_project_memory()
                            except Exception as e:
                                pass

                        asyncio.create_task(_background_summarize())
                    except Exception as e:
                        pass
                # -----------------------------

                self._notify_status("IDLE", {"depth": depth, "status": "complete"})
                if hasattr(self.client, "temperature"):
                    self.client.temperature = initial_temp
                return result

            elif action == "tool":
                # Dynamic Pre-Flight Tool Normalization: Auto-promote EDIT_FILE without old_text
                # on new/empty files or full-file writes (<150 lines). If only partial lines are passed
                # without old_text, reject with a single surgical-edit directive to protect against truncation.
                preflight_err = None
                if tool_name and str(tool_name).upper() == "EDIT_FILE" and isinstance(tool_args, dict):
                    t_path = tool_args.get("path", "")
                    if tool_args.get("old_text"):
                        from core.tools.implementations import _clean_copied_file_text
                        tool_args["old_text"] = _clean_copied_file_text(str(tool_args["old_text"]), t_path)
                    if tool_args.get("new_text"):
                        from core.tools.implementations import _clean_copied_file_text
                        tool_args["new_text"] = _clean_copied_file_text(str(tool_args["new_text"]), t_path)

                    has_old = bool(
                        tool_args.get("old_text")
                        or tool_args.get("diff")
                        or tool_args.get("start_line")
                        or tool_args.get("symbol")
                    )
                    new_c = (
                        tool_args.get("new_text")
                        or tool_args.get("content")
                        or tool_args.get("code")
                        or tool_args.get("text")
                    )
                    if new_c:
                        from core.tools.implementations import _clean_copied_file_text
                        new_c = _clean_copied_file_text(str(new_c), t_path)

                    if not has_old and new_c and t_path:
                        abs_p = os.path.join(self.project_root, t_path) if not os.path.isabs(t_path) else t_path
                        if not os.path.exists(abs_p) or os.path.getsize(abs_p) == 0:
                            tool_name = "WRITE_FILE"
                            tool_args = {"path": t_path, "content": new_c, "force": tool_args.get("force", False)}
                            step.tool_name = tool_name
                            step.tool_args = tool_args
                        else:
                            try:
                                with open(abs_p, "r", encoding="utf-8", errors="replace") as f_chk:
                                    f_lines = [l for l in f_chk.read().splitlines() if l.strip()]
                                new_lines = [l for l in str(new_c).replace("\\n", "\n").splitlines() if l.strip()]
                                
                                # Full-file replacement on small files (<=150 lines): safe to promote
                                if len(f_lines) <= 150 and (len(new_lines) >= int(len(f_lines) * 0.7) or len(f_lines) <= 3):
                                    tool_name = "WRITE_FILE"
                                    tool_args = {"path": t_path, "content": new_c, "force": tool_args.get("force", False)}
                                    step.tool_name = tool_name
                                    step.tool_args = tool_args
                                elif len(new_lines) < len(f_lines):
                                    # Partial content without old_text: reject early to protect from truncation
                                    preflight_err = (
                                        f"⛔ EDIT_FILE rejected: Target file '{t_path}' has {len(f_lines)} lines, but only {len(new_lines)} line(s) "
                                        f"were provided in 'new_text' with no 'old_text' or line numbers.\n"
                                        f"To safely edit without losing existing code, read '{t_path}' first to inspect current content and obtain exact 'old_text' anchors:\n"
                                        f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{t_path}"}}}}</tool_call>'
                                    )
                            except Exception:
                                pass

                    if not preflight_err and not tool_args.get("old_text") and tool_args.get("start_line") and t_path:
                        abs_p = os.path.join(self.project_root, t_path) if not os.path.isabs(t_path) else t_path
                        if os.path.exists(abs_p):
                            try:
                                with open(abs_p, "r", encoding="utf-8", errors="replace") as f_chk:
                                    tot_lines = len(f_chk.read().splitlines())
                                s_line = int(tool_args.get("start_line"))
                                if s_line > tot_lines:
                                    preflight_err = (
                                        f"⛔ EDIT_FILE rejected: start_line {s_line} is out of bounds for '{t_path}' (file has only {tot_lines} lines).\n"
                                        f"Run READ_FILE to inspect current content and line numbers:\n"
                                        f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{t_path}"}}}}</tool_call>'
                                    )
                            except Exception:
                                pass

                if preflight_err:
                    is_valid, err_msg = False, preflight_err
                else:
                    is_valid, err_msg, tool_args = validate_and_normalize_tool_call(
                        tool_name, tool_args or {}
                    )
                step.tool_name = tool_name
                step.tool_args = tool_args

                # ── Duplicate tool call & rate limit detection ─────────────────
                # Mutating tools (WRITE_FILE, EDIT_FILE, SAVE_MEMORY, UPDATE_TASK_GRAPH, RUN_COMMAND)
                # are strictly deduplicated. Read-only tools (READ_FILE, GREP, etc.) are soft rate-limited.
                _READ_ONLY_TOOLS = {
                    "READ_FILE",
                    "READ_SYMBOLS",
                    "LIST_DIR",
                    "GREP",
                    "SEARCH_AST",
                    "INSPECT_WEB",
                    "PLAY_AND_VERIFY_GAME",
                    "WEB_SEARCH",
                    "WEB_FETCH",
                    "DOC_SEARCH",
                    "WEB_VERIFY",
                    "GIT",
                    "FORMAT_CODE",
                    "VERIFY",
                    "ASK_USER",
                }
                tool_name_upper = tool_name.upper() if tool_name else ""
                is_read_only = tool_name_upper in _READ_ONLY_TOOLS

                is_dup, dup_count, hint = trajectory_lock.is_duplicate(
                    tool_name, tool_args or {}, is_read_only=is_read_only
                )
                if not is_valid and not is_dup:
                    trajectory_lock.register(tool_name, tool_args or {})
                    step.result = f"❌ {err_msg}"
                    result.steps.append(step)
                    if self.on_step:
                        self.on_step(step)
                    self._notify_status(
                        "TOOL_DONE", {"tool_name": tool_name, "success": False}
                    )
                    feedback = (
                        build_step_message("tool_error", err_msg)
                        + "\nRe-issue the tool call matching the exact schema."
                    )
                    if use_memory:
                        memory.add_assistant_message(response)
                        memory.add_user_message(feedback)
                    else:
                        messages.append({"role": "assistant", "content": response})
                        messages.append({"role": "user", "content": feedback})
                    continue

                if not is_valid and is_dup:
                    # Duplicate invalid call: fall through to trajectory lock handling below
                    pass
                if is_dup:
                    t_path = (
                        str(
                            tool_args.get("path")
                            or tool_args.get("file")
                            or tool_args.get("target")
                            or tool_args.get("filename")
                            or ""
                        )
                        if isinstance(tool_args, dict)
                        else ""
                    )
                    if t_path and tool_name_upper in ("READ_FILE", "READ", "EDIT_FILE", "EDIT", "WRITE_FILE", "WRITE"):
                        from core.tools.implementations import tool_read_file_impl
                        file_preview = tool_read_file_impl({"path": t_path}, self.project_root)
                        if file_preview and (file_preview.startswith("File not found") or not os.path.exists(os.path.join(self.project_root, t_path))):
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
                                f"⛔ [DUPLICATE {tool_name_upper} BLOCKED]: Repeated call on '{t_path}' halted.\n"
                                f"Here is the CURRENT FILE CONTENT of '{t_path}' directly from disk (lines 1–{tot_lines}):\n\n"
                                f"```\n{preview_body}\n```\n\n"
                                f"Next required action: Inspect the actual lines above and submit your edit using exact old_text:\n"
                                f'<tool_call>{{"name": "EDIT_FILE", "arguments": {{"path": "{t_path}", "old_text": "...", "new_text": "..."}}}}</tool_call>'
                            )

                    step.result = f"(duplicate — already executed {tool_name})\n\n{hint}"
                    result.steps.append(step)
                    if self.on_step:
                        self.on_step(step)
                    self._notify_status(
                        "TOOL_DONE",
                        {
                            "tool_name": tool_name,
                            "success": True,
                            "duplicate": True,
                        },
                    )

                    if (
                        use_memory
                        and hasattr(memory, "state")
                        and memory.state is not None
                    ):
                        if hasattr(memory.state, "tried_and_failed"):
                            entry = f"Duplicate {tool_name_upper} call blocked ({dup_count}x)"
                            if entry not in memory.state.tried_and_failed:
                                memory.state.tried_and_failed.append(entry)

                    if dup_count >= MAX_DUPLICATES:
                        # Force-extract — the model is stuck in a loop
                        forced = f"Tool {tool_name} was executed {dup_count} times with identical or semantically-equivalent arguments. Present whatever you have using <FINAL_ANSWER>."
                        step_forced = Step(
                            step_number=iteration + 2,
                            depth=depth,
                            action="final_answer",
                            thinking=f"(forced after {dup_count} duplicate {tool_name} calls)",
                            content=forced,
                            result=forced,
                        )
                        result.steps.append(step_forced)
                        if self.on_step:
                            self.on_step(step_forced)
                        result.answer = forced
                        result.total_llm_calls = self._total_llm_calls
                        if hasattr(self.client, "temperature"):
                            self.client.temperature = initial_temp
                        return result

                    feedback = hint
                    if use_memory:
                        memory.add_assistant_message(response)
                        memory.add_user_message(feedback)
                    else:
                        messages.append({"role": "assistant", "content": response})
                        messages.append({"role": "user", "content": feedback})
                    continue
                else:
                    trajectory_lock.register(tool_name, tool_args)

                # Tiered approval
                registry = get_tool_registry()
                risk = registry.risk_level_for(tool_name, tool_args)
                if risk in (CONFIRM, REVIEW):
                    self._notify_status(
                        "WAITING_APPROVAL",
                        {"tool_name": tool_name, "risk": risk, "args": tool_args},
                    )
                else:
                    self._notify_status(
                        "TOOL",
                        {"tool_name": tool_name, "args": tool_args, "depth": depth},
                    )

                approved = True
                if risk in (CONFIRM, REVIEW) and self.approval_fn:
                    if asyncio.iscoroutinefunction(self.approval_fn):
                        approved = await self.approval_fn(tool_name, risk, tool_args)
                    else:
                        approved = self.approval_fn(tool_name, risk, tool_args)

                if approved:
                    self._notify_status(
                        "TOOL",
                        {"tool_name": tool_name, "args": tool_args, "depth": depth},
                    )
                    is_plan_session = (
                        getattr(self, "_current_phase", "code") == "plan"
                        or getattr(self, "execution_mode", "") == "plan"
                    )
                    t_name_upper = (tool_name or "").upper().strip()

                    if t_name_upper == "ASK_USER":
                        if getattr(self, "ask_user_fn", None):
                            if asyncio.iscoroutinefunction(self.ask_user_fn):
                                user_resp = await self.ask_user_fn(tool_args)
                            else:
                                user_resp = self.ask_user_fn(tool_args)
                            from core.tools.registry import ToolResult
                            tool_result = ToolResult(
                                success=True,
                                output=str(user_resp),
                            )
                        else:
                            tool_result = await asyncio.to_thread(
                                registry.execute, tool_name, tool_args, self.project_root
                            )
                    elif t_name_upper == "SET_PHASE":
                        current_exec_mode = getattr(self, "execution_mode", "unified")
                        if hasattr(current_exec_mode, "value"):
                            current_exec_mode = current_exec_mode.value
                        current_exec_mode = str(current_exec_mode or "unified").lower().strip()
                        if current_exec_mode in FIXED_EXECUTION_MODES:
                            tool_result = ToolResult(
                                success=False,
                                output=f"Phase switching is disabled in {current_exec_mode.upper()} mode. The agent remains in '{current_exec_mode}' mode.",
                            )
                        else:
                            target_phase = (
                                str(tool_args.get("phase", "code")).lower().strip()
                            )
                            self.lock_phase(target_phase)
                            tool_result = ToolResult(
                                success=True,
                                output=f"Agent phase switched to '{target_phase}' successfully.",
                            )



                    elif is_plan_session and t_name_upper in ("WRITE_FILE", "EDIT_FILE"):
                        target_p = str(tool_args.get("path", "") if isinstance(tool_args, dict) else "").strip()
                        base_p = os.path.basename(target_p).lower()
                        norm_p = os.path.normpath(target_p)
                        is_plan_target = (
                            base_p in ("implementation_plan.md", "plan.md")
                            or norm_p == "implementation_plan.md"
                            or target_p.lower().endswith("implementation_plan.md")
                            or norm_p.startswith(".torchlight")
                        )
                        if not is_plan_target:
                            from core.tools.registry import ToolResult
                            tool_result = ToolResult(
                                success=False,
                                output=(
                                    f"❌ [PLAN MODE GUARD] In Plan Mode, you cannot create or modify application code files like '{target_p}'. "
                                    "Plan Mode is strictly for inspecting the workspace and writing 'implementation_plan.md'. "
                                    "Conclude your turn immediately with <FINAL_ANSWER> to present the plan summary and open questions for user review."
                                ),
                            )
                        else:
                            # Normalize path to implementation_plan.md if targeting the plan
                            if isinstance(tool_args, dict) and base_p in ("implementation_plan.md", "plan.md"):
                                tool_args["path"] = "implementation_plan.md"
                            tool_result = await asyncio.to_thread(
                                registry.execute, tool_name, tool_args, self.project_root
                            )
                            if tool_result.success:
                                tool_result.output += (
                                    "\n\n💡 [PLAN SAVED] 'implementation_plan.md' has been successfully updated on disk. "
                                    "Verify the plan: if any edge cases, dependencies, or tasks are missing, update the plan using EDIT_FILE. "
                                    "When the plan is verified and complete, conclude your turn with <FINAL_ANSWER> summarizing your proposed plan and asking the user for confirmation to switch to Coding Mode to begin implementation."
                                )
                    else:
                        tool_result = await asyncio.to_thread(
                            registry.execute, tool_name, tool_args, self.project_root
                        )
                    step.result = tool_result.output
                    consecutive_thinking = 0
                    if hasattr(self.client, "temperature"):
                        self.client.temperature = initial_temp
                    if tool_name_upper not in _READ_ONLY_TOOLS:
                        trajectory_lock.record_output(tool_name, tool_args, tool_result.output)
                    result.steps.append(step)
                    if self.on_step:
                        self.on_step(step)
                    self._notify_status(
                        "TOOL_DONE",
                        {"tool_name": tool_name, "success": tool_result.success},
                    )

                    # Pin file content after READ_FILE so it survives compression
                    if use_memory and tool_result.success and tool_name:
                        tname_upper = tool_name.upper()
                        if "READ_FILE" in tname_upper:
                            fpath = tool_args.get("path", "")
                            if fpath:
                                if hasattr(memory, "record_file_read"):
                                    memory.record_file_read(fpath)
                                if tool_result.output:
                                    memory.pin_file(fpath, tool_result.output)
                        elif "EDIT_FILE" in tname_upper or "WRITE_FILE" in tname_upper:
                            fpath = tool_args.get("path") or tool_args.get("file", "")
                            if fpath:
                                added = 0
                                deleted = 0
                                diff_m = re.search(
                                    r"\(\+(\d+),\s*[-–](\d+)\)",
                                    tool_result.output or "",
                                )
                                if diff_m:
                                    added = int(diff_m.group(1))
                                    deleted = int(diff_m.group(2))
                                new_content = None
                                full_p = (
                                    os.path.join(self.project_root, fpath)
                                    if not os.path.isabs(fpath)
                                    else fpath
                                )
                                if os.path.exists(full_p):
                                    try:
                                        with open(full_p, "r", encoding="utf-8") as _f:
                                            new_content = _f.read()
                                    except Exception:
                                        pass
                                if hasattr(memory, "record_file_modified"):
                                    memory.record_file_modified(
                                        fpath,
                                        added=added,
                                        deleted=deleted,
                                        new_content=new_content,
                                    )
                                if hasattr(memory, "refresh_pin"):
                                    memory.refresh_pin(fpath, self.project_root)

                    msg_type = "tool_result" if tool_result.success else "tool_error"
                    feedback = build_step_message(msg_type, tool_result.output)

                    # Execution feedback: auto-run tests or web inspector after code changes
                    if (
                        self.feedback_loop
                        and tool_name
                        and tool_name.upper()
                        in ("EDIT_FILE", "WRITE_FILE", "RUN_COMMAND")
                    ):
                        await asyncio.to_thread(
                            self.feedback_loop.on_tool_executed,
                            tool_name.upper(),
                            tool_args,
                            tool_result.output,
                        )
                        fb_ctx = await asyncio.to_thread(
                            self.feedback_loop.build_feedback_context
                        )
                        if fb_ctx:
                            feedback += f"\n\n[AUTOMATIC POST-EDIT EXECUTION FEEDBACK]\n{fb_ctx}"

                    if tool_result.success:
                        fpath = (
                            tool_args.get("path") or tool_args.get("file", "")
                        ).lower()
                        if (
                            "implementation_plan" in fpath
                            or "tasks.md" in fpath
                            or "goal_spec" in fpath
                        ):
                            if getattr(self, "execution_mode", "unified") in ("goal", "unified"):
                                self._current_phase = "code"
                            try:
                                from core.tools.task_helpers import sync_workspace_tasks

                                sync_workspace_tasks(self.project_root)
                            except Exception:
                                pass
                            self._notify_tasks_changed(
                                {"tool_name": tool_name, "path": fpath}
                            )
                            if getattr(self, "execution_mode", "unified") in ("goal", "unified"):
                                feedback += "\n\n🚀 Implementation plan created/updated successfully! Switched to SURGICAL CODING phase. Proceed immediately to execute open tasks (- [ ]) using tools (WRITE_FILE, EDIT_FILE, RUN_COMMAND, etc.)."
                        else:
                            # Auto-sync task completion if written file matches an open task item.
                            # Completion is gated on verification (no failing tests); otherwise
                            # the task is marked in_progress so status is realtime, not late.
                            try:
                                from core.tools.task_helpers import (
                                    auto_mark_task_completed_by_file,
                                    auto_mark_task_completed_by_command,
                                )

                                if fpath:
                                    has_failing = bool(
                                        self.feedback_loop
                                        and getattr(
                                            self.feedback_loop,
                                            "has_failing_tests",
                                            False,
                                        )
                                    )
                                    auto_mark_task_completed_by_file(
                                        self.project_root,
                                        fpath,
                                        verified=not has_failing,
                                    )
                                elif (
                                    tool_name.upper() == "RUN_COMMAND"
                                    and tool_result.success
                                ):
                                    cmd_str = str(
                                        tool_args.get("cmd")
                                        or tool_args.get("command")
                                        or ""
                                    )
                                    if cmd_str:
                                        auto_mark_task_completed_by_command(
                                            self.project_root,
                                            cmd_str,
                                            return_code=0,
                                        )
                                self._notify_tasks_changed(
                                    {"tool_name": tool_name, "path": fpath}
                                )
                            except Exception:
                                pass

                            try:
                                from core.tools.task_helpers import (
                                    get_workspace_pending_tasks,
                                )

                                p_tasks = get_workspace_pending_tasks(
                                    self.project_root
                                )
                            except Exception:
                                p_tasks = []

                            if p_tasks and getattr(self, "execution_mode", "unified") != "chat":
                                next_task = p_tasks[0]
                                file_m = re.search(
                                    r"([a-zA-Z0-9_\-\.\/]+\.(?:html|css|js|py|ts|jsx|tsx|json|md|go|rs))",
                                    next_task,
                                )
                                target_p = file_m.group(1) if file_m else ""
                                target_exists = (
                                    os.path.exists(os.path.join(self.project_root, target_p))
                                    if self.project_root and target_p
                                    else False
                                )
                                if target_exists:
                                    action_tpl = f'<tool_call>{{"name": "EDIT_FILE", "arguments": {{"path": "{target_p}", "old_text": "...", "new_text": "..."}}}}</tool_call>'
                                elif target_p:
                                    action_tpl = f'<tool_call>{{"name": "WRITE_FILE", "arguments": {{"path": "{target_p}", "content": "..."}}}}</tool_call>'
                                else:
                                    action_tpl = '<tool_call>{"name": "...", "arguments": {...}}</tool_call>'

                                feedback += (
                                    f"\n🎯 NEXT PENDING TASK: {next_task}\n"
                                    f"Do NOT yield <FINAL_ANSWER>. Immediately emit the next tool call:\n"
                                    f"{action_tpl}"
                                )
                            elif not p_tasks:
                                feedback += "\nAll tasks in the plan are completed! You may now conclude with <FINAL_ANSWER>."
                            else:
                                feedback += "\nContinue with next step, or if done, use <FINAL_ANSWER> tags."
                    elif tool_name and "EDIT_FILE" in tool_name.upper():
                        # Inject READ_FILE nudge — small models often skip the read step
                        target_path = tool_args.get("path", "the file")
                        feedback += (
                            f"\nCRITICAL: READ_FILE('{target_path}') FIRST, then copy the exact lines "
                            f"you want to replace as old_text. Do NOT paraphrase or reconstruct from memory."
                        )

                else:
                    self._notify_status("TOOL_DENIED", {"tool_name": tool_name})
                    step.result = "⚠ User denied execution"
                    result.steps.append(step)
                    if self.on_step:
                        self.on_step(step)
                    feedback = build_step_message(
                        "tool_denied", f"{tool_name} was denied."
                    )

                images_to_attach = None
                if tool_name and tool_result.success:
                    t_upper = tool_name.upper()
                    if t_upper == "VIEW_IMAGE":
                        img_p = (
                            tool_args.get("path")
                            or tool_args.get("file")
                            or tool_args.get("image")
                        )
                        if img_p:
                            images_to_attach = [img_p]
                    elif t_upper == "INSPECT_WEB":
                        m_shot = re.search(
                            r"\*\*Screenshot Saved:\*\*\s*`([^`]+)`",
                            tool_result.output or "",
                        )
                        if m_shot:
                            images_to_attach = [m_shot.group(1)]

                if use_memory:
                    memory.add_assistant_message(response)
                    memory.add_user_message(feedback, images=images_to_attach)
                else:
                    messages.append({"role": "assistant", "content": response})
                    if images_to_attach:
                        from core.utils.image_utils import (
                            format_openai_vision_content,
                        )

                        messages.append(
                            {
                                "role": "user",
                                "content": format_openai_vision_content(
                                    feedback,
                                    images_to_attach,
                                    project_root=self.project_root,
                                ),
                            }
                        )
                    else:
                        messages.append({"role": "user", "content": feedback})

            elif action == "code":
                # Validate content is actually executable code / syntax valid
                import ast

                is_valid = False
                try:
                    ast.parse(content)
                    is_valid = True
                except SyntaxError:
                    if re.search(
                        r"\b(?:def|class|import|from|return|if|for|while|const|let|var|function|val|var|fn)\b",
                        content,
                    ):
                        is_valid = True

                if not is_valid:
                    step.action = "thinking"
                    step.result = "(classified as reasoning — not executable code)"
                    result.steps.append(step)
                    if self.on_step:
                        self.on_step(step)
                    feedback = "Your response contained text inside code tags that was not valid code syntax. If you are planning or reasoning, continue with your next tool call."
                    if use_memory:
                        memory.add_assistant_message(response)
                        memory.add_user_message(feedback)
                    else:
                        messages.append({"role": "assistant", "content": response})
                        messages.append({"role": "user", "content": feedback})
                    continue

                # Check for duplicate REPL execution
                if content in _executed_code_payloads:
                    step.result = "ERROR: Duplicate code execution block. You already executed this exact code on a previous turn and it failed. Do NOT repeat the exact same code block. Adjust your logic/syntax, or present your findings with <FINAL_ANSWER>."
                    result.steps.append(step)
                    if self.on_step:
                        self.on_step(step)
                    feedback = "⚠️ You already executed this exact code block and it failed. Do NOT repeat it. Modify the code to address the error."
                    if hasattr(self.client, "temperature"):
                        self.client.temperature = 0.4
                    if use_memory:
                        memory.add_assistant_message(response)
                        memory.add_user_message(feedback)
                    else:
                        messages.append({"role": "assistant", "content": response})
                        messages.append({"role": "user", "content": feedback})
                    continue

                # Check if code modifies files or executes system commands
                modifies_files = bool(
                    re.search(
                        r"\b(open\s*\(.*['\"][wa\+]|write_text|write_bytes|os\.remove|os\.unlink|"
                        r"os\.mkdir|os\.makedirs|os\.rename|shutil\.|subprocess\.|os\.system)\b",
                        content,
                        re.IGNORECASE,
                    )
                )
                if modifies_files:
                    self._notify_status(
                        "WAITING_APPROVAL",
                        {"tool_name": "CODE_FILE_WRITE", "risk": CONFIRM},
                    )
                else:
                    self._notify_status(
                        "TOOL", {"tool_name": "REPL_CODE", "depth": depth}
                    )

                approved = True
                if modifies_files and self.approval_fn:
                    tool_args = {"preview": content[:300]}
                    if asyncio.iscoroutinefunction(self.approval_fn):
                        approved = await self.approval_fn(
                            "CODE_FILE_WRITE", CONFIRM, tool_args
                        )
                    else:
                        approved = self.approval_fn(
                            "CODE_FILE_WRITE", CONFIRM, tool_args
                        )

                if approved:
                    self._notify_status(
                        "TOOL", {"tool_name": "REPL_CODE", "depth": depth}
                    )
                    async with sandbox_lock:
                        exec_result = await asyncio.to_thread(
                            self.sandbox.execute, content, cwd=self.project_root
                        )
                else:
                    self._notify_status("TOOL_DENIED", {"tool_name": "REPL_CODE"})
                    exec_result = {
                        "success": False,
                        "error": "Code execution denied by user",
                        "stdout": "",
                        "stderr": "",
                    }

                consecutive_thinking = 0
                if exec_result["success"]:
                    consecutive_code_errors = 0
                    _executed_code_payloads.add(content)
                    _last_tool_key = None
                    if hasattr(self.client, "temperature"):
                        self.client.temperature = initial_temp
                    output = exec_result["stdout"].strip()
                    if not output:
                        output = "(Code executed successfully, no output)"

                    MAX_OUTPUT_LENGTH = 2000
                    if len(output) > MAX_OUTPUT_LENGTH:
                        output = output[:MAX_OUTPUT_LENGTH] + "\n... [Output truncated]"

                    step.result = output
                    last_code_output = output
                    feedback = build_step_message("code_result", output)
                    # Hint the model to wrap up after successful computation
                    feedback += "\nIf this answers the user's question, present the result using <FINAL_ANSWER> tags now."
                    self._notify_status(
                        "TOOL_DONE", {"tool_name": "REPL_CODE", "success": True}
                    )
                else:
                    consecutive_code_errors += 1
                    _executed_code_payloads.add(content)
                    error_msg = exec_result["error"] or "Unknown error"
                    if exec_result["stderr"]:
                        error_msg += f"\nstderr: {exec_result['stderr']}"
                    step.result = f"ERROR: {error_msg}"
                    last_code_output = None
                    feedback = build_step_message("code_error", error_msg)

                    # Eagerly update tried_and_failed memory state
                    if use_memory and memory:
                        tf_entry = f"Failed REPL execution: {error_msg[:120]}"
                        if tf_entry not in memory.state.tried_and_failed:
                            memory.state.tried_and_failed.append(tf_entry)

                    # Raise temperature to break logic rut
                    if hasattr(self.client, "temperature"):
                        self.client.temperature = 0.4

                    if consecutive_code_errors >= 3:
                        forced = f"Code execution failed {consecutive_code_errors} consecutive times: {error_msg}. Present your final findings using <FINAL_ANSWER>."
                        step_forced = Step(
                            step_number=iteration + 2,
                            depth=depth,
                            action="final_answer",
                            thinking=f"(forced after {consecutive_code_errors} consecutive code errors)",
                            content=forced,
                            result=forced,
                        )
                        result.steps.append(step_forced)
                        if self.on_step:
                            self.on_step(step_forced)
                        result.answer = forced
                        result.total_llm_calls = self._total_llm_calls
                        if hasattr(self.client, "temperature"):
                            self.client.temperature = initial_temp
                        return result
                    elif consecutive_code_errors >= 2:
                        feedback += "\n⚠️ Code execution has failed 2 times consecutively. Do not retry the same code. Change approach or return <FINAL_ANSWER>."
                    self._notify_status(
                        "TOOL_DONE", {"tool_name": "REPL_CODE", "success": False}
                    )

                result.steps.append(step)
                if self.on_step:
                    self.on_step(step)

                if use_memory:
                    memory.add_assistant_message(response)
                    memory.add_user_message(feedback)
                else:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": feedback})

            elif action == "sub_queries":
                if depth >= self.max_depth:
                    step.result = "DEPTH LIMIT REACHED"
                    result.steps.append(step)
                    if self.on_step:
                        self.on_step(step)

                    if use_memory:
                        memory.add_assistant_message(response)
                        memory.add_user_message(build_step_message("depth_limit", ""))
                    else:
                        messages.append({"role": "assistant", "content": response})
                        messages.append(
                            {
                                "role": "user",
                                "content": build_step_message("depth_limit", ""),
                            }
                        )
                else:
                    queries = [content] + extra_queries
                    step.content = " | ".join(queries)
                    self._notify_status(
                        "SUBAGENT", {"depth": depth + 1, "queries_count": len(queries)}
                    )

                    # On 8GB devices with 1 llama-server slot, run sequentially
                    # to avoid memory thrashing. On 16GB+ run in parallel.
                    if IS_8GB_DEVICE:
                        sub_results = []
                        for q in queries:
                            sub_res = await self.solve_async(q, depth=depth + 1)
                            sub_results.append(sub_res)
                    else:
                        tasks = [self.solve_async(q, depth=depth + 1) for q in queries]
                        sub_results = await asyncio.gather(*tasks)

                    combined_answers = []
                    for idx, sub_res in enumerate(sub_results):
                        result.steps.extend(sub_res.steps)
                        combined_answers.append(
                            f"Sub-query [{queries[idx]}]: {sub_res.answer}"
                        )

                    aggregated_answer = "\n".join(combined_answers)
                    step.result = aggregated_answer
                    result.steps.append(step)
                    if self.on_step:
                        self.on_step(step)

                    if use_memory:
                        memory.add_assistant_message(response)
                        memory.add_user_message(
                            build_step_message("sub_query_result", aggregated_answer)
                        )
                    else:
                        messages.append({"role": "assistant", "content": response})
                        messages.append(
                            {
                                "role": "user",
                                "content": build_step_message(
                                    "sub_query_result", aggregated_answer
                                ),
                            }
                        )

            else:
                consecutive_thinking += 1
                step.result = (
                    f"(No action tag detected — thinking loop {consecutive_thinking})"
                )
                result.steps.append(step)
                if self.on_step:
                    self.on_step(step)

                sanitized_resp = response
                if len(response) > 60 and (
                    "rejection" in response.lower()
                    or "pending task" in response.lower()
                    or response.strip().endswith("```json")
                    or response.strip().endswith("```")
                ):
                    sanitized_resp = "[Attempted reasoning without <tool_call>]"

                if use_memory:
                    memory.add_assistant_message(sanitized_resp)
                else:
                    messages.append({"role": "assistant", "content": sanitized_resp})

                # Progressive escalation to break out of reasoning loops
                if consecutive_thinking >= MAX_THINKING_LOOPS:
                    # Force-extract: build a clean, user-friendly final answer
                    # instead of dumping garbled rejection echoes.
                    forced = ""
                    if last_code_output:
                        forced = f"Based on computation: {last_code_output}"
                    else:
                        # Build a meaningful summary from pending tasks
                        try:
                            from core.tools.task_helpers import get_workspace_pending_tasks
                            _fp = get_workspace_pending_tasks(self.project_root) if self.project_root else []
                            if _fp:
                                forced = (
                                    f"The model was unable to emit a tool call after {MAX_THINKING_LOOPS} attempts.\n"
                                    f"Next pending task: **{_fp[0]}**\n\n"
                                    "Try sending a more specific instruction like:\n"
                                    f'"Write the code for {_fp[0]}" or "Read implementation_plan.md"'
                                )
                            else:
                                forced = (
                                    f"The model was unable to emit a tool call after {MAX_THINKING_LOOPS} attempts.\n"
                                    "Try a more specific instruction (e.g. \"read implementation_plan.md\") "
                                    "or check that implementation_plan.md exists in the workspace."
                                )
                        except Exception:
                            forced = (
                                f"Turn completed after {MAX_THINKING_LOOPS} reasoning loops. "
                                "The model could not produce a valid tool call. "
                                "Try a more specific instruction."
                            )
                    step_forced = Step(
                        step_number=iteration + 2,
                        depth=depth,
                        action="final_answer",
                        thinking=f"(auto-extracted after {MAX_THINKING_LOOPS} thinking loops)",
                        content=forced,
                        result=forced,
                    )
                    result.steps.append(step_forced)
                    if self.on_step:
                        self.on_step(step_forced)
                    result.answer = forced
                    result.total_llm_calls = self._total_llm_calls
                    if hasattr(self.client, "temperature"):
                        self.client.temperature = initial_temp
                    return result
                else:
                    try:
                        from core.tools.task_helpers import get_workspace_pending_tasks
                        pending = get_workspace_pending_tasks(self.project_root) if self.project_root else []
                    except Exception:
                        pending = []

                    if pending:
                        next_t = pending[0]
                        file_m = re.search(
                            r"([a-zA-Z0-9_\-\.\/]+\.(?:html|css|js|py|ts|jsx|tsx|json|md|go|rs))",
                            next_t,
                        )
                        target_p = file_m.group(1) if file_m else "index.html"
                        target_exists = (
                            os.path.exists(os.path.join(self.project_root, target_p))
                            if self.project_root
                            else False
                        )
                        if target_exists:
                            tool_tmpl = f'<tool_call>{{"name": "EDIT_FILE", "arguments": {{"path": "{target_p}", "old_text": "...", "new_text": "..."}}}}</tool_call>'
                        else:
                            tool_tmpl = f'<tool_call>{{"name": "WRITE_FILE", "arguments": {{"path": "{target_p}", "content": "..."}}}}</tool_call>'
                        nudge = (
                            f"Do NOT output conversational text. You MUST emit a valid <tool_call> tag right now to execute task '{next_t}':\n"
                            f"{tool_tmpl}"
                        )
                    else:
                        nudge = (
                            "Do NOT output conversational text. You MUST emit a valid <tool_call> tag (e.g. <tool_call>{\"name\": \"READ_FILE\", \"arguments\": {\"path\": \"index.html\"}}</tool_call> or EDIT_FILE/WRITE_FILE/RUN_COMMAND)."
                        )

                if use_memory:
                    memory.add_user_message(nudge)
                else:
                    messages.append({"role": "user", "content": nudge})

            # Auto-detect phase and update inference params (for unified/goal modes)
            if self.execution_mode in ("unified", "goal"):
                self._update_params(task, response)

        # Iteration limit reached
        if use_memory:
            memory.add_user_message(build_step_message("iteration_limit", ""))
            context = memory.get_context_for_llm()
        else:
            messages.append(
                {"role": "user", "content": build_step_message("iteration_limit", "")}
            )
            context = messages

        self._total_llm_calls += 1
        response = await self._stream_llm_with_retry(context)
        _, _, final_content, _, _, _ = self._parse_response(response)

        if not final_content:
            final_content = response

        # Surface any unresolved test failures even when the loop was forced to end.
        final_content = final_content + self._build_unresolved_failures_warning()

        step = Step(
            step_number=MAX_ITERATIONS_PER_LEVEL + 1,
            depth=depth,
            action="final_answer",
            thinking="(forced)",
            content=final_content,
            result=final_content,
        )
        result.steps.append(step)
        if self.on_step:
            self.on_step(step)

        result.answer = final_content
        result.total_llm_calls = self._total_llm_calls
        if hasattr(self.client, "temperature"):
            self.client.temperature = initial_temp
        return result



__all__ = [
    "RLMEngineOptimized",
    "Step",
    "SolveResult",
    "_looks_like_prose_or_outline",
    "_looks_like_full_file",
    "_trim_trailing_prose",
]
