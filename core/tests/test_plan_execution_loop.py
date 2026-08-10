import os
import json
import tempfile
import pytest
from unittest.mock import MagicMock

from core.tools.task_helpers import get_workspace_pending_tasks, get_workspace_task_status_summary
from core.memory.manager import TieredMemory, SessionState, MemoryConfig


def test_get_workspace_task_status_summary():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Implementation Plan\n"
                "- [x] Task 1: Setup project\n"
                "- [/] Task 2: Build backend\n"
                "- [ ] Task 3: Add unit tests\n"
                "- [ ] Task 4: Write documentation\n"
            )

        summary = get_workspace_task_status_summary(tmpdir)
        assert summary["total_count"] == 4
        assert summary["completed_count"] == 1
        assert summary["current_task"]["description"] == "Task 2: Build backend"
        assert summary["current_task"]["status"] == "in_progress"
        assert summary["next_task"]["description"] == "Task 3: Add unit tests"
        assert summary["next_task"]["status"] == "pending"
        assert "Task 3: Add unit tests" in summary["remaining_tasks"]
        assert "Task 4: Write documentation" in summary["remaining_tasks"]


def test_get_workspace_pending_tasks_md():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Implementation Plan\n"
                "- [ ] Task 1: Write tests\n"
                "- [/] Task 2: Implement logic\n"
                "- [x] Task 3: Finished setup\n"
            )

        pending = get_workspace_pending_tasks(tmpdir)
        assert len(pending) == 2
        assert "Task 1: Write tests" in pending
        assert "Task 2: Implement logic" in pending
        assert "Task 3: Finished setup" not in pending


def test_get_workspace_pending_tasks_goal_spec():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".torchlight"), exist_ok=True)
        gpath = os.path.join(tmpdir, ".torchlight", "goal_spec.json")
        with open(gpath, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "title": "Build Module",
                    "tasks": [
                        {
                            "id": "t1",
                            "description": "Pending Subtask",
                            "status": "pending",
                        },
                        {
                            "id": "t2",
                            "description": "Verified Subtask",
                            "status": "verified",
                        },
                    ],
                },
                f,
            )

        pending = get_workspace_pending_tasks(tmpdir)
        assert len(pending) == 1
        assert "Pending Subtask" in pending


def test_format_l0_scratchpad_includes_pending_tasks():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("- [ ] Add food collision logic\n")

        memory = TieredMemory(MemoryConfig())
        pad = memory.format_l0_scratchpad(project_root=tmpdir)
        assert "Task Matrix:" in pad
        assert "add food collision logic" in pad.lower()


@pytest.mark.anyio
async def test_verification_gate_rejects_premature_final_answer():
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("- [ ] Define unit tests for generateFood\n")

        mock_client = MagicMock()
        engine = RLMEngineOptimized(client=mock_client, project_root=tmpdir)

        responses = [
            ["<FINAL_ANSWER>All features are done!</FINAL_ANSWER>"],
            ["<FINAL_ANSWER>All done after task execution.</FINAL_ANSWER>"],
        ]
        iter_resp = iter(responses)

        def mock_stream(*args, **kwargs):
            try:
                return next(iter_resp)
            except StopIteration:
                return ["<FINAL_ANSWER>Done.</FINAL_ANSWER>"]

        mock_client.stream_chat_with_history.side_effect = mock_stream

        res = await engine.solve_async("Test query")

        assert engine._final_answer_rejections >= 1
        assert res.answer is not None
        # Verify that the first step action was recorded as rejected_final_answer
        rejected_steps = [s for s in res.steps if s.action == "rejected_final_answer"]
        assert len(rejected_steps) >= 1


@pytest.mark.anyio
async def test_verification_gate_allows_final_answer_when_all_done():
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("- [x] Task 1: Complete\n- [x] Task 2: Complete\n")

        mock_client = MagicMock()
        mock_client.stream_chat_with_history.return_value = [
            "<FINAL_ANSWER>All tasks complete.</FINAL_ANSWER>"
        ]
        engine = RLMEngineOptimized(client=mock_client, project_root=tmpdir)

        res = await engine.solve_async("Test query")

        assert engine._final_answer_rejections == 0
        assert res.answer == "All tasks complete."


