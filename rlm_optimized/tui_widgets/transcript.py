"""Rich transcript widgets for the Torchlight TUI.

Phase 1 of the UI-improvements plan: message cards (user / assistant /
final answer), the live streaming turn, and the bounded scroll container
that hosts the transcript.
"""

from __future__ import annotations

import datetime

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Markdown, Static

ROLE_LABELS = {
    "user": "YOU",
    "assistant": "ASSISTANT",
    "final": "ANSWER",
}


def estimate_token_count(text: str) -> int:
    """Cheap token estimate (≈3 chars/token, matching the engine heuristic)."""
    return max(1, len(text) // 3)


def card_meta_for(content: str) -> str:
    """Footer summary for an assistant card: word count + token estimate."""
    words = len(content.split())
    return f"{words:,} words · ≈{estimate_token_count(content):,} tok"


def timestamp_str() -> str:
    """Current time as a compact HH:MM label (local time, display only)."""
    return datetime.datetime.now().strftime("%H:%M")  # noqa: DTZ005


class MessageCard(Container):
    """A chat turn rendered as a rich Markdown card with header chrome.

    Styled with theme variables only (CSS-first, no ``styles.set``). The role
    is carried as a ``role-*`` class so callers can restyle per role.
    """

    DEFAULT_CSS = """
    MessageCard {
        height: auto;
        width: 1fr;
        layout: vertical;
        margin: 0 0 1 0;
        background: $surface;
        border: round $panel;
        border-left: thick $primary;
    }

    MessageCard.role-user {
        border-left: thick $accent;
    }

    MessageCard.role-assistant,
    MessageCard.role-final {
        border-left: thick $success;
    }

    MessageCard > Horizontal.message-card-header {
        height: 1;
        align: left middle;
        padding: 0 1;
        background: $panel;
    }

    Static.message-card-role {
        width: auto;
        color: $text-muted;
        text-style: bold;
    }

    Static.message-card-time {
        width: 1fr;
        color: $foreground-muted;
        text-align: right;
    }

    MessageCard > Markdown {
        height: auto;
        padding: 1 2 1 2;
        overflow-y: hidden;
    }

    MessageCard > Horizontal.message-card-footer {
        height: auto;
        padding: 0 1 1 2;
    }

    Static.message-card-meta {
        width: 1fr;
        color: $foreground-muted;
        text-align: right;
    }

    MessageCard:focus-within {
        border-left: tall $primary;
    }

    MessageCard:hover {
        background-tint: $foreground 3%;
    }
    """

    def __init__(
        self,
        content: str,
        *,
        role: str = "assistant",
        meta: str = "",
        timestamp: str | None = None,
        classes: str | None = None,
        id: str | None = None,
    ) -> None:
        role = role if role in ROLE_LABELS else "assistant"
        role_class = f"role-{role}"
        merged = f"{role_class} {classes}".strip() if classes else role_class
        super().__init__(classes=merged, id=id)
        self._content = content or ""
        self._role = role
        self._meta = meta or ""
        self._timestamp = timestamp

    def _role_label(self) -> str:
        return ROLE_LABELS.get(self._role, "ASSISTANT")

    def _time_str(self) -> str:
        return self._timestamp or timestamp_str()

    def compose(self) -> ComposeResult:
        with Horizontal(classes="message-card-header"):
            yield Static(self._role_label(), classes="message-card-role")
            yield Static(self._time_str(), classes="message-card-time")
        yield Markdown(self._content, classes="message-card-body")
        if self._meta:
            with Horizontal(classes="message-card-footer"):
                yield Static(self._meta, classes="message-card-meta")


class StreamingView(Container):
    """Live streaming turn: header, cheap body, and live meta footer.

    The body stays a ``Static`` (Rich markup) so high-frequency token updates
    never pay the cost of a full Markdown re-parse; the completed turn is
    re-rendered as a ``MessageCard`` when the stream finishes.
    """

    DEFAULT_CSS = """
    StreamingView {
        height: auto;
        width: 1fr;
        layout: vertical;
        margin: 0 0 1 0;
        background: $surface;
        border: round $panel;
        border-left: thick $success;
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

    Static.streaming-meta {
        width: 1fr;
        color: $foreground-muted;
        text-align: right;
    }

    Static.streaming-body {
        width: 1fr;
        height: auto;
        padding: 1 2 1 2;
        color: $foreground;
    }
    """

    def __init__(self, *, meta: str = "", id: str | None = None) -> None:
        super().__init__(classes="streaming-view", id=id)
        self._meta = meta
        self._body: Static | None = None
        self._meta_widget: Static | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(classes="streaming-header"):
            yield Static("▍", classes="streaming-live")
            yield Static("ASSISTANT", classes="streaming-role")
            self._meta_widget = Static(self._meta, classes="streaming-meta")
            yield self._meta_widget
        self._body = Static("", classes="streaming-body", markup=False)
        yield self._body

    def update_markup(self, markup: str) -> None:
        """Replace the streaming body with plain text (markup disabled)."""
        if self._body is not None:
            self._body.update(markup)

    def set_meta(self, meta: str) -> None:
        """Update the live meta footer (tps / tokens / latency)."""
        self._meta = meta
        if self._meta_widget is not None:
            self._meta_widget.update(meta)


class TranscriptView(VerticalScroll):
    """Bounded scroll container hosting the transcript.

    Encapsulates the 120-child DOM cap and auto-scroll so the App shell stays
    thin. The cap is tracked with an internal FIFO because Textual processes
    ``mount``/``remove`` messages asynchronously and ``children`` is not
    reliable mid-pump.

    Composed with ``id="chat-container"`` so existing selectors and tests keep
    working.
    """

    MAX_CHILDREN = 35

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cards: list = []

    def append_card(self, widget, *, scroll: bool = True) -> None:
        """Mount a card, prune the oldest when over the cap, and scroll."""
        if not self.is_attached:
            return
        self.mount(widget)
        self._cards.append(widget)
        while len(self._cards) > self.MAX_CHILDREN:
            oldest = self._cards.pop(0)
            try:
                oldest.remove()
            except Exception:  # noqa: BLE001, S110 - already detached, keep bounded
                pass
        if scroll:
            self.call_after_refresh(self.scroll_to_end)

    def scroll_to_end(self) -> None:
        """Scroll the transcript to the bottom without animation."""
        try:
            self.scroll_end(animate=False)
        except Exception:  # noqa: BLE001, S110 - not attached yet, ignore
            pass
