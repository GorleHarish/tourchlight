import os
import time
from typing import Generator, Optional
from rlm_optimized.config import CLOUD_MODEL, CLOUD_BASE_URL, CLOUD_API_KEY, TEMPERATURE, TOP_P, NUM_PREDICT

PROVIDER_PRESETS = {
    "groq": {"base_url": "https://api.groq.com/openai/v1", "default_model": "llama-3.3-70b-versatile", "env_key": "GROQ_API_KEY"},
    "together": {"base_url": "https://api.together.xyz/v1", "default_model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "env_key": "TOGETHER_API_KEY"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "default_model": "meta-llama/llama-3.3-70b-instruct", "env_key": "OPENROUTER_API_KEY"},
    "openai": {"base_url": "https://api.openai.com/v1", "default_model": "gpt-4o-mini", "env_key": "OPENAI_API_KEY"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "default_model": "gemini-2.5-flash", "env_key": "GEMINI_API_KEY"},
}

def _sanitize_messages_for_cloud(messages: list, model: str = "") -> list:
    """Sanitize message roles. Convert system role to user role for models (e.g. Gemma 2) that do not support system role."""
    if not messages:
        return []
    is_gemma_2 = "gemma-2" in model.lower() or "gemma2" in model.lower()
    sanitized = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if not content:
            continue
        if is_gemma_2 and role == "system":
            role = "user"
            content = f"[System Instructions]\n{content}"
        
        if sanitized and sanitized[-1]["role"] == role:
            sanitized[-1]["content"] += f"\n\n{content}"
        else:
            sanitized.append({"role": role, "content": content})
    return sanitized

class CloudClient:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Cloud mode requires the 'openai' package. Install it with: pip install openai")

        preset = PROVIDER_PRESETS.get(provider, {}) if provider else {}
        self._base_url = base_url or preset.get("base_url") or CLOUD_BASE_URL
        self._api_key = api_key or os.environ.get(preset.get("env_key", ""), "") or CLOUD_API_KEY or os.environ.get("LLM_API_KEY", "")
        self.model = model or preset.get("default_model") or CLOUD_MODEL
        self._provider = provider or "custom"

        if not self._api_key:
            if self._base_url and ("localhost" in self._base_url or "127.0.0.1" in self._base_url or self._provider == "custom"):
                self._api_key = "not-needed"
            else:
                raise ValueError(f"No API key found for provider '{self._provider}'. Set env variable or pass key.")
        if not self._base_url:
            raise ValueError("No base URL configured.")

        self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)

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

    def query(self, prompt: str, system_prompt: str = "", messages: Optional[list] = None, max_retries: int = 3) -> str:
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        cleaned_messages = _sanitize_messages_for_cloud(messages, self.model)

        for attempt in range(max_retries):
            try:
                kwargs = dict(
                    model=self.model,
                    messages=cleaned_messages,
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                    stop=["</TOOL>", "</CODE>", "</FINAL_ANSWER>", "</SUB_QUERY>", "</action>", "\nAction:", "Action:", "Observation:"],
                )
                if NUM_PREDICT > 0:
                    kwargs["max_tokens"] = NUM_PREDICT
                response = self._client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except Exception as e:
                error_str = str(e)
                if any(code in error_str for code in ["401", "403", "404", "invalid_api_key", "model_not_found"]):
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

        cleaned_messages = _sanitize_messages_for_cloud(messages, self.model)

        try:
            kwargs = dict(
                model=self.model,
                messages=cleaned_messages,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                stream=True,
                stop=["</TOOL>", "</CODE>", "</FINAL_ANSWER>", "</SUB_QUERY>", "</action>", "\nAction:", "Action:", "Observation:"],
            )
            if NUM_PREDICT > 0:
                kwargs["max_tokens"] = NUM_PREDICT
            stream = self._client.chat.completions.create(**kwargs)
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            error_str = str(e)
            if "404" in error_str or "NotFoundError" in type(e).__name__ or getattr(e, "status_code", None) == 404:
                try:
                    models_res = self._client.models.list()
                    model_list = list(models_res.data) if hasattr(models_res, 'data') else []
                    if model_list:
                        target_model = model_list[0].id
                        fallback_kwargs = dict(
                            model=target_model,
                            messages=messages,
                            temperature=TEMPERATURE,
                            top_p=TOP_P,
                            stream=True,
                            stop=["</TOOL>", "</CODE>", "</FINAL_ANSWER>", "</SUB_QUERY>", "</action>", "\nAction:", "Action:", "Observation:"],
                        )
                        if NUM_PREDICT > 0:
                            fallback_kwargs["max_tokens"] = NUM_PREDICT
                        stream = self._client.chat.completions.create(**fallback_kwargs)
                        for chunk in stream:
                            if chunk.choices and chunk.choices[0].delta.content:
                                yield chunk.choices[0].delta.content
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

        cleaned_messages = _sanitize_messages_for_cloud(messages, self.model)

        def _call():
            kwargs = dict(
                model=self.model,
                messages=cleaned_messages,
                temperature=temp,
                top_p=top_p,
                stop=stop or ["</TOOL>", "</CODE>", "</FINAL_ANSWER>", "</SUB_QUERY>", "</action>", "\nAction:", "Action:", "Observation:"],
            )
            if NUM_PREDICT > 0:
                kwargs["max_tokens"] = NUM_PREDICT
            response = self._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""

        return await loop.run_in_executor(None, _call)

    async def chat_stream(self, messages: list, params: Optional[object] = None):
        """Async streaming implementation required by LLMClient protocol."""
        for token in self.stream_chat_with_history(messages):
            yield token
