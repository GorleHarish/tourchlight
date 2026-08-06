import re
import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field
from rlm_optimized.config import (
    MAX_RECURSION_DEPTH,
    MAX_ITERATIONS_PER_LEVEL,
    MAX_THINKING_LOOPS,
    IS_8GB_DEVICE,
)
from rlm_optimized.repl_sandbox import REPLSandbox
from core.prompts.system import get_phase_system_prompt
from rlm_optimized.prompts import build_step_message
from core.tools.registry import get_tool_registry
from core.tools.classification import CONFIRM, REVIEW
from rlm_optimized.tool_schemas import validate_and_normalize_tool_call

try:
    from core.memory.token_counter import get_token_counter
except ImportError:
    pass

try:
    from core.compression.summarizer import ConversationSummarizer
    from core.memory.models import Message, MessageRole
    from core.memory.manager import TieredMemory, MemoryConfig
    from core.memory.persistence import ProjectMemory, ensure_project_initialized

    _summarizer = ConversationSummarizer()
except ImportError:
    _summarizer = None
    TieredMemory = None
    MemoryConfig = None
    ensure_project_initialized = None

try:
    from core.debate.verifier import DebateVerifier
except ImportError:
    DebateVerifier = None


@dataclass
class Step:
    step_number: int
    depth: int
    action: str  # "code", "tool", "sub_queries", "final_answer", "thinking"
    thinking: str
    content: str
    result: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None


@dataclass
class SolveResult:
    answer: str
    steps: list[Step] = field(default_factory=list)
    depth: int = 0
    total_llm_calls: int = 0
    quality_score: float = 1.0
    gate_bypasses: int = 0


from core.tools.parser import (
    tolerant_json_repair as _tolerant_json_repair,
    extract_balanced_json_object as _extract_balanced_json_object,
    clean_and_parse_json as _clean_and_parse_json,
    parse_tool_call_payload,
    repair_unclosed_tool_call_tag,
    strip_interleaved_prose,
    unwrap_double_encoded_json,
)
from core.tools.dedup import TrajectoryLock


def _looks_like_prose_or_outline(content: str) -> bool:
    """Heuristic gate for inline code interception (step 6b of _parse_response).

    Returns True when a bare ``` block is likely a plan/outline/prose dump
    rather than actual code. Small models frequently emit their step-by-step
    plan inside a ``` block during plan/code phases; auto-WRITE_FILE'ing that
    prose verbatim produced the "gibberish file" bug (e.g. inline_code_output_N.txt).
    """
    text = (content or "").strip()
    if not text:
        return True
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return True
    joined = text

    code_tokens = re.findall(
        r"\b(?:def|class|function|const|let|var|import|from|return|print|echo|"
        r"SELECT|INSERT|UPDATE|DELETE|CREATE)\b",
        joined,
        re.IGNORECASE,
    )
    code_punct = len(re.findall(r"[{}();\[\]=<>+\-*/\"'`]", joined))

    # Outline markers: "# 1. ...", "1. ...", "## Step ...", "- [ ] ..."
    outline_lines = re.findall(
        r"^\s*(?:#{1,6}\s*)?(?:\d+[\.\)]\s+\S|[-*]\s*\[\s*\]\s+\S)",
        joined,
        re.MULTILINE,
    )
    # Plan lead-ins at line starts (step-by-step prose).
    has_plan_leadin = bool(
        re.search(
            r"^\s*(?:first|next|then|finally|step\s*\d+|approach|overview|summary|"
            r"goal|objective|we\s+will|i\s+will|let'?s)\b(?=[\s\:\,])",
            joined,
            re.IGNORECASE | re.MULTILINE,
        )
    )
    # Sentence-like majority: wordy lines ending in sentence punctuation.
    sentence_like = sum(
        1
        for ln in lines
        if len(ln) >= 16
        and re.search(r"[.!?]\s*$", ln)
        and len(re.findall(r"[{}();\[\]=<>+\-*/\"'`]", ln)) <= 2
    )

    # 1. Strong code signals (tokens + structural punctuation) -> definitely code.
    if code_tokens and code_punct >= 6 and not outline_lines:
        return False

    # 2. Outlined plan beats weak code signals ("# 1. ...", "## Step ...").
    if outline_lines and code_punct < 12 and len(code_tokens) <= 1:
        return True

    # 3. Plan lead-ins / sentence-style prose with no code tokens.
    if not code_tokens and (has_plan_leadin or sentence_like or outline_lines):
        return True

    # 4. No code tokens and almost no code punctuation -> prose.
    return bool(not code_tokens and code_punct < 6)


