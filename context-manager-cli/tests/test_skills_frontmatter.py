from pathlib import Path

import pytest

from context_manager.skills.base import (
    MarkdownDocumentSkill,
    SkillResult,
    _extract_markdown_skill_metadata,
    create_default_registry,
    get_skill_directories,
    parse_frontmatter,
)
from context_manager.skills.discovery import _load_skill_index, discover_skills


def test_parse_frontmatter_valid():
    content = """---
name: db-migrator
description: Run postgres migrations safely
icon: 🐘
risk_level: confirm
category: database
tags: [postgres, sql, db]
---
# Database Migrator
Some instructions here.
"""
    meta, body = parse_frontmatter(content)
    assert meta["name"] == "db-migrator"
    assert meta["description"] == "Run postgres migrations safely"
    assert meta["icon"] == "🐘"
    assert meta["risk_level"] == "confirm"
    assert meta["category"] == "database"
    assert meta["tags"] == ["postgres", "sql", "db"]
    assert "# Database Migrator\nSome instructions here." in body


def test_parse_frontmatter_missing():
    content = """# Plain Document
No YAML header here.
"""
    meta, body = parse_frontmatter(content)
    assert meta == {}
    assert body == content.strip()


def test_extract_markdown_skill_metadata_frontmatter(tmp_path: Path):
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("""---
name: custom-release-bot
description: Automates git tags and release notes
icon: 🚀
risk_level: confirm
category: workflow
tags: [git, release]
---
# Release Bot
Instructions...
""", encoding="utf-8")

    name, desc, icon, risk, cat, tags = _extract_markdown_skill_metadata(str(skill_file))
    assert name == "custom_release_bot"
    assert desc == "Automates git tags and release notes"
    assert icon == "🚀"
    assert risk == "confirm"
    assert cat == "workflow"
    assert "git" in tags
    assert "release" in tags


def test_extract_markdown_skill_metadata_legacy_fallback(tmp_path: Path):
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("""# Legacy Skill Title
Icon: ⚡
This is the first paragraph describing the legacy skill.

## Section
More text...
""", encoding="utf-8")

    name, desc, icon, risk, cat, tags = _extract_markdown_skill_metadata(str(skill_file))
    assert name == "legacy_skill_title"
    assert desc == "This is the first paragraph describing the legacy skill."
    assert icon == "⚡"
    assert risk == "auto"
    assert cat == "docs"


def test_multi_root_skill_discovery(tmp_path: Path):
    # Setup mock .agents/skills and skills/ directories
    agents_skills = tmp_path / ".agents" / "skills" / "security-scanner"
    agents_skills.mkdir(parents=True)
    (agents_skills / "SKILL.md").write_text("""---
name: security-scanner
description: Audits dependencies and code for CVEs
icon: 🛡️
risk_level: auto
category: security
tags: [cve, audit]
---
# Security Scanner
Audit instructions.
""", encoding="utf-8")

    # Verify get_skill_directories finds the path
    dirs = get_skill_directories(str(tmp_path))
    assert str(agents_skills.parent) in dirs

    # Verify create_default_registry registers it
    reg = create_default_registry(workspace_root=str(tmp_path))
    skill = reg.get("security_scanner")
    assert skill is not None
    assert isinstance(skill, MarkdownDocumentSkill)
    assert skill.name == "security_scanner"
    assert skill.icon == "🛡️"
    assert skill.risk_level == "auto"
    assert skill.category == "security"

    # Verify discovery on demand
    _load_skill_index(skills_dirs=dirs, reload=True)
    res = discover_skills(query="cve", reload=False)
    assert any(s["name"] == "security_scanner" for s in res["skills"])


@pytest.mark.asyncio
async def test_markdown_document_skill_execution(tmp_path: Path):
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("""# Helpful Guide
Step 1: Check inputs.
Step 2: Run verification.
""", encoding="utf-8")

    skill = MarkdownDocumentSkill(
        name="helpful_guide",
        description="A helpful guide",
        icon="📖",
        file_path=str(skill_file),
    )

    res: SkillResult = await skill.execute({"request": "How do I verify?"})
    assert res.success is True
    assert "## Skill Guidance" in res.output
    assert "Step 1: Check inputs." in res.output
    assert "## Current Request\nHow do I verify?" in res.output
