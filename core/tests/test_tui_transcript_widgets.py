"""Tests for Phase-1 transcript widgets (message cards, streaming, thinking)."""

import tempfile
from unittest.mock import MagicMock

import pytest


def test_estimate_token_count():
    from rlm_optimized.tui_widgets.transcript import estimate_token_count

    assert estimate_token_count("") == 1
    assert estimate_token_count("x" * 9) == 3


def test_card_meta_for():
    from rlm_optimized.tui_widgets.transcript import card_meta_for

    meta = card_meta_for("hello world")
    assert "words" in meta
    assert "tok" in meta


@pytest.mark.anyio
async def test_thinking_block_factory():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets import thinking_block as tb
        from rlm_optimized.tui_widgets.thinking_block import thinking_block
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"rlm_optimized not importable in this environment: {e}")

    class ThinkApp(App):
        def compose(self):
            yield thinking_block(
                "💭 Step 1 Reasoning", "[dim]thinking...[/dim]", collapsed=True
            )

    app = ThinkApp()
    async with app.run_test() as pilot:
        widget = app.query_one(".thinking-block")
        assert widget is not None
        assert "thinking-block" in widget.classes
        if tb.Collapsible is not None:
            assert isinstance(widget, tb.Collapsible)
        await pilot.pause()


@pytest.mark.anyio
async def test_message_card_composes():
    try:
        from textual.app import App
        from textual.widgets import Markdown

        from rlm_optimized.tui_widgets.transcript import MessageCard
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class CardApp(App):
        def compose(self):
            yield MessageCard(
                "# Hello\n\n```python\nx = 1\n```",
                role="assistant",
                meta="2 words · ≈1 tok",
            )

    app = CardApp()
    async with app.run_test() as pilot:
        cards = app.query(MessageCard)
        assert len(cards) == 1
        card = cards[0]
        assert card._role == "assistant"
        assert "role-assistant" in card.classes
        assert len(card.query(Markdown)) == 1
        await pilot.pause()


@pytest.mark.anyio
async def test_streaming_view_updates():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.transcript import StreamingView
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class StreamApp(App):
        def compose(self):
            yield StreamingView()

    app = StreamApp()
    async with app.run_test() as pilot:
        view = app.query_one(StreamingView)
        assert view._body is not None
        view.update_markup("[bold green]hi[/]")
        view.set_meta("24.0 tps · 120 tok")
        assert view._body.content is not None
        assert "hi" in str(view._body.content)
        await pilot.pause()


@pytest.mark.anyio
async def test_app_transcript_wiring():
    """Smoke test: the real app mounts MessageCards and drives the streaming view."""
    try:
        from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
        from rlm_optimized.tui_app import TorchlightApp
        from rlm_optimized.tui_widgets.transcript import MessageCard, StreamingView
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    engine = MagicMock(spec=RLMEngineOptimized)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10
    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    async with app.run_test() as pilot:
        container = app.query_one("#chat-container")
        assert len(container.query(MessageCard)) == 0

        container.append_card(MessageCard("hello user", role="user"))
        assert len(container.query(MessageCard)) == 1

        view = app._ensure_streaming_widget()
        assert isinstance(view, StreamingView)
        app._append_token("## partial")
        assert app._streaming_text == "## partial"

        app._remove_streaming()
        assert app._streaming_widget is None


@pytest.mark.anyio
async def test_transcript_view_prunes_over_cap():
    try:
        from textual.app import App
        from textual.widgets import Static

        from rlm_optimized.tui_widgets.transcript import TranscriptView
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class TApp(App):
        def compose(self):
            yield TranscriptView()

    app = TApp()
    async with app.run_test() as pilot:
        view = app.query_one(TranscriptView)
        for i in range(TranscriptView.MAX_CHILDREN + 15):
            view.append_card(Static(str(i)))
        assert len(view._cards) <= TranscriptView.MAX_CHILDREN
        await pilot.pause()
        await pilot.pause()
        assert len(view.children) <= TranscriptView.MAX_CHILDREN
