"""AST knowledge graph queries, shortest path-finding, and subgraph traversal."""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class GraphTraversalMixin:
    """Mixin providing query evaluation, BFS path-finding, and subgraph formatting."""

    _MAX_SNIPPET_LINES = 5
    _MAX_QUERY_OUTPUT_LINES = 40

    def query(self, search_term: str, top_k: int = 5) -> str:
        """Search nodes matching search_term. Returns code snippets alongside names."""
        if not self.nodes:
            if not self.load():
                self.build()

        term = search_term.strip().lower().lstrip("@")
        if not term:
            return self.get_structure()
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
        output_lines = [f"Found {len(matches)} matching AST nodes for '{search_term}' (showing {len(capped)}):"]
        total_lines_used = 1

        for m in capped:
            ntype = m.get("type", "node").upper()
            nid = m["id"]
            file_path = m.get("file", nid)
            lstart = m.get("line_start", 1)
            sig = m.get("signature", "")
            doc = m.get("docstring", "")

            header = f"- `[{ntype}]` **{m.get('name', nid)}** (`{file_path}:L{lstart}`)"
            if sig:
                header += f"\n  Signature: `{sig}`"
            if doc:
                first_line = doc.split("\n")[0][:80]
                header += f"\n  Doc: _{first_line}_"

            # Extract code preview snippet
            snippet_lines = self._get_node_snippet(m)
            if snippet_lines:
                snippet_text = "\n".join(snippet_lines)
                ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
                header += f"\n  ```{ext}\n{snippet_text}\n  ```"

            output_lines.append(header)
            total_lines_used += header.count("\n") + 1
            if total_lines_used >= self._MAX_QUERY_OUTPUT_LINES:
                output_lines.append(f"... (truncated to {self._MAX_QUERY_OUTPUT_LINES} lines max)")
                break

        output_lines.append(f'  → Use READ_FILE("path:Symbol") for full body, or SEARCH_AST(action="subgraph") for dependencies.')
        return "\n".join(output_lines)

    def _get_node_snippet(self, node: Dict[str, Any]) -> List[str]:
        """Extract up to _MAX_SNIPPET_LINES lines for preview in graph query."""
        try:
            rel_file = node.get("file")
            if not rel_file:
                return []
            abs_p = self.project_dir / rel_file
            if not abs_p.exists():
                return []
            lines = abs_p.read_text(errors="ignore").splitlines()
            start = max(0, int(node.get("line_start", 1)) - 1)
            end = min(len(lines), start + self._MAX_SNIPPET_LINES)
            return lines[start:end]
        except Exception:
            return []

    def find_path(self, source_name: str, target_name: str, max_depth: int = 10) -> str:
        """Find relationship path between source and target symbols."""
        if not source_name or not target_name:
            return "Path search requires both source and target names."

        if not self.nodes:
            if not self.load():
                self.build()

        s_term = source_name.strip().lower().lstrip("@")
        t_term = target_name.strip().lower().lstrip("@")

        def _find_matches(term: str) -> List[str]:
            exact_id = [nid for nid in self.nodes if nid.lower() == term]
            if exact_id:
                return exact_id
            exact_name = [nid for nid, n in self.nodes.items() if n.get("name", "").lower() == term]
            if exact_name:
                return exact_name
            return [
                nid for nid, n in self.nodes.items()
                if term in nid.lower() or term in n.get("name", "").lower()
            ]

        src_nodes = _find_matches(s_term)
        tgt_nodes = _find_matches(t_term)

        if not src_nodes or not tgt_nodes:
            return f"Path search failed: '{source_name}' or '{target_name}' not found in AST index."

        adj: Dict[str, List[Tuple[str, str]]] = {}
        for edge in self.edges:
            f, t, etype = edge["from"], edge["to"], edge["type"]
            adj.setdefault(f, []).append((t, etype))

        from collections import deque
        queue: deque = deque()
        queue.append((src_nodes[0], [src_nodes[0]], 0))
        visited = {src_nodes[0]}
        target_set = set(tgt_nodes)
        target_names = {n.get("name", "").lower() for nid, n in self.nodes.items() if nid in target_set}
        target_names.add(t_term)

        while queue:
            curr, path, depth = queue.popleft()
            curr_clean = curr.split("::")[-1].lower() if "::" in curr else curr.lower()
            if curr in target_set or curr_clean in target_names or any(curr.endswith("::" + tn) for tn in target_names):
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
        term = symbol_or_path.strip().lower().lstrip("@")
        # 1. Exact node ID match
        for nid in self.nodes:
            if nid.lower() == term:
                matched_id = nid
                break
        # 2. Exact symbol name match
        if not matched_id:
            for nid, n in self.nodes.items():
                if n.get("name", "").lower() == term:
                    matched_id = nid
                    break
        # 3. Partial match fallback
        if not matched_id:
            for nid, n in self.nodes.items():
                if term in nid.lower() or term in n.get("name", "").lower():
                    matched_id = nid
                    break

        if not matched_id:
            return f"Symbol or path '{symbol_or_path}' not found in AST graph."

        connected_edges = []
        seen_edges = set()
        current_level = {matched_id}
        visited_nodes = {matched_id}

        for _ in range(max_depth):
            next_level = set()
            for e in self.edges:
                edge_key = (e["from"], e["to"], e["type"])
                if edge_key in seen_edges:
                    continue
                if e["from"] in current_level or e["to"] in current_level:
                    connected_edges.append(e)
                    seen_edges.add(edge_key)
                    if e["from"] not in visited_nodes:
                        next_level.add(e["from"])
                        visited_nodes.add(e["from"])
                    if e["to"] not in visited_nodes:
                        next_level.add(e["to"])
                        visited_nodes.add(e["to"])
            current_level = next_level
            if not current_level:
                break

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
            if not self.load() or not self.nodes:
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
