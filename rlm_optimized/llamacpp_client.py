import os
import json
import time
import urllib.request
import urllib.error
from typing import Generator, Optional, Union
from rlm_optimized.config import LOCAL_API_BASE_URL, MODEL_NAME, TEMPERATURE, TOP_P, NUM_PREDICT, CTX_SIZE, GRAMMAR_FILE, USE_GRAMMAR_CONSTRAINT

def _sanitize_messages(messages: list) -> list:
    """Ensure strict role alternation (user, assistant...) and merge consecutive same-role messages."""
    if not messages:
        return []
    sanitized = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if not content:
            continue
        if sanitized and sanitized[-1]["role"] == role and role != "system":
            sanitized[-1]["content"] += f"\n\n{content}"
        else:
            sanitized.append({"role": role, "content": content})
    return sanitized

class LlamaCppClient:
    def __init__(self, base_url: str = LOCAL_API_BASE_URL, model: str = MODEL_NAME):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = TEMPERATURE
        self._grammar_content = self._load_grammar()
        print(f"[LlamaCppClient] connecting to {self.base_url} (model={self.model})")

    def _load_grammar(self) -> Optional[str]:
        if not USE_GRAMMAR_CONSTRAINT:
            return None
        if GRAMMAR_FILE and os.path.exists(GRAMMAR_FILE):
            try:
                with open(GRAMMAR_FILE, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"[LlamaCppClient] WARNING: Failed to read grammar file {GRAMMAR_FILE}: {e}")
        else:
            print(f"[LlamaCppClient] WARNING: grammar file not found at {GRAMMAR_FILE} — "
                  f"model output will be unconstrained and may use unrecognized tags.")
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

    def query(self, prompt: str, system_prompt: str = "", messages: Optional[list] = None, max_retries: int = 3, use_grammar: bool = True) -> str:
        url = f"{self.base_url}/chat/completions"
        
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
                "max_tokens": NUM_PREDICT,
                "presence_penalty": 0.1,
                "frequency_penalty": 0.0,
                "stop": [
                    "</TOOL>",
                    "</CODE>",
                    "</FINAL_ANSWER>",
                    "</SUB_QUERY>",
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
                p["repeat_penalty"] = 1.1
                if use_grammar and self._grammar_content:
                    p["grammar"] = self._grammar_content
            return p

        headers = {"Content-Type": "application/json"}

        for attempt in range(max_retries):
            # First try full payload, on attempt > 0 or HTTP 400 try standard payload
            fallback = attempt > 0
            payload = _make_payload(include_extra=not fallback)
            data = json.dumps(payload).encode("utf-8")
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=60) as response:
                    res_body = json.loads(response.read().decode("utf-8"))
                    return res_body["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                err_body = ""
                try:
                    err_body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                if e.code == 404 and "/v1" in url:
                    url = url.replace("/v1", "")
                    continue
                if e.code == 400:
                    if "exceed" in err_body.lower() or "context" in err_body.lower():
                        msg = (
                            f"llama-server context limit exceeded: {err_body}\n"
                            f"To resolve this issue:\n"
                            f" 1. Restart llama-server with a larger context window: `./rlm_optimized/start_optimized_local.sh` (defaults to 12288) or run `llama-server -c 12288`\n"
                            f" 2. Or set `export RLM_CTX_SIZE=8192` to match your server's current context limit so Torchlight compresses context earlier."
                        )
                        raise ConnectionError(msg) from e
                    if not fallback:
                        # Retry immediately with standard payload (stripping grammar & repeat_penalty)
                        try:
                            std_data = json.dumps(_make_payload(include_extra=False)).encode("utf-8")
                            req_std = urllib.request.Request(url, data=std_data, headers=headers, method="POST")
                            with urllib.request.urlopen(req_std, timeout=60) as response:
                                res_body = json.loads(response.read().decode("utf-8"))
                                return res_body["choices"][0]["message"]["content"]
                        except Exception as fallback_err:
                            err_body += f" | Fallback error: {fallback_err}"
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    msg = f"llama-server connection error: {e} ({err_body})" if err_body else f"llama-server connection error: {e}"
                    raise ConnectionError(msg) from e
            except urllib.error.URLError as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    raise ConnectionError(
                        f"Local engine server connection error on {self.base_url}: {e}. "
                        f"Ensure llama-server or MLX server is running."
                    ) from e
        return ""

    def chat_with_history(self, messages: list, use_grammar: bool = True) -> str:
        return self.query(prompt="", messages=messages, use_grammar=use_grammar)

    def stream_chat_with_history(self, messages: list, use_grammar: bool = True) -> Generator[str, None, None]:
        url = f"{self.base_url}/chat/completions"
        cleaned_messages = _sanitize_messages(messages)
        payload = {
            "model": self.model,
            "messages": cleaned_messages,
            "temperature": self.temperature,
            "top_p": TOP_P,
            "max_tokens": NUM_PREDICT,
            "repeat_penalty": 1.1,
            "presence_penalty": 0.1,
            "frequency_penalty": 0.0,
            "stop": [
                "</TOOL>",
                "</CODE>",
                "</FINAL_ANSWER>",
                "</SUB_QUERY>",
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

        if use_grammar and self._grammar_content:
            payload["grammar"] = self._grammar_content

        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as response:
                for line in response:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        data_content = line_str[6:]
                        if data_content == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_content)
                            delta = chunk["choices"][0]["delta"]
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                        except Exception:
                            pass
        except urllib.error.HTTPError as e:
            if e.code == 404 and "/v1" in url:
                url_fallback = url.replace("/v1", "")
                try:
                    req = urllib.request.Request(url_fallback, data=data, headers=headers, method="POST")
                    with urllib.request.urlopen(req, timeout=60) as response:
                        for line in response:
                            line_str = line.decode("utf-8").strip()
                            if line_str.startswith("data: "):
                                data_content = line_str[6:]
                                if data_content == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_content)
                                    delta = chunk["choices"][0]["delta"]
                                    if "content" in delta and delta["content"]:
                                        yield delta["content"]
                                except Exception:
                                    pass
                        return
                except Exception:
                    pass
            content = self.query(prompt="", messages=messages, use_grammar=use_grammar)
            yield content
        except Exception as e:
            content = self.query(prompt="", messages=messages, use_grammar=use_grammar)
            yield content

    async def chat(self, messages: list, params: Optional[object] = None, use_grammar: bool = True) -> str:
        """Async implementation of chat protocol method required by LLMClient / DebateVerifier."""
        import asyncio
        if params is not None and getattr(params, "use_grammar", None) is not None:
            use_grammar = params.use_grammar
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.query, "", "", messages, 3, use_grammar)

    async def chat_stream(self, messages: list, params: Optional[object] = None, use_grammar: bool = True):
        """Async streaming implementation required by LLMClient protocol."""
        if params is not None and getattr(params, "use_grammar", None) is not None:
            use_grammar = params.use_grammar
        for token in self.stream_chat_with_history(messages, use_grammar=use_grammar):
            yield token