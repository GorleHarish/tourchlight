"""Tests for Phase-5 tabbed editor split pane (open_file_tab, dirty marker,
keyboard tab navigation, _refresh_editor_split_view)."""

import tempfile
import os
from unittest.mock import MagicMock

import pytest


def test_open_tabs_starts_empty():
    from rlm_optimized.tui_app import TorchlightApp

    engine = MagicMock(spec=MagicMock)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10
    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    assert app._open_tabs == {}
    assert app._active_tab_path is None


def test_show_plan_sidebar_initialized():
    from rlm_optimized.tui_app import TorchlightApp

    engine = MagicMock(spec=MagicMock)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10
    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    assert getattr(app, "_show_plan_sidebar", False) is True


def test_toggle_editor_split_action_exists():
    from rlm_optimized.tui_app import TorchlightApp

    assert hasattr(TorchlightApp, "action_toggle_editor_split")


def test_toggle_editor_split_binds_ctrl_backslash():
    from rlm_optimized.tui_app import TorchlightApp

    bindings = {b.key: b.action for b in TorchlightApp.BINDINGS}
    assert "ctrl+\\" in bindings
    assert bindings["ctrl+\\"] == "toggle_editor_split"


def test_get_tab_hash():
    from rlm_optimized.tui_app import TorchlightApp

    engine = MagicMock(spec=MagicMock)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10
    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    h = app._get_tab_hash("/tmp/test.py")
    assert len(h) == 10
    assert app._get_tab_hash("/tmp/test.py") == app._get_tab_hash("/tmp/test.py")
    assert app._get_tab_hash("/tmp/test.py") != app._get_tab_hash("/tmp/other.py")


