"""Tests for Phase-3 inline diff rendering (render_unified_diff + DiffView)."""

import os

import pytest


def test_render_unified_diff_additions_and_deletions():
    from rlm_optimized.tui_widgets.diff_view import (
        KIND_ADD,
        KIND_DEL,
        render_unified_diff,
    )

    old = "a\nb\nc\n"
    new = "a\nB\nc\nd\n"
    entries = render_unified_diff(old, new, path="x.py")
    kinds = {kind for kind, _ in entries}
    assert KIND_ADD in kinds
    assert KIND_DEL in kinds
    adds = [line for kind, line in entries if kind == KIND_ADD]
    dels = [line for kind, line in entries if kind == KIND_DEL]
    assert any(line == "+B" for line in adds)
    assert any(line == "+d" for line in adds)
    assert any(line == "-b" for line in dels)


def test_render_unified_diff_meta_headers():
    from rlm_optimized.tui_widgets.diff_view import KIND_META, render_unified_diff

    entries = render_unified_diff("x\n", "y\n", path="a.txt")
    metas = [line for kind, line in entries if kind == KIND_META]
    assert any(line.startswith("@@") for line in metas)
    assert any("a/a.txt" in line for line in metas)


def test_render_unified_diff_empty_sides():
    from rlm_optimized.tui_widgets.diff_view import render_unified_diff

    assert render_unified_diff("", "") == []
    assert render_unified_diff(None, None) == []


def test_diff_summary_counts():
    from rlm_optimized.tui_widgets.diff_view import diff_summary, render_unified_diff

    entries = render_unified_diff("a\nb\n", "a\nb\nc\nd\n")
    assert diff_summary(entries) == "+2 −0"
    assert diff_summary([]) == ""


def test_diff_markup_colors_lines():
    from rlm_optimized.tui_widgets.diff_view import diff_markup, render_unified_diff

    entries = render_unified_diff("a\nb\n", "a\nB\n", path="f.py")
    markup = diff_markup(entries)
    assert "[green]+B" in markup
    assert "[red]-b" in markup
    assert "a/f.py" in markup


def test_diff_markup_truncates():
    from rlm_optimized.tui_widgets.diff_view import diff_markup, render_unified_diff

    old = "\n".join(f"o{i}" for i in range(200))
    new = "\n".join(f"n{i}" for i in range(200))
    entries = render_unified_diff(old, new)
    markup = diff_markup(entries, max_lines=30)
    assert "Diff Truncated for UI Performance" in markup
    assert markup.count("\n") <= 31


def test_build_diff_preview_write_file(tmp_path):
    from rlm_optimized.tui_widgets.diff_view import build_diff_preview

    target = tmp_path / "a.py"
    target.write_text("x = 1\n", encoding="utf-8")
    preview = build_diff_preview(
        "WRITE_FILE",
        {"path": str(target), "content": "x = 1\ny = 2\n"},
        str(tmp_path),
    )
    assert preview is not None
    path, old, new, entries = preview
    assert path == str(target)
    assert old == "x = 1\n"
    assert "y = 2" in new
    assert any(kind == "add" for kind, _ in entries)


def test_build_diff_preview_edit_file(tmp_path):
    from rlm_optimized.tui_widgets.diff_view import build_diff_preview

    target = tmp_path / "a.py"
    target.write_text("x = 1\n", encoding="utf-8")
    preview = build_diff_preview(
        "EDIT_FILE",
        {"path": str(target), "old_text": "x = 1", "new_text": "x = 2"},
        str(tmp_path),
    )
    assert preview is not None
    _path, _old, new, entries = preview
    assert new == "x = 2\n"
    assert any(kind == "del" for kind, _ in entries)
    assert any(kind == "add" for kind, _ in entries)


def test_build_diff_preview_new_file(tmp_path):
    from rlm_optimized.tui_widgets.diff_view import build_diff_preview

    target = tmp_path / "new.txt"
    preview = build_diff_preview(
        "WRITE_FILE",
        {"path": str(target), "content": "hello\n"},
        str(tmp_path),
    )
    assert preview is not None
    _path, old, new, entries = preview
    assert old == ""
    assert new == "hello\n"
    assert all(kind in ("add", "meta") for kind, _ in entries)


def test_build_diff_preview_non_diffable():
    from rlm_optimized.tui_widgets.diff_view import build_diff_preview

    assert build_diff_preview("READ_FILE", {"path": "/tmp/x"}, "/tmp") is None
    assert build_diff_preview("WRITE_FILE", {}, "/tmp") is None
    assert (
        build_diff_preview("WRITE_FILE", {"path": "/tmp/x", "content": "x"}, "/tmp")
        is not None
    )
    assert build_diff_preview("WRITE_FILE", {"path": "/tmp/x"}, "/tmp") is None


