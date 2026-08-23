import os
import tempfile
import pytest

from core.tools.task_helpers import (
    parse_all_tasks_from_markdown,
    mark_task_status,
    get_workspace_task_status_summary,
    _render_plan_checkboxes,
    _is_task_match,
    sync_workspace_tasks,
)
from core.prompts.system import PLAN_PROMPT, get_phase_system_prompt


def test_parse_numbered_tasks_from_markdown():
    md = """# Implementation Plan
## Proposed Changes
### [NEW] index.html
- [ ] 1. Create HTML skeleton with canvas element
- [/] 2. Add score and game-over overlay
### [NEW] game.js
- [x] 3. Implement game loop with requestAnimationFrame
- [-] 4. Optional sound effects
"""
    tasks = parse_all_tasks_from_markdown(md)
    assert len(tasks) == 4

    assert tasks[0]["description"] == "1. Create HTML skeleton with canvas element"
    assert tasks[0]["status"] == "pending"
    assert tasks[0]["task_number"] == 1

    assert tasks[1]["description"] == "2. Add score and game-over overlay"
    assert tasks[1]["status"] == "in_progress"
    assert tasks[1]["task_number"] == 2

    assert tasks[2]["description"] == "3. Implement game loop with requestAnimationFrame"
    assert tasks[2]["status"] == "completed"
    assert tasks[2]["task_number"] == 3

    assert tasks[3]["description"] == "4. Optional sound effects"
    assert tasks[3]["status"] == "skipped"
    assert tasks[3]["task_number"] == 4


def test_mark_task_status_by_number():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Implementation Plan\n\n"
                "## Proposed Changes\n"
                "- [ ] 1. Setup project configuration\n"
                "- [ ] 2. Implement core engine\n"
                "- [ ] 3. Write comprehensive tests\n"
            )

        # Initialize goal spec
        sync_workspace_tasks(tmpdir)

        # Mark task 2 completed using plain number "2"
        res = mark_task_status(tmpdir, "2", status="completed")
        assert res is True

        content = open(plan_path, "r", encoding="utf-8").read()
        assert "- [ ] 1. Setup project configuration" in content
        assert "- [x] 2. Implement core engine" in content
        assert "- [ ] 3. Write comprehensive tests" in content

        # Mark task 1 in_progress using "task 1"
        res = mark_task_status(tmpdir, "task 1", status="in_progress")
        assert res is True

        content = open(plan_path, "r", encoding="utf-8").read()
        assert "- [/] 1. Setup project configuration" in content
        assert "- [x] 2. Implement core engine" in content

        # Mark task 3 using "#3"
        res = mark_task_status(tmpdir, "#3", status="completed")
        assert res is True

        content = open(plan_path, "r", encoding="utf-8").read()
        assert "- [x] 3. Write comprehensive tests" in content


def test_status_summary_counts_verified_and_completed():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Plan\n"
                "- [x] 1. First task done\n"
                "- [/] 2. Second in progress\n"
                "- [ ] 3. Third pending\n"
            )

        sync_workspace_tasks(tmpdir)
        summary = get_workspace_task_status_summary(tmpdir)
        assert summary["total_count"] == 3
        assert summary["completed_count"] == 1
        assert summary["current_task"]["status"] == "in_progress"


def test_is_task_match_precision():
    # Number matches
    assert _is_task_match("1", "1. Create canvas") is True
    assert _is_task_match("2", "1. Create canvas") is False
    assert _is_task_match("task 1", "1. Create canvas") is True
    assert _is_task_match("#1", "1. Create canvas") is True

    # Exact description match
    assert _is_task_match("Create canvas", "Create canvas") is True
    assert _is_task_match("Create canvas", "1. Create canvas") is True

    # Internal task IDs do NOT wild-card match everything
    assert _is_task_match("task_abc123", "Some unrelated task") is False


def test_plan_prompt_contract():
    assert "MANDATORY TOOL CALL & PATH GUARD" in PLAN_PROMPT
    assert "numbered checkbox item" in PLAN_PROMPT

    prompt = get_phase_system_prompt("plan")
    assert "[PHASE: PLANNING]" in prompt


def test_phase_wise_tasks_and_hierarchical_marking():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Implementation Plan\n\n"
                "## Proposed Changes\n"
                "### Phase 1: Setup & Foundations\n"
                "- [ ] 1.1 Create HTML skeleton with canvas\n"
                "- [ ] 1.2 Setup CSS styles\n\n"
                "### Phase 2: Core Mechanics\n"
                "- [ ] 2.1 Implement snake movement\n"
                "- [ ] 2.2 Implement food spawning\n"
            )

        sync_workspace_tasks(tmpdir)

        tasks_md_p = os.path.join(tmpdir, ".torchlight", "tasks.md")
        assert os.path.exists(tasks_md_p)
        tasks_md_content = open(tasks_md_p, "r", encoding="utf-8").read()
        assert "Phase 1: Setup & Foundations" in tasks_md_content
        assert "Phase 2: Core Mechanics" in tasks_md_content

        # Mark 1.1 as completed
        res1 = mark_task_status(tmpdir, "1.1", status="completed")
        assert res1 is True

        # Mark 2.1 as in_progress using task 2.1
        res2 = mark_task_status(tmpdir, "task 2.1", status="in_progress")
        assert res2 is True

        plan_content = open(plan_path, "r", encoding="utf-8").read()
        assert "- [x] 1.1 Create HTML skeleton with canvas" in plan_content
        assert "- [ ] 1.2 Setup CSS styles" in plan_content
        assert "- [/] 2.1 Implement snake movement" in plan_content
        assert "- [ ] 2.2 Implement food spawning" in plan_content

