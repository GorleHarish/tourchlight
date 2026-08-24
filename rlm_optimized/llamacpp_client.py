import asyncio
import json
import os
import re
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


def _strip_multimodal_images(messages: list[dict]) -> list[dict]:
    """Convert multimodal image_url content blocks to pure text descriptions for text-only servers."""
    if not messages:
        return []
    stripped: list[dict] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content")
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict):
                    p_type = part.get("type")
                    if p_type == "text":
                        text_parts.append(part.get("text", ""))
                    elif p_type == "image_url":
                        text_parts.append("[Attached Image: use VIEW_IMAGE tool to inspect]")
                    else:
                        text_parts.append(str(part))
                elif isinstance(part, str):
                    text_parts.append(part)
            new_content = "\n\n".join(tp for tp in text_parts if tp).strip()
            stripped.append({"role": role, "content": new_content})
        else:
            stripped.append({"role": role, "content": content})
    return stripped


def _sanitize_messages(messages: list[dict]) -> list[dict]:
    """Sanitize message roles and preserve multimodal content blocks."""
    if not messages:
        return []
    sanitized: list[dict] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content")
        if content is None:
            content = ""
        elif not isinstance(content, (str, list)):
            content = str(content)
        if not content and role == "system":
            continue
        if sanitized and sanitized[-1]["role"] == role and role != "system":
            prev = sanitized[-1]
            prev_c = prev.get("content")
            if isinstance(prev_c, str) and isinstance(content, str):
                if prev_c and content:
                    prev["content"] = f"{prev_c}\n\n{content}"
                elif content:
                    prev["content"] = content
            else:
                p_parts = [{"type": "text", "text": prev_c}] if isinstance(prev_c, str) else list(prev_c)
                c_parts = [{"type": "text", "text": content}] if isinstance(content, str) else list(content)
                prev["content"] = p_parts + c_parts
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


def _is_model_loading_error(e: urllib.error.HTTPError, err_body: str) -> bool:
    """Detect if HTTPError represents llama-server currently loading model weights."""
    if e.code == 503:
        return True
    lower_body = err_body.lower()
    return "loading model" in lower_body or "unavailable_error" in lower_body


