"""
Flashlight Indexer — scans the project and builds a searchable symbol index.

The index stores per-file:
  - Full path and size
  - Function / class / method names with line numbers
  - Import statements (used for cross-file relationship scoring)
  - First 30 lines (used for keyword density scoring)

Supported languages: Python, JavaScript/TypeScript, Go, Rust, Java, C/C++,
                     Ruby, C#, Swift, Kotlin, plus config files.
"""

import ast
import re
from pathlib import Path
from typing import Optional


SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".go", ".rs", ".java", ".cpp", ".c", ".h",
    ".rb", ".cs", ".swift", ".kt",
    ".md", ".toml", ".yaml", ".yml", ".json",
}

IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "env", "dist", "build", ".next", ".nuxt", "coverage",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "site-packages",
    ".egg-info", "context_manager_cli.egg-info",
}


class FileEntry:
    """Indexed metadata for a single file."""

    __slots__ = ("rel_path", "lines", "symbols", "imports", "size")

    def __init__(
        self,
        rel_path: str,
        lines: list[str],
        symbols: list[tuple[str, int, str]],   # (name, lineno, kind)
        imports: list[str],
    ):
        self.rel_path  = rel_path
        self.lines     = lines
        self.symbols   = symbols
        self.imports   = imports
        self.size      = len(lines)


class SymbolIndex:
    """
    Scans a project directory and builds a lightweight searchable index.

    Call .build() to rescan after file changes.
    Access .files for the index: {rel_path: FileEntry}
    """

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir.resolve()
        self.files: dict[str, FileEntry] = {}
        # NOTE: Do NOT call self.build() here as it is slow.
        # The caller must call it explicitly (ideally off-thread).

    # ── Public API ─────────────────────────────────────────────────────────────

    def build(self) -> int:
        """Scan the project and rebuild the index. Returns number of files indexed."""
        self.files = {}
        for path in sorted(self.project_dir.rglob("*")):
            if not path.is_file():
                continue
            if any(part in IGNORE_DIRS for part in path.parts):
                continue
            if path.suffix not in SUPPORTED_EXTENSIONS:
                continue
            try:
                text = path.read_text(errors="ignore")
                rel  = str(path.relative_to(self.project_dir))
                lines, symbols, imports = self._parse(text, path.suffix)
                self.files[rel] = FileEntry(rel, lines, symbols, imports)
            except Exception:
                continue
        return len(self.files)

    def summary(self) -> str:
        """One-line project summary injected into the system prompt."""
        total_files = len(self.files)
        total_syms  = sum(len(e.symbols) for e in self.files.values())
        file_list   = "\n".join(f"  {p}" for p in list(self.files.keys())[:50])
        if total_files > 50:
            file_list += f"\n  ... and {total_files - 50} more"
        return (
            f"Project: {self.project_dir.name}  |  "
            f"{total_files} files  |  {total_syms} symbols indexed\n"
            f"Files:\n{file_list}"
        )

    def symbol_list(self) -> str:
        """Compact symbol table for all indexed files."""
        lines = []
        for rel, entry in sorted(self.files.items()):
            if entry.symbols:
                names = ", ".join(f"{s[0]}({s[2][0]})" for s in entry.symbols[:8])
                lines.append(f"  {rel}: {names}")
        return "\n".join(lines)

    # ── Parsing ────────────────────────────────────────────────────────────────

    def _parse(
        self, text: str, ext: str
    ) -> tuple[list[str], list[tuple[str, int, str]], list[str]]:
        lines = text.splitlines()
        if ext == ".py":
            symbols, imports = self._parse_python(text)
        else:
            symbols, imports = self._parse_generic(lines)
        return lines, symbols, imports

    def _parse_python(self, text: str) -> tuple[list, list]:
        symbols: list[tuple[str, int, str]] = []
        imports: list[str] = []
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append((node.name, node.lineno, "function"))
                elif isinstance(node, ast.ClassDef):
                    symbols.append((node.name, node.lineno, "class"))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for alias in node.names:
                        imports.append(f"{mod}.{alias.name}")
        except SyntaxError:
            # Fall back to regex for files with syntax errors
            symbols, imports = self._parse_generic(text.splitlines())
        return symbols, imports

    def _parse_generic(self, lines: list[str]) -> tuple[list, list]:
        symbols: list[tuple[str, int, str]] = []
        imports: list[str] = []

        fn_re  = re.compile(
            r"^\s*(?:export\s+)?(?:async\s+)?(?:function|def|fn|func)\s+(\w+)"
            r"|^\s*(?:public|private|protected|static)(?:\s+\w+)*\s+(\w+)\s*\("
        )
        cls_re = re.compile(r"^\s*(?:export\s+)?(?:class|struct|interface|type|impl)\s+(\w+)")
        imp_re = re.compile(r"^\s*(?:import|require|use|include|from)\s+(.+)")

        for i, line in enumerate(lines, 1):
            m = fn_re.match(line)
            if m:
                name = m.group(1) or m.group(2)
                if name:
                    symbols.append((name, i, "function"))
                continue
            m = cls_re.match(line)
            if m:
                symbols.append((m.group(1), i, "class"))
                continue
            m = imp_re.match(line)
            if m:
                imports.append(m.group(1).strip()[:80])

        return symbols, imports
