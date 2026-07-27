"""
Tests for WebOutcomeInspector and INSPECT_WEB tool.
"""

import tempfile
from pathlib import Path
import pytest

from core.execution.web_inspector import (
    WebOutcomeInspector,
    WebInspectionResult,
    EphemeralHTTPServer,
    StaticHTMLValidator,
)
from core.tools.registry import get_tool_registry, ToolRegistry


def test_ephemeral_http_server():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "index.html").write_text("<h1>Test</h1>", encoding="utf-8")

        server = EphemeralHTTPServer(tmp_path)
        url = server.start()
        assert url.startswith("http://127.0.0.1:")
        assert server.port > 0

        server.stop()
        assert server.server is None


def test_static_html_validator():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        html_file = tmp_path / "index.html"
        html_file.write_text("""<!DOCTYPE html>
<html>
<head>
    <title>Canvas Snake Game</title>
    <script src="missing_game.js"></script>
    <link rel="stylesheet" href="missing_style.css">
</head>
<body>
    <canvas id="gameCanvas" width="400" height="400"></canvas>
</body>
</html>""", encoding="utf-8")

        validator = StaticHTMLValidator(tmp_path)
        validator.feed(html_file.read_text(encoding="utf-8"))

        assert validator.title == "Canvas Snake Game"
        assert len(validator.found_canvases) == 1
        assert len(validator.missing_files) == 2
        assert any("missing_game.js" in item for item in validator.missing_files)
        assert any("missing_style.css" in item for item in validator.missing_files)


def test_web_outcome_inspector_static_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        html_file = tmp_path / "clean.html"
        html_file.write_text("""<!DOCTYPE html>
<html>
<head><title>Clean Page</title></head>
<body><h1>Hello World</h1></body>
</html>""", encoding="utf-8")

        inspector = WebOutcomeInspector(output_dir=tmp_path / "shots")
        result = inspector.inspect(str(html_file), wait_ms=100)

        assert isinstance(result, WebInspectionResult)
        assert result.status in ("PASS", "FAIL")
        markdown = result.to_markdown()
        assert "Web Inspection Outcome" in markdown


def test_inspect_web_tool_registration():
    registry = get_tool_registry()
    tool_def = registry.get("INSPECT_WEB")

    assert tool_def is not None
    assert tool_def.name == "INSPECT_WEB"
    assert tool_def.risk_level == "auto"
    assert tool_def.category == "web"
