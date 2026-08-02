"""Per-step thinking blocks for the Torchlight TUI.

Phase 1 of the UI-improvements plan: one ``Collapsible`` per reasoning step,
auto-expanded while streaming and collapsed once the step completes.
"""

from __future__ import annotations

from textual.widgets import Static

try:
    from textual.widgets import Collapsible
except ImportError:  # pragma: no cover - older Textual
    Collapsible = None


def thinking_block(title: str, body: str, *, collapsed: bool = True):
    """Build a per-step thinking ``Collapsible``.

    Falls back to a plain ``Static`` when ``Collapsible`` is unavailable so the
    transcript never hard-fails on older Textual versions.

    Args:
        title: Collapsible title (Rich markup allowed).
        body: Reasoning body (Rich markup allowed; callers should escape).
        collapsed: Whether the block starts collapsed.
    """
    if Collapsible is None:  # pragma: no cover - older Textual
        return Static(body, classes="thinking-block")
    return Collapsible(
        Static(body, classes="thinking-block-body"),
        title=title,
        collapsed=collapsed,
        classes="thinking-block",
    )
