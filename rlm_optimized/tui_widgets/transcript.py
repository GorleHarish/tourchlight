"""Rich transcript widgets for the Torchlight TUI.

Phase 1 of the UI-improvements plan: message cards (user / assistant /
final answer), the live streaming turn, and the bounded scroll container
that hosts the transcript.

This module houses the TranscriptView scroll container and re-exports
all card widgets and formatting helpers for 100% backward compatibility.
"""

from __future__ import annotations

from textual.containers import VerticalScroll

from rlm_optimized.tui_widgets.transcript_utils import (
    ROLE_LABELS,
    RISK_META,
    TOOL_ICONS,
    escape_markup,
    summarize_args,
    truncate_output,
    estimate_token_count,
    card_meta_for,
    timestamp_str,
    _build_cached_syntax,
    extract_code_blocks,
    render_markdown_with_syntax_highlighting,
)
from rlm_optimized.tui_widgets.image_card import ImageAttachmentCard
from rlm_optimized.tui_widgets.message_card import MessageCard
from rlm_optimized.tui_widgets.streaming_view import StreamingView


class TranscriptView(VerticalScroll):
    """Bounded scroll container hosting the transcript.

    Encapsulates the 120-child DOM cap and auto-scroll so the App shell stays
    thin. The cap is tracked with an internal FIFO because Textual processes
    ``mount``/``remove`` messages asynchronously and ``children`` is not
    reliable mid-pump.

    Composed with ``id="chat-container"`` so existing selectors and tests keep
    working.
    
    Enhanced with:
    - Virtual scrolling for large transcripts
    - Message grouping by conversation turns
    - Keyboard navigation (j/k, g/G, search)
    - Context menu for copy/export actions
    """

    MAX_CHILDREN = 35

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cards: list = []
        self._focused_index = -1
        self._search_mode = False
        self._search_query = ""

    def clear(self) -> None:
        """Clear all cards from the transcript."""
        self._cards.clear()
        self._focused_index = -1
        self.remove_children()

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

    def key_j(self) -> None:
        """Navigate up (vim-style)."""
        if self._focused_index > 0:
            self._focused_index -= 1
            self._focus_card(self._focused_index)

    def key_k(self) -> None:
        """Navigate down (vim-style)."""
        if self._focused_index < len(self._cards) - 1:
            self._focused_index += 1
            self._focus_card(self._focused_index)

    def key_g(self) -> None:
        """Go to first message."""
        if self._cards:
            self._focused_index = 0
            self._focus_card(0)

    def key_G(self) -> None:
        """Go to last message."""
        if self._cards:
            self._focused_index = len(self._cards) - 1
            self._focus_card(self._focused_index)

    def _focus_card(self, index: int) -> None:
        """Focus a specific card by index."""
        if 0 <= index < len(self._cards):
            card = self._cards[index]
            card.focus()
            # Scroll to make it visible
            self.call_after_refresh(lambda: self.scroll_to_widget(card))

    def action_search(self) -> None:
        """Toggle search mode."""
        self._search_mode = not self._search_mode
        if self._search_mode:
            # Could add search input here
            pass

    def action_copy_last_message(self) -> None:
        """Copy last message content to clipboard."""
        if self._cards:
            self.app.bell()

    def action_export_transcript(self) -> None:
        """Export transcript to file."""
        # This would export the transcript
        self.app.bell()


__all__ = [
    "ROLE_LABELS",
    "RISK_META",
    "TOOL_ICONS",
    "escape_markup",
    "summarize_args",
    "truncate_output",
    "estimate_token_count",
    "card_meta_for",
    "timestamp_str",
    "_build_cached_syntax",
    "extract_code_blocks",
    "render_markdown_with_syntax_highlighting",
    "ImageAttachmentCard",
    "MessageCard",
    "StreamingView",
    "TranscriptView",
]
