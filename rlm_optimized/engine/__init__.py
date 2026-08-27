"""Engine package for RLMEngineOptimized."""

from __future__ import annotations

from rlm_optimized.engine.models import SolveResult, Step
from rlm_optimized.engine.phase_detector import PhaseDetectorMixin
from rlm_optimized.engine.response_parser import (
    ResponseParserMixin,
    _looks_like_full_file,
    _looks_like_prose_or_outline,
    _trim_trailing_prose,
)
from rlm_optimized.engine.stream_handler import StreamHandlerMixin
from rlm_optimized.engine.verification_gate import VerificationGateMixin

__all__ = [
    "Step",
    "SolveResult",
    "PhaseDetectorMixin",
    "StreamHandlerMixin",
    "ResponseParserMixin",
    "VerificationGateMixin",
    "_looks_like_prose_or_outline",
    "_looks_like_full_file",
    "_trim_trailing_prose",
]
