"""
Unit tests for Task Lifecycle and Directed Acyclic Graph (DAG) Engine.
"""

import os
import tempfile
import pytest
from core.memory.task_graph import (
    TaskDAG,
    TaskLifecycleEvent,
    TaskNode,
    TaskStatus,
    TaskStateTransitionError,
    TaskCycleError,
    TaskTransaction,
)


def test_task_status_enum_values():
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.IN_PROGRESS == "in_progress"
    assert TaskStatus.VERIFYING == "verifying"
    assert TaskStatus.COMPLETED == "completed"
    assert TaskStatus.SKIPPED == "skipped"
    assert TaskStatus.FAILED == "failed"
    assert TaskStatus.BLOCKED == "blocked"


def test_task_node_creation_and_serialization():
    node = TaskNode(
        id="task_001",
        description="Write core unit tests",
        status=TaskStatus.PENDING,
        dependencies=[],
        max_attempts=3,
    )
    d = node.to_dict()
    assert d["id"] == "task_001"
    assert d["description"] == "Write core unit tests"
    assert d["status"] == "pending"
    assert d["attempts"] == 0

    reconstructed = TaskNode.from_dict(d)
    assert reconstructed.id == node.id
    assert reconstructed.status == TaskStatus.PENDING
    assert reconstructed.max_attempts == 3


def test_valid_state_transitions():
    dag = TaskDAG()
    t1 = TaskNode(id="t1", description="Implement auth", status=TaskStatus.PENDING)
    dag.add_node(t1)

    # Valid transition: PENDING -> IN_PROGRESS
    dag.transition_task_status("t1", TaskStatus.IN_PROGRESS)
    assert dag.nodes["t1"].status == TaskStatus.IN_PROGRESS
    assert dag.nodes["t1"].attempts == 1

    # Valid transition: IN_PROGRESS -> VERIFYING
    dag.transition_task_status("t1", TaskStatus.VERIFYING)
    assert dag.nodes["t1"].status == TaskStatus.VERIFYING

    # Valid transition: VERIFYING -> COMPLETED
    dag.transition_task_status("t1", TaskStatus.COMPLETED)
    assert dag.nodes["t1"].status == TaskStatus.COMPLETED
    assert dag.nodes["t1"].completed_at is not None


def test_invalid_state_transition_raises_error():
    dag = TaskDAG()
    t1 = TaskNode(id="t1", description="Implement feature", status=TaskStatus.SKIPPED)
    dag.add_node(t1)

    # SKIPPED directly to COMPLETED is invalid (must go to PENDING or IN_PROGRESS first)
    with pytest.raises(TaskStateTransitionError):
        dag.transition_task_status("t1", TaskStatus.COMPLETED)


def test_dag_topological_sort_and_ready_tasks():
    dag = TaskDAG()
    t1 = TaskNode(id="t1", description="Design Schema", status=TaskStatus.COMPLETED)
    t2 = TaskNode(
        id="t2",
        description="Build Database Model",
        status=TaskStatus.PENDING,
        dependencies=["t1"],
    )
    t3 = TaskNode(
        id="t3",
        description="Build API Endpoint",
        status=TaskStatus.PENDING,
        dependencies=["t2"],
    )
    dag.add_node(t1)
    dag.add_node(t2)
    dag.add_node(t3)

    sorted_tasks = [t.id for t in dag.topological_sort()]
    assert sorted_tasks == ["t1", "t2", "t3"]

    ready = dag.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == "t2"  # t1 is completed, so t2 is ready


def test_cycle_detection_raises_error():
    dag = TaskDAG()
    t1 = TaskNode(id="t1", description="Task 1", dependencies=["t2"])
    t2 = TaskNode(id="t2", description="Task 2", dependencies=["t1"])

    dag.add_node(t1)
    with pytest.raises(TaskCycleError):
        dag.add_node(t2)


def test_parent_status_auto_rollup():
    dag = TaskDAG()
    parent = TaskNode(id="p1", description="Parent epic", status=TaskStatus.PENDING)
    child1 = TaskNode(
        id="c1", description="Subtask 1", parent_id="p1", status=TaskStatus.PENDING
    )
    child2 = TaskNode(
        id="c2", description="Subtask 2", parent_id="p1", status=TaskStatus.PENDING
    )

    dag.add_node(parent)
    dag.add_node(child1)
    dag.add_node(child2)

    dag.transition_task_status("c1", TaskStatus.IN_PROGRESS)
    assert dag.nodes["p1"].status == TaskStatus.IN_PROGRESS

    dag.transition_task_status("c1", TaskStatus.COMPLETED)
    assert dag.nodes["p1"].status == TaskStatus.IN_PROGRESS  # c2 still pending

    dag.transition_task_status("c2", TaskStatus.COMPLETED)
    assert dag.nodes["p1"].status == TaskStatus.COMPLETED  # Both finished!


def test_checkpoint_and_rollback():
    dag = TaskDAG()
    t1 = TaskNode(id="t1", description="Initial task", status=TaskStatus.PENDING)
    dag.add_node(t1)

    snap = dag.create_checkpoint()

    dag.transition_task_status("t1", TaskStatus.IN_PROGRESS)
    assert dag.nodes["t1"].status == TaskStatus.IN_PROGRESS

    # Rollback to snapshot
    assert dag.restore_checkpoint(snap.snapshot_id) is True
    assert dag.nodes["t1"].status == TaskStatus.PENDING


def test_render_l0_view():
    dag = TaskDAG()
    t1 = TaskNode(id="t1", description="Create Schema", status=TaskStatus.COMPLETED)
    t2 = TaskNode(
        id="t2",
        description="Implement Routes",
        status=TaskStatus.PENDING,
        dependencies=["t1"],
        output_symbols=["get_users", "post_user"],
    )
    dag.add_node(t1)
    dag.add_node(t2)

    l0_str = dag.render_l0_view()
    assert "**Goal Progress**: 1/2 tasks completed" in l0_str
    assert "Implement Routes" in l0_str
    assert "get_users" in l0_str


def test_task_transaction_atomic_file_write():
    with tempfile.TemporaryDirectory() as tmp_dir:
        with TaskTransaction(tmp_dir) as dag:
            dag.add_node(
                TaskNode(id="t1", description="Persistent Task", status=TaskStatus.PENDING)
            )

        goal_path = os.path.join(tmp_dir, ".torchlight", "goal_spec.json")
        assert os.path.exists(goal_path)

        with TaskTransaction(tmp_dir) as reloaded_dag:
            assert "t1" in reloaded_dag.nodes
            assert reloaded_dag.nodes["t1"].description == "Persistent Task"