def test_sync_workspace_tasks_populates_tasks_md():
    from core.tools.task_helpers import sync_workspace_tasks

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Web App Goal\n\n- [ ] Task A: Add index.html\n- [x] Task B: Setup repo\n"
            )

        res = sync_workspace_tasks(tmpdir)
        assert res["synced"] is True
        assert res["task_count"] == 2

        tasks_md = os.path.join(tmpdir, ".torchlight", "tasks.md")
        assert os.path.exists(tasks_md)
        content = open(tasks_md, "r", encoding="utf-8").read()
        assert "- [ ] Task A: Add index.html" in content
        assert "- [x] Task B: Setup repo" in content

        goal_json = os.path.join(tmpdir, ".torchlight", "goal_spec.json")
        assert os.path.exists(goal_json)
        gdata = json.load(open(goal_json, "r", encoding="utf-8"))
        assert len(gdata["tasks"]) == 2


def test_mark_task_status_preserves_markdown():
    from core.tools.task_helpers import mark_task_status

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Implementation Plan\n\n## Tasks\n- [ ] Task 1: Create index.html\n- [ ] Task 2: Create game.js\n"
            )

        res = mark_task_status(tmpdir, "Task 1: Create index.html", status="completed")
        assert res is True

        content = open(plan_path, "r", encoding="utf-8").read()
        assert "# Implementation Plan" in content
        assert "## Tasks" in content
        assert "- [x] Task 1: Create index.html" in content
        assert "- [ ] Task 2: Create game.js" in content


def test_auto_mark_task_completed_by_file():
    from core.tools.task_helpers import auto_mark_task_completed_by_file

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Implementation Plan\n\n- [ ] Create index.html with game canvas\n- [ ] Create game.js script\n"
            )

        # A real (non-stub) file must exist AND verification must pass to complete.
        with open(os.path.join(tmpdir, "index.html"), "w") as f:
            f.write("<canvas id='game'></canvas><script src='game.js'></script>")

        res = auto_mark_task_completed_by_file(tmpdir, "index.html", verified=True)
        assert res is True

        content = open(plan_path, "r", encoding="utf-8").read()
        assert "- [x] Create index.html with game canvas" in content
        assert "- [ ] Create game.js script" in content


def test_auto_mark_pending_task_becomes_in_progress_without_verification():
    from core.tools.task_helpers import auto_mark_task_completed_by_file

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Implementation Plan\n\n- [ ] Create index.html with game canvas\n"
            )

        # File exists but not verified -> in_progress, NOT completed.
        with open(os.path.join(tmpdir, "index.html"), "w") as f:
            f.write("<html></html>")

        res = auto_mark_task_completed_by_file(tmpdir, "index.html", verified=False)
        assert res is True
        content = open(plan_path, "r", encoding="utf-8").read()
        assert "- [/] Create index.html with game canvas" in content


def test_auto_mark_does_not_complete_stub_or_missing_file():
    from core.tools.task_helpers import auto_mark_task_completed_by_file

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Implementation Plan\n\n- [ ] Create index.html with game canvas\n- [ ] Create utils.py helpers\n"
            )

        # Stub file (placeholder marker) must NOT be auto-completed even if verified.
        with open(os.path.join(tmpdir, "index.html"), "w") as f:
            f.write("<!-- TODO: placeholder page -->")

        res = auto_mark_task_completed_by_file(tmpdir, "index.html", verified=True)
        assert res is True
        content = open(plan_path, "r", encoding="utf-8").read()
        assert "- [/] Create index.html with game canvas" in content

        # Missing file entirely -> in_progress at best (work has started).
        res2 = auto_mark_task_completed_by_file(tmpdir, "utils.py", verified=True)
        assert res2 is True
        content2 = open(plan_path, "r", encoding="utf-8").read()
        assert "- [/] Create utils.py helpers" in content2


