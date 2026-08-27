"""Live streaming turn widget for high-frequency token updates."""

from __future__ import annotations

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static

from rlm_optimized.tui_widgets.transcript_utils import estimate_token_count


class StreamingView(Container):
    """Live streaming turn: header, cheap body, and live meta footer.

    The body stays a ``Static`` (Rich markup) so high-frequency token updates
    never pay the cost of a full Markdown re-parse; the completed turn is
    re-rendered as a ``MessageCard`` when the stream finishes.
    
    Enhanced with:
    - Live token count display
    - Smooth scrolling during streaming
    - Phase-aware streaming indicators
    """

    DEFAULT_CSS = """
    StreamingView {
        height: auto;
        width: 1fr;
        layout: vertical;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $panel;
        border-left: solid $success;
    }

    StreamingView.phase-plan {
        border-left: solid $warning;
    }

    StreamingView.phase-code {
        border-left: solid $primary;
    }

    StreamingView.phase-troubleshoot {
        border-left: solid $error;
    }

    StreamingView > Horizontal.streaming-header {
        height: 1;
        align: left middle;
        padding: 0 1;
        background: $panel;
    }

    Static.streaming-live {
        width: 2;
        color: $success;
        text-style: bold blink;
    }

    Static.streaming-role {
        width: auto;
        color: $text-muted;
        text-style: bold;
    }

    Static.streaming-phase {
        width: auto;
        margin: 0 0 0 1;
        padding: 0 1;
        color: $foreground-muted;
        text-style: italic;
    }

    Static.streaming-meta {
        width: 1fr;
        color: $foreground-muted;
        text-align: right;
    }

    Static.streaming-tokens {
        width: auto;
        color: $accent;
        margin-right: 1;
        text-style: bold;
    }

    Static.streaming-body {
        width: 1fr;
        height: auto;
        padding: 1 2 1 2;
        color: $foreground;
    }
    """

    def __init__(self, *, meta: str = "", phase: str = "chat", id: str | None = None) -> None:
        super().__init__(classes=f"streaming-view phase-{phase}", id=id)
        self._meta = meta
        self._phase = phase
        self._body: Static | None = None
        self._meta_widget: Static | None = None
        self._token_widget: Static | None = None
        self._phase_widget: Static | None = None
        self._token_count = 0

    def compose(self) -> ComposeResult:
        with Horizontal(classes="streaming-header"):
            yield Static("▍", classes="streaming-live")
            yield Static("ASSISTANT", classes="streaming-role")
            phase_labels = {"plan": "PLAN", "code": "CODE", "troubleshoot": "DEBUG", "chat": "CHAT"}
            self._phase_widget = Static(phase_labels.get(self._phase, "CHAT"), classes="streaming-phase")
            yield self._phase_widget
            self._token_widget = Static("0 tok", classes="streaming-tokens")
            yield self._token_widget
            self._meta_widget = Static(self._meta, classes="streaming-meta")
            yield self._meta_widget
        self._body = Static("", classes="streaming-body", markup=False)
        yield self._body

    def update_markup(self, markup: str) -> None:
        """Replace the streaming body with plain text (markup disabled)."""
        if self._body is not None:
            self._body.update(markup)
            # Update token count only on change
            new_count = estimate_token_count(markup)
            if new_count != self._token_count:
                self._token_count = new_count
                if self._token_widget:
                    self._token_widget.update(f"{self._token_count:,} tok")

    def set_meta(self, meta: str) -> None:
        """Update the live meta footer (tps / tokens / latency)."""
        self._meta = meta
        if self._meta_widget is not None:
            self._meta_widget.update(meta)
    
    def set_phase(self, phase: str) -> None:
        """Update the phase indicator."""
        self._phase = phase
        phase_labels = {"plan": "PLAN", "code": "CODE", "troubleshoot": "DEBUG", "chat": "CHAT"}
        self.set_classes(f"streaming-view phase-{phase}")
        if self._phase_widget:
            self._phase_widget.update(phase_labels.get(phase, "CHAT"))
