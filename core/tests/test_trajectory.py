"""
Tests for TrajectoryLogger.
"""

import json
import tempfile
from pathlib import Path
from core.execution.trajectory import TrajectoryLogger, TrajectoryStep


def test_trajectory_logger_record_step():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = TrajectoryLogger(project_root=tmpdir, session_id="test_session")
        step = logger.record_step(
            phase="code",
            prompt="Fix failing test",
            tool_calls=[{"tool_name": "EDIT_FILE", "path": "main.py"}],
            tool_results=[{"success": True, "output": "Edited main.py"}],
            test_status="PASS",
            duration_ms=150.0,
            tokens_used=120,
        )

        assert step.step_index == 1
        assert step.phase == "code"

        traj_file = Path(tmpdir) / ".torchlight" / "trajectories" / "test_session.jsonl"
        assert traj_file.exists()

        lines = traj_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1

        data = json.loads(lines[0])
        assert data["step_index"] == 1
        assert data["phase"] == "code"
        assert data["test_status"] == "PASS"
        assert len(data["tool_calls"]) == 1
