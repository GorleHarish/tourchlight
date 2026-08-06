"""
Flashlight Indexer — scans the project and builds a searchable symbol index.
"""

import re
from pathlib import Path

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
    ".egg-info",
}


import os

_PY_FUNC_RE = re.compile(r'^(?:async )?def\s+(\w+)\s*\(')
_PY_CLASS_RE = re.compile(r'^class\s+(\w+)')
_JS_FUNC_RE = re.compile(r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)')
_JS_CLASS_RE = re.compile(r'^(?:export\s+)?class\s+(\w+)')
_JS_ARROW_RE = re.compile(r'^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^\s=]+)\s*=>')
_TS_INTF_RE = re.compile(r'^(?:export\s+)?interface\s+(\w+)')
_RS_FUNC_RE = re.compile(r'^\s*(?:pub\s+)?fn\s+(\w+)')
_RS_STRUCT_RE = re.compile(r'^\s*(?:pub\s+)?(?:struct|enum)\s+(\w+)')
_GO_FUNC_RE = re.compile(r'^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(')
_GO_STRUCT_RE = re.compile(r'^type\s+(\w+)\s+struct')

class FileEntry:
    __slots__ = ("rel_path", "lines", "symbols", "imports", "size", "mtime")

    def __init__(self, rel_path: str, lines: list[str], symbols: list, imports: list[str], mtime: float = 0.0):
        self.rel_path = rel_path
        self.lines = lines
        self.symbols = symbols
        self.imports = imports
        self.size = len(lines)
        self.mtime = mtime


class SymbolIndex:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir.resolve()
        self.files: dict[str, FileEntry] = {}

    def build(self) -> int:
        old_files = self.files
        new_files: dict[str, FileEntry] = {}

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
                    rel = path.relative_to(self.project_dir).as_posix()
                    mtime = path.stat().st_mtime
                    if rel in old_files and old_files[rel].mtime == mtime:
                        new_files[rel] = old_files[rel]
                        continue

                    text = path.read_text(errors="ignore")
                    lines, symbols, imports = self._parse(text, path.suffix)
                    new_files[rel] = FileEntry(rel, lines, symbols, imports, mtime=mtime)
                except Exception:
                    continue
        self.files = new_files
        return len(self.files)


    def summary(self) -> str:
        total_files = len(self.files)
        total_syms = sum(len(e.symbols) for e in self.files.values())
        file_list = "\n".join(f"  {p}" for p in list(self.files.keys())[:50])
        if total_files > 50:
            file_list += f"\n  ... and {total_files - 50} more"
        return (
            f"Project: {self.project_dir.name}  |  "
            f"{total_files} files  |  {total_syms} symbols indexed\n"
            f"Files:\n{file_list}"
        )

    def _parse(self, text: str, suffix: str) -> tuple[list[str], list, list[str]]:
        lines = text.splitlines()
        symbols = []
        imports = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                continue
            if suffix == ".py":
                m = _PY_FUNC_RE.match(stripped)
                if m:
                    symbols.append((m.group(1), i, "function"))
                    continue
                m = _PY_CLASS_RE.match(stripped)
                if m:
                    symbols.append((m.group(1), i, "class"))
                    continue
                if stripped.startswith("import ") or stripped.startswith("from "):
                    imports.append(stripped)
            elif suffix in (".js", ".ts", ".jsx", ".tsx"):
                m = _JS_FUNC_RE.match(stripped) or _JS_ARROW_RE.match(stripped)
                if m:
                    symbols.append((m.group(1), i, "function"))
                    continue
                m = _JS_CLASS_RE.match(stripped) or _TS_INTF_RE.match(stripped)
                if m:
                    symbols.append((m.group(1), i, "class"))
                    continue
            elif suffix in (".rs",):
                m = _RS_FUNC_RE.match(stripped)
                if m:
                    symbols.append((m.group(1), i, "function"))
                    continue
                m = _RS_STRUCT_RE.match(stripped)
                if m:
                    symbols.append((m.group(1), i, "struct"))
                    continue
            elif suffix in (".go",):
                m = _GO_FUNC_RE.match(stripped)
                if m:
                    symbols.append((m.group(1), i, "function"))
                    continue
                m = _GO_STRUCT_RE.match(stripped)
                if m:
                    symbols.append((m.group(1), i, "struct"))
                    continue

        return lines, symbols, imports
