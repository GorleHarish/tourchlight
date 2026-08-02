"""
Unit tests for the adaptive, headroom-driven context budget coordinator.

Budgets must expand to use idle context (no reserved tokens sitting unused)
and shrink under pressure so the conversation never gets crowded out.
"""

from core.memory.budget import ContextBudget
from core.memory.manager import TieredMemory, MemoryConfig


def test_effective_budget_uses_idle_headroom_on_large_window():
    memory = TieredMemory(MemoryConfig(max_tokens=12288))
    budget = memory.get_effective_budget()

    # Fresh session on a 12k window: nothing is using the context, so the L0
    # budget should expand well beyond the static 1600-char default.
    assert budget.target_tokens == int(12288 * 0.85)
    assert budget.headroom_tokens > 8000
    assert budget.l0_tokens > 600
    assert budget.l0_chars > 1600
    assert budget.scratchpad_entry_limit > 120
    assert budget.scratchpad_section_cap >= 5


def test_effective_budget_shrinks_under_pressure():
    memory = TieredMemory(MemoryConfig(max_tokens=4096))
    # Consume most of the target window with conversation content.
    memory.add_user_message("tokens " * 3500)
    budget = memory.get_effective_budget()

    assert budget.l0_chars < 1600
    assert budget.l0_tokens == budget.l0_min_tokens
    assert budget.headroom_tokens == 0
    assert budget.utilization() > 0.9


def test_l0_budget_expands_with_headroom():
    memory = TieredMemory(MemoryConfig(max_tokens=12288))
    long = "decision" * 30
    memory.state.decisions = [long] * 8
    memory.state.tried_and_failed = ["tried and failed entry"]

    pad = memory.format_l0_scratchpad()
    budget = memory.get_effective_budget()
    assert len(pad) > 1600
    assert len(pad) <= budget.l0_chars
    # Expanded budget keeps low-priority sections that a static cap would drop.
    assert "- Tried & Failed: " in pad


def test_l0_budget_surfaces_more_entries_when_roomy():
    memory = TieredMemory(MemoryConfig(max_tokens=12288))
    for i in range(10):
        memory.state.decisions.append(f"decision {i}")
        memory.state.errors_seen.append(f"error {i}")

    pad = memory.format_l0_scratchpad()
    assert "decision 9" in pad
    assert "decision 4" in pad
    assert "error 7" in pad


def test_pinned_budget_scales_with_headroom():
    tight = ContextBudget(max_tokens=4096, used_tokens=3900, base_pinned_tokens=600)
    roomy = ContextBudget(max_tokens=12288, used_tokens=0, base_pinned_tokens=600)

    assert tight.pinned_tokens < 600
    assert roomy.pinned_tokens > 600
    assert tight.pinned_tokens >= tight.pinned_min_tokens
    assert roomy.pinned_tokens <= int(
        roomy.base_pinned_tokens * roomy.pinned_max_multiplier
    )


def test_context_budget_bounds():
    budget = ContextBudget(max_tokens=4096, used_tokens=2000, base_pinned_tokens=300)

    assert budget.l0_min_tokens <= budget.l0_tokens <= budget.l0_max_tokens
    assert 3 <= budget.scratchpad_section_cap <= 8
    assert 60 <= budget.scratchpad_entry_limit <= 240
    assert budget.pinned_min_tokens <= budget.pinned_tokens
    assert budget.recent_min_tokens <= budget.recent_tokens <= budget.recent_max_tokens
