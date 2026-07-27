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
        )


def test_detect_code_phase():
    s = _make_session()
    assert s._detect_phase("write_file some code") == "code"
    assert s._detect_phase("def foo():") == "code"
    assert s._detect_phase("```python\nprint('hi')") == "code"
    assert s._detect_phase("class MyClass:") == "code"


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


def test_detect_phase_empty_input():
    s = _make_session()
    assert s._detect_phase("") == "chat"
    assert s._detect_phase("   ") == "chat"


def test_detect_phase_mixed_signals():
    """Troubleshoot wins over code when both signals are present."""
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
