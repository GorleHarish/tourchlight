import logging
from typing import Optional, AsyncIterator
from dataclasses import dataclass, field
import httpx
import json

log = logging.getLogger(__name__)


# ── Timeout configuration ─────────────────────────────────────────────────────
#
# httpx.Timeout has four independent components:
#
#   connect  — time to establish the TCP connection to LM Studio
#   read     — for streaming: max idle time between chunks (NOT total response time)
#              for non-streaming: total time to receive the full response body
#   write    — time to send the request payload
#   pool     — time to acquire a connection from the pool
#
# Qwen2.5-Coder-3B on a MacBook at ~8-12 tok/s generating 2048 tokens takes
# ~170–256 seconds. The old flat 120s timeout cut responses off mid-generation.
#
# For streaming: read=600 means "if no chunk arrives for 10 minutes, abort."
# This is very generous but correct — a slow Mac under memory pressure can pause
# generation for seconds between chunks.

_CONNECT_TIMEOUT = 10.0    # fail fast if LM Studio isn't running
_READ_TIMEOUT    = 600.0   # 10 min max idle between streaming chunks
_WRITE_TIMEOUT   = 60.0    # time to upload the request payload
_POOL_TIMEOUT    = 10.0    # time to get a connection from the pool

DEFAULT_TIMEOUT = httpx.Timeout(
    connect = _CONNECT_TIMEOUT,
    read    = _READ_TIMEOUT,
    write   = _WRITE_TIMEOUT,
    pool    = _POOL_TIMEOUT,
)

# Non-streaming calls need a total-response timeout, not a per-chunk timeout.
# httpx uses read= as the total body receive time for non-streaming requests.
NON_STREAM_TIMEOUT = httpx.Timeout(
    connect = _CONNECT_TIMEOUT,
    read    = 300.0,   # 5 min total for non-streaming response
    write   = _WRITE_TIMEOUT,
    pool    = _POOL_TIMEOUT,
)


# ── Inference parameters ──────────────────────────────────────────────────────
#
# A coding agent has three distinct phases, each needing different sampling:
#
#   PLAN          — emitting <plan> blocks, reasoning through steps
#                   needs moderate creativity, structured output
#   CODE          — writing actual code via WRITE_FILE
#                   needs near-determinism, exact syntax matters
#   TROUBLESHOOT  — diagnosing errors, exploring failure causes
#                   needs slightly more exploration than coding
#   CHAT          — general conversation, clarification
#                   default conversational settings
#
# Parameter reference (LM Studio / llama.cpp):
#   temperature   — randomness of token selection (0=greedy, 1=very random)
#   top_k         — keep only the K most likely next tokens (0=disabled)
#   top_p         — nucleus sampling: keep tokens covering top P of probability
#   min_p         — discard tokens below min_p × (prob of top token)
#   repeat_penalty— penalise recently generated tokens (1.0=disabled)
#   seed          — -1 means random; set a fixed int for reproducible output

@dataclass
class InferenceParams:
    """
    Sampling parameters forwarded to the LM Studio /chat/completions endpoint.
    Only non-None fields are included in the API payload so that LM Studio
    falls back to its own defaults for anything not specified.
    """
    temperature:    float         = 0.7
    top_k:          int           = 50
    top_p:          float         = 0.95
    min_p:          float         = 0.05
    repeat_penalty: float         = 1.05
    seed:           int           = -1        # -1 = random
    stop:           list[str]     = field(default_factory=list)

    # ── Named presets ─────────────────────────────────────────────────────────

    @classmethod
    def for_coding(cls) -> "InferenceParams":
        """Writing code files.  Near-deterministic — exact syntax matters."""
        return cls(
            temperature    = 0.1,
            top_k          = 20,
            top_p          = 0.90,
            min_p          = 0.05,
            repeat_penalty = 1.10,
            seed           = -1,
        )

    @classmethod
    def for_planning(cls) -> "InferenceParams":
        """Emitting <plan> blocks and <thought> reasoning.
        Some creativity for step generation, still structured."""
        return cls(
            temperature    = 0.4,
            top_k          = 40,
            top_p          = 0.92,
            min_p          = 0.05,
            repeat_penalty = 1.05,
            seed           = -1,
        )

    @classmethod
    def for_troubleshoot(cls) -> "InferenceParams":
        """Analysing errors and diagnosing failures.
        Moderate exploration to surface non-obvious causes."""
        return cls(
            temperature    = 0.3,
            top_k          = 35,
            top_p          = 0.92,
            min_p          = 0.05,
            repeat_penalty = 1.10,
            seed           = -1,
        )

    @classmethod
    def for_chat(cls) -> "InferenceParams":
        """General conversation and clarification — default settings."""
        return cls(
            temperature    = 0.7,
            top_k          = 50,
            top_p          = 0.95,
            min_p          = 0.05,
            repeat_penalty = 1.05,
            seed           = -1,
        )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_payload(self) -> dict:
        """Return only the fields that LM Studio accepts, dropping None/defaults."""
        d: dict = {
            "temperature":    self.temperature,
            "top_k":          self.top_k,
            "top_p":          self.top_p,
            "min_p":          self.min_p,
            "repeat_penalty": self.repeat_penalty,
        }
        if self.seed != -1:
            d["seed"] = self.seed
        if self.stop:
            d["stop"] = self.stop
        return d

    def describe(self) -> str:
        """One-line human-readable summary for the dashboard."""
        seed_str = str(self.seed) if self.seed != -1 else "rnd"
        return (
            f"temp={self.temperature}  top_k={self.top_k}  top_p={self.top_p}  "
            f"min_p={self.min_p}  rep={self.repeat_penalty}  seed={seed_str}"
        )


