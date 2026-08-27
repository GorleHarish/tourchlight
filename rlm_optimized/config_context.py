"""Context window profiles and budget allocations for small and large LLMs."""

from __future__ import annotations

import os
from enum import Enum


# Default base context window size (12288 tokens for TurboQuant)
CTX_SIZE = int(os.environ.get("RLM_CTX_SIZE", "12288"))

class ContextProfile(Enum):
    """Context window profiles with profile-specific budget allocations."""
    SMALL_4K = "4k"       # 4096 tokens - Gemma 2B, small models
    MEDIUM_8K = "8k"      # 8192 tokens - medium models
    LARGE_12K = "12k"     # 12288 tokens - TurboQuant base (default)
    XLARGE_32K = "32k"    # 32768 tokens - large context models
    CUSTOM = "custom"     # Custom context size

    @classmethod
    def from_context_size(cls, ctx_size: int) -> "ContextProfile":
        """Auto-detect profile from context size."""
        if ctx_size <= 5000:
            return cls.SMALL_4K
        elif ctx_size <= 9000:
            return cls.MEDIUM_8K
        elif ctx_size <= 16000:
            return cls.LARGE_12K
        elif ctx_size <= 40000:
            return cls.XLARGE_32K
        else:
            return cls.CUSTOM

    def get_budget_allocations(self, max_tokens: int, metadata_overhead: int = 0) -> dict:
        """Get profile-specific budget allocations."""
        available = max(0, max_tokens - metadata_overhead)
        
        if self == ContextProfile.SMALL_4K:
            return {
                "recent_window": 1,
                "recent_tokens_fraction": 0.40,
                "pinned_token_budget": 200,
                "compression_threshold": 0.80,
                "summary_trigger_fraction": 0.40,
                "message_compact_threshold": 200,
                "l0_scratchpad_fraction": 0.10,
                "max_messages": 50,
            }
        elif self == ContextProfile.MEDIUM_8K:
            return {
                "recent_window": 2,
                "recent_tokens_fraction": 0.35,
                "pinned_token_budget": 300,
                "compression_threshold": 0.80,
                "summary_trigger_fraction": 0.50,
                "message_compact_threshold": 300,
                "l0_scratchpad_fraction": 0.08,
                "max_messages": 75,
            }
        elif self == ContextProfile.LARGE_12K:
            return {
                "recent_window": 3,
                "recent_tokens_fraction": 0.25,
                "pinned_token_budget": 600,
                "compression_threshold": 0.75,
                "summary_trigger_fraction": 0.75,
                "message_compact_threshold": 500,
                "l0_scratchpad_fraction": 0.07,
                "max_messages": 100,
            }
        elif self == ContextProfile.XLARGE_32K:
            return {
                "recent_window": 5,
                "recent_tokens_fraction": 0.20,
                "pinned_token_budget": 1000,
                "compression_threshold": 0.70,
                "summary_trigger_fraction": 0.75,
                "message_compact_threshold": 800,
                "l0_scratchpad_fraction": 0.05,
                "max_messages": 200,
            }
        else:
            # Custom - use 12K defaults
            return {
                "recent_window": 3,
                "recent_tokens_fraction": 0.25,
                "pinned_token_budget": 600,
                "compression_threshold": 0.75,
                "summary_trigger_fraction": 0.75,
                "message_compact_threshold": 500,
                "l0_scratchpad_fraction": 0.07,
                "max_messages": 100,
            }

    def apply_to_config(self, config, max_tokens: int, metadata_overhead: int = 0) -> None:
        """Apply profile-specific settings to a MemoryConfig."""
        allocations = self.get_budget_allocations(max_tokens, metadata_overhead)
        available = max(0, max_tokens - metadata_overhead)
        
        config.recent_window = allocations["recent_window"]
        config.recent_tokens = int(available * allocations["recent_tokens_fraction"])
        config.pinned_token_budget = allocations["pinned_token_budget"]
        config.compression_threshold = allocations["compression_threshold"]
        config.summary_trigger_tokens = int(available * allocations["summary_trigger_fraction"])
        config.message_compact_threshold = allocations["message_compact_threshold"]
        config.max_messages = allocations["max_messages"]


def get_context_profile() -> ContextProfile:
    """Get the current context profile based on CTX_SIZE."""
    return ContextProfile.from_context_size(CTX_SIZE)

def estimate_metadata_overhead(
    system_content: str = "", ctx_size: int = CTX_SIZE
) -> int:
    """Estimate tokens consumed by system prompt, tool schemas, and the flashlight beam."""
    base = max(400, len(system_content) // 4) if system_content else 800
    if ctx_size <= 5000:
        beam = 600
    elif ctx_size <= 9000:
        beam = 1500
    else:
        beam = 3000
    return base + beam
