"""
Skill Discovery - On-demand skill retrieval to minimize context.

Instead of injecting all skill descriptions, we provide:
1. Core tool summaries (minimal)
2. A discovery mechanism for skills

The LLM learns skills dynamically when it needs them.
"""

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if TYPE_CHECKING:
    from context_manager.skills.base import SkillResult
else:
    SkillResult = None

try:
    from .base import _extract_markdown_skill_metadata, get_skill_directories
except (ImportError, ValueError):
    from context_manager.skills.base import _extract_markdown_skill_metadata, get_skill_directories

# Compact skill registry for fast lookup (loaded once at startup)
_SKILL_INDEX: Dict[str, Dict[str, Any]] = {}
_SKILL_CACHE_LOADED = False
_SKILL_CACHE_DIRS: Optional[List[str]] = None


def _load_skill_index(skills_dirs: Optional[List[str]] = None, reload: bool = False) -> Dict[str, Dict[str, Any]]:
    """Build a minimal index of skills across standard directories for fast discovery."""
    global _SKILL_INDEX, _SKILL_CACHE_LOADED, _SKILL_CACHE_DIRS

    if _SKILL_CACHE_LOADED and not reload:
        if skills_dirs is None or _SKILL_CACHE_DIRS == list(skills_dirs):
            return _SKILL_INDEX

    dirs = skills_dirs if skills_dirs is not None else get_skill_directories()

    _SKILL_INDEX = {}
    _SKILL_CACHE_DIRS = list(dirs)

    for s_dir in dirs:
        if not os.path.isdir(s_dir):
            continue

        try:
            entries = sorted(os.listdir(s_dir))
        except Exception:
            continue

        for filename in entries:
            full_path = os.path.join(s_dir, filename)

            if os.path.isdir(full_path):
                skill_md = os.path.join(full_path, "SKILL.md")
                if not os.path.isfile(skill_md):
                    skill_md = os.path.join(full_path, "skill.md")
                if os.path.isfile(skill_md):
                    try:
                        name, desc, icon, risk_level, category, tags = _extract_markdown_skill_metadata(skill_md)
                        key = name.upper()
                        if key not in _SKILL_INDEX:
                            _SKILL_INDEX[key] = {
                                "name": name,
                                "title": name,
                                "desc": desc[:100],
                                "icon": icon,
                                "path": skill_md,
                                "risk_level": risk_level,
                                "category": category,
                                "tags": tags,
                            }
                    except Exception:
                        pass
                continue

            if filename.endswith(".md") and not filename.startswith("__") and filename.upper() != "README.MD":
                try:
                    name, desc, icon, risk_level, category, tags = _extract_markdown_skill_metadata(full_path)
                    key = name.upper()
                    if key not in _SKILL_INDEX:
                        _SKILL_INDEX[key] = {
                            "name": name,
                            "title": name,
                            "desc": desc[:100],
                            "icon": icon,
                            "path": full_path,
                            "risk_level": risk_level,
                            "category": category,
                            "tags": tags,
                        }
                except Exception:
                    pass
                continue

            if not filename.endswith(".py") or filename.startswith("__"):
                continue

            try:
                import ast
                source = open(full_path, encoding="utf-8").read()
                tree = ast.parse(source, filename=filename)

                for node in ast.walk(tree):
                    if not isinstance(node, ast.ClassDef):
                        continue
                    bases = [getattr(b, "id", None) for b in node.bases]
                    if "BaseSkill" not in bases:
                        continue

                    name = icon = desc = cat = risk = None
                    for stmt in node.body:
                        if not isinstance(stmt, ast.Assign):
                            continue
                        for target in stmt.targets:
                            if not isinstance(target, ast.Name):
                                continue
                            if target.id == "name" and isinstance(stmt.value, ast.Constant):
                                name = stmt.value.value
                            elif target.id == "icon" and isinstance(stmt.value, ast.Constant):
                                icon = stmt.value.value
                            elif target.id == "description" and isinstance(stmt.value, ast.Constant):
                                desc = stmt.value.value
                            elif target.id == "category" and isinstance(stmt.value, ast.Constant):
                                cat = stmt.value.value
                            elif target.id == "risk_level" and isinstance(stmt.value, ast.Constant):
                                risk = stmt.value.value

                    if name and name.upper() not in _SKILL_INDEX:
                        _SKILL_INDEX[name.upper()] = {
                            "name": name,
                            "title": name,
                            "desc": (desc or "")[:100],
                            "icon": icon or "🔧",
                            "path": full_path,
                            "category": cat or "skill",
                            "risk_level": risk or "confirm",
                            "tags": [],
                        }
            except Exception:
                pass

    _SKILL_CACHE_LOADED = True
    return _SKILL_INDEX


