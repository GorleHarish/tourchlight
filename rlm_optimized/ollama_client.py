import time
import ollama
from typing import Generator, Optional
from rlm_optimized.config import MODEL_NAME, TEMPERATURE, TOP_P, NUM_PREDICT, CTX_SIZE

class OllamaClient:
    def __init__(self, model: str = MODEL_NAME):
        self.model = model
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

        for attempt in range(max_retries):
            try:
                response = self._client.chat(
                    model=self.model,
                    messages=messages,
                    options={
                        "temperature": TEMPERATURE,
                        "top_p": TOP_P,
                        "num_predict": NUM_PREDICT,
                        "num_ctx": CTX_SIZE,
                        "stop": ["</TOOL>", "</CODE>", "</FINAL_ANSWER>", "</SUB_QUERY>", "</action>", "\nAction:", "Action:", "Observation:"],
                    },
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

        try:
            stream = self._client.chat(
                model=self.model,
                messages=messages,
                stream=True,
                options={
                    "temperature": TEMPERATURE,
                    "top_p": TOP_P,
                    "num_predict": NUM_PREDICT,
                    "num_ctx": CTX_SIZE,
                    "stop": ["</TOOL>", "</CODE>", "</FINAL_ANSWER>", "</SUB_QUERY>", "</action>", "\nAction:", "Action:", "Observation:"],
                },
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