def test_build_diff_preview_snapshot_override(tmp_path):
    """A pre-write snapshot (from approval) wins over the already-written disk state."""
    from rlm_optimized.tui_widgets.diff_view import build_diff_preview

    target = tmp_path / "a.py"
    target.write_text("x = 2\n", encoding="utf-8")  # already written
    preview = build_diff_preview(
        "WRITE_FILE",
        {"path": str(target), "content": "x = 3\n"},
        str(tmp_path),
        old_text="x = 1\n",
    )
    assert preview is not None
    _path, old, new, entries = preview
    assert old == "x = 1\n"
    assert new == "x = 3\n"
    assert any(kind == "del" for kind, _ in entries)
    assert any(kind == "add" for kind, _ in entries)


def test_build_diff_preview_code_file_write():
    """The engine's own CODE_FILE_WRITE approval path is diffable too."""
    from rlm_optimized.tui_widgets.diff_view import build_diff_preview

    preview = build_diff_preview(
        "CODE_FILE_WRITE",
        {"path": "/tmp/gen.py", "content": "print(1)\n"},
        "/tmp",
        old_text="",
    )
    assert preview is not None
    _path, old, new, entries = preview
    assert old == ""
    assert "print(1)" in new
    assert any(kind == "add" for kind, _ in entries)


@pytest.mark.anyio
async def test_diff_view_composes():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.diff_view import DiffView, render_unified_diff
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    entries = render_unified_diff("a\n", "b\n", path="x.py")

    class DiffApp(App):
        def compose(self):
            yield DiffView(entries, path="x.py")

    app = DiffApp()
    async with app.run_test() as pilot:
        view = app.query_one(DiffView)
        assert "+1 −1" in str(view.query_one(".diff-view-stat").content)
        body = view.query_one(".diff-view-body").content
        assert "x.py" in str(view.query_one(".diff-view-path").content)
        assert "+1 −1" in str(body) or "+1 −1" in str(
            view.query_one(".diff-view-stat").content
        )
        await pilot.pause()


@pytest.mark.anyio
async def test_approval_modal_renders_diff():
    """The approval modal shows a DIFF PREVIEW section when entries exist."""
    try:
        from textual.app import App

        from rlm_optimized.tui_app import ApprovalModal
        from rlm_optimized.tui_widgets.diff_view import render_unified_diff
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    entries = render_unified_diff("x = 1\n", "x = 2\n", path="/tmp/a.py")

    class ModalApp(App):
        def compose(self):
            yield ApprovalModal(
                "WRITE_FILE",
                "confirm",
                {"path": "/tmp/a.py"},
                diff_entries=entries,
                diff_path="/tmp/a.py",
            )

    app = ModalApp()
    async with app.run_test() as pilot:
        modal = app.query_one(ApprovalModal)
        label = modal.query_one("#approval-diff-label")
        assert "DIFF PREVIEW" in str(label.content)
        diff = modal.query_one("#approval-diff")
        assert "x = 2" in str(diff.content)
        assert "[green]+x = 2" in str(diff.content)
        await pilot.pause()


@pytest.mark.anyio
async def test_approval_modal_omits_diff_when_empty():
    try:
        from textual.app import App

        from rlm_optimized.tui_app import ApprovalModal
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class ModalApp(App):
        def compose(self):
            yield ApprovalModal("RUN_COMMAND", "auto", {"command": "ls"})

    app = ModalApp()
    async with app.run_test() as pilot:
        modal = app.query_one(ApprovalModal)
        assert len(modal.query("#approval-diff")) == 0
        await pilot.pause()


@pytest.mark.anyio
async def test_app_write_step_renders_diff_card():
    """A successful WRITE_FILE step mounts a DiffView card with real content."""
    try:
        from unittest.mock import MagicMock

        from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized, Step
        from rlm_optimized.tui_app import TorchlightApp
        from rlm_optimized.tui_widgets.diff_view import DiffView
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    import tempfile

    def _make_file(root: str, name: str, content: str) -> str:
        target = os.path.join(root, name)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return target

    with tempfile.TemporaryDirectory() as tmpdir:
        target = _make_file(tmpdir, "a.py", "x = 1\n")

        engine = MagicMock(spec=RLMEngineOptimized)
        engine.project_root = tmpdir
        engine._total_llm_calls = 0
        engine.max_depth = 10
        app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
        async with app.run_test() as pilot:
            container = app.query_one("#chat-container")
            app._capture_prewrite_snapshot("WRITE_FILE", {"path": target})
            step = Step(
                step_number=1,
                depth=0,
                action="tool",
                thinking="write",
                content="",
                result="OK: wrote a.py",
                tool_name="WRITE_FILE",
                tool_args={"path": target, "content": "x = 2\n"},
            )
            app._handle_step(step)
            await pilot.pause()
            await pilot.pause()
            diffs = container.query(DiffView)
            assert len(diffs) == 1
            assert "a.py" in str(diffs[0].query_one(".diff-view-path").content)
            body = str(diffs[0].query_one(".diff-view-body").content)
            assert "x = 2" in body
            await pilot.pause()
