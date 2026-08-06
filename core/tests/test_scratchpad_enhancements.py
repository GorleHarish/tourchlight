"""
Unit tests for Torchlight Scratchpad and Task Harness Enhancements.
"""

import json
from pathlib import Path

from core.memory.manager import TieredMemory, MemoryConfig
from core.memory.persistence import ProjectMemory
from core.tools.registry import get_tool_registry
from core.execution.autonomous_harness import AutonomousHarness, TaskStatus


def test_l0_scratchpad_includes_tried_and_failed():
    memory = TieredMemory(MemoryConfig(max_tokens=4096))
    memory.state.current_task = "Implement auth middleware"
    memory.state.tried_and_failed.append("Failed JWT regex parsing in auth.py")

    pad = memory.format_l0_scratchpad()
    assert "- Active Goal: Implement auth middleware" in pad
    assert "- Tried & Failed: Failed JWT regex parsing in auth.py" in pad


def test_tiered_memory_record_memory(tmp_path):
    pm = ProjectMemory(Path(tmp_path))
    memory = TieredMemory(MemoryConfig(max_tokens=4096), project_memory=pm)
    memory.record_memory("Use bcrypt for password hashing", category="decision")
    memory.record_memory("Attempted MD5 hash (insecure)", category="tried_failed")

    assert "Use bcrypt for password hashing" in memory.state.decisions
    assert "Attempted MD5 hash (insecure)" in memory.state.tried_and_failed

    pad = memory.format_l0_scratchpad()
    assert "- Key Decisions: Use bcrypt for password hashing" in pad
    assert "- Tried & Failed: Attempted MD5 hash (insecure)" in pad


def test_l0_scratchpad_truncates_long_and_multiline_entries():
    memory = TieredMemory(MemoryConfig(max_tokens=4096))
    memory.state.current_task = (
        "Fix flaky auth timeout in the payment service integration layer"
    )
    raw_error = (
        "AssertionError: expected 200 but got 500\n"
        "  at src/api/payments.py:42\n"
        "  RuntimeError: connection refused"
    )
    memory.state.errors_seen.append(raw_error)
    memory.state.decisions.append("x" * 500)

    pad = memory.format_l0_scratchpad()
    assert "- Active Errors: " in pad
    assert raw_error not in pad
    assert "\n  at src/api/payments.py:42" not in pad
    assert "at src/api/payments.py:42 RuntimeError" in pad
    assert "x" * 500 not in pad
    assert "..." in pad
    assert len(pad) <= memory.get_effective_budget().l0_chars


def test_l0_scratchpad_budget_drops_low_priority_sections():
    from core.memory.budget import ContextBudget

    memory = TieredMemory(MemoryConfig(max_tokens=4096))
    long = "long" * 250
    memory.state.current_task = long
    memory.state.active_file = long
    memory.state.files_modified = [long] * 5
    memory.state.failing_tests = [long] * 3
    memory.state.errors_seen = [long] * 3
    memory.state.decisions = [long] * 3
    memory.state.tried_and_failed = ["tried and failed entry"] * 3

    # Under pressure the L0 budget shrinks, so low-priority sections are dropped
    # rather than crowding the conversation.
    tight = ContextBudget(max_tokens=4096, used_tokens=3900, base_pinned_tokens=600, l0_min_tokens=150)
    pad = memory.format_l0_scratchpad(budget=tight)
    assert pad.startswith("[L0 WORKING MEMORY SCRATCHPAD]")
    assert len(pad) <= tight.l0_chars
    assert "- Tried & Failed: " not in pad


def test_save_memory_tool(tmp_path):
    registry = get_tool_registry()
    res = registry.execute(
        "SAVE_MEMORY",
        {"entry": "Use Redis for session caching", "category": "arch_decision"},
        project_root=str(tmp_path),
    )
    assert res.success is True
    assert "Saved to project memory" in res.output

    mem_file = tmp_path / ".context-memory.json"
    assert mem_file.exists()
    data = json.loads(mem_file.read_text(encoding="utf-8"))
    assert "Use Redis for session caching" in data.get("arch_decisions", [])


def test_update_task_graph_tool(tmp_path):
    registry = get_tool_registry()
    memory = TieredMemory(MemoryConfig(max_tokens=4096))

    # Initialize goal spec file
    harness = AutonomousHarness(memory=memory, project_root=str(tmp_path))
    harness.initialize_goal(
        "goal_1",
        "Test Goal",
        "Test Description",
        tasks=[
            {
                "id": "task_1",
                "description": "Initial task",
                "target_files": ["src/main.py"],
            }
        ],
    )

    # Test adding a subtask via tool call
    res = registry.execute(
        "UPDATE_TASK_GRAPH",
        {
            "action": "add_subtask",
            "task_id": "task_2",
            "description": "Second task",
            "target_files": ["src/utils.py"],
            "depends_on": ["task_1"],
        },
        project_root=str(tmp_path),
    )
    assert res.success is True
    assert "Successfully added sub-task 'task_2'" in res.output

    # Verify updated goal_spec.json
    g_path = tmp_path / ".torchlight" / "goal_spec.json"
    data = json.loads(g_path.read_text(encoding="utf-8"))
    task_ids = [t["id"] for t in data["tasks"]]
    assert "task_1" in task_ids
    assert "task_2" in task_ids

    # Test skipping a task
    res_skip = registry.execute(
        "UPDATE_TASK_GRAPH",
        {
            "action": "skip_task",
            "task_id": "task_1",
        },
        project_root=str(tmp_path),
    )
    assert res_skip.success is True
    assert "Task 'task_1' marked as SKIPPED" in res_skip.output


def test_autonomous_harness_ast_symbol_handoff(tmp_path):
    # Setup test file with python symbols
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    target_file = src_dir / "service.py"
    target_file.write_text(
        "def authenticate_user(): pass\nclass SessionManager: pass\n", encoding="utf-8"
    )

    memory = TieredMemory(MemoryConfig(max_tokens=4096))
    harness = AutonomousHarness(memory=memory, project_root=str(tmp_path))
    harness.initialize_goal(
        "goal_ast",
        "AST Goal",
        "Test AST summary generation",
        tasks=[
            {
                "id": "task_ast",
                "description": "Create service module",
                "target_files": ["src/service.py"],
            }
        ],
    )

    task = harness.goal_spec.tasks[0]
    success = harness.run_micro_epoch(task)
    assert success is True
    assert task.status == TaskStatus.VERIFIED
    assert "[Symbols: src/service.py (" in task.outputs_summary
    assert (
        "authenticate_user" in task.outputs_summary
        or "SessionManager" in task.outputs_summary
    )
