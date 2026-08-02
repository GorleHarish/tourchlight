"""Tests for Phase-4 git-aware file tree (porcelain parsing + label decoration)."""

import tempfile
from pathlib import Path

import pytest


def test_normalize_status_code():
    from rlm_optimized.tui_widgets.file_tree import normalize_status_code

    assert normalize_status_code("??") == "??"
    assert normalize_status_code("M ") == "M"
    assert normalize_status_code(" M") == "M"
    assert normalize_status_code("MM") == "M"
    assert normalize_status_code("A ") == "A"
    assert normalize_status_code(" D") == "D"
    assert normalize_status_code("R ") == "R"
    assert normalize_status_code("UU") == "U"
    assert normalize_status_code("AA") == "U"
    assert normalize_status_code("DD") == "U"
    assert normalize_status_code("  ") == ""
    assert normalize_status_code("") == ""


def test_parse_git_status_porcelain_basic():
    from rlm_optimized.tui_widgets.file_tree import parse_git_status_porcelain

    out = " M src/app.py\n?? new_file.py\nA  staged.py\n D gone.py\nMM both.py\n"
    result = parse_git_status_porcelain(out)
    assert result["src/app.py"] == "M"
    assert result["new_file.py"] == "??"
    assert result["staged.py"] == "A"
    assert result["gone.py"] == "D"
    assert result["both.py"] == "M"


def test_parse_git_status_porcelain_rename_takes_destination():
    from rlm_optimized.tui_widgets.file_tree import parse_git_status_porcelain

    result = parse_git_status_porcelain("R  old.py -> new.py\n")
    assert result["new.py"] == "R"
    assert "old.py" not in result


def test_parse_git_status_porcelain_quoted_path():
    from rlm_optimized.tui_widgets.file_tree import parse_git_status_porcelain

    result = parse_git_status_porcelain(' M "src/my file.py"\n')
    assert result["src/my file.py"] == "M"


def test_git_status_for_tree_uses_porcelain(monkeypatch):
    import rlm_optimized.tui_widgets.file_tree as ft

    captured = {}

    def fake_run(cmd, cwd=None, **kwargs):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        return _FakeProc(0, " M src/app.py\n?? new.py\n")

    monkeypatch.setattr(ft.subprocess, "run", fake_run)
    result = ft.git_status_for_tree("/some/root")
    assert result["src/app.py"] == "M"
    assert result["new.py"] == "??"
    assert captured["cmd"] == ["git", "status", "--porcelain"]
    assert captured["cwd"] == "/some/root"


def test_git_status_for_tree_non_repo_returns_empty(monkeypatch):
    import rlm_optimized.tui_widgets.file_tree as ft

    def fake_run(cmd, cwd=None, **kwargs):
        return _FakeProc(128, "", "fatal: not a git repository")

    monkeypatch.setattr(ft.subprocess, "run", fake_run)
    assert ft.git_status_for_tree("/some/root") == {}


def test_git_status_for_tree_exception_returns_empty(monkeypatch):
    import rlm_optimized.tui_widgets.file_tree as ft

    def fake_run(cmd, cwd=None, **kwargs):
        raise FileNotFoundError("no git")

    monkeypatch.setattr(ft.subprocess, "run", fake_run)
    assert ft.git_status_for_tree("/some/root") == {}


@pytest.mark.anyio
async def test_git_tree_decorates_file_labels():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.file_tree import GitFileTree
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p / "a.txt").write_text("a")
        (p / "b.py").write_text("b")
        (p / "sub").mkdir()
        (p / "sub" / "c.txt").write_text("c")

        class TreeApp(App):
            def compose(self):
                yield GitFileTree(tmp, id="tree")

        app = TreeApp()
        async with app.run_test() as pilot:
            tree = app.query_one("#tree", GitFileTree)
            tree._git_status = {"a.txt": "M", "sub/c.txt": "??"}
            tree.reload()
            await pilot.pause()
            await pilot.pause()

            root_labels = {str(c.label) for c in tree.root.children}
            assert "[M] a.txt" in root_labels
            assert "b.py" in root_labels
            assert "sub" in root_labels

            sub = next(c for c in tree.root.children if c.data.path.name == "sub")
            sub.expand()
            await pilot.pause()
            await pilot.pause()
            sub_labels = {str(c.label) for c in sub.children}
            assert "[U] c.txt" in sub_labels
            await pilot.pause()


class _FakeProc:
    def __init__(self, returncode, stdout, stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
