import pytest
from core.errors.types import (
    TorchlightError, ToolError, ParseError, ContextOverflowError,
    ConnectionError, SecurityError, ToolValidationError, RecoveryAction,
)


def test_torchlight_error_basic():
    e = TorchlightError("something went wrong")
    assert str(e) == "something went wrong"
    assert e.recoverable is True


def test_torchlight_error_with_context():
    e = TorchlightError("err", context={"key": "val"}, source="test")
    assert e.context == {"key": "val"}
    assert e.source == "test"
    assert "[test] err" == str(e)


def test_tool_error():
    e = ToolError(tool_name="READ_FILE", reason="File not found")
    assert "READ_FILE" in e.message
    assert "File not found" in e.message
    assert e.tool_name == "READ_FILE"


def test_tool_error_defaults():
    e = ToolError()
    assert e.tool_name == ""
    assert e.reason == ""


def test_parse_error():
    e = ParseError(raw_output="bad json", parser_used="json")
    assert e.raw_output == "bad json"
    assert e.parser_used == "json"
    assert e.recoverable is True


def test_context_overflow_error():
    e = ContextOverflowError(token_count=5000, max_tokens=4096)
    assert "5,000" in e.message
    assert "4,096" in e.message


def test_connection_error():
    e = ConnectionError(provider="lmstudio", base_url="http://localhost:1234")
    assert "lmstudio" in e.message
    assert e.recoverable is True


def test_security_error_not_recoverable():
    e = SecurityError(attempted="/etc/passwd", allowed_scope="/project")
    assert e.recoverable is False
    assert "/etc/passwd" in e.message


def test_tool_validation_error():
    e = ToolValidationError(tool_name="WRITE_FILE", missing_fields=["content"])
    assert "content" in e.message
    assert e.tool_name == "WRITE_FILE"


def test_recovery_action_enum():
    assert RecoveryAction.RETRY.value == "retry"
    assert RecoveryAction.COMPRESS_AND_RETRY.value == "compress_and_retry"
    assert RecoveryAction.SKIP.value == "skip"
    assert RecoveryAction.ABORT.value == "abort"
    assert RecoveryAction.ASK_USER.value == "ask_user"
