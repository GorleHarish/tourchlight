"""Tests for skill upload/import and TUI skills overview formatting."""

import sys
import tempfile
from pathlib import Path

import pytest

workspace_root = Path(__file__).resolve().parent.parent.parent
cli_src = workspace_root / "context-manager-cli" / "src"
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))
if str(cli_src) not in sys.path:
    sys.path.insert(0, str(cli_src))

from context_manager.skills.discovery import discover_skills
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Static

from rlm_optimized.tui_app import SkillUploadModal
from rlm_optimized.tui_widgets.format import (
    build_skills_overview_text,
    import_skill_file,
)


def test_import_markdown_skill_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "workspace"
        workspace.mkdir()

        # Create external source skill file
        ext_skill = Path(tmpdir) / "my_custom_tool.md"
        ext_skill.write_text(
            """---
name: my_custom_tool
description: A great external custom tool.
icon: 🚀
risk: auto
category: tool
tags: [custom, helper]
---
# My Custom Tool
Instructions here.
""",
            encoding="utf-8",
        )

        ok, msg = import_skill_file(str(ext_skill), workspace_root=str(workspace))
        assert ok is True
        assert "my_custom_tool" in msg

        target_file = workspace / ".agents" / "skills" / "my_custom_tool" / "SKILL.md"
        assert target_file.exists()
        content = target_file.read_text(encoding="utf-8")
        assert "A great external custom tool." in content

        # Check discovery
        res = discover_skills(workspace_root=str(workspace), reload=True)
        assert res["count"] >= 1
        found = next((s for s in res["skills"] if s["name"] == "my_custom_tool"), None)
        assert found is not None
        assert found["icon"] == "🚀"
        assert found["risk_level"] == "auto"


def test_import_python_skill_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "workspace"
        workspace.mkdir()

        # Create external python skill
        ext_skill = Path(tmpdir) / "test_runner.py"
        ext_skill.write_text(
            """\"\"\"Test Runner Skill\"\"\"
name = "test_runner"
description = "Runs automated test suites"
icon = "🧪"
""",
            encoding="utf-8",
        )

        ok, msg = import_skill_file(str(ext_skill), workspace_root=str(workspace))
        assert ok is True
        assert "test_runner" in msg

        target_file = workspace / ".agents" / "skills" / "test_runner.py"
        assert target_file.exists()


def test_import_skill_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "workspace"
        workspace.mkdir()

        # Create external skill folder
        ext_dir = Path(tmpdir) / "complex_skill"
        ext_dir.mkdir()
        (ext_dir / "SKILL.md").write_text(
            """---
name: complex_skill
description: Multi-file complex skill
icon: 🧩
risk: confirm
---
# Complex Skill
""",
            encoding="utf-8",
        )
        (ext_dir / "helper.py").write_text("# helper", encoding="utf-8")

        ok, msg = import_skill_file(str(ext_dir), workspace_root=str(workspace))
        assert ok is True
        assert "complex_skill" in msg

        target_dir = workspace / ".agents" / "skills" / "complex_skill"
        assert (target_dir / "SKILL.md").exists()
        assert (target_dir / "helper.py").exists()

        # Test TUI skills overview formatting
        overview_text = build_skills_overview_text(str(workspace))
        assert "complex_skill" in overview_text
        assert "[CONFIRM]" in overview_text
        assert "[WORKSPACE]" in overview_text
        assert "/complex_skill" in overview_text


def test_import_skill_with_custom_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "workspace"
        workspace.mkdir()

        ext_skill = Path(tmpdir) / "random_notes.md"
        ext_skill.write_text("# Random Skill", encoding="utf-8")

        ok, msg = import_skill_file(
            str(ext_skill),
            custom_name="super-scanner",
            workspace_root=str(workspace),
        )
        assert ok is True
        assert "super_scanner" in msg
        target_file = workspace / ".agents" / "skills" / "super_scanner" / "SKILL.md"
        assert target_file.exists()


class ModalTestApp(App):
    def compose(self) -> ComposeResult:
        yield Button("Open Modal", id="open-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.push_screen(SkillUploadModal())


@pytest.mark.asyncio
async def test_skill_upload_modal():
    app = ModalTestApp()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.click("#open-btn")
        await pilot.pause()

        # Verify modal is mounted
        src_input = app.screen.query_one("#skill-src-input", Input)
        name_input = app.screen.query_one("#skill-custom-name-input", Input)
        assert src_input is not None
        assert name_input is not None

        # Test typing in input
        src_input.value = "/tmp/my-skill.md"
        await pilot.pause()
        preview = app.screen.query_one("#skill-dest-preview", Static)
        assert ".agents/skills/my_skill/SKILL.md" in str(preview.render())

        # Test cancel
        await pilot.press("escape")
        await pilot.pause(0.1)
        assert not isinstance(app.screen, SkillUploadModal)
