"""
Unit tests for ExecutionFeedbackLoop test lifecycle event callbacks and metadata.
"""

from pathlib import Path
from unittest.mock import MagicMock

from core.execution.feedback_loop import ExecutionFeedbackLoop, TestResultStatus, TestRunResult


def test_feedback_loop_emits_test_events(tmp_path):
    """
    Verifies that ExecutionFeedbackLoop fires 'test_started' and 'test_completed' events
    with rich metadata.
    """
    fb = ExecutionFeedbackLoop(project_root=tmp_path)

    events_received = []

    def event_callback(event_type: str, data: dict):
        events_received.append((event_type, data))

    fb.set_event_callback(event_callback)

    # 1. Modify a python file
    py_file = tmp_path / "test_sample.py"
    py_file.write_text("def test_ok(): assert True\n", encoding="utf-8")
    fb._files_modified_since_test.add("test_sample.py")

    # 2. Run tests
    res = fb._run_tests_internal()

    # 3. Verify events
    event_types = [e[0] for e in events_received]
    assert "test_started" in event_types

    # Find completed event if ran
    completed_events = [e for e in events_received if e[0] == "test_completed"]
    if res.ran:
        assert len(completed_events) > 0
        comp_data = completed_events[0][1]
        assert "command" in comp_data
        assert "duration_ms" in comp_data
        assert "passed" in comp_data
        assert "failed" in comp_data


def test_test_verification_card_rendering():
    """
    Verifies TestVerificationCard composes properly for passed and failed test data.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    from rlm_optimized.tui_widgets.tool_card import TestVerificationCard

    pass_data = {
        "command": "pytest core/tests/",
        "passed": 18,
        "failed": 0,
        "duration_ms": 420.0,
        "all_passed": True,
        "stdout": "18 passed in 0.42s",
        "stderr": "",
    }
    card_pass = TestVerificationCard(pass_data)
    assert "test-passed" in card_pass.classes

    fail_data = {
        "command": "pytest core/tests/",
        "passed": 10,
        "failed": 2,
        "duration_ms": 550.0,
        "all_passed": False,
        "stdout": "",
        "stderr": "FAILED test_foo - AssertionError",
    }
    card_fail = TestVerificationCard(fail_data)
    assert "test-failed" in card_fail.classes
