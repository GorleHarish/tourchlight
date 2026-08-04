import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest


def _build_plan_text(project_root: str, is_goal: bool = False) -> str:
    """Delegate to the real TUI plan-builder helper."""
    try:
        from rlm_optimized.tui_widgets.format import build_plan_text
    except ImportError:
        pytest.skip("rlm_optimized.tui_widgets not importable in this environment")
    return build_plan_text(project_root, is_goal)


def test_build_plan_text_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        res = _build_plan_text(tmpdir)
        assert "No active plan checkboxes found." in res
        assert "Waiting for goal initialization" in res


def test_build_plan_text_with_tasks():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Project Setup\n+ [x] Done Task\n* [ ] Pending Task\n1. [/] In-progress Task\n1) [✓] Checked Task\n"
            )

        res = _build_plan_text(tmpdir)
        assert "PLAN & TASKS" in res
        assert "50%" in res
        assert "(2/4)" in res
        assert "[✓] Done Task" in res
        assert "[ ] Pending Task" in res
        assert "[►] In-progress Task █" in res
        assert "[✓] Checked Task" in res


def test_build_plan_text_all_done():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("- [x] Done 1\n- [X] Done 2\n")

        res = _build_plan_text(tmpdir)
        assert "100%" in res
        assert "(2/2)" in res


def test_build_plan_text_goal_spec_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".torchlight"), exist_ok=True)
        goal_path = os.path.join(tmpdir, ".torchlight", "goal_spec.json")
        with open(goal_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "title": "Build Agent",
                    "tasks": [
                        {"id": "t1", "description": "Design UI", "status": "verified"},
                        {
                            "id": "t2",
                            "description": "Implement feature",
                            "status": "in_progress",
                        },
                    ],
                },
                f,
            )

        res = _build_plan_text(tmpdir, is_goal=True)
        assert "50%" in res
        assert "(1/2)" in res
        assert "[✓] Design UI" in res
        assert "[►] Implement feature █" in res


def test_build_plan_text_dedupes_duplicate_checkbox_lines():
    """Repeated checklist entries (summary + detailed sections) must not duplicate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(
                "# Plan\n"
                "- [ ] Build API\n"
                "- [ ] Build API\n"
                "- [x] Setup repo\n"
                "- [x] Setup repo\n"
                "- [ ] Write docs\n"
                "- [ ] BUILD API\n"
            )

        res = _build_plan_text(tmpdir)
        # 3 unique tasks (2 pending, 1 done) -> 33%, (1/3)
        assert "(1/3)" in res
        assert "33%" in res
        assert res.count("[ ] Build API") == 1
        assert res.count("[✓] Setup repo") == 1
        assert res.count("[ ] Write docs") == 1
        assert "[ ] BUILD API" not in res  # case-insensitive dup of "Build API"


def test_build_plan_text_goal_spec_json_dedupes():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".torchlight"), exist_ok=True)
        goal_path = os.path.join(tmpdir, ".torchlight", "goal_spec.json")
        with open(goal_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "title": "Build Agent",
                    "tasks": [
                        {"id": "t1", "description": "Design UI", "status": "verified"},
                        {"id": "t1b", "description": "Design UI", "status": "pending"},
                        {"id": "t2", "description": "Ship it", "status": "pending"},
                    ],
                },
                f,
            )

        res = _build_plan_text(tmpdir, is_goal=True)
        assert "(1/2)" in res
        assert res.count("[✓] Design UI") == 1
        assert "[ ] Design UI" not in res  # duplicate dropped regardless of status
        assert "[ ] Ship it" in res


def test_tui_app_tcss_valid_syntax():
    tcss_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "rlm_optimized", "tui_app.tcss"
        )
    )
    assert os.path.exists(tcss_path), f"tui_app.tcss not found at {tcss_path}"
    with open(tcss_path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        from textual.css.parse import parse

        parse("tui_app.tcss", content, read_from="tui_app.tcss")
    except ImportError:
        pytest.skip("textual not installed in test environment")


def _make_app():
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
    from rlm_optimized.tui_app import TorchlightApp

    engine = MagicMock(spec=RLMEngineOptimized)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10
    return TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")


@pytest.mark.anyio
async def test_shortcuts_help_modal_composes():
    try:
        from rlm_optimized.tui_app import ShortcutsHelpModal

        app = _make_app()
        async with app.run_test() as pilot:
            app.push_screen(ShortcutsHelpModal())
            await pilot.pause()
            assert isinstance(app.screen, ShortcutsHelpModal)
            assert len(app.query("*")) > 0
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")


@pytest.mark.anyio
async def test_torchlight_app_headless_run():
    try:
        from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
        from rlm_optimized.tui_app import TorchlightApp

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
            assert app.model_name == "qwen2.5-coder-7b-instruct"
            # Verify Explorer sidebar and Agent Reasoning & Trajectory view widgets exist
            explorer = app.query_one("#explorer-sidebar")
            agent_split = app.query_one("#agent-split-pane")
            chat_container = app.query_one("#chat-container")
            status_bar = app.query_one("#status-bar")
            compact_btn = app.query_one("#compact-btn")
            assert explorer is not None
            assert agent_split is not None
            assert chat_container is not None
            assert status_bar is not None
            assert compact_btn is not None

            # Verify input state toggle preserves clickable Stop button
            app._set_input_enabled(False)
            btn = app.query_one("#send-btn")
            assert btn.disabled is False
            assert "STOP" in str(btn.label).upper()

            app._set_input_enabled(True)
            assert btn.disabled is False
            assert "SEND" in str(btn.label).upper()
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")


@pytest.mark.anyio
async def test_copy_selection_modal_composes():
    try:
        from rlm_optimized.tui_app import CopySelectionModal

        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        app = _make_app()
        async with app.run_test() as pilot:
            app.push_screen(CopySelectionModal(history))
            await pilot.pause()
            assert isinstance(app.screen, CopySelectionModal)
            assert len(app.query("*")) > 0
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")
