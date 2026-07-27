import pytest
from core.tools.schemas import TOOL_SCHEMAS, validate_tool_call, get_openai_tools_schema


def test_tool_schemas_exist():
    expected = [
        "READ_FILE", "WRITE_FILE", "EDIT_FILE", "READ_SYMBOLS",
        "LIST_DIR", "GREP", "RUN_COMMAND", "WEB_SEARCH", "WEB_FETCH",
        "DOC_SEARCH", "WEB_VERIFY", "SAVE_MEMORY", "FORMAT_CODE", "VERIFY", "ASK_USER",
    ]
    for name in expected:
        assert name in TOOL_SCHEMAS


def test_validate_tool_call_valid():
    is_valid, msg, args = validate_tool_call("READ_FILE", {"path": "main.py"})
    assert is_valid is True
    assert args["path"] == "main.py"


def test_validate_tool_call_alias():
    is_valid, msg, args = validate_tool_call("READ_FILE", {"file": "main.py"})
    assert is_valid is True
    assert args["path"] == "main.py"


def test_validate_tool_call_missing_required():
    is_valid, msg, args = validate_tool_call("WRITE_FILE", {"path": "test.py"})
    assert is_valid is False
    assert "content" in msg


def test_validate_tool_call_unknown_tool():
    is_valid, msg, args = validate_tool_call("UNKNOWN_TOOL", {})
    assert is_valid is False
    assert "Unknown tool" in msg


def test_get_openai_tools_schema():
    tools = get_openai_tools_schema()
    assert len(tools) > 0
    assert tools[0]["type"] == "function"
    assert "function" in tools[0]
    assert "name" in tools[0]["function"]
    assert "parameters" in tools[0]["function"]
