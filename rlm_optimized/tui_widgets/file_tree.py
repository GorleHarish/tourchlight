"""Git-aware file tree for the Torchlight TUI.

Phase 4: the explorer's ``DirectoryTree`` becomes a ``GitFileTree`` that
decorates changed paths with one-letter status codes from ``git status
--porcelain`` (``M`` modified, ``A`` added, ``D`` deleted, ``U`` conflict,
``??`` untracked). Files only — directories stay clean so the explorer
doesn't look noisy.

``parse_git_status_porcelain`` / ``normalize_status_code`` / ``git_status_for_tree``
are pure helpers (no Textual imports) so the porcelain parsing is trivially
unit-testable; ``GitFileTree`` is a thin ``DirectoryTree`` subclass that swaps
labels at ``_populate_node`` time.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterable
from pathlib import Path

from textual.widgets import DirectoryTree

try:
    from textual.widgets._directory_tree import DirEntry
except ImportError:  # pragma: no cover - fallback for other Textual versions
    from textual.widgets._tree import TreeNode as _Unused  # noqa: F401

    class DirEntry:  # type: ignore[no-redef]
        def __init__(self, path: Path) -> None:
            self.path = path


def normalize_status_code(code: str) -> str:
    """Collapse a two-column porcelain code (``XY``) to one display letter.

    ``??`` → ``??`` (untracked), conflict pairs (``UU``/``AA``/``DD``) → ``U``,
    staged column ``X`` + unstaged column ``Y`` collapse to whichever column is
    non-blank, preferring the worktree column (last char) when both are set.
    """
    if not code:
        return ""
    if code == "??":
        return "??"
    stripped = code.replace(" ", "")
    if stripped in ("UU", "AA", "DD"):
        return "U"
    if not stripped:
        return ""
    return stripped[-1]


def _unquote_c_style(path_part: str) -> str:
    """Undo git's C-style quoting for paths with special characters."""
    if not path_part.startswith('"') or not path_part.endswith('"'):
        return path_part
    inner = path_part[1:-1]
    out: list[str] = []
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch == "\\" and i + 1 < len(inner):
            nxt = inner[i + 1]
            out.append({'"': '"', "\\": "\\", "t": "\t", "n": "\n"}.get(nxt, nxt))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def parse_git_status_porcelain(output: str) -> dict[str, str]:
    """Parse ``git status --porcelain`` (v1 format) into ``{rel_path: code}``.

    Handles the two-column ``XY PATH`` layout, ``??`` untracked entries, and
    rename/copy lines (``R  old -> new`` — the destination path wins).
    """
    result: dict[str, str] = {}
    for raw in output.splitlines():
        line = raw.rstrip("\n")
        if len(line) < 3:
            continue
        code = line[:2]
        path_part = line[3:]
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1]
        path = _unquote_c_style(path_part.strip())
        if not path:
            continue
        result[path] = normalize_status_code(code)
    return result


def git_status_for_tree(root: str | Path) -> dict[str, str]:
    """Run ``git status --porcelain`` once for the given root.

    Returns ``{}`` when the root isn't inside a repo, when git is missing, or
    on any subprocess failure — the tree simply renders undecorated.
    """
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0:
            return {}
        return parse_git_status_porcelain(proc.stdout)
    except Exception:  # noqa: BLE001 - non-repo / missing git
        return {}


def _should_skip_dir(name: str) -> bool:
    """Check if a directory name should be skipped from exploration."""
    return name in (
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
        ".torchlight",
        ".pytest_cache",
    ) or name.startswith(".") or name.startswith(".torchlight_")


def _should_skip_path(path: Path) -> bool:
    """Filter out OS noise, cache directories, and internal state files."""
    name = path.name
    if _should_skip_dir(name) or name in (".DS_Store", ".context-memory", ".context-memory.json"):
        return True
    return False


class GitFileTree(DirectoryTree):
    """DirectoryTree whose file labels carry git status decorations."""

    def __init__(self, path: str | Path, **kwargs) -> None:
        super().__init__(str(path), **kwargs)
        self._git_status: dict[str, str] = {}

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Filter out hidden dotfiles and OS clutter from tree view."""
        return [p for p in paths if not _should_skip_path(p)]

    def refresh_git(self) -> None:
        """Re-run ``git status --porcelain`` for the current root."""
        try:
            self._git_status = git_status_for_tree(self.path)
        except Exception:  # noqa: BLE001, S110 - keep last-known status on failure
            pass

    def _rel_key(self, path: Path) -> str:
        try:
            key = os.path.relpath(str(path.resolve()), str(self.path.resolve()))
        except Exception:  # noqa: BLE001 - path outside root (symlinked tempdirs, etc.)
            return path.name
        key = key.replace(os.sep, "/")
        if key.startswith(".."):
            return path.name
        return key

    def _decorated_name(self, path: Path) -> str:
        """Prefix file labels with clean git status badges ([U] untracked, [M] modified, etc.); leave directories clean."""
        name = path.name
        if path.is_dir():
            return name
        code = self._git_status.get(self._rel_key(path))
        if code:
            disp_code = "U" if code == "??" else code
            return f"[{disp_code}] {name}"
        return name

    def _populate_node(
        self,
        node,
        content: Iterable[Path],  # type: ignore[override]
    ) -> None:
        node.remove_children()
        filtered = [p for p in content if not _should_skip_path(p)]
        for path in filtered:
            try:
                allow_expand = self._safe_is_dir(path)
                node.add(
                    self._decorated_name(path),
                    data=DirEntry(path),
                    allow_expand=allow_expand,
                )
            except OSError:
                continue
        node.expand()

