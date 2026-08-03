"""Tests for Phase-6 theme consistency and responsive layout classes.

Covers:
- CSS uses theme variables instead of hardcoded hex values.
- Responsive layout classes are applied correctly on resize.
- Short-terminal class applied for terminals < 24 rows.
"""

import inspect
import os
import re
import tempfile
from unittest.mock import MagicMock


def _make_app():
    from rlm_optimized.tui_app import TorchlightApp

    engine = MagicMock(spec=MagicMock)
    engine.project_root = tempfile.gettempdir()
    engine._total_llm_calls = 0
    engine.max_depth = 10
    return TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")


def _tcss_path():
    from rlm_optimized.tui_app import TorchlightApp

    module_dir = os.path.dirname(inspect.getfile(TorchlightApp))
    return os.path.join(module_dir, "tui_app.tcss")


def _read_css():
    with open(_tcss_path(), encoding="utf-8") as fh:
        return fh.read()


def test_no_hardcoded_hex_in_css():
    """Ensure CSS doesn't contain hardcoded hex colors."""
    css_text = _read_css()
    hex_pattern = re.compile(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b')
    matches = hex_pattern.findall(css_text)
    assert len(matches) == 0, f"Found hardcoded hex colors: {matches}"


def test_uses_theme_variables():
    """Ensure CSS uses theme variables like $background."""
    css_text = _read_css()
    assert "$background" in css_text


def test_responsive_classes_defined_in_css():
    """Ensure CSS has rules for responsive terminal classes."""
    css_text = _read_css()
    assert "narrow-terminal" in css_text
    assert "short-terminal" in css_text


async def test_responsive_classes_applied_on_resize():
    """Responsive classes are applied when terminal is narrow."""
    app = _make_app()
    async with app.run_test(size=(70, 20)) as pilot:
        app._apply_responsive_layout()
        await pilot.pause()
        screen = app.screen
        assert screen.has_class("narrow-terminal")
        assert not screen.has_class("very-narrow-terminal")

    app2 = _make_app()
    async with app2.run_test(size=(40, 20)) as pilot:
        app2._apply_responsive_layout()
        await pilot.pause()
        screen = app2.screen
        assert screen.has_class("very-narrow-terminal")


async def test_short_terminal_class_applied():
    """Short-terminal class applied when height < 24."""
    app = _make_app()
    async with app.run_test(size=(100, 20)) as pilot:
        app._apply_responsive_layout()
        await pilot.pause()
        screen = app.screen
        assert screen.has_class("short-terminal")
