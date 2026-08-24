"""
Unit and integration tests for Torchlight Plan Mode (ExecutionMode.PLAN).
"""

import os
import json
import pytest
from unittest.mock import MagicMock, AsyncMock

from core.memory.models import ExecutionMode, SessionState
from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized


def test_session_state_execution_mode_plan():
    """Verify ExecutionMode.PLAN can be set on SessionState."""
    state = SessionState()
    state.execution_mode = ExecutionMode.PLAN
    assert state.execution_mode == ExecutionMode.PLAN
    assert state.execution_mode.value == "plan"


def test_rlm_engine_plan_mode_normalization():
    """Verify RLMEngineOptimized normalizes PLAN mode string and Enum."""
    engine = RLMEngineOptimized(project_root=".")
    engine.execution_mode = ExecutionMode.PLAN
    assert engine.execution_mode == "plan"
    assert engine.memory.state.execution_mode == ExecutionMode.PLAN

    engine.execution_mode = "plan"
    assert engine.execution_mode == "plan"
    assert engine.memory.state.execution_mode == ExecutionMode.PLAN


def test_detect_phase_plan_mode_resilience():
    """Verify _detect_phase returns 'plan' when execution_mode is 'plan' regardless of input."""
    engine = RLMEngineOptimized(project_root=".", execution_mode="plan")
    assert engine._detect_phase("Write python code for binary search") == "plan"
    assert engine._detect_phase("Fix broken bug in main.py") == "plan"
    assert engine._detect_phase("Explain database schema") == "plan"
    assert engine._detect_phase("Create index.html") == "plan"


def test_detect_phase_plan_signals_in_unified_mode():
    """Verify phase auto-detection detects 'plan' from brainstorming and planning signals."""
    engine = RLMEngineOptimized(project_root=".", execution_mode="unified")
    assert engine._detect_phase("Generate plan to refactor auth module") == "plan"
    assert engine._detect_phase("Brainstorm architecture for notification system") == "plan"
    assert engine._detect_phase("Create a plan for the new API endpoints") == "plan"
    assert engine._detect_phase("What is the implementation plan for billing?") == "plan"
    assert engine._detect_phase("Steps to implement oauth login") == "plan"
    assert engine._detect_phase("Let me plan the migration") == "plan"


@pytest.mark.anyio
async def test_solve_async_plan_mode_allows_final_answer_with_pending_tasks(tmp_path):
    """Verify that in Plan Mode, pending - [ ] tasks in implementation_plan.md do not block <FINAL_ANSWER>."""
    plan_file = tmp_path / "implementation_plan.md"
    plan_file.write_text("# Plan\n\n## Proposed Changes\n- [ ] Task 1: Pending action\n- [ ] Task 2: Another pending action\n")

    mock_client = MagicMock()
    mock_client.stream_chat_with_history.return_value = [
        "<FINAL_ANSWER>Here is the implementation plan designed for review.</FINAL_ANSWER>"
    ]

    engine = RLMEngineOptimized(client=mock_client, project_root=str(tmp_path), execution_mode="plan")
    res = await engine.solve_async("Plan the user auth feature")

    assert res.answer == "Here is the implementation plan designed for review."
    assert len(res.steps) == 1
    assert res.steps[0].action == "final_answer"


@pytest.mark.anyio
async def test_solve_async_plan_mode_missing_plan_rejects_premature_final_answer(tmp_path):
    """Verify that in Plan Mode with no implementation_plan.md, premature FINAL_ANSWER is rejected until plan is written."""
    mock_client = MagicMock()
    responses = [
        # First turn: agent prematurely outputs FINAL_ANSWER without creating plan
        ['<FINAL_ANSWER>I planned everything in my head.</FINAL_ANSWER>'],
        # Second turn: agent writes implementation_plan.md
        ['<tool_call>{"name": "WRITE_FILE", "arguments": {"path": "implementation_plan.md", "content": "# Auth Plan\\n\\n## Proposed Changes\\n- [ ] Add auth route\\n"}}</tool_call>'],
        # Third turn: final answer
        ['<FINAL_ANSWER>Implementation plan has been saved to implementation_plan.md.</FINAL_ANSWER>'],
    ]
    iter_resp = iter(responses)

    def mock_stream(*args, **kwargs):
        try:
            return next(iter_resp)
        except StopIteration:
            return ["<FINAL_ANSWER>Done.</FINAL_ANSWER>"]

    mock_client.stream_chat_with_history.side_effect = mock_stream

    engine = RLMEngineOptimized(client=mock_client, project_root=str(tmp_path), execution_mode="plan")
    res = await engine.solve_async("Plan the authentication architecture")

    assert len(res.steps) >= 2
    assert res.steps[0].action == "rejected_final_answer"
    assert "MISSING PLAN" in res.steps[0].result or "VERIFICATION GATE REJECTION" in res.steps[0].result
    assert "implementation_plan.md" in res.steps[0].result


