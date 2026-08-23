import os
import re
import time
from typing import Generator, Optional
from rlm_optimized.config import (
    CLOUD_MODEL,
    CLOUD_BASE_URL,
    CLOUD_API_KEY,
    TEMPERATURE,
    TOP_P,
    NUM_PREDICT,
    REPEAT_PENALTY,
    PRESENCE_PENALTY,
    FREQUENCY_PENALTY,
)
from core.api.base import InferenceParams

PROVIDER_PRESETS = {
    "groq": {"base_url": "https://api.groq.com/openai/v1", "default_model": "llama-3.3-70b-versatile", "env_key": "GROQ_API_KEY"},
    "together": {"base_url": "https://api.together.xyz/v1", "default_model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "env_key": "TOGETHER_API_KEY"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "default_model": "meta-llama/llama-3.3-70b-instruct", "env_key": "OPENROUTER_API_KEY"},
    "openai": {"base_url": "https://api.openai.com/v1", "default_model": "gpt-4o-mini", "env_key": "OPENAI_API_KEY"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "default_model": "gemini-2.5-flash", "env_key": "GEMINI_API_KEY"},
}

def _sanitize_messages_for_cloud(messages: list, model: str = "") -> list:
    """Sanitize message roles. Convert system role to user role for models (e.g. Gemma) that do not support system role."""
    if not messages:
        return []
    is_gemma = "gemma" in model.lower()
    sanitized = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if not content:
            continue
        if is_gemma and role == "system":
            role = "user"
            if isinstance(content, str):
                content = f"[System Instructions]\n{content}"
            elif isinstance(content, list):
                content = [{"type": "text", "text": "[System Instructions]"}] + list(content)
        
        if sanitized and sanitized[-1]["role"] == role:
            prev_content = sanitized[-1]["content"]
            if isinstance(prev_content, str) and isinstance(content, str):
                sanitized[-1]["content"] = f"{prev_content}\n\n{content}"
            else:
                p_parts = [{"type": "text", "text": prev_content}] if isinstance(prev_content, str) else list(prev_content)
                c_parts = [{"type": "text", "text": content}] if isinstance(content, str) else list(content)
                sanitized[-1]["content"] = p_parts + c_parts
        else:
            sanitized.append({"role": role, "content": content})
    return sanitized

class _HttpxOpenAIModels:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def list(self):
        import httpx
        from types import SimpleNamespace
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key and self.api_key != "not-needed" else {}
        try:
            with httpx.Client(timeout=5) as client:
                r = client.get(f"{self.base_url}/models", headers=headers)
                r.raise_for_status()
                data = r.json().get("data", [])
                return SimpleNamespace(data=[SimpleNamespace(id=m["id"]) for m in data if "id" in m])
        except Exception:
            return SimpleNamespace(data=[])


class _HttpxOpenAIChatCompletions:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def create(self, **kwargs):
        import httpx
        import json
        from types import SimpleNamespace

        stream = kwargs.get("stream", False)
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.api_key != "not-needed":
            headers["Authorization"] = f"Bearer {self.api_key}"

        if not stream:
            with httpx.Client(timeout=300) as client:
                r = client.post(f"{self.base_url}/chat/completions", json=kwargs, headers=headers)
                r.raise_for_status()
                body = r.json()
                content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
        else:
            def _stream_gen():
                with httpx.Client(timeout=300) as client:
                    with client.stream("POST", f"{self.base_url}/chat/completions", json=kwargs, headers=headers) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            if line.startswith("data: ") and line.strip() != "data: [DONE]":
                                try:
                                    chunk = json.loads(line[6:])
                                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                                    content = delta.get("content", "")
                                    reasoning = delta.get("reasoning", "")
                                    if content or reasoning:
                                        yield SimpleNamespace(
                                            choices=[
                                                SimpleNamespace(
                                                    delta=SimpleNamespace(
                                                        content=content,
                                                        reasoning=reasoning,
                                                    )
                                                )
                                            ]
                                        )
                                except Exception:
                                    continue
            return _stream_gen()


class _HttpxOpenAIClient:
    def __init__(self, base_url: str = "http://localhost:8080/v1", api_key: str = "not-needed"):
        from types import SimpleNamespace
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.models = _HttpxOpenAIModels(self.base_url, self.api_key)
        self.chat = SimpleNamespace(completions=_HttpxOpenAIChatCompletions(self.base_url, self.api_key))


class CloudClient:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None):
        preset = PROVIDER_PRESETS.get(provider, {}) if provider else {}
        self._base_url = base_url or preset.get("base_url") or CLOUD_BASE_URL
        self._api_key = api_key or os.environ.get(preset.get("env_key", ""), "") or CLOUD_API_KEY or os.environ.get("LLM_API_KEY", "")
        self.model = model or preset.get("default_model") or CLOUD_MODEL
        self._provider = provider or "custom"

        if not self._api_key:
            if self._base_url and ("localhost" in self._base_url or "127.0.0.1" in self._base_url or self._provider == "custom" or self._provider == "mlx"):
                self._api_key = "not-needed"
            else:
                raise ValueError(f"No API key found for provider '{self._provider}'. Set env variable or pass key.")
        if not self._base_url:
            raise ValueError("No base URL configured.")

        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        except Exception:
            self._client = _HttpxOpenAIClient(api_key=self._api_key, base_url=self._base_url)

        calibrated = InferenceParams.for_model_and_phase(self.model, "code")
        self.temperature = calibrated.temperature
        self.repeat_penalty = calibrated.repeat_penalty
        self.repetition_penalty = calibrated.repetition_penalty or calibrated.repeat_penalty
        self.presence_penalty = calibrated.presence_penalty
        self.frequency_penalty = calibrated.frequency_penalty
        self.top_p = calibrated.top_p
        self.top_k = calibrated.top_k
        self.min_p = calibrated.min_p

    def is_running(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return True

    def is_model_available(self) -> bool:
        return True

    def list_models(self) -> list[str]:
        """Return the ids of models the provider currently reports as available.
        Used by the TUI's model picker to show live LM Studio / Ollama models."""
        try:
            res = self._client.models.list()
            return sorted([m.id for m in res.data])
        except Exception:
            return []

    def _resolve_model_target(self) -> str:
        """Resolve requested self.model against live models to prevent 404 mismatches."""
        if not self.model:
            live = self.list_models()
            if live:
                self.model = live[0]
            return self.model or ""
        live = self.list_models()
        if not live:
            return self.model
        if self.model in live:
            return self.model
        # Check fuzzy match
        requested_lower = self.model.lower()
        for m_id in live:
            if requested_lower in m_id.lower() or m_id.lower() in requested_lower:
                print(f"[CloudClient] Fuzzy matched model '{self.model}' -> '{m_id}'")
                self.model = m_id
                return m_id
        return self.model

    def query(self, prompt: str, system_prompt: str = "", messages: Optional[list] = None, max_retries: int = 3) -> str:
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        self._resolve_model_target()
        cleaned_messages = _sanitize_messages_for_cloud(messages, self.model)

        for attempt in range(max_retries):
            try:
                kwargs = dict(
                    model=self.model,
                    messages=cleaned_messages,
                    temperature=self.temperature,
                    top_p=getattr(self, "top_p", TOP_P),
                    presence_penalty=getattr(self, "presence_penalty", PRESENCE_PENALTY),
                    frequency_penalty=getattr(self, "frequency_penalty", FREQUENCY_PENALTY),
                    stop=["</tool_call>", "</WRITE_FILE>", "</TOOL>", "</CODE>", "</FINAL_ANSWER>", "</SUB_QUERY>", "</action>"],
                )
                rep = getattr(self, "repetition_penalty", getattr(self, "repeat_penalty", REPEAT_PENALTY))
                if rep and rep != 1.0:
                    kwargs["extra_body"] = {"repetition_penalty": rep}
                if NUM_PREDICT > 0:
                    kwargs["max_tokens"] = NUM_PREDICT
                response = self._client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except Exception as e:
                error_str = str(e)
                if "404" in error_str or "NotFoundError" in type(e).__name__ or getattr(e, "status_code", None) == 404:
                    live = self.list_models()
                    if live and self.model != live[0]:
                        print(f"[CloudClient] Model '{self.model}' 404, falling back to '{live[0]}'")
                        self.model = live[0]
                        cleaned_messages = _sanitize_messages_for_cloud(messages, self.model)
                        continue
                if any(code in error_str for code in ["401", "403", "invalid_api_key"]):
                    raise RuntimeError(f"Cloud API error: {e}") from e
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise ConnectionError(f"Failed after {max_retries} attempts: {e}") from e
        return ""

    def stream_query(self, prompt: str, system_prompt: str = "", messages: Optional[list] = None) -> Generator[str, None, None]:
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        self._resolve_model_target()
        cleaned_messages = _sanitize_messages_for_cloud(messages, self.model)

        try:
            kwargs = dict(
                model=self.model,
                messages=cleaned_messages,
                temperature=self.temperature,
                top_p=getattr(self, "top_p", TOP_P),
                presence_penalty=getattr(self, "presence_penalty", PRESENCE_PENALTY),
                frequency_penalty=getattr(self, "frequency_penalty", FREQUENCY_PENALTY),
                stream=True,
                stop=["</tool_call>", "</WRITE_FILE>", "</TOOL>", "</CODE>", "</FINAL_ANSWER>", "</SUB_QUERY>", "</action>"],
            )
            rep = getattr(self, "repetition_penalty", getattr(self, "repeat_penalty", REPEAT_PENALTY))
            if rep and rep != 1.0:
                kwargs["extra_body"] = {"repetition_penalty": rep}
            if NUM_PREDICT > 0:
                kwargs["max_tokens"] = NUM_PREDICT
            stream = self._client.chat.completions.create(**kwargs)

            recent_lines: list[str] = []
            current_line_buf: list[str] = []
            accumulated_tokens: list[str] = []

            for chunk in stream:
                if chunk.choices and hasattr(chunk.choices[0], "delta"):
                    d = chunk.choices[0].delta
                    token = getattr(d, "content", "") or getattr(d, "reasoning", "")
                    if token:
                        # Stream repetition loop breaker (supports real \n, escaped \\n, and token sub-cycles)
                        raw_segments = re.split(r"\r?\n|\\n", token)
                        if len(raw_segments) > 1:
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
                        recent_text = "".join(accumulated_tokens[-120:])
                        if len(recent_text) >= 120:
                            for wlen in (20, 28, 36):
                                sample = recent_text[-wlen:]
                                if len(recent_text) >= wlen * 3 and recent_text.endswith(sample * 3):
                                    return

                        yield token
        except Exception as e:
            error_str = str(e)
            if "404" in error_str or "NotFoundError" in type(e).__name__ or getattr(e, "status_code", None) == 404:
                try:
                    model_list = self.list_models()
                    if model_list:
                        target_model = model_list[0]
                        print(f"[CloudClient] Stream model '{self.model}' 404, updating self.model -> '{target_model}'")
                        self.model = target_model
                        fallback_kwargs = dict(
                            model=target_model,
                            messages=messages,
                            temperature=self.temperature,
                            top_p=getattr(self, "top_p", TOP_P),
                            presence_penalty=getattr(self, "presence_penalty", PRESENCE_PENALTY),
                            frequency_penalty=getattr(self, "frequency_penalty", FREQUENCY_PENALTY),
                            stream=True,
                            stop=["</tool_call>", "</WRITE_FILE>", "</TOOL>", "</CODE>", "</FINAL_ANSWER>", "</SUB_QUERY>", "</action>"],
                        )
                        rep = getattr(self, "repetition_penalty", getattr(self, "repeat_penalty", REPEAT_PENALTY))
                        if rep and rep != 1.0:
                            fallback_kwargs["extra_body"] = {"repetition_penalty": rep}
                        if NUM_PREDICT > 0:
                            fallback_kwargs["max_tokens"] = NUM_PREDICT
                        stream = self._client.chat.completions.create(**fallback_kwargs)
                        for chunk in stream:
                            if chunk.choices and hasattr(chunk.choices[0], "delta"):
                                d = chunk.choices[0].delta
                                token = getattr(d, "content", "") or getattr(d, "reasoning", "")
                                if token:
                                    yield token
                        return
                except Exception as inner_e:
                    print(f"Fallback failed: {inner_e}")
            raise ConnectionError(f"Streaming failed: {e}") from e

    def chat_with_history(self, messages: list) -> str:
        return self.query(prompt="", messages=messages)

    def stream_chat_with_history(self, messages: list) -> Generator[str, None, None]:
        return self.stream_query(prompt="", messages=messages)

    async def chat(self, messages: list, params: Optional[object] = None) -> str:
        """Async implementation of chat protocol method required by LLMClient and DebateVerifier."""
        import asyncio
        loop = asyncio.get_running_loop()

        stop = getattr(params, "stop", None) if params else None
        temp = getattr(params, "temperature", TEMPERATURE) if params else TEMPERATURE
        top_p = getattr(params, "top_p", TOP_P) if params else TOP_P
        presence_pen = getattr(params, "presence_penalty", 0.0) if params else 0.0
        frequency_pen = getattr(params, "frequency_penalty", 0.0) if params else 0.0
        rep_pen = getattr(params, "repeat_penalty", getattr(params, "repetition_penalty", None)) if params else None

        cleaned_messages = _sanitize_messages_for_cloud(messages, self.model)

        def _call():
            kwargs = dict(
                model=self.model,
                messages=cleaned_messages,
                temperature=temp,
                top_p=top_p,
                stop=stop or ["</TOOL>", "</CODE>", "</FINAL_ANSWER>", "</SUB_QUERY>", "</action>", "\nAction:", "Action:", "Observation:"],
            )
            if presence_pen != 0.0:
                kwargs["presence_penalty"] = presence_pen
            if frequency_pen != 0.0:
                kwargs["frequency_penalty"] = frequency_pen
            if rep_pen is not None and rep_pen != 1.0:
                kwargs["extra_body"] = {"repetition_penalty": rep_pen}
            if NUM_PREDICT > 0:
                kwargs["max_tokens"] = NUM_PREDICT
            response = self._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""

        return await loop.run_in_executor(None, _call)

    async def chat_stream(self, messages: list, params: Optional[object] = None):
        """Async streaming implementation required by LLMClient protocol."""
        for token in self.stream_chat_with_history(messages):
            yield token