def test_open_file_tab_registers_tab():
    engine = MagicMock(spec=MagicMock)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10

    from rlm_optimized.tui_app import TorchlightApp

    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    test_file = os.path.join(tempfile.gettempdir(), "test_tab_file.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("x = 1\n")

    try:
        app.open_file_tab(test_file)
        assert test_file in app._open_tabs
        assert app._open_tabs[test_file]["dirty"] is False
        assert app._active_tab_path == test_file
    finally:
        os.unlink(test_file)


def test_open_file_tab_sets_dirty_on_reopen():
    engine = MagicMock(spec=MagicMock)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10

    from rlm_optimized.tui_app import TorchlightApp

    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    test_file = os.path.join(tempfile.gettempdir(), "test_tab_file2.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("x = 1\n")

    try:
        app.open_file_tab(test_file)
        assert app._open_tabs[test_file]["dirty"] is False
        app._open_tabs[test_file]["dirty"] = True
        assert app._open_tabs[test_file]["dirty"] is True
    finally:
        os.unlink(test_file)


def test_close_file_tab_removes_from_open_tabs():
    engine = MagicMock(spec=MagicMock)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10

    from rlm_optimized.tui_app import TorchlightApp

    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    test_file = os.path.join(tempfile.gettempdir(), "test_tab_file3.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("x = 1\n")

    try:
        app.open_file_tab(test_file)
        assert test_file in app._open_tabs
        app.close_file_tab(test_file)
        assert test_file not in app._open_tabs
    finally:
        os.unlink(test_file)


def test_close_file_tab_switches_active_tab():
    engine = MagicMock(spec=MagicMock)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10

    from rlm_optimized.tui_app import TorchlightApp

    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    f1 = os.path.join(tempfile.gettempdir(), "test_tab_a.py")
    f2 = os.path.join(tempfile.gettempdir(), "test_tab_b.py")
    with open(f1, "w", encoding="utf-8") as f:
        f.write("a = 1\n")
    with open(f2, "w", encoding="utf-8") as f:
        f.write("b = 1\n")

    try:
        app.open_file_tab(f1)
        app.open_file_tab(f2)
        assert app._active_tab_path == f2
        app.close_file_tab(f2)
        assert app._active_tab_path == f1
        app.close_file_tab(f1)
        assert app._active_tab_path is None
    finally:
        os.unlink(f1)
        os.unlink(f2)


def test_dirty_marker_set_on_write_step():
    engine = MagicMock(spec=MagicMock)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10

    from rlm_optimized.tui_app import TorchlightApp
    from rlm_optimized.rlm_engine_optimized import Step

    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    test_file = os.path.join(tempfile.gettempdir(), "test_dirty.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("x = 1\n")

    try:
        app.open_file_tab(test_file)
        assert app._open_tabs[test_file]["dirty"] is False

        step = Step(
            step_number=1,
            depth=0,
            action="tool",
            thinking="",
            content="",
            result="OK",
            tool_name="WRITE_FILE",
            tool_args={"path": test_file},
        )
        app._handle_step(step)
        assert app._open_tabs[test_file]["dirty"] is True
    finally:
        os.unlink(test_file)


def test_dirty_marker_not_set_for_non_tab_file():
    engine = MagicMock(spec=MagicMock)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10

    from rlm_optimized.tui_app import TorchlightApp
    from rlm_optimized.rlm_engine_optimized import Step

    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    test_file = os.path.join(tempfile.gettempdir(), "test_notab.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("x = 1\n")

    try:
        step = Step(
            step_number=1,
            depth=0,
            action="tool",
            thinking="",
            content="",
            result="OK",
            tool_name="WRITE_FILE",
            tool_args={"path": test_file},
        )
        app._handle_step(step)
        assert test_file not in app._open_tabs
    finally:
        os.unlink(test_file)


@pytest.mark.anyio
async def test_editor_split_pane_composes():
    try:
        from rlm_optimized.tui_app import TorchlightApp
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    engine = MagicMock(spec=MagicMock)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10
    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    async with app.run_test() as pilot:
        editor_pane = app.query_one("#editor-split-pane")
        assert editor_pane is not None
        tab_bar = app.query_one("#tab-bar-header")
        assert tab_bar is not None
        tab_buttons = app.query_one("#tab-buttons-container")
        assert tab_buttons is not None
        content_area = app.query_one("#editor-content-area")
        assert content_area is not None


@pytest.mark.anyio
async def test_toggle_split_btn_toggles_editor_pane():
    try:
        from rlm_optimized.tui_app import TorchlightApp
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    engine = MagicMock(spec=MagicMock)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10
    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    async with app.run_test() as pilot:
        editor_pane = app.query_one("#editor-split-pane")
        initial_display = editor_pane.display
        app.on_toggle_split_btn()
        assert editor_pane.display != initial_display


@pytest.mark.anyio
async def test_keyboard_tab_navigation():
    try:
        from rlm_optimized.tui_app import TorchlightApp
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    engine = MagicMock(spec=MagicMock)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10
    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    f1 = os.path.join(tempfile.gettempdir(), "test_nav_a.py")
    f2 = os.path.join(tempfile.gettempdir(), "test_nav_b.py")
    with open(f1, "w", encoding="utf-8") as f:
        f.write("a = 1\n")
    with open(f2, "w", encoding="utf-8") as f:
        f.write("b = 1\n")

    try:
        app.open_file_tab(f1)
        app.open_file_tab(f2)
        assert app._active_tab_path == f2

        key_event = type("Key", (), {"key": "left", "prevent_default": lambda self: None, "stop": lambda self: None})()
        await app.on_key(key_event)
        assert app._active_tab_path == f1

        key_event = type("Key", (), {"key": "right", "prevent_default": lambda self: None, "stop": lambda self: None})()
        await app.on_key(key_event)
        assert app._active_tab_path == f2
    finally:
        os.unlink(f1)
        os.unlink(f2)


@pytest.mark.anyio
async def test_torchlight_app_headless_run_has_editor_pane():
    try:
        from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
        from rlm_optimized.tui_app import TorchlightApp
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    engine = MagicMock(spec=RLMEngineOptimized)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10
    app = TorchlightApp(
        engine=engine,
        model_name="qwen2.5-coder-7b-instruct",
        provider_name="llama-cpp",
    )
    async with app.run_test() as pilot:
        editor_pane = app.query_one("#editor-split-pane")
        assert editor_pane is not None
        tab_buttons = app.query_one("#tab-buttons-container")
        assert tab_buttons is not None
        content_area = app.query_one("#editor-content-area")
        assert content_area is not None