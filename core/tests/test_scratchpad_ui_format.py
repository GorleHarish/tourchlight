"""Tests for UI/UX Pro Agent Working Memory Scratchpad formatting."""

import pytest
from unittest.mock import MagicMock

from core.memory.manager import MemoryConfig, TieredMemory
from core.memory.models import MemoryNeedle, MemoryObject, SessionState
from rlm_optimized.tui_widgets.format import (
    build_agent_memory_scratchpad_text,
)


def test_scratchpad_empty_state():
    """Empty memory renders a clean, friendly idle state."""
    res = build_agent_memory_scratchpad_text(None)
    assert "WORKING MEMORY" in res
    assert "Idle / Listening" in res or "Idle / Ready" in res


def test_scratchpad_with_session_state():
    """Scratchpad formats structured SessionState into distinct, styled UI cards."""
    mem = TieredMemory(config=MemoryConfig())
    mem.state.current_task = "Build authentication login flow"
    mem.state.active_file = "src/auth/login.py"
    mem.state.current_blocker = "Missing JWT secret key"
    mem.state.next_steps = ["Implement token refresh endpoint", "Add unit tests"]
    mem.state.errors_seen = ["ValueError: Invalid token format", "KeyError: 'jwt_secret'"]
    mem.state.failing_tests = ["test_auth_token", "test_jwt_validation"]
    mem.state.files_modified = ["src/auth/login.py", "src/auth/jwt.py"]
    mem.state.files_modified_stats = {
        "src/auth/login.py": [18, 4],
        "src/auth/jwt.py": [32, 2],
    }
    mem.state.files_modified_symbols = {
        "src/auth/login.py": ["authenticate_user", "verify_password"],
    }
    mem.state.decisions = ["Use RS256 for JWT signing", "Store refresh tokens in Redis"]
    mem.state.tried_and_failed = ["Attempted HMAC-SHA256 with static secret; rejected for security"]
    mem.state.tech_stack = ["FastAPI", "Pydantic", "Pytest"]
    mem.state.needle_ledger = [MemoryNeedle(kind="preference", value="User prefers strict type validation")]

    formatted = build_agent_memory_scratchpad_text(mem)

    # Check Objective Card
    assert "ACTIVE OBJECTIVE" in formatted
    assert "Build authentication login flow" in formatted
    assert "src/auth/login.py" in formatted
    assert "Missing JWT secret key" in formatted
    assert "Implement token refresh endpoint" in formatted

    # Check Issues Card
    assert "ACTIVE ISSUES" in formatted
    assert "test_auth_token" in formatted
    assert "Invalid token format" in formatted

    # Check Modified Files Card
    assert "MODIFIED FILES" in formatted
    assert "+18" in formatted
    assert "-4" in formatted
    assert "authenticate_user" in formatted

    # Check Decisions Card
    assert "KEY DECISIONS" in formatted
    assert "RS256" in formatted

    # Check Anti-Loop Card
    assert "ANTI-LOOP LOG" in formatted
    assert "Attempted HMAC-SHA256" in formatted

    # Check Tech Stack Card
    assert "TECH STACK" in formatted
    assert "FastAPI" in formatted

    # Check Memory / Facts Card
    assert "CONTEXT & MEMORY" in formatted
    assert "strict type validation" in formatted


def test_scratchpad_parses_raw_prompt_string():
    """Scratchpad gracefully falls back to parsing raw prompt strings."""
    raw_prompt = """[L0 WORKING MEMORY SCRATCHPAD]
- Active Errors: FileNotFoundError: config.yaml missing
- Failing Tests: test_config_loader, test_env_override
- Active Goal: Refactor configuration loader
- Active File: src/config.py
- Key Decisions: Use Pydantic Settings; Fallback to .env.local
- Modified Files: src/config.py (+15, -3), tests/test_config.py
- Tech Stack: Python, Pytest, Pydantic
- Tried & Failed: Tried yaml.safe_load without schema validation
- Facts & Past Context: Project uses Python 3.9+"""

    formatted = build_agent_memory_scratchpad_text(raw_text=raw_prompt)

    assert "ACTIVE OBJECTIVE" in formatted
    assert "Refactor configuration loader" in formatted
    assert "src/config.py" in formatted
    assert "ACTIVE ISSUES" in formatted
    assert "FileNotFoundError" in formatted
    assert "test_config_loader" in formatted
    assert "KEY DECISIONS" in formatted
    assert "Pydantic Settings" in formatted
    assert "MODIFIED FILES" in formatted
    assert "ANTI-LOOP LOG" in formatted
    assert "yaml.safe_load" in formatted
    assert "TECH STACK" in formatted
    assert "Python" in formatted
    assert "CONTEXT & MEMORY" in formatted
    assert "Python 3.9+" in formatted


def test_scratchpad_escapes_rich_special_characters():
    """Verify that square brackets and special markup characters in code/errors are escaped."""
    mem = TieredMemory(config=MemoryConfig())
    mem.state.current_task = "Fix List[Dict[str, Any]] type annotation"
    mem.state.errors_seen = ["IndexError: list index [0] out of range"]
    mem.state.files_modified = ["src/models[v2].py"]

    formatted = build_agent_memory_scratchpad_text(mem)

    # Verify no unclosed rich markup crashes
    from rich.text import Text
    parsed_text = Text.from_markup(formatted)
    assert len(parsed_text.plain) > 0


@pytest.mark.asyncio
async def test_agent_memory_widget_lifecycle():
    """Verify AgentMemoryWidget updates and deduplicates properly."""
    from rlm_optimized.tui_app import AgentMemoryWidget

    widget = AgentMemoryWidget()
    app = MagicMock()
    app.engine.memory = TieredMemory(config=MemoryConfig())
    app.engine.memory.state.current_task = "Task 1"
    app.engine.project_root = "/tmp"
    app._is_goal_mode.return_value = False
    widget._app = app

    widget.update_memory()
    assert widget._last_markup != ""
    assert "Task 1" in widget._last_markup

    # Updating with unchanged memory should retain markup
    prev_markup = widget._last_markup
    widget.update_memory()
    assert widget._last_markup == prev_markup


def test_scratchpad_preserves_long_error_messages():
    """Verify long error messages are preserved in full without 75-char ellipsis truncation."""
    mem = TieredMemory(config=MemoryConfig())
    long_err = (
        "FileNotFoundError: [Errno 2] No such file or directory: "
        "'/Users/harishgorle/Desktop/opencode/tourchlight v1_i6/core/prompts/system.py' "
        "at line 245 in execute_agent_loop"
    )
    mem.state.errors_seen = [long_err]
    formatted = build_agent_memory_scratchpad_text(mem)

    # Full error text should be in formatted output without being cut off
    assert "execute_agent_loop" in formatted
    assert "line 245" in formatted
    assert "/Users/harishgorle/Desktop/opencode/tourchlight v1_i6/core/prompts/system.py" in formatted



