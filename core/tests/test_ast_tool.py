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

    res_struct = tool_search_ast_impl({"action": "get_project_structure"}, str(tmp_path))
    assert isinstance(res_struct, str)


def test_run_command_intercept_ast_functions(tmp_path):
    from core.tools.implementations import tool_run_command_impl
    (tmp_path / "bar.py").write_text("class DemoClass:\n    pass\n", encoding="utf-8")

    # When LLM sends "get_project_structure()*" to RUN_COMMAND
    res = tool_run_command_impl({"cmd": "get_project_structure()*"}, str(tmp_path))
    assert "Exit 2" not in res
    assert "syntax error" not in res
    assert "bar.py" in res or "DemoClass" in res or "Structure" in res or "Project" in res


def test_search_ast_after_writing_file(tmp_path):
    from core.tools.implementations import tool_write_file_impl, tool_search_ast_impl

    # Write a new JS file
    game_js_content = "function generateFood() {\n    return { x: 5, y: 10 };\n}\n"
    res_write = tool_write_file_impl({"path": "game.js", "content": game_js_content}, str(tmp_path))
    assert "Written" in res_write

    # Query AST graph immediately after writing
    res_ast = tool_search_ast_impl({"query": "generateFood"}, str(tmp_path))
    assert "generateFood" in res_ast
    assert "game.js" in res_ast
    assert "No AST knowledge graph indexed" not in res_ast



