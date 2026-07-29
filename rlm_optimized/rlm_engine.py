import re
from typing import Optional, Callable
from dataclasses import dataclass, field
from rlm_optimized.config import MAX_RECURSION_DEPTH, MAX_ITERATIONS_PER_LEVEL
from rlm_optimized.repl_sandbox import REPLSandbox
from rlm_optimized.prompts import SYSTEM_PROMPT, build_step_message

try:
    from core.memory.token_counter import get_token_counter
except ImportError:
    pass

try:
    from core.compression.summarizer import ConversationSummarizer
    from core.memory.models import Message, MessageRole
    from core.memory.manager import TieredMemory, MemoryConfig
    _summarizer = ConversationSummarizer()
except ImportError:
    _summarizer = None
    TieredMemory = None
    MemoryConfig = None

@dataclass
class Step:
    step_number: int
    depth: int
    action: str            # "code", "sub_query", "final_answer", "thinking"
    thinking: str
    content: str
    result: Optional[str] = None

@dataclass
class SolveResult:
    answer: str
    steps: list[Step] = field(default_factory=list)
    depth: int = 0
    total_llm_calls: int = 0

class RLMEngine:
    def __init__(self, client=None, on_step: Optional[Callable[[Step], None]] = None, max_depth: int = MAX_RECURSION_DEPTH):
        if client is None:
            from rlm_optimized.config import PROVIDER
            if PROVIDER in ("llama-cpp", "lmstudio", "turbo", "turboquant"):
                from rlm_optimized.llamacpp_client import LlamaCppClient
                client = LlamaCppClient()
            else:
                from rlm_optimized.ollama_client import OllamaClient
                client = OllamaClient()
        self.client = client
        self.on_step = on_step
        self.max_depth = max_depth
        self.sandbox = REPLSandbox()
        self._total_llm_calls = 0
        self.sandbox.set_llm_query_fn(self._sandbox_llm_query)

    def _sandbox_llm_query(self, prompt: str) -> str:
        return self.client.query(prompt)

    def solve(self, task: str, depth: int = 0) -> SolveResult:
        result = SolveResult(answer="", depth=depth)
        
        if TieredMemory and MemoryConfig:
            from .config import CTX_SIZE
            memory = TieredMemory(config=MemoryConfig.auto_tune(max_tokens=CTX_SIZE))
            memory.add_system_message(SYSTEM_PROMPT)
            memory.add_user_message(task)
            use_memory = True
        else:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": task},
            ]
            use_memory = False

        REPEAT_LIMIT = 2  # how many identical actions in a row before we force an answer
        consecutive_repeats = 0
        last_signature = None

        for iteration in range(MAX_ITERATIONS_PER_LEVEL):
            self._total_llm_calls += 1
            
            if use_memory:
                if memory.should_compress():
                    summarizer_fn = _summarizer.simple_summarize if _summarizer else None
                    memory.compress_recent(summarizer_fn=summarizer_fn, preserve_first=2)
                context = memory.get_context_for_llm()
            else:
                context = messages

            response = self.client.chat_with_history(context)
            action, thinking, content = self._parse_response(response)

            step = Step(step_number=iteration + 1, depth=depth, action=action, thinking=thinking, content=content)

            # --- Repeat detection
            signature = (action, content.strip()) if action in ("code", "sub_query") else None
            if signature is not None and signature == last_signature:
                consecutive_repeats += 1
            else:
                consecutive_repeats = 0
            last_signature = signature

            if signature is not None and consecutive_repeats >= 1:
                step.result = (
                    f"(Skipped executing — identical {action} action repeated "
                    f"{consecutive_repeats + 1}x in a row; not re-running it)"
                )
                result.steps.append(step)
                if self.on_step:
                    self.on_step(step)
                if use_memory:
                    memory.add_assistant_message(response)
                else:
                    messages.append({"role": "assistant", "content": response})

                if consecutive_repeats >= REPEAT_LIMIT:
                    forced = content or response.strip()
                    step_forced = Step(
                        step_number=iteration + 2, depth=depth, action="final_answer",
                        thinking=f"(auto-extracted after {consecutive_repeats + 1} repeated {action} actions)",
                        content=forced, result=forced,
                    )
                    result.steps.append(step_forced)
                    if self.on_step:
                        self.on_step(step_forced)
                    result.answer = forced
                    result.total_llm_calls = self._total_llm_calls
                    return result

                nudge = (
                    f"You repeated the exact same {action} action you already ran — "
                    "it will produce the same result again, not new information. "
                    "Try a genuinely different approach, or if you already have enough "
                    "information, respond now with <FINAL_ANSWER>your answer</FINAL_ANSWER>."
                )
                if use_memory:
                    memory.add_user_message(nudge)
                else:
                    messages.append({"role": "user", "content": nudge})
                continue

            if action == "final_answer":
                step.result = content
                result.steps.append(step)
                if self.on_step:
                    self.on_step(step)
                result.answer = content
                result.total_llm_calls = self._total_llm_calls
                return result

            elif action == "code":
                exec_result = self.sandbox.execute(content)
                if exec_result["success"]:
                    output = exec_result["stdout"].strip()
                    if not output:
                        output = "(Code executed successfully, no output)"
                    
                    MAX_OUTPUT_LENGTH = 2000
                    if len(output) > MAX_OUTPUT_LENGTH:
                        output = output[:MAX_OUTPUT_LENGTH] + "\n... [Output truncated]"
                        
                    step.result = output
                    feedback = build_step_message("code_result", output)
                else:
                    error_msg = exec_result["error"] or "Unknown error"
                    if exec_result["stderr"]:
                        error_msg += f"\nstderr: {exec_result['stderr']}"
                    step.result = f"ERROR: {error_msg}"
                    feedback = build_step_message("code_error", error_msg)

                result.steps.append(step)
                if self.on_step:
                    self.on_step(step)

                if use_memory:
                    memory.add_assistant_message(response)
                    memory.add_user_message(feedback)
                else:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": feedback})

            elif action == "sub_query":
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
                    sub_result = self.solve(content, depth=depth + 1)
                    step.result = sub_result.answer
                    result.steps.extend(sub_result.steps)
                    result.steps.append(step)
                    if self.on_step:
                        self.on_step(step)

                    if use_memory:
                        memory.add_assistant_message(response)
                        memory.add_user_message(build_step_message("sub_query_result", sub_result.answer))
                    else:
                        messages.append({"role": "assistant", "content": response})
                        messages.append({"role": "user", "content": build_step_message("sub_query_result", sub_result.answer)})

            else:
                step.result = "(No action tag detected — prompting model to continue)"
                result.steps.append(step)
                if self.on_step:
                    self.on_step(step)

                if use_memory:
                    memory.add_assistant_message(response)
                    memory.add_user_message("Please continue with an action. Use <CODE>, <SUB_QUERY>, or <FINAL_ANSWER>.")
                else:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": "Please continue with an action. Use <CODE>, <SUB_QUERY>, or <FINAL_ANSWER>."})

        if use_memory:
            memory.add_user_message(build_step_message("iteration_limit", ""))
            context = memory.get_context_for_llm()
        else:
            messages.append({"role": "user", "content": build_step_message("iteration_limit", "")})
            context = messages
            
        self._total_llm_calls += 1
        final_response = self.client.chat_with_history(context)
        _, _, final_content = self._parse_response(final_response)

        if not final_content:
            final_content = final_response

        step = Step(step_number=MAX_ITERATIONS_PER_LEVEL + 1, depth=depth, action="final_answer", thinking="(forced)", content=final_content, result=final_content)
        result.steps.append(step)
        if self.on_step:
            self.on_step(step)

        result.answer = final_content
        result.total_llm_calls = self._total_llm_calls
        return result

    def _parse_response(self, response: str) -> tuple[str, str, str]:
        explicit_thinking = ""
        think_match = re.search(r'<(?:think|thought|thinking|reasoning)>(.*?)(?:</(?:think|thought|thinking|reasoning)>|$)', response, re.DOTALL | re.IGNORECASE)
        if think_match:
            explicit_thinking = think_match.group(1).strip()
        else:
            prefix_match = re.match(
                r'^\s*(?:thought\s+|\[(?:thought|thinking|reasoning|plan)\][:\s]*|(?:thought|thinking|reasoning|plan)(?:\s+process)?\s*[\n\r:]\s*|(?:chain\s*of\s*thought)[:\s]+)(.*)',
                response, re.DOTALL | re.IGNORECASE
            )
            if prefix_match:
                explicit_thinking = prefix_match.group(1).strip()

        def _get_thinking(tag_start_pos: int) -> str:
            pre_tag_text = response[:tag_start_pos].strip()
            cleaned_pre = re.sub(r'<(?:think|thought|thinking|reasoning)>[\s\S]*?(?:</(?:think|thought|thinking|reasoning)>|$)', '', pre_tag_text, flags=re.IGNORECASE).strip()
            cleaned_pre = re.sub(r'^\s*(?:thought\s+|\[(?:thought|thinking|reasoning|plan)\][:\s]*|(?:thought|thinking|reasoning|plan)(?:\s+process)?\s*[\n\r:]\s*|(?:chain\s*of\s*thought)[:\s]+)', '', cleaned_pre, flags=re.IGNORECASE).strip()
            if explicit_thinking and cleaned_pre and cleaned_pre not in explicit_thinking:
                return f"{explicit_thinking}\n\n{cleaned_pre}"
            return explicit_thinking or cleaned_pre

        code_match = re.search(r"<CODE(?:\s+[^>]*)?>(.*?)(?:</CODE>|$)", response, re.DOTALL)
        if not code_match:
            code_match = re.search(r"(?<!`)<CODE(?:\s+[^>]*)?>(.*?)</(?:CODE|code)>", response, re.DOTALL | re.IGNORECASE)

        sub_query_match = re.search(r"<SUB_QUERY>(.*?)(?:</SUB_QUERY>|$)", response, re.DOTALL | re.IGNORECASE)
        final_match = re.search(r"<FINAL_ANSWER>(.*?)(?:</FINAL_ANSWER>|$)", response, re.DOTALL | re.IGNORECASE)

        matches = []
        if code_match:
            matches.append(("code", code_match))
        if sub_query_match:
            matches.append(("sub_query", sub_query_match))
        if final_match:
            raw_content = final_match.group(1).strip()
            pre_text = response[:final_match.start()].strip()
            is_template = bool(re.match(r"^(?:your|the)?\s*(?:complete\s+)?answer$", raw_content.lower()))
            is_mid_sentence = bool(re.search(r"\b(?:use|using|with|by|in|written|into|output|tag|provide|format|wrap)\s*[`'\"]*$", pre_text, re.IGNORECASE))
            if not is_template and not is_mid_sentence and raw_content:
                matches.append(("final_answer", final_match))

        if matches:
            matches.sort(key=lambda x: x[1].start())
            first_action, match = matches[0]
            content = match.group(1).strip()
            if first_action == "code":
                content = re.sub(r'^\s*```(?:python|py)?\s*\n?', '', content, flags=re.IGNORECASE)
                content = re.sub(r'\n?\s*```\s*$', '', content).strip()
            thinking = _get_thinking(match.start())
            return (first_action, thinking, content)

        cleaned_body = re.sub(r'<(?:think|thought|thinking|reasoning)>[\s\S]*?(?:</(?:think|thought|thinking|reasoning)>|$)', '', response, flags=re.IGNORECASE).strip()
        has_unclosed = bool(re.search(r'<(?:TOOL|CODE|SUB_QUERY|WRITE_FILE|action)\b', cleaned_body, re.IGNORECASE))
        
        reasoning_prefix_match = re.match(
            r'^\s*(?:thought\s+|\[(?:thought|thinking|reasoning|plan)\][:\s]*|(?:thought|thinking|reasoning|plan)(?:\s+process)?\s*[\n\r:]\s*|(?:chain\s*of\s*thought)[:\s]+)',
            response.strip(), re.IGNORECASE
        )
        is_planning_cot = (
            bool(reasoning_prefix_match) or
            bool(re.search(r'\b(?:LIST_DIR|READ_FILE|EDIT_FILE|WRITE_FILE|GREP|SEARCH_AST|EXECUTE|RUN_COMMAND)\b', cleaned_body)) or
            bool(re.match(r'^(?:1[\.\s]|step\s*1|first,|I\s+will\s+start|I\s+need\s+to\s+first)', cleaned_body, re.IGNORECASE))
        )

        if is_planning_cot and not has_unclosed:
            thinking_text = explicit_thinking or cleaned_body
            if reasoning_prefix_match:
                thinking_text = re.sub(r'^\s*(?:thought\s+|\[(?:thought|thinking|reasoning|plan)\][:\s]*|(?:thought|thinking|reasoning|plan)(?:\s+process)?\s*[\n\r:]\s*|(?:chain\s*of\s*thought)[:\s]+)', '', cleaned_body, flags=re.IGNORECASE).strip()
            return ("thinking", thinking_text or cleaned_body, "")

        if not has_unclosed and cleaned_body:
            if explicit_thinking:
                return ("final_answer", explicit_thinking, cleaned_body)
            final_cleaned = re.sub(r'</?FINAL_ANSWER>', '', cleaned_body, flags=re.IGNORECASE).strip()
            if final_cleaned:
                return ("final_answer", "", final_cleaned)

        return ("thinking", response.strip(), "")

    def reset(self):
        self.sandbox.reset()
        self._total_llm_calls = 0