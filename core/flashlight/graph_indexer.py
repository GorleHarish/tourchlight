"""AST project indexing, incremental change tracking, and graph file serialization."""

from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from core.flashlight.graph_visitor import (
    HAS_TREE_SITTER,
    IGNORE_DIRS,
    SUPPORTED_EXTENSIONS,
    PyASTVisitor,
)


class GraphIndexerMixin:
    """Mixin providing incremental file scanning, indexing, and disk persistence."""

    def build(self) -> Dict[str, Any]:
        """Scan project files incrementally using st_mtime and construct/update the AST graph."""
        if not self.nodes:
            self.load()

        old_nodes = self.nodes.copy()
        old_edges = list(self.edges)

        new_nodes: Dict[str, Dict[str, Any]] = {}
        new_edges: List[Dict[str, Any]] = []

        for root, dirs, files in os.walk(self.project_dir, followlinks=False):
            dirs[:] = [
                d for d in dirs
                if d not in IGNORE_DIRS
                and not os.path.islink(os.path.join(root, d))
            ]
            for file in files:
                path = Path(root) / file
                if path.is_symlink():
                    continue
                if path.suffix not in SUPPORTED_EXTENSIONS:
                    continue
                try:
                    rel_path = path.relative_to(self.project_dir).as_posix()
                    mtime = path.stat().st_mtime

                    # Incremental check: if file is in old_nodes and mtime is unchanged, reuse nodes/edges
                    if rel_path in old_nodes and old_nodes[rel_path].get("mtime") == mtime:
                        new_nodes[rel_path] = old_nodes[rel_path]
                        for nid, node in old_nodes.items():
                            if node.get("file") == rel_path or nid.startswith(f"{rel_path}::"):
                                new_nodes[nid] = node
                        for edge in old_edges:
                            ef, et = edge.get("from", ""), edge.get("to", "")
                            if ef == rel_path or ef.startswith(f"{rel_path}::") or et == rel_path or et.startswith(f"{rel_path}::"):
                                if edge not in new_edges:
                                    new_edges.append(edge)
                        continue

                    self.nodes = new_nodes
                    self.edges = new_edges
                    self._index_file(path, rel_path, mtime=mtime)
                except Exception:
                    continue

        self.nodes = new_nodes
        self.edges = new_edges
        self.save()
        return self.to_dict()

    def _index_file(self, abs_path: Path, rel_path: str, mtime: float = 0.0):
        file_node_id = rel_path
        text = abs_path.read_text(errors="ignore")
        mtime_val = mtime or (abs_path.stat().st_mtime if abs_path.exists() else 0.0)

        self.nodes[file_node_id] = {
            "id": file_node_id,
            "type": "file",
            "name": rel_path,
            "lines": len(text.splitlines()),
            "mtime": mtime_val,
        }

        if HAS_TREE_SITTER:
            if self._tree_sitter_index_file(abs_path, rel_path, text):
                return

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
    def _tree_sitter_index_file(self, abs_path: Path, rel_path: str, text: str) -> bool:
        """Parse file via Tree-Sitter when tree_sitter library is installed."""
        if not HAS_TREE_SITTER:
            return False
        try:
            ext = abs_path.suffix.lower()
            lang_name = {
                ".py": "python",
                ".js": "javascript",
                ".ts": "typescript",
                ".jsx": "javascript",
                ".tsx": "typescript",
                ".html": "html",
                ".go": "go",
                ".rs": "rust",
                ".cpp": "cpp",
                ".c": "c",
                ".java": "java",
            }.get(ext)
            if not lang_name:
                return False

            import tree_sitter
            try:
                import tree_sitter_languages
                lang = tree_sitter_languages.get_language(lang_name)
            except Exception:
                return False

            parser = tree_sitter.Parser()
            parser.set_language(lang)
            tree = parser.parse(bytes(text, "utf-8"))

            file_node_id = rel_path

            def _traverse(node):
                if node.type in ("function_declaration", "method_definition", "function_definition"):
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        func_name = text[name_node.start_byte:name_node.end_byte]
                        func_id = f"{rel_path}::{func_name}"
                        self.nodes[func_id] = {
                            "id": func_id,
                            "type": "function",
                            "name": func_name,
                            "file": rel_path,
                            "line_start": node.start_point[0] + 1,
                            "line_end": node.end_point[0] + 1,
                        }
                        self.edges.append({"from": file_node_id, "to": func_id, "type": "contains"})
                elif node.type in ("class_declaration", "class_definition", "struct_item"):
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        class_name = text[name_node.start_byte:name_node.end_byte]
                        class_id = f"{rel_path}::{class_name}"
                        self.nodes[class_id] = {
                            "id": class_id,
                            "type": "class",
                            "name": class_name,
                            "file": rel_path,
                            "line_start": node.start_point[0] + 1,
                            "line_end": node.end_point[0] + 1,
                        }
                        self.edges.append({"from": file_node_id, "to": class_id, "type": "contains"})

                for child in node.children:
                    _traverse(child)

            _traverse(tree.root_node)
            return True
        except Exception:
            return False

    def _regex_fallback(self, text: str, rel_path: str):
        file_node_id = rel_path

        # For HTML/HTM, parse text within <script> tags if present
        if rel_path.endswith((".html", ".htm")):
            script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL | re.IGNORECASE)
            parse_text = "\n".join(script_blocks) if script_blocks else text
        else:
            parse_text = text

        func_re = re.compile(
            r'^\s*(?:export\s+)?(?:async\s+)?(?:function|fn|def|func)\s+([a-zA-Z_]\w*)',
            re.MULTILINE
        )
        arrow_re = re.compile(
            r'^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z_]\w*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z_]\w*|\(\))\s*=>',
            re.MULTILINE
        )
        fn_expr_re = re.compile(
            r'^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z_]\w*)\s*=\s*(?:async\s*)?function',
            re.MULTILINE
        )
        class_re = re.compile(
            r'^\s*(?:export\s+)?(?:class|struct|type)\s+([a-zA-Z_]\w*)',
            re.MULTILINE
        )

        found_funcs = set()
        for m in func_re.finditer(parse_text):
            func_name = m.group(1)
            found_funcs.add(func_name)
            func_id = f"{rel_path}::{func_name}"
            lineno = text[:m.start()].count("\n") + 1 if parse_text is text else 1
            self.nodes[func_id] = {
                "id": func_id,
                "type": "function",
                "name": func_name,
                "file": rel_path,
                "line_start": lineno,
            }
            self.edges.append({"from": file_node_id, "to": func_id, "type": "contains"})

        for m in arrow_re.finditer(parse_text):
            func_name = m.group(1)
            if func_name in found_funcs:
                continue
            found_funcs.add(func_name)
            func_id = f"{rel_path}::{func_name}"
            lineno = text[:m.start()].count("\n") + 1 if parse_text is text else 1
            self.nodes[func_id] = {
                "id": func_id,
                "type": "function",
                "name": func_name,
                "file": rel_path,
                "line_start": lineno,
            }
            self.edges.append({"from": file_node_id, "to": func_id, "type": "contains"})

        for m in fn_expr_re.finditer(parse_text):
            func_name = m.group(1)
            if func_name in found_funcs:
                continue
            found_funcs.add(func_name)
            func_id = f"{rel_path}::{func_name}"
            lineno = text[:m.start()].count("\n") + 1 if parse_text is text else 1
            self.nodes[func_id] = {
                "id": func_id,
                "type": "function",
                "name": func_name,
                "file": rel_path,
                "line_start": lineno,
            }
            self.edges.append({"from": file_node_id, "to": func_id, "type": "contains"})

        for m in class_re.finditer(parse_text):
            class_name = m.group(1)
            class_id = f"{rel_path}::{class_name}"
            lineno = text[:m.start()].count("\n") + 1 if parse_text is text else 1
            self.nodes[class_id] = {
                "id": class_id,
                "type": "class",
                "name": class_name,
                "file": rel_path,
                "line_start": lineno,
            }
            self.edges.append({"from": file_node_id, "to": class_id, "type": "contains"})

    def update_file(self, abs_path: Path, rel_path: str) -> None:
        """Perform an incremental O(1) AST update for a single modified file."""
        if not self.nodes:
            if not self.load():
                self.build()
                return

        # 1. Remove nodes belonging to or inside rel_path
        to_remove_nodes = [
            nid for nid, n in self.nodes.items()
            if nid == rel_path or n.get("file") == rel_path or nid.startswith(f"{rel_path}::")
        ]
        for nid in to_remove_nodes:
            self.nodes.pop(nid, None)

        # 2. Remove edges associated with rel_path
        self.edges = [
            e for e in self.edges
            if not (e["from"] == rel_path or e["from"].startswith(f"{rel_path}::") or
                    e["to"] == rel_path or e["to"].startswith(f"{rel_path}::"))
        ]

        # 3. Re-index modified file if supported and exists
        if abs_path.exists() and abs_path.suffix in SUPPORTED_EXTENSIONS:
            try:
                self._index_file(abs_path, rel_path)
            except Exception:
                pass

        # 4. Save updated graph state
        self.save()

    def remove_file(self, rel_path: str) -> None:
        """Remove all nodes and edges referencing a deleted file."""
        to_remove_nodes = [
            nid for nid, n in self.nodes.items()
            if nid == rel_path or n.get("file") == rel_path or nid.startswith(f"{rel_path}::")
        ]
        for nid in to_remove_nodes:
            self.nodes.pop(nid, None)
        self.edges = [
            e for e in self.edges
            if not (e["from"] == rel_path or e["from"].startswith(f"{rel_path}::") or
                    e["to"] == rel_path or e["to"].startswith(f"{rel_path}::"))
        ]
        self.save()

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