# Convenience: the four named presets as a lookup dict
PRESETS: dict[str, InferenceParams] = {
    "code":         InferenceParams.for_coding(),
    "plan":         InferenceParams.for_planning(),
    "troubleshoot": InferenceParams.for_troubleshoot(),
    "chat":         InferenceParams.for_chat(),
}


def _friendly_timeout_msg(e: httpx.TimeoutException, url: str) -> str:
    """Return a human-readable message explaining which part of the request timed out."""
    if isinstance(e, httpx.ConnectTimeout):
        return (
            f"⏰ Connect timeout — LM Studio not responding at {url}\n"
            f"   Check that LM Studio is running and the Local Server is started."
        )
    if isinstance(e, httpx.ReadTimeout):
        return (
            f"⏰ Read timeout — model took too long to generate a response.\n"
            f"   Try: shorter max_tokens, lower temperature, or /compress to reduce context."
        )
    if isinstance(e, httpx.WriteTimeout):
        return (
            f"⏰ Write timeout — request payload took too long to send.\n"
            f"   Context may be too large. Try /compress."
        )
    return f"⏰ Request timed out: {e}"


class LMStudioClient:
    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: Optional[str] = None,
        timeout: Optional[httpx.Timeout] = None,
    ):
        self.base_url       = base_url.rstrip("/")
        self.model          = model
        self.timeout        = timeout or DEFAULT_TIMEOUT
        self._client:       Optional[httpx.AsyncClient] = None
        self._sync_client:  Optional[httpx.Client]      = None

    def _provider_label(self) -> str:
        return "Ollama" if "11434" in self.base_url or "ollama" in self.base_url.lower() else "LM Studio"

    def _root_base_url(self) -> str:
        if self.base_url.endswith("/v1"):
            return self.base_url[:-3]
        return self.base_url

    async def _list_models_ollama_async(self) -> list[str]:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=NON_STREAM_TIMEOUT)
        response = await self._client.get(f"{self._root_base_url()}/api/tags")
        response.raise_for_status()
        return [m.get("name", "") for m in response.json().get("models", []) if m.get("name")]

    def _list_models_ollama_sync(self) -> list[str]:
        if not self._sync_client:
            self._sync_client = httpx.Client(timeout=NON_STREAM_TIMEOUT)
        response = self._sync_client.get(f"{self._root_base_url()}/api/tags")
        response.raise_for_status()
        return [m.get("name", "") for m in response.json().get("models", []) if m.get("name")]

    # ── System message merging ─────────────────────────────────────────────────

    def _merge_system_messages(self, messages: list[dict]) -> list[dict]:
        system_content   = []
        filtered_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_content.append(msg.get("content", ""))
            else:
                filtered_messages.append(msg)
        final_messages = []
        if system_content:
            final_messages.append({
                "role":    "system",
                "content": "\n\n".join(system_content),
            })
        final_messages.extend(filtered_messages)
        return final_messages

    # ── Async context manager ──────────────────────────────────────────────────

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    # ── Async chat (non-streaming) ─────────────────────────────────────────────

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        params: Optional["InferenceParams"] = None,
    ) -> str:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=NON_STREAM_TIMEOUT)

        messages = self._merge_system_messages(messages)
        payload  = {
            "model":      self.model or "default",
            "messages":   messages,
            "max_tokens": max_tokens,
            "stream":     stream,
        }
        # InferenceParams takes priority over legacy temperature kwarg
        if params is not None:
            payload.update(params.to_payload())
        else:
            payload["temperature"] = temperature

        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        except httpx.TimeoutException as e:
            raise RuntimeError(_friendly_timeout_msg(e, self.base_url)) from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"{self._provider_label()} API error {e.response.status_code}: {e.response.text[:300]}"
            ) from e

    # ── Sync chat (non-streaming) ──────────────────────────────────────────────

    def chat_sync(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        params: Optional["InferenceParams"] = None,
    ) -> str:
        if not self._sync_client:
            self._sync_client = httpx.Client(timeout=NON_STREAM_TIMEOUT)

        messages = self._merge_system_messages(messages)
        payload: dict = {
            "messages":   messages,
            "max_tokens": max_tokens,
            "stream":     False,
        }
        if self.model:
            payload["model"] = self.model
        if params is not None:
            payload.update(params.to_payload())
        else:
            payload["temperature"] = temperature

        try:
            response = self._sync_client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )
        except httpx.TimeoutException as e:
            raise RuntimeError(_friendly_timeout_msg(e, self.base_url)) from e

        if response.status_code != 200:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text[:500]
            raise RuntimeError(
                f"{self._provider_label()} API error {response.status_code}: {error_body}"
            )

        return response.json()["choices"][0]["message"]["content"]

    # ── Sync streaming ─────────────────────────────────────────────────────────

    def chat_stream_sync(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        params: Optional["InferenceParams"] = None,
    ):
        """Synchronous streaming generator — yields tokens one-by-one.

        Uses DEFAULT_TIMEOUT (read=600s per chunk) so slow local models
        don't trip the timeout between tokens.
        """
        if not self._sync_client:
            self._sync_client = httpx.Client(timeout=self.timeout)

        messages = self._merge_system_messages(messages)
        payload: dict = {
            "messages":   messages,
            "max_tokens": max_tokens,
            "stream":     True,
        }
        if self.model:
            payload["model"] = self.model
        if params is not None:
            payload.update(params.to_payload())
        else:
            payload["temperature"] = temperature

        try:
            with self._sync_client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
            ) as response:
                if response.status_code != 200:
                    response.read()
                    try:
                        error_body = response.json()
                    except Exception:
                        error_body = response.text[:500]
                    raise RuntimeError(
                        f"{self._provider_label()} API error {response.status_code}: {error_body}"
                    )
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        if line.strip() == "data: [DONE]":
                            break
                        try:
                            data  = json.loads(line[6:])
                            delta = (
                                data.get("choices", [{}])[0]
                                    .get("delta", {})
                                    .get("content")
                            )
                            if delta:
                                yield delta
                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException as e:
            raise RuntimeError(_friendly_timeout_msg(e, self.base_url)) from e

    # ── Async streaming ────────────────────────────────────────────────────────

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        params: Optional["InferenceParams"] = None,
    ) -> AsyncIterator[str]:
        """Async streaming generator. Uses per-chunk read timeout (DEFAULT_TIMEOUT)."""
        if not self._client:
            self._client = httpx.AsyncClient(timeout=self.timeout)

        messages = self._merge_system_messages(messages)
        payload: dict = {
            "model":      self.model or "default",
            "messages":   messages,
            "max_tokens": max_tokens,
            "stream":     True,
        }
        if params is not None:
            payload.update(params.to_payload())
        else:
            payload["temperature"] = temperature

        try:
            async with self._client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        if line.strip() == "data: [DONE]":
                            break
                        try:
                            data = json.loads(line[6:])
                            if delta := (
                                data.get("choices", [{}])[0]
                                    .get("delta", {})
                                    .get("content")
                            ):
                                yield delta
                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException as e:
            raise RuntimeError(_friendly_timeout_msg(e, self.base_url)) from e

    # ── Embeddings ────────────────────────────────────────────────────────────

    async def embeddings(self, text: str) -> list[float]:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=NON_STREAM_TIMEOUT)

        try:
            response = await self._client.post(
                f"{self.base_url}/embeddings",
                json={"input": text, "model": self.model or "default"},
            )
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]
        except httpx.TimeoutException as e:
            raise RuntimeError(_friendly_timeout_msg(e, self.base_url)) from e

    def embeddings_sync(self, text: str) -> list[float]:
        if not self._sync_client:
            self._sync_client = httpx.Client(timeout=NON_STREAM_TIMEOUT)

        try:
            response = self._sync_client.post(
                f"{self.base_url}/embeddings",
                json={"input": text, "model": self.model or "default"},
            )
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]
        except httpx.TimeoutException as e:
            raise RuntimeError(_friendly_timeout_msg(e, self.base_url)) from e

    # ── Model list ─────────────────────────────────────────────────────────────

    async def list_models(self) -> list[str]:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=NON_STREAM_TIMEOUT)
        try:
            response = await self._client.get(f"{self.base_url}/models")
            response.raise_for_status()
            return [m["id"] for m in response.json().get("data", [])]
        except (httpx.HTTPError, httpx.TimeoutException):
            try:
                return await self._list_models_ollama_async()
            except (httpx.HTTPError, httpx.TimeoutException):
                return [self.model] if self.model else []

    # ── Health checks ──────────────────────────────────────────────────────────

    async def health_check(self) -> bool:
        # Uses a local short-timeout client — does NOT clobber self._client
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self.base_url}/models")
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                    response = await client.get(f"{self._root_base_url()}/api/tags")
                    return response.status_code == 200
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError):
                return False

    def health_check_sync(self) -> bool:
        try:
            with httpx.Client(timeout=httpx.Timeout(5.0)) as client:
                response = client.get(f"{self.base_url}/models")
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            try:
                with httpx.Client(timeout=httpx.Timeout(5.0)) as client:
                    response = client.get(f"{self._root_base_url()}/api/tags")
                    return response.status_code == 200
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError):
                return False