@pytest.mark.asyncio
async def test_cli_plan_mode_session(tmp_path):
    """Verify StreamingChatSession in Plan Mode correctly handles plan creation and verification gate."""
    mock_client = MagicMock()
    mock_client.health_check = MagicMock(return_value=True)
    mock_client.list_models = MagicMock(return_value=[])
    mock_client.__aenter__ = MagicMock(return_value=mock_client)
    mock_client.__aexit__ = MagicMock(return_value=False)

    from unittest.mock import patch

    with patch("context_manager.cli.main.LMStudioClient", return_value=mock_client), \
         patch("context_manager.cli.main.ProjectMemory"), \
         patch("context_manager.cli.main.get_token_counter") as mock_tc, \
         patch("context_manager.cli.main.create_unified_registry") as mock_ur, \
         patch("context_manager.cli.main.ExecutionFeedbackLoop"), \
         patch("context_manager.cli.main.SymbolIndex"), \
         patch("context_manager.cli.main.Flashlight"):
        mock_tc.return_value.count.return_value = 100
        mock_tc.return_value._estimate.return_value = 100
        mock_ur.return_value.get_all_prompts.return_value = ""
        from context_manager.cli.main import StreamingChatSession

        session = StreamingChatSession(
            base_url="http://localhost:1234/v1",
            model="test",
            max_tokens=4096,
            stream=False,
            project_dir=str(tmp_path),
            mode="plan",
        )

        assert session.mode == "plan"
        assert session.memory.state.execution_mode == ExecutionMode.PLAN
        assert session._detect_phase("Write some code") == "plan"

        # Test verification gate with missing plan
        responses = [
            "<FINAL_ANSWER>Premature completion without saving plan.</FINAL_ANSWER>",
            "<tool_call>{\"name\": \"WRITE_FILE\", \"arguments\": {\"path\": \"implementation_plan.md\", \"content\": \"# Plan\\n- [ ] Task 1\"}}</tool_call>",
        ]
        session.client.chat = AsyncMock(side_effect=responses)

        resp = await session._generate_response("Plan caching layer")
        assert "<FINAL_ANSWER>" not in resp
        assert "WRITE_FILE" in resp
        rejections = [m for m in session.memory.messages if "VERIFICATION GATE REJECTION" in m.content]
        assert len(rejections) >= 1
        assert "Plan Mode" in rejections[0].content or "implementation_plan.md" in rejections[0].content


def test_parse_response_auto_intercepts_pseudocode_plan():
    """Verify that when a model outputs markdown plan with pseudocode $ WRITE_FILE, it is auto-intercepted."""
    engine = RLMEngineOptimized(project_root=".", execution_mode="plan")
    raw_response = '''Let's first inspect the current workspace:
```plaintext
$ LIST_DIR
```

### Implementation Plan
```markdown
# Implementation Plan

## Proposed Changes
- [ ] 1. Create HTML structure with canvas element
- [ ] 2. Include CSS and JavaScript files

## Verification Plan
- Command: open index.html
```

### Writing the Implementation Plan
```plaintext
$ WRITE_FILE("implementation_plan.md", content)
```'''
    action, thinking, summary, extra_queries, tool_name, tool_args = engine._parse_response(raw_response)
    assert action == "tool"
    assert tool_name == "WRITE_FILE"
    assert tool_args["path"] == "implementation_plan.md"
    assert "# Implementation Plan" in tool_args["content"]
    assert "- [ ] 1. Create HTML structure" in tool_args["content"]


