"""
Unit tests for AutonomousHarness module.
"""

from pathlib import Path
import json
import tempfile

from core.memory.manager import TieredMemory, MemoryConfig
from core.execution.feedback_loop import ExecutionFeedbackLoop, TestRunResult, TestResult, TestResultStatus
from core.execution.autonomous_harness import (
    AutonomousHarness, TaskStatus, TaskSpec, GoalSpec, HarnessConfig
)


def create_mock_feedback_loop(tmp_path: Path, all_passed: bool = True) -> ExecutionFeedbackLoop:
    fb = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True)
    def mock_run():
        status = TestResultStatus.PASS if all_passed else TestResultStatus.FAIL
        res = TestResult(name="test_sample", status=status)
        return TestRunResult(command="pytest", return_code=0 if all_passed else 1, duration_ms=10.0, results=[res])
    fb._run_tests = mock_run
    return fb


def test_goal_initialization_and_persistence():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        memory = TieredMemory(config=MemoryConfig.auto_tune(max_tokens=2000))
        harness = AutonomousHarness(project_root=tmp_path, memory=memory)

        tasks = [
            {"id": "t1", "description": "Add async support", "target_files": ["api.py"]},
            {"id": "t2", "description": "Add unit tests", "target_files": ["test_api.py"]},
        ]
        goal = harness.initialize_goal(goal_id="g1", title="Async Refactor", description="Convert to async", tasks=tasks)

        assert goal.goal_id == "g1"
        assert len(goal.tasks) == 2
        assert harness.goal_json_path.exists()
        assert harness.tasks_md_path.exists()

        # Check Markdown content
        md_text = harness.tasks_md_path.read_text()
        assert "# Goal: Async Refactor" in md_text
        assert "[ ] **t1**: Add async support" in md_text

        # Reload spec
        loaded_harness = AutonomousHarness(project_root=tmp_path, memory=memory)
        loaded_goal = loaded_harness.load_goal_spec()
        assert loaded_goal is not None
        assert loaded_goal.goal_id == "g1"
        assert loaded_goal.tasks[0].id == "t1"


def test_context_flushing_during_micro_epoch():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        memory = TieredMemory(config=MemoryConfig.auto_tune(max_tokens=2000))
        memory.add_user_message("Old turn 1")
        memory.add_assistant_message("Old turn 2")
        assert len(memory.messages) == 2

        fb = create_mock_feedback_loop(tmp_path, all_passed=True)
        harness = AutonomousHarness(project_root=tmp_path, memory=memory, feedback_loop=fb)

        tasks = [{"id": "t1", "description": "Quick fix"}]
        harness.initialize_goal(goal_id="g1", title="Quick Goal", description="Fix issue", tasks=tasks)

        task = harness.goal_spec.tasks[0]
        success = harness.run_micro_epoch(task)

        assert success is True
        assert task.status == TaskStatus.VERIFIED
        # Messages should contain only the system message + fresh task prompt
        assert len(memory.messages) == 2
        assert "GOAL: Quick Goal" in memory.messages[1].content


def test_task_failure_and_retry_limit():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        memory = TieredMemory(config=MemoryConfig.auto_tune(max_tokens=2000))
        fb = create_mock_feedback_loop(tmp_path, all_passed=False)
        config = HarnessConfig(max_task_attempts=2, auto_git_commit=False, revert_on_failure=False)
        harness = AutonomousHarness(project_root=tmp_path, memory=memory, feedback_loop=fb, config=config)

        tasks = [{"id": "t1", "description": "Failing task", "max_attempts": 2}]
        harness.initialize_goal(goal_id="g1", title="Failing Goal", description="Test failure", tasks=tasks)

        task = harness.goal_spec.tasks[0]

        # Attempt 1
        res1 = harness.run_micro_epoch(task)
        assert res1 is False
        assert task.attempts == 1
        assert task.status == TaskStatus.IN_PROGRESS

        # Attempt 2
        res2 = harness.run_micro_epoch(task)
        assert res2 is False
        assert task.attempts == 2
        assert task.status == TaskStatus.FAILED
        assert len(task.failure_reasons) == 2


def test_daemon_loop_completion():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        memory = TieredMemory(config=MemoryConfig.auto_tune(max_tokens=2000))
        fb = create_mock_feedback_loop(tmp_path, all_passed=True)
        config = HarnessConfig(auto_git_commit=False)
        harness = AutonomousHarness(project_root=tmp_path, memory=memory, feedback_loop=fb, config=config)

        tasks = [
            {"id": "t1", "description": "Task 1"},
            {"id": "t2", "description": "Task 2"},
        ]
        harness.initialize_goal(goal_id="g1", title="Daemon Goal", description="Test daemon", tasks=tasks)

        results = harness.run_daemon()

        assert results["total_tasks"] == 2
        assert results["verified"] == 2
        assert results["failed"] == 0
        assert results["pending"] == 0


def test_auto_git_init_and_clean_commit():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        memory = TieredMemory(config=MemoryConfig.auto_tune(max_tokens=2000))
        harness = AutonomousHarness(project_root=tmp_path, memory=memory)

        # Check git dir created automatically
        assert (tmp_path / ".git").exists()

        # Clean git commit should return True without throwing
        assert harness._git_commit("test clean commit") is True


def test_get_status_summary():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        memory = TieredMemory(config=MemoryConfig.auto_tune(max_tokens=2000))
        harness = AutonomousHarness(project_root=tmp_path, memory=memory)

        # Empty harness check
        empty_sum = harness.get_status_summary()
        assert empty_sum["goal_id"] is None
        assert empty_sum["total_tasks"] == 0

        # Initialize goal with tasks
        tasks = [
            {"id": "t1", "description": "Setup DB", "target_files": ["db.py"]},
            {"id": "t2", "description": "Add routes", "target_files": ["api.py"]},
        ]
        harness.initialize_goal(goal_id="g100", title="DB & API Goal", description="Build API", tasks=tasks)
        harness.goal_spec.tasks[0].status = TaskStatus.VERIFIED

        summary = harness.get_status_summary()
        assert summary["goal_id"] == "g100"
        assert summary["title"] == "DB & API Goal"
        assert summary["total_tasks"] == 2
        assert summary["verified"] == 1
        assert summary["pending"] == 1
        assert summary["progress_pct"] == 50.0
        assert summary["tasks"][0]["id"] == "t1"
        assert summary["tasks"][0]["status"] == "verified"


