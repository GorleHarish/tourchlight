import pytest
from unittest.mock import MagicMock, patch
import sys



def _make_session():
    """Create a StreamingChatSession with mocked heavy dependencies."""
    mock_client = MagicMock()
    mock_client.health_check = MagicMock(return_value=True)
    mock_client.list_models = MagicMock(return_value=[])
    mock_client.__aenter__ = MagicMock(return_value=mock_client)
    mock_client.__aexit__ = MagicMock(return_value=False)

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
        return StreamingChatSession(
            base_url="http://localhost:1234/v1",
            model="test",
            max_tokens=4096,
            stream=False,
            project_dir=".",
            mode="unified",
        )


def test_detect_code_phase():
    s = _make_session()
    assert s._detect_phase("write_file some code") == "code"
    assert s._detect_phase("def foo():") == "code"
    assert s._detect_phase("```python\nprint('hi')") == "code"
    assert s._detect_phase("class MyClass:") == "code"
    assert s._detect_phase("create index.html file") == "code"
    assert s._detect_phase("modify main.py to add logging") == "code"
    assert s._detect_phase("build a new feature") == "code"
    assert s._detect_phase("implement user auth") == "code"


def test_detect_troubleshoot_phase():
    s = _make_session()
    assert s._detect_phase("error: null pointer") == "troubleshoot"
    assert s._detect_phase("the app crashed") == "troubleshoot"
    assert s._detect_phase("why does this fail?") == "troubleshoot"
    assert s._detect_phase("debug this issue") == "troubleshoot"


def test_detect_plan_phase():
    s = _make_session()
    assert s._detect_phase("<plan>step 1: setup") == "plan"
    assert s._detect_phase("let me plan the migration") == "plan"
    assert s._detect_phase("step by step approach") == "plan"
    assert s._detect_phase("i will: do this") == "plan"


def test_detect_chat_phase():
    s = _make_session()
    assert s._detect_phase("hello there") == "chat"
    assert s._detect_phase("what is fastapi?") == "chat"
    assert s._detect_phase("tell me about docker") == "chat"


def test_detect_chat_mode_resilient():
    """Verify that when session is explicitly in Chat Mode, _detect_phase returns 'chat'."""
    s = _make_session()
    s.mode = "chat"
    assert s._detect_phase("error: null pointer") == "chat"
    assert s._detect_phase("write_file some code") == "chat"
    assert s._detect_phase("<plan>step 1: setup") == "chat"
    assert s._detect_phase("create index.html file") == "chat"


def test_detect_plan_mode_resilient():
    """Verify that when session is explicitly in Plan Mode, _detect_phase returns 'plan'."""
    s = _make_session()
    s.mode = "plan"
    assert s._detect_phase("error: null pointer") == "plan"
    assert s._detect_phase("write_file some code") == "plan"
    assert s._detect_phase("def foo():") == "plan"
    assert s._detect_phase("create index.html file") == "plan"
    assert s._detect_phase("hello there") == "plan"


def test_detect_plan_signals():
    """Verify various planning and brainstorming prompts detect 'plan' phase."""
    s = _make_session()
    assert s._detect_phase("generate plan for user authentication") == "plan"
    assert s._detect_phase("brainstorm steps to implement payments") == "plan"
    assert s._detect_phase("create a plan to refactor database") == "plan"
    assert s._detect_phase("what is the implementation plan?") == "plan"




def test_detect_phase_empty_input():
    s = _make_session()
    assert s._detect_phase("") == "chat"
    assert s._detect_phase("   ") == "chat"


def test_detect_phase_mixed_signals():
    """Troubleshoot wins over code when both signals are present in unified mode."""
    s = _make_session()
    assert s._detect_phase("error: while running def foo()") == "troubleshoot"


def test_inference_params_code():
    """Code phase should yield lower temperature than chat phase."""
    from context_manager.api.lmstudio import PRESETS
    code_params = PRESETS["code"]
    chat_params = PRESETS["chat"]
    assert code_params.temperature < chat_params.temperature


def test_inference_params_chat():
    """Chat phase should have higher temperature than code phase."""
    from context_manager.api.lmstudio import PRESETS
    chat_params = PRESETS["chat"]
    code_params = PRESETS["code"]
    assert chat_params.temperature > code_params.temperature


