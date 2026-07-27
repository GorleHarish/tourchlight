"""
Unit tests for Inter-Task Context Pipeline, Dependencies, and File Collision Guard in AutonomousHarness.
"""

from pathlib import Path
import tempfile

from core.memory.manager import TieredMemory, MemoryConfig
from core.execution.feedback_loop import ExecutionFeedbackLoop, TestRunResult, TestResult, TestResultStatus
from core.execution.autonomous_harness import (
    AutonomousHarness, TaskStatus, TaskSpec, HarnessConfig
)


def create_mock_feedback_loop(tmp_path: Path, all_passed: bool = True) -> ExecutionFeedbackLoop:
    fb = ExecutionFeedbackLoop(project_root=tmp_path, enabled=True)
    def mock_run():
        status = TestResultStatus.PASS if all_passed else TestResultStatus.FAIL
        res = TestResult(name="test_sample", status=status)
        return TestRunResult(command="pytest", return_code=0 if all_passed else 1, duration_ms=10.0, results=[res])
    fb._run_tests = mock_run
    return fb


def test_task_dependencies_and_execution_ordering():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        memory = TieredMemory(config=MemoryConfig.auto_tune(max_tokens=2000))
        fb = create_mock_feedback_loop(tmp_path, all_passed=True)
        harness = AutonomousHarness(project_root=tmp_path, memory=memory, feedback_loop=fb)

        tasks = [
            {"id": "t1", "description": "Base setup", "target_files": ["base.py"]},
            {"id": "t2", "description": "Feature depending on t1", "target_files": ["feat.py"], "depends_on": ["t1"]},
        ]
        harness.initialize_goal(goal_id="g_dep", title="Dependency Goal", description="Test task dependencies", tasks=tasks)

        # Before t1 is verified, t2 should not be runnable
        runnable = harness._get_runnable_pending_tasks()
        assert len(runnable) == 1
        assert runnable[0].id == "t1"

        # Execute t1 micro-epoch
        success1 = harness.run_micro_epoch(runnable[0])
        assert success1 is True
        assert harness.goal_spec.tasks[0].status == TaskStatus.VERIFIED

        # After t1 is verified, t2 should now be runnable
        runnable_after = harness._get_runnable_pending_tasks()
        assert len(runnable_after) == 1
        assert runnable_after[0].id == "t2"


def test_inter_task_output_summary_injection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        memory = TieredMemory(config=MemoryConfig.auto_tune(max_tokens=2000))
        fb = create_mock_feedback_loop(tmp_path, all_passed=True)
        harness = AutonomousHarness(project_root=tmp_path, memory=memory, feedback_loop=fb)

        tasks = [
            {"id": "t1", "description": "Create database schema", "target_files": ["db.py"]},
            {"id": "t2", "description": "Create API routes", "target_files": ["api.py"], "depends_on": ["t1"]},
        ]
        harness.initialize_goal(goal_id="g_pipe", title="Pipeline Goal", description="Test context pipeline", tasks=tasks)

        # Verify t1 first
        task1 = harness.goal_spec.tasks[0]
        harness.run_micro_epoch(task1)
        assert task1.status == TaskStatus.VERIFIED
        assert task1.outputs_summary is not None

        # Run t2 and verify that t1's outputs_summary is injected into memory context
        task2 = harness.goal_spec.tasks[1]
        harness.run_micro_epoch(task2)
        
        # User message in memory should contain prior task summary context
        user_msg = memory.messages[1].content
        assert "Prior Completed Sub-Tasks Context:" in user_msg
        assert "t1 (Direct Dependency): Create database schema" in user_msg


def test_target_file_collision_detection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        memory = TieredMemory(config=MemoryConfig.auto_tune(max_tokens=2000))
        harness = AutonomousHarness(project_root=tmp_path, memory=memory)

        tasks = [
            {"id": "t1", "description": "Edit manager", "target_files": ["core/manager.py", "core/models.py"]},
            {"id": "t2", "description": "Refactor manager", "target_files": ["core/manager.py", "core/utils.py"]},
        ]
        harness.initialize_goal(goal_id="g_col", title="Collision Goal", description="Test collision detection", tasks=tasks)

        # Set t1 as IN_PROGRESS
        harness.goal_spec.tasks[0].status = TaskStatus.IN_PROGRESS

        # Test collision detection for t2
        collisions = harness._validate_file_collisions(harness.goal_spec.tasks[1])
        assert collisions == ["core/manager.py"]
