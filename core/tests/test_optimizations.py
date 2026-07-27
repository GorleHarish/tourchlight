"""
Tests for performance and accuracy optimizations in Torchlight.
"""

import tempfile
from pathlib import Path
from core.tools.registry import get_tool_registry, ToolResult
from core.flashlight.indexer import SymbolIndex
from core.tools.implementations import tool_write_file_impl, _check_syntax


def test_batch_tool_execution():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "a.py").write_text("def foo(): pass", encoding="utf-8")
        (tmp_path / "b.py").write_text("def bar(): pass", encoding="utf-8")

        registry = get_tool_registry()
        tool_calls = [
            {"name": "READ_FILE", "arguments": {"path": "a.py"}},
            {"name": "READ_FILE", "arguments": {"path": "b.py"}},
            {"name": "GREP", "arguments": {"pattern": "def"}},
        ]

        results = registry.execute_batch(tool_calls, project_root=str(tmp_path))
        assert len(results) == 3
        assert all(isinstance(r, ToolResult) for r in results)
        assert all(r.success for r in results)


def test_symbol_index_mtime_cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        py_file = tmp_path / "main.py"
        py_file.write_text("def hello(): pass\n", encoding="utf-8")

        index = SymbolIndex(tmp_path)
        count1 = index.build()
        entry1 = index.files["main.py"]

        # Re-build without touching main.py -> expect cached entry instance reuse
        count2 = index.build()
        entry2 = index.files["main.py"]
        assert entry1 is entry2  # exact object reuse from cache!


def test_inline_syntax_guardrail():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Test valid Python syntax
        res_valid = tool_write_file_impl({"path": "clean.py", "content": "x = 10\n"}, project_root=str(tmp_path))
        assert "Syntax Warning" not in res_valid

        # Test broken Python syntax
        res_invalid = tool_write_file_impl({"path": "broken.py", "content": "def broken_func(\n"}, project_root=str(tmp_path))
        assert "Syntax Warning" in res_invalid
