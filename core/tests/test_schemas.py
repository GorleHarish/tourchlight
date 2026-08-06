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


def test_validate_tool_call_coercion():
    is_valid, msg, args = validate_tool_call("EDIT_FILE", {"path": "main.py", "old_text": "a", "new_text": "b", "start_line": "10"})
    assert is_valid is True
    assert args["start_line"] == 10
    assert isinstance(args["start_line"], int)

    is_valid_bool, msg_bool, args_bool = validate_tool_call("WRITE_FILE", {"path": "main.py", "content": "x", "force": "true"})
    assert is_valid_bool is True
    assert args_bool["force"] is True
    assert isinstance(args_bool["force"], bool)


def test_get_schemas_for_phase():
    from core.tools.schemas import get_schemas_for_phase
    plan_schemas = get_schemas_for_phase("plan")
    assert "READ_FILE" in plan_schemas
    assert "RUN_COMMAND" not in plan_schemas
    assert "WRITE_FILE" not in plan_schemas

    chat_schemas = get_schemas_for_phase("chat")
    assert "READ_FILE" in chat_schemas
    assert "WRITE_FILE" not in chat_schemas
    assert "RUN_COMMAND" not in chat_schemas

    code_schemas = get_schemas_for_phase("code")
    assert "RUN_COMMAND" in code_schemas
    assert "WRITE_FILE" in code_schemas
    assert "EDIT_FILE" in code_schemas

    troubleshoot_schemas = get_schemas_for_phase("troubleshoot")
    assert "RUN_COMMAND" in troubleshoot_schemas
    assert "EDIT_FILE" in troubleshoot_schemas
    assert "WRITE_FILE" not in troubleshoot_schemas  # WRITE_FILE is excluded in troubleshoot phase


def test_registry_get_description_block_phase():
    from core.tools.registry import get_tool_registry
    registry = get_tool_registry()
    plan_block = registry.get_description_block(phase="plan")
    assert "READ_FILE" in plan_block
    assert "RUN_COMMAND" not in plan_block

    code_block = registry.get_description_block(phase="code")
    assert "RUN_COMMAND" in code_block
    assert "WRITE_FILE" in code_block


