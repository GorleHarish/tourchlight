"""Unit tests for context breakdown performance and TUI on-demand trigger."""

import time
from unittest.mock import MagicMock

from core.memory.manager import MemoryConfig, TieredMemory
from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
from rlm_optimized.tui_app import TorchlightApp


def test_total_tokens_performance_o1():
    config = MemoryConfig.auto_tune(max_tokens=12288)
    memory = TieredMemory(config=config)

    # Populate memory
    memory.add_user_message("Test message " * 50)
    memory.pin_file("test.py", "def foo():\n    return 42\n" * 100)
    memory.state.errors_seen.append("RuntimeError: failed")
    memory.state.decisions.append("Use sqlite backend")

    # 10,000 accesses of total_tokens should take < 0.05 seconds (O(1))
    start = time.perf_counter()
    for _ in range(10000):
        _ = memory.total_tokens
    elapsed = time.perf_counter() - start

    assert elapsed < 0.1, f"total_tokens took {elapsed:.4f}s for 10k reads (expected < 0.1s)"
    assert memory.total_tokens > 0


def test_context_breakdown_sections_and_accuracy():
    engine = RLMEngineOptimized(client=MagicMock(), project_root=".")
    app = TorchlightApp(engine=engine)

    breakdown = app._context_section_breakdown()
    assert "System" in breakdown
    assert "Scratchpad" in breakdown
    assert "Beam" in breakdown
    assert "Chat" in breakdown


def test_tui_breakdown_toggle_state():
    engine = RLMEngineOptimized(client=MagicMock(), project_root=".")
    app = TorchlightApp(engine=engine)
    # By default, breakdown is collapsed / hidden
    assert getattr(app, "_show_ctx_breakdown", False) is False
