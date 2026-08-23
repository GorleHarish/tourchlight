"""
Abstract LLM client interface and shared inference parameters.

All LLM backends (LM Studio, llama.cpp, Ollama, cloud) implement this protocol.
"""

import re
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Protocol, runtime_checkable


def detect_model_traits(model_name: Optional[str]) -> dict:
    """
    Detect architecture traits (size, reasoning status, vision capability) from model name.

    Returns dict:
      {
         "is_reasoning": bool,
         "param_size_b": Optional[float], # e.g. 1.5, 2.0, 3.0, 7.0, 8.0, 70.0
         "is_small_model": bool,          # True if parameter size < 4.0B
         "is_vision": bool,               # True if multimodal vision model (Gemma 3, Qwen VL, etc.)
      }
    """
    if not model_name or not isinstance(model_name, str):
        return {
            "is_reasoning": False,
            "param_size_b": None,
            "is_small_model": False,
            "is_vision": False,
        }

    name_lower = model_name.lower()

    # 1. Reasoning model detection
    is_reasoning = any(
        k in name_lower
        for k in ["deepseek-r1", "-r1", "qwq", "reasoner", "o1-", "o3-"]
    )

    # 2. Parameter size detection via regex (matches 1.5b, 2b, 3b, 7b, 8b, 14b, 32b, 70b in paths/ggufs)
    match = re.search(r"(?:^|[^0-9a-zA-Z])(\d+(?:\.\d+)?)[bB](?![a-zA-Z0-9])", model_name)
    param_size_b = float(match.group(1)) if match else None

    if param_size_b is None:
        if "4e4b" in name_lower or "e4b" in name_lower:
            param_size_b = 4.0
        elif "e2b" in name_lower:
            param_size_b = 2.0

    is_small_model = param_size_b is not None and param_size_b <= 4.0

    # 3. Vision / Multimodal model detection (Gemma 3, Qwen VL, Llama Vision, GPT-4o, Gemini, etc.)
    is_vision = any(
        k in name_lower
        for k in [
            "gemma-3",
            "gemma3",
            "qwen2.5-vl",
            "qwen2-vl",
            "qwenvl",
            "qwen-vl",
            "llama-3.2-11b-vision",
            "llama-3.2-90b-vision",
            "llama-vision",
            "llava",
            "moondream",
            "gpt-4o",
            "gpt-4-vision",
            "gpt-4-turbo",
            "gemini-1.5",
            "gemini-2.0",
            "gemini-2.5",
            "gemini-flash",
            "gemini-pro",
            "claude-3",
            "claude-3-5",
            "claude-3-7",
            "-vl-",
            "-vl",
            "vision",
            "multimodal",
            "mmproj",
        ]
    )

    return {
        "is_reasoning": is_reasoning,
        "param_size_b": param_size_b,
        "is_small_model": is_small_model,
        "is_vision": is_vision,
    }


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
    repetition_penalty: Optional[float] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.10
    seed: int = -1  # -1 = random
    stop: list[str] = field(default_factory=list)
    use_grammar: Optional[bool] = None
    allowed_tools: Optional[list[str]] = None

    def __post_init__(self):
        if self.repetition_penalty is not None:
            self.repeat_penalty = self.repetition_penalty
        else:
            self.repetition_penalty = self.repeat_penalty

    def describe(self) -> str:
        """One-line description of current params."""
        rep = self.repeat_penalty if self.repeat_penalty is not None else self.repetition_penalty
        return f"temp={self.temperature}, top_k={self.top_k}, top_p={self.top_p}, rep={rep}"

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
        rep = self.repeat_penalty if self.repeat_penalty is not None else self.repetition_penalty
        if rep is not None and rep != 1.0:
            payload["repeat_penalty"] = rep
            payload["repetition_penalty"] = rep
            payload["repetition_context_size"] = 256
            payload["repeat_last_n"] = 256
        if self.presence_penalty != 0.0:
            payload["presence_penalty"] = self.presence_penalty
        if self.frequency_penalty != 0.0:
            payload["frequency_penalty"] = self.frequency_penalty
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
            temperature=0.1,
            top_k=20,
            top_p=0.90,
            min_p=0.05,
            repeat_penalty=1.02,
            seed=-1,
            stop=["</tool_call>", "</FINAL_ANSWER>"],
        )

    @classmethod
    def for_planning(cls) -> "InferenceParams":
        """Reasoning through plans. Moderate creativity. All tools remain available."""
        return cls(
            temperature=0.45,
            top_k=40,
            top_p=0.90,
            min_p=0.08,
            repeat_penalty=1.12,
            seed=-1,
            stop=["</tool_call>", "</FINAL_ANSWER>"],
        )

    @classmethod
    def for_troubleshoot(cls) -> "InferenceParams":
        """Diagnosing errors. Slightly more exploration."""
        return cls(
            temperature=0.3,
            top_k=35,
            top_p=0.92,
            min_p=0.05,
            repeat_penalty=1.02,
            seed=-1,
            stop=["</tool_call>", "</FINAL_ANSWER>"],
        )

    @classmethod
    def for_chat(cls) -> "InferenceParams":
        """General conversation."""
        return cls(
            temperature=0.7,
            top_k=50,
            top_p=0.95,
            min_p=0.05,
            repeat_penalty=1.02,
            seed=-1,
            stop=["</FINAL_ANSWER>"],
        )

    @classmethod
    def for_critic(cls) -> "InferenceParams":
        """Adversarial critique / debate. Focused flaw identification."""
        return cls(
            temperature=0.2,
            top_k=25,
            top_p=0.90,
            min_p=0.05,
            repeat_penalty=1.05,
            seed=-1,
            stop=["</CRITIQUE>", "</FINAL_ANSWER>"],
        )

    @classmethod
    def for_refine(cls) -> "InferenceParams":
        """Synthesis and refinement following critique. Deterministic."""
        return cls(
            temperature=0.1,
            top_k=20,
            top_p=0.90,
            min_p=0.05,
            repeat_penalty=1.10,
            seed=-1,
            use_grammar=False,
            stop=["</REFINED_ANSWER>", "</FINAL_ANSWER>", "</tool_call>"],
        )

    @classmethod
    def for_model_and_phase(
        cls, model_name: Optional[str], phase: str = "code"
    ) -> "InferenceParams":
        """
        Dynamically return an InferenceParams preset calibrated for both
        the target model architecture (size & reasoning trait) and phase.
        Hardcoded for <7b models on 8GB RAM.
        """
        base_params = PRESETS.get(phase, cls.for_coding())

        params = cls(
            temperature=base_params.temperature,
            top_k=base_params.top_k,
            top_p=base_params.top_p,
            min_p=base_params.min_p,
            repeat_penalty=base_params.repeat_penalty,
            repetition_penalty=base_params.repetition_penalty,
            presence_penalty=base_params.presence_penalty,
            frequency_penalty=base_params.frequency_penalty,
            seed=base_params.seed,
            stop=list(base_params.stop),
            use_grammar=base_params.use_grammar,
            allowed_tools=base_params.allowed_tools,
        )

        traits = detect_model_traits(model_name)
        is_small = traits.get("is_small_model", False) or (
            traits.get("param_size_b") is not None and traits["param_size_b"] <= 4.0
        )

        if is_small:
            # Small models (<=4B, e.g. Qwen2.5-Coder-3B, Gemma 2B, DeepSeek-1.5B) have narrow attention dynamic range
            # and require aggressive presence/frequency penalties and repeat_penalty >= 1.12 to break degenerate token loops.
            params.repeat_penalty = max(params.repeat_penalty, 1.12)
            params.repetition_penalty = params.repeat_penalty
            params.presence_penalty = max(params.presence_penalty, 0.20)
            params.frequency_penalty = max(params.frequency_penalty, 0.15)
            if phase in ["plan", "chat"]:
                params.temperature = max(params.temperature, 0.25)
        else:
            # Standard models (7B, 14B, 32B, 70B)
            params.repeat_penalty = max(params.repeat_penalty, 1.08)
            params.repetition_penalty = params.repeat_penalty
            params.presence_penalty = max(params.presence_penalty, 0.15)
            params.frequency_penalty = max(params.frequency_penalty, 0.10)
            if phase in ["plan", "chat"]:
                params.temperature = max(params.temperature, 0.20)

        return params


# ── Phase presets ──────────────────────────────────────────────────────────

PRESETS: dict[str, InferenceParams] = {
    "code": InferenceParams.for_coding(),
    "plan": InferenceParams.for_planning(),
    "goal": InferenceParams.for_coding(),
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
