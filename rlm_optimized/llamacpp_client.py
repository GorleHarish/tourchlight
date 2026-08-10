import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from typing import Generator, Optional

from rlm_optimized.config import (
    GRAMMAR_FILE,
    LOCAL_API_BASE_URL,
    MODEL_NAME,
    NUM_PREDICT,
    TEMPERATURE,
    TOP_P,
    USE_GRAMMAR_CONSTRAINT,
)
from core.api.base import InferenceParams, detect_model_traits

# Local models at ~8-12 tok/s can legitimately take minutes on a large
# (multi-thousand-token) context. The previous 60s timeout caused the client
# to drop the connection mid-generation, which made llama-server cancel the
# task ("srv stop: cancel task") and killed the whole solve loop. 300s is a
# safe bound for streaming reads; the engine's per-chunk stall guard still
# detects genuine hangs much sooner.
REQUEST_TIMEOUT = int(os.environ.get("RLM_REQUEST_TIMEOUT", "300"))


def _sanitize_messages(messages: list) -> list:
    """Ensure strict role alternation (user, assistant...) and merge consecutive same-role messages.

    Empty-content turns are preserved (only empty system turns are dropped) so
    prompt turn-taking structure is never silently altered.
    """
    if not messages:
        return []
    sanitized: list[dict] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content")
        if content is None:
            content = ""
        elif not isinstance(content, str):
            content = str(content)
        if not content and role == "system":
            continue
        if sanitized and sanitized[-1]["role"] == role and role != "system":
            prev = sanitized[-1]
            if prev["content"] and content:
                prev["content"] += f"\n\n{content}"
            elif content:
                prev["content"] = content
        else:
            sanitized.append({"role": role, "content": content})
    return sanitized


def _context_limit_message(err_body: str) -> str:
    """Friendly remediation for llama-server 'context exceeded' errors."""
    return (
        f"llama-server context limit exceeded: {err_body}\n"
        f"To resolve this issue:\n"
        f" 1. Restart llama-server with a larger context window: "
        f"`./rlm_optimized/start_optimized_local.sh` (defaults to 12288) "
        f"or run `llama-server -c 12288`\n"
        f" 2. Or set `export RLM_CTX_SIZE=8192` to match your server's current "
        f"context limit so Torchlight compresses context earlier."
    )


