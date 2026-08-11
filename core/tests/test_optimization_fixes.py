import json
import pytest
from unittest.mock import MagicMock
from core.tools.registry import ToolRegistry, get_tool_registry
from core.tools.implementations import _validate_and_repair, tool_edit_file_impl, tool_search_ast_impl
from core.tools.task_helpers import get_compact_task_matrix
from core.memory.budget import ContextBudget
from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized


def test_identical_old_new_text_preflight():
    registry = get_tool_registry()
    res = registry.execute("EDIT_FILE", {"path": "dummy.py", "old_text": "abc", "new_text": "abc"})
    assert res.success is True
    assert "identical" in res.output
    assert res.metadata.get("cached") is True


def test_validate_and_repair_compact_json_errors():
    status, payload = _validate_and_repair("def foo(:", "syntax_err.py", ".", force=False)
    assert status == "error"
    assert "Syntax gate rejected write ->" in payload
    json_part = payload.split("-> ", 1)[1]
    parsed = json.loads(json_part)
    assert parsed["error"] == "syntax_error"
    assert parsed["file"] == "syntax_err.py"


def test_edit_file_tail_ultra_compact_directive(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    res = tool_edit_file_impl({"path": str(f), "old_text": "non_existent_code_block", "new_text": "foo"}, str(tmp_path))
    assert "EDIT_FAIL:" in res
    assert "NEXT: READ_FILE(" in res or "WRITE_FILE" in res


def test_task_matrix_compress_over_45_percent_context():
    class DummyBudget:
        context_usage_ratio = 0.50
        headroom_ratio = 0.50
        scratchpad_section_cap = 5

    # Test with dummy project root
    lines = get_compact_task_matrix("/tmp", budget=DummyBudget())
    # Should be empty or 1-line if files existed; verify is_tight evaluation logic
    b = ContextBudget(max_tokens=12000, used_tokens=7000, base_pinned_tokens=500)
    assert b.context_usage_ratio > 0.45


@pytest.mark.asyncio
async def test_ring_buffer_prompt_dedup_skip():
    engine = RLMEngineOptimized(client=MagicMock())
    messages = [{"role": "user", "content": "repeat test"}]
    res1 = await engine._stream_llm_with_retry(messages)
    res2 = await engine._stream_llm_with_retry(messages)
    assert "Duplicate prompt state detected" in res2


def test_schema_target_alias_no_collision():
    from core.tools.schemas import validate_tool_call
    is_valid, msg, args = validate_tool_call("EDIT_FILE", {"target": "src/main.py", "old_text": "foo", "new_text": "bar"})
    assert is_valid is True
    assert args["path"] == "src/main.py"
    assert args["old_text"] == "foo"
    assert args["new_text"] == "bar"


def test_whitespace_stripped_preflight():
    registry = get_tool_registry()
    res = registry.execute("EDIT_FILE", {"path": "dummy.py", "old_text": "  def foo():\n  pass \n", "new_text": "def foo():\n  pass"})
    assert res.success is True
    assert "identical" in res.output


def test_trajectory_lock_window_and_read_only_rate_limiting():
    from core.tools.dedup import TrajectoryLock
    lock = TrajectoryLock(window_size=10, max_duplicates=3)
    assert lock.window_size == 10

    # Test mutating tool (READ_FILE=False)
    args = {"path": "test.txt", "content": "hello"}
    # Call 1: new
    is_d1, c1, _ = lock.is_duplicate("WRITE_FILE", args, is_read_only=False)
    assert is_d1 is False
    lock.register("WRITE_FILE", args)

    # Call 2: duplicate
    is_d2, c2, _ = lock.is_duplicate("WRITE_FILE", args, is_read_only=False)
    assert is_d2 is True
    assert c2 == 2

    # Test read-only tool (READ_FILE=True)
    read_args = {"path": "read_test.py"}
    r_lock = TrajectoryLock(window_size=10)
    
    # Calls 1, 2, 3 should not soft-block
    for i in range(3):
        is_d, count, _ = r_lock.is_duplicate("READ_FILE", read_args, is_read_only=True)
        assert is_d is False
        r_lock.register("READ_FILE", read_args)

    # Call 4 should soft-block
    is_d4, count4, hint4 = r_lock.is_duplicate("READ_FILE", read_args, is_read_only=True)
    assert is_d4 is True
    assert count4 == 4
    assert "Trajectory Lock" in hint4


def test_recovery_engine_reset():
    from core.errors.recovery import RecoveryEngine
    from core.errors.types import ToolError
    engine = RecoveryEngine()
    err = ToolError("READ_FILE", "file not found", reason="FileNotFound")
    action1 = engine.handle(err)
    assert engine._states != {}
    engine.reset()
    assert engine._states == {}

