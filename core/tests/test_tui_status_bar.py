"""Tests for Phase-4 consolidated status bar (gauge + segments widget)."""

import pytest


def test_gauge_markup_empty():
    from rlm_optimized.tui_widgets.status_bar import GAUGE_WIDTH, gauge_markup

    m = gauge_markup(0)
    assert m.startswith("[bold green]")
    assert m.count("░") == GAUGE_WIDTH
    assert "█" not in m


def test_gauge_markup_full():
    from rlm_optimized.tui_widgets.status_bar import GAUGE_WIDTH, gauge_markup

    m = gauge_markup(100)
    assert m.startswith("[bold red]")
    assert m.count("█") == GAUGE_WIDTH
    assert "░" not in m


def test_gauge_markup_proportional():
    from rlm_optimized.tui_widgets.status_bar import gauge_markup

    m = gauge_markup(50, width=8)
    assert m.count("█") == 4
    assert m.count("░") == 4
    assert "[bold yellow]" in m


def test_gauge_markup_color_escalation():
    from rlm_optimized.tui_widgets.status_bar import gauge_markup

    assert gauge_markup(0).startswith("[bold green]")
    assert gauge_markup(49.9).startswith("[bold green]")
    assert gauge_markup(50).startswith("[bold yellow]")
    assert gauge_markup(74.9).startswith("[bold yellow]")
    assert gauge_markup(75).startswith("[bold red]")


def test_gauge_markup_clamps_out_of_range():
    from rlm_optimized.tui_widgets.status_bar import GAUGE_WIDTH, gauge_markup

    assert gauge_markup(-20) == gauge_markup(0)
    assert gauge_markup(200) == gauge_markup(100)
    assert gauge_markup(0).count("░") == GAUGE_WIDTH
    assert gauge_markup(100).count("█") == GAUGE_WIDTH


def test_build_status_segments_defaults():
    from rlm_optimized.tui_widgets.status_bar import build_status_segments

    seg = build_status_segments()
    assert set(seg) == {
        "sb-state",
        "sb-model",
        "sb-gauge",
        "sb-tps",
        "sb-tokens",
        "sb-errors",
        "sb-git",
    }
    assert "IDLE" in seg["sb-state"]
    assert "CLOUD" in seg["sb-state"]
    assert "-- tps" in seg["sb-tps"]
    assert "no-git" in seg["sb-git"]
    assert "✗ 0" in seg["sb-errors"]
    assert "0/0" in seg["sb-tokens"]


def test_build_status_segments_populated():
    from rlm_optimized.tui_widgets.status_bar import build_status_segments

    seg = build_status_segments(
        state="TOOL",
        model="a[b]c",
        pct=80,
        tokens=1024,
        ctx_max=12288,
        tps=12.3,
        errors=2,
        branch="main",
        port=8080,
        server_online=True,
        is_running=True,
    )
    assert "EXECUTING TOOL" in seg["sb-state"]
    assert "ON:8080" in seg["sb-state"]
    assert seg["sb-model"] == r"a\[b]c"
    assert "12.3 tps" in seg["sb-tps"]
    assert "1,024/12,288" in seg["sb-tokens"]
    assert "✗" in seg["sb-errors"]
    assert "main" in seg["sb-git"]


def test_build_status_segments_server_offline_and_branch_escape():
    from rlm_optimized.tui_widgets.status_bar import build_status_segments

    seg = build_status_segments(state="IDLE", port=8080, server_online=False)
    assert "OFF:8080" in seg["sb-state"]
    seg2 = build_status_segments(branch="feat/x[y]")
    assert r"feat/x\[y]" in seg2["sb-git"]


def test_build_status_segments_running_no_tps_yet():
    from rlm_optimized.tui_widgets.status_bar import build_status_segments

    seg = build_status_segments(state="THINKING", is_running=True, tps=0)
    assert "tps…" in seg["sb-tps"]


@pytest.mark.anyio
async def test_status_bar_composes_and_updates():
    try:
        from textual.app import App

        from rlm_optimized.tui_widgets.status_bar import StatusBar
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class BarApp(App):
        def compose(self):
            yield StatusBar(id="status-bar")

    app = BarApp()
    async with app.run_test() as pilot:
        bar = app.query_one("#status-bar", StatusBar)
        assert app.query_one("#sb-state") is not None
        assert app.query_one("#sb-git") is not None
        bar.update_status(
            state="THINKING",
            model="qwen2.5",
            pct=60,
            tokens=100,
            ctx_max=12288,
            tps=0,
            errors=0,
            branch="dev",
            port=8080,
            server_online=True,
            is_running=True,
        )
        await pilot.pause()
        state_text = str(app.query_one("#sb-state").render())
        assert "THINKING" in state_text
        assert "ON:8080" in state_text
        assert str(app.query_one("#sb-model").render()) == "qwen2.5"
        await pilot.pause()
