"""
Unit tests for core/tools/parser.py tolerant tool parser & fuzzy repair engine.
"""

import pytest
from core.tools.parser import (
    tolerant_json_repair,
    extract_balanced_json_object,
    repair_unclosed_tool_call_tag,
    strip_interleaved_prose,
    unwrap_double_encoded_json,
    clean_and_parse_json,
    parse_tool_call_payload,
)
from core.tools.schemas import validate_tool_call


def test_tolerant_json_repair():
    # Test unescaped newlines/tabs inside string values
    bad_json = '{"path": "foo/bar.py", "content": "line1\nline2\ttab"}'
    repaired = tolerant_json_repair(bad_json)
    assert "\\n" in repaired
    assert "\\t" in repaired

    # Test unterminated string at end
    unterminated = '{"path": "foo/bar.py", "content": "line1'
    repaired_un = tolerant_json_repair(unterminated)
    assert repaired_un.endswith('"')


def test_extract_balanced_json_object():
    # Nested braces and trailing prose
    text = 'Here is the call: {"name": "READ_FILE", "arguments": {"path": "main.py"}} extra text after'
    extracted = extract_balanced_json_object(text)
    assert extracted == '{"name": "READ_FILE", "arguments": {"path": "main.py"}}'

    # Braces in string values
    text_str_braces = '{"code": "def foo(): { return 1; }", "path": "a.py"} trailing'
    extracted_str = extract_balanced_json_object(text_str_braces)
    assert extracted_str == '{"code": "def foo(): { return 1; }", "path": "a.py"}'


def test_repair_unclosed_tool_call_tag():
    text = '<tool_call>{"name": "READ_FILE", "arguments": {"path": "x.py"}}'
    repaired = repair_unclosed_tool_call_tag(text)
    assert repaired.endswith("</tool_call>")


def test_strip_interleaved_prose():
    text = 'Sure, I will execute the tool for you!\n<tool_call>{"name": "READ_FILE"}</tool_call>\nLet me know if you need anything else.'
    stripped = strip_interleaved_prose(text)
    assert stripped == '{"name": "READ_FILE"}'


def test_unwrap_double_encoded_json():
    double_encoded = '{"path": "test.py", "lines": "1-10"}'
    unwrapped = unwrap_double_encoded_json(double_encoded)
    assert isinstance(unwrapped, dict)
    assert unwrapped["path"] == "test.py"


def test_parse_tool_call_payload():
    # 1. Standard call
    raw = '<tool_call>{"name": "READ_FILE", "arguments": {"path": "src/main.py"}}</tool_call>'
    tool_name, args, meta = parse_tool_call_payload(raw)
    assert tool_name == "READ_FILE"
    assert args == {"path": "src/main.py"}

    # 2. Double-encoded string arguments
    raw_double = '<tool_call>{"name": "WRITE_FILE", "arguments": "{\\"path\\": \\"foo.py\\", \\"content\\": \\"hello\\"}"}</tool_call>'
    tool_name, args, meta = parse_tool_call_payload(raw_double)
    assert tool_name == "WRITE_FILE"
    assert args.get("path") == "foo.py"

    # 3. Unclosed tag with interleaved prose
    raw_unclosed = 'I will now run the command:\n<tool_call>{"name": "RUN_COMMAND", "arguments": {"command_line": "ls -l"}}'
    tool_name, args, meta = parse_tool_call_payload(raw_unclosed)
    assert tool_name == "RUN_COMMAND"
    assert args.get("command_line") == "ls -l"
    assert meta["is_repaired"] is True


def test_validate_tool_call_with_unwrapping_and_coercion():
    # Test double-encoded string passed as args to validate_tool_call
    double_encoded_args = '{"path": "src/app.py", "start_line": "10", "new_text": "hello"}'
    is_valid, msg, norm = validate_tool_call("EDIT_FILE", double_encoded_args)
    assert is_valid is True
    assert norm["path"] == "src/app.py"
    assert norm.get("start_line") == 10


def test_single_quoted_dict_parsing():
    raw_single_quotes = "<tool_call>{'name': 'READ_FILE', 'arguments': {'path': 'src/index.py'}}</tool_call>"
    tool_name, args, meta = parse_tool_call_payload(raw_single_quotes)
    assert tool_name == "READ_FILE"
    assert args == {"path": "src/index.py"}


def test_strip_thinking_tags():
    raw = "<think>Let me analyze the repo structure first...</think><tool_call>{\"name\": \"SEARCH_AST\", \"arguments\": {\"query\": \"main\"}}</tool_call>"
    stripped = strip_interleaved_prose(raw)
    assert stripped == '{"name": "SEARCH_AST", "arguments": {"query": "main"}}'


def test_repair_unclosed_action_tags():
    raw_write = '<WRITE_FILE path="test.py">def main(): pass'
    repaired = repair_unclosed_tool_call_tag(raw_write)
    assert repaired.endswith("</WRITE_FILE>")

