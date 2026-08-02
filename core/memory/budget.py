"""
Adaptive, headroom-driven context budget coordinator for Torchlight.

Static reservations leave context idle when the conversation is small and
crowd the conversation when the window is tight. This module computes
effective, per-turn budgets that scale with real headroom so no context sits
unused:

- L0 scratchpad expands to enrich the model with more project memory (more
  decisions, errors, tried-and-failed entries, longer entries) when headroom is
  plentiful, and shrinks to protect the conversation when the window is tight.
- Pinned-file and recent-window reserves follow the same curve instead of
  being fixed ceilings.
- All allocations share a single target-utilization ceiling so the assembled
  prompt always stays inside the model's context window.
"""

from dataclasses import dataclass


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


@dataclass
class ContextBudget:
    """Effective budget allocations for the current turn.

    `used_tokens` is the live token footprint of the conversation (messages +
    pinned files) before the L0 scratchpad is rendered; `headroom_tokens` is the
    free space remaining up to the shared target-utilization ceiling.
    """

    max_tokens: int
    used_tokens: int
    base_pinned_tokens: int
    target_utilization: float = 0.85
    # L0 scratchpad
    l0_min_tokens: int = 150
    l0_max_tokens: int = 1200
    l0_headroom_share: float = 0.20
    # Pinned files
    pinned_min_tokens: int = 200
    pinned_max_multiplier: float = 1.5
    # Conversation recent-window reserve (feeds compression decisions)
    recent_min_tokens: int = 300
    recent_max_tokens: int = 3000
    recent_headroom_share: float = 0.15
    # Rendering approximations (chars <-> tokens)
    chars_per_token: int = 4
    entry_chars_per_token: int = 20

    @property
    def target_tokens(self) -> int:
        return int(self.max_tokens * self.target_utilization)

    @property
    def headroom_tokens(self) -> int:
        return max(0, self.target_tokens - self.used_tokens)

    @property
    def headroom_ratio(self) -> float:
        return min(1.0, self.headroom_tokens / max(1, self.target_tokens))

    @property
    def l0_tokens(self) -> int:
        """Token allowance for the L0 working memory scratchpad this turn."""
        return _clamp(
            int(self.headroom_tokens * self.l0_headroom_share),
            self.l0_min_tokens,
            self.l0_max_tokens,
        )

    @property
    def l0_chars(self) -> int:
        return self.l0_tokens * self.chars_per_token

    @property
    def scratchpad_entry_limit(self) -> int:
        """Max characters per scratchpad entry (longer when headroom is ample)."""
        return _clamp(self.l0_chars // self.entry_chars_per_token, 60, 240)

    @property
    def scratchpad_section_cap(self) -> int:
        """Max entries shown per state section (3 tight ... 8 rich)."""
        return _clamp(self.l0_tokens // 120, 3, 8)

    @property
    def pinned_tokens(self) -> int:
        """Token ceiling for pinned file content this turn."""
        scaled = int(self.base_pinned_tokens * (0.5 + 0.75 * self.headroom_ratio))
        return _clamp(
            scaled,
            self.pinned_min_tokens,
            int(self.base_pinned_tokens * self.pinned_max_multiplier),
        )

    @property
    def recent_tokens(self) -> int:
        """Token reserve kept for the recent-message window."""
        return _clamp(
            int(self.headroom_tokens * self.recent_headroom_share),
            self.recent_min_tokens,
            self.recent_max_tokens,
        )

    def utilization(self) -> float:
        """Current fraction of the target window in use."""
        return self.used_tokens / self.target_tokens if self.target_tokens else 0.0
