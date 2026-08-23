import subprocess

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
            test_run = loop.on_tool_executed(
                "EDIT_FILE", {"path": "main.py", "content": "bad code"}, "Success"
            )

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


def test_associated_test_command_detection(tmp_path):
    (tmp_path / "pyproject.toml").touch()
    test_dir = tmp_path / "core" / "tests"
    test_dir.mkdir(parents=True)
    (test_dir / "test_manager.py").touch()

    loop = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True, auto_run=True)
    # Modifying a source file (not named test_*)
    loop._files_modified_since_test.add("core/memory/manager.py")
    cmd = loop._detect_test_command()
    assert "pytest core/tests/test_manager.py" in cmd


def test_subproject_test_directory_scoping(tmp_path):
    (tmp_path / "pyproject.toml").touch()
    test_dir = tmp_path / "core" / "tests"
    test_dir.mkdir(parents=True)
    (test_dir / "test_unrelated.py").touch()

    loop = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True, auto_run=True)
    # Modifying a source file without a direct matching test_name.py
    loop._files_modified_since_test.add("core/utils/helper.py")
    cmd = loop._detect_test_command()
    assert "pytest core/tests" in cmd


def test_all_passed_uses_exit_code():
    """Quiet runners (e.g. `pytest -q`) produce no per-test markers; exit code
    must be authoritative so a clean run is not misreported as failing."""
    passed = TestRunResult(
        command="python -m pytest -q",
        return_code=0,
        duration_ms=10.0,
        results=[],
        ran=True,
    )
    assert passed.all_passed
    failed = TestRunResult(
        command="python -m pytest",
        return_code=2,
        duration_ms=10.0,
        results=[],
        ran=True,
    )
    assert not failed.all_passed
    with_fail_result = TestRunResult(
        command="python -m pytest",
        return_code=0,
        duration_ms=10.0,
        results=[TestResult(name="t", status=TestResultStatus.FAIL)],
        ran=True,
    )
    assert not with_fail_result.all_passed


def test_no_test_command_is_not_failing(tmp_path):
    """Project with nothing to verify must not trip the verification gate."""
    loop = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True, auto_run=True)
    loop._files_modified_since_test.add("src/main.py")
    result = loop._run_tests()
    assert result is not None
    assert result.command == ""
    assert not result.ran
    assert not result.all_passed
    assert loop._last_test_result is result
    assert not loop.has_failing_tests
    assert loop.get_test_failure_error() is None
    assert loop.build_feedback_context() == ""
    assert "src/main.py" in loop._files_modified_since_test


def test_timeout_records_failing_result(tmp_path):
    loop = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True, auto_run=True)
    loop._files_modified_since_test.add("src/main.py")

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="python -m pytest", timeout=60)

    with (
        patch.object(loop, "_detect_test_command", return_value="python -m pytest"),
        patch("subprocess.run", side_effect=_raise_timeout),
    ):
        result = loop._run_tests()

    assert result.ran
    assert result.return_code == -1
    assert not result.all_passed
    assert result.results[0].name == "test_timeout"
    assert loop._last_test_result is result
    assert loop.has_failing_tests
    err = loop.get_test_failure_error()
    assert err is not None
    assert err.failing_tests == ["test_timeout"]
    ctx = loop.build_feedback_context()
    assert "[POST-EDIT TEST FAILURE DETECTED]" in ctx
    assert "timed out" in ctx


def test_run_exception_records_failing_result(tmp_path):
    loop = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True, auto_run=True)
    loop._files_modified_since_test.add("src/main.py")

    with (
        patch.object(loop, "_detect_test_command", return_value="python -m pytest"),
        patch("subprocess.run", side_effect=RuntimeError("boom")),
    ):
        result = loop._run_tests()

    assert result.ran
    assert result.return_code == -1
    assert not result.all_passed
    assert result.results[0].name == "test_run_error"
    assert loop.has_failing_tests
    assert loop.get_test_failure_error().failing_tests == ["test_run_error"]
    assert "Test run crashed" in loop.build_feedback_context()


