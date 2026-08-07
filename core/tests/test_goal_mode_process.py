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


def test_detect_phase_goal_mode_missing_plan_forces_plan(tmp_path):
    """Verify Goal mode detects missing implementation_plan.md and forces 'plan' phase."""
    engine = RLMEngineOptimized(project_root=str(tmp_path), execution_mode="goal")
    
    # Even when user prompt asks to 'create file' or 'build feature', missing implementation_plan.md forces 'plan' phase
    phase = engine._detect_phase("create index.html file with html code")
    assert phase == "plan"
    
    # Create implementation_plan.md
    plan_file = tmp_path / "implementation_plan.md"
    plan_file.write_text("# Plan\n- [ ] Task 1")
    
    # Now that implementation_plan.md exists, phase switches to 'code' for code creation prompt
    phase_after = engine._detect_phase("create index.html file with html code")
    assert phase_after == "code"
