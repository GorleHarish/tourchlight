"""Flashlight AST indexing, beam block retrieval, and symbols preview for CLI session."""

from __future__ import annotations

import re
from typing import Optional
from rich.console import Console

from context_manager.cli.dashboard import ContextDashboard, ActionTracker
from context_manager.flashlight import Flashlight, SymbolIndex

console = Console()
dashboard = ContextDashboard()

_SMALL_CTX = 5000  # models at or below this limit get the trimmed pipeline


def _beam_budget(max_tokens: int) -> tuple[int, int]:
    """Return (max_beam_files, max_lines_per_file) for the given context size."""
    if max_tokens <= _SMALL_CTX:
        return 1, 50  # 1 file, 50 lines ≈ 500 tokens
    if max_tokens <= 9000:
        return 2, 80  # 2 files, 80 lines ≈ 1300 tokens
    return 3, 120  # default — full beam


class FlashlightMixin:
    """Provides Flashlight codebase indexing and beam retrieval for StreamingChatSession."""

    def _init_flashlight(self) -> None:
        console.print(
            f"[dim]◉ Flashlight scanning [cyan]{self._project_dir.name}[/cyan]...[/dim]",
            end=" ",
        )
        self._index = SymbolIndex(self._project_dir)
        self._light = Flashlight(self._index)
        # Override beam limits in the Flashlight instance
        import context_manager.flashlight.beam as _bm

        _bm.MAX_BEAM_FILES = self._beam_files
        _bm.MAX_LINES_PER_FILE = self._beam_lines
        total_syms = sum(len(e.symbols) for e in self._index.files.values())
        graph_info = ""
        try:
            from core.flashlight.graph_engine import get_project_graph

            graph = get_project_graph(str(self._project_dir))
            graph_info = f", graph: {len(graph.nodes)} nodes"
        except Exception:
            pass
        console.print(
            f"[dim]{len(self._index.files)} files, {total_syms} symbols"
            f"{graph_info} (beam: {self._beam_files}×{self._beam_lines}L)[/dim]"
        )

    def _rebuild_index(self) -> None:
        if self._index is None:
            self._init_flashlight()
            return
        console.print("[dim]◉ Flashlight reindexing...[/dim]", end=" ")
        n = self._index.build()
        total_syms = sum(len(e.symbols) for e in self._index.files.values())
        console.print(f"[dim]{n} files, {total_syms} symbols[/dim]")

    def _get_beam_block(self, query: str) -> str:
        if self._light is None:
            return ""
        return self._light.beam_block(query, max_files=self._beam_files)

    def _notify_file_touched(self, tool_name: str, content: str) -> None:
        if self._light is None:
            return

        if tool_name in ("READ_FILE", "WRITE_FILE", "read_file", "write_file"):
            m = re.search(r"📄\s*([\w/\.\-]+)|Written .+ to ([\w/\.\-]+)", content)
            if m:
                path = (m.group(1) or m.group(2) or "").strip()
                if path:
                    self._light.mark_active(path)

    def _flash_preview(self, query: str) -> None:
        if self._light is None:
            dashboard.print_warning("Flashlight not initialised.")
            return
        results = self._light.beam(query, max_files=self._beam_files)
        if not results:
            dashboard.print_info("Flashlight: no relevant files found.")
            return
        for r in results:
            syms = ", ".join(f"{s[0]}({s[2][0]})" for s in r.symbols[:5])
            console.print(f"  [cyan]◉[/cyan] [bold]{r.path}[/bold]  [dim]{r.reason}[/dim]")
            if syms:
                console.print(f"     [dim]{syms}[/dim]")
