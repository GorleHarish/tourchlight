"""
Unit and integration tests for Torchlight Code Mode (ExecutionMode.CODE).
"""

from pathlib import Path
import json
import pytest

from core.memory.models import ExecutionMode, SessionState
from core.memory.manager import TieredMemory, MemoryConfig
from core.prompts.system import get_phase_system_prompt, CODE_PROMPT
from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
from rlm_optimized.tui_widgets.format import build_plan_overview_text, build_plan_text


def test_code_mode_enum_and_state():
    """Verify ExecutionMode.CODE is defined and can be set on SessionState."""
    state = SessionState()
    state.execution_mode = ExecutionMode.CODE
    assert state.execution_mode == ExecutionMode.CODE
    assert state.execution_mode.value == "code"


def test_engine_code_mode_setting():
    """Verify RLMEngineOptimized supports setting execution_mode to CODE."""
    engine = RLMEngineOptimized()
    engine.execution_mode = ExecutionMode.CODE
    assert engine.execution_mode == "code"
    assert engine.memory.state.execution_mode == ExecutionMode.CODE

    engine.execution_mode = "code"
    assert engine.execution_mode == "code"
    assert engine.memory.state.execution_mode == ExecutionMode.CODE


def test_code_mode_phase_detection_persistence():
    """Verify _detect_phase always returns 'code' in Code Mode."""
    engine = RLMEngineOptimized()
    engine.execution_mode = "code"

    assert engine._detect_phase("What is the plan for this?") == "code"
    assert engine._detect_phase("Why is this error happening?") == "code"
    assert engine._detect_phase("Implement phase 1 tasks in index.html") == "code"
    assert engine._detect_phase("Can you explain how this works?") == "code"


def test_code_mode_prompt_task_integration():
    """Verify Code Mode system prompt includes task execution and plan preservation directives."""
    code_prompt = get_phase_system_prompt("code")
    assert "[PHASE: SURGICAL CODING]" in code_prompt
    assert "Code Mode" in code_prompt
    assert "TASK EXECUTION RULES (IMMEDIATE ACTION ON ENTRY)" in code_prompt
    assert "JUMP STRAIGHT INTO TASKS" in code_prompt
    assert "ONE TASK AT A TIME" in code_prompt
    assert "Preserve Plan Hierarchy" in code_prompt
    assert "DO NOT rewrite the plan" in code_prompt
    assert "Mark Completed Tasks" in code_prompt
    assert "- [x]" in code_prompt


def test_code_mode_badge_in_tui_format(tmp_path):
    """Verify TUI format helpers render CODE MODE badge with task checklist."""
    plan_file = tmp_path / "implementation_plan.md"
    plan_file.write_text(
        "# Snake Game Implementation Plan\n\n"
        "## Architecture & Design Decisions\n"
        "- Vanilla JS\n\n"
        "## Proposed Changes\n"
        "### Phase 1: Setup & Foundations\n"
        "#### [NEW] index.html\n"
        "- [ ] 1.1 Create HTML skeleton\n"
        "#### [NEW] style.css\n"
        "- [ ] 1.2 Add styling\n\n"
        "### Phase 2: Core Mechanics\n"
        "#### [NEW] game.js\n"
        "- [ ] 2.1 Initialize snake\n"
    )

    overview = build_plan_overview_text(str(tmp_path), mode="code")
    assert "CODE MODE" in overview
    assert "Snake Game Implementation Plan" in overview

    plan_text = build_plan_text(str(tmp_path), mode="code")
    assert "CODE MODE" in plan_text
    assert "1.1 Create HTML skeleton" in plan_text
    assert "1.2 Add styling" in plan_text
    assert "2.1 Initialize snake" in plan_text


def test_code_mode_scratchpad_task_matrix_injection(tmp_path):
    """Verify Code Mode injects task matrix from implementation_plan.md into L0 working memory."""
    plan_file = tmp_path / "implementation_plan.md"
    plan_file.write_text(
        "# Snake Game\n\n"
        "## Proposed Changes\n"
        "### Phase 1: Foundations\n"
        "- [ ] 1.1 Create HTML skeleton\n"
        "- [ ] 1.2 Add styling\n"
    )

    memory = TieredMemory(config=MemoryConfig())
    memory.state.execution_mode = ExecutionMode.CODE

    scratchpad = memory.format_l0_scratchpad(project_root=str(tmp_path))
    assert "Active Goal" in scratchpad or "Tasks" in scratchpad or "1.1" in scratchpad


def test_code_mode_prompt_strict_tool_execution_rules():
    """Verify Code Mode prompt includes strict anti-simulation and real XML tool invocation rules."""
    code_prompt = get_phase_system_prompt("code")
    assert "[CRITICAL INVOCATION RULES — STRICT REAL TOOL EXECUTION]" in code_prompt
    assert "ONE ACTION PER TURN" in code_prompt
    assert "NEVER SIMULATE MULTI-STEP SCRIPTS" in code_prompt
    assert "NEVER USE MARKDOWN CODE BLOCKS FOR TOOL CALLS" in code_prompt
    assert "STOP GENERATING IMMEDIATELY" in code_prompt


def test_engine_parse_markdown_json_block_fallback():
    """Verify RLMEngineOptimized._parse_response gracefully handles markdown json tool calls."""
    engine = RLMEngineOptimized()
    raw_response = """Let's read the file and then proceed with editing it.

### Tool Calls:
```json
{
    "name": "READ_FILE",
    "arguments": {
        "path": "game.js",
        "start_line": 5,
        "end_line": 8
    }
}
```

### Step 2: Verify the Content
Once we have the content, we can proceed with editing the file.
"""
    action, thinking, content, extra_queries, tool_name, tool_args = engine._parse_response(raw_response)
    assert action == "tool"
    assert tool_name == "READ_FILE"
    assert tool_args["path"] == "game.js"
    assert tool_args["start_line"] == 5
    assert tool_args["end_line"] == 8


