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


def test_edit_file_line_bounded():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "sample.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("val = 1\nval = 1\nval = 1\n")

        res = tool_edit_file_impl({"path": "sample.py", "old_text": "val = 1", "new_text": "val = 99", "start_line": 2, "end_line": 2}, project_root=tmpdir)
        assert "Surgically edited" in res

        with open(test_file, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        assert lines[0] == "val = 1"
        assert lines[1] == "val = 99"
        assert lines[2] == "val = 1"


def test_edit_file_symbol_anchored():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "code.py")
        code = "def alpha():\n    return 'old'\n\ndef beta():\n    return 42\n"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(code)

        new_fn = "def alpha():\n    return 'new'"
        res = tool_edit_file_impl({"path": "code.py", "symbol": "alpha", "new_text": new_fn}, project_root=tmpdir)
        assert "Surgically replaced symbol 'alpha'" in res

        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()

        assert "return 'new'" in updated
        assert "def beta():" in updated


def test_edit_file_multi_chunk():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "multi.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("a = 1\nb = 2\nc = 3\n")

        chunks = [
            {"old_text": "a = 1", "new_text": "a = 10"},
            {"old_text": "c = 3", "new_text": "c = 30"}
        ]
        res = tool_edit_file_impl({"path": "multi.py", "chunks": chunks}, project_root=tmpdir)
        assert "Chunk 1:" in res and "Chunk 2:" in res

        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()

        assert "a = 10" in updated
        assert "b = 2" in updated
        assert "c = 30" in updated


def test_edit_file_diagnostic_nudge():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "diag.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def calculate_total_amount(items):\n    return sum(items)\n")

        res = tool_edit_file_impl({"path": "diag.py", "old_text": "def totally_different_function_name(x, y, z):\n    return x + y + z"}, project_root=tmpdir)
        assert "Edit failed:" in res
        assert "HINT" in res or "READ_FILE" in res

