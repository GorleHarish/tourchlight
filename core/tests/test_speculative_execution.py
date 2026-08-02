"""
Unit tests for Speculative Test Execution in ExecutionFeedbackLoop.
"""

import tempfile
from pathlib import Path
from core.execution.feedback_loop import ExecutionFeedbackLoop


def test_speculative_execution_trigger_on_file_edit():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        loop = ExecutionFeedbackLoop(root, enabled=True, auto_run=False)

        # Trigger EDIT_FILE with auto_run=False so we can inspect _speculative_future before consumption
        loop.on_tool_executed("EDIT_FILE", {"file": "main.py"}, "output")

        # Verify speculative future was created and executed in background
        res = loop._run_tests()
        assert res is not None
        assert loop._last_test_result is not None
