import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

# ── Import from core/ shared library ──────────────────────────────────────
try:
    from core.api.base import InferenceParams, PRESETS
    from core.api.lmstudio import LMStudioClient
    from core.memory.manager import TieredMemory, MemoryConfig
    from core.memory.models import ExecutionMode
    from core.memory.token_counter import get_token_counter
    from core.compression.compactor import VerbatimCompactor, CompressionConfig
    from core.compression.summarizer import ConversationSummarizer
    from core.memory.persistence import ProjectMemory
    from core.flashlight import SymbolIndex, Flashlight
    from core.execution.feedback_loop import ExecutionFeedbackLoop
    from core.tools.classification import AUTO, CONFIRM, REVIEW, classify_command
    from core.tools.implementations import set_ctx_window as _set_ctx_window
    from core.prompts.system import DEFAULT_SYSTEM_PROMPT, get_phase_system_prompt, sanitize_assistant_text
    from core.debate.verifier import DebateVerifier
    from core.execution.autonomous_harness import AutonomousHarness
    from core.tools.dedup import TrajectoryLock, get_alternate_trajectory_hint
except ImportError:
    # Fallback to local modules if core/ is not installed
    from ..api.lmstudio import LMStudioClient, InferenceParams, PRESETS
    from ..memory.manager import TieredMemory, MemoryConfig
    from ..memory.models import ExecutionMode
    from ..memory.token_counter import get_token_counter
    from ..compression.compactor import VerbatimCompactor, CompressionConfig
    from ..compression.summarizer import ConversationSummarizer
    from ..memory.persistence import ProjectMemory
    from ..flashlight import SymbolIndex, Flashlight
    from ..execution.feedback_loop import ExecutionFeedbackLoop
    from ..tools.core import (
        AUTO,
        CONFIRM,
        REVIEW,
        classify_command,
        set_ctx_window as _set_ctx_window,
    )

    try:
        from core.prompts.system import DEFAULT_SYSTEM_PROMPT, get_phase_system_prompt
    except ImportError:
        from ..prompts import DEFAULT_SYSTEM_PROMPT

        def get_phase_system_prompt(phase="code"):
            return DEFAULT_SYSTEM_PROMPT

    try:
        from core.debate.verifier import DebateVerifier
    except ImportError:
        DebateVerifier = None
    try:
        from core.execution.autonomous_harness import AutonomousHarness
    except ImportError:
        AutonomousHarness = None


from ..skills.unified import create_unified_registry
from ..tools.core import get_core_registry


app = typer.Typer(help="Context Manager CLI - Chat with LLMs while managing context")
console = Console()

from .dashboard import ContextDashboard, ActionTracker

dashboard = ContextDashboard()
_core_reg = get_core_registry()

# ── Token budget constants ─────────────────────────────────────────────────────
#
# These control how much of the context window each layer consumes.
# For a 4096-token model the entire pipeline must fit inside 4096 tokens:
#
#   base system prompt   ~200 tok   (SYSTEM_PROMPT in prompts.py)
#   tool syntax suffix   ~80  tok   (bare call format reminder)
#   flashlight beam      ≤600 tok   (1 file, 50 lines — see _beam_budget)
#   state summary        ≤200 tok   (when context truncated)
#   conversation         remaining  (~3000 tok at 4096 total)
#
# Skills prompts (get_all_prompts) are SKIPPED for models with ≤5000 token
# windows because they are too large and the model uses bare tool syntax anyway.

_SMALL_CTX = 5000  # models at or below this limit get the trimmed pipeline


def _beam_budget(max_tokens: int) -> tuple[int, int]:
    """Return (max_beam_files, max_lines_per_file) for the given context size."""
    if max_tokens <= _SMALL_CTX:
        return 1, 50  # 1 file, 50 lines ≈ 500 tokens
    if max_tokens <= 9000:
        return 2, 80  # 2 files, 80 lines ≈ 1300 tokens
    return 3, 120  # default — full beam


# ── Tool name → ActionTracker kind ───────────────────────────────────────────
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