class LlamaCppClient:
    def __init__(self, base_url: str = LOCAL_API_BASE_URL, model: str = MODEL_NAME):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.traits = detect_model_traits(self.model)
        calibrated = InferenceParams.for_model_and_phase(self.model, "code")
        self.temperature = calibrated.temperature
        self.repeat_penalty = calibrated.repeat_penalty
        self.presence_penalty = calibrated.presence_penalty
        self.frequency_penalty = calibrated.frequency_penalty
        self.min_p = calibrated.min_p
        self._grammar_content = self._load_grammar()
        print(
            f"[LlamaCppClient] connecting to {self.base_url} (model={self.model}, "
            f"rep_pen={self.repeat_penalty}, temp={self.temperature})"
        )

    def _load_grammar(self) -> Optional[str]:
        if not USE_GRAMMAR_CONSTRAINT:
            return None
        if GRAMMAR_FILE and os.path.exists(GRAMMAR_FILE):
            try:
                with open(GRAMMAR_FILE, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(
                    f"[LlamaCppClient] WARNING: Failed to read grammar file {GRAMMAR_FILE}: {e}"
                )
        else:
            print(
                f"[LlamaCppClient] WARNING: grammar file not found at {GRAMMAR_FILE} — "
                f"model output will be unconstrained and may use unrecognized tags."
            )
        return None

    def is_running(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/models", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status == 200
        except Exception:
            return False

    def is_model_available(self) -> bool:
        return self.is_running()

    def query(
        self,
        prompt: str,
        system_prompt: str = "",
        messages: Optional[list] = None,
        max_retries: int = 3,
        use_grammar: bool = True,
    ) -> str:
        request_url = f"{self.base_url}/chat/completions"

        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        cleaned_messages = _sanitize_messages(messages)

        def _make_payload(include_extra=True):
            p = {
                "model": self.model,
                "messages": cleaned_messages,
                "temperature": self.temperature,
                "top_p": TOP_P,
                "min_p": getattr(self, "min_p", 0.05),
                "max_tokens": NUM_PREDICT,
                "presence_penalty": getattr(self, "presence_penalty", 0.0),
                "frequency_penalty": getattr(self, "frequency_penalty", 0.0),
                "stop": [
                    "</tool_call>",
                    "</WRITE_FILE>",
                    "</TOOL>",
                    "</CODE>",
                    "</FINAL_ANSWER>",
                    "</SUB_QUERY>",
                    "</ERROR>",
                    "</action>",
                    "\nAction:",
                    "Action:",
                    "Observation:",
                    "<|im_end|>",
                    "<|endoftext|>",
                    "<|im_start|>",
                    "</s>",
                ],
            }
            if include_extra:
                if getattr(self, "repeat_penalty", 1.0) != 1.0:
                    p["repeat_penalty"] = getattr(self, "repeat_penalty", 1.0)
                if use_grammar and self._grammar_content:
                    p["grammar"] = self._grammar_content
            return p

        def _extract_content(res_body) -> str:
            try:
                return res_body["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                raise ConnectionError(
                    "Unexpected API response — missing 'choices[0].message.content': "
                    f"{str(res_body)[:500]}"
                ) from exc

        headers = {"Content-Type": "application/json"}
        standard_payload_tried = False

        for attempt in range(max_retries):
            # Keep grammar/repeat_penalty on retries — only strip them once when the
            # server explicitly rejects them with a 400 (fallback below).
            payload = _make_payload(include_extra=not standard_payload_tried)
            data = json.dumps(payload).encode("utf-8")
            try:
                req = urllib.request.Request(
                    request_url, data=data, headers=headers, method="POST"
                )
                with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                    res_body = json.loads(response.read().decode("utf-8"))
                    return _extract_content(res_body)
            except urllib.error.HTTPError as e:
                err_body = ""
                try:
                    err_body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                if e.code == 404 and "/v1" in request_url:
                    request_url = request_url.replace("/v1", "")
                    continue
                if e.code == 400:
                    if "exceed" in err_body.lower() or "context" in err_body.lower():
                        raise ConnectionError(_context_limit_message(err_body)) from e
                    if not standard_payload_tried:
                        # Server rejected grammar/repeat_penalty — retry once with a standard payload
                        standard_payload_tried = True
                        try:
                            std_data = json.dumps(
                                _make_payload(include_extra=False)
                            ).encode("utf-8")
                            req_std = urllib.request.Request(
                                request_url,
                                data=std_data,
                                headers=headers,
                                method="POST",
                            )
                            with urllib.request.urlopen(
                                req_std, timeout=REQUEST_TIMEOUT
                            ) as response:
                                res_body = json.loads(response.read().decode("utf-8"))
                                return _extract_content(res_body)
                        except Exception as fallback_err:
                            err_body += f" | Fallback error: {fallback_err}"
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
                    continue
                msg = (
                    f"llama-server connection error: {e} ({err_body})"
                    if err_body
                    else f"llama-server connection error: {e}"
                )
                raise ConnectionError(msg) from e
            except urllib.error.URLError as e:
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
                    continue
                raise ConnectionError(
                    f"Local engine server connection error on {self.base_url}: {e}. "
                    f"Ensure llama-server or MLX server is running."
                ) from e
        raise ConnectionError("llama-server request failed after all retries")

    def chat_with_history(self, messages: list, use_grammar: bool = True) -> str:
        return self.query(prompt="", messages=messages, use_grammar=use_grammar)

    def stream_chat_with_history(
        self, messages: list, use_grammar: bool = True
    ) -> Generator[str, None, None]:
        request_url = f"{self.base_url}/chat/completions"
        cleaned_messages = _sanitize_messages(messages)
        headers = {"Content-Type": "application/json"}

        def _make_payload(include_extra=True):
            p = {
                "model": self.model,
                "messages": cleaned_messages,
                "temperature": self.temperature,
                "top_p": TOP_P,
                "min_p": getattr(self, "min_p", 0.05),
                "max_tokens": NUM_PREDICT,
                "presence_penalty": getattr(self, "presence_penalty", 0.0),
                "frequency_penalty": getattr(self, "frequency_penalty", 0.0),
                "stop": [
                    "</tool_call>",
                    "</WRITE_FILE>",
                    "</TOOL>",
                    "</CODE>",
                    "</FINAL_ANSWER>",
                    "</SUB_QUERY>",
                    "</ERROR>",
                    "</action>",
                    "\nAction:",
                    "Action:",
                    "Observation:",
                    "<|im_end|>",
                    "<|endoftext|>",
                    "<|im_start|>",
                    "</s>",
                ],
                "stream": True,
            }
            if include_extra:
                if getattr(self, "repeat_penalty", 1.0) != 1.0:
                    p["repeat_penalty"] = getattr(self, "repeat_penalty", 1.0)
                if use_grammar and self._grammar_content:
                    p["grammar"] = self._grammar_content
            return p

        def _iter_stream(target_url: str, include_extra: bool = True):
            req = urllib.request.Request(
                target_url,
                data=json.dumps(_make_payload(include_extra)).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                for line in response:
                    line_str = line.decode("utf-8").strip()
                    if not line_str.startswith("data: "):
                        continue
                    data_content = line_str[6:]
                    if data_content == "[DONE]":
                        return
                    try:
                        chunk = json.loads(data_content)
                        delta = chunk["choices"][0]["delta"]
                        if delta.get("content"):
                            yield delta["content"]
                    except Exception:
                        continue

        standard_payload_tried = False
        for attempt in range(3):
            try:
                yield from _iter_stream(request_url, not standard_payload_tried)
                return
            except urllib.error.HTTPError as e:
                err_body = ""
                try:
                    err_body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                if e.code == 404 and "/v1" in request_url:
                    request_url = request_url.replace("/v1", "")
                    continue
                if e.code == 400 and (
                    "exceed" in err_body.lower() or "context" in err_body.lower()
                ):
                    raise ConnectionError(_context_limit_message(err_body)) from e
                if not standard_payload_tried:
                    # Server rejected grammar — retry once with a standard payload
                    standard_payload_tried = True
                    continue
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                msg = (
                    f"llama-server streaming error: {e} ({err_body})"
                    if err_body
                    else f"llama-server streaming error: {e}"
                )
                raise ConnectionError(msg) from e
            except urllib.error.URLError as e:
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise ConnectionError(
                    f"Local engine server connection error on {self.base_url}: {e}. "
                    f"Ensure llama-server or MLX server is running."
                ) from e

    async def chat(
        self, messages: list, params: Optional[object] = None, use_grammar: bool = True
    ) -> str:
        """Async implementation of chat protocol method required by LLMClient / DebateVerifier."""
        if params is not None and getattr(params, "use_grammar", None) is not None:
            use_grammar = params.use_grammar
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.query, "", "", messages, 3, use_grammar
        )

    async def chat_stream(
        self, messages: list, params: Optional[object] = None, use_grammar: bool = True
    ):
        """Async streaming implementation required by LLMClient protocol.

        Runs the blocking sync generator in a worker thread so the async
        event loop is never blocked while tokens stream in.
        """
        if params is not None and getattr(params, "use_grammar", None) is not None:
            use_grammar = params.use_grammar
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        sentinel = object()

        def _produce():
            try:
                for token in self.stream_chat_with_history(
                    messages, use_grammar=use_grammar
                ):
                    loop.call_soon_threadsafe(queue.put_nowait, token)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, e)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, sentinel)

        loop.run_in_executor(None, _produce)
        while True:
            item = await queue.get()
            if item is sentinel:
                break
            if isinstance(item, Exception):
                raise item
            yield item