def _wait_for_server_ready(base_url: str, timeout: float = 60.0, print_progress: bool = True) -> bool:
    """Poll llama-server health/models endpoint until the model finishes loading."""
    start_time = time.time()
    last_print = 0.0
    while time.time() - start_time < timeout:
        # Check /health endpoint first (native llama-server)
        try:
            req = urllib.request.Request(f"{base_url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    try:
                        h_data = json.loads(resp.read().decode("utf-8"))
                        status = str(h_data.get("status", "")).lower()
                        if status in ("ok", "ready", "loaded"):
                            return True
                        if "loading" in status:
                            if print_progress and (time.time() - last_print > 3.0):
                                print(
                                    f"[LlamaCppClient] Waiting for model weights to finish loading ({int(time.time() - start_time)}s)..."
                                )
                                last_print = time.time()
                            time.sleep(1.5)
                            continue
                    except Exception:
                        return True
                    return True
        except urllib.error.HTTPError as he:
            if he.code == 503:
                if print_progress and (time.time() - last_print > 3.0):
                    print(
                        f"[LlamaCppClient] llama-server reports model loading (HTTP 503) — waiting for readiness ({int(time.time() - start_time)}s)..."
                    )
                    last_print = time.time()
                time.sleep(1.5)
                continue
        except Exception:
            pass

        # Fallback check on /v1/models or /models
        for endpoint in (f"{base_url}/v1/models", f"{base_url}/models"):
            try:
                m_req = urllib.request.Request(endpoint, method="GET")
                with urllib.request.urlopen(m_req, timeout=3) as resp:
                    if resp.status == 200:
                        return True
            except urllib.error.HTTPError as he:
                if he.code == 503:
                    if print_progress and (time.time() - last_print > 3.0):
                        print(
                            f"[LlamaCppClient] llama-server reports model loading (HTTP 503) — waiting for readiness ({int(time.time() - start_time)}s)..."
                        )
                        last_print = time.time()
                    time.sleep(1.5)
                    break
            except Exception:
                pass
        time.sleep(1.5)
    return False


class LlamaCppClient:
    def __init__(self, base_url: str = LOCAL_API_BASE_URL, model: str = MODEL_NAME):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.traits = detect_model_traits(self.model)
        self.is_vision = self.traits.get("is_vision", False)
        self._server_supports_vision = self.is_vision
        calibrated = InferenceParams.for_model_and_phase(self.model, "code")
        self.temperature = calibrated.temperature
        self.repeat_penalty = calibrated.repeat_penalty
        self.repetition_penalty = calibrated.repetition_penalty or calibrated.repeat_penalty
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
            req = urllib.request.Request(f"{self.base_url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status in (200, 503):
                    return True
        except urllib.error.HTTPError as e:
            if e.code == 503:
                return True
        except Exception:
            pass
        try:
            req = urllib.request.Request(f"{self.base_url}/models", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status in (200, 503)
        except urllib.error.HTTPError as e:
            if e.code == 503:
                return True
        except Exception:
            return False

    def is_model_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    try:
                        h_data = json.loads(response.read().decode("utf-8"))
                        return str(h_data.get("status", "")).lower() in ("ok", "ready", "loaded")
                    except Exception:
                        return True
        except Exception:
            pass
        try:
            req = urllib.request.Request(f"{self.base_url}/models", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status == 200
        except Exception:
            return False


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

        if not getattr(self, "_server_supports_vision", True):
            messages = _strip_multimodal_images(messages)

        cleaned_messages = _sanitize_messages(messages)

        def _make_payload(include_extra=True):
            p = {
                "model": self.model,
                "messages": cleaned_messages,
                "temperature": self.temperature,
                "top_p": TOP_P,
                "min_p": getattr(self, "min_p", 0.05),
                "max_tokens": NUM_PREDICT,
                "presence_penalty": getattr(self, "presence_penalty", 0.15),
                "frequency_penalty": getattr(self, "frequency_penalty", 0.10),
                "stop": [
                    "</tool_call>",
                    "<|tool_call_end|>",
                    "</WRITE_FILE>",
                    "</TOOL>",
                    "</CODE>",
                    "</FINAL_ANSWER>",
                    "</SUB_QUERY>",
                    "</ERROR>",
                    "</action>",
                    "<|im_end|>",
                    "<|endoftext|>",
                    "<|im_start|>",
                    "</s>",
                ],
            }
            if include_extra:
                rep_pen = getattr(
                    self, "repetition_penalty", getattr(self, "repeat_penalty", 1.0)
                )
                if rep_pen != 1.0:
                    p["repeat_penalty"] = rep_pen
                    p["repetition_penalty"] = rep_pen
                    p["repetition_context_size"] = 256
                    p["repeat_last_n"] = 256
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
            payload = _make_payload(not standard_payload_tried)
            try:
                req = urllib.request.Request(
                    request_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST",
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
                if "not a directory" in err_body.lower() and "config.json" in err_body.lower():
                    raise ConnectionError(
                        f"Inference Backend Mismatch on {self.base_url}: An MLX server (mlx_lm.server) is active on port 8080, "
                        f"but LlamaCppClient sent a GGUF request ({err_body}). "
                        f"Please switch the Engine backend to 'MLX' in the sidebar or restart llama-server."
                    ) from e
                if _is_model_loading_error(e, err_body):
                    print(
                        f"[LlamaCppClient] llama-server is currently loading model weights (HTTP 503). "
                        f"Waiting for server readiness..."
                    )
                    if _wait_for_server_ready(self.base_url, timeout=60.0):
                        continue
                    raise ConnectionError(
                        f"llama-server model loading timed out after 60s: {e} ({err_body}). "
                        f"Please ensure llama-server has finished loading the GGUF model into memory."
                    ) from e
                if e.code == 404 and "/v1" in request_url:
                    request_url = request_url.replace("/v1", "")
                    continue
                if "image input is not supported" in err_body.lower() or "mmproj" in err_body.lower():
                    self._server_supports_vision = False
                    self.is_vision = False
                    cleaned_messages = _strip_multimodal_images(cleaned_messages)
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

    def chat_with_history(self, messages: list, use_grammar: bool = True) -> str:
        return self.query(prompt="", messages=messages, use_grammar=use_grammar)

    def stream_chat_with_history(self, messages: list) -> Generator[str, None, None]:
        """Stream chat completion tokens from llama-server using OpenAI-compatible SSE format."""
        request_url = f"{self.base_url}/chat/completions"
        use_grammar = USE_GRAMMAR_CONSTRAINT and bool(self._grammar_content)

        if not getattr(self, "_server_supports_vision", True):
            messages = _strip_multimodal_images(messages)

        cleaned_messages = _sanitize_messages(messages)

        def _make_payload(include_extra=True):
            payload_model = (
                os.path.basename(self.model).replace(".gguf", "")
                if isinstance(self.model, str) and self.model.endswith(".gguf")
                else (self.model or "default")
            )
            p = {
                "model": payload_model,
                "messages": cleaned_messages,
                "temperature": self.temperature,
                "top_p": TOP_P,
                "min_p": getattr(self, "min_p", 0.05),
                "max_tokens": NUM_PREDICT,
                "presence_penalty": getattr(self, "presence_penalty", 0.15),
                "frequency_penalty": getattr(self, "frequency_penalty", 0.10),
                "stop": [
                    "</tool_call>",
                    "<|tool_call_end|>",
                    "</WRITE_FILE>",
                    "</TOOL>",
                    "</CODE>",
                    "</FINAL_ANSWER>",
                    "</SUB_QUERY>",
                    "</ERROR>",
                    "</action>",
                    "<|im_end|>",
                    "<|endoftext|>",
                    "<|im_start|>",
                    "</s>",
                ],
                "stream": True,
            }
            if include_extra:
                rep_pen = getattr(
                    self, "repetition_penalty", getattr(self, "repeat_penalty", 1.0)
                )
                if rep_pen != 1.0:
                    p["repeat_penalty"] = rep_pen
                    p["repetition_penalty"] = rep_pen
                    p["repetition_context_size"] = 256
                    p["repeat_last_n"] = 256
                if use_grammar and self._grammar_content:
                    p["grammar"] = self._grammar_content
            return p

        def _iter_stream(target_url: str, include_extra: bool = True):
            req = urllib.request.Request(
                target_url,
                data=json.dumps(_make_payload(include_extra)).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            recent_lines: list[str] = []
            current_line_buf: list[str] = []
            accumulated_tokens: list[str] = []

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
                        token = delta.get("content")
                        if token:
                            # Stream repetition loop breaker (supports real \n and escaped \n in JSON)
                            if "\n" in token or "\\n" in token:
                                raw_segments = re.split(r"\r?\n|\\n", token)
                                for seg_idx, seg in enumerate(raw_segments):
                                    current_line_buf.append(seg)
                                    if seg_idx < len(raw_segments) - 1:
                                        full_line = "".join(current_line_buf).strip()
                                        current_line_buf = []
                                        if len(full_line) >= 6:
                                            recent_lines.append(full_line)
                                            if len(recent_lines) > 40:
                                                recent_lines.pop(0)
                                            # Period 1: 3 identical lines in a row
                                            if (
                                                len(recent_lines) >= 3
                                                and recent_lines[-1] == recent_lines[-2] == recent_lines[-3]
                                            ):
                                                return
                                            # Periods 2..8: repeating cycle of k lines repeated 2 full cycles
                                            for k in range(2, 9):
                                                if len(recent_lines) >= 2 * k:
                                                    if all(
                                                        recent_lines[-i] == recent_lines[-i - k]
                                                        for i in range(1, k + 1)
                                                    ):
                                                        return
                            else:
                                current_line_buf.append(token)

                            # Subphrase repetition detector on recent token window (consecutive loop breaker)
                            accumulated_tokens.append(token)
                            if len(accumulated_tokens) > 300:
                                accumulated_tokens.pop(0)
                            if len(accumulated_tokens) >= 120 and len(accumulated_tokens) % 8 == 0:
                                recent_text = "".join(accumulated_tokens[-120:])
                                if len(recent_text) >= 120:
                                    for wlen in (20, 28, 36):
                                        sample = recent_text[-wlen:]
                                        if len(recent_text) >= wlen * 3 and recent_text.endswith(sample * 3):
                                            return

                            yield token
                    except (KeyError, IndexError, json.JSONDecodeError):
                        continue
                return

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
                if "not a directory" in err_body.lower() and "config.json" in err_body.lower():
                    raise ConnectionError(
                        f"Inference Backend Mismatch on {self.base_url}: An MLX server (mlx_lm.server) is active on port 8080, "
                        f"but LlamaCppClient sent a GGUF request ({err_body}). "
                        f"Please switch the Engine backend to 'MLX' in the sidebar or restart llama-server."
                    ) from e
                if _is_model_loading_error(e, err_body):
                    print(
                        f"[LlamaCppClient] llama-server is currently loading model weights (HTTP 503). "
                        f"Waiting for server readiness..."
                    )
                    if _wait_for_server_ready(self.base_url, timeout=60.0):
                        continue
                    raise ConnectionError(
                        f"llama-server model loading timed out after 60s: {e} ({err_body}). "
                        f"Please ensure llama-server has finished loading the GGUF model into memory."
                    ) from e
                if e.code == 404 and "/v1" in request_url:
                    request_url = request_url.replace("/v1", "")
                    continue
                if "image input is not supported" in err_body.lower() or "mmproj" in err_body.lower():
                    self._server_supports_vision = False
                    self.is_vision = False
                    cleaned_messages = _strip_multimodal_images(cleaned_messages)
                    continue
                if e.code == 400 and (
                    "exceed" in err_body.lower() or "context" in err_body.lower()
                ):
                    raise ConnectionError(_context_limit_message(err_body)) from e
                if e.code == 400 and not standard_payload_tried:
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
