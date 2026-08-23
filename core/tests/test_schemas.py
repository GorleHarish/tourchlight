import pytest
from core.tools.schemas import TOOL_SCHEMAS, validate_tool_call, get_openai_tools_schema


def test_tool_schemas_exist():
    expected = [
        "READ_FILE",
        "WRITE_FILE",
        "EDIT_FILE",
        "READ_SYMBOLS",
        "LIST_DIR",
        "GREP",
        "RUN_COMMAND",
        "WEB_SEARCH",
        "WEB_FETCH",
        "DOC_SEARCH",
        "WEB_VERIFY",
        "SAVE_MEMORY",
        "FORMAT_CODE",
        "VERIFY",
        "ASK_USER",
        "SET_PHASE",
    ]
    for name in expected:
        assert name in TOOL_SCHEMAS


def test_validate_tool_call_set_phase():
    is_valid, msg, args = validate_tool_call("SET_PHASE", {"phase": "code", "reason": "switching to implementation"})
    assert is_valid is True
    assert args["phase"] == "code"
    assert args["reason"] == "switching to implementation"

    # Alias check
    is_valid_alias, _, args_alias = validate_tool_call("SET_PHASE", {"mode": "troubleshoot"})
    assert is_valid_alias is True
    assert args_alias["phase"] == "troubleshoot"



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


def test_validate_tool_call_list_dir_optional_path():
    is_valid, msg, args = validate_tool_call("LIST_DIR", {})
    assert is_valid is True
    assert args.get("path") == "."


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
    is_valid, msg, args = validate_tool_call(
        "EDIT_FILE",
        {"path": "main.py", "old_text": "a", "new_text": "b", "start_line": "10"},
    )
    assert is_valid is True
    assert args["start_line"] == 10
    assert isinstance(args["start_line"], int)

    is_valid_bool, msg_bool, args_bool = validate_tool_call(
        "WRITE_FILE", {"path": "main.py", "content": "x", "force": "true"}
    )
    assert is_valid_bool is True
    assert args_bool["force"] is True
    assert isinstance(args_bool["force"], bool)


def test_get_schemas_for_phase():
    from core.tools.schemas import get_schemas_for_phase

    plan_schemas = get_schemas_for_phase("plan")
    assert "READ_FILE" in plan_schemas
    assert "RUN_COMMAND" in plan_schemas
    assert "WRITE_FILE" in plan_schemas
    assert "EDIT_FILE" in plan_schemas

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
    assert "WRITE_FILE" in troubleshoot_schemas


def test_registry_get_description_block_phase():
    from core.tools.registry import get_tool_registry

    registry = get_tool_registry()
    plan_block = registry.get_description_block(phase="plan")
    assert "READ_FILE" in plan_block
    assert "RUN_COMMAND" in plan_block

    code_block = registry.get_description_block(phase="code")
    assert "RUN_COMMAND" in code_block
    assert "WRITE_FILE" in code_block


def test_ask_user_schema_and_formatting():
    from core.tools.implementations import tool_ask_user_impl

    is_valid, msg, args = validate_tool_call(
        "ASK_USER",
        {
            "question": "Which theme?",
            "choices": ["(Recommended) Dark Mode", "Light Mode"],
            "multi_select": False,
        },
    )
    assert is_valid is True
    assert args["question"] == "Which theme?"
    assert args["options"] == ["(Recommended) Dark Mode", "Light Mode"]
    assert args["is_multi_select"] is False

    output = tool_ask_user_impl(args, ".")
    assert "[AWAITING USER INPUT] Which theme?" in output
    assert "Radio (Single Choice)" in output
    assert "( ) 1. (Recommended) Dark Mode" in output
    assert "( ) 2. Light Mode" in output
    assert "Custom text input" in output

    # Checkbox multi-select
    out_multi = tool_ask_user_impl(
        {
            "question": "Select features:",
            "options": ["(Recommended) Sound effects", "Particle animations"],
            "is_multi_select": True,
        },
        ".",
    )
    assert "Checkbox (Multi-Select)" in out_multi
    assert "[ ] 1. (Recommended) Sound effects" in out_multi


def test_read_file_line_range_flexibility(tmp_path):
    from core.tools.implementations import tool_read_file_impl

    # Create dummy file with 30 lines
    test_file = tmp_path / "sample.py"
    lines = [f"line_{i} = {i}" for i in range(1, 31)]
    test_file.write_text("\n".join(lines), encoding="utf-8")

    # 1. Path colon suffix: "sample.py:10-20"
    out1 = tool_read_file_impl({"path": "sample.py:10-20"}, str(tmp_path))
    assert "lines 10–20 (of 30 total)" in out1
    assert "10 | line_10 = 10" in out1
    assert "20 | line_20 = 20" in out1

    # 2. Path L-prefix suffix: "sample.py:L5-L15"
    out2 = tool_read_file_impl({"path": "sample.py:L5-L15"}, str(tmp_path))
    assert "lines 5–15 (of 30 total)" in out2

    # 3. Explicit arguments: start_line / end_line
    out3 = tool_read_file_impl({"path": "sample.py", "start_line": "L8", "end_line": "12"}, str(tmp_path))
    assert "lines 8–12 (of 30 total)" in out3

    # 4. Range parameter: range: "15-25"
    out4 = tool_read_file_impl({"path": "sample.py", "range": "15-25"}, str(tmp_path))
    assert "lines 15–25 (of 30 total)" in out4

