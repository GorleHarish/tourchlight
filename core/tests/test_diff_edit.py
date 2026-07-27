"""
Tests for Aider-style Search/Replace block editing (Approach B)
and dynamic JIT context pinning scaling (Approach C).
"""

import os
import tempfile
import pytest

from core.tools.implementations import tool_edit_file_impl, _parse_diff_block
from core.memory.manager import MemoryConfig, TieredMemory


def test_parse_diff_block_valid():
    text = """<<<<<<< SEARCH
def foo():
    return 1
=======
def foo():
    return 2
>>>>>>> REPLACE"""
    old_text, new_text = _parse_diff_block(text)
    assert old_text == "def foo():\n    return 1"
    assert new_text == "def foo():\n    return 2"


def test_parse_diff_block_invalid():
    old_text, new_text = _parse_diff_block("invalid diff string")
    assert old_text is None
    assert new_text is None


def test_edit_file_with_diff_block():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a - b\n")

        diff_block = """<<<<<<< SEARCH
def add(a, b):
    return a - b
=======
def add(a, b):
    return a + b
>>>>>>> REPLACE"""

        res = tool_edit_file_impl({"path": "test.py", "diff": diff_block}, project_root=tmpdir)
        assert "Surgically edited" in res or "fuzzy" in res

        with open(test_file, "r", encoding="utf-8") as f:
            updated_content = f.read()

        assert "return a + b" in updated_content


def test_edit_file_diff_block_in_old_text():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("x = 10\ny = 20\n")

        diff_block = """<<<<<<< SEARCH
x = 10
=======
x = 100
>>>>>>> REPLACE"""

        res = tool_edit_file_impl({"path": "test.py", "old_text": diff_block}, project_root=tmpdir)
        assert "Surgically edited" in res or "fuzzy" in res

        with open(test_file, "r", encoding="utf-8") as f:
            updated_content = f.read()

        assert "x = 100" in updated_content


def test_memory_config_auto_tune_pinned_budget():
    config_4k = MemoryConfig.auto_tune(max_tokens=4000)
    assert config_4k.pinned_token_budget == 300

    config_8k = MemoryConfig.auto_tune(max_tokens=8000)
    assert config_8k.pinned_token_budget == 600

    config_12k = MemoryConfig.auto_tune(max_tokens=12000)
    assert config_12k.pinned_token_budget == 1000


def test_pin_file_truncation_to_budget():
    config = MemoryConfig(max_tokens=4000, pinned_token_budget=100)
    mem = TieredMemory(config)

    # Large content
    large_content = "\n".join([f"line_{i} = {i}" for i in range(100)])
    mem.pin_file("large.py", large_content)

    pinned = mem.get_pinned_files()
    assert len(pinned) == 1
    path, pinned_content = pinned[0]
    assert path == "large.py"
    assert "truncated" in pinned_content
