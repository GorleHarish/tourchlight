"""
Unit tests for Torchlight Native AST Graph Engine.
"""

import json
from pathlib import Path
import pytest
from core.flashlight.graph_engine import ProjectGraph, get_project_graph
from core.tools.registry import get_tool_registry


def test_project_graph_build(tmp_path: Path):
    # Create sample Python project structure
    main_py = tmp_path / "main.py"
    main_py.write_text("""
import sys

class Calculator:
    def add(self, a, b):
        return a + b

def main():
    calc = Calculator()
    return calc.add(1, 2)
""")

    graph = ProjectGraph(tmp_path)
    data = graph.build()

    assert data["node_count"] > 0
    assert "main.py" in graph.nodes
    assert "main.py::Calculator" in graph.nodes
    assert "main.py::main" in graph.nodes

    assert (tmp_path / ".torchlight" / "graph.json").exists()
    assert (tmp_path / ".torchlight" / "GRAPH_REPORT.md").exists()


def test_project_graph_queries(tmp_path: Path):
    main_py = tmp_path / "app.py"
    main_py.write_text("""
class Database:
    def connect(self):
        pass

def run_app():
    db = Database()
    db.connect()
""")

    graph = ProjectGraph(tmp_path)
    graph.build()

    # Query search
    res = graph.query("Database")
    assert "Database" in res
    assert "[CLASS]" in res

    # Path search
    path_res = graph.find_path("run_app", "Database")
    assert "Path found" in path_res or "Database" in path_res

    # Subgraph search
    subgraph_res = graph.get_subgraph("Database")
    assert "Subgraph for" in subgraph_res

    # Structure
    struct_res = graph.get_structure()
    assert "Project Structure" in struct_res
    assert "app.py" in struct_res


def test_tool_search_ast_integration(tmp_path: Path):
    py_file = tmp_path / "service.py"
    py_file.write_text("""
class AuthService:
    def login(self, username, password):
        return True
""")

    registry = get_tool_registry()

    # Re-index via tool
    res = registry.execute("SEARCH_AST", {"action": "update"}, project_root=str(tmp_path))
    assert res.success
    assert "AST Graph re-indexed" in res.output

    # Query structure via tool
    res_struct = registry.execute("SEARCH_AST", {"action": "structure"}, project_root=str(tmp_path))
    assert res_struct.success
    assert "AuthService" in res_struct.output

    # Query search via tool
    res_search = registry.execute("SEARCH_AST", {"query": "AuthService", "action": "search"}, project_root=str(tmp_path))
    assert res_search.success
    assert "AuthService" in res_search.output


def test_project_graph_advanced_signatures_and_paths(tmp_path: Path):
    mod_py = tmp_path / "module.py"
    mod_py.write_text("""
class Processor:
    def process(self, data, *args, flag=True, **kwargs):
        pass
""")
    graph = ProjectGraph(tmp_path)
    graph.build()

    # Verify signature extraction
    struct = graph.get_structure()
    assert "*args" in struct
    assert "flag" in struct
    assert "**kwargs" in struct

    # Path search with full node ID
    path_res = graph.find_path("module.py::Processor", "process")
    assert "Path found" in path_res

    # Multi-hop subgraph exact match
    subgraph_res = graph.get_subgraph("Processor", max_depth=2)
    assert "Subgraph for `module.py::Processor`" in subgraph_res

