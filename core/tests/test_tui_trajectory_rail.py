"""Tests for Phase-2 trajectory rail (pending → ok/error/denied dots)."""

import pytest


def test_dot_glyph_map():
    from rlm_optimized.tui_widgets.trajectory_rail import DOT_GLYPHS

    assert DOT_GLYPHS["running"] == "⏳"
    assert DOT_GLYPHS["ok"] == "●"
    assert DOT_GLYPHS["error"] == "✗"
    assert DOT_GLYPHS["denied"] == "○"


def test_max_dots_constant():
    from rlm_optimized.tui_widgets.trajectory_rail import MAX_DOTS

    assert MAX_DOTS >= 1
    assert isinstance(MAX_DOTS, int)


@pytest.mark.anyio
async def test_rail_add_pending_and_complete_ok():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.trajectory_rail import TrajectoryRail
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class RailApp(App):
        def compose(self):
            yield TrajectoryRail(id="rail")

    app = RailApp()
    async with app.run_test() as pilot:
        rail = app.query_one("#rail", TrajectoryRail)
        rail.add_pending("READ_FILE")
        await pilot.pause()
        assert len(rail._dots) == 1
        dot = rail._dots[0]
        assert "running" in dot.classes
        assert dot.tooltip == "READ_FILE"
        assert "⏳" in str(dot.content)

        rail.complete("ok")
        await pilot.pause()
        assert "ok" in dot.classes
        assert "●" in str(dot.content)
        assert "running" not in dot.classes
        await pilot.pause()


@pytest.mark.anyio
async def test_rail_complete_error_and_denied():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.trajectory_rail import TrajectoryRail
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class RailApp(App):
        def compose(self):
            yield TrajectoryRail(id="rail")

    app = RailApp()
    async with app.run_test() as pilot:
        rail = app.query_one("#rail", TrajectoryRail)
        rail.add_pending("RUN_COMMAND")
        rail.complete("error")
        await pilot.pause()
        assert "error" in rail._dots[0].classes
        assert "✗" in str(rail._dots[0].content)

        rail.add_pending("WRITE_FILE")
        rail.complete("denied")
        await pilot.pause()
        assert "denied" in rail._dots[-1].classes
        assert "○" in str(rail._dots[-1].content)
        assert len(rail._dots) == 2
        await pilot.pause()


@pytest.mark.anyio
async def test_rail_complete_without_pending_is_noop():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.trajectory_rail import TrajectoryRail
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class RailApp(App):
        def compose(self):
            yield TrajectoryRail(id="rail")

    app = RailApp()
    async with app.run_test() as pilot:
        rail = app.query_one("#rail", TrajectoryRail)
        rail.complete("ok")
        await pilot.pause()
        assert len(rail._dots) == 0
        await pilot.pause()


@pytest.mark.anyio
async def test_rail_clear_removes_dots():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.trajectory_rail import TrajectoryRail
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class RailApp(App):
        def compose(self):
            yield TrajectoryRail(id="rail")

    app = RailApp()
    async with app.run_test() as pilot:
        rail = app.query_one("#rail", TrajectoryRail)
        for _ in range(5):
            rail.add_pending("GIT")
        await pilot.pause()
        assert len(rail._dots) == 5
        rail.clear()
        await pilot.pause()
        assert len(rail._dots) == 0
        assert len(rail.children) == 1  # header only
        await pilot.pause()


@pytest.mark.anyio
async def test_rail_prunes_over_max():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.trajectory_rail import (
            MAX_DOTS,
            TrajectoryRail,
        )
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class RailApp(App):
        def compose(self):
            yield TrajectoryRail(id="rail")

    app = RailApp()
    async with app.run_test() as pilot:
        rail = app.query_one("#rail", TrajectoryRail)
        for i in range(MAX_DOTS + 10):
            rail.add_pending(f"TOOL{i}")
        await pilot.pause()
        assert len(rail._dots) == MAX_DOTS
        await pilot.pause()


@pytest.mark.anyio
async def test_app_pending_step_updates_rail():
    """The streamed <tool_call> adds a dot; the completing step flips it."""
    try:
        from unittest.mock import MagicMock

        from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized, Step
        from rlm_optimized.tui_app import TorchlightApp
        from rlm_optimized.tui_widgets.trajectory_rail import TrajectoryRail
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    import tempfile

    engine = MagicMock(spec=RLMEngineOptimized)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10
    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    async with app.run_test() as pilot:
        rail = app.query_one("#trajectory-rail", TrajectoryRail)
        assert len(rail._dots) == 0

        app._append_token('<tool_call>{"name": "READ_FILE", "path": "/tmp/x.py"}')
        assert len(rail._dots) == 1
        assert "running" in rail._dots[0].classes

        step = Step(
            step_number=1,
            depth=0,
            action="tool",
            thinking="read the file",
            content="",
            result="OK: read /tmp/x.py",
            tool_name="READ_FILE",
            tool_args={"path": "/tmp/x.py"},
        )
        app._handle_step(step)
        assert "ok" in rail._dots[0].classes
        assert "●" in str(rail._dots[0].content)
