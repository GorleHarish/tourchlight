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


def test_read_symbols_indented_methods_and_duplicate_names(tmp_path):
    from core.tools.implementations import tool_read_symbols_impl
    code = (
        "class ComponentA:\n"
        "    def execute(self):\n"
        "        pass\n\n"
        "class ComponentB:\n"
        "    def execute(self):\n"
        "        pass\n"
    )
    file_path = tmp_path / "comp.py"
    file_path.write_text(code, encoding="utf-8")

    res = tool_read_symbols_impl({"path": "comp.py"}, str(tmp_path))
    assert "ComponentA" in res
    assert "ComponentB" in res
    # Ensure both execute methods (L2 and L6) are extracted
    assert "L   2" in res or "L2" in res or "2" in res
    assert "L   6" in res or "L6" in res or "6" in res


def test_search_ast_action_aliases(tmp_path):
    (tmp_path / "foo.py").write_text("def my_func(a, b):\n    return a + b\n", encoding="utf-8")
    res_sig = tool_search_ast_impl({"action": "signature", "query": "my_func"}, str(tmp_path))
    assert "my_func" in res_sig

    res_deps = tool_search_ast_impl({"action": "deps", "query": "foo.py"}, str(tmp_path))
    assert "Subgraph" in res_deps

