"""Trajectory rail for the Torchlight TUI.

Phase 2: a collapsed, status-colored rail pinned to the right edge of the
transcript. Every tool call adds a dot; dots flip from ``running`` to
``ok`` / ``error`` / ``denied`` as the engine completes each step, yielding a
glanceable vertical trace of the agent trajectory.

Styled with theme variables only (CSS-first, no ``styles.set``).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

DOT_GLYPHS = {
    "running": "⏳",
    "ok": "●",
    "error": "✗",
    "denied": "○",
}

MAX_DOTS = 80


class TrajectoryRail(Vertical):
    """Vertical spine of tool-outcome dots next to the transcript.

    ``add_pending`` appends a blinking running dot; ``complete`` flips the
    most recent pending dot to its final status. Dots are pruned FIFO to
    keep the DOM bounded (mirrors the transcript's 120-child cap).
    """

    DEFAULT_CSS = """
    TrajectoryRail {
        width: 4;
        height: 100%;
        background: $background;
        border-left: solid $panel;
        padding: 0 0 0 0;
        overflow-y: auto;
    }

    TrajectoryRail > Static.rail-header {
        width: 1fr;
        height: 1;
        content-align: center middle;
        color: $text-muted;
        text-style: bold;
    }

    TrajectoryRail > Static.rail-dot {
        width: 1fr;
        height: 2;
        content-align: center top;
    }

    Static.rail-dot.running {
        color: $accent;
        text-style: bold blink;
    }

    Static.rail-dot.ok {
        color: $success;
    }

    Static.rail-dot.error {
        color: $error;
        text-style: bold;
    }

    Static.rail-dot.denied {
        color: $warning;
        text-style: bold;
    }
    """

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(classes="trajectory-rail", id=id)
        self._dots: list[Static] = []

    def compose(self) -> ComposeResult:
        header = Static("⛓", classes="rail-header")
        header.tooltip = "Tool trajectory"
        yield header

    def add_pending(self, tool_name: str = "") -> None:
        """Append a running dot for a newly streamed/started tool call."""
        dot = Static(DOT_GLYPHS["running"] + "\n│", classes="rail-dot running")
        dot.tooltip = tool_name or "tool"
        if self.is_attached:
            self.mount(dot)
        self._dots.append(dot)
        self._prune()
        self.call_after_refresh(self._scroll_to_end)

    def _scroll_to_end(self) -> None:
        try:
            self.scroll_end(animate=False)
        except Exception:  # noqa: BLE001, S110 - not attached yet, ignore
            pass

    def complete(self, status: str = "ok") -> None:
        """Flip the most recent pending dot to a terminal status."""
        if not self._dots:
            return
        status = status if status in DOT_GLYPHS else "ok"
        dot = self._dots[-1]
        dot.update(f"{DOT_GLYPHS[status]}\n│")
        dot.set_classes(f"rail-dot {status}")

    def clear(self) -> None:
        """Remove all dots (called on transcript clear/reset)."""
        for dot in list(self._dots):
            try:
                dot.remove()
            except Exception:  # noqa: BLE001, S110 - already detached
                pass
        self._dots.clear()

    def _prune(self) -> None:
        while len(self._dots) > MAX_DOTS:
            oldest = self._dots.pop(0)
            try:
                oldest.remove()
            except Exception:  # noqa: BLE001, S110 - already detached
                pass
