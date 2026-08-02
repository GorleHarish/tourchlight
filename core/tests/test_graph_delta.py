"""
Unit tests for incremental O(1) AST graph delta updates.
"""

import tempfile
from pathlib import Path
from core.flashlight.graph_engine import ProjectGraph, update_project_graph_file


def test_incremental_graph_file_update():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create two sample python files
        file_a = root / "module_a.py"
        file_a.write_text("def func_a():\n    pass\n")

        file_b = root / "module_b.py"
        file_b.write_text("def func_b():\n    pass\n")

        graph = ProjectGraph(root)
        graph.build()

        assert "module_a.py::func_a" in graph.nodes
        assert "module_b.py::func_b" in graph.nodes

        # Modify module_a.py to add a class and a new function
        file_a.write_text("class ClassA:\n    pass\n\ndef func_a_v2():\n    pass\n")

        # Perform incremental update for module_a.py
        graph.update_file(file_a, "module_a.py")

        # Verify old func_a is removed, new symbols are indexed, module_b remains untouched
        assert "module_a.py::func_a" not in graph.nodes
        assert "module_a.py::ClassA" in graph.nodes
        assert "module_a.py::func_a_v2" in graph.nodes
        assert "module_b.py::func_b" in graph.nodes


def test_update_project_graph_file_helper():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        file_x = root / "service.py"
        file_x.write_text("def start_service():\n    pass\n")

        graph = update_project_graph_file(str(root), "service.py")
        assert "service.py::start_service" in graph.nodes

        # Update service.py
        file_x.write_text("def stop_service():\n    pass\n")
        graph2 = update_project_graph_file(str(root), "service.py")

        assert "service.py::start_service" not in graph2.nodes
        assert "service.py::stop_service" in graph2.nodes
