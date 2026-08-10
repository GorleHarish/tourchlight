"""Tests for Phase-2 tool call cards (risk badge, status, timing, sections)."""

import tempfile
from unittest.mock import MagicMock

import pytest


def test_risk_for_tool():
    from rlm_optimized.tui_widgets.tool_card import risk_for_tool

    assert risk_for_tool("READ_FILE") == "auto"
    assert risk_for_tool("WRITE_FILE") == "confirm"
    assert risk_for_tool("RUN_COMMAND", {"command": "ls"}) == "auto"
    assert risk_for_tool("RUN_COMMAND", {"command": "rm -rf /"}) == "review"
    assert risk_for_tool("UNKNOWN_TOOL") == "confirm"


def test_summarize_args():
    from rlm_optimized.tui_widgets.tool_card import summarize_args

    assert summarize_args(None) == ""
    s = summarize_args({"path": "/tmp/a.py", "query": "def foo"})
    assert "path: /tmp/a.py" in s
    assert "query: def foo" in s

    long_val = summarize_args({"cmd": "x" * 300})
    assert "..." in long_val

    no_key = summarize_args({"foo": "bar", "baz": 1})
    assert "argument(s)" in no_key


def test_target_from_args_line_ranges():
    from rlm_optimized.tui_widgets.tool_card import ToolCallCard

    assert ToolCallCard._target_from_args({"path": "src/main.py", "start_line": 10, "end_line": 25}) == "src/main.py:L10-L25"
    assert ToolCallCard._target_from_args({"path": "src/main.py", "start_line": 10}) == "src/main.py:L10"
    assert ToolCallCard._target_from_args({"path": "src/main.py", "symbol": "foo_func"}) == "src/main.py:foo_func"
    assert ToolCallCard._target_from_args({"path": "src/main.py:10-25"}) == "src/main.py:10-25"


def test_truncate_output():
    from rlm_optimized.tui_widgets.tool_card import truncate_output

    short = "a\nb"
    assert truncate_output(short) == short

    text = "\n".join(f"line {i}" for i in range(50))
    out = truncate_output(text)
    assert "Truncated for UI Performance" in out
    assert len(out.splitlines()) == 41

    big = "x" * 20000
    out = truncate_output(big, max_lines=1000)
    assert len(out) <= 15000 + len("... [Output Truncated for UI Performance]")


@pytest.mark.anyio
async def test_tool_card_composes_with_header():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.tool_card import ToolCallCard
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class CardApp(App):
        def compose(self):
            yield ToolCallCard("READ_FILE", args={"path": "/tmp/x.py"})

    app = CardApp()
    async with app.run_test() as pilot:
        card = app.query_one(ToolCallCard)
        assert "risk-auto" in card.classes
        assert "READ_FILE" in str(card.query_one(".tool-card-name").content)
        badge = card.query_one(".risk-badge")
        assert "risk-auto" in badge.classes
        assert "AUTO" in str(badge.content)
        assert card._status == "running"
        assert "running" in card._status_widget.classes
        assert card._time_widget is not None
        await pilot.pause()


@pytest.mark.anyio
async def test_tool_card_complete_ok():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.tool_card import ToolCallCard
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class CardApp(App):
        def compose(self):
            yield ToolCallCard("READ_FILE", args={"path": "/tmp/x.py"})

    app = CardApp()
    async with app.run_test() as pilot:
        card = app.query_one(ToolCallCard)
        card.complete(
            result="OK: read /tmp/x.py",
            args={"path": "/tmp/x.py"},
            status="ok",
            elapsed_ms=500,
        )
        await pilot.pause()
        assert card._status == "ok"
        assert card._status_widget.content == "✓"
        assert {"tool-card-status", "ok"} <= card._status_widget.classes
        assert "status-ok" in card.classes
        badge = card.query_one(".risk-badge")
        assert badge.content == "✓ DONE"
        assert "risk-done" in badge.classes
        assert "500ms" in str(card._time_widget.content)
        body = card.query_one(".tool-card-body")
        assert "OK: read /tmp/x.py" in str(body.content)
        assert "Params" in str(body.content)
        await pilot.pause()


@pytest.mark.anyio
async def test_tool_card_complete_error_expands():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets import tool_card as tc
        from rlm_optimized.tui_widgets.tool_card import ToolCallCard
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class CardApp(App):
        def compose(self):
            yield ToolCallCard("RUN_COMMAND", args={"command": "pytest"})

    app = CardApp()
    async with app.run_test() as pilot:
        card = app.query_one(ToolCallCard)
        card.complete(result="Error: boom", args={"command": "pytest"}, status="error")
        await pilot.pause()
        assert card._status == "error"
        assert card._status_widget.content == "✗"
        assert "status-error" in card.classes
        badge = card.query_one(".risk-badge")
        assert badge.content == "✗ FAILED"
        assert "risk-error" in badge.classes
        if tc.Collapsible is not None:
            section = card.query_one(".tool-card-section")
            assert section.collapsed is False
        await pilot.pause()


@pytest.mark.anyio
async def test_tool_card_complete_denied():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.tool_card import ToolCallCard
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class CardApp(App):
        def compose(self):
            yield ToolCallCard("WRITE_FILE", args={"path": "/tmp/a.py"})

    app = CardApp()
    async with app.run_test() as pilot:
        card = app.query_one(ToolCallCard)
        card.complete(
            result="Action denied by user",
            args={"path": "/tmp/a.py"},
            status="denied",
        )
        await pilot.pause()
        assert card._status == "denied"
        assert card._status_widget.content == "⚠️"
        assert {"tool-card-status", "denied"} <= card._status_widget.classes
        assert "status-denied" in card.classes
        badge = card.query_one(".risk-badge")
        assert badge.content == "⚠️ DENIED"
        assert "risk-denied" in badge.classes
        await pilot.pause()


@pytest.mark.anyio
async def test_tool_card_risk_escalation():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.tool_card import ToolCallCard
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class CardApp(App):
        def compose(self):
            yield ToolCallCard("RUN_COMMAND")

    app = CardApp()
    async with app.run_test() as pilot:
        card = app.query_one(ToolCallCard)
        assert card._risk == "confirm"
        card.complete(args={"command": "rm -rf /tmp"}, result="done", status="ok")
        assert card._risk == "review"
        assert "risk-review" in card.classes
        assert "risk-review" in card.query_one(".risk-badge").classes


@pytest.mark.anyio
async def test_app_pending_card_wiring():
    """The streamed <tool_call> mounts a pending card completed by the step."""
    try:
        from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized, Step
        from rlm_optimized.tui_app import TorchlightApp
        from rlm_optimized.tui_widgets.tool_card import ToolCallCard
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    engine = MagicMock(spec=RLMEngineOptimized)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10
    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    async with app.run_test() as pilot:
        container = app.query_one("#chat-container")
        assert app._pending_tool_card is None

        app._append_token('<tool_call>{"name": "READ_FILE", "path": "/tmp/example.py"}')
        assert app._pending_tool_card is not None
        assert isinstance(app._pending_tool_card, ToolCallCard)
        assert app._pending_tool_name == "READ_FILE"

        step = Step(
            step_number=1,
            depth=0,
            action="tool",
            thinking="read the file",
            content="",
            result="OK: read /tmp/example.py",
            tool_name="READ_FILE",
            tool_args={"path": "/tmp/example.py"},
        )
        app._handle_step(step)

        assert app._pending_tool_card is None
        cards = container.query(ToolCallCard)
        assert len(cards) == 1
        assert cards[0]._status == "ok"
