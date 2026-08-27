"""
Torchlight Native Graph Engine — AST-based Knowledge Graph & Dependency Mapping.

Parses project source files into a lightweight knowledge graph stored at `.torchlight/graph.json`
and `.torchlight/GRAPH_REPORT.md`. Provides graph traversal, pathfinding, and subgraph retrieval.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.flashlight.graph_visitor import (
    HAS_TREE_SITTER,
    IGNORE_DIRS,
    SUPPORTED_EXTENSIONS,
    PyASTVisitor,
)
from core.flashlight.graph_indexer import GraphIndexerMixin
from core.flashlight.graph_traversal import GraphTraversalMixin


class ProjectGraph(GraphIndexerMixin, GraphTraversalMixin):
    """Stores nodes (files, classes, functions) and edges (contains, calls, imports)."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir.resolve()
        self.dot_torchlight = self.project_dir / ".torchlight"
        self.graph_file = self.dot_torchlight / "graph.json"
        self.report_file = self.dot_torchlight / "GRAPH_REPORT.md"

        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []


# ── Global Cache ─────────────────────────────────────────────────────────────

_graphs: Dict[str, ProjectGraph] = {}


def get_project_graph(project_root: str = ".") -> ProjectGraph:
    """Get or create the ProjectGraph instance for a given root directory."""
    root_path = Path(project_root).resolve()
    key = str(root_path)
    if key not in _graphs:
        graph = ProjectGraph(root_path)
        if not graph.load() or len(graph.nodes) == 0:
            graph.build()
        _graphs[key] = graph
    return _graphs[key]


def update_project_graph_file(project_root: str = ".", file_path: str = "") -> ProjectGraph:
    """Incrementally update the AST graph for a single modified file."""
    root_path = Path(project_root).resolve()
    graph = get_project_graph(project_root)
    if not file_path:
        return graph
    p = Path(file_path)
    abs_path = p if p.is_absolute() else (root_path / p).resolve()
    try:
        rel_path = abs_path.relative_to(root_path).as_posix()
        graph.update_file(abs_path, rel_path)
    except Exception:
        pass
    return graph


__all__ = [
    "IGNORE_DIRS",
    "SUPPORTED_EXTENSIONS",
    "HAS_TREE_SITTER",
    "PyASTVisitor",
    "ProjectGraph",
    "get_project_graph",
    "update_project_graph_file",
]
