"""
Debate & Self-Critique Verification module for Torchlight.
"""

from .prompts import CRITIC_SYSTEM_PROMPT, REFINER_SYSTEM_PROMPT
from .verifier import DebateVerifier, CritiqueResult

__all__ = [
    "DebateVerifier",
    "CritiqueResult",
    "CRITIC_SYSTEM_PROMPT",
    "REFINER_SYSTEM_PROMPT",
]
