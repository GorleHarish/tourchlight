import os
import json
import tempfile
import pytest
from unittest.mock import MagicMock

from core.tools.task_helpers import get_workspace_pending_tasks
from core.memory.manager import TieredMemory, SessionState, MemoryConfig


def test_get_workspace_pending_tasks_md():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("# Implementation Plan\n"
                    "- [ ] Task 1: Write tests\n"
                    "- [/] Task 2: Implement logic\n"
                    "- [x] Task 3: Finished setup\n")

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
            json.dump({
                "title": "Build Module",
                "tasks": [
                    {"id": "t1", "description": "Pending Subtask", "status": "pending"},
                    {"id": "t2", "description": "Verified Subtask", "status": "verified"}
                ]
            }, f)

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
        assert "[L0 WORKING MEMORY SCRATCHPAD]" in pad
        assert "- Pending Tasks: Add food collision logic" in pad


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
        mock_client.stream_chat_with_history.return_value = ["<FINAL_ANSWER>All tasks complete.</FINAL_ANSWER>"]
        engine = RLMEngineOptimized(client=mock_client, project_root=tmpdir)

        res = await engine.solve_async("Test query")

        assert engine._final_answer_rejections == 0
        assert res.answer == "All tasks complete."