class StreamingChatSession:
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

    def _init_flashlight(self) -> None:
        console.print(
            f"[dim]◉ Flashlight scanning [cyan]{self._project_dir.name}[/cyan]...[/dim]",
            end=" ",
        )
        self._index = SymbolIndex(self._project_dir)
        self._light = Flashlight(self._index)
        # Override beam limits in the Flashlight instance
        import context_manager.flashlight.beam as _bm

        _bm.MAX_BEAM_FILES = self._beam_files
        _bm.MAX_LINES_PER_FILE = self._beam_lines
        total_syms = sum(len(e.symbols) for e in self._index.files.values())
        graph_info = ""
        try:
            from core.flashlight.graph_engine import get_project_graph

            graph = get_project_graph(str(self._project_dir))
            graph_info = f", graph: {len(graph.nodes)} nodes"
        except Exception:
            pass
        console.print(
            f"[dim]{len(self._index.files)} files, {total_syms} symbols"
            f"{graph_info} (beam: {self._beam_files}×{self._beam_lines}L)[/dim]"
        )

    def _rebuild_index(self) -> None:
        if self._index is None:
            self._init_flashlight()
            return
        console.print("[dim]◉ Flashlight reindexing...[/dim]", end=" ")
        n = self._index.build()
        total_syms = sum(len(e.symbols) for e in self._index.files.values())
        console.print(f"[dim]{n} files, {total_syms} symbols[/dim]")

    def _get_beam_block(self, query: str) -> str:
        if self._light is None:
            return ""
        return self._light.beam_block(query, max_files=self._beam_files)

    def _notify_file_touched(self, tool_name: str, content: str) -> None:
        if self._light is None:
            return
        import re

        if tool_name in ("READ_FILE", "WRITE_FILE", "read_file", "write_file"):
            m = re.search(r"📄\s*([\w/\.\-]+)|Written .+ to ([\w/\.\-]+)", content)
            if m:
                path = (m.group(1) or m.group(2) or "").strip()
                if path:
                    self._light.mark_active(path)

    def _flash_preview(self, query: str) -> None:
        if self._light is None:
            dashboard.print_warning("Flashlight not initialised.")
            return
        results = self._light.beam(query, max_files=self._beam_files)
        if not results:
            dashboard.print_info("Flashlight: no relevant files found.")
            return
        for r in results:
            syms = ", ".join(f"{s[0]}({s[2][0]})" for s in r.symbols[:5])
            console.print(f"  [cyan]◉[/cyan] [bold]{r.path}[/bold]  [dim]{r.reason}[/dim]")
            if syms:
                console.print(f"     [dim]{syms}[/dim]")

    # ── Phase detection & inference param management ─────────────────────────

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

    def _detect_phase(self, user_input: str, last_response: str = "") -> str:
        """
        Infer the current agent phase from user input and the last model response.
        Returns one of: "plan" | "code" | "troubleshoot" | "chat".
        """
        if getattr(self, "mode", None) == "chat":
            return "chat"
        if getattr(self, "mode", None) == "plan":
            return "plan"
        if getattr(self, "mode", None) == "code":
            return "code"
        mem_state = getattr(getattr(self, "memory", None), "state", None)
        if mem_state and getattr(mem_state, "execution_mode", None) is not None:
            em_val = mem_state.execution_mode
            em_str = em_val.value if hasattr(em_val, "value") else str(em_val)
            if em_str.lower() == "chat":
                return "chat"
            if em_str.lower() == "plan":
                return "plan"
            if em_str.lower() == "code":
                return "code"


        if getattr(self, "mode", None) == "goal":
            return "goal"

        if self._phase_lock:
            if self._phase_lock_turns > 0:
                self._phase_lock_turns -= 1
                return self._phase_lock
            self._phase_lock = None

        inp_lower = user_input.lower()
        combined = (user_input + " " + last_response).lower()
        if any(s in combined for s in self._TROUBLESHOOT_SIGNALS):
            return "troubleshoot"
        if any(s in inp_lower for s in self._PLAN_SIGNALS):
            return "plan"
        if any(
            s in combined
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
        if any(s in combined for s in self._CODE_SIGNALS):
            return "code"
        if getattr(self, "mode", None) == "goal":
            return "goal"
        return "chat"

    def _update_params(self, user_input: str, last_response: str = "") -> None:
        """Auto-switch _params based on detected phase.  No-op when locked."""
        if self._params_locked:
            return
        phase = self._detect_phase(user_input, last_response)
        if phase == self._current_phase:
            return
        self._current_phase = phase
        self._params = PRESETS[phase]
        console.print(f"  [dim]◉ Phase → [bold]{phase}[/bold]  {self._params.describe()}[/dim]")

    # ── Tool execution — tier-aware ───────────────────────────────────────────

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

    # ── Command handling ───────────────────────────────────────────────────────

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
                    from core.memory.models import ExecutionMode

                    if mode_arg == "code":
                        new_mode = ExecutionMode.CODE
                    elif mode_arg == "goal":
                        new_mode = ExecutionMode.GOAL
                    elif mode_arg == "plan":
                        new_mode = ExecutionMode.PLAN
                    elif mode_arg == "unified":
                        new_mode = ExecutionMode.UNIFIED
                    else:
                        new_mode = ExecutionMode.CHAT
                    self.memory.state.execution_mode = new_mode

                if mode_arg == "code":
                    if not self._params_locked:
                        self._current_phase = "code"
                        self._params = PRESETS["code"]
                        self._phase_lock = "code"
                        self._phase_lock_turns = 2
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
                        self._phase_lock_turns = 2
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
                        self._phase_lock_turns = 2
                    dashboard.print_success(
                        "Switched to Plan Mode (Brainstorm & maintain implementation_plan.md)"
                    )
                elif mode_arg == "unified":
                    dashboard.print_success("Switched to Unified Mode (Dynamic Phase Auto-Detection)")
                else:
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


@app.command()
def chat(
    url: str = typer.Option("http://localhost:1234/v1", "--url", "-u", help="LM Studio API URL"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name"),
    image: Optional[str] = typer.Option(
        None, "--image", "-i", help="Initial image file path to inspect (PNG, JPG, WEBP, etc.)"
    ),
    max_tokens: int = typer.Option(
        4096,
        "--max-tokens",
        "-t",
        help="Context window size. Match your model's actual n_ctx in LM Studio (default: 4096).",
        min=100,
        max=200000,
    ),
    repeat_penalty: Optional[float] = typer.Option(
        None,
        "--repeat-penalty",
        "--repetition-penalty",
        "--rep",
        help="Repetition penalty for generation (e.g. 1.05). Prevents repeating text or code loops.",
    ),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming"),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Project directory (default: CWD)"
    ),
    mode: str = typer.Option(
        "chat",
        "--mode",
        "-mode",
        help="Execution mode: 'chat' (lightweight Q&A), 'plan' (brainstorm & plan), or 'goal' (task tracking & harness)",
    ),
):
    """Start an interactive chat session with context management and flashlight."""
    console.print("[bold cyan]Context Manager CLI — Torchlight[/bold cyan]")
    console.print(f"Connecting to: {url}")
    console.print(f"[dim]Context window: {max_tokens:,} tokens[/dim]")

    m_str = (mode or "chat").lower().strip()
    if m_str == "goal":
        console.print(
            "[bold green]🎯 Mode: Goal Mode[/bold green] [dim](Autonomous task tracking in .torchlight/tasks.md)[/dim]"
        )
    elif m_str == "plan":
        console.print(
            "[bold cyan]📋 Mode: Plan Mode[/bold cyan] [dim](Brainstorm architecture & write/update implementation_plan.md)[/dim]"
        )
    else:
        console.print(
            "[bold cyan]💬 Mode: Chat Mode[/bold cyan] [dim](Lightweight Q&A & ad-hoc code edits, no task files)[/dim]"
        )

    if max_tokens <= _SMALL_CTX:
        console.print(
            f"[yellow]Small context mode ({max_tokens} tok): "
            f"skills prompts skipped, beam=1×50 lines[/yellow]"
        )

    session = StreamingChatSession(
        base_url=url,
        model=model,
        max_tokens=max_tokens,
        stream=not no_stream,
        project_dir=project,
        mode=m_str,
        repeat_penalty=repeat_penalty,
    )
    asyncio.run(session.start())


@app.command()
def plan(
    title: Optional[str] = typer.Argument(None, help="Target feature or task description to plan"),
    url: str = typer.Option("http://localhost:1234/v1", "--url", "-u", help="LM Studio API URL"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name"),
    max_tokens: int = typer.Option(4096, "--max-tokens", "-t", help="Context window size"),
    repeat_penalty: Optional[float] = typer.Option(
        None,
        "--repeat-penalty",
        "--repetition-penalty",
        "--rep",
        help="Repetition penalty for generation (e.g. 1.05).",
    ),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
):
    """Start a planning session to brainstorm and write/update implementation_plan.md."""
    if title:
        console.print(f"[bold cyan]📋 Starting Plan Mode:[/bold cyan] {title}")
    else:
        console.print(
            "[bold cyan]📋 Starting Plan Mode[/bold cyan] [dim](Brainstorm architecture & write/update implementation_plan.md)[/dim]"
        )
    session = StreamingChatSession(
        base_url=url,
        model=model,
        max_tokens=max_tokens,
        stream=True,
        project_dir=project,
        mode="plan",
        repeat_penalty=repeat_penalty,
    )
    asyncio.run(session.start())


@app.command()
def goal(
    title: str = typer.Argument(..., help="Goal title or target feature description"),
    url: str = typer.Option("http://localhost:1234/v1", "--url", "-u", help="LM Studio API URL"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name"),
    max_tokens: int = typer.Option(4096, "--max-tokens", "-t", help="Context window size"),
    repeat_penalty: Optional[float] = typer.Option(
        None,
        "--repeat-penalty",
        "--repetition-penalty",
        "--rep",
        help="Repetition penalty for generation (e.g. 1.05).",
    ),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
):
    """Start an autonomous goal execution session driven by .torchlight task tracking."""
    console.print(f"[bold green]🎯 Starting Goal Mode:[/bold green] {title}")
    session = StreamingChatSession(
        base_url=url,
        model=model,
        max_tokens=max_tokens,
        stream=True,
        project_dir=project,
        mode="goal",
        repeat_penalty=repeat_penalty,
    )
    if AutonomousHarness:
        harness = AutonomousHarness(project_root=session.project_path, memory=session.memory)
        harness.ensure_goal_spec_initialized(title=title, description=title)
        console.print("[dim]✓ Goal spec initialized in .torchlight/goal_spec.json & tasks.md[/dim]")
    asyncio.run(session.start())



@app.command()
def compress_file(
    input_file: str = typer.Argument(..., help="File to compress"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o"),
    aggressive: bool = typer.Option(False, "--aggressive", "-a"),
):
    """Compress a file using verbatim compaction."""
    try:
        with open(input_file, "r") as f:
            content = f.read()
        config = CompressionConfig(aggressive_mode=aggressive)
        compactor = VerbatimCompactor(config)
        compressed = compactor.compress(content)
        if output_file:
            with open(output_file, "w") as f:
                f.write(compressed)
            ratio = len(content) / max(len(compressed), 1)
            console.print(f"[green]✓[/green] {input_file} -> {output_file}")
            console.print(
                f"Original: {len(content):,} | Compressed: {len(compressed):,} | Ratio: {ratio:.2f}x"
            )
        else:
            print(compressed)
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] File not found: {input_file}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def count_tokens(text: str = typer.Argument(..., help="Text to count tokens")):
    """Count tokens in text."""
    counter = get_token_counter()
    count = counter.count(text)
    console.print(f"[cyan]Tokens:[/cyan] {count:,}")
    console.print(f"[cyan]Chars:[/cyan] {len(text):,}")
    console.print(f"[cyan]Ratio:[/cyan] {len(text) / max(count, 1):.2f} chars/token")


@app.command()
def sessions(
    action: str = typer.Argument("list", help="Action: list, show, delete"),
    name: Optional[str] = typer.Option(None, "--name", "-n"),
):
    """Manage saved sessions."""
    from ..memory.persistence import SessionPersistence

    persistence = SessionPersistence()

    if action == "list":
        sessions_list = persistence.list_sessions()
        if not sessions_list:
            console.print("[yellow]No saved sessions[/yellow]")
            return
        table = Table(title="Saved Sessions", show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Created", style="white")
        table.add_column("Messages", style="green")
        table.add_column("Tokens", style="yellow")
        for s in sessions_list:
            table.add_row(
                s["name"],
                s["created"][:19] if s["created"] else "N/A",
                str(s["message_count"]),
                f"{s['total_tokens']:,}",
            )
        console.print(table)

    elif action == "show" and name:
        from ..memory.manager import TieredMemory

        memory = TieredMemory(tokenizer=get_token_counter())
        if persistence.load_session(name, memory):
            console.print(f"[green]Loaded:[/green] {name}")
            console.print(f"Messages: {memory.message_count}")
            console.print(f"Tokens: {memory.total_tokens:,}")
        else:
            console.print(f"[red]Not found:[/red] {name}")

    elif action == "delete" and name:
        if persistence.delete_session(name):
            console.print(f"[green]Deleted:[/green] {name}")
        else:
            console.print(f"[red]Not found:[/red] {name}")
    else:
        console.print("[yellow]Usage: sessions [list|show|delete] [--name NAME][/yellow]")


def main():
    app()


if __name__ == "__main__":
    main()