def discover_skills(
    query: str = "",
    category: str = "",
    reload: bool = False,
    project_root: Optional[str] = None,
    workspace_root: Optional[str] = None,
    skills_dirs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Discover available skills based on query or category across all standard directories.

    This is called ON-DEMAND when the LLM needs skill help,
    not pre-injected into every prompt.

    Args:
        query: Search term (matches name, description, title, or tags)
        category: Filter by category (workflow, vcs, utility, docs, etc.)
        reload: Force reload the skill index cache
        project_root: Optional project root path to scan
        workspace_root: Alias for project_root
        skills_dirs: Optional explicit list of skill directories

    Returns:
        Dict with matching skills and compact summaries
    """
    root = project_root or workspace_root
    if skills_dirs is None and root is not None:
        skills_dirs = get_skill_directories(root)
    _load_skill_index(skills_dirs=skills_dirs, reload=reload)

    results = []
    query_lower = query.lower() if query else ""
    cat_lower = category.lower() if category else ""

    for skill_id, info in _SKILL_INDEX.items():
        name = info["name"]
        desc = info["desc"]
        s_cat = str(info.get("category", "")).lower()
        tags = [str(t).lower() for t in info.get("tags", [])]

        if cat_lower and s_cat != cat_lower and cat_lower not in tags:
            continue

        matches_query = not query_lower or (
            query_lower in name.lower() or
            query_lower in desc.lower() or
            query_lower in info.get("title", "").lower() or
            any(query_lower in t for t in tags)
        )

        if matches_query:
            results.append({
                "name": name,
                "title": info.get("title", name),
                "desc": desc,
                "icon": info.get("icon", "🔧"),
                "category": info.get("category", "skill"),
                "risk_level": info.get("risk_level", "auto"),
                "use": f"/{name.lower()} <task>"
            })

    return {
        "count": len(results),
        "skills": results,
        "tip": "Use /<skill_name> <task> to invoke. Example: /tdd create a calculator"
    }


def get_compact_skill_list(limit: int = 10) -> str:
    """Get ultra-compact skill list for system prompt."""
    _load_skill_index()

    if not _SKILL_INDEX:
        return ""

    lines = ["## AVAILABLE SKILLS (discover with DISCOVER_SKILLS)"]
    for i, (skill_id, info) in enumerate(list(_SKILL_INDEX.items())[:limit]):
        name = info["name"]
        desc = info["desc"][:50]
        lines.append(f"- {name}: {desc}...")

    if len(_SKILL_INDEX) > limit:
        lines.append(f"... and {len(_SKILL_INDEX) - limit} more (use DISCOVER_SKILLS to find)")

    return "\n".join(lines)


def get_skill_executor():
    """Lazy import to avoid circular deps."""
    from src.context_manager.skills.unified import create_unified_registry
    return create_unified_registry()


async def execute_skill_by_name(name: str, args: Dict[str, Any]) -> "SkillResult":
    """Execute a skill by name, loading it on demand."""
    registry = get_skill_executor()
    skill_name_upper = name.upper()
    skill_name_lower = name.lower()

    skill = registry.get(skill_name_upper) or registry.get(skill_name_lower)
    if skill:
        return await registry.execute_skill(skill_name_upper, args)

    return SkillResult(
        success=False,
        output="",
        error=f"Skill '{name}' not found. Use DISCOVER_SKILLS to find available skills."
    )


# CLI interface for testing
if __name__ == "__main__":
    print("=== Skill Discovery ===")
    print()

    print("All skills:")
    result = discover_skills()
    for s in result["skills"]:
        print(f"  {s['icon']} {s['name']}: {s['desc']}")

    print()
    print("Search 'test':")
    result = discover_skills(query="test")
    for s in result["skills"]:
        print(f"  {s['icon']} {s['name']}")

    print()
    print("=== Compact List ===")
    print(get_compact_skill_list(limit=5))
