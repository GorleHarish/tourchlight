"""
Torchlight Native Graph Engine — AST-based Knowledge Graph & Dependency Mapping.

Parses project source files into a lightweight knowledge graph stored at `.torchlight/graph.json`
and `.torchlight/GRAPH_REPORT.md`. Provides graph traversal, pathfinding, and subgraph retrieval.
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "env", "dist", "build", ".next", ".nuxt", "coverage",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "site-packages",
    ".egg-info", ".torchlight", "graphify-out",
}

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".go", ".rs", ".java", ".cpp", ".c", ".h",
    ".rb", ".cs", ".kt",
}


class PyASTVisitor(ast.NodeVisitor):
    """AST visitor to extract classes, functions, calls, and imports from Python code."""
    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.classes: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
        self.imports: List[str] = []
        self.calls: List[Dict[str, Any]] = []
        self._current_class: Optional[str] = None
        self._current_func: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef):
        class_id = f"{self.rel_path}::{node.name}"
        bases = [ast.unparse(b) for b in node.bases] if hasattr(ast, "unparse") else []
        doc = ast.get_docstring(node) or ""
        self.classes.append({
            "id": class_id,
            "name": node.name,
            "file": self.rel_path,
            "bases": bases,
            "line_start": node.lineno,
            "line_end": getattr(node, "end_lineno", node.lineno),
            "docstring": doc.splitlines()[0] if doc else "",
        })

        prev_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_func(node)

    def _visit_func(self, node):
        parent_id = f"{self.rel_path}::{self._current_class}" if self._current_class else self.rel_path
        func_id = f"{parent_id}::{node.name}"
        args = [arg.arg for arg in node.args.args]
        doc = ast.get_docstring(node) or ""

        self.functions.append({
            "id": func_id,
            "name": node.name,
            "class": self._current_class,
            "file": self.rel_path,
            "args": args,
            "line_start": node.lineno,
            "line_end": getattr(node, "end_lineno", node.lineno),
            "docstring": doc.splitlines()[0] if doc else "",
        })

        prev_func = self._current_func
        self._current_func = func_id
        self.generic_visit(node)
        self._current_func = prev_func

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        for alias in node.names:
            self.imports.append(f"{mod}.{alias.name}" if mod else alias.name)

    def visit_Call(self, node: ast.Call):
        if self._current_func:
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name:
                self.calls.append({
                    "caller": self._current_func,
                    "target_name": func_name,
                    "line": node.lineno,
                })
        self.generic_visit(node)


class ProjectGraph:
    """Stores nodes (files, classes, functions) and edges (contains, calls, imports)."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir.resolve()
        self.dot_torchlight = self.project_dir / ".torchlight"
        self.graph_file = self.dot_torchlight / "graph.json"
        self.report_file = self.dot_torchlight / "GRAPH_REPORT.md"

        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []

    def build(self) -> Dict[str, Any]:
        """Scan project files and construct the AST graph."""
        self.nodes.clear()
        self.edges.clear()

        for root, dirs, files in os.walk(self.project_dir):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for file in files:
                path = Path(root) / file
                if path.suffix not in SUPPORTED_EXTENSIONS:
                    continue
                try:
                    rel_path = str(path.relative_to(self.project_dir))
                    self._index_file(path, rel_path)
                except Exception:
                    continue

        self.save()
        return self.to_dict()

    def _index_file(self, abs_path: Path, rel_path: str):
        file_node_id = rel_path
        text = abs_path.read_text(errors="ignore")

        self.nodes[file_node_id] = {
            "id": file_node_id,
            "type": "file",
            "name": rel_path,
            "lines": len(text.splitlines()),
        }

        if abs_path.suffix == ".py":
            try:
                tree = ast.parse(text, filename=rel_path)
                visitor = PyASTVisitor(rel_path)
                visitor.visit(tree)

                for c in visitor.classes:
                    self.nodes[c["id"]] = {"type": "class", **c}
                    self.edges.append({"from": file_node_id, "to": c["id"], "type": "contains"})

                for fn in visitor.functions:
                    self.nodes[fn["id"]] = {"type": "function", **fn}
                    parent = f"{rel_path}::{fn['class']}" if fn["class"] else file_node_id
                    self.edges.append({"from": parent, "to": fn["id"], "type": "contains"})

                for imp in visitor.imports:
                    self.edges.append({"from": file_node_id, "to": imp, "type": "imports"})

                for call in visitor.calls:
                    self.edges.append({
                        "from": call["caller"],
                        "to": call["target_name"],
                        "type": "calls",
                        "line": call["line"],
                    })

            except Exception:
                self._regex_fallback(text, rel_path)
        else:
            self._regex_fallback(text, rel_path)

    def _regex_fallback(self, text: str, rel_path: str):
        file_node_id = rel_path
        func_re = re.compile(r'^(?:export\s+)?(?:async\s+)?(?:function|fn|def|func)\s+(\w+)', re.MULTILINE)
        class_re = re.compile(r'^(?:export\s+)?(?:class|struct|type)\s+(\w+)', re.MULTILINE)

        for m in func_re.finditer(text):
            func_name = m.group(1)
            func_id = f"{rel_path}::{func_name}"
            lineno = text[:m.start()].count("\n") + 1
            self.nodes[func_id] = {
                "id": func_id,
                "type": "function",
                "name": func_name,
                "file": rel_path,
                "line_start": lineno,
            }
            self.edges.append({"from": file_node_id, "to": func_id, "type": "contains"})

        for m in class_re.finditer(text):
            class_name = m.group(1)
            class_id = f"{rel_path}::{class_name}"
            lineno = text[:m.start()].count("\n") + 1
            self.nodes[class_id] = {
                "id": class_id,
                "type": "class",
                "name": class_name,
                "file": rel_path,
                "line_start": lineno,
            }
            self.edges.append({"from": file_node_id, "to": class_id, "type": "contains"})

    def save(self):
        """Save graph data to JSON and markdown report."""
        self.dot_torchlight.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()

        with open(self.graph_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        report_lines = [
            f"# Torchlight Knowledge Graph Report",
            f"**Project**: `{self.project_dir.name}`",
            f"**Total Nodes**: {len(self.nodes)} | **Total Edges**: {len(self.edges)}",
            "",
            "## Indexed Nodes",
        ]
        files = [n for n in self.nodes.values() if n["type"] == "file"]
        classes = [n for n in self.nodes.values() if n["type"] == "class"]
        funcs = [n for n in self.nodes.values() if n["type"] == "function"]

        report_lines.append(f"- **Files**: {len(files)}")
        report_lines.append(f"- **Classes**: {len(classes)}")
        report_lines.append(f"- **Functions**: {len(funcs)}")
        report_lines.append("")
        report_lines.append("### Key Classes & Functions")

        for c in classes[:25]:
            report_lines.append(f"- `[Class]` **{c['name']}** (`{c['file']}:L{c['line_start']}`)")
        for fn in funcs[:35]:
            report_lines.append(f"- `[Function]` **{fn['name']}** (`{fn['file']}:L{fn['line_start']}`)")

        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

    def load(self) -> bool:
        """Load graph from JSON file if available."""
        if not self.graph_file.exists():
            return False
        try:
            with open(self.graph_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.nodes = data.get("nodes", {})
            self.edges = data.get("edges", [])
            return True
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project": self.project_dir.name,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": self.nodes,
            "edges": self.edges,
        }

    # ── Traversal and Querying ────────────────────────────────────────────────

    def query(self, search_term: str, top_k: int = 5) -> str:
        """Search nodes matching search_term."""
        if not self.nodes:
            if not self.load():
                self.build()

        term = search_term.lower()
        matches = []

        for nid, node in self.nodes.items():
            name = node.get("name", "")
            doc = node.get("docstring", "")
            if term in name.lower() or term in doc.lower() or term in nid.lower():
                matches.append(node)

        if not matches:
            return f"No AST graph nodes found matching '{search_term}'."

        # Cap at top_k to prevent context overflow
        capped = matches[:top_k]
        lines = [f"Found {len(matches)} matching AST nodes for '{search_term}' (showing {len(capped)}):"]
        for m in capped:
            ntype = m.get("type", "node").upper()
            file_loc = f"{m.get('file', m.get('id'))}:L{m.get('line_start', 1)}"
            doc_str = f" - {m['docstring'][:80]}" if m.get("docstring") else ""
            lines.append(f"  [{ntype}] {m.get('name')} ({file_loc}){doc_str}")
        return "\n".join(lines)

    def find_path(self, source_name: str, target_name: str, max_depth: int = 10) -> str:
        """Find relationship path between source and target symbols."""
        if not source_name or not target_name:
            return "Path search requires both source and target names."

        if not self.nodes:
            if not self.load():
                self.build()

        src_nodes = [nid for nid, n in self.nodes.items() if source_name.lower() in n.get("name", "").lower()]
        tgt_nodes = [nid for nid, n in self.nodes.items() if target_name.lower() in n.get("name", "").lower()]

        if not src_nodes or not tgt_nodes:
            return f"Path search failed: '{source_name}' or '{target_name}' not found in AST index."

        adj: Dict[str, List[Tuple[str, str]]] = {}
        for edge in self.edges:
            f, t, etype = edge["from"], edge["to"], edge["type"]
            adj.setdefault(f, []).append((t, etype))

        # BFS for shortest path with depth limit to prevent runaway traversal
        from collections import deque
        queue: deque = deque()
        queue.append((src_nodes[0], [src_nodes[0]], 0))
        visited = {src_nodes[0]}
        target_set = set(tgt_nodes)

        while queue:
            curr, path, depth = queue.popleft()
            if curr in target_set:
                return f"Path found ({len(path)-1} hops):\n" + " -> ".join(path)
            if depth >= max_depth:
                continue
            for nxt, etype in adj.get(curr, []):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, path + [f"[{etype}]-> {nxt}"], depth + 1))

        return f"No direct graph relationship path found between '{source_name}' and '{target_name}'."

    _MAX_SUBGRAPH_EDGES = 40

    def get_subgraph(self, symbol_or_path: str, max_depth: int = 2) -> str:
        """Extract connected subgraph centered at symbol or file path."""
        if not self.nodes:
            if not self.load():
                self.build()

        matched_id = None
        for nid, n in self.nodes.items():
            if symbol_or_path.lower() in nid.lower() or symbol_or_path.lower() in n.get("name", "").lower():
                matched_id = nid
                break

        if not matched_id:
            return f"Symbol or path '{symbol_or_path}' not found in AST graph."

        connected_edges = []
        for e in self.edges:
            if e["from"] == matched_id or e["to"] == matched_id:
                connected_edges.append(e)

        capped = connected_edges[:self._MAX_SUBGRAPH_EDGES]
        lines = [f"Subgraph for `{matched_id}` ({len(connected_edges)} connections, showing {len(capped)}):"]
        for e in capped:
            direction = f"{e['from']} --[{e['type']}]--> {e['to']}"
            lines.append(f"  • {direction}")
        if len(connected_edges) > self._MAX_SUBGRAPH_EDGES:
            lines.append(f"  ... and {len(connected_edges) - self._MAX_SUBGRAPH_EDGES} more connections")

        return "\n".join(lines)

    _MAX_STRUCTURE_FILES = 20
    _MAX_FUNCS_PER_FILE = 5

    def get_structure(self) -> str:
        """Return structured summary of files, classes, and function signatures."""
        if not self.nodes:
            if not self.load():
                self.build()

        files = [n for n in self.nodes.values() if n["type"] == "file"]
        classes = [n for n in self.nodes.values() if n["type"] == "class"]
        funcs = [n for n in self.nodes.values() if n["type"] == "function"]

        lines = [
            f"Project Structure ({len(files)} files, {len(classes)} classes, {len(funcs)} functions):",
        ]
        for f in files[:self._MAX_STRUCTURE_FILES]:
            f_funcs = [fn for fn in funcs if fn.get("file") == f["id"]]
            f_classes = [cl for cl in classes if cl.get("file") == f["id"]]
            lines.append(f"\n📂 {f['id']} ({len(f_classes)} classes, {len(f_funcs)} funcs)")
            for cl in f_classes:
                lines.append(f"   └─ class {cl['name']} (L{cl['line_start']})")
            for fn in f_funcs[:self._MAX_FUNCS_PER_FILE]:
                args_str = ", ".join(fn.get("args", []))
                lines.append(f"   └─ def {fn['name']}({args_str}) (L{fn['line_start']})")
        if len(files) > self._MAX_STRUCTURE_FILES:
            lines.append(f"\n... and {len(files) - self._MAX_STRUCTURE_FILES} more files")

        return "\n".join(lines)


# ── Global Cache ─────────────────────────────────────────────────────────────

_graphs: Dict[str, ProjectGraph] = {}

def get_project_graph(project_root: str = ".") -> ProjectGraph:
    """Get or create the ProjectGraph instance for a given root directory."""
    root_path = Path(project_root).resolve()
    key = str(root_path)
    if key not in _graphs:
        graph = ProjectGraph(root_path)
        if not graph.load():
            graph.build()
        _graphs[key] = graph
    return _graphs[key]
