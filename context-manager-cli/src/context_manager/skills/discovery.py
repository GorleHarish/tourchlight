"""
Skill Discovery - On-demand skill retrieval to minimize context.

Instead of injecting all skill descriptions, we provide:
1. Core tool summaries (minimal)
2. A discovery mechanism for skills

The LLM learns skills dynamically when it needs them.
"""

import asyncio
import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if TYPE_CHECKING:
    from context_manager.skills.base import SkillResult
else:
    SkillResult = None

# Compact skill registry for fast lookup (loaded once at startup)
_SKILL_INDEX: Dict[str, Dict[str, str]] = {}
_SKILL_CACHE_LOADED = False


def _load_skill_index(skills_dir: str) -> Dict[str, Dict[str, str]]:
    """Build a minimal index of skills for fast discovery."""
    global _SKILL_INDEX, _SKILL_CACHE_LOADED
    
    if _SKILL_CACHE_LOADED:
        return _SKILL_INDEX
    
    _SKILL_INDEX = {}
    
    if not os.path.isdir(skills_dir):
        _SKILL_CACHE_LOADED = True
        return _SKILL_INDEX
    
    for filename in os.listdir(skills_dir):
        full_path = os.path.join(skills_dir, filename)
        
        if os.path.isdir(full_path):
            skill_md = os.path.join(full_path, "SKILL.md")
            if os.path.isfile(skill_md):
                try:
                    with open(skill_md, encoding="utf-8") as f:
                        content = f.read().strip()
                    lines = content.splitlines()
                    title = next((l[2:].strip() for l in lines if l.startswith("# ")), filename)
                    desc = next((l.strip() for l in lines[1:5] if l.strip() and not l.startswith("#")), "")
                    icon = "📘"
                    for line in lines:
                        if line.lower().startswith("icon:"):
                            icon = line.split(":", 1)[1].strip() or "📘"
                            break
                    _SKILL_INDEX[filename] = {
                        "name": filename.replace("-", "_").lower(),
                        "title": title,
                        "desc": desc[:100],
                        "icon": icon,
                        "path": skill_md
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
                
                name = icon = desc = None
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
                
                if name:
                    _SKILL_INDEX[name.upper()] = {
                        "name": name,
                        "title": name,
                        "desc": (desc or "")[:100],
                        "icon": icon or "🔧",
                        "path": full_path
                    }
        except Exception:
            pass
    
    _SKILL_CACHE_LOADED = True
    return _SKILL_INDEX


def discover_skills(query: str = "", category: str = "") -> Dict[str, Any]:
    """
    Discover available skills based on query or category.
    
    This is called ON-DEMAND when the LLM needs skill help,
    not pre-injected into every prompt.
    
    Args:
        query: Search term (matches name or description)
        category: Filter by category (workflow, vcs, utility, etc.)
    
    Returns:
        Dict with matching skills and compact summaries
    """
    skills_dir = os.path.join(os.getcwd(), "agent_skills")
    _load_skill_index(skills_dir)
    
    results = []
    query_lower = query.lower() if query else ""
    
    for skill_id, info in _SKILL_INDEX.items():
        name = info["name"]
        desc = info["desc"]
        
        matches_query = not query_lower or (
            query_lower in name.lower() or 
            query_lower in desc.lower() or
            query_lower in info.get("title", "").lower()
        )
        
        if matches_query:
            results.append({
                "name": name,
                "title": info.get("title", name),
                "desc": desc,
                "icon": info.get("icon", "🔧"),
                "use": f"/{name.lower()} <task>"
            })
    
    return {
        "count": len(results),
        "skills": results,
        "tip": "Use /<skill_name> <task> to invoke. Example: /tdd create a calculator"
    }


def get_compact_skill_list(limit: int = 10) -> str:
    """Get ultra-compact skill list for system prompt."""
    skills_dir = os.path.join(os.getcwd(), "agent_skills")
    _load_skill_index(skills_dir)
    
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
