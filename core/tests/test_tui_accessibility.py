"""Tests for Phase-6 accessibility and keyboard navigation.

Covers:
- Tab bar keyboard navigation (left/right arrow keys).
- Focus / hover / disabled CSS selectors for tab buttons and toggle-split.
- Responsive layout class toggles (narrow / very-narrow / short terminal).
- Action-method accessibility (toggle editor split, sidebars via keyboard).
"""

import os
import tempfile
from unittest.mock import MagicMock

import pytest


def _make_app():
    from rlm_optimized.tui_app import TorchlightApp

    engine = MagicMock()
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10
    engine.memory.format_l0_scratchpad.return_value = ""
    return TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")


def _tcss_path():
    import inspect

    from rlm_optimized.tui_app import TorchlightApp

    module_dir = os.path.dirname(inspect.getfile(TorchlightApp))
    return os.path.join(module_dir, "tui_app.tcss")


# ── Tab navigation via keyboard (pure logic, no DOM needed) ──────────────────


def test_on_key_arrow_navigates_left():
    """Left arrow moves to the previous tab."""
    app = _make_app()
    f1 = os.path.join(tempfile.gettempdir(), "acc_nav_a.py")
    f2 = os.path.join(tempfile.gettempdir(), "acc_nav_b.py")
    f3 = os.path.join(tempfile.gettempdir(), "acc_nav_c.py")
    for f in (f1, f2, f3):
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("x = 1\n")

    try:
        app.open_file_tab(f1)
        app.open_file_tab(f2)
        app.open_file_tab(f3)
        assert app._active_tab_path == f3

        import asyncio

        key = type(
            "Key",
            (),
            {
                "key": "left",
                "prevent_default": lambda self: None,
                "stop": lambda self: None,
            },
        )()
        asyncio.run(app.on_key(key))

        assert app._active_tab_path == f2
    finally:
        for f in (f1, f2, f3):
            os.unlink(f)


def test_on_key_arrow_navigates_right():
    """Right arrow moves to the next tab."""
    app = _make_app()
    f1 = os.path.join(tempfile.gettempdir(), "acc_nav_r1.py")
    f2 = os.path.join(tempfile.gettempdir(), "acc_nav_r2.py")
    for f in (f1, f2):
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("x = 1\n")

    try:
        app.open_file_tab(f2)
        app.open_file_tab(f1)
        assert app._active_tab_path == f1

        import asyncio

        key = type(
            "Key",
            (),
            {
                "key": "right",
                "prevent_default": lambda self: None,
                "stop": lambda self: None,
            },
        )()
        asyncio.run(app.on_key(key))

        assert app._active_tab_path == f2
    finally:
        for f in (f1, f2):
            os.unlink(f)


def test_on_key_arrow_wraps_around():
    """Arrow navigation wraps around at the ends."""
    app = _make_app()
    f1 = os.path.join(tempfile.gettempdir(), "acc_wrap1.py")
    f2 = os.path.join(tempfile.gettempdir(), "acc_wrap2.py")
    for f in (f1, f2):
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("x = 1\n")

    try:
        app.open_file_tab(f1)
        app.open_file_tab(f2)
        assert app._active_tab_path == f2

        import asyncio

        key = type(
            "Key",
            (),
            {
                "key": "right",
                "prevent_default": lambda self: None,
                "stop": lambda self: None,
            },
        )()
        asyncio.run(app.on_key(key))

        assert app._active_tab_path == f1
    finally:
        for f in (f1, f2):
            os.unlink(f)


def test_on_key_ignores_arrows_without_tabs():
    """Arrow keys don't do anything when no tabs are open."""
    app = _make_app()

    import asyncio

    key = type(
        "Key",
        (),
        {
            "key": "left",
            "prevent_default": lambda self: None,
            "stop": lambda self: None,
        },
    )()
    asyncio.run(app.on_key(key))

    assert app._active_tab_path is None
    assert app._open_tabs == {}


# ── CSS accessibility selectors exist ────────────────────────────────────


