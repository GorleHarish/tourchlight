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
    async with app.run_test():
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


@pytest.mark.anyio
async def test_message_card_copy_and_reuse_actions(monkeypatch):
    """Verify MessageCard copy and reuse actions work for user and assistant messages."""
    try:
        from textual.app import App
        from textual.widgets import TextArea

        from rlm_optimized.tui_widgets.transcript import MessageCard
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    copied = []

    def mock_copy(text: str) -> bool:
        copied.append(text)
        return True

    monkeypatch.setattr("rlm_optimized.tui_app.copy_to_clipboard", mock_copy)

    class DummyApp(App):
        def compose(self):
            yield TextArea(id="user-input")
            yield MessageCard("fix the bug in auth.py", role="user")
            yield MessageCard("Here is the fix", role="assistant")

    app = DummyApp()
    async with app.run_test():
        cards = app.query(MessageCard)
        assert len(cards) == 2
        user_card = cards[0]
        assistant_card = cards[1]

        # 1. Test Copy action on user message
        user_card.action_copy()
        assert "fix the bug in auth.py" in copied

        # 2. Test Reuse action on user message (loads into #user-input)
        user_card.action_reuse()
        input_widget = app.query_one("#user-input", TextArea)
        assert input_widget.text == "fix the bug in auth.py"

        # 3. Test Copy action on assistant message
        assistant_card.action_copy()
        assert "Here is the fix" in copied


@pytest.mark.anyio
async def test_message_card_duration_and_time_str():
    """Verify MessageCard duration formatting, empty user headers, and timestamp override."""
    try:
        from textual.app import App
        from textual.widgets import Static

        from rlm_optimized.tui_widgets.transcript import MessageCard
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class TimeApp(App):
        def compose(self):
            # User card: no duration or timestamp
            yield MessageCard("user prompt", role="user", id="card-user")
            # Assistant card with float duration
            yield MessageCard("assistant response", role="assistant", duration=2.36, id="card-asst-float")
            # Final card with str duration
            yield MessageCard("final answer", role="final", duration="1.8s", id="card-final-str")
            # Assistant card without duration
            yield MessageCard("plain assistant", role="assistant", id="card-plain")
            # Backward-compat timestamp override
            yield MessageCard("legacy card", role="assistant", timestamp="16:02", id="card-legacy")

    app = TimeApp()
    async with app.run_test() as pilot:
        user_card = app.query_one("#card-user", MessageCard)
        asst_float = app.query_one("#card-asst-float", MessageCard)
        final_str = app.query_one("#card-final-str", MessageCard)
        plain_asst = app.query_one("#card-plain", MessageCard)
        legacy_card = app.query_one("#card-legacy", MessageCard)

        # 1. User card has empty time string (no wall-clock timestamp)
        assert user_card._time_str() == ""
        user_time_static = user_card.query_one(".message-card-time", Static)
        assert str(user_time_static.content) == ""

        # 2. Assistant card with float duration formats to 1 decimal place ("2.4s")
        assert asst_float._time_str() == "2.4s"
        float_time_static = asst_float.query_one(".message-card-time", Static)
        assert str(float_time_static.content) == "2.4s"

        # 3. Final card with string duration preserves string
        assert final_str._time_str() == "1.8s"
        final_time_static = final_str.query_one(".message-card-time", Static)
        assert str(final_time_static.content) == "1.8s"

        # 4. Plain assistant without duration is empty
        assert plain_asst._time_str() == ""
        plain_time_static = plain_asst.query_one(".message-card-time", Static)
        assert str(plain_time_static.content) == ""

        # 5. Legacy timestamp override
        assert legacy_card._time_str() == "16:02"
        legacy_time_static = legacy_card.query_one(".message-card-time", Static)
        assert str(legacy_time_static.content) == "16:02"

        await pilot.pause()

