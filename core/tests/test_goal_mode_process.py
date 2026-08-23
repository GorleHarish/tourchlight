import os
import json
import pytest
from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized


def test_parse_response_bare_json_tool_call():
    """Verify bare JSON tool calls without <tool_call> tags are correctly parsed as tools instead of text FINAL_ANSWER."""
    engine = RLMEngineOptimized(project_root=".")
    
    # 1. Bare JSON EDIT_FILE tool call
    raw_response = '{"name": "EDIT_FILE", "arguments": {"path": "index.html", "old_text": "", "new_text": "<html></html>"}}'
    action, thinking, content, extra_queries, tool_name, tool_args = engine._parse_response(raw_response)
    
    assert action == "tool"
    assert tool_name == "EDIT_FILE"
    assert tool_args == {"path": "index.html", "old_text": "", "new_text": "<html></html>"}
    
    # 2. Bare JSON tool call inside ```json markdown block
    raw_response_fence = 'Here is the change:\n```json\n{"tool": "WRITE_FILE", "arguments": {"path": "app.py", "content": "print(1)"}}\n```'
    action2, _, _, _, tool_name2, tool_args2 = engine._parse_response(raw_response_fence)
    
    assert action2 == "tool"
    assert tool_name2 == "WRITE_FILE"
    assert tool_args2 == {"path": "app.py", "content": "print(1)"}


def test_detect_phase_goal_mode_detects_goal_phase(tmp_path):
    """Verify Goal mode detects 'goal' phase."""
    engine = RLMEngineOptimized(project_root=str(tmp_path), execution_mode="goal")
    phase = engine._detect_phase("create index.html file with html code")
    assert phase == "goal"


@pytest.mark.anyio
async def test_solve_async_goal_mode_missing_plan_rejects_premature_final_answer(tmp_path):
    """Verify Goal mode rejects premature FINAL_ANSWER on turn 1 when implementation_plan.md is missing."""
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    responses = [
        # First turn: premature FINAL_ANSWER without writing plan
        ['<FINAL_ANSWER>I will implement everything in index.html.</FINAL_ANSWER>'],
        # Second turn: agent writes implementation plan
        ['<tool_call>{"name": "WRITE_FILE", "arguments": {"path": "implementation_plan.md", "content": "# Plan\\n- [x] Task 1\\n"}}</tool_call>'],
        # Third turn: final answer after task completion
        ['<FINAL_ANSWER>Goal complete.</FINAL_ANSWER>'],
    ]
    iter_resp = iter(responses)

    def mock_stream(*args, **kwargs):
        try:
            return next(iter_resp)
        except StopIteration:
            return ["<FINAL_ANSWER>Done.</FINAL_ANSWER>"]

    mock_client.stream_chat_with_history.side_effect = mock_stream

    engine = RLMEngineOptimized(client=mock_client, project_root=str(tmp_path), execution_mode="goal")
    res = await engine.solve_async("Build index.html app")

    assert len(res.steps) >= 2
    # Step 1 should be a rejected_final_answer due to missing plan
    assert res.steps[0].action == "rejected_final_answer"
    assert "MISSING PLAN" in res.steps[0].result or "VERIFICATION GATE REJECTION" in res.steps[0].result
    assert res.steps[0].step_number == 1


@pytest.mark.anyio
async def test_solve_async_goal_mode_sets_goal_phase_initially(tmp_path):
    """Verify solve_async in Goal Mode initializes phase to 'goal'."""
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_client.stream_chat_with_history.return_value = ["<FINAL_ANSWER>Done.</FINAL_ANSWER>"]

    engine = RLMEngineOptimized(client=mock_client, project_root=str(tmp_path), execution_mode="goal")
    assert engine._detect_phase("Build web app") == "goal"

