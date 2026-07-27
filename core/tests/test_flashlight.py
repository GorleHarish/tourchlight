import pytest
from core.flashlight.indexer import SymbolIndex, FileEntry, SUPPORTED_EXTENSIONS, IGNORE_DIRS


def test_supported_extensions():
    assert ".py" in SUPPORTED_EXTENSIONS
    assert ".js" in SUPPORTED_EXTENSIONS
    assert ".rs" in SUPPORTED_EXTENSIONS


def test_ignore_dirs():
    assert ".git" in IGNORE_DIRS
    assert "__pycache__" in IGNORE_DIRS
    assert "node_modules" in IGNORE_DIRS


def test_file_entry():
    entry = FileEntry(rel_path="test.py", lines=["line1", "line2"], symbols=[("foo", 1, "fn")], imports=[])
    assert entry.rel_path == "test.py"
    assert entry.size == 2


def test_symbol_index_build(tmp_path):
    # Create a test file
    test_file = tmp_path / "test.py"
    test_file.write_text("def foo():\n    pass\nclass Bar:\n    pass\n")
    
    index = SymbolIndex(tmp_path)
    count = index.build()
    assert count == 1
    assert "test.py" in index.files
    assert len(index.files["test.py"].symbols) == 2


def test_symbol_index_summary(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("def foo():\n    pass\n")
    
    index = SymbolIndex(tmp_path)
    index.build()
    summary = index.summary()
    assert "test" in summary.lower() or "1 files" in summary