@pytest.mark.asyncio
async def test_cli_goal_mode_verification_gate_rejects_premature_final_answer(tmp_path):
    """Verify that in Goal Mode with no implementation_plan.md, _generate_response rejects <FINAL_ANSWER>."""
    import pytest
    from unittest.mock import AsyncMock

    s = _make_session()
    s.mode = "goal"
    s.project_path = tmp_path

    responses = [
        "<FINAL_ANSWER>Premature completion without plan.</FINAL_ANSWER>",
        "<tool_call>{\"name\": \"WRITE_FILE\", \"arguments\": {\"path\": \"implementation_plan.md\", \"content\": \"# Plan\\n- [ ] Task 1\"}}</tool_call>",
    ]
    s.client.chat = AsyncMock(side_effect=responses)

    resp = await s._generate_response("Build web application")
    assert "<FINAL_ANSWER>" not in resp
    assert "WRITE_FILE" in resp
    # Check that rejection message was added to memory
    rejections = [m for m in s.memory.messages if "VERIFICATION GATE REJECTION" in m.content]
    assert len(rejections) >= 1
    assert "MISSING" in rejections[0].content or "implementation_plan.md" in rejections[0].content


@pytest.mark.asyncio
async def test_session_init_with_repeat_penalty():
    mock_client = MagicMock()
    mock_client.health_check = MagicMock(return_value=True)
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
        s = StreamingChatSession(
            base_url="http://localhost:1234/v1",
            model="test",
            max_tokens=4096,
            stream=False,
            project_dir=".",
            mode="chat",
            repeat_penalty=1.15,
        )
        assert s._params.repeat_penalty == 1.15
        assert s._params.repetition_penalty == 1.15


@pytest.mark.asyncio
async def test_handle_params_command_repetition_penalty_and_rep():
    s = _make_session()
    await s._handle_params_command("rep=1.08")
    assert s._params_locked is True
    assert s._params.repeat_penalty == 1.08
    assert s._params.repetition_penalty == 1.08

    await s._handle_params_command("repetition_penalty=1.12 temp=0.25")
    assert s._params.repeat_penalty == 1.12
    assert s._params.repetition_penalty == 1.12
    assert s._params.temperature == 0.25


def test_last_response_does_not_hijack_phase():
    """Verify that error messages or code in last_response do not switch phase if user input is general."""
    s = _make_session()
    # In unified mode, if user input is conversational, it should stay 'chat' even if last_response has errors/code
    last_err = "Traceback (most recent call last):\nError: Null pointer exception in def foo():"
    assert s._detect_phase("what do you think?", last_response=last_err) == "chat"
    assert s._detect_phase("thank you!", last_response=last_err) == "chat"


def test_detect_phase_goal_mode_via_memory_state():
    """Verify that ExecutionMode.GOAL in memory.state is respected."""
    from core.memory.models import ExecutionMode
    s = _make_session()
    s.mode = "unified"
    s.memory.state.execution_mode = ExecutionMode.GOAL
    assert s._detect_phase("what is this?") == "goal"
    assert s._detect_phase("error in code") == "goal"


def test_session_persistence_preserves_execution_mode(tmp_path):
    """Verify that SessionPersistence saves and loads execution_mode accurately."""
    from context_manager.memory.persistence import SessionPersistence
    from context_manager.memory.models import ExecutionMode
    s = _make_session()
    s.memory.state.execution_mode = ExecutionMode.PLAN
    
    p = SessionPersistence(session_dir=tmp_path)
    file_path = p.save_session(s.memory, session_name="test_mode_persist")
    
    assert file_path is not None
    s2 = _make_session()
    s2.memory.state.execution_mode = ExecutionMode.UNIFIED
    loaded = p.load_session("test_mode_persist", s2.memory)
    assert loaded is True
    assert s2.memory.state.execution_mode == ExecutionMode.PLAN


def test_cli_auto_mode_change_disabled_in_plan_code_chat():
    """Verify that in CLI StreamingChatSession, _update_params does not change phase in plan, code, or chat modes."""
    # 1. Plan Mode
    s_plan = _make_session()
    s_plan.mode = "plan"
    s_plan._current_phase = "plan"
    s_plan._update_params("error: fatal exception", "Traceback...")
    assert s_plan._current_phase == "plan"
    s_plan._update_params("write_file new.py", "")
    assert s_plan._current_phase == "plan"

    # 2. Code Mode
    s_code = _make_session()
    s_code.mode = "code"
    s_code._current_phase = "code"
    s_code._update_params("let's plan the architecture", "")
    assert s_code._current_phase == "code"
    s_code._update_params("error: crash", "Traceback...")
    assert s_code._current_phase == "code"

    # 3. Chat Mode
    s_chat = _make_session()
    s_chat.mode = "chat"
    s_chat._current_phase = "chat"
    s_chat._update_params("write_file server.py", "")
    assert s_chat._current_phase == "chat"
    s_chat._update_params("error: database connection failed", "")
    assert s_chat._current_phase == "chat"

    # 4. Unified Mode (Auto-detection active)
    s_unified = _make_session()
    s_unified.mode = "unified"
    s_unified._current_phase = "chat"
    s_unified._update_params("write_file index.html", "")
    assert s_unified._current_phase == "code"
    s_unified._update_params("error: null pointer", "")
    assert s_unified._current_phase == "troubleshoot"
    s_unified._update_params("plan the user auth", "")
    assert s_unified._current_phase == "plan"





