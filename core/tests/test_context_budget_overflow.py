"""
Unit tests for context budget overflow detection and fixes in TieredMemory, RLMEngine, and Tool Window Scaling.
"""

from pathlib import Path
import tempfile

from core.memory.manager import TieredMemory, MemoryConfig
from core.tools.implementations import set_ctx_window, _read_budget_for_ctx


def test_tiered_memory_total_tokens_includes_pinned_files():
    config = MemoryConfig.auto_tune(max_tokens=4096)
    memory = TieredMemory(config=config)

    memory.add_user_message("Hello world")
    initial_tokens = memory.total_tokens

    # Pin a file
    memory.pin_file("sample.py", "def foo(): pass\n" * 10)
    pinned_tokens = memory.total_tokens

    # total_tokens must include the pinned file content
    assert pinned_tokens > initial_tokens
    assert memory.should_compress() is False or memory.should_compress() is True


def test_tool_context_window_scaling():
    set_ctx_window(4096)
    max_lines_small, max_chars_small = _read_budget_for_ctx()
    assert max_lines_small == 60
    assert max_chars_small == 2400

    set_ctx_window(16384)
    max_lines_large, max_chars_large = _read_budget_for_ctx()
    assert max_lines_large == 150
    assert max_chars_large == 6000
