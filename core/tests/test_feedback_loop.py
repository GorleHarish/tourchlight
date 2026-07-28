import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.execution.feedback_loop import (
    ExecutionFeedbackLoop,
    TestResult,
    TestResultStatus,
    TestRunResult,
    extract_surgical_traceback,
)
from core.errors.types import TestFailureError
from core.errors.recovery import get_recovery_hint


def test_extract_surgical_traceback_pytest():
    pytest_output = """
============================= test session starts ==============================
platform darwin -- Python 3.11.0, pytest-7.4.0
rootdir: /path/to/project
collected 5 items

core/tests/test_foo.py .F...

=================================== FAILURES ===================================
_________________________________ test_addition ________________________________

    def test_addition():
>       assert 2 + 2 == 5
E       AssertionError: assert 4 == 5

core/tests/test_foo.py:12: AssertionError
=========================== short test summary info ============================
FAILED core/tests/test_foo.py::test_addition - AssertionError: assert 4 == 5
============================== 1 failed in 0.05s ===============================
"""
    surgical = extract_surgical_traceback(pytest_output, "python -m pytest")
    assert "FAILURES" in surgical
    assert "assert 2 + 2 == 5" in surgical
    assert "AssertionError: assert 4 == 5" in surgical
    assert "test session starts" not in surgical
    assert "platform darwin" not in surgical


def test_extract_surgical_traceback_syntax_error():
    syntax_error_output = """
============================= test session starts ==============================
Traceback (most recent call last):
  File "core/foo.py", line 10, in <module>
    def broken_func(:
                    ^
SyntaxError: invalid syntax
"""
    surgical = extract_surgical_traceback(syntax_error_output, "python -m pytest")
    assert "Traceback (most recent call last):" in surgical
    assert "SyntaxError: invalid syntax" in surgical


def test_get_recovery_hint_test_failure():
    err = TestFailureError(
        command="python -m pytest -x",
        failing_tests=["test_addition", "test_subtraction"],
        surgical_traceback="AssertionError: assert 4 == 5",
    )
    hint = get_recovery_hint(err)
    assert "Post-edit test failure in test_addition, test_subtraction" in hint
    assert "Inspect the surgical traceback" in hint


def test_feedback_loop_trigger_and_context(tmp_path):
    loop = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True, auto_run=True)

    # 1. Non-edit tool should not run tests
    res = loop.on_tool_executed("READ_FILE", {"path": "main.py"}, "content")
    assert res is None

    # 2. EDIT_FILE registers modified file
    with patch.object(loop, "_detect_test_command", return_value="python -m pytest"):
        mock_run = MagicMock()
        mock_run.returncode = 1
        mock_run.stdout = """
=================================== FAILURES ===================================
_________________________________ test_bug __________________________________
>   assert False
E   AssertionError
core/test_demo.py:5: AssertionError
"""
        mock_run.stderr = ""

        with patch("subprocess.run", return_value=mock_run):
            test_run = loop.on_tool_executed("EDIT_FILE", {"path": "main.py", "content": "bad code"}, "Success")

            assert test_run is not None
            assert not test_run.all_passed
            
            err = loop.get_test_failure_error()
            assert isinstance(err, TestFailureError)
            assert "AssertionError" in err.surgical_traceback

            ctx = loop.build_feedback_context()
            assert "[POST-EDIT TEST FAILURE DETECTED]" in ctx
            assert "Recovery Hint:" in ctx
            assert "AssertionError" in ctx


def test_extract_surgical_traceback_ansi_stripping():
    ansi_output = "\x1b[31m=================================== FAILURES ===================================\x1b[0m\n\x1b[1mAssertionError: 4 == 5\x1b[0m"
    surgical = extract_surgical_traceback(ansi_output)
    assert "\x1b[" not in surgical
    assert "FAILURES" in surgical
    assert "AssertionError: 4 == 5" in surgical


def test_scoped_test_command_detection(tmp_path):
    (tmp_path / "pyproject.toml").touch()
    loop = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True, auto_run=True)
    loop._files_modified_since_test.add("core/tests/test_feature.py")
    cmd = loop._detect_test_command()
    assert "pytest core/tests/test_feature.py" in cmd

