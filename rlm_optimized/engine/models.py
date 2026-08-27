"""Core data models for RLMEngine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Step:
    step_number: int
    depth: int
    action: str  # "code", "tool", "sub_queries", "final_answer", "thinking"
    thinking: str
    content: str
    result: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None


@dataclass
class SolveResult:
    answer: str
    steps: list[Step] = field(default_factory=list)
    depth: int = 0
    total_llm_calls: int = 0
    quality_score: float = 1.0
    gate_bypasses: int = 0
