import pytest
from core.tools.implementations import (
    tool_read_file_impl, tool_write_file_impl, tool_edit_file_impl,
    tool_read_symbols_impl, tool_list_dir_impl, tool_grep_impl,
    tool_run_command_impl, tool_verify_impl,
)


def test_read_file_impl(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("def foo():\n    pass\n")
    result = tool_read_file_impl({"path": str(test_file)}, str(tmp_path))
    assert "foo" in result
    assert "def" in result


def test_read_file_impl_not_found(tmp_path):
    result = tool_read_file_impl({"path": "nonexistent.py"}, str(tmp_path))
    assert "not found" in result.lower() or "error" in result.lower()


def test_write_file_impl(tmp_path):
    result = tool_write_file_impl(
        {"path": "new.py", "content": "print('hello')"},
        str(tmp_path),
    )
    assert "Written" in result or "Error" not in result
    assert (tmp_path / "new.py").exists()


def test_write_file_impl_missing_path(tmp_path):
    result = tool_write_file_impl({"content": "test"}, str(tmp_path))
    assert "Missing" in result or "Error" in result


def test_edit_file_impl(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("def foo():\n    pass\n")
    result = tool_edit_file_impl(
        {"path": "test.py", "old_text": "pass", "new_text": "return 42"},
        str(tmp_path),
    )
    assert "Surgically" in result or "edited" in result.lower()
    assert test_file.read_text() == "def foo():\n    return 42\n"


def test_edit_file_impl_not_found(tmp_path):
    result = tool_edit_file_impl(
        {"path": "nope.py", "old_text": "a", "new_text": "b"},
        str(tmp_path),
    )
    assert "not found" in result.lower() or "error" in result.lower()


def test_read_symbols_impl(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("def foo():\n    pass\nclass Bar:\n    pass\n")
    result = tool_read_symbols_impl({"path": "test.py"}, str(tmp_path))
    assert "foo" in result
    assert "Bar" in result


def test_list_dir_impl(tmp_path):
    (tmp_path / "file.txt").write_text("hello")
    (tmp_path / "subdir").mkdir()
    result = tool_list_dir_impl({"path": "."}, str(tmp_path))
    assert "file.txt" in result
    assert "subdir" in result


def test_grep_impl(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("def foo():\n    pass\ndef bar():\n    pass\n")
    result = tool_grep_impl({"pattern": "def foo", "path": "."}, str(tmp_path))
    assert "foo" in result


def test_grep_impl_file_path(tmp_path):
    test_file = tmp_path / "target.py"
    test_file.write_text("def target_function():\n    return 100\n")
    result = tool_grep_impl({"pattern": "target_function", "path": "target.py"}, str(tmp_path))
    assert "target_function" in result


def test_grep_impl_no_match(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("def foo():\n    pass\n")
    result = tool_grep_impl({"pattern": "xyz", "path": "."}, str(tmp_path))
    assert "no matches" in result.lower()


def test_run_command_impl():
    result = tool_run_command_impl({"cmd": "echo hello"}, ".")
    assert "hello" in result


def test_run_command_impl_fail():
    result = tool_run_command_impl({"cmd": "false"}, ".")
    assert "Exit" in result or "Error" in result


def test_verify_impl(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("hello world")
    result = tool_verify_impl({"path": "test.py"}, str(tmp_path))
    assert "SUCCESS" in result


def test_verify_impl_with_expected(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("hello world")
    result = tool_verify_impl(
        {"path": "test.py", "expected_snippet": "hello"},
        str(tmp_path),
    )
    assert "SUCCESS" in result


def test_verify_impl_not_found(tmp_path):
    result = tool_verify_impl({"path": "nope.py"}, str(tmp_path))
    assert "FAILED" in result


def test_run_command_impl_stderr_and_stdout():
    result = tool_run_command_impl({"cmd": "echo 'out' && echo 'err' >&2"}, ".")
    assert "out" in result
    assert "err" in result


def test_grep_hyphen_pattern(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("option -m description\n")
    result = tool_grep_impl({"pattern": "-m", "path": "."}, str(tmp_path))
    assert "-m" in result

