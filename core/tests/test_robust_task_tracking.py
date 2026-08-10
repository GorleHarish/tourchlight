"""
Tests for robust task and status tracking in LLM context and TUI.
"""

import os
import tempfile
from core.tools.task_helpers import (
    validate_task_transition,
    _status_to_box,
    _status_badge,
    get_compact_task_matrix,
    sync_workspace_tasks,
    mark_task_status,
)
from core.memory.manager import TieredMemory, MemoryConfig
from core.memory.budget import ContextBudget


def test_validate_task_transition():
    assert validate_task_transition("pending", "in_progress") is True
    assert validate_task_transition("in_progress", "verifying") is True
    assert validate_task_transition("verifying", "completed") is True
    assert validate_task_transition("in_progress", "failed") is True
    assert validate_task_transition("completed", "blocked") is False


def test_status_badges_and_boxes():
    assert _status_to_box("completed") == "x"
    assert _status_to_box("in_progress") == "/"
    assert _status_to_box("verifying") == "v"
    assert _status_to_box("blocked") == "~"
    assert _status_to_box("failed") == "!"
    assert _status_to_box("skipped") == "-"

    assert "COMPLETED" in _status_badge("completed")
    assert "IN_PROGRESS" in _status_badge("in_progress")
    assert "BLOCKED" in _status_badge("blocked")
    assert "FAILED" in _status_badge("failed")


def test_compact_task_matrix_adaptive_rendering():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Test Goal\n"
                "- [x] Task 1: Setup project\n"
                "- [/] Task 2: Build auth module\n"
                "- [~] Task 3: Add integration tests\n"
                "- [ ] Task 4: Write documentation\n"
            )

        sync_workspace_tasks(tmpdir)

        # Roomy context: multi-line rich task matrix
        roomy_budget = ContextBudget(max_tokens=12288, used_tokens=1000, base_pinned_tokens=600)
        lines = get_compact_task_matrix(tmpdir, budget=roomy_budget)
        assert len(lines) > 1
        assert "Task Matrix:" in lines[0]
        assert "1/4" in lines[0] or "25%" in lines[0]

        # Tight context: single-line compact summary
        tight_budget = ContextBudget(max_tokens=4096, used_tokens=3900, base_pinned_tokens=600)
        tight_lines = get_compact_task_matrix(tmpdir, budget=tight_budget)
        assert len(tight_lines) == 1
        assert "Active:" in tight_lines[0]
        assert "Next:" in tight_lines[0]


def test_l0_scratchpad_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("- [ ] Implement AST query cache\n")

        memory = TieredMemory(MemoryConfig())
        pad = memory.format_l0_scratchpad(project_root=tmpdir)
        assert "[L0 WORKING MEMORY SCRATCHPAD]" in pad
        assert "Task Matrix:" in pad
        assert "implement ast query cache" in pad.lower()
