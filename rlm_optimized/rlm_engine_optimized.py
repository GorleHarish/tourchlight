import re
import os
import json
import asyncio
from typing import Optional, Callable
from dataclasses import dataclass, field
from rlm_optimized.config import MAX_RECURSION_DEPTH, MAX_ITERATIONS_PER_LEVEL, MAX_THINKING_LOOPS, IS_8GB_DEVICE
from rlm_optimized.repl_sandbox import REPLSandbox
from rlm_optimized.prompts import SYSTEM_PROMPT, build_system_prompt, build_step_message
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
    action: str            # "code", "tool", "sub_queries", "final_answer", "thinking"
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

def _clean_and_parse_json(raw_str: str) -> dict:
    raw = (raw_str or "").strip()
    if not raw:
        return {}
        
    def _extract_dict(data):
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            return data[0]
        return None
    
    # 1. Direct JSON parse
    try:
        data = json.loads(raw)
        extracted = _extract_dict(data)
        if extracted is not None:
            return extracted
    except Exception:
        pass

    # 2. Fix unescaped newlines in JSON multiline string literals
    try:
        # Match content/code/text fields with raw multiline strings
        fixed = re.sub(
            r'("(?:content|code|text|raw)")\s*:\s*"(.*?)"(?=\s*[,}\]])',
            lambda m: m.group(1) + ': ' + json.dumps(m.group(2)),
            raw,
            flags=re.DOTALL
        )
        data = json.loads(fixed)
        extracted = _extract_dict(data)
        if extracted is not None:
            return extracted
    except Exception:
        pass

    # 3. Regex fallback extraction for key properties
    result = {}
    path_match = re.search(r'["\']?(?:path|file|filepath|filename)["\']?\s*:\s*["\']([^"\']+)["\']', raw)
    if path_match:
        result["path"] = path_match.group(1)

    content_match = re.search(r'["\']?(?:content|code|text)["\']?\s*:\s*["\']([\s\S]*?)["\']\s*(?:,|\}|\])?$', raw)
    if content_match:
        result["content"] = content_match.group(1)

    if not result:
        result = {"raw": raw}

    return result