def _trim_trailing_prose(content: str, path: str = "") -> str:
    """Trim prose a model appended after the file body when </WRITE_FILE> was
    consumed as a stop token (the regex's `$` alternative swallows trailing text).

    Only applied to code targets to avoid corrupting legitimately prose-based
    files (README.md, plan docs, notes, etc.)."""
    ext = os.path.splitext(path)[1].lower() if path else ""
    code_ext = ext in (
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".mjs",
        ".cjs",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".java",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".sh",
        ".bash",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".sql",
        ".html",
        ".css",
        ".scss",
        ".vue",
        ".svelte",
    )
    if not code_ext:
        return content
    lines = content.rstrip("\n").splitlines()
    cut = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        ln = lines[i].strip()
        if not ln:
            break
        if (
            len(ln) >= 20
            and ln[-1] in ".!?"
            and len(re.findall(r"[{}();\[\]=<>+*/\\]", ln)) <= 2
            and not re.search(
                r"^\s*(?:def|class|function|const|let|var|import|return|print|echo)\b",
                ln,
            )
        ):
            cut = i
        else:
            break
    if cut < len(lines):
        trimmed = "\n".join(lines[:cut])
        if trimmed.strip():
            return trimmed
    return content


class RLMEngineOptimized:
    def __init__(
        self,
        client=None,
        on_step: Optional[Callable[[Step], None]] = None,
        max_depth: int = MAX_RECURSION_DEPTH,
        project_root: Optional[str] = None,
        approval_fn: Optional[Callable[[str, str, dict], bool]] = None,
        on_token: Optional[Callable[[str], None]] = None,
        on_status_change: Optional[Callable[[dict], None]] = None,
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
        self.max_depth = max_depth
        self.project_root = project_root or os.getcwd()
        if ensure_project_initialized:
            ensure_project_initialized(self.project_root)
        self.sandbox = REPLSandbox(project_root=self.project_root)
        self._total_llm_calls = 0
        self.sandbox.set_llm_query_fn(self._sandbox_llm_query)
        self.approval_fn = approval_fn  # fn(tool_name, risk, args) -> bool or async
        self._inline_code_counter = 0
        self.execution_mode = execution_mode or "unified"

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

    def _sandbox_llm_query(self, prompt: str) -> str:
        return self.client.query(prompt)

    # Stop tokens used by the LLM — the server strips these from output,
    # so we need to re-append them for the parser to match properly.
    _STOP_TAG_PAIRS = [
        ("<WRITE_FILE", "</WRITE_FILE>"),
        ("<TOOL", "</TOOL>"),
        ("<CODE>", "</CODE>"),
        ("<FINAL_ANSWER>", "</FINAL_ANSWER>"),
        ("<SUB_QUERY>", "</SUB_QUERY>"),
        ("<action>", "</action>"),
    ]

    def _repair_stop_tokens(self, text: str) -> str:
        """Re-append closing tags that were consumed as stop tokens by llama-server."""
        for open_tag, close_tag in self._STOP_TAG_PAIRS:
            # Check if text has the opening tag but NOT the closing tag
            if (
                open_tag.lower() in text.lower()
                and close_tag.lower() not in text.lower()
            ):
                text = text.rstrip() + close_tag
                break  # Only one action per response
        return text

    async def _stream_llm(self, messages: list[dict]) -> str:
        """Stream LLM response token-by-token cleanly without thread deadlocks."""
        loop = asyncio.get_running_loop()
        if hasattr(self.client, "stream_chat_with_history"):
            queue = asyncio.Queue()
            sentinel = object()

            def _worker():
                try:
                    for chunk in self.client.stream_chat_with_history(messages):
                        loop.call_soon_threadsafe(queue.put_nowait, chunk)
                except Exception as e:
                    loop.call_soon_threadsafe(queue.put_nowait, e)
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, sentinel)

            loop.run_in_executor(None, _worker)

            chunks = []
            while True:
                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=60.0)
                except asyncio.TimeoutError:
                    # LLM server stopped responding mid-stream — abort
                    break
                if isinstance(chunk, Exception):
                    raise chunk
                if chunk is sentinel:
                    break
                chunks.append(chunk)
                if self.on_token:
                    try:
                        self.on_token(chunk)
                    except Exception:
                        pass
                else:
                    print(chunk, end="", flush=True)

            if not self.on_token:
                print()
            response = "".join(chunks)
            return self._repair_stop_tokens(response)
        else:
            raw = await loop.run_in_executor(
                None, self.client.chat_with_history, messages
            )
            return self._repair_stop_tokens(raw)

    def compact_context(self, memory=None, force: bool = True) -> tuple[int, int, int]:
        """Manually compact context memory and return (before, after, freed)."""
        target_mem = memory or getattr(self, "_memory", None)
        if not target_mem:
            return 0, 0, 0
        before = getattr(target_mem, "total_tokens", 0)
        summarizer_fn = _summarizer.simple_summarize if _summarizer else None
        target_mem.compress_recent(
            summarizer_fn=summarizer_fn, preserve_first=2, force=force
        )
        after = getattr(target_mem, "total_tokens", 0)
        return before, after, max(0, before - after)

    async def solve_async(
        self, task: str, depth: int = 0, phase: Optional[str] = None
    ) -> SolveResult:
        result = SolveResult(answer="", depth=depth)
        self._total_llm_calls = 0
        self._final_answer_rejections = 0

        # Determine effective phase: explicit param > execution_mode > "code" default
        if phase is None:
            if self.execution_mode == "chat":
                phase = "chat"
            elif self.execution_mode == "goal":
                phase = "code"
            else:
                phase = "code"

        self._current_phase = phase

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

            self._memory.add_user_message(task)
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
                        summarizer_fn=summarizer_fn, preserve_first=2
                    )
                context = memory.get_context_for_llm(project_root=self.project_root)
            else:
                context = messages

            self._notify_status(
                "THINKING", {"depth": depth, "iteration": iteration + 1}
            )
            response = await self._stream_llm(context)
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

                if (
                    iteration < MAX_ITERATIONS_PER_LEVEL - 2
                    and getattr(self, "_final_answer_rejections", 0) < 2
                ):
                    # 1. Check for failing post-edit tests
                    if has_failing:
                        fb_ctx = self.feedback_loop.build_feedback_context()
                        rejection_reason = f"❌ [VERIFICATION GATE REJECTION]\nPost-edit tests are currently FAILING. You cannot yield a final answer until tests pass.\n\n{fb_ctx}\n\nDo not yield <FINAL_ANSWER>. Use tools (READ_FILE, EDIT_FILE, GREP, SEARCH_AST, RUN_COMMAND, INSPECT_WEB) to debug and resolve the failure."

                    # 2. Check for pending goal sub-tasks in workspace task files (implementation_plan.md, tasks.md, goal_spec.json)
                    else:
                        try:
                            from core.tools.task_helpers import (
                                get_workspace_pending_tasks,
                            )

                            pending_tasks = get_workspace_pending_tasks(
                                self.project_root
                            )
                            if pending_tasks:
                                task_descs = [f"- {t}" for t in pending_tasks[:3]]
                                rejection_reason = (
                                    "❌ [VERIFICATION GATE REJECTION]\n"
                                    "The following tasks in the implementation plan are still PENDING or IN_PROGRESS:\n"
                                    + "\n".join(task_descs)
                                    + "\n\nWriting implementation_plan.md is only the planning step. Continue executing tool calls to complete remaining tasks before yielding <FINAL_ANSWER>."
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
                    if self._final_answer_rejections >= 2:
                        rejection_reason += (
                            "\n\n⚠️ [GATE ESCALATION] This is your FINAL rejection for this prompt. "
                            "If you yield a final answer again it will be accepted but marked UNRESOLVED. "
                            "Prefer abandoning broken edits (revert to a known-good state) and reporting "
                            "the blocker explicitly rather than repeating the same fix attempt."
                        )
                    step.result = rejection_reason
                    result.steps.append(step)
                    if self.on_step:
                        self.on_step(step)
                    if use_memory:
                        memory.add_assistant_message(response)
                        memory.add_user_message(rejection_reason)
                    else:
                        messages.append({"role": "assistant", "content": response})
                        messages.append({"role": "user", "content": rejection_reason})
                    continue

                # Gate exhausted or passed: if failures are still unresolved, surface
                # them so callers/users never see a clean success on broken work.
                if getattr(self, "_final_answer_rejections", 0) >= 2 and rejection_reason:
                    if not content.startswith("[UNVERIFIED CHANGES]"):
                        content = f"[UNVERIFIED CHANGES]\n{content}"
                    result.gate_bypasses = getattr(self, "_final_answer_rejections", 0)

                if has_failing:
                    content = content + self._build_unresolved_failures_warning()

                quality_score = (0.5 if has_failing else 1.0) * (0.5 if pending_tasks else 1.0)
                result.quality_score = quality_score

                step.result = content
                result.steps.append(step)
                if self.on_step:
                    self.on_step(step)
                result.answer = content
                result.total_llm_calls = self._total_llm_calls

                # ---- Summarize Session ----
                try:
                    import datetime

                    loop = asyncio.get_running_loop()
                    self._notify_status(
                        "THINKING", {"depth": depth, "status": "summarizing task"}
                    )
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
                            print(f"Session summarization skipped or failed: {e}")

                    asyncio.create_task(_background_summarize())
                except Exception as e:
                    print(f"Session summarization skipped or failed: {e}")
                # -----------------------------

                self._notify_status("IDLE", {"depth": depth, "status": "complete"})
                if hasattr(self.client, "temperature"):
                    self.client.temperature = initial_temp
                return result

            elif action == "tool":
                is_valid, err_msg, tool_args = validate_and_normalize_tool_call(
                    tool_name, tool_args or {}
                )
                if not is_valid:
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

                # ── Duplicate tool call detection ──────────────────────
                # Read-only tools are exempt — re-reading a file is always
                # legitimate (verify edits, context compression, refresh memory).
                _READ_ONLY_TOOLS = {
                    "READ_FILE",
                    "READ_SYMBOLS",
                    "LIST_DIR",
                    "GREP",
                    "SEARCH_AST",
                    "INSPECT_WEB",
                    "UPDATE_TASK_GRAPH",
                    "WEB_SEARCH",
                    "WEB_FETCH",
                    "DOC_SEARCH",
                    "WEB_VERIFY",
                    "GIT",
                    "SAVE_MEMORY",
                    "FORMAT_CODE",
                    "VERIFY",
                    "ASK_USER",
                }
                tool_name_upper = tool_name.upper() if tool_name else ""

                if tool_name_upper not in _READ_ONLY_TOOLS:
                    is_dup, dup_count, hint = trajectory_lock.is_duplicate(tool_name, tool_args)
                    if is_dup:
                        step.result = f"(duplicate — already executed {tool_name})"
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

                        if use_memory and hasattr(memory, "state") and memory.state is not None:
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
                    tool_result = await asyncio.to_thread(
                        registry.execute, tool_name, tool_args, self.project_root
                    )
                    step.result = tool_result.output
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
                            if fpath and tool_result.output:
                                memory.pin_file(fpath, tool_result.output)
                        elif "EDIT_FILE" in tname_upper or "WRITE_FILE" in tname_upper:
                            fpath = tool_args.get("path") or tool_args.get("file", "")
                            if fpath and hasattr(memory, "refresh_pin"):
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

                if use_memory:
                    memory.add_assistant_message(response)
                    memory.add_user_message(feedback)
                else:
                    messages.append({"role": "assistant", "content": response})
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

                if exec_result["success"]:
                    consecutive_code_errors = 0
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

                if use_memory:
                    memory.add_assistant_message(response)
                else:
                    messages.append({"role": "assistant", "content": response})

                # Progressive escalation to break out of reasoning loops
                if consecutive_thinking >= MAX_THINKING_LOOPS:
                    # Force-extract: treat the entire response as the answer
                    forced = response.strip()
                    if last_code_output:
                        forced = f"Based on computation: {last_code_output}"
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
                elif consecutive_thinking >= 4:
                    nudge = (
                        "You MUST respond with exactly one action tag now. "
                        "If you have completed your work, wrap your response in <FINAL_ANSWER>your answer</FINAL_ANSWER>. "
                        "If you need to perform an action, use <TOOL> or <CODE>."
                    )
                else:
                    nudge = "Please continue with an action using <TOOL>, <CODE>, <SUB_QUERY>, or <FINAL_ANSWER>."

                if use_memory:
                    memory.add_user_message(nudge)
                else:
                    messages.append({"role": "user", "content": nudge})

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
        response = await self._stream_llm(context)
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

    def _build_unresolved_failures_warning(self) -> str:
        """Build an explicit warning attached to an accepted final answer when the
        verification gate was bypassed but test state is still failing/unverified.
        Returns an empty string when there is nothing unresolved to surface."""
        parts = []
        try:
            if getattr(self.feedback_loop, "has_failing_tests", False):
                detail = ""
                try:
                    err = self.feedback_loop.get_test_failure_error()
                    if err is not None and err.surgical_traceback:
                        detail = f"\n{err.surgical_traceback[:400]}"
                except Exception:
                    pass
                parts.append(
                    "[UNRESOLVED TEST FAILURES] This final answer was accepted with "
                    f"post-edit tests still failing or unverified.{detail}"
                )
        except Exception:
            pass
        try:
            if getattr(self.feedback_loop, "_files_modified_since_test", None):
                parts.append(
                    "[UNVERIFIED CHANGES] Recent edits have not been verified by passing tests."
                )
        except Exception:
            pass
        if not parts:
            return ""
        return "\n\n⚠️ " + "\n⚠️ ".join(parts)

    def _parse_response(
        self, response: str
    ) -> tuple[str, str, str, list[str], Optional[str], Optional[dict]]:
        """Parse the LLM response for action tags.
        Returns: (action, thinking, content, extra_queries, tool_name, tool_args)
        """
        # 0. Extract explicit <think>...</think> or <thought>...</thought> or unwrapped reasoning prefixes
        explicit_thinking = ""
        think_match = re.search(
            r"<(?:think|thought|thinking|reasoning)>(.*?)(?:</(?:think|thought|thinking|reasoning)>|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if think_match:
            explicit_thinking = think_match.group(1).strip()
        else:
            prefix_match = re.match(
                r"^\s*(?:thought\s+|\[(?:thought|thinking|reasoning|plan)\][:\s]*|(?:thought|thinking|reasoning|plan)(?:\s+process)?\s*[\n\r:]\s*|(?:chain\s*of\s*thought)[:\s]+)(.*)",
                response,
                re.DOTALL | re.IGNORECASE,
            )
            if prefix_match:
                explicit_thinking = prefix_match.group(1).strip()

        def _get_thinking(tag_start_pos: int) -> str:
            pre_tag_text = response[:tag_start_pos].strip()
            cleaned_pre = re.sub(
                r"<(?:think|thought|thinking|reasoning)>[\s\S]*?(?:</(?:think|thought|thinking|reasoning)>|$)",
                "",
                pre_tag_text,
                flags=re.IGNORECASE,
            ).strip()
            cleaned_pre = re.sub(
                r"^\s*(?:thought\s+|\[(?:thought|thinking|reasoning|plan)\][:\s]*|(?:thought|thinking|reasoning|plan)(?:\s+process)?\s*[\n\r:]\s*|(?:chain\s*of\s*thought)[:\s]+)",
                "",
                cleaned_pre,
                flags=re.IGNORECASE,
            ).strip()
            if (
                explicit_thinking
                and cleaned_pre
                and cleaned_pre not in explicit_thinking
            ):
                return f"{explicit_thinking}\n\n{cleaned_pre}"
            return explicit_thinking or cleaned_pre

        # 1. Check for <tool_call>...</tool_call> (standard tag for Qwen / Llama models)
        tool_call_match = re.search(
            r"<tool_call>\s*(.*?)(?:</tool_call>|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if tool_call_match and tool_call_match.group(1).strip():
            raw_payload = tool_call_match.group(1).strip()
            thinking = _get_thinking(tool_call_match.start())
            parsed_json = _clean_and_parse_json(raw_payload)

            tool_name = (
                parsed_json.get("name")
                or parsed_json.get("tool")
                or parsed_json.get("action")
            )
            tool_args = (
                parsed_json.get("arguments") or parsed_json.get("args") or parsed_json
            )

            if tool_name:
                t_name = str(tool_name).upper()
                if isinstance(tool_args, str):
                    tool_args = _clean_and_parse_json(tool_args)
                return (
                    "tool",
                    thinking,
                    f"{t_name}({json.dumps(tool_args)})",
                    [],
                    t_name,
                    tool_args,
                )

        # 2. Check for <TOOL name="...">JSON</TOOL> or <tool name="...">JSON</tool>
        tool_match = re.search(
            r'<TOOL\s+name=["\'](\w+)["\']>\s*(.*?)(?:</TOOL>|$)',
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if tool_match and tool_match.group(2).strip():
            tool_name = tool_match.group(1).upper()
            raw_args = tool_match.group(2).strip()
            thinking = _get_thinking(tool_match.start())
            tool_args = _clean_and_parse_json(raw_args)
            return (
                "tool",
                thinking,
                f"{tool_name}({raw_args})",
                [],
                tool_name,
                tool_args,
            )

        # 2b. Check for <action>NAME {JSON}</action> — fallback shape when grammar is off
        action_tag_match = re.search(
            r"<action>\s*(\w+)\s*(.*?)(?:</action>|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if action_tag_match and action_tag_match.group(1).strip():
            tool_name = action_tag_match.group(1).upper()
            thinking = _get_thinking(action_tag_match.start())
            # Extract the first balanced JSON object from inside the tag so we
            # never lose args to an unclosed <action> tag or grab trailing prose.
            json_obj = _extract_balanced_json_object(action_tag_match.group(0))
            if json_obj:
                tool_args = _clean_and_parse_json(json_obj)
            else:
                tool_args = {}
            return (
                "tool",
                thinking,
                f"{tool_name}({json.dumps(tool_args)})",
                [],
                tool_name,
                tool_args,
            )

        # 3. Check for <WRITE_FILE path="...">content</WRITE_FILE>
        write_tag_match = re.search(
            r'<WRITE_FILE\s+path=["\']([^"\']+)["\']>\s*(.*?)(?:</WRITE_FILE>|$)',
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if write_tag_match:
            path_val = write_tag_match.group(1).strip()
            content_val = write_tag_match.group(2)
            # When the closing tag was consumed as a stop token the `$`
            # alternative may have swallowed trailing prose — trim it for code
            # targets only.
            if not re.search(r"</WRITE_FILE>", write_tag_match.group(0), re.IGNORECASE):
                content_val = _trim_trailing_prose(content_val, path_val)
            thinking = _get_thinking(write_tag_match.start())
            return (
                "tool",
                thinking,
                f"WRITE_FILE({path_val})",
                [],
                "WRITE_FILE",
                {"path": path_val, "content": content_val},
            )

        # 3b. Check for JSON array output (fallback for Qwen JSON outputs)
        json_array_match = re.search(
            r'(?:```(?:json)?\s*)?(\[\s*\{\s*["\'](?:tool_name|name|action|tool)["\'].*?\}\s*\])(?:\s*```)?',
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if json_array_match:
            try:
                first_tool = _clean_and_parse_json(json_array_match.group(1))
                if first_tool and isinstance(first_tool, dict):
                    t_name = (
                        first_tool.get("tool_name")
                        or first_tool.get("name")
                        or first_tool.get("action")
                        or first_tool.get("tool")
                        or ""
                    ).upper()
                    if t_name:
                        t_args = (
                            first_tool.get("params")
                            or first_tool.get("arguments")
                            or first_tool.get("args")
                        )
                        if t_args is None:
                            t_args = dict(first_tool)
                            t_args.pop("tool_name", None)
                            t_args.pop("name", None)
                            t_args.pop("action", None)
                            t_args.pop("tool", None)

                        thinking = _get_thinking(json_array_match.start())
                        return (
                            "tool",
                            thinking,
                            f"{t_name}({json.dumps(t_args)})",
                            [],
                            t_name,
                            t_args,
                        )
            except Exception:
                pass

        # 4. Check for <CODE>...</CODE>
        code_match = re.search(
            r"<CODE(?:\s+[^>]*)?>(.*?)(?:</CODE>|$)", response, re.DOTALL
        )
        if not code_match:
            code_match = re.search(
                r"(?<!`)<CODE(?:\s+[^>]*)?>(.*?)</(?:CODE|code)>",
                response,
                re.DOTALL | re.IGNORECASE,
            )

        if code_match and code_match.group(1).strip():
            content = code_match.group(1).strip()
            # Clean up any surrounding markdown code fences (e.g. ```python ... ```) inside <CODE>
            content = re.sub(
                r"^\s*```(?:python|py)?\s*\n?", "", content, flags=re.IGNORECASE
            )
            content = re.sub(r"\n?\s*```\s*$", "", content).strip()

            thinking = _get_thinking(code_match.start())

            # Check if code block specifies a target file writing intent (e.g. # file: path/foo.py or # filename: foo.py)
            file_match = re.search(
                r"^(?:#|//)\s*(?:file|filename|filepath|path)\s*:\s*([^\n\r]+)",
                content,
                re.IGNORECASE,
            )
            if file_match:
                target_path = file_match.group(1).strip()
                # Remove header line from content
                cleaned_content = re.sub(
                    r"^(?:#|//)\s*(?:file|filename|filepath|path)\s*:\s*[^\n\r]+\n?",
                    "",
                    content,
                ).strip()
                return (
                    "tool",
                    thinking,
                    f"WRITE_FILE({target_path})",
                    [],
                    "WRITE_FILE",
                    {"path": target_path, "content": cleaned_content},
                )

            # Validate if content actually looks like executable code or code file declaration
            import ast

            is_valid_code = False
            try:
                ast.parse(content)
                is_valid_code = True
            except SyntaxError:
                words = content.split()
                prose_indicators = sum(
                    1
                    for w in words
                    if w.lower().strip("`'\",.")
                    in {
                        "the",
                        "is",
                        "are",
                        "was",
                        "were",
                        "will",
                        "would",
                        "should",
                        "could",
                        "have",
                        "has",
                        "had",
                        "been",
                        "being",
                        "this",
                        "that",
                        "with",
                        "from",
                        "into",
                        "since",
                        "because",
                        "however",
                        "therefore",
                        "i",
                        "we",
                        "they",
                        "he",
                        "she",
                        "it",
                        "my",
                        "your",
                        "executing",
                        "here",
                        "generating",
                        "result",
                        "file",
                        "asking",
                    }
                )
                is_prose = (
                    len(words) > 3 and (prose_indicators / max(len(words), 1)) > 0.1
                )
                if not is_prose and re.search(
                    r"\b(?:def|class|import|from|return|const|let|function|fn)\b",
                    content,
                ):
                    is_valid_code = True

            if is_valid_code:
                # In chat/troubleshoot mode, treat <CODE> blocks as
                # thinking (displayed) rather than executable code.
                current_phase = getattr(self, "_current_phase", "code")
                if current_phase in ("chat", "troubleshoot"):
                    thinking_text = (
                        f"{thinking}\n\n{content}".strip() if thinking else content
                    )
                    return ("thinking", thinking_text, "", [], None, None)
                return ("code", thinking, content, [], None, None)
            else:
                # Content inside <CODE> tag is natural language/prose, reclassify as thinking
                thinking_text = (
                    f"{thinking}\n\n{content}".strip() if thinking else content
                )
                return ("thinking", thinking_text, "", [], None, None)

        # 5. Check for <SUB_QUERY>...</SUB_QUERY>
        sub_query_matches = re.findall(
            r"<SUB_QUERY>(.*?)(?:</SUB_QUERY>|$)", response, re.DOTALL | re.IGNORECASE
        )
        if sub_query_matches:
            first_tag_pos = response.lower().find("<sub_query>")
            thinking = (
                _get_thinking(first_tag_pos)
                if first_tag_pos != -1
                else explicit_thinking
            )
            return (
                "sub_queries",
                thinking,
                sub_query_matches[0].strip(),
                [q.strip() for q in sub_query_matches[1:]],
                None,
                None,
            )

        # 6. Check for <FINAL_ANSWER>...</FINAL_ANSWER>
        final_match = re.search(
            r"<FINAL_ANSWER>(.*?)(?:</FINAL_ANSWER>|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if final_match:
            raw_content = final_match.group(1).strip()
            pre_text = response[: final_match.start()].strip()

            is_template = bool(
                re.match(
                    r"^(?:your|the)?\s*(?:complete\s+)?answer$", raw_content.lower()
                )
            )
            is_mid_sentence = bool(
                re.search(
                    r"\b(?:use|using|with|by|in|written|into|output|tag|provide|format|wrap)\s*[`'\"]*$",
                    pre_text,
                    re.IGNORECASE,
                )
            )

            if not is_template and not is_mid_sentence and raw_content:
                thinking = _get_thinking(final_match.start())
                return ("final_answer", thinking, raw_content, [], None, None)

        # 6b. Inline code interception (Auto-WRITE_FILE for bare markdown blocks)
        # Skip in chat/troubleshoot/plan mode — code blocks there are for
        # display/reference or planning, not file creation.
        bare_code_match = re.search(
            r"```(?:\w+)?\n?(.*?)```", response, re.DOTALL | re.IGNORECASE
        )
        if bare_code_match and not re.search(
            r"<(?:TOOL|CODE|SUB_QUERY|WRITE_FILE|action)\b", response, re.IGNORECASE
        ):
            current_phase = getattr(self, "_current_phase", "code")
            if current_phase not in ("chat", "troubleshoot", "plan"):
                content = bare_code_match.group(1).strip()
                thinking = _get_thinking(bare_code_match.start())

                # Try to extract file path from comment inside block
                file_match = re.search(
                    r"^(?:#|//|/\*|<!--)\s*(?:file|filename|filepath|path)\s*[:=]?\s*([^\n\r]+)",
                    content,
                    re.IGNORECASE,
                )

                # Guard: bare blocks that look like a plan/outline/prose dump must
                # NOT be auto-written (gibberish file bug). An explicit
                # `# file: ...` header signals a deliberate write and overrides.
                intercept = True
                if not file_match and _looks_like_prose_or_outline(content):
                    intercept = False

                if intercept:
                    if not file_match:
                        # Try to extract from text preceding the block
                        pre_text = response[: bare_code_match.start()].strip()
                        file_match_pre = re.search(
                            r"(?:for|file|filename|filepath|path|in)\s*[:=]?\s*`?([\w\.\-/]+\.\w+)`?\s*$",
                            pre_text,
                            re.IGNORECASE,
                        )
                        if file_match_pre:
                            target_path = file_match_pre.group(1).strip()
                        else:
                            self._inline_code_counter += 1
                            target_path = (
                                f"inline_code_output_{self._inline_code_counter}.txt"
                            )
                    else:
                        target_path = (
                            file_match.group(1)
                            .replace("*/", "")
                            .replace("-->", "")
                            .strip()
                        )
                        # Remove header line from content
                        content = re.sub(
                            r"^(?:#|//|/\*|<!--)\s*(?:file|filename|filepath|path)\s*[:=]?\s*[^\n\r]+\n?",
                            "",
                            content,
                            flags=re.IGNORECASE,
                        ).strip()

                    return (
                        "tool",
                        thinking,
                        f"WRITE_FILE({target_path})",
                        [],
                        "WRITE_FILE",
                        {"path": target_path, "content": content},
                    )

        # 7. Direct answer / non-tool response handling
        cleaned_body = re.sub(
            r"<(?:think|thought|thinking|reasoning)>[\s\S]*?(?:</(?:think|thought|thinking|reasoning)>|$)",
            "",
            response,
            flags=re.IGNORECASE,
        ).strip()
        has_unclosed_tool_attempt = bool(
            re.search(
                r"<(?:TOOL|CODE|SUB_QUERY|WRITE_FILE|action)\b",
                cleaned_body,
                re.IGNORECASE,
            )
        )

        reasoning_prefix_match = re.match(
            r"^\s*(?:system\s+thought[:\s]*|thought\s+|\[(?:thought|thinking|reasoning|plan)\][:\s]*|(?:thought|thinking|reasoning|plan)(?:\s+process)?\s*[\n\r:]\s*|(?:chain\s*of\s*thought)[:\s]+)",
            response.strip(),
            re.IGNORECASE,
        )

        execution_intent = bool(
            re.search(
                r"\b(?:I\s+will|let\s*me|I\s+need\s+to|going\s+to|will\s+start\s+by|create|write|inspect)\s+.*?\b(?:LIST_DIR|READ_FILE|EDIT_FILE|WRITE_FILE|GREP|SEARCH_AST|RUN_COMMAND|INSPECT_WEB|WEB_SEARCH|WEB_FETCH)\b",
                cleaned_body,
                re.IGNORECASE,
            )
        )

        plan_action_start = bool(
            re.match(
                r"^(?:1[\.\s]|step\s*1|first,|I\s+will\s+start|I\s+need\s+to\s+first)\s*(?:I\s+will|let\s*me|use|call|run|create|write|read|inspect|list|search|find|edit|check|verify)",
                cleaned_body,
                re.IGNORECASE,
            )
        )

        has_plan_file = bool(
            re.search(r"implementation_plan\.md", cleaned_body, re.IGNORECASE)
        )

        is_planning_cot = (
            bool(reasoning_prefix_match)
            or execution_intent
            or plan_action_start
            or has_plan_file
        )

        if is_planning_cot and not has_unclosed_tool_attempt:
            combined_thinking = (
                f"{explicit_thinking}\n\n{cleaned_body}".strip()
                if explicit_thinking
                else cleaned_body
            )
            if reasoning_prefix_match:
                combined_thinking = re.sub(
                    r"^\s*(?:system\s+thought[:\s]*|thought\s+|\[(?:thought|thinking|reasoning|plan)\][:\s]*|(?:thought|thinking|reasoning|plan)(?:\s+process)?\s*[\n\r:]\s*|(?:chain\s*of\s*thought)[:\s]+)",
                    "",
                    combined_thinking,
                    flags=re.IGNORECASE,
                ).strip()
            return ("thinking", combined_thinking or cleaned_body, "", [], None, None)

        if not has_unclosed_tool_attempt and cleaned_body:
            if explicit_thinking:
                return ("final_answer", explicit_thinking, cleaned_body, [], None, None)

            final_cleaned = re.sub(
                r"</?FINAL_ANSWER>", "", cleaned_body, flags=re.IGNORECASE
            ).strip()
            if final_cleaned:
                return ("final_answer", "", final_cleaned, [], None, None)

        return ("thinking", response.strip(), "", [], None, None)
