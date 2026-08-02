"""Consolidated status bar for the Torchlight TUI.

Phase 4: one glanceable row that replaces the scattered HUD badges and the
plain-text context meter —
``model ▸ phase ▸ [context gauge ████░ 62%] ▸ TPS ▸ tokens ▸ errors ▸ git``.

The context gauge is a real proportional block-art bar whose color escalates
through green → yellow → red as the window fills (Rich named colors, matching
the existing ``diff_view`` convention). Layout stays CSS-first: no
``styles.set``, no hardcoded hex.

``gauge_markup`` / ``build_status_segments`` are pure helpers (no Textual
imports) so the fill math and segment formatting are trivially unit-testable.
"""

from __future__ import annotations

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

STATE_BADGES = {
    "IDLE": "[bold green]IDLE[/]",
    "THINKING": "[bold magenta]THINKING...[/]",
    "CRITIQUING": "[bold yellow]🔍 CRITIQUING...[/]",
    "REFINED": "[bold green]✨ REFINED[/]",
    "TOOL": "[bold cyan]EXECUTING TOOL[/]",
    "TOOL_DONE": "[bold green]TOOL DONE[/]",
    "TOOL_DENIED": "[bold red]TOOL DENIED[/]",
    "WAITING_APPROVAL": "[bold yellow]WAITING APPROVAL[/]",
    "SUBAGENT": "[bold purple]SUBAGENT[/]",
}

GAUGE_WIDTH = 16


def gauge_markup(pct: float, width: int = GAUGE_WIDTH) -> str:
    """Rich-markup a proportional context gauge: ``███░░░`` blocks + color.

    Returns the filled/empty block string (no percentage label). The color
    escalates green (<50%) → yellow (<75%) → red (≥75%).
    """
    pct = min(100.0, max(0.0, float(pct)))
    filled = round(pct / 100.0 * width)
    bar = "█" * filled + "░" * (width - filled)
    color = "green" if pct < 50 else "yellow" if pct < 75 else "red"
    return f"[bold {color}]{bar}[/]"


def build_status_segments(
    *,
    state: str = "IDLE",
    model: str = "",
    pct: float = 0.0,
    tokens: int = 0,
    ctx_max: int = 0,
    tps: float = 0.0,
    errors: int = 0,
    branch: str = "",
    port: int = 0,
    server_online: bool = False,
    is_running: bool = False,
) -> dict[str, str]:
    """Build the per-segment Rich markup for the status bar.

    Segments: ``sb-state`` (phase + server), ``sb-model``, ``sb-gauge``
    (proportional bar + %), ``sb-tps``, ``sb-tokens``, ``sb-errors``,
    ``sb-git``. Pure function — no widget access.
    """
    badge = STATE_BADGES.get(state, f"[bold cyan]{escape(state)}[/]")
    if port <= 0:
        srv = "[bold green]CLOUD[/]"
    else:
        srv = (
            f"[bold green]ON:{port}[/]" if server_online else f"[bold red]OFF:{port}[/]"
        )

    if tps > 0:
        tps_str = f"[cyan]{tps:.1f} tps[/]"
    elif is_running:
        tps_str = "[dim]tps…[/]"
    else:
        tps_str = "[dim]-- tps[/]"

    ctx = f"{int(tokens):,}/{int(ctx_max):,}"
    err_str = f"✗ [bold red]{errors}[/]" if errors else "[dim]✗ 0[/]"
    git_str = f"[magenta]{escape(branch)}[/]" if branch else "[dim]no-git[/]"

    return {
        "sb-state": f"{badge} │ {srv}",
        "sb-model": escape(model),
        "sb-gauge": f"{gauge_markup(pct)} [bold yellow]{int(pct)}%[/]",
        "sb-tps": tps_str,
        "sb-tokens": f"[bold yellow]{ctx}[/]",
        "sb-errors": err_str,
        "sb-git": git_str,
    }


class StatusBar(Horizontal):
    """Single-row consolidated status bar (Phase 4).

    Hosted where the old text meter lived (``#context-meter-bar``). Every
    segment is a ``Static`` updated via ``update_status``; the widget never
    touches ``styles.set`` — all layout comes from DEFAULT_CSS.
    """

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $surface;
        border-top: solid $panel;
        padding: 0 1;
    }

    StatusBar > Static.sb-segment {
        width: auto;
        height: 1;
        margin-right: 2;
        text-style: bold;
        text-overflow: ellipsis;
    }

    StatusBar > Static.sb-model {
        color: $text-muted;
    }

    StatusBar > Static.sb-spacer {
        width: 1fr;
        height: 1;
    }
    """

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(classes="status-bar", id=id)

    def compose(self) -> ComposeResult:
        yield Static("", id="sb-state", classes="sb-segment")
        yield Static("", id="sb-model", classes="sb-segment sb-model")
        yield Static("", id="sb-gauge", classes="sb-segment")
        yield Static("", id="sb-tps", classes="sb-segment")
        yield Static("", id="sb-tokens", classes="sb-segment")
        yield Static("", id="sb-errors", classes="sb-segment")
        yield Static("", id="sb-spacer", classes="sb-spacer")
        yield Static("", id="sb-git", classes="sb-segment")

    def update_status(self, **kwargs) -> None:
        """Apply ``build_status_segments`` to the live segments."""
        segments = build_status_segments(**kwargs)
        for seg_id, markup in segments.items():
            try:
                widget = self.query_one(f"#{seg_id}", Static)
                widget.update(markup)
            except Exception:  # noqa: BLE001, S110 - not attached yet
                pass