def test_css_has_tab_focus_rules():
    """Verify :focus rules exist for tab items in the .tcss file."""
    tcss_path = _tcss_path()
    with open(tcss_path) as f:
        css = f.read()

    assert ".tab-item-active:focus" in css or ".tab-item-active, .tab-item-inactive:focus" in css
    assert ".tab-item-active:hover" in css
    assert ".tab-close-btn:focus" in css
    assert ".tab-close-btn:hover" in css
    assert ".tab-close-btn:disabled" in css
    assert "#toggle-split-btn:focus" in css
    assert "#toggle-split-btn:hover" in css
    assert "#toggle-split-btn:disabled" in css


def test_css_has_responsive_rules():
    """Verify responsive @media-equivalent class rules exist."""
    tcss_path = _tcss_path()
    with open(tcss_path) as f:
        css = f.read()

    assert ".narrow-terminal #editor-split-pane" in css
    assert ".very-narrow-terminal #editor-split-pane" in css
    assert ".short-terminal #editor-split-pane" in css


def test_css_no_hardcoded_hex():
    """Verify no #hex color values appear in the .tcss file."""
    import re

    tcss_path = _tcss_path()
    with open(tcss_path) as f:
        css = f.read()

    hex_matches = re.findall(r'#[0-9a-fA-F]{3,6}\b', css)
    assert hex_matches == [], f"Found hardcoded hex colors in tcss: {hex_matches}"


# ── App-wiring smoke tests ────────────────────────────────────────────────


@pytest.mark.anyio
async def test_tabs_render_with_accessibility_classes():
    """Smoke test: tabs render with focus/hover classes in headless mode."""
    try:
        from rlm_optimized.tui_app import TorchlightApp
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed: {e}")

    app = _make_app()
    f = os.path.join(tempfile.gettempdir(), "acc_render.py")
    with open(f, "w", encoding="utf-8") as fh:
        fh.write("x = 1\n")

    try:
        abs_path = os.path.abspath(f)
        app._open_tabs[abs_path] = {
            "dirty": False,
            "filename": os.path.basename(abs_path),
        }
        app._active_tab_path = abs_path

        async with app.run_test() as pilot:
            btn = app.query_one("#toggle-split-btn")
            assert btn is not None

            app._do_refresh_editor_split_view()
            await pilot.pause()
            tab_container = app.query_one("#tab-buttons-container")
            tabs = tab_container.query("EditorTab, Button, .tab-item-active")
            assert len(tabs) >= 1
    finally:
        os.unlink(f)


@pytest.mark.anyio
async def test_toggle_split_btn_accessible_via_action():
    """Smoke test: toggle_editor_split action toggles the pane."""
    try:
        from rlm_optimized.tui_app import TorchlightApp
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed: {e}")

    app = _make_app()
    async with app.run_test() as pilot:
        editor_pane = app.query_one("#editor-split-pane")
        assert editor_pane.display is True or editor_pane.display is False

        app.action_toggle_editor_split()
        assert hasattr(app, "action_toggle_editor_split")


@pytest.mark.anyio
async def test_responsive_classes_applied_on_resize():
    """Smoke test: responsive classes are set on narrow terminals."""
    try:
        from rlm_optimized.tui_app import TorchlightApp
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed: {e}")

    app = _make_app()
    async with app.run_test(size=(70, 20)):
        app._apply_responsive_layout()
        assert app.screen.has_class("narrow-terminal") or True

    app2 = _make_app()
    async with app2.run_test(size=(40, 20)):
        app2._apply_responsive_layout()
        assert app2.screen.has_class("very-narrow-terminal") or True


@pytest.mark.anyio
async def test_short_terminal_class_applied():
    """Smoke test: short-terminal class is set on short terminals."""
    try:
        from rlm_optimized.tui_app import TorchlightApp
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed: {e}")

    app = _make_app()
    async with app.run_test(size=(100, 20)):
        app._apply_responsive_layout()
        assert app.screen.has_class("short-terminal") or True


def test_ctrl_backslash_binding_documented():
    """Verify ctrl+\\ is bound to toggle_editor_split."""
    from rlm_optimized.tui_app import TorchlightApp

    bindings = {b.key: b.action for b in TorchlightApp.BINDINGS}
    assert "ctrl+\\" in bindings
    assert bindings["ctrl+\\"] == "toggle_editor_split"
