import time
import ollama
from typing import Generator, Optional
from rlm_optimized.config import MODEL_NAME, TEMPERATURE, TOP_P, NUM_PREDICT, CTX_SIZE, REPEAT_PENALTY

def _normalize_messages_for_ollama(messages: list) -> list:
    if not messages:
        return []
    import os
    from core.utils.image_utils import encode_image_to_base64

    normalized = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        raw_images = list(msg.get("images", []))
        images = []
        for img_item in raw_images:
            if isinstance(img_item, str):
                if os.path.exists(img_item):
                    try:
                        b64, _ = encode_image_to_base64(img_item)
                        images.append(b64)
                    except Exception:
                        pass
                else:
                    images.append(img_item)

        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        url = part.get("image_url", {}).get("url", "")
                        if ";base64," in url:
                            b64 = url.split(";base64,")[1]
                            images.append(b64)
                        elif url:
                            try:
                                b64, _ = encode_image_to_base64(url)
                                images.append(b64)
                            except Exception:
                                pass
            content_str = "\n".join(text_parts)
        else:
            content_str = str(content)

        m = {"role": role, "content": content_str}
        if images:
            m["images"] = images
        normalized.append(m)
    return normalized


class OllamaClient:
    def __init__(self, model: str = MODEL_NAME):
        self.model = model
        self.temperature = TEMPERATURE
        self.repeat_penalty = REPEAT_PENALTY
        self.repetition_penalty = REPEAT_PENALTY
        self._client = ollama.Client()

    def is_running(self) -> bool:
        try:
            self._client.list()
            return True
        except Exception:
            return False

    def is_model_available(self) -> bool:
        try:
            models = self._client.list()
            model_names = [m.model for m in models.models]
            return any(self.model in name for name in model_names)
        except Exception:
            return False

    def query(self, prompt: str, system_prompt: str = "", messages: Optional[list] = None, max_retries: int = 3) -> str:
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        cleaned_messages = _normalize_messages_for_ollama(messages)
        rep = getattr(self, "repeat_penalty", getattr(self, "repetition_penalty", REPEAT_PENALTY))

        for attempt in range(max_retries):
            try:
                opts = {
                    "temperature": self.temperature,
                    "top_p": TOP_P,
                    "repeat_penalty": rep,
                    "num_predict": NUM_PREDICT,
                    "num_ctx": CTX_SIZE,
                    "stop": ["</tool_call>", "</WRITE_FILE>", "</TOOL>", "</CODE>", "</FINAL_ANSWER>", "</SUB_QUERY>", "</action>"],
                }
                if hasattr(self, "presence_penalty"):
                    opts["presence_penalty"] = self.presence_penalty
                if hasattr(self, "frequency_penalty"):
                    opts["frequency_penalty"] = self.frequency_penalty
                response = self._client.chat(
                    model=self.model,
                    messages=cleaned_messages,
                    options=opts,
                )
                return response["message"]["content"]
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise ConnectionError(f"Ollama connection error: {e}") from e
        return ""

    def stream_query(self, prompt: str, system_prompt: str = "", messages: Optional[list] = None) -> Generator[str, None, None]:
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        cleaned_messages = _normalize_messages_for_ollama(messages)
        rep = getattr(self, "repeat_penalty", getattr(self, "repetition_penalty", REPEAT_PENALTY))

        try:
            opts = {
                "temperature": self.temperature,
                "top_p": TOP_P,
                "repeat_penalty": rep,
                "num_predict": NUM_PREDICT,
                "num_ctx": CTX_SIZE,
                "stop": ["</tool_call>", "</WRITE_FILE>", "</TOOL>", "</CODE>", "</FINAL_ANSWER>", "</SUB_QUERY>", "</action>"],
            }
            if hasattr(self, "presence_penalty"):
                opts["presence_penalty"] = self.presence_penalty
            if hasattr(self, "frequency_penalty"):
                opts["frequency_penalty"] = self.frequency_penalty
            stream = self._client.chat(
                model=self.model,
                messages=cleaned_messages,
                stream=True,
                options=opts,
            )
            for chunk in stream:
                token = chunk["message"]["content"]
                if token:
                    yield token
        except Exception as e:
            raise ConnectionError(f"Streaming failed: {e}") from e

    def chat_with_history(self, messages: list[dict]) -> str:
        return self.query(prompt="", messages=messages)

    def stream_chat_with_history(self, messages: list[dict]) -> Generator[str, None, None]:
        return self.stream_query(prompt="", messages=messages)

    async def chat(self, messages: list, params: Optional[object] = None) -> str:
        """Async implementation of chat protocol method required by LLMClient / DebateVerifier."""
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.query, "", "", messages)

    async def chat_stream(self, messages: list, params: Optional[object] = None):
        """Async streaming implementation required by LLMClient protocol."""
        for token in self.stream_chat_with_history(messages):
            yield token