def test_assistant_messages_never_deduplicated():
    """Verify assistant conversational answers are never replaced with deduplication placeholders."""
    from core.memory.models import Message, MessageRole

    memory = TieredMemory(config=MemoryConfig())
    # Turn 1
    memory.add_user_message("proceed with next steps in implementation_plan.md")
    memory.add_assistant_message("I am inspecting the workspace and proceeding with task 1.1 in implementation_plan.md.")

    # Turn 2: similar text from assistant
    memory.add_user_message("proceed with next steps in implementation_plan.md")
    memory.add_assistant_message("I am inspecting the workspace and proceeding with task 1.1 in implementation_plan.md.")

    # Context build
    context = memory.get_context_for_llm()

    # Active memory messages must remain unmutated
    for msg in memory.messages:
        if msg.role == MessageRole.ASSISTANT:
            assert "[Deduplicated:" not in msg.content
            assert "I am inspecting the workspace" in msg.content

    # LLM context must also contain actual assistant content
    assistant_ctxs = [c["content"] for c in context if c.get("role") == "assistant"]
    for content in assistant_ctxs:
        assert "[Deduplicated:" not in content
        assert "I am inspecting the workspace" in content


def test_engine_parse_bracket_tool_calls():
    """Verify RLMEngineOptimized._parse_response parses bracket and CLI tool calls like [LIST_DIR]."""
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
    engine = RLMEngineOptimized(project_root=".")

    # 1. Bare [LIST_DIR]
    action, _, _, _, tool_name, tool_args = engine._parse_response("[LIST_DIR]")
    assert action == "tool"
    assert tool_name == "LIST_DIR"
    assert tool_args.get("path") == "."

    # 2. [READ_FILE(path="game.js")]
    action, _, _, _, tool_name, tool_args = engine._parse_response('[READ_FILE(path="game.js")]')
    assert action == "tool"
    assert tool_name == "READ_FILE"
    assert tool_args.get("path") == "game.js"

    # 3. [EDIT_FILE: {"path": "game.js", "old_text": "foo", "new_text": "bar"}]
    action, _, _, _, tool_name, tool_args = engine._parse_response('[EDIT_FILE: {"path": "game.js", "old_text": "foo", "new_text": "bar"}]')
    assert action == "tool"
    assert tool_name == "EDIT_FILE"
    assert tool_args.get("path") == "game.js"
    assert tool_args.get("new_text") == "bar"


def test_engine_parse_direct_xml_attribute_tool_calls():
    """Verify RLMEngineOptimized._parse_response parses XML self-closing and attribute tool calls."""
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
    engine = RLMEngineOptimized(project_root=".")

    # 1. Exact string from user screenshot: <EDIT_FILE path="game.js" start_line=15 end_line=25 new_text=" // updated implementation\n requestAnimationFrame(gameLoop);"/>
    raw = '<EDIT_FILE path="game.js" start_line=15 end_line=25 new_text=" // updated implementation\\n requestAnimationFrame(gameLoop);"/>'
    action, _, _, _, tool_name, tool_args = engine._parse_response(raw)
    assert action == "tool"
    assert tool_name == "EDIT_FILE"
    assert tool_args.get("path") == "game.js"
    assert tool_args.get("start_line") == 15
    assert tool_args.get("end_line") == 25
    assert "requestAnimationFrame" in tool_args.get("new_text", "")

    # 2. <READ_FILE path="game.js" start_line=1 end_line=50/>
    raw2 = '<READ_FILE path="game.js" start_line=1 end_line=50/>'
    action, _, _, _, tool_name, tool_args = engine._parse_response(raw2)
    assert action == "tool"
    assert tool_name == "READ_FILE"
    assert tool_args.get("path") == "game.js"
    assert tool_args.get("start_line") == 1
    assert tool_args.get("end_line") == 50

    # 3. <RUN_COMMAND cmd="npm test"/>
    raw3 = '<RUN_COMMAND cmd="npm test"/>'
    action, _, _, _, tool_name, tool_args = engine._parse_response(raw3)
    assert action == "tool"
    assert tool_name == "RUN_COMMAND"
    assert tool_args.get("cmd") == "npm test"


def test_single_in_progress_task_exclusivity(tmp_path):
    """Verify that marking a task in_progress maintains single-active exclusivity."""
    from core.tools.task_helpers import mark_task_in_progress, parse_all_tasks_from_markdown

    plan_file = tmp_path / "implementation_plan.md"
    plan_file.write_text("""# Plan
## Proposed Changes
- [ ] 1.1 Task One
- [ ] 1.2 Task Two
- [ ] 1.3 Task Three
""")

    # Mark 1.1 in progress
    mark_task_in_progress(str(tmp_path), "1.1")
    tasks = parse_all_tasks_from_markdown(str(plan_file))
    in_prog = [t for t in tasks if t["status"] == "in_progress"]
    assert len(in_prog) == 1
    assert "1.1" in in_prog[0]["description"]

    # Mark 1.2 in progress -> 1.1 should revert to pending, only 1.2 in progress
    mark_task_in_progress(str(tmp_path), "1.2")
    tasks = parse_all_tasks_from_markdown(str(plan_file))
    in_prog = [t for t in tasks if t["status"] == "in_progress"]
    assert len(in_prog) == 1
    assert "1.2" in in_prog[0]["description"]
    assert tasks[0]["status"] == "pending"





