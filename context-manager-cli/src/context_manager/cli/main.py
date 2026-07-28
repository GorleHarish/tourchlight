import asyncio
import json
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
    from core.memory.token_counter import get_token_counter
    from core.compression.compactor import VerbatimCompactor, CompressionConfig
    from core.compression.summarizer import ConversationSummarizer
    from core.memory.persistence import ProjectMemory
    from core.flashlight import SymbolIndex, Flashlight
    from core.execution.feedback_loop import ExecutionFeedbackLoop
    from core.tools.classification import AUTO, CONFIRM, REVIEW, classify_command
    from core.tools.implementations import set_ctx_window as _set_ctx_window
    from core.prompts.system import DEFAULT_SYSTEM_PROMPT
    from core.debate.verifier import DebateVerifier
    from core.execution.autonomous_harness import AutonomousHarness
except ImportError:
    # Fallback to local modules if core/ is not installed
    from ..api.lmstudio import LMStudioClient, InferenceParams, PRESETS
    from ..memory.manager import TieredMemory, MemoryConfig
    from ..memory.token_counter import get_token_counter
    from ..compression.compactor import VerbatimCompactor, CompressionConfig
    from ..compression.summarizer import ConversationSummarizer
    from ..memory.persistence import ProjectMemory
    from ..flashlight import SymbolIndex, Flashlight
    from ..execution.feedback_loop import ExecutionFeedbackLoop
    from ..tools.core import AUTO, CONFIRM, REVIEW, classify_command, set_ctx_window as _set_ctx_window
    from ..prompts import DEFAULT_SYSTEM_PROMPT
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
dashboard  = ContextDashboard()
_core_reg  = get_core_registry()

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

_SMALL_CTX = 5000   # models at or below this limit get the trimmed pipeline


def _beam_budget(max_tokens: int) -> tuple[int, int]:
    """Return (max_beam_files, max_lines_per_file) for the given context size."""
    if max_tokens <= _SMALL_CTX:
        return 1, 50    # 1 file, 50 lines ≈ 500 tokens
    if max_tokens <= 9000:
        return 2, 80    # 2 files, 80 lines ≈ 1300 tokens
    return 3, 120       # default — full beam


# ── Tool name → ActionTracker kind ───────────────────────────────────────────
_TOOL_KIND: dict[str, str] = {
    "READ_FILE":    "read_file",
    "WRITE_FILE":   "write_file",
    "RUN_COMMAND":  "run_command",
    "WEB_SEARCH":   "web_search",
    "WEB_FETCH":    "web_fetch",
    "DOC_SEARCH":   "doc_search",
    "WEB_VERIFY":   "web_verify",
    "SAVE_MEMORY":  "save_memory",
}

def _tool_kind(name: str) -> str:
    return _TOOL_KIND.get(name.upper(), "default")

def _tool_label(name: str, params: dict) -> str:
    name_u = name.upper()
    args   = list(params.values())
    first  = str(args[0])[:60] if args else ""
    if name_u == "READ_FILE":    return f"Reading  {first}"
    if name_u == "WRITE_FILE":   return f"Writing  {first}"
    if name_u == "RUN_COMMAND":  return f"Running  {first}"
    if name_u == "WEB_SEARCH":   return f"Searching  \"{first}\""
    if name_u == "WEB_FETCH":    return f"Fetching  {first}"
    if name_u == "DOC_SEARCH":   return f"Doc search  \"{first}\""
    if name_u == "WEB_VERIFY":
        lang = str(args[1])[:12] if len(args) > 1 else "code"
        return f"Verifying {lang}  {first[:40]}"
    if name_u == "SAVE_MEMORY":  return f"Saving memory  \"{first[:40]}\""
    return f"{name}  {first}"

