"""
Abstract LLM client interface and shared inference parameters.

All LLM backends (LM Studio, llama.cpp, Ollama, cloud) implement this protocol.
"""

from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Protocol, runtime_checkable


# ── Inference parameters ──────────────────────────────────────────────────

@dataclass
class InferenceParams:
    """
    Sampling parameters forwarded to the LLM /chat/completions endpoint.
    Only non-None fields are included in the API payload.

    A coding agent has three distinct phases, each needing different sampling:
      PLAN          — moderate creativity, structured output
      CODE          — near-determinism, exact syntax matters
      TROUBLESHOOT  — slightly more exploration than coding
      CHAT          — default conversational settings
    """
    temperature: float = 0.7
    top_k: int = 50
    top_p: float = 0.95
    min_p: float = 0.05
    repeat_penalty: float = 1.05
    seed: int = -1  # -1 = random
    stop: list[str] = field(default_factory=list)
    use_grammar: Optional[bool] = None

    def describe(self) -> str:
        """One-line description of current params."""
        return f"temp={self.temperature}, top_k={self.top_k}, top_p={self.top_p}, rep={self.repeat_penalty}"

    def to_payload(self) -> dict:
        """Convert to API payload dict, excluding None and default values."""
        payload = {}
        if self.temperature != 0.7:
            payload["temperature"] = self.temperature
        if self.top_k != 50:
            payload["top_k"] = self.top_k
        if self.top_p != 0.95:
            payload["top_p"] = self.top_p
        if self.min_p != 0.05:
            payload["min_p"] = self.min_p
        if self.repeat_penalty != 1.0:
            payload["repeat_penalty"] = self.repeat_penalty
        if self.seed != -1:
            payload["seed"] = self.seed
        if self.stop:
            payload["stop"] = self.stop
        return payload

    # ── Named presets ─────────────────────────────────────────────────────

    @classmethod
    def for_coding(cls) -> "InferenceParams":
        """Writing code files. Near-deterministic — exact syntax matters."""
        return cls(
            temperature=0.1, top_k=20, top_p=0.90,
            min_p=0.05, repeat_penalty=1.10, seed=-1,
        )

    @classmethod
    def for_planning(cls) -> "InferenceParams":
        """Reasoning through plans. Moderate creativity."""
        return cls(
            temperature=0.4, top_k=40, top_p=0.92,
            min_p=0.05, repeat_penalty=1.05, seed=-1,
        )

    @classmethod
    def for_troubleshoot(cls) -> "InferenceParams":
        """Diagnosing errors. Slightly more exploration."""
        return cls(
            temperature=0.3, top_k=35, top_p=0.92,
            min_p=0.05, repeat_penalty=1.05, seed=-1,
        )

    @classmethod
    def for_chat(cls) -> "InferenceParams":
        """General conversation."""
        return cls(
            temperature=0.7, top_k=50, top_p=0.95,
            min_p=0.05, repeat_penalty=1.05, seed=-1,
        )

    @classmethod
    def for_critic(cls) -> "InferenceParams":
        """Adversarial critique / debate. Focused flaw identification."""
        return cls(
            temperature=0.2, top_k=25, top_p=0.90,
            min_p=0.05, repeat_penalty=1.05, seed=-1, use_grammar=False,
        )

    @classmethod
    def for_refine(cls) -> "InferenceParams":
        """Synthesis and refinement following critique. Deterministic."""
        return cls(
            temperature=0.1, top_k=20, top_p=0.90,
            min_p=0.05, repeat_penalty=1.10, seed=-1, use_grammar=False,
        )


# ── Phase presets ──────────────────────────────────────────────────────────

PRESETS: dict[str, InferenceParams] = {
    "code": InferenceParams.for_coding(),
    "plan": InferenceParams.for_planning(),
    "troubleshoot": InferenceParams.for_troubleshoot(),
    "chat": InferenceParams.for_chat(),
    "critic": InferenceParams.for_critic(),
    "refine": InferenceParams.for_refine(),
}


# ── LLM Client Protocol ──────────────────────────────────────────────────

@runtime_checkable
class LLMClient(Protocol):
    """
    Protocol that all LLM backends must implement.

    Both sync and async methods are defined. Backends may implement
    one or both depending on their capabilities.
    """

    async def chat(
        self,
        messages: list[dict],
        params: Optional[InferenceParams] = None,
    ) -> str:
        """Send messages and return the full response."""
        ...

    async def chat_stream(
        self,
        messages: list[dict],
        params: Optional[InferenceParams] = None,
    ) -> AsyncIterator[str]:
        """Send messages and yield response chunks."""
        ...

    async def health_check(self) -> bool:
        """Check if the backend is reachable."""
        ...

    async def list_models(self) -> list[str]:
        """List available models."""
        ...

    def query(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        """Simple query interface (for backward compatibility)."""
        ...