def test_update_task_graph_syncs_plan():
    from core.tools.implementations import tool_update_task_graph_impl
    from core.tools.task_helpers import sync_workspace_tasks

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Implementation Plan\n\n- [ ] Task 1: Write initial tests\n- [ ] Task 2: Build game logic\n"
            )

        sync_workspace_tasks(tmpdir)

        # Call UPDATE_TASK_GRAPH to update status of Task 1
        res = tool_update_task_graph_impl(
            {
                "action": "update_status",
                "task_id": "Task 1: Write initial tests",
                "status": "completed",
            },
            project_root=tmpdir,
        )
        assert "status updated" in res

        content = open(plan_path, "r", encoding="utf-8").read()
        assert "- [x] Task 1: Write initial tests" in content
        assert "- [ ] Task 2: Build game logic" in content


def test_auto_mark_multi_file_task_in_progress():
    from core.tools.task_helpers import auto_mark_task_completed_by_file

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("# Implementation Plan\n\n- [ ] Create index.html and game.js\n")

        # Step 1: Write index.html only -> should set status to [/] (in_progress)
        with open(os.path.join(tmpdir, "index.html"), "w") as f:
            f.write("<html></html>")

        res1 = auto_mark_task_completed_by_file(tmpdir, "index.html")
        assert res1 is True
        content1 = open(plan_path, "r", encoding="utf-8").read()
        assert "- [/] Create index.html and game.js" in content1

        # Step 2: Write game.js + verification -> all files exist -> [x] (completed)
        with open(os.path.join(tmpdir, "game.js"), "w") as f:
            f.write("console.log('ready');")

        res2 = auto_mark_task_completed_by_file(tmpdir, "game.js", verified=True)
        assert res2 is True
        content2 = open(plan_path, "r", encoding="utf-8").read()
        assert "- [x] Create index.html and game.js" in content2


def test_parse_and_auto_mark_plain_numbered_list_plan():
    from core.tools.task_helpers import (
        parse_all_tasks_from_markdown,
        auto_mark_task_completed_by_file,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Implementation Plan: HTML Snake Game\n\n"
                "## 10 Core Important Functions\n"
                "1. Game Initialization (`initGame`): Sets up canvas\n\n"
                "## Execution Steps\n"
                "1. Create `index.html` with canvas element.\n"
                "2. Create `style.css` for basic layout.\n"
                "3. Implement `game.js`.\n"
            )

        # Verify fallback parser extracts non-checkbox items
        tasks = parse_all_tasks_from_markdown(plan_path)
        assert len(tasks) >= 3
        descs = [t["description"] for t in tasks]
        assert any("index.html" in d for d in descs)

        # Auto-mark index.html creation (file exists + verified)
        with open(os.path.join(tmpdir, "index.html"), "w") as f:
            f.write("<canvas id='game'></canvas>")

        res = auto_mark_task_completed_by_file(tmpdir, "index.html", verified=True)
        assert res is True

        content = open(plan_path, "r", encoding="utf-8").read()
        assert "1. [x] Create `index.html` with canvas element." in content
        # Ensure style.css and game.js are NOT marked completed prematurely
        assert "2. Create `style.css` for basic layout." in content
        assert "3. Implement `game.js`." in content