def _risk_tier(name: str, params: dict) -> str:
    name_u = name.upper()
    args   = [str(v) for v in params.values()]
    tool   = _core_reg.get(name_u)
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
    ):
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if not base_url:
            raise ValueError("base_url cannot be empty")

        self.client = LMStudioClient(base_url=base_url, model=model)
        self._project_dir = Path(project_dir).resolve() if project_dir else Path.cwd()
        self.project_path = self._project_dir
        self.project_memory = ProjectMemory(self.project_path)
        
        self.tokenizer = get_token_counter()
        self.skills         = create_unified_registry()
        self.max_tokens     = max_tokens
        
        # Calculate initial overhead
        overhead = self._calculate_metadata_overhead()
        self.memory_config = MemoryConfig.auto_tune(max_tokens, metadata_overhead=overhead)

        self.memory = TieredMemory(
            config=self.memory_config,
            tokenizer=self.tokenizer,
            project_memory=self.project_memory,
            llm_client=self.client,   # enables LLM-powered state extraction at compression time
        )
        self.compactor      = VerbatimCompactor(CompressionConfig())
        self.summarizer     = ConversationSummarizer()
        self.stream_enabled = stream
        self._response_tokens = 0
        self._start_time      = 0
        
        # Execution feedback loop - auto-run tests after code changes
        self._feedback_loop = ExecutionFeedbackLoop(
            project_root=self.project_path,
            enabled=True,
            auto_run=True,
            timeout=60,
        )

        self._index: Optional[SymbolIndex] = None
        self._light: Optional[Flashlight]  = None

        # Pre-compute beam limits for this model's context size
        self._beam_files, self._beam_lines = _beam_budget(max_tokens)

        # Tell the tool layer the model's context window so READ_FILE scales correctly
        _set_ctx_window(max_tokens)

        # ── Inference parameter state ───────────────────────────────────────────────
        # _params holds the currently active InferenceParams for every call.
        # _params_locked = True means the user pinned a preset via /params <name>;
        # auto phase-detection is disabled and _params won't change mid-session.
        self._params: InferenceParams        = InferenceParams.for_chat()
        self._params_locked: bool            = False
        self._current_phase: str             = "chat"

        # ── Debate & Self-Critique Verifier ──────────────────────────────────────
        if DebateVerifier is not None:
            self.debate_verifier = DebateVerifier(self.client, enabled=True)
        else:
            self.debate_verifier = None



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
            if self.max_tokens <= _SMALL_CTX: overhead = base_tokens + 600
            elif self.max_tokens <= 9000:     overhead = base_tokens + 1500
            else:                             overhead = base_tokens + 3000
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
        _bm.MAX_BEAM_FILES     = self._beam_files
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
            m = re.search(r'📄\s*([\w/\.\-]+)|Written .+ to ([\w/\.\-]+)', content)
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

    # Signals checked against lowercased (user_input + last_response).
    # Priority on match: troubleshoot > plan > code > chat.
    _PLAN_SIGNALS = (
        "<plan>", "<thought>", "let me plan", "step by step",
        "here is my plan", "i will:", "steps:",
    )
    _CODE_SIGNALS = (
        "write_file", "<tool_call>", "```python", "```kotlin",
        "```java", "```javascript", "```typescript", "```swift",
        "```go", "```rust", "def ", "class ", "function ",
    )
    _TROUBLESHOOT_SIGNALS = (
        "error:", "exception:", "traceback", "failed", "not working",
        "stack trace", "segfault", "crash", "adb ", "gradle ",
        "anr", "nullpointer", "outofmemory", "build fail",
        "why is", "why does", "what went wrong", "debug",
    )

    def _detect_phase(self, user_input: str, last_response: str = "") -> str:
        """
        Infer the current agent phase from user input and the last model response.
        Returns one of: "plan" | "code" | "troubleshoot" | "chat".
        """
        combined = (user_input + " " + last_response).lower()
        if any(s in combined for s in self._TROUBLESHOOT_SIGNALS):
            return "troubleshoot"
        if any(s in combined for s in self._PLAN_SIGNALS):
            return "plan"
        if any(s in combined for s in self._CODE_SIGNALS):
            return "code"
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
        console.print(
            f"  [dim]◉ Phase → [bold]{phase}[/bold]  "
            f"{self._params.describe()}[/dim]"
        )

    # ── Tool execution — tier-aware ───────────────────────────────────────────

    async def _execute_tool_with_approval(
        self,
        name: str,
        params: dict,
        tracker: ActionTracker,
    ) -> Optional[str]:
        tier  = _risk_tier(name, params)
        kind  = _tool_kind(name)
        label = _tool_label(name, params)
        act   = tracker.start(kind, label)

        if tier == AUTO:
            try:
                result  = await self.skills.execute_skill(name, params)
                ok      = result.success
                out     = f"Result of {name}:\n{result.output}" if ok else f"Error in {name}:\n{result.error}"
                
                # Agentic Self-Correction Hints
                if not ok:
                    if "No such file" in result.error:
                        out += "\n💡 HINT: Use DOC_SEARCH(\"filename\") or RUN_COMMAND(\"find . -name '...' \") to locate it."
                    elif "Permission denied" in result.error:
                        out += "\n💡 HINT: Check file permissions or use 'ls -la' to inspect the directory."
                    elif "not enough arguments" in result.error.lower():
                        out += f"\n💡 HINT: Check the signature of {name} in the system prompt."

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
                    # Add test feedback to memory
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
                    result  = await self.skills.execute_skill(name, params)
                    ok      = result.success
                    out     = f"Result of {name}:\n{result.output}" if ok else f"Error in {name}:\n{result.error}"
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
                    result  = await self.skills.execute_skill(name, params)
                    ok      = result.success
                    out     = f"Result of {name}:\n{result.output}" if ok else f"Error in {name}:\n{result.error}"
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

    async def _verify_and_refine_if_needed(self, proposal: str, user_task: str, phase_name: str = "code") -> str:
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
                    phase=phase_name
                )
                if critique_res.has_flaws and refined_output != proposal:
                    dashboard.print_refined(flaws=critique_res.flaws, tool_name=first_tool)
                    return refined_output
            except Exception as verifier_err:
                pass
        return proposal

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
                    user_input = await loop.run_in_executor(
                        None, lambda: typer.prompt("\nYou")
                    )

                    if user_input.startswith("/"):
                        await self._handle_command(user_input)
                        continue

                    if not user_input.strip():
                        continue

                    dashboard.print_user_input(user_input)
                    self.memory.add_user_message(user_input)

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


                    dashboard.print_response(response)
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
                                await self._execute_tool_with_approval(
                                    name, params, tool_tracker
                                )

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


                        dashboard.print_response(response)

                    if chain_depth >= MAX_CHAIN:
                        dashboard.print_warning(
                            f"Agent chain limit ({MAX_CHAIN}) reached. "
                            "Review results and continue manually."
                        )

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
        small   = self.max_tokens <= _SMALL_CTX

        # ── System message — base prompt + optional tool syntax ───────────────
        if small:
            # Bare tool syntax reminder only — skip get_all_prompts() entirely
            cli_suffix = (
                "\nTool syntax: bare call at end of response, e.g.  READ_FILE(\"path\")\n"
                "Only ONE tool per response. Never put tools in backticks."
            )
            system_content = DEFAULT_SYSTEM_PROMPT + cli_suffix
        else:
            tool_instruct = (
                f"\n\n{self.skills.get_all_prompts(max_tokens=self.max_tokens)}\n"
                "To use a skill, output EXACTLY:\n<tool_call>\n"
                "{\"name\": \"skill_name\", \"arguments\": {\"param\": \"value\"}}\n</tool_call>"
            )
            cli_suffix = (
                "\n\n## Tool Calling Syntax (CLI):\n"
                "Output EXACTLY this at the END of your response:\n"
                "<tool_call>\n"
                '{"name": "skill_name", "arguments": {"param": "value"}}\n'
                "</tool_call>\n"
                "Tool calls MUST be last. Only ONE tool call per turn.\n"
            )
            system_content = DEFAULT_SYSTEM_PROMPT + cli_suffix + tool_instruct

        critical = self.memory.build_critical_context()
        if critical:
            system_content += f"\n\n{'='*50}\n{critical}\n{'='*50}"

        # Execution feedback: test results from recent changes
        test_feedback = self._feedback_loop.build_feedback_context()
        if test_feedback:
            system_content += f"\n\n{test_feedback}"

        # Tool prediction hints based on current state
        predicted_tools = self.memory.predict_next_tools()
        if predicted_tools and small:
            system_content += f"\n\nLikely next tools: {', '.join(predicted_tools)}"

        system_msg = {"role": "system", "content": system_content}
        messages   = [system_msg]

        # ── Flashlight beam with intent-aware selection ───────────────────────
        # Combine project intent + active file + current query for better beam
        intent_hint = self.memory.get_intent_for_retrieval()
        active_file_hint = self.memory.get_active_file_hint()
        
        # Sanitize query: strip tool output tags/prefixes if present
        clean_user_query = re.sub(r'(?:Result of|Error in|<tool_call>).*', '', user_query, flags=re.DOTALL).strip()
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
            beam_files = [r.path for r in self._light.beam(beam_query, max_files=self._beam_files)] \
                         if self._light else []
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
        messages = self._build_messages(user_query)
        return await self.client.chat(messages, params=self._params)

    async def _generate_streaming_response(self, user_query: str = "") -> str:
        messages = self._build_messages(user_query)

        self._response_tokens = 0
        self._start_time      = time.time()
        buffer = []
        stats  = self._create_stats_panel()

        with Live(stats, console=console, refresh_per_second=10, transient=True) as live:
            async for chunk in self.client.chat_stream(messages, params=self._params):
                buffer.append(chunk)
                self._response_tokens += 1
                elapsed = time.time() - self._start_time
                tps     = self._response_tokens / elapsed if elapsed > 0 else 0
                stats   = self._create_stats_panel(
                    response_preview="".join(buffer[-50:]),
                    tokens_per_sec=tps,
                )
                live.update(stats)

        return "".join(buffer)

    def _create_stats_panel(
        self,
        response_preview: str = "",
        tokens_per_sec: float = 0,
    ) -> Panel:
        snapshot  = self.memory.get_snapshot()
        usage_pct = snapshot.compression_ratio * 100
        bar_color = "green" if usage_pct < 50 else ("yellow" if usage_pct < 70 else "red")
        fill      = int(usage_pct / 2)
        bar       = "█" * fill + "░" * (50 - fill)
        preview   = response_preview[:40] + "..." if len(response_preview) > 40 else response_preview

        lock_str = " 🔒" if self._params_locked else ""
        content = (
            f"[cyan]Context[/cyan]: {snapshot.token_count:,}/{self.max_tokens:,} "
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

        return Panel(content, title="[bold]Live Stats[/bold]", border_style="blue")

    async def _compress_context(self):
        # Persist session state to project memory before compressing
        if self.project_memory:
            self.project_memory.persist_session_state(self.memory.state)
            console.print("\n[dim]◉ Session findings persisted to project memory.[/dim]")
        older = list(self.memory.messages)[: -self.memory.config.recent_window]
        if older:
            # Use async path when available — runs LLM extractor + regex in parallel.
            # Falls back to sync compress_recent() if extractor is not wired in.
            await self.memory.compress_recent_async(self.summarizer.simple_summarize)

            # Log extractor diagnostics at DEBUG level
            if self.memory._llm_extractor is not None:
                s = self.memory._llm_extractor.stats
                console.print(
                    f"  [dim]◉ State extractor: {s['hits']} hits / "
                    f"{s['calls']} calls / {s['errors']} errors[/dim]"
                )

    # ── Command handling ───────────────────────────────────────────────────────

    async def _handle_command(self, cmd: str):
        parts   = cmd.split(maxsplit=1)
        command = parts[0].lower()
        arg     = parts[1] if len(parts) > 1 else ""

        if command == "/help":
            self._print_help()
        elif command == "/status":
            dashboard.show_snapshot(self.memory.get_snapshot())
        elif command == "/stream":
            self.stream_enabled = not self.stream_enabled
            dashboard.print_info(f"Streaming {'enabled' if self.stream_enabled else 'disabled'}")
        elif command == "/compress":
            await self._compress_context()
            dashboard.print_success("Context compressed")
        elif command == "/clear":
            self.memory.clear()
            dashboard.print_success("Context cleared")
        elif command == "/tokens":
            dashboard.print_info(
                f"Current tokens: {self.memory.total_tokens:,} / {self.max_tokens:,}"
            )
        elif command in ("/quit", "/exit"):
            raise KeyboardInterrupt
        elif command == "/save":
            from ..memory.persistence import SessionPersistence
            persistence = SessionPersistence()
            name = arg.strip() if arg else None
            path = persistence.save_session(self.memory, session_name=name)
            dashboard.print_success(f"Session saved: {path}")
        elif command == "/params":
            await self._handle_params_command(arg.strip())
        elif command == "/reindex":
            self._rebuild_index()
            dashboard.print_success("Flashlight index rebuilt.")
        elif command == "/beam":
            query = arg.strip() or typer.prompt("Query for beam preview")
            self._flash_preview(query)
        elif command in ("/tasks", "/goal", "/subagents"):
            if AutonomousHarness:
                harness = AutonomousHarness(project_root=self.project_path, memory=self.memory)
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
                    suffix    = f"  [dim]→ {sym_names}[/dim]" if sym_names else ""
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

        # Named preset
        if arg in PRESETS:
            self._params        = PRESETS[arg]
            self._current_phase = arg
            self._params_locked = True
            dashboard.print_success(
                f"Locked to preset '{arg}': {self._params.describe()}"
            )
            return

        # Key=value overrides  e.g.  /params temp=0.15 top_k=25 seed=42
        kv_pairs = _re.findall(r'(\w+)=([\d.]+)', arg)
        if kv_pairs:
            for key, val in kv_pairs:
                # Normalise aliases
                key = {"temp": "temperature", "rep": "repeat_penalty"}.get(key, key)
                if hasattr(self._params, key):
                    field_type = type(getattr(self._params, key))
                    try:
                        setattr(self._params, key, field_type(val))
                    except (ValueError, TypeError) as e:
                        dashboard.print_warning(f"Bad value for {key}: {e}")
                else:
                    dashboard.print_warning(f"Unknown param: {key}")
            self._params_locked = True
            dashboard.print_success(f"Params updated (locked): {self._params.describe()}")
            return

        dashboard.print_warning(
            f"Unknown /params arg '{arg}'. "
            "Use: auto | code | plan | troubleshoot | chat | key=value"
        )

    def _print_help(self):
        small = self.max_tokens <= _SMALL_CTX
        mode  = f"[yellow]small-ctx ({self.max_tokens} tok)[/yellow]" if small \
                else f"[green]full ({self.max_tokens} tok)[/green]"
        help_text = f"""
[bold]Context mode:[/bold] {mode}
{"[yellow]Skills prompts skipped, beam=1×50L to fit 4k window[/yellow]" if small else ""}

[bold]Commands:[/bold]
  /help        — this help
  /status      — context statistics
  /tasks       — show sub-agent goal & task progress telemetry
  /stream      — toggle streaming
  /compress    — compress context now
  /clear       — wipe all context
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
  AUTO    — runs immediately (READ_FILE, WEB_*, DOC_*, SAVE_MEMORY, safe shell)
  CONFIRM — shows preview, one keypress (WRITE_FILE, pip/npm install, scripts)
  REVIEW  — destructive warning, default=No (rm, git push, git commit, sudo)
"""
        console.print(Panel(help_text, title="Help"))


@app.command()
def chat(
    url: str = typer.Option("http://localhost:1234/v1", "--url", "-u",
                             help="LM Studio API URL"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name"),
    max_tokens: int = typer.Option(
        4096,   # ← default changed from 8000 to 4096 for Qwen2.5-Coder-3B
        "--max-tokens", "-t",
        help="Context window size. Match your model's actual n_ctx in LM Studio (default: 4096).",
        min=100, max=200000,
    ),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming"),
    project: Optional[str] = typer.Option(None, "--project", "-p",
                                           help="Project directory (default: CWD)"),
):
    """Start an interactive chat session with context management and flashlight.

    IMPORTANT: Set --max-tokens to match your model's context length in LM Studio.
    For Qwen2.5-Coder-3B the default 4096 is correct.
    For larger models: --max-tokens 8192 or --max-tokens 16384.
    """
    console.print("[bold cyan]Context Manager CLI — Torchlight[/bold cyan]")
    console.print(f"Connecting to: {url}")
    console.print(f"[dim]Context window: {max_tokens:,} tokens[/dim]")

    if max_tokens <= _SMALL_CTX:
        console.print(
            f"[yellow]Small context mode ({max_tokens} tok): "
            f"skills prompts skipped, beam=1×50 lines[/yellow]"
        )

    session = StreamingChatSession(
        base_url=url, model=model, max_tokens=max_tokens,
        stream=not no_stream, project_dir=project,
    )
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
        config     = CompressionConfig(aggressive_mode=aggressive)
        compactor  = VerbatimCompactor(config)
        compressed = compactor.compress(content)
        if output_file:
            with open(output_file, "w") as f:
                f.write(compressed)
            ratio = len(content) / max(len(compressed), 1)
            console.print(f"[green]✓[/green] {input_file} -> {output_file}")
            console.print(f"Original: {len(content):,} | Compressed: {len(compressed):,} | Ratio: {ratio:.2f}x")
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
    count   = counter.count(text)
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
