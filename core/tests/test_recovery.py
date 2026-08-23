import pytest
from core.errors.types import ToolError, ParseError, SecurityError
from core.errors.recovery import RecoveryEngine, RecoveryAction, get_recovery_hint


def test_recovery_engine_retry():
    engine = RecoveryEngine()
    error = ToolError(tool_name="READ_FILE", reason="File not found")
    action = engine.handle(error)
    assert action == RecoveryAction.RETRY


def test_recovery_engine_escalation():
    engine = RecoveryEngine()
    error = ToolError(tool_name="READ_FILE", reason="File not found")
    for _ in range(3):
        engine.handle(error)
    action = engine.handle(error)
    assert action == RecoveryAction.COMPRESS_AND_RETRY


def test_recovery_engine_skip():
    engine = RecoveryEngine()
    error = ToolError(tool_name="READ_FILE", reason="File not found")
    for _ in range(5):
        engine.handle(error)
    action = engine.handle(error)
    assert action == RecoveryAction.SKIP


def test_recovery_engine_security_abort():
    engine = RecoveryEngine()
    error = SecurityError(attempted="/etc/passwd", allowed_scope="/project")
    action = engine.handle(error)
    assert action == RecoveryAction.ABORT


def test_recovery_engine_reset():
    engine = RecoveryEngine()
    error = ToolError(tool_name="READ_FILE", reason="File not found")
    for _ in range(3):
        engine.handle(error)
    engine.reset()
    action = engine.handle(error)
    assert action == RecoveryAction.RETRY


def test_recovery_hint_tool_error():
    error = ToolError(tool_name="READ_FILE", reason="File not found")
    hint = get_recovery_hint(error)
    assert "GREP" in hint or "find" in hint.lower()


def test_recovery_hint_connection_error():
    from core.errors.types import ConnectionError
    error = ConnectionError(provider="lmstudio", base_url="http://localhost:1234")
    hint = get_recovery_hint(error)
    assert "lmstudio" in hint.lower() or "connect" in hint.lower()


def test_recovery_hint_503_loading_model():
    from core.errors.types import ConnectionError
    error = ConnectionError(
        provider="llama-server",
        message="HTTP Error 503: Service Unavailable (Loading model)",
    )
    hint = get_recovery_hint(error)
    assert "loading model weights" in hint.lower() or "loading" in hint.lower()




def test_recovery_hint_security_error():
    error = SecurityError(attempted="/etc/passwd", allowed_scope="/project")
    hint = get_recovery_hint(error)
    assert "workspace" in hint.lower() or "path" in hint.lower()


def test_recovery_engine_none_reason():
    engine = RecoveryEngine()
    error = ToolError(tool_name="WRITE_FILE", reason=None, message="File error")
    action = engine.handle(error)
    assert action == RecoveryAction.RETRY
    hint = get_recovery_hint(error)
    assert "WRITE_FILE" in hint or "failed" in hint

