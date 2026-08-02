"""Tests for Phase-4 command palette + prompt autocomplete."""

import tempfile
from pathlib import Path

import pytest


def test_slash_command_list_shape():
    from rlm_optimized.tui_widgets.command_palette import slash_command_list

    cmds = slash_command_list()
    assert cmds
    for cmd, usage, desc in cmds:
        assert cmd.startswith("/")
        assert usage.startswith("/")
        assert desc
    assert "/help" in [c for c, _, _ in cmds]
    assert "/model" in [c for c, _, _ in cmds]


def test_fuzzy_filter_prefix_beats_substring():
    from rlm_optimized.tui_widgets.command_palette import fuzzy_filter

    items = [
        ("/status", "s", "slash", "/status"),
        ("/start", "s", "slash", "/start"),
        ("/stop", "s", "slash", "/stop"),
        ("zzz", "s", "slash", "/zzz"),
    ]
    result = fuzzy_filter("/sta", items)
    labels = [i[0] for i in result]
    assert labels[0] == "/start"
    assert labels[1] == "/status"
    assert "/stop" not in labels


def test_fuzzy_filter_empty_query_and_no_match():
    from rlm_optimized.tui_widgets.command_palette import fuzzy_filter

    items = [("alpha", "d", "slash", "a"), ("beta", "d", "slash", "b")]
    assert len(fuzzy_filter("", items)) == 2
    assert fuzzy_filter("qqqq", items) == []


def test_iter_project_files_skips_dot_and_vendor_dirs():
    from rlm_optimized.tui_widgets.command_palette import iter_project_files

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p / "a.py").write_text("")
        (p / ".git").mkdir()
        (p / ".git" / "config").write_text("")
        (p / "node_modules").mkdir()
        (p / "node_modules" / "x.js").write_text("")
        (p / "src").mkdir()
        (p / "src" / "b.py").write_text("")

        files = iter_project_files(tmp)
        assert "a.py" in files
        assert "src/b.py" in files
        assert not any(f.startswith(".git") for f in files)
        assert not any(f.startswith("node_modules") for f in files)


def test_iter_project_files_caps():
    from rlm_optimized.tui_widgets.command_palette import iter_project_files

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        for i in range(10):
            (p / f"f{i}.py").write_text("")
        files = iter_project_files(tmp, max_files=3)
        assert len(files) == 3


def test_match_prompt_suggestions_slash():
    from rlm_optimized.tui_widgets.command_palette import (
        match_prompt_suggestions,
        slash_command_list,
    )

    cmds = slash_command_list()
    got = match_prompt_suggestions("/sta", cmds, [])
    assert got == ["/start", "/status"]
    assert match_prompt_suggestions("/help", cmds, []) == []
    assert match_prompt_suggestions("/model gpt4", cmds, []) == []
    assert match_prompt_suggestions("hello", cmds, []) == []


def test_match_prompt_suggestions_file_at():
    from rlm_optimized.tui_widgets.command_palette import (
        match_prompt_suggestions,
        slash_command_list,
    )

    cmds = slash_command_list()
    files = ["src/app.py", "src/util.py", "tests/test_x.py"]
    got = match_prompt_suggestions("@sr", cmds, files)
    assert "@src/app.py" in got
    assert "@src/util.py" in got
    assert not any("tests" in g for g in got)


def test_build_palette_items_kinds_and_visibility():
    from textual.binding import Binding

    from rlm_optimized.tui_widgets.command_palette import (
        build_palette_items,
        slash_command_list,
    )

    bindings = [
        Binding("ctrl+k", "command_palette", "Command Palette", show=True),
        Binding("ctrl+r", "reset_session", "Reset REPL", show=False),
    ]
    items = build_palette_items(bindings, slash_command_list(), ["a.py"])
    kinds = {i[2] for i in items}
    assert kinds == {"action", "slash", "file"}
    labels = [i[0] for i in items]
    assert any("Command Palette" in l for l in labels)
    assert "@ a.py" in labels
    assert not any("Reset REPL" in l for l in labels)


@pytest.mark.anyio
async def test_prompt_text_area_suggestion_callback_and_accept():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.command_palette import PromptTextArea
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    seen = []

    class HostApp(App):
        def compose(self):
            yield PromptTextArea(id="ta", suggestion_callback=seen.append)

    app = HostApp()
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", PromptTextArea)
        ta.load_text("/sta")
        await pilot.pause()
        assert seen[-1] == ["/start", "/status"]
        assert ta.suggestions_visible
        ta.accept_suggestion()
        assert ta.text == "/start"
        assert ta.matches == []
        assert seen[-1] == []
        await pilot.pause()


@pytest.mark.anyio
async def test_prompt_text_area_file_suggestions_and_dismiss():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.command_palette import PromptTextArea
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    seen = []

    class HostApp(App):
        def compose(self):
            yield PromptTextArea(
                id="ta", file_paths=["app.py"], suggestion_callback=seen.append
            )

    app = HostApp()
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", PromptTextArea)
        ta.load_text("@ap")
        await pilot.pause()
        assert ta.suggestions_visible
        assert ta.matches == ["@app.py"]
        ta.dismiss_suggestion()
        assert not ta.suggestions_visible
        assert seen[-1] == []
        await pilot.pause()


@pytest.mark.anyio
async def test_prompt_text_area_enter_submits_and_accepts_suggestion():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.command_palette import PromptTextArea
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    submitted = []

    class SubApp(App):
        def compose(self):
            yield PromptTextArea(id="ta")

        def on_prompt_text_area_submit_requested(self, event):
            submitted.append(event)

    app = SubApp()
    async with app.run_test() as pilot:
        ta = app.query_one("#ta", PromptTextArea)
        ta.focus()
        await pilot.pause()

        # "/sta" shows suggestions; Enter accepts the first (/start), not submit.
        await pilot.press("/", "s", "t", "a")
        await pilot.pause()
        assert ta.suggestions_visible
        await pilot.press("enter")
        await pilot.pause()
        assert ta.text == "/start"
        assert not ta.suggestions_visible
        assert submitted == []

        # A second Enter now submits (no active suggestion).
        await pilot.press("enter")
        await pilot.pause()
        assert len(submitted) == 1

        # Plain message text submits directly.
        await pilot.press("h", "i")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert len(submitted) == 2
        await pilot.pause()


@pytest.mark.anyio
async def test_command_palette_composes_filters_and_selects():
    try:
        from textual.app import App
        from textual.widgets import Label, ListView, Static

        from rlm_optimized.tui_widgets.command_palette import CommandPalette
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "readme.md").write_text("hi")

        class PaletteApp(App):
            def compose(self):
                yield Static("host")

        app = PaletteApp()
        async with app.run_test() as pilot:
            results = []
            palette = CommandPalette(tmp)
            app.push_screen(palette, results.append)
            await pilot.pause()

            inp = palette.query_one("#palette-input")
            lv = palette.query_one("#palette-list", ListView)
            assert lv.display
            assert len(lv._nodes) > 0
            labels = [str(n.query_one(Label).render()) for n in lv._nodes]
            assert any("/help" in l for l in labels)

            inp.value = "/hel"
            await pilot.pause()
            labels = [str(n.query_one(Label).render()) for n in lv._nodes]
            assert labels and all("/help" in l for l in labels)

            palette.action_select()
            await pilot.pause()
            assert results and results[0].kind == "slash"
            assert results[0].value == "/help"
            await pilot.pause()
