"""
Tests for read/edit tool memory synchronization (unpin_file, refresh_pin).
"""

import os
import tempfile
import pytest
from core.memory.manager import TieredMemory, MemoryConfig
from core.tools.implementations import tool_write_file_impl, tool_edit_file_impl


def test_memory_unpin_file():
    mem = TieredMemory(MemoryConfig())
    mem.pin_file("a.py", "print(1)")
    mem.pin_file("b.py", "print(2)")
    assert len(mem.get_pinned_files()) == 2

    mem.unpin_file("a.py")
    pinned = mem.get_pinned_files()
    assert len(pinned) == 1
    assert pinned[0][0] == "b.py"


def test_memory_refresh_pin():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def foo():\n    return 1\n")

        mem = TieredMemory(MemoryConfig())
        mem.pin_file("test.py", "def foo():\n    return 1\n")

        # Edit file on disk
        tool_edit_file_impl(
            {"path": "test.py", "old_text": "return 1", "new_text": "return 42"},
            project_root=tmpdir
        )

        # Refresh pin
        mem.refresh_pin("test.py", project_root=tmpdir)
        pinned = mem.get_pinned_files()
        assert len(pinned) == 1
        assert "42" in pinned[0][1]


def test_memory_refresh_pin_deleted_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        mem = TieredMemory(MemoryConfig())
        mem.pin_file("deleted.py", "some content")

        mem.refresh_pin("deleted.py", project_root=tmpdir)
        assert len(mem.get_pinned_files()) == 0