class RLMEngineOptimized:
    def __init__(self, client=None, on_step: Optional[Callable[[Step], None]] = None,
                 max_depth: int = MAX_RECURSION_DEPTH, project_root: Optional[str] = None,
                 approval_fn: Optional[Callable[[str, str, dict], bool]] = None,
                 on_token: Optional[Callable[[str], None]] = None,
                 on_status_change: Optional[Callable[[dict], None]] = None,
                 enable_debate: bool = True,
                 debate_verifier: Optional[object] = None):
        if client is None:
            from rlm_optimized.llamacpp_client import LlamaCppClient
            client = LlamaCppClient()
        self.client = client
        self.on_step = on_step
        self.on_token = on_token  # callback for each streaming token
        self.on_status_change = on_status_change  # callback for real-time telemetry state
        self.max_depth = max_depth
        self.project_root = project_root or os.getcwd()
        if ensure_project_initialized:
            ensure_project_initialized(self.project_root)
        self.sandbox = REPLSandbox(project_root=self.project_root)
        self._total_llm_calls = 0
        self.sandbox.set_llm_query_fn(self._sandbox_llm_query)
        self.approval_fn = approval_fn  # fn(tool_name, risk, args) -> bool or async

        if debate_verifier is not None:
            self.debate_verifier = debate_verifier
        elif DebateVerifier is not None and enable_debate:
            self.debate_verifier = DebateVerifier(self.client, enabled=enable_debate)
        else:
            self.debate_verifier = None

        try:
            from core.execution.feedback_loop import ExecutionFeedbackLoop
            self.feedback_loop = ExecutionFeedbackLoop(project_root=Path(self.project_root))
        except Exception:
            self.feedback_loop = None


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
        ("<TOOL",   "</TOOL>"),
        ("<CODE>",  "</CODE>"),
        ("<FINAL_ANSWER>", "</FINAL_ANSWER>"),
        ("<SUB_QUERY>",    "</SUB_QUERY>"),
        ("<action>", "</action>"),
    ]

    def _repair_stop_tokens(self, text: str) -> str:
        """Re-append closing tags that were consumed as stop tokens by llama-server."""
        for open_tag, close_tag in self._STOP_TAG_PAIRS:
            # Check if text has the opening tag but NOT the closing tag
            if open_tag.lower() in text.lower() and close_tag.lower() not in text.lower():
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


    async def solve_async(self, task: str, depth: int = 0) -> SolveResult:
        result = SolveResult(answer="", depth=depth)
        
        if TieredMemory and MemoryConfig:
            from .config import CTX_SIZE
            memory = TieredMemory(config=MemoryConfig.auto_tune(max_tokens=CTX_SIZE))
            memory.add_system_message(build_system_prompt(self.project_root, compact=(CTX_SIZE < 8192)))
            memory.add_user_message(task)
            use_memory = True
        else:
            from .config import CTX_SIZE
            messages = [
                {"role": "system", "content": build_system_prompt(self.project_root, compact=(CTX_SIZE < 8192))},
                {"role": "user", "content": task},
            ]
            use_memory = False

        sandbox_lock = asyncio.Lock()
        consecutive_thinking = 0    # Track loops with no action tag
        consecutive_code_errors = 0 # Track consecutive failed code executions
        last_code_output = None     # Track last successful CODE result

        # ── Consecutive duplicate tool call detection ─────────────────
        _last_tool_key: Optional[tuple[str, str]] = None
        consecutive_duplicates = 0
        MAX_DUPLICATES = 3  # force-break after this many consecutive identical calls

        for iteration in range(MAX_ITERATIONS_PER_LEVEL):
            self._total_llm_calls += 1

            if use_memory:
                if memory.should_compress():
                    self._notify_status("THINKING", {"depth": depth, "status": "compacting context"})
                    summarizer_fn = _summarizer.simple_summarize if _summarizer else None
                    memory.compress_recent(summarizer_fn=summarizer_fn, preserve_first=2)
                context = memory.get_context_for_llm()
            else:
                context = messages

            self._notify_status("THINKING", {"depth": depth, "iteration": iteration + 1})
            response = await self._stream_llm(context)
            action, thinking, content, extra_queries, tool_name, tool_args = self._parse_response(response)

            # ── Debate & Self-Critique Verification Pass ──
            if self.debate_verifier:
                phase_name = "plan" if action in ("thinking", "plan") else "code"
                if self.debate_verifier.should_debate(tool_name=tool_name, phase=phase_name):
                    self._notify_status("CRITIQUING", {"tool_name": tool_name, "action": action})
                    try:
                        refined_response, critique_res = await self.debate_verifier.verify_and_refine(
                            proposal=response,
                            task_context=task,
                            tool_name=tool_name,
                            phase=phase_name
                        )
                        if critique_res.has_flaws and refined_response != response:
                            response = refined_response
                            action, thinking, content, extra_queries, tool_name, tool_args = self._parse_response(response)
                            self._notify_status("REFINED", {"tool_name": tool_name, "flaws": critique_res.flaws})
                    except Exception as verifier_err:
                        print(f"[RLMEngine] Debate verifier bypassed due to error: {verifier_err}")

            step = Step(
                step_number=iteration + 1,
                depth=depth,
                action=action,
                thinking=thinking,
                content=content,
                tool_name=tool_name,
                tool_args=tool_args,
            )

            # Reset thinking counter when model produces an action
            if action != "thinking":
                consecutive_thinking = 0

            if action == "final_answer":
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
                    self._notify_status("THINKING", {"depth": depth, "status": "summarizing task"})
                    summary_prompt = "Summarize the key actions taken and findings discovered during this task execution in exactly 3 concise bullet points. Focus on what was modified and what was learned."
                    
                    summary_messages = memory.get_context_for_llm() if use_memory else messages.copy()
                    if len(summary_messages) > 4:
                        summary_messages = [summary_messages[0]] + summary_messages[-3:]
                    summary_messages.append({"role": "assistant", "content": f"<FINAL_ANSWER>{content}</FINAL_ANSWER>"})
                    summary_messages.append({"role": "user", "content": summary_prompt})
                    
                    def _call_summarize():
                        try:
                            return self.client.chat_with_history(summary_messages, use_grammar=False)
                        except TypeError:
                            return self.client.chat_with_history(summary_messages)

                    summary = await asyncio.wait_for(
                        loop.run_in_executor(None, _call_summarize),
                        timeout=15.0
                    )
                    if hasattr(self, "_repair_stop_tokens"):
                        summary = self._repair_stop_tokens(summary)
                        
                    history_file = os.path.join(self.project_root, ".torchlight_history.log")
                    with open(history_file, "a", encoding="utf-8") as f:
                        f.write(f"\n--- Session Summary ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---\n")
                        f.write(summary.strip() + "\n")
                        
                    try:
                        if "ProjectMemory" in globals():
                            from pathlib import Path
                            pm = ProjectMemory(Path(self.project_root))
                            pm.update(f"Session on {datetime.datetime.now().strftime('%Y-%m-%d')}: {summary.strip()}")
                    except Exception as inner_e:
                        print(f"Failed to save to ProjectMemory (.context-memory.json): {inner_e}")
                except Exception as e:
                    print(f"Session summarization skipped or failed: {e}")
                # -----------------------------

                self._notify_status("IDLE", {"depth": depth, "status": "complete"})
                return result

            elif action == "tool":
                is_valid, err_msg, tool_args = validate_and_normalize_tool_call(tool_name, tool_args or {})
                if not is_valid:
                    step.result = f"❌ {err_msg}"
                    result.steps.append(step)
                    if self.on_step:
                        self.on_step(step)
                    self._notify_status("TOOL_DONE", {"tool_name": tool_name, "success": False})
                    feedback = build_step_message("tool_error", err_msg) + "\nRe-issue the tool call matching the exact schema."
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
                _READ_ONLY_TOOLS = {"READ_FILE", "READ_SYMBOLS", "LIST_DIR", "GREP",
                                    "WEB_SEARCH", "WEB_FETCH", "DOC_SEARCH", "WEB_VERIFY",
                                    "GIT", "SAVE_MEMORY", "FORMAT_CODE", "VERIFY", "ASK_USER"}
                canonical_args = json.dumps(tool_args, sort_keys=True, default=str)
                tool_name_upper = tool_name.upper() if tool_name else ""
                tool_key = (tool_name_upper, canonical_args)

                if tool_name_upper not in _READ_ONLY_TOOLS:
                    if tool_key == _last_tool_key:
                        consecutive_duplicates += 1
                        step.result = f"(duplicate — already executed {tool_name})"
                        result.steps.append(step)
                        if self.on_step:
                            self.on_step(step)
                        self._notify_status("TOOL_DONE", {"tool_name": tool_name, "success": True, "duplicate": True})

                        if consecutive_duplicates >= MAX_DUPLICATES:
                            # Force-extract — the model is stuck in a loop
                            forced = f"Tool {tool_name} was executed {consecutive_duplicates} times with identical arguments. The result is unchanged. Present whatever you have using <FINAL_ANSWER>."
                            step_forced = Step(
                                step_number=iteration + 2, depth=depth,
                                action="final_answer", thinking=f"(forced after {consecutive_duplicates} duplicate {tool_name} calls)",
                                content=forced, result=forced,
                            )
                            result.steps.append(step_forced)
                            if self.on_step:
                                self.on_step(step_forced)
                            result.answer = forced
                            result.total_llm_calls = self._total_llm_calls
                            return result

                        feedback = (
                            f"⚠️ You already called {tool_name} with identical arguments on a previous turn. "
                            "Do NOT repeat the exact same tool call. "
                            "If you need to verify the result, use READ_FILE instead. "
                            "Otherwise, use a different tool or parameters, "
                            "or wrap your response in <FINAL_ANSWER>your answer</FINAL_ANSWER>."
                        )
                        if use_memory:
                            memory.add_assistant_message(response)
                            memory.add_user_message(feedback)
                        else:
                            messages.append({"role": "assistant", "content": response})
                            messages.append({"role": "user", "content": feedback})
                        continue
                    else:
                        _last_tool_key = tool_key
                        consecutive_duplicates = 0

                # Tiered approval
                registry = get_tool_registry()
                risk = registry.risk_level_for(tool_name, tool_args)
                if risk in (CONFIRM, REVIEW):
                    self._notify_status("WAITING_APPROVAL", {"tool_name": tool_name, "risk": risk, "args": tool_args})
                else:
                    self._notify_status("TOOL", {"tool_name": tool_name, "args": tool_args, "depth": depth})

                approved = True
                if risk in (CONFIRM, REVIEW) and self.approval_fn:
                    if asyncio.iscoroutinefunction(self.approval_fn):
                        approved = await self.approval_fn(tool_name, risk, tool_args)
                    else:
                        approved = self.approval_fn(tool_name, risk, tool_args)

                if approved:
                    self._notify_status("TOOL", {"tool_name": tool_name, "args": tool_args, "depth": depth})
                    tool_result = registry.execute(tool_name, tool_args, self.project_root)
                    step.result = tool_result.output
                    result.steps.append(step)
                    if self.on_step:
                        self.on_step(step)
                    self._notify_status("TOOL_DONE", {"tool_name": tool_name, "success": tool_result.success})

                    # Pin file content after READ_FILE so it survives compression
                    if (use_memory and tool_result.success and tool_name):
                        tname_upper = tool_name.upper()
                        if "READ_FILE" in tname_upper:
                            fpath = tool_args.get("path", "")
                            if fpath and tool_result.output:
                                memory.pin_file(fpath, tool_result.output)
                        elif "EDIT_FILE" in tname_upper or "WRITE_FILE" in tname_upper:
                            fpath = tool_args.get("path") or tool_args.get("file", "")
                            if fpath and hasattr(memory, "refresh_pin"):
                                memory.refresh_pin(fpath, self.project_root)

                    # Execution feedback: auto-run tests after code changes
                    if self.feedback_loop and tool_name and tool_name.upper() in ("EDIT_FILE", "WRITE_FILE", "RUN_COMMAND"):
                        test_run = self.feedback_loop.on_tool_executed(tool_name.upper(), tool_args, tool_result.output)
                        if test_run and not test_run.all_passed:
                            fb_ctx = self.feedback_loop.build_feedback_context()
                            if fb_ctx:
                                feedback += f"\n\n{fb_ctx}"

                    msg_type = "tool_result" if tool_result.success else "tool_error"
                    feedback = build_step_message(msg_type, tool_result.output)
                    if self.feedback_loop and self.feedback_loop._last_test_result and not self.feedback_loop._last_test_result.all_passed:
                        fb_ctx = self.feedback_loop.build_feedback_context()
                        if fb_ctx:
                            feedback += f"\n\n{fb_ctx}"

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
                    feedback = build_step_message("tool_denied", f"{tool_name} was denied.")

                if use_memory:
                    memory.add_assistant_message(response)
                    memory.add_user_message(feedback)
                else:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": feedback})

            elif action == "code":
                # Check if code modifies files or executes system commands
                modifies_files = bool(re.search(
                    r"\b(open\s*\(.*['\"][wa\+]|write_text|write_bytes|os\.remove|os\.unlink|"
                    r"os\.mkdir|os\.makedirs|os\.rename|shutil\.|subprocess\.|os\.system)\b",
                    content, re.IGNORECASE
                ))
                if modifies_files:
                    self._notify_status("WAITING_APPROVAL", {"tool_name": "CODE_FILE_WRITE", "risk": CONFIRM})
                else:
                    self._notify_status("TOOL", {"tool_name": "REPL_CODE", "depth": depth})

                approved = True
                if modifies_files and self.approval_fn:
                    tool_args = {"preview": content[:300]}
                    if asyncio.iscoroutinefunction(self.approval_fn):
                        approved = await self.approval_fn("CODE_FILE_WRITE", CONFIRM, tool_args)
                    else:
                        approved = self.approval_fn("CODE_FILE_WRITE", CONFIRM, tool_args)

                if approved:
                    self._notify_status("TOOL", {"tool_name": "REPL_CODE", "depth": depth})
                    async with sandbox_lock:
                        exec_result = self.sandbox.execute(content, cwd=self.project_root)
                else:
                    self._notify_status("TOOL_DENIED", {"tool_name": "REPL_CODE"})
                    exec_result = {"success": False, "error": "Code execution denied by user", "stdout": "", "stderr": ""}

                if exec_result["success"]:
                    consecutive_code_errors = 0
                    _last_tool_key = None
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
                    self._notify_status("TOOL_DONE", {"tool_name": "REPL_CODE", "success": True})
                else:
                    consecutive_code_errors += 1
                    error_msg = exec_result["error"] or "Unknown error"
                    if exec_result["stderr"]:
                        error_msg += f"\nstderr: {exec_result['stderr']}"
                    step.result = f"ERROR: {error_msg}"
                    last_code_output = None
                    feedback = build_step_message("code_error", error_msg)
                    if consecutive_code_errors >= 3:
                        feedback += "\n⚠️ Code execution has failed 3 times consecutively. Do not retry the same code. Change approach or return <FINAL_ANSWER>."
                    self._notify_status("TOOL_DONE", {"tool_name": "REPL_CODE", "success": False})

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
                        messages.append({"role": "user", "content": build_step_message("depth_limit", "")})
                else:
                    queries = [content] + extra_queries
                    step.content = " | ".join(queries)
                    self._notify_status("SUBAGENT", {"depth": depth + 1, "queries_count": len(queries)})

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
                        combined_answers.append(f"Sub-query [{queries[idx]}]: {sub_res.answer}")

                    aggregated_answer = "\n".join(combined_answers)
                    step.result = aggregated_answer
                    result.steps.append(step)
                    if self.on_step:
                        self.on_step(step)

                    if use_memory:
                        memory.add_assistant_message(response)
                        memory.add_user_message(build_step_message("sub_query_result", aggregated_answer))
                    else:
                        messages.append({"role": "assistant", "content": response})
                        messages.append({"role": "user", "content": build_step_message("sub_query_result", aggregated_answer)})

            else:
                consecutive_thinking += 1
                step.result = f"(No action tag detected — thinking loop {consecutive_thinking})"
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
                        step_number=iteration + 2, depth=depth,
                        action="final_answer", thinking=f"(auto-extracted after {MAX_THINKING_LOOPS} thinking loops)",
                        content=forced, result=forced,
                    )
                    result.steps.append(step_forced)
                    if self.on_step:
                        self.on_step(step_forced)
                    result.answer = forced
                    result.total_llm_calls = self._total_llm_calls
                    return result
                elif consecutive_thinking >= 4:
                    nudge = ("You MUST respond with exactly one action tag now. "
                             "If you have completed your work, wrap your response in <FINAL_ANSWER>your answer</FINAL_ANSWER>. "
                             "If you need to perform an action, use <TOOL> or <CODE>.")
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
            messages.append({"role": "user", "content": build_step_message("iteration_limit", "")})
            context = messages
            
        self._total_llm_calls += 1
        response = await self._stream_llm(context)
        _, _, final_content, _, _, _ = self._parse_response(response)

        if not final_content:
            final_content = response

        step = Step(step_number=MAX_ITERATIONS_PER_LEVEL + 1, depth=depth, action="final_answer",
                    thinking="(forced)", content=final_content, result=final_content)
        result.steps.append(step)
        if self.on_step:
            self.on_step(step)

        result.answer = final_content
        result.total_llm_calls = self._total_llm_calls
        return result

    def _parse_response(self, response: str) -> tuple[str, str, str, list[str], Optional[str], Optional[dict]]:
        """Parse the LLM response for action tags.
        Returns: (action, thinking, content, extra_queries, tool_name, tool_args)
        """
        # 1. Check for <tool_call>...</tool_call> (standard tag for Qwen / Llama models)
        tool_call_match = re.search(r'<tool_call>\s*(.*?)\s*</tool_call>', response, re.DOTALL | re.IGNORECASE)
        if tool_call_match:
            raw_payload = tool_call_match.group(1).strip()
            thinking = response[:tool_call_match.start()].strip()
            parsed_json = _clean_and_parse_json(raw_payload)
            
            tool_name = parsed_json.get("name") or parsed_json.get("tool") or parsed_json.get("action")
            tool_args = parsed_json.get("arguments") or parsed_json.get("args") or parsed_json
            
            if tool_name:
                t_name = str(tool_name).upper()
                if isinstance(tool_args, str):
                    tool_args = _clean_and_parse_json(tool_args)
                return ("tool", thinking, f"{t_name}({json.dumps(tool_args)})", [], t_name, tool_args)

        # 2. Check for <TOOL name="...">JSON</TOOL> or <tool name="...">JSON</tool>
        tool_match = re.search(
            r'<TOOL\s+name=["\'](\w+)["\']>\s*(.*?)\s*</TOOL>',
            response, re.DOTALL | re.IGNORECASE,
        )
        if tool_match:
            tool_name = tool_match.group(1).upper()
            raw_args = tool_match.group(2).strip()
            thinking = response[:tool_match.start()].strip()
            tool_args = _clean_and_parse_json(raw_args)
            return ("tool", thinking, f"{tool_name}({raw_args})", [], tool_name, tool_args)

        # 2b. Check for <action>NAME {JSON}</action> — fallback shape when grammar is off
        action_tag_match = re.search(
            r'<action>\s*(\w+)\s*(?:\{.*?\})?\s*</action>',
            response, re.DOTALL | re.IGNORECASE,
        )
        if action_tag_match:
            tool_name = action_tag_match.group(1).upper()
            thinking = response[:action_tag_match.start()].strip()
            # Try to extract JSON args from inside the tag
            tag_content = action_tag_match.group(0)
            json_match = re.search(r'\{.*\}', tag_content, re.DOTALL)
            if json_match:
                tool_args = _clean_and_parse_json(json_match.group(0))
            else:
                tool_args = {}
            return ("tool", thinking, f"{tool_name}({json.dumps(tool_args)})", [], tool_name, tool_args)

        # 3. Check for <WRITE_FILE path="...">content</WRITE_FILE>
        write_tag_match = re.search(
            r'<WRITE_FILE\s+path=["\']([^"\']+)["\']>\s*(.*?)\s*</WRITE_FILE>',
            response, re.DOTALL | re.IGNORECASE,
        )
        if write_tag_match:
            path_val = write_tag_match.group(1).strip()
            content_val = write_tag_match.group(2)
            thinking = response[:write_tag_match.start()].strip()
            return ("tool", thinking, f"WRITE_FILE({path_val})", [], "WRITE_FILE", {"path": path_val, "content": content_val})

        # 3b. Check for JSON array output (fallback for Qwen JSON outputs)
        json_array_match = re.search(r'(?:```(?:json)?\s*)?(\[\s*\{\s*["\'](?:tool_name|name|action|tool)["\'].*?\}\s*\])(?:\s*```)?', response, re.DOTALL | re.IGNORECASE)
        if json_array_match:
            try:
                first_tool = _clean_and_parse_json(json_array_match.group(1))
                if first_tool and isinstance(first_tool, dict):
                    t_name = (first_tool.get("tool_name") or first_tool.get("name") or first_tool.get("action") or first_tool.get("tool") or "").upper()
                    if t_name:
                        t_args = first_tool.get("params") or first_tool.get("arguments") or first_tool.get("args")
                        if t_args is None:
                            t_args = dict(first_tool)
                            t_args.pop("tool_name", None)
                            t_args.pop("name", None)
                            t_args.pop("action", None)
                            t_args.pop("tool", None)
                        
                        thinking = response[:json_array_match.start()].strip()
                        return ("tool", thinking, f"{t_name}({json.dumps(t_args)})", [], t_name, t_args)
            except Exception:
                pass

        # 4. Check for <CODE>...</CODE>
        code_match = re.search(r"<CODE>(.*?)</CODE>", response, re.DOTALL | re.IGNORECASE)
        if code_match:
            content = code_match.group(1).strip()
            thinking = response[:code_match.start()].strip()
            
            # Check if code block specifies a target file writing intent (e.g. # file: path/foo.py or # filename: foo.py)
            file_match = re.search(r"^(?:#|//)\s*(?:file|filename|filepath|path)\s*:\s*([^\n\r]+)", content, re.IGNORECASE)
            if file_match:
                target_path = file_match.group(1).strip()
                # Remove header line from content
                cleaned_content = re.sub(r"^(?:#|//)\s*(?:file|filename|filepath|path)\s*:\s*[^\n\r]+\n?", "", content).strip()
                return ("tool", thinking, f"WRITE_FILE({target_path})", [], "WRITE_FILE", {"path": target_path, "content": cleaned_content})

            return ("code", thinking, content, [], None, None)

        # 5. Check for <SUB_QUERY>...</SUB_QUERY>
        sub_query_matches = re.findall(r"<SUB_QUERY>(.*?)</SUB_QUERY>", response, re.DOTALL | re.IGNORECASE)
        if sub_query_matches:
            first_tag_pos = response.lower().find("<sub_query>")
            thinking = response[:first_tag_pos].strip() if first_tag_pos != -1 else ""
            return ("sub_queries", thinking, sub_query_matches[0].strip(),
                    [q.strip() for q in sub_query_matches[1:]], None, None)

        # 6. Check for <FINAL_ANSWER>...</FINAL_ANSWER>
        final_match = re.search(r"<FINAL_ANSWER>(.*?)</FINAL_ANSWER>", response, re.DOTALL | re.IGNORECASE)
        if final_match:
            content = final_match.group(1).strip()
            thinking = response[:final_match.start()].strip()
            return ("final_answer", thinking, content, [], None, None)

        return ("thinking", response.strip(), "", [], None, None)
