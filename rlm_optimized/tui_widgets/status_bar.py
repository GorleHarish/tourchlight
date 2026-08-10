"""Consolidated status bar for the Torchlight TUI.

Phase 5 (UX Overhaul): state-aware single-row footer.

Display modes:
  • DISCONNECTED  → ``SYSTEM: IDLE │ ○ Offline │ ^M Connect Model │ ^B Sidebar``
  • IDLE          → ``SYSTEM: IDLE │ ● Model │ Context: ▓▓░░ 24% │ ^⏎ Send │ ^B Sidebar``
  • WORKING       → ``SYSTEM: GENERATING │ ● Model │ ▓▓▓▓ 45% │ Speed: 42 t/s │ ^C Stop``

Design rules:
  - Speed metric is hidden (not zeroed) when idle or disconnected.
  - ``$error`` reserved for actual runtime errors, never for offline state.
  - Server ON/OFF indicator uses ``$success`` / ``$foreground-muted``.
  - All layout is CSS-first; no ``styles.set`` calls.

``gauge_markup`` / ``build_status_segments`` remain pure (no Textual imports)
so the fill math is trivially unit-testable.
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

GAUGE_WIDTH = 14


def gauge_markup(pct: float, width: int = GAUGE_WIDTH) -> str:
    """Rich-markup a proportional context gauge: ``███░░░`` blocks + color.

    Color escalates green (<50%) → yellow (<75%) → red (≥75%).
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
    task_progress: str = "",
) -> dict[str, str]:
    """Build the per-segment Rich markup for the status bar.

    Segments:
      ``sb-state``  — phase badge + server status indicator
      ``sb-model``  — model name (muted; hidden when offline)
      ``sb-gauge``  — proportional block bar + % (hidden when offline)
      ``sb-task``   — live task progress pill
      ``sb-tps``    — token speed (hidden when not generating)
      ``sb-tokens`` — token count (hidden when offline)
      ``sb-errors`` — error counter (always shown when > 0)
      ``sb-git``    — git branch
    """
    badge = STATE_BADGES.get(state, f"[bold cyan]{escape(state)}[/]")

    # Server status — use muted gray for offline (NOT red)
    is_cloud = port <= 0
    if is_cloud:
        srv = "[bold green]CLOUD[/]"
    elif server_online:
        srv = f"[bold green]●[/] [dim]port {port}[/]"
    else:
        srv = "[dim]○ Offline[/]"

    # TPS — only show when actively generating; hide entirely when idle
    if tps > 0 and is_running:
        tps_str = f"[bold cyan]{tps:.1f} t/s[/]"
    elif is_running:
        tps_str = "[dim]calculating…[/]"
    else:
        tps_str = ""  # hidden when idle — not "-- tps"

    ctx = f"{int(tokens):,}/{int(ctx_max):,}" if ctx_max > 0 else ""
    err_str = f"✗ [bold red]{errors}[/]" if errors else ""
    git_str = f"[magenta]{escape(branch)}[/]" if branch else ""

    # Model segment — only when connected
    model_str = f"[bold]{escape(model)}[/]" if (server_online or is_cloud) and model else ""

    # Gauge — only when connected
    gauge_str = (
        f"{gauge_markup(pct)} [dim]{int(pct)}%[/]"
        if (server_online or is_cloud) and ctx_max > 0
        else ""
    )

    task_str = f"[bold yellow]🎯 {escape(task_progress)}[/]" if task_progress else ""

    return {
        "sb-state": f"{badge} [dim]│[/] {srv}",
        "sb-model": model_str,
        "sb-gauge": gauge_str,
        "sb-task": task_str,
        "sb-tps": tps_str,
        "sb-tokens": ctx,
        "sb-errors": err_str,
        "sb-git": git_str,
    }


class StatusBar(Horizontal):
    """Single-row consolidated status bar.

    Every segment is a ``Static`` updated via ``update_status``; the widget
    never touches ``styles.set`` — all layout comes from DEFAULT_CSS.
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
        color: $foreground-muted;
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
        yield Static("", id="sb-task", classes="sb-segment")
        yield Static("", id="sb-tps", classes="sb-segment")
        yield Static("", id="sb-tokens", classes="sb-segment")
        yield Static("", id="sb-errors", classes="sb-segment")
        yield Static("", id="sb-spacer", classes="sb-spacer")
        yield Static("", id="sb-git", classes="sb-segment")

    def update_status(self, **kwargs) -> None:
        """Apply ``build_status_segments`` to the live segments.

        Empty strings cause the segment to be hidden (width: auto → 0).
        """
        segments = build_status_segments(**kwargs)
        for seg_id, markup in segments.items():
            try:
                widget = self.query_one(f"#{seg_id}", Static)
                widget.update(markup)
                # Hide segment entirely when empty to save space
                widget.display = bool(markup.strip())
            except Exception:  # noqa: BLE001, S110 — not yet attached
                pass
