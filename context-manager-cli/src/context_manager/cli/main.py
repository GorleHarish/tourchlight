"""Context Manager CLI — Interactive terminal session with intelligent context management."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

# ── Import from core/ shared library with local fallback ────────────────────
try:
    from core.api.base import InferenceParams, PRESETS
    from core.api.lmstudio import LMStudioClient
    from core.memory.manager import TieredMemory, MemoryConfig
    from core.memory.models import ExecutionMode, FIXED_EXECUTION_MODES, Message, MessageRole
    from core.memory.token_counter import get_token_counter
    from core.compression.compactor import VerbatimCompactor, CompressionConfig
    from core.compression.summarizer import ConversationSummarizer
    from core.memory.persistence import ProjectMemory, ensure_project_initialized
    from core.flashlight import SymbolIndex, Flashlight
    from core.execution.feedback_loop import ExecutionFeedbackLoop
    from core.tools.classification import AUTO, CONFIRM, REVIEW, classify_command
    from core.tools.implementations import set_ctx_window as _set_ctx_window
    from core.prompts.system import DEFAULT_SYSTEM_PROMPT, get_phase_system_prompt, sanitize_assistant_text
    from core.debate.verifier import DebateVerifier
    from core.execution.autonomous_harness import AutonomousHarness
    from core.tools.dedup import TrajectoryLock, get_alternate_trajectory_hint
except ImportError:
    from ..api.lmstudio import LMStudioClient, InferenceParams, PRESETS
    from ..memory.manager import TieredMemory, MemoryConfig
    from ..memory.models import ExecutionMode, FIXED_EXECUTION_MODES, Message, MessageRole

    from ..memory.token_counter import get_token_counter
    from ..compression.compactor import VerbatimCompactor, CompressionConfig
    from ..compression.summarizer import ConversationSummarizer
    from ..memory.persistence import ProjectMemory, ensure_project_initialized
    from ..flashlight import SymbolIndex, Flashlight
    from ..execution.feedback_loop import ExecutionFeedbackLoop
    from ..tools.core import AUTO, CONFIRM, REVIEW, classify_command, set_ctx_window as _set_ctx_window
    try:
        from core.prompts.system import DEFAULT_SYSTEM_PROMPT, get_phase_system_prompt, sanitize_assistant_text
    except ImportError:
        from ..prompts import DEFAULT_SYSTEM_PROMPT
        def get_phase_system_prompt(phase="code"):
            return DEFAULT_SYSTEM_PROMPT
        def sanitize_assistant_text(text):
            return text
    try:
        from core.debate.verifier import DebateVerifier
    except ImportError:
        DebateVerifier = None
    try:
        from core.execution.autonomous_harness import AutonomousHarness
    except ImportError:
        AutonomousHarness = None
    try:
        from core.tools.dedup import TrajectoryLock, get_alternate_trajectory_hint
    except ImportError:
        TrajectoryLock = None
        get_alternate_trajectory_hint = None

from ..skills.unified import create_unified_registry
from ..tools.core import get_core_registry

from context_manager.cli import dashboard
from context_manager.cli.dashboard import ContextDashboard, ActionTracker
from context_manager.cli.session import (
    CommandDispatcherMixin,
    FlashlightMixin,
    StatsPanelMixin,
    ToolExecutorMixin,
    _beam_budget,
    _risk_tier,
    _tool_kind,
    _tool_label,
)
from context_manager.cli.commands import (
    register_chat_commands,
    register_utility_commands,
)

console = Console()
_core_reg = get_core_registry()
_SMALL_CTX = 5000
app = typer.Typer(help="Context Manager CLI - Chat with LLMs while managing context")

class StreamingChatSession(
    FlashlightMixin,
    ToolExecutorMixin,
    StatsPanelMixin,
    CommandDispatcherMixin,
):
    """Interactive streaming chat session with tiered memory and flashlight context."""

    def __init__(
        self,
        base_url: str,
        model: Optional[str],
        max_tokens: int,
        stream: bool = True,
        project_dir: Optional[str] = None,
        mode: str = "chat",
        repeat_penalty: Optional[float] = None,
    ):
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if not base_url:
            raise ValueError("base_url cannot be empty")

        self.mode = (mode or "chat").lower().strip()
        self.client = LMStudioClient(base_url=base_url, model=model)

        self._project_dir = Path(project_dir).resolve() if project_dir else Path.cwd()
        self.project_path = self._project_dir
        self.project_memory = ProjectMemory(self.project_path)

        self.tokenizer = get_token_counter()
        self.skills = create_unified_registry()
        self.max_tokens = max_tokens

        # Calculate initial overhead
        overhead = self._calculate_metadata_overhead()
        self.memory_config = MemoryConfig.auto_tune(max_tokens, metadata_overhead=overhead)

        self.memory = TieredMemory(
            config=self.memory_config,
            tokenizer=self.tokenizer,
            project_memory=self.project_memory,
            llm_client=self.client,  # enables LLM-powered state extraction at compression time
        )
        if hasattr(self.memory.state, "execution_mode"):
            self.memory.state.execution_mode = (
                ExecutionMode.CODE
                if self.mode == "code"
                else ExecutionMode.GOAL
                if self.mode == "goal"
                else ExecutionMode.PLAN
                if self.mode == "plan"
                else ExecutionMode.UNIFIED
                if self.mode == "unified"
                else ExecutionMode.CHAT
            )

        self.compactor = VerbatimCompactor(CompressionConfig())
        self.summarizer = ConversationSummarizer()
        self.stream_enabled = stream
        self._response_tokens = 0
        self._start_time = 0

        # Execution feedback loop - auto-run tests after code changes
        self._feedback_loop = ExecutionFeedbackLoop(
            project_root=self.project_path,
            enabled=True,
            auto_run=True,
            timeout=60,
        )

        self._index: Optional[SymbolIndex] = None
        self._light: Optional[Flashlight] = None

        # Pre-compute beam limits for this model's context size
        self._beam_files, self._beam_lines = _beam_budget(max_tokens)

        # Tell the tool layer the model's context window so READ_FILE scales correctly
        _set_ctx_window(max_tokens)

        # ── Inference parameter state ───────────────────────────────────────────────
        # _params holds the currently active InferenceParams for every call.
        # _params_locked = True means the user pinned a preset via /params <name>;
        # auto phase-detection is disabled and _params won't change mid-session.
        self._params: InferenceParams = InferenceParams.for_chat()
        if repeat_penalty is not None:
            self._params.repeat_penalty = repeat_penalty
            self._params.repetition_penalty = repeat_penalty
        self._params_locked: bool = False
        self._current_phase: str = "chat"
        self._phase_lock: Optional[str] = None
        self._phase_lock_turns: int = 0

    def _event_lock_phase(self, event: str, data: str = "") -> None:
        """Lock phase based on concrete execution events."""
        if event == "tool_error":
            self._phase_lock = "troubleshoot"
            self._phase_lock_turns = 2
        elif event == "file_edit":
            self._phase_lock = "code"
            self._phase_lock_turns = 2
        elif event == "user_explicit":
            self._phase_lock = None
            self._phase_lock_turns = 0

    def _repair_stop_tokens(self, text: str) -> str:
        """Re-append closing tags and unclosed JSON braces that were consumed as stop tokens or truncated by LLM."""
        if not text:
            return ""
        for open_tag, close_tag in self._STOP_TAG_PAIRS:
            if open_tag.lower() in text.lower() and close_tag.lower() not in text.lower():
                text = text.rstrip() + close_tag
                break
        open_braces = text.count("{") - text.count("}")
        if open_braces > 0:
            text = text.rstrip() + "}" * open_braces
        return text

    def _calculate_metadata_overhead(self) -> int:
        """Estimate tokens consumed by system prompt, tools, and flashlight beam."""
        try:
            # Re-calculate system content like _build_messages does
            small = self.max_tokens <= _SMALL_CTX
            if small:
                cli_suffix = "\nTool syntax: bare call...\n"
                system_content = DEFAULT_SYSTEM_PROMPT + cli_suffix
            else:
                tool_instruct = self.skills.get_all_prompts(max_tokens=self.max_tokens)
                cli_suffix = "\n\n## Tool Calling Syntax (CLI)...\n"
                system_content = DEFAULT_SYSTEM_PROMPT + cli_suffix + tool_instruct

            base_tokens = self.tokenizer.count(system_content)

            # Beam overhead (rough estimate based on budget)
            if self.max_tokens <= _SMALL_CTX:
                overhead = base_tokens + 600
            elif self.max_tokens <= 9000:
                overhead = base_tokens + 1500
            else:
                overhead = base_tokens + 3000
            return overhead
        except Exception:
            return 1500

    # ── Flashlight helpers ────────────────────────────────────────────────────

    # Stop Token & Truncation Recovery — re-append closing tags consumed as
    # stop tokens or truncated by the LLM.  See _repair_stop_tokens().
    _STOP_TAG_PAIRS = [
        ("<WRITE_FILE", "</WRITE_FILE>"),
        ("<TOOL", "</TOOL>"),
        ("<CODE>", "</CODE>"),
        ("<FINAL_ANSWER>", "</FINAL_ANSWER>"),
        ("<action>", "</action>"),
        ("<tool_call>", "</tool_call>"),
    ]

    # Signals checked against lowercased (user_input + last_response).
    # Priority on match: troubleshoot > plan > code > chat.
    _PLAN_SIGNALS = (
        "<plan>",
        "<thought>",
        "plan",
        "planning",
        "brainstorm",
        "brainstorming",
        "implementation plan",
        "steps to implement",
        "generate plan",
        "make a plan",
        "create a plan",
        "plan mode",
        "let me plan",
        "step by step",
        "here is my plan",
        "i will:",
        "steps:",
        "roadmap",
        "break down tasks",
        "break down the tasks",
        "decompose tasks",
    )
    _CODE_SIGNALS = (
        "write_file",
        "edit_file",
        "run_command",
        "<tool_call>",
        "```python",
        "```kotlin",
        "```java",
        "```javascript",
        "```typescript",
        "```swift",
        "```go",
        "```rust",
        "def ",
        "class ",
        "function ",
        "create ",
        "write ",
        "modify ",
        "fix ",
        "add ",
        "edit ",
        "build ",
        "implement ",
        "update ",
        "generate ",
        "refactor ",
    )
    _TROUBLESHOOT_SIGNALS = (
        "error:",
        "exception:",
        "traceback",
        "failed",
        "not working",
        "stack trace",
        "segfault",
        "crash",
        "adb ",
        "gradle ",
        "anr",
        "nullpointer",
        "outofmemory",
        "build fail",
        "why is",
        "why does",
        "what went wrong",
        "debug",
    )

    def _get_active_execution_mode(self) -> str:
        """Resolve and normalize active execution mode from self.mode or memory state."""
        mode_val = getattr(self, "mode", None)
        if hasattr(mode_val, "value"):
            mode_val = mode_val.value
        mode_str = str(mode_val or "").lower().strip()

        mem_state = getattr(getattr(self, "memory", None), "state", None)
        if mem_state and getattr(mem_state, "execution_mode", None) is not None:
            mem_mode = mem_state.execution_mode
            if hasattr(mem_mode, "value"):
                mem_mode = mem_mode.value
            mem_mode_str = str(mem_mode or "").lower().strip()
            if mem_mode_str and (not mode_str or mode_str == "unified"):
                return mem_mode_str

        return mode_str or "unified"


    def _detect_phase(self, user_input: str, last_response: str = "") -> str:
        """
        Infer the current agent phase from user input and the last model response.
        Returns one of: "plan" | "code" | "troubleshoot" | "chat".
        """
        m = self._get_active_execution_mode()
        if m in FIXED_EXECUTION_MODES:
            return m
        if m == "goal":
            return "goal"

        # Transient phase lock (if any)
        if self._phase_lock:
            if self._phase_lock_turns > 0:
                self._phase_lock_turns -= 1
                return self._phase_lock
            self._phase_lock = None

        # Dynamic phase detection for unified mode (inspect user_input only)
        inp_lower = user_input.lower()
        if any(s in inp_lower for s in self._TROUBLESHOOT_SIGNALS):
            return "troubleshoot"
        if any(s in inp_lower for s in self._PLAN_SIGNALS):
            return "plan"
        if any(
            s in inp_lower
            for s in (
                "resume",
                "continue",
                "proceed",
                "carry on",
                "pick up",
                "finish task",
            )
        ):
            return "code"
        if any(s in inp_lower for s in self._CODE_SIGNALS):
            return "code"
        return "chat"

    def _update_params(self, user_input: str, last_response: str = "") -> None:
        """Auto-switch _params based on detected phase. No-op when locked or in fixed modes."""
        if self._params_locked:
            return
        if self._get_active_execution_mode() in FIXED_EXECUTION_MODES:
            return
        phase = self._detect_phase(user_input, last_response)
        if phase == self._current_phase:
            return
        self._current_phase = phase
        self._params = PRESETS[phase]
        console.print(f"  [dim]◉ Phase → [bold]{phase}[/bold]  {self._params.describe()}[/dim]")



    # ── Tool execution — tier-aware ───────────────────────────────────────────

    async def start(self):
        self._init_flashlight()

        async with self.client:
            if await self.client.health_check():
                dashboard.print_success("Connected to LM Studio")
                models = await self.client.list_models()
                if models:
                    dashboard.print_info(f"Available models: {', '.join(models)}")
            else:
                dashboard.print_error("LM Studio not running at localhost:1234")
                return

            if self.stream_enabled:
                dashboard.print_info("Streaming enabled")
            dashboard.print_info(
                "Type /help for commands | /stream to toggle | "
                "/reindex to rescan | /beam <query> to preview flashlight"
            )

            while True:
                try:
                    loop = asyncio.get_running_loop()
                    user_input = await loop.run_in_executor(None, lambda: typer.prompt("\nYou"))

                    if user_input.startswith("/"):
                        await self._handle_command(user_input)
                        continue

                    if not user_input.strip():
                        continue

                    dashboard.print_user_input(user_input)
                    from core.utils.image_utils import extract_image_paths_from_text

                    img_paths = extract_image_paths_from_text(user_input)
                    self.memory.add_user_message(
                        user_input, images=img_paths if img_paths else None
                    )
                    if getattr(self, "trajectory_lock", None):
                        self.trajectory_lock.reset()

                    # Detect phase from user input before generating
                    self._update_params(user_input)

                    tracker = dashboard.action_tracker()
                    with tracker:
                        if self.memory.should_compress():
                            act = tracker.start("compress", "Compressing context...")
                            await self._compress_context()
                            tracker.finish(act)

                        think_act = tracker.start("thinking", "Generating response...")
                        try:
                            if self.stream_enabled:
                                response = await self._generate_streaming_response(user_input)
                            else:
                                response = await self._generate_response(user_input)
                        except RuntimeError as e:
                            tracker.finish(think_act, ok=False)
                            dashboard.print_error(str(e))
                            continue
                        tracker.finish(think_act)

                        # Debate & Self-Critique pass (Out-of-band)
                        response = await self._verify_and_refine_if_needed(
                            response, user_task=user_input, phase_name=self._current_phase
                        )
                        self.memory.add_assistant_message(response)

                    dashboard.print_response(sanitize_assistant_text(response))
                    dashboard.show_snapshot(self.memory.get_snapshot())

                    # Re-detect after seeing the model's response
                    self._update_params(user_input, response)

                    MAX_CHAIN = 10
                    chain_depth = 0

                    while chain_depth < MAX_CHAIN:
                        parsed_skills = self.skills.parse_skills(response)
                        if not parsed_skills:
                            break

                        chain_depth += 1
                        tool_tracker = dashboard.action_tracker()

                        with tool_tracker:
                            for name, params in parsed_skills:
                                await self._execute_tool_with_approval(name, params, tool_tracker)

                            think2 = tool_tracker.start("thinking", "Processing tool results...")
                            # Use the last assistant response as the beam query so
                            # Flashlight focuses on files relevant to the current
                            # step, not the original user message.
                            beam_query = response[:300] if response else user_input
                            try:
                                if self.stream_enabled:
                                    response = await self._generate_streaming_response(beam_query)
                                else:
                                    response = await self._generate_response(beam_query)
                            except RuntimeError as e:
                                tool_tracker.finish(think2, ok=False)
                                dashboard.print_error(str(e))
                                break
                            tool_tracker.finish(think2)
                            # Debate & Self-Critique pass on multi-step tool proposals
                            response = await self._verify_and_refine_if_needed(
                                response, user_task=user_input, phase_name=self._current_phase
                            )
                            self.memory.add_assistant_message(response)

                        dashboard.print_response(sanitize_assistant_text(response))

                    if chain_depth >= MAX_CHAIN:
                        dashboard.print_warning(
                            f"Agent chain limit ({MAX_CHAIN}) reached. "
                            "Review results and continue manually."
                        )

                    # Persist session findings to .context-memory.json at turn conclusion
                    if self.project_memory:
                        self.project_memory.persist_session_state(self.memory.state)

                except KeyboardInterrupt:
                    dashboard.print_info("\nGoodbye!")
                    break
                except Exception as e:
                    dashboard.print_error(str(e))

    # ── Response generation ────────────────────────────────────────────────────

    def _build_messages(self, user_query: str) -> list[dict]:
        """
        Build the final message list for the LLM, respecting the context budget.

        For small context models (≤ 5000 tokens):
          - Skip skills prompts entirely (too large, model uses bare tool syntax)
          - Inject flashlight beam as a USER message, not a system message
            (system messages are merged by lmstudio.py into n_keep, which must
             fit inside n_ctx — injecting beam as user avoids the n_keep overflow)
          - Beam is already limited to 1 file × 50 lines ≈ 500 tokens

        For larger context models (> 5000 tokens):
          - Include skills prompts
          - Inject beam as a system message (higher attention priority)
          - Full beam (3 files × 120 lines)
        """
        context = self.memory.get_context_for_llm(user_query)
        small = self.max_tokens <= _SMALL_CTX
        phase = self._detect_phase(user_query)
        base_prompt = get_phase_system_prompt(phase)
        allowed_tools = PRESETS[phase].allowed_tools if phase in PRESETS else None

        # ── System message — base prompt + optional tool syntax ───────────────
        if small:
            # Bare tool syntax reminder only — skip get_all_prompts() entirely
            cli_suffix = (
                '\nTool syntax: bare call at end of response, e.g.  READ_FILE("path")\n'
                "Only ONE tool per response. Never put tools in backticks."
            )
            system_content = base_prompt + cli_suffix
        else:
            tool_instruct = (
                f"\n\n{self.skills.get_all_prompts(max_tokens=self.max_tokens, allowed_tools=allowed_tools)}\n"
                "To use a skill, output EXACTLY:\n<tool_call>\n"
                "{'name': 'skill_name', 'arguments': {'param': 'value'}}\n</tool_call>"
            )
            cli_suffix = (
                "\n\n## Tool Calling Syntax (CLI):\n"
                "Output EXACTLY this at the END of your response:\n"
                "<tool_call>\n"
                "{'name': 'skill_name', 'arguments': {'param': 'value'}}\n"
                "</tool_call>\n"
                "Tool calls MUST be last. Only ONE tool call per turn.\n"
            )
            system_content = base_prompt + cli_suffix + tool_instruct

        critical = self.memory.build_critical_context()
        if critical:
            system_content += f"\n\n{'=' * 50}\n{critical}\n{'=' * 50}"

        # Execution feedback: test results from recent changes
        test_feedback = self._feedback_loop.build_feedback_context()
        if test_feedback:
            system_content += f"\n\n{test_feedback}"

        # Tool prediction hints based on current state
        predicted_tools = self.memory.predict_next_tools()
        if predicted_tools and small:
            system_content += f"\n\nLikely next tools: {', '.join(predicted_tools)}"

        system_msg = {"role": "system", "content": system_content}
        messages = [system_msg]

        # ── Flashlight beam with intent-aware selection ───────────────────────
        # Combine project intent + active file + current query for better beam
        intent_hint = self.memory.get_intent_for_retrieval()
        active_file_hint = self.memory.get_active_file_hint()

        # Sanitize query: strip tool output tags/prefixes if present
        clean_user_query = re.sub(
            r"(?:Result of|Error in|<tool_call>).*", "", user_query, flags=re.DOTALL
        ).strip()
        if not clean_user_query:
            clean_user_query = user_query[:100]

        # Prioritize active file in beam query
        if active_file_hint:
            beam_query = f"{active_file_hint} {clean_user_query}"
        elif intent_hint:
            beam_query = f"{intent_hint} | {clean_user_query}"
        else:
            beam_query = clean_user_query

        beam_block = self._get_beam_block(beam_query)
        if beam_block:
            beam_files = (
                [r.path for r in self._light.beam(beam_query, max_files=self._beam_files)]
                if self._light
                else []
            )
            if beam_files:
                console.print(f"  [dim]◉ Flashlight → {', '.join(beam_files)}[/dim]")

            if small:
                # Inject as a USER message so it does NOT count toward n_keep
                messages.extend(context)
                messages.append({"role": "user", "content": beam_block})
                return messages
            else:
                # Inject as system for larger models (higher attention priority)
                messages.append({"role": "system", "content": beam_block})

        messages.extend(context)
        return messages

    async def _generate_response(self, user_query: str = "") -> str:
        self._plan_updated_this_turn = False
        messages = self._build_messages(user_query)
        res = await self.client.chat(messages, params=self._params)
        response = self._repair_stop_tokens(res)

        # Verification gate: check for pending tasks or missing plan in Goal / Plan Mode before allowing FINAL_ANSWER
        gate_rejections = 0
        max_gate_rejections = 10
        while (
            self.mode == "plan"
            and "<FINAL_ANSWER>" in response
            and gate_rejections < max_gate_rejections
        ):
            plan_file = os.path.join(self.project_path, "implementation_plan.md")
            plan_exists = os.path.exists(plan_file)
            plan_in_response = (
                ("WRITE_FILE" in response or "EDIT_FILE" in response)
                and "implementation_plan.md" in response
            )
            plan_updated = getattr(self, "_plan_updated_this_turn", False) or plan_in_response

            if not plan_updated:
                if "- [ ]" in response or any(kw in response.lower() for kw in ("proposed changes", "implementation plan", "phase 1")):
                    try:
                        clean_save = re.sub(r"</?FINAL_ANSWER>", "", response).strip()
                        with open(plan_file, "w", encoding="utf-8") as pf:
                            pf.write(clean_save)
                        self._plan_updated_this_turn = True
                        plan_updated = True
                        break
                    except Exception:
                        pass

            if plan_updated:
                break
            gate_rejections += 1
            rejection = (
                f"❌ [VERIFICATION GATE REJECTION #{gate_rejections}]\n"
                "You are in Plan Mode, but 'implementation_plan.md' has not been written or updated during this turn.\n"
                "You MUST first inspect the workspace (using SEARCH_AST, LIST_DIR, READ_FILE) and save 'implementation_plan.md' with brainstormed steps and actionable checkbox tasks (`- [ ]`) via WRITE_FILE before yielding <FINAL_ANSWER>."
            )
            self.memory.add_user_message(rejection)
            messages = self._build_messages("")
            res = await self.client.chat(messages, params=self._params)
            response = self._repair_stop_tokens(res)

        while (
            self.mode == "goal"
            and "<FINAL_ANSWER>" in response
            and gate_rejections < max_gate_rejections
        ):
            from core.tools.task_helpers import get_workspace_pending_tasks

            pending_tasks = get_workspace_pending_tasks(str(self.project_path))
            plan_file = os.path.join(self.project_path, "implementation_plan.md")
            plan_exists = os.path.exists(plan_file)

            if not pending_tasks and plan_exists:
                break

            gate_rejections += 1
            if not plan_exists and not pending_tasks:
                rejection = (
                    f"❌ [VERIFICATION GATE REJECTION #{gate_rejections}]\n"
                    "You are in Goal Mode, but 'implementation_plan.md' has not been created yet and no tasks are tracked.\n"
                    "You MUST first inspect the workspace (using SEARCH_AST, LIST_DIR, READ_FILE) and create 'implementation_plan.md' with actionable checkbox tasks (`- [ ]`) via WRITE_FILE before yielding <FINAL_ANSWER>."
                )
            else:
                task_descs = [f"- {t}" for t in pending_tasks[:3]]
                rejection = (
                    f"❌ [VERIFICATION GATE REJECTION #{gate_rejections}]\n"
                    "The following tasks in the implementation plan are still PENDING or IN_PROGRESS:\n"
                    + "\n".join(task_descs)
                    + f"\n\nTask '{pending_tasks[0]}' is still PENDING. You MUST execute tool calls (EDIT_FILE, WRITE_FILE, RUN_COMMAND, etc.) to complete and verify this task. Do NOT return <FINAL_ANSWER> until ALL tasks are verified and completed."
                )
            # Add rejection as user message and regenerate
            self.memory.add_user_message(rejection)
            messages = self._build_messages("")  # Rebuild with rejection
            res = await self.client.chat(messages, params=self._params)
            response = self._repair_stop_tokens(res)

        # ── Code Mode Gate: block FINAL_ANSWER when tasks are still pending ──
        if (
            self.mode == "code"
            and "<FINAL_ANSWER>" in response
            and gate_rejections < max_gate_rejections
        ):
            from core.tools.task_helpers import get_workspace_pending_tasks
            pending_tasks = get_workspace_pending_tasks(str(self.project_path))
            if pending_tasks:
                # Extract the content between FINAL_ANSWER tags — if empty, always reject
                fa_content = re.search(r"<FINAL_ANSWER>(.*?)</FINAL_ANSWER>", response, re.DOTALL)
                fa_text = fa_content.group(1).strip() if fa_content else ""
                if not fa_text or len(fa_text) < 20:
                    task_descs = [f"- {t}" for t in pending_tasks[:3]]
                    rejection = (
                        f"❌ [CODE MODE GATE — PREMATURE FINAL ANSWER]\n"
                        "You returned an empty or trivial <FINAL_ANSWER> but the following tasks are still PENDING:\n"
                        + "\n".join(task_descs)
                        + f"\n\nDO NOT output <FINAL_ANSWER> yet. Pick the next pending task ('{pending_tasks[0]}') and immediately emit a tool call to implement it."
                    )
                    self.memory.add_user_message(rejection)
                    messages = self._build_messages("")
                    res = await self.client.chat(messages, params=self._params)
                    response = self._repair_stop_tokens(res)

        # ── Plan Mode completion: inject Code Mode switch banner ──
        if self.mode == "plan" and "<FINAL_ANSWER>" in response:
            plan_file = os.path.join(self.project_path, "implementation_plan.md")
            if os.path.exists(plan_file):
                switch_banner = (
                    "\n\n---\n"
                    "✅ **Implementation plan saved.** "
                    "Switch to Code Mode to begin implementation: "
                    "type `/mode code` (CLI) or press **Ctrl+G → Code** (TUI)."
                )
                # Append banner just before closing </FINAL_ANSWER> if present
                response = re.sub(
                    r"</FINAL_ANSWER>",
                    switch_banner + "</FINAL_ANSWER>",
                    response,
                    count=1,
                )

        return response

    async def _generate_streaming_response(self, user_query: str = "") -> str:
        self._plan_updated_this_turn = False
        messages = self._build_messages(user_query)

        self._response_tokens = 0
        self._start_time = time.time()
        buffer = []
        stats = self._create_stats_panel()

        with Live(stats, console=console, refresh_per_second=10, transient=True) as live:
            async for chunk in self.client.chat_stream(messages, params=self._params):
                buffer.append(chunk)
                self._response_tokens += max(1, len(chunk) // 3)
                elapsed = time.time() - self._start_time
                tps = self._response_tokens / elapsed if elapsed > 0 else 0
                stats = self._create_stats_panel(
                    response_preview="".join(buffer[-50:]),
                    tokens_per_sec=tps,
                )
                live.update(stats, refresh=False)
            live.update(stats, refresh=True)

        full_text = "".join(buffer)
        response = self._repair_stop_tokens(full_text)

        # Verification gate: check for pending tasks or missing plan in Goal / Plan Mode before allowing FINAL_ANSWER
        gate_rejections = 0
        max_gate_rejections = 10
        while (
            self.mode == "plan"
            and "<FINAL_ANSWER>" in response
            and gate_rejections < max_gate_rejections
        ):
            plan_file = os.path.join(self.project_path, "implementation_plan.md")
            plan_exists = os.path.exists(plan_file)
            plan_in_response = (
                ("WRITE_FILE" in response or "EDIT_FILE" in response)
                and "implementation_plan.md" in response
            )
            plan_updated = getattr(self, "_plan_updated_this_turn", False) or plan_in_response

            if not plan_updated:
                if "- [ ]" in response or any(kw in response.lower() for kw in ("proposed changes", "implementation plan", "phase 1")):
                    try:
                        clean_save = re.sub(r"</?FINAL_ANSWER>", "", response).strip()
                        with open(plan_file, "w", encoding="utf-8") as pf:
                            pf.write(clean_save)
                        self._plan_updated_this_turn = True
                        plan_updated = True
                        break
                    except Exception:
                        pass

            if plan_updated:
                break
            gate_rejections += 1
            rejection = (
                f"❌ [VERIFICATION GATE REJECTION #{gate_rejections}]\n"
                "You are in Plan Mode, but 'implementation_plan.md' has not been written or updated during this turn.\n"
                "You MUST first inspect the workspace (using SEARCH_AST, LIST_DIR, READ_FILE) and save 'implementation_plan.md' with brainstormed steps and actionable checkbox tasks (`- [ ]`) via WRITE_FILE before yielding <FINAL_ANSWER>."
            )
            self.memory.add_user_message(rejection)
            messages = self._build_messages("")
            buffer = []
            self._response_tokens = 0
            self._start_time = time.time()
            stats = self._create_stats_panel()
            with Live(stats, console=console, refresh_per_second=10, transient=True) as live:
                async for chunk in self.client.chat_stream(messages, params=self._params):
                    buffer.append(chunk)
                    self._response_tokens += max(1, len(chunk) // 3)
                    elapsed = time.time() - self._start_time
                    tps = self._response_tokens / elapsed if elapsed > 0 else 0
                    stats = self._create_stats_panel(
                        response_preview="".join(buffer[-50:]),
                        tokens_per_sec=tps,
                    )
                    live.update(stats, refresh=False)
                live.update(stats, refresh=True)
            full_text = "".join(buffer)
            response = self._repair_stop_tokens(full_text)

        while (
            self.mode == "goal"
            and "<FINAL_ANSWER>" in response
            and gate_rejections < max_gate_rejections
        ):
            from core.tools.task_helpers import get_workspace_pending_tasks

            pending_tasks = get_workspace_pending_tasks(str(self.project_path))
            plan_file = os.path.join(self.project_path, "implementation_plan.md")
            plan_exists = os.path.exists(plan_file)

            if not pending_tasks and plan_exists:
                break

            gate_rejections += 1
            if not plan_exists and not pending_tasks:
                rejection = (
                    f"❌ [VERIFICATION GATE REJECTION #{gate_rejections}]\n"
                    "You are in Goal Mode, but 'implementation_plan.md' has not been created yet and no tasks are tracked.\n"
                    "You MUST first inspect the workspace (using SEARCH_AST, LIST_DIR, READ_FILE) and create 'implementation_plan.md' with actionable checkbox tasks (`- [ ]`) via WRITE_FILE before yielding <FINAL_ANSWER>."
                )
            else:
                task_descs = [f"- {t}" for t in pending_tasks[:3]]
                rejection = (
                    f"❌ [VERIFICATION GATE REJECTION #{gate_rejections}]\n"
                    "The following tasks in the implementation plan are still PENDING or IN_PROGRESS:\n"
                    + "\n".join(task_descs)
                    + f"\n\nTask '{pending_tasks[0]}' is still PENDING. You MUST execute tool calls (EDIT_FILE, WRITE_FILE, RUN_COMMAND, etc.) to complete and verify this task. Do NOT return <FINAL_ANSWER> until ALL tasks are verified and completed."
                )
            # Add rejection as user message and regenerate
            self.memory.add_user_message(rejection)
            messages = self._build_messages("")  # Rebuild with rejection
            buffer = []
            self._response_tokens = 0
            self._start_time = time.time()
            stats = self._create_stats_panel()
            with Live(stats, console=console, refresh_per_second=10, transient=True) as live:
                async for chunk in self.client.chat_stream(messages, params=self._params):
                    buffer.append(chunk)
                    self._response_tokens += max(1, len(chunk) // 3)
                    elapsed = time.time() - self._start_time
                    tps = self._response_tokens / elapsed if elapsed > 0 else 0
                    stats = self._create_stats_panel(
                        response_preview="".join(buffer[-50:]),
                        tokens_per_sec=tps,
                    )
                    live.update(stats, refresh=False)
                live.update(stats, refresh=True)
            full_text = "".join(buffer)
            response = self._repair_stop_tokens(full_text)

        # ── Code Mode Gate: block empty/premature FINAL_ANSWER when tasks pending ──
        if (
            self.mode == "code"
            and "<FINAL_ANSWER>" in response
            and gate_rejections < max_gate_rejections
        ):
            from core.tools.task_helpers import get_workspace_pending_tasks
            pending_tasks = get_workspace_pending_tasks(str(self.project_path))
            if pending_tasks:
                fa_content = re.search(r"<FINAL_ANSWER>(.*?)</FINAL_ANSWER>", response, re.DOTALL)
                fa_text = fa_content.group(1).strip() if fa_content else ""
                if not fa_text or len(fa_text) < 20:
                    task_descs = [f"- {t}" for t in pending_tasks[:3]]
                    rejection = (
                        f"❌ [CODE MODE GATE — PREMATURE FINAL ANSWER]\n"
                        "You returned an empty or trivial <FINAL_ANSWER> but the following tasks are still PENDING:\n"
                        + "\n".join(task_descs)
                        + f"\n\nDO NOT output <FINAL_ANSWER> yet. Pick the next pending task ('{pending_tasks[0]}') and immediately emit a tool call to implement it."
                    )
                    self.memory.add_user_message(rejection)
                    messages = self._build_messages("")
                    buffer = []
                    self._response_tokens = 0
                    self._start_time = time.time()
                    stats = self._create_stats_panel()
                    with Live(stats, console=console, refresh_per_second=10, transient=True) as live:
                        async for chunk in self.client.chat_stream(messages, params=self._params):
                            buffer.append(chunk)
                            self._response_tokens += max(1, len(chunk) // 3)
                            elapsed = time.time() - self._start_time
                            tps = self._response_tokens / elapsed if elapsed > 0 else 0
                            stats = self._create_stats_panel(
                                response_preview="".join(buffer[-50:]),
                                tokens_per_sec=tps,
                            )
                            live.update(stats, refresh=False)
                        live.update(stats, refresh=True)
                    full_text = "".join(buffer)
                    response = self._repair_stop_tokens(full_text)

        # ── Plan Mode completion: inject Code Mode switch banner ──
        if self.mode == "plan" and "<FINAL_ANSWER>" in response:
            plan_file = os.path.join(self.project_path, "implementation_plan.md")
            if os.path.exists(plan_file):
                switch_banner = (
                    "\n\n---\n"
                    "✅ **Implementation plan saved.** "
                    "Switch to Code Mode to begin implementation: "
                    "type `/mode code` (CLI) or press **Ctrl+G → Code** (TUI)."
                )
                response = re.sub(
                    r"</FINAL_ANSWER>",
                    switch_banner + "</FINAL_ANSWER>",
                    response,
                    count=1,
                )

        return response

    def _create_stats_panel(
        self,
        response_preview: str = "",
        tokens_per_sec: float = 0,
    ) -> Panel:
        snapshot = self.memory.get_snapshot()
        ctx_tokens = snapshot.token_count + self._response_tokens
        usage_pct = (ctx_tokens / self.max_tokens) * 100 if self.max_tokens > 0 else 0
        bar_color = "green" if usage_pct < 50 else ("yellow" if usage_pct < 70 else "red")
        fill = int(usage_pct / 2)
        bar = "█" * fill + "░" * (50 - fill)
        preview = response_preview[:40] + "..." if len(response_preview) > 40 else response_preview

        lock_str = " 🔒" if self._params_locked else ""
        content = (
            f"[cyan]Context[/cyan]: {ctx_tokens:,}/{self.max_tokens:,} "
            f"tokens ({usage_pct:.0f}%)\n"
            f"[{bar_color}]{bar}[/{bar_color}]\n"
            f"[cyan]Messages[/cyan]: {snapshot.message_count} | "
            f"[cyan]Response[/cyan]: {self._response_tokens} tokens\n"
            f"[cyan]Phase[/cyan]: {self._current_phase}{lock_str}  "
            f"[dim]{self._params.describe()}[/dim]"
        )
        if tokens_per_sec > 0:
            content += f" | [cyan]Speed[/cyan]: {tokens_per_sec:.1f} tok/s"
        if preview:
            from rich.markup import escape

            content += f"\n[dim]Streaming:[/dim] {escape(preview)}"

        # Per-section context breakdown
        breakdown = self._context_section_breakdown(
            ctx_tokens=ctx_tokens,
            response_tokens=self._response_tokens,
        )
        if breakdown:
            content += f"\n\n[dim]─ Context Breakdown ─────────────────[/dim]\n{breakdown}"

        return Panel(content, title="[bold]Live Stats[/bold]", border_style="blue")

    def _context_section_breakdown(self, ctx_tokens: int = 0, response_tokens: int = 0) -> str:
        """Return a compact Rich markup string showing per-section token estimates.

        Sections: System Prompt, Scratchpad/L0, Flashlight Beam, Chat History, Pins, Streaming.
        Results are cached for 2.0s to avoid redundant formatting during streaming.
        """
        ctx_max = self.max_tokens
        if ctx_max <= 0:
            return ""

        # ── 2.0s TTL cache — only recompute static sections once per 2 seconds ──
        now = time.monotonic()
        cached_static = getattr(self, "_ctx_breakdown_cache", None)
        cached_ts = getattr(self, "_ctx_breakdown_ts", 0.0)
        SPARK_W = 10
        if cached_static is not None and (now - cached_ts) < 2.0:
            # Still in cache window: only update streaming row (cheap, no I/O)
            if response_tokens > 0:
                pct = min(100.0, (response_tokens / ctx_max) * 100)
                filled = min(SPARK_W, round((pct / 100.0) * SPARK_W))
                spark = "\u25aa" * filled + "\u00b7" * (SPARK_W - filled)
                stream_row = (
                    f"[dim]{'Streaming':<11}[/dim]"
                    f"[yellow]{spark}[/yellow] "
                    f"[bold]{response_tokens:>5,}[/bold] "
                    f"[dim]{pct:>4.1f}%[/dim]"
                )
                return cached_static + "\n" + stream_row
            return cached_static

        # ── Full recompute (at most every 2s, O(1) in memory) ──
        # 1. System prompt estimate per phase
        _SYSTEM_SIZES = {"chat": 900, "plan": 1100, "code": 1050, "goal": 1000, "troubleshoot": 950}
        system_tok = _SYSTEM_SIZES.get(self._current_phase, 1000) + 300  # +300 tool syntax

        # 2. Scratchpad/L0 — fast estimate from memory state
        scratchpad_tok = getattr(self.memory, "_estimate_l0_tokens", lambda: 150)()
        if scratchpad_tok == 0:
            scratchpad_tok = 50

        # 3. Flashlight beam — heuristic
        beam_tok = 600 if ctx_max >= 8000 else 250

        # 4. Chat history — committed message tokens in memory
        chat_tok = getattr(self.memory, "_cached_msg_tokens", 0)

        # 5. Pinned files
        pinned_tok = getattr(self.memory, "_cached_pinned_tokens", 0)

        total_static = system_tok + scratchpad_tok + beam_tok + chat_tok + pinned_tok
        if total_static <= 0:
            return ""

        def _row(label: str, tok: int, color: str) -> str:
            pct = min(100.0, (tok / ctx_max) * 100)
            filled = min(SPARK_W, round((pct / 100.0) * SPARK_W))
            spark = "\u25aa" * filled + "\u00b7" * (SPARK_W - filled)
            return (
                f"[dim]{label:<11}[/dim]"
                f"[{color}]{spark}[/{color}] "
                f"[bold]{tok:>5,}[/bold] "
                f"[dim]{pct:>4.1f}%[/dim]"
            )

        row_list = [
            _row("System",     system_tok,     "blue"),
            _row("Scratchpad",  scratchpad_tok, "cyan"),
            _row("Beam",        beam_tok,       "bright_cyan"),
            _row("Chat",        chat_tok,       "green"),
        ]
        if pinned_tok > 0:
            row_list.append(_row("Pins", pinned_tok, "magenta"))

        static_rows = "\n".join(row_list)

        # Cache the static rows (no streaming row) for 2s
        self._ctx_breakdown_cache = static_rows  # type: ignore[attr-defined]
        self._ctx_breakdown_ts = now              # type: ignore[attr-defined]

        if response_tokens > 0:
            pct = min(100.0, (response_tokens / ctx_max) * 100)
            filled = min(SPARK_W, round((pct / 100.0) * SPARK_W))
            spark = "\u25aa" * filled + "\u00b7" * (SPARK_W - filled)
            stream_row = (
                f"[dim]{'Streaming':<11}[/dim]"
                f"[yellow]{spark}[/yellow] "
                f"[bold]{response_tokens:>5,}[/bold] "
                f"[dim]{pct:>4.1f}%[/dim]"
            )
            return static_rows + "\n" + stream_row
        return static_rows

    async def _compress_context(self, force: bool = True):
        tokens_before = self.memory.total_tokens
        # Persist session state to project memory before compressing
        if self.project_memory:
            self.project_memory.persist_session_state(self.memory.state)
            console.print("\n[dim]◉ Session findings persisted to project memory.[/dim]")

        await self.memory.compress_recent_async(self.summarizer.simple_summarize, force=force)
        tokens_after = self.memory.total_tokens
        tokens_freed = max(0, tokens_before - tokens_after)

        # Log extractor diagnostics at DEBUG level
        if self.memory._llm_extractor is not None:
            s = self.memory._llm_extractor.stats
            console.print(
                f"  [dim]◉ State extractor: {s['hits']} hits / "
                f"{s['calls']} calls / {s['errors']} errors[/dim]"
            )
        return tokens_before, tokens_after, tokens_freed




# Register CLI commands
register_chat_commands(app, StreamingChatSession, AutonomousHarness)
register_utility_commands(app)


def main():
    app()


if __name__ == "__main__":
    main()