def test_auto_mark_does_not_overmark_unrelated_tasks():
    from core.tools.task_helpers import (
        parse_all_tasks_from_markdown,
        auto_mark_task_completed_by_file,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Implementation Plan: HTML Snake Game\n\n"
                "## 10 Core Important Functions\n"
                "1. **Game Initialization (`initGame`):** Sets up canvas.\n"
                "2. **Snake Object Management:** Defines data structure.\n"
                "3. **Drawing Function (`drawGame`):** Renders canvas.\n\n"
                "## Execution Steps\n"
                "1. Create `index.html` with canvas element.\n"
                "2. Create `style.css` for basic layout.\n"
                "3. Implement JavaScript logic in `game.js`.\n"
            )

        # 1. Verify execution_header_regex correctly targets Execution Steps (3 tasks) rather than doc lists
        tasks = parse_all_tasks_from_markdown(plan_path)
        assert len(tasks) == 3
        assert "Create `index.html` with canvas element." in [
            t["description"] for t in tasks
        ]

        # 2. Writing style.css must ONLY mark style.css step as completed
        with open(os.path.join(tmpdir, "style.css"), "w") as f:
            f.write("body { background: black; }")

        res = auto_mark_task_completed_by_file(tmpdir, "style.css", verified=True)
        assert res is True

        content = open(plan_path, "r", encoding="utf-8").read()
        assert "2. [x] Create `style.css` for basic layout." in content
        assert "1. Create `index.html` with canvas element." in content
        assert "3. Implement JavaScript logic in `game.js`." in content


def test_skipped_tasks_not_reported_as_pending():
    from core.tools.task_helpers import get_workspace_pending_tasks

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Implementation Plan\n"
                "- [ ] Task 1: Do something\n"
                "- [-] Task 2: Skipped work\n"
                "- [x] Task 3: Finished\n"
            )

        pending = get_workspace_pending_tasks(tmpdir)
        assert len(pending) == 1
        assert "Task 1: Do something" in pending
        assert "Task 2: Skipped work" not in pending


def test_goal_spec_has_precedence_over_plan_for_pending():
    from core.tools.task_helpers import get_workspace_pending_tasks

    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".torchlight"), exist_ok=True)
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("# Plan\n- [ ] PlanOnlyTask\n")

        gpath = os.path.join(tmpdir, ".torchlight", "goal_spec.json")
        with open(gpath, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "title": "Goal",
                    "tasks": [
                        {
                            "id": "g1",
                            "description": "GoalCanonicalTask",
                            "status": "pending",
                        },
                        {
                            "id": "g2",
                            "description": "GoalDoneTask",
                            "status": "verified",
                        },
                    ],
                },
                f,
            )

        pending = get_workspace_pending_tasks(tmpdir)
        assert "GoalCanonicalTask" in pending
        assert "GoalDoneTask" not in pending
        assert "PlanOnlyTask" not in pending


def test_sync_preserves_stable_ids_and_fields_across_reorder():
    from core.tools.task_helpers import sync_workspace_tasks

    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".torchlight"), exist_ok=True)
        gpath = os.path.join(tmpdir, ".torchlight", "goal_spec.json")
        with open(gpath, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "title": "Goal",
                    "tasks": [
                        {
                            "id": "task_aaaa1111",
                            "description": "Task B",
                            "status": "pending",
                            "target_files": ["b.py"],
                            "depends_on": [],
                            "outputs_summary": "sum",
                            "attempts": 2,
                            "max_attempts": 3,
                            "failure_reasons": [],
                            "completed_at": None,
                        },
                        {
                            "id": "task_bbbb2222",
                            "description": "Task A",
                            "status": "in_progress",
                            "target_files": ["a.py"],
                            "depends_on": [],
                            "outputs_summary": None,
                            "attempts": 1,
                            "max_attempts": 3,
                            "failure_reasons": [],
                            "completed_at": None,
                        },
                    ],
                },
                f,
            )

        # Plan lists tasks in REVERSE order + one brand new task
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("# Plan\n- [ ] Task A\n- [ ] Task B\n- [ ] Task C new\n")

        sync_workspace_tasks(tmpdir)

        gdata = json.load(open(gpath, "r", encoding="utf-8"))
        by_desc = {t["description"]: t for t in gdata["tasks"]}
        # Stable ids preserved, never regenerated by index
        assert by_desc["Task A"]["id"] == "task_bbbb2222"
        assert by_desc["Task B"]["id"] == "task_aaaa1111"
        # Preserved rich fields
        assert by_desc["Task B"]["attempts"] == 2
        assert by_desc["Task B"]["target_files"] == ["b.py"]
        assert by_desc["Task A"]["status"] == "in_progress"
        # New task got a fresh stable id (not a reindexed task_03)
        assert by_desc["Task C new"]["id"] not in ("task_01", "task_02", "task_03")