@pytest.mark.anyio
async def test_plan_mode_guard_blocks_non_plan_files(tmp_path):
    """Verify that in Plan Mode, tool executions targeting non-plan files (e.g. index.html) are rejected by the guard."""
    mock_client = MagicMock()
    responses = [
        ['<tool_call>{"name": "WRITE_FILE", "arguments": {"path": "index.html", "content": "<h1>Hello</h1>"}}</tool_call>'],
        ['<tool_call>{"name": "WRITE_FILE", "arguments": {"path": "implementation_plan.md", "content": "# Web Plan\\n- [ ] Task 1"}}</tool_call>'],
        ['<FINAL_ANSWER>Here is the plan.</FINAL_ANSWER>'],
    ]
    iter_resp = iter(responses)
    def mock_stream(*args, **kwargs):
        try:
            return next(iter_resp)
        except StopIteration:
            return ["<FINAL_ANSWER>Done.</FINAL_ANSWER>"]
    mock_client.stream_chat_with_history.side_effect = mock_stream

    engine = RLMEngineOptimized(client=mock_client, project_root=str(tmp_path), execution_mode="plan")
    res = await engine.solve_async("Plan the website")

    assert len(res.steps) >= 2
    assert res.steps[0].action == "tool"
    assert "PLAN MODE GUARD" in res.steps[0].result
    assert not (tmp_path / "index.html").exists()
    assert (tmp_path / "implementation_plan.md").exists()
    assert "Here is the plan." in res.answer


@pytest.mark.anyio
async def test_ask_user_fn_modal_delegation(tmp_path):
    """Verify that ASK_USER delegates to engine.ask_user_fn when registered."""
    mock_client = MagicMock()
    responses = [
        ['<tool_call>{"name": "ASK_USER", "arguments": {"question": "Which theme?", "options": ["(Recommended) Dark", "Light"], "is_multi_select": false}}</tool_call>'],
        ['<FINAL_ANSWER>Applied dark theme.</FINAL_ANSWER>'],
    ]
    iter_resp = iter(responses)
    def mock_stream(*args, **kwargs):
        try:
            return next(iter_resp)
        except StopIteration:
            return ["<FINAL_ANSWER>Done.</FINAL_ANSWER>"]
    mock_client.stream_chat_with_history.side_effect = mock_stream

    engine = RLMEngineOptimized(client=mock_client, project_root=str(tmp_path), execution_mode="chat")
    async def mock_ask_user(args):
        return f"Selected: {args['options'][0]}"

    engine.ask_user_fn = mock_ask_user
    res = await engine.solve_async("Choose theme")

    assert len(res.steps) >= 1
    assert res.steps[0].action == "tool"
    assert res.steps[0].tool_name == "ASK_USER"
    assert "Selected: (Recommended) Dark" in res.steps[0].result
    assert "Applied dark theme." in res.answer


def test_parse_plan_review_questions_radio_and_checkbox():
    from core.utils.plan_utils import parse_plan_review_questions

    plan_md = """### Implementation Plan

#### Architecture & Design Decisions
- Game Controls: Standard keyboard inputs.

#### User Review Required / Open Questions
### 1. Game Controls [Single Choice / Radio]
- (•) (Recommended) Arrow Keys + WASD: Standard dual-layout controls
- ( ) Arrow Keys Only: Minimal controls
- ( ) Custom Input: Specify custom key mappings

### 2. Sound Effects [Multi-Select / Checkbox]
- [x] (Recommended) Background Music
- [ ] Sound Effects
- [ ] Custom Input: Custom sound packs

#### Proposed Changes
### [NEW] index.html
- [ ] 1. Create HTML skeleton
"""
    questions = parse_plan_review_questions(plan_md)
    assert len(questions) == 2

    q1 = questions[0]
    assert "Game Controls" in q1["question"]
    assert q1["is_multi_select"] is False
    assert len(q1["options"]) == 2
    assert "(Recommended) Arrow Keys + WASD" in q1["options"][0]
    assert "Arrow Keys Only" in q1["options"][1]

    q2 = questions[1]
    assert "Sound Effects" in q2["question"]
    assert q2["is_multi_select"] is True
    assert len(q2["options"]) == 2
    assert "(Recommended) Background Music" in q2["options"][0]
    assert "Sound Effects" in q2["options"][1]


