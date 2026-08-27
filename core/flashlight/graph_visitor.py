"""AST and source visitor implementations for Torchlight Knowledge Graph."""

from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional

IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "env", "dist", "build", ".next", ".nuxt", "coverage",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "site-packages",
    ".egg-info", ".torchlight", "graphify-out",
    "models", "llama-cpp-turboquant", "llama.cpp",
}

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".html", ".htm", ".css",
    ".go", ".rs", ".java", ".cpp", ".c", ".h",
    ".rb", ".cs", ".kt",
}

try:
    import tree_sitter
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False


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
        posargs = [arg.arg for arg in getattr(node.args, "posonlyargs", [])]
        normargs = [arg.arg for arg in node.args.args]
        kwonly = [arg.arg for arg in getattr(node.args, "kwonlyargs", [])]
        args = posargs + normargs
        if getattr(node.args, "vararg", None):
            args.append(f"*{node.args.vararg.arg}")
        args.extend(kwonly)
        if getattr(node.args, "kwarg", None):
            args.append(f"**{node.args.kwarg.arg}")
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