def test_add_subtask_survives_sync_and_lands_in_plan():
    from core.tools.implementations import tool_update_task_graph_impl
    from core.tools.task_helpers import sync_workspace_tasks

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Implementation Plan\n\n## Execution Steps\n- [ ] Task 1: Write tests\n"
            )

        sync_workspace_tasks(tmpdir)

        res = tool_update_task_graph_impl(
            {"action": "add_subtask", "description": "Task 2: Build game logic"},
            project_root=tmpdir,
        )
        assert "added sub-task" in res

        gpath = os.path.join(tmpdir, ".torchlight", "goal_spec.json")
        gdata = json.load(open(gpath, "r", encoding="utf-8"))
        descs = [t["description"] for t in gdata["tasks"]]
        assert "Task 2: Build game logic" in descs

        # A subsequent sync must NOT drop the added subtask (merge, never rebuild)
        sync_workspace_tasks(tmpdir)
        gdata2 = json.load(open(gpath, "r", encoding="utf-8"))
        assert len(gdata2["tasks"]) == 2
        assert "Task 2: Build game logic" in [t["description"] for t in gdata2["tasks"]]

        # And it landed in implementation_plan.md as a checkbox item
        plan_content = open(plan_path, "r", encoding="utf-8").read()
        assert "- [ ] Task 2: Build game logic" in plan_content


def test_insert_task_into_plan_section():
    from core.tools.task_helpers import insert_task_into_plan

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Implementation Plan\n\n## Execution Steps\n- [ ] Existing task\n"
            )

        assert insert_task_into_plan(tmpdir, "New subtask", status="pending") is True
        content = open(plan_path, "r", encoding="utf-8").read()
        assert "- [ ] New subtask" in content
        assert "# Implementation Plan" in content


def test_auto_mark_matches_target_files_exact_basename():
    from core.tools.task_helpers import auto_mark_task_completed_by_file

    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".torchlight"), exist_ok=True)
        gpath = os.path.join(tmpdir, ".torchlight", "goal_spec.json")
        with open(gpath, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "title": "Goal",
                    "tasks": [
                        {
                            "id": "task_cc",
                            "description": "Implement auth",
                            "target_files": ["src/auth.py"],
                            "status": "pending",
                            "depends_on": [],
                            "outputs_summary": None,
                            "attempts": 0,
                            "max_attempts": 3,
                            "failure_reasons": [],
                            "completed_at": None,
                        },
                    ],
                },
                f,
            )
        os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
        with open(os.path.join(tmpdir, "src", "auth.py"), "w") as f:
            f.write("def login():\n    pass\n")

        res = auto_mark_task_completed_by_file(tmpdir, "src/auth.py", verified=True)
        assert res is True

        gdata = json.load(open(gpath, "r", encoding="utf-8"))
        assert gdata["tasks"][0]["status"] == "verified"


def test_auto_mark_no_false_positive_substring():
    from core.tools.task_helpers import auto_mark_task_completed_by_file

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Plan\n"
                "- [ ] Add auth to main.py\n"
                "- [ ] Document auth flow in README-style notes\n"
            )
        with open(os.path.join(tmpdir, "main.py"), "w") as f:
            f.write("print('auth wired')\n")

        # "main.py" is a whole-word token in only ONE task; README note task is untouched.
        res = auto_mark_task_completed_by_file(tmpdir, "main.py", verified=True)
        assert res is True
        content = open(plan_path, "r", encoding="utf-8").read()
        assert "- [x] Add auth to main.py" in content
        assert "- [ ] Document auth flow in README-style notes" in content
