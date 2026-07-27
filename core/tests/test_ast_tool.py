"""
Tests for SEARCH_AST tool implementation and Kuzu connection handling.
"""

from core.tools.registry import get_tool_registry
from core.tools.schemas import validate_tool_call
from core.tools.implementations import tool_search_ast_impl


def test_search_ast_schema_validation():
    registry = get_tool_registry()
    tool = registry.get("SEARCH_AST")
    assert tool is not None
    assert tool.name == "SEARCH_AST"
    assert tool.risk_level == "auto"

    # Valid call
    is_valid, msg, norm = validate_tool_call("SEARCH_AST", {"query": "IndexVisitor", "action": "signature"})
    assert is_valid
    assert norm["query"] == "IndexVisitor"
    assert norm["action"] == "signature"


def test_search_ast_impl_fallback():
    # Test call when no graph DB is indexed yet
    result = tool_search_ast_impl({"query": "non_existent_symbol", "action": "signature"}, project_root=".")
    assert isinstance(result, str)
    assert len(result) > 0
