"""
Unit and Integration Tests for HTML Game Player & Autonomous Self-Improver.
"""

import tempfile
from pathlib import Path
import pytest

from core.execution.game_inspector import (
    HtmlGamePlayer,
    GameOutcomeResult,
    GameInputEvent,
    get_process_memory_mb,
)
from core.execution.game_self_improver import GameSelfImprover, GameSelfImprovementReport
from core.tools.registry import get_tool_registry


def test_game_player_clean_canvas_static():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        game_file = tmp_path / "game.html"
        game_file.write_text("""<!DOCTYPE html>
<html>
<head><title>Canvas Test Game</title></head>
<body>
    <canvas id="gameCanvas" width="400" height="400"></canvas>
    <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        let x = 10;
        function update() {
            x += 2;
            ctx.clearRect(0, 0, 400, 400);
            ctx.fillStyle = 'red';
            ctx.fillRect(x, 50, 50, 50);
            requestAnimationFrame(update);
        }
        update();
    </script>
</body>
</html>""", encoding="utf-8")

        progress_events = []
        def on_prog(stage, msg):
            progress_events.append((stage, msg))

        player = HtmlGamePlayer(output_dir=tmp_path / "shots")
        result = player.play_and_verify(str(game_file), duration_ms=500, on_progress=on_prog)

        assert isinstance(result, GameOutcomeResult)
        assert result.status in ("PASS", "FAIL")
        assert result.memory_mb > 0.0
        assert len(progress_events) >= 3
        assert any(e[0] == "INIT" for e in progress_events)
        markdown = result.to_markdown()
        assert "HTML Game Verification" in markdown
        assert "RSS Memory Load" in markdown


def test_game_self_improver_repair_context_typo():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        game_file = tmp_path / "typo_game.html"
        # Has getContext("2D") uppercase typo which throws exception
        game_file.write_text("""<!DOCTYPE html>
<html>
<head><title>Typo Game</title></head>
<body>
    <canvas id="gameCanvas" width="200" height="200"></canvas>
    <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2D');
        ctx.fillRect(0, 0, 50, 50);
    </script>
</body>
</html>""", encoding="utf-8")

        progress_events = []
        def on_prog(stage, msg):
            progress_events.append((stage, msg))

        improver = GameSelfImprover(project_root=tmp_path)
        report = improver.run_self_improvement_cycle(
            str(game_file), max_iterations=2, duration_ms=400, on_progress=on_prog
        )

        assert isinstance(report, GameSelfImprovementReport)
        assert report.total_iterations >= 1
        assert any(e[0] == "CYCLE_START" for e in progress_events)
        assert any(e[0] == "DIAGNOSE" for e in progress_events)
        # Verify fix was applied in source file
        repaired_text = game_file.read_text(encoding="utf-8")
        assert "getContext('2d')" in repaired_text or "getContext(\"2d\")" in repaired_text


def test_game_self_improver_repair_frame_typo():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        game_file = tmp_path / "frame_typo_game.html"
        # Has requestAniamtionFrame typo
        game_file.write_text("""<!DOCTYPE html>
<html>
<head><title>Frame Typo Game</title></head>
<body>
    <canvas id="gameCanvas" width="200" height="200"></canvas>
    <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        function draw() {
            ctx.fillRect(10, 10, 20, 20);
            requestAniamtionFrame(draw);
        }
        draw();
    </script>
</body>
</html>""", encoding="utf-8")

        improver = GameSelfImprover(project_root=tmp_path)
        report = improver.run_self_improvement_cycle(str(game_file), max_iterations=2, duration_ms=400)

        assert isinstance(report, GameSelfImprovementReport)
        repaired_text = game_file.read_text(encoding="utf-8")
        assert "requestAnimationFrame" in repaired_text


def test_process_memory_helper():
    mem = get_process_memory_mb()
    assert isinstance(mem, float)
    assert mem > 0.0


def test_game_tools_registered():
    registry = get_tool_registry()

    pv_tool = registry.get("PLAY_AND_VERIFY_GAME")
    assert pv_tool is not None
    assert pv_tool.name == "PLAY_AND_VERIFY_GAME"
    assert pv_tool.risk_level == "auto"
    assert pv_tool.category == "web"

    si_tool = registry.get("SELF_IMPROVE_GAME")
    assert si_tool is not None
    assert si_tool.name == "SELF_IMPROVE_GAME"
    assert si_tool.risk_level == "confirm"
    assert si_tool.category == "web"
