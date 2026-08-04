"""Regression tests for the PaneResizer drag/click resizing in tui_app.py.

The PaneResizer must:
  * expand the adjacent pane on left-click and shrink it on right-click,
  * clamp pane widths to [MIN_WIDTH, MAX_WIDTH] for clicks and drags,
  * resize live while dragging and suppress the trailing click after a drag,
  * hide/show with the ctrl+b / ctrl+r sidebar toggles.

Textual 8.x mouse `button` is an int (1 == left, 3 == right) on every mouse
event type, including `Click` — never a string.
"""

import asyncio
import os
import sys
import tempfile

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_TEST_DIR)
for _p in (_REPO_ROOT, _TEST_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from textual import events

from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
from rlm_optimized.tui_app import TorchlightApp


class _StubClient:
    """No-op client so the engine never touches LM Studio / Ollama / cloud."""

    model = "test-model"
    _provider = "stub"


def _build_app():
    tmp = tempfile.mkdtemp(prefix="tui_resizer_")
    engine = RLMEngineOptimized(client=_StubClient(), project_root=tmp)
    app = TorchlightApp(
        engine=engine,
        model_name="test-model",
        provider_name="stub",
        engine_port=0,
    )
    app._test_runner = True
    return app


def _resize_to(app, width):
    app.left_pane_width = width
    app._apply_pane_widths()


async def _click_resizer(pilot, selector, button):
    await pilot.click(selector, button=button, offset=(0, 1))
    await pilot.pause()


async def _drag_resizer(app, pilot, selector, delta_x):
    """Simulate a real drag: mouse_down -> captured MouseMove -> mouse_up."""
    resizer = app.query_one(selector)
    x0, y0 = resizer.region.x, resizer.region.y
    await pilot.mouse_down(selector, offset=(0, 1), button=1)
    await pilot.pause()
    app.post_message(
        events.MouseMove(
            widget=app.screen,
            x=x0 + delta_x,
            y=y0 + 1,
            delta_x=delta_x,
            delta_y=0,
            button=1,
            shift=False,
            meta=False,
            ctrl=False,
            screen_x=x0 + delta_x,
            screen_y=y0 + 1,
        )
    )
    await pilot.pause()
    await pilot.mouse_up(selector, offset=(0, 1))
    await pilot.pause()


async def _start_app():
    app = _build_app()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        await pilot.pause()
        yield app, pilot


async def _test_clicks_expand_and_shrink():
    async for app, pilot in _start_app():
        await _click_resizer(pilot, "#resizer-left", 1)
        assert app.left_pane_width == 26
        await _click_resizer(pilot, "#resizer-left", 3)
        assert app.left_pane_width == 24

        await _click_resizer(pilot, "#resizer-right", 1)
        assert app.right_pane_width == 32
        await _click_resizer(pilot, "#resizer-right", 3)
        assert app.right_pane_width == 30


def test_clicks_expand_and_shrink():
    asyncio.run(_test_clicks_expand_and_shrink())


async def _test_click_clamps():
    async for app, pilot in _start_app():
        for _ in range(30):
            await _click_resizer(pilot, "#resizer-left", 3)
        assert app.left_pane_width == 14
        for _ in range(30):
            await _click_resizer(pilot, "#resizer-left", 1)
        assert app.left_pane_width == 60


def test_click_clamps():
    asyncio.run(_test_click_clamps())


async def _test_drag_resizes_and_clamps():
    async for app, pilot in _start_app():
        _resize_to(app, 24)
        await pilot.pause()
        await _drag_resizer(app, pilot, "#resizer-left", 5)
        assert app.left_pane_width == 29

        _resize_to(app, 30)
        await pilot.pause()
        await _drag_resizer(app, pilot, "#resizer-right", 5)
        assert app.right_pane_width == 25

        _resize_to(app, 24)
        await pilot.pause()
        await _drag_resizer(app, pilot, "#resizer-left", 1000)
        assert app.left_pane_width == 60

        _resize_to(app, 24)
        await pilot.pause()
        await _drag_resizer(app, pilot, "#resizer-left", -1000)
        assert app.left_pane_width == 14


def test_drag_resizes_and_clamps():
    asyncio.run(_test_drag_resizes_and_clamps())


async def _test_drag_suppresses_trailing_click():
    async for app, pilot in _start_app():
        _resize_to(app, 24)
        await pilot.pause()
        await _drag_resizer(app, pilot, "#resizer-left", 3)
        # 24 + 3 = 27; if the trailing Click were NOT suppressed it would be 29.
        assert app.left_pane_width == 27


def test_drag_suppresses_trailing_click():
    asyncio.run(_test_drag_suppresses_trailing_click())


async def _test_sidebar_toggle_bindings():
    async for app, pilot in _start_app():
        left = app.query_one("#resizer-left")
        right = app.query_one("#resizer-right")

        await pilot.press("ctrl+b")
        await pilot.pause()
        assert left.display is False
        await pilot.press("ctrl+b")
        await pilot.pause()
        assert left.display is True

        await pilot.press("ctrl+r")
        await pilot.pause()
        assert right.display is False
        await pilot.press("ctrl+r")
        await pilot.pause()
        assert right.display is True


def test_sidebar_toggle_bindings():
    asyncio.run(_test_sidebar_toggle_bindings())