def test_has_failing_tests_respects_ran(tmp_path):
    """A stored non-run must never be reported as failing, regardless of exit code."""
    loop = ExecutionFeedbackLoop(project_root=tmp_path)
    loop._last_test_result = TestRunResult(
        command="", return_code=-1, duration_ms=0, results=[], ran=False
    )
    assert not loop.has_failing_tests
    loop._last_test_result = TestRunResult(
        command="pytest", return_code=-1, duration_ms=0, results=[], ran=True
    )
    assert loop.has_failing_tests
    loop._last_test_result = TestRunResult(
        command="pytest", return_code=0, duration_ms=0, results=[], ran=True
    )
    assert not loop.has_failing_tests


def test_verify_pending_changes_nothing_pending(tmp_path):
    """No dirty files → nothing to verify → passes even if a prior run failed."""
    loop = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True)
    loop._last_test_result = TestRunResult(
        command="pytest", return_code=1, duration_ms=0, results=[], ran=True
    )
    assert loop.verify_pending_changes() is True


def test_verify_pending_changes_runs_fresh_tests(tmp_path):
    """Dirty files trigger a fresh run; a failing fresh run reports False and
    keeps the dirty set as an unverified-changes signal."""
    loop = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True)
    loop._files_modified_since_test.add("src/main.py")
    mock_run = MagicMock()
    mock_run.returncode = 1
    mock_run.stdout = "Traceback: boom"
    mock_run.stderr = ""
    with (
        patch.object(loop, "_detect_test_command", return_value="python -m pytest"),
        patch("subprocess.run", return_value=mock_run),
    ):
        assert loop.verify_pending_changes() is False
    assert loop.has_failing_tests
    assert "src/main.py" in loop._files_modified_since_test


def test_verify_pending_changes_nothing_to_run_passes(tmp_path):
    """A project with nothing runnable to verify must not block the gate."""
    loop = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True)
    loop._files_modified_since_test.add("src/main.py")
    assert loop.verify_pending_changes() is True
    assert "src/main.py" in loop._files_modified_since_test


def test_failing_run_keeps_dirty_set(tmp_path):
    loop = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True)
    loop._files_modified_since_test.add("src/main.py")
    mock_run = MagicMock()
    mock_run.returncode = 1
    mock_run.stdout = "Traceback: boom"
    mock_run.stderr = ""
    with (
        patch.object(loop, "_detect_test_command", return_value="python -m pytest"),
        patch("subprocess.run", return_value=mock_run),
    ):
        loop._run_tests()
    assert "src/main.py" in loop._files_modified_since_test


def test_passing_run_clears_dirty_set(tmp_path):
    loop = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True)
    loop._files_modified_since_test.add("src/main.py")
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = "1 passed"
    mock_run.stderr = ""
    with (
        patch.object(loop, "_detect_test_command", return_value="python -m pytest"),
        patch("subprocess.run", return_value=mock_run),
    ):
        loop._run_tests()
    assert loop._files_modified_since_test == set()
    assert not loop.has_failing_tests


def test_feedback_loop_js_syntax_error_detection(tmp_path):
    loop = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True)
    js_file = tmp_path / "broken.js"
    js_file.write_text("function broken() { return }", encoding="utf-8")
    loop._files_modified_since_test.add(str(js_file))

    mock_run = MagicMock()
    mock_run.returncode = 1
    mock_run.stderr = "SyntaxError: Unexpected token"
    mock_run.stdout = ""

    with (
        patch.object(loop, "_detect_test_command", return_value=""),
        patch("subprocess.run", return_value=mock_run),
    ):
        res = loop._run_tests()
        assert res.ran
        assert not res.all_passed
        assert "SyntaxError" in res.stderr