def test_parse_plan_review_questions_three_or_n_questions():
    from core.utils.plan_utils import parse_plan_review_questions

    plan_md = """# Space Invaders Implementation Plan

## Architecture & Design Decisions
- HTML5 2D Canvas game loop.

## User Review Required / Open Questions
### 1. Game Controls [Single Choice / Radio]
- (•) (Recommended) Arrow Keys + Space: Classic layout
- ( ) WASD + Space: Alternate layout

### 2. Difficulty Modes [Single Choice / Radio]
- (•) (Recommended) Dynamic Scaling
- ( ) Fixed Speed
- ( ) Nightmare

### 3. Audio & Visuals [Multi-Select / Checkbox]
- [x] (Recommended) Retro Sound Effects
- [x] (Recommended) CRT Scanline Overlay
- [ ] Particle Explosions

## Proposed Changes
### Phase 1: Setup
#### [NEW] index.html
- [ ] 1.1 [index.html] [NEW] Canvas container
"""
    questions = parse_plan_review_questions(plan_md)
    assert len(questions) == 3

    assert "Game Controls" in questions[0]["question"]
    assert questions[0]["is_multi_select"] is False
    assert len(questions[0]["options"]) == 2

    assert "Difficulty Modes" in questions[1]["question"]
    assert questions[1]["is_multi_select"] is False
    assert len(questions[1]["options"]) == 3

    assert "Audio & Visuals" in questions[2]["question"]
    assert questions[2]["is_multi_select"] is True
    assert len(questions[2]["options"]) == 3


def test_ask_user_modal_multi_questions():
    from rlm_optimized.tui_app import AskUserModal

    questions = [
        {
            "question": "1. Controls Layout",
            "options": ["(Recommended) Arrow Keys", "WASD"],
            "is_multi_select": False,
        },
        {
            "question": "2. Difficulty",
            "options": ["(Recommended) Normal", "Hard"],
            "is_multi_select": False,
        },
        {
            "question": "3. Optional FX",
            "options": ["Sound FX", "Particles"],
            "is_multi_select": True,
        },
    ]

    modal = AskUserModal(questions=questions)
    assert len(modal.questions) == 3
    assert modal.questions[0]["question"] == "1. Controls Layout"
    assert modal.questions[1]["question"] == "2. Difficulty"
    assert modal.questions[2]["question"] == "3. Optional FX"


def test_tool_ask_user_impl_multi_questions():
    from core.tools.implementations import tool_ask_user_impl

    args = {
        "questions": [
            {
                "question": "Controls Layout",
                "options": ["(Recommended) Arrow Keys", "WASD"],
                "is_multi_select": False,
            },
            {
                "question": "Difficulty",
                "options": ["(Recommended) Normal", "Hard"],
                "is_multi_select": False,
            },
            {
                "question": "Optional FX",
                "options": ["Sound FX", "Particles"],
                "is_multi_select": True,
            },
        ]
    }
    output = tool_ask_user_impl(args, ".")
    assert "Multiple questions for review" in output
    assert "1. Controls Layout [Radio (Single Choice)]" in output
    assert "2. Difficulty [Radio (Single Choice)]" in output
    assert "3. Optional FX [Checkbox (Multi-Select)]" in output


def test_ask_user_schema_validation_with_questions_array():
    from core.tools.schemas import validate_tool_call

    args = {
        "questions": [
            {"question": "Q1", "options": ["A", "B"]},
            {"question": "Q2", "options": ["C", "D"]},
        ]
    }
    is_valid, msg, normalized = validate_tool_call("ASK_USER", args)
    assert is_valid is True
    assert "questions" in normalized
    assert len(normalized["questions"]) == 2




