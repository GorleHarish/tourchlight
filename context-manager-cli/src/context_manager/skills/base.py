"""
Skills — external / plugin capabilities.

Skills are DIFFERENT from core tools:

  Core tools (tools/core.py)          Skills (skills/base.py + agent_skills/)
  ─────────────────────────────────   ────────────────────────────────────────
  Built-in, always available          Optional, loaded at startup or on demand
  Called via TOOL_NAME("arg")         Called via skill name in SkillRegistry
  Plain synchronous functions         Async classes with richer input schemas
  Shown as "Tools" in the UI          Shown as "Skills" in the UI
  No user installation needed         Can be dropped into agent_skills/ folder

Built-in skills provided here (always loaded):
  - GitSkill       — git operations with working-directory support
  - CalculatorSkill — safe arithmetic evaluation

External skills (loaded from agent_skills/*.py at startup):
  - Any class that subclasses BaseSkill and is placed in the agent_skills/ directory
"""

import asyncio
import ast
import operator
import os
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class SkillResult:
    success:  bool
    output:   str
    error:    Optional[str]       = None
    metadata: Optional[Dict[str, Any]] = None


# ── Base class ────────────────────────────────────────────────────────────────

class BaseSkill(ABC):
    """
    Base class for all external skills.

    Subclass this in agent_skills/*.py to add new capabilities.
    Drop the file in the agent_skills/ directory — it will be auto-loaded.
    """
    name:        str = "base_skill"
    description: str = "Base skill class"
    icon:        str = "🔧"
    risk_level:  str = "confirm"  # "auto", "confirm", or "review"
    category:    str = "skill"    # UI category

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> SkillResult:
        pass

    def get_prompt(self) -> str:
        """Return a short description shown in the Skills panel."""
        return f"{self.icon} **{self.name}**: {self.description}"


# ── Built-in skills ───────────────────────────────────────────────────────────

class GitSkill(BaseSkill):
    """Run git commands with a configurable working directory."""
    name        = "git"
    description = "Execute git commands (status, commit, log, diff, etc.)"
    icon        = "📦"
    risk_level  = "confirm"
    category    = "vcs"

    async def execute(self, input_data: Dict[str, Any]) -> SkillResult:
        try:
            command = input_data.get("command", "status")
            repo    = input_data.get("repo", ".")

            result = subprocess.run(
                f"git {command}",
                shell=True, capture_output=True, text=True, cwd=repo,
            )
            output = result.stdout or result.stderr
            return SkillResult(
                success=result.returncode == 0,
                output=output[:5000],
                error=f"Exit code {result.returncode}" if result.returncode != 0 else None,
            )
        except Exception as e:
            return SkillResult(success=False, output="", error=str(e))

    def get_prompt(self) -> str:
        return (
            f"{self.icon} **{self.name}**: {self.description}\n"
            "  Input: {command: 'log --oneline -10', repo: '.'}"
        )


class CalculatorSkill(BaseSkill):
    """Evaluate a mathematical expression safely using Python's AST."""
    name        = "calculate"
    description = "Safely evaluate a mathematical expression (+, -, *, /, **)"
    icon        = "🧮"
    risk_level  = "auto"
    category    = "utility"

    _OPERATORS = {
        ast.Add:  operator.add,
        ast.Sub:  operator.sub,
        ast.Mult: operator.mul,
        ast.Div:  operator.truediv,
        ast.Pow:  operator.pow,
    }

    def _eval(self, node: ast.expr):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            return self._OPERATORS[type(node.op)](self._eval(node.left), self._eval(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self._eval(node.operand)
        raise ValueError(f"Unsupported operation: {ast.dump(node)}")

    async def execute(self, input_data: Dict[str, Any]) -> SkillResult:
        expr = input_data.get("expression", "").strip()
        if not expr:
            return SkillResult(success=False, output="", error="No expression provided")
        try:
            tree   = ast.parse(expr, mode="eval")
            result = self._eval(tree.body)
            return SkillResult(
                success=True,
                output=f"{expr} = {result}",
                metadata={"result": result},
            )
        except Exception as e:
            return SkillResult(success=False, output="", error=str(e))

    def get_prompt(self) -> str:
        return (
            f"{self.icon} **{self.name}**: {self.description}\n"
            "  Input: {expression: '(5 * 2) / 3'}"
        )


class MarkdownDocumentSkill(BaseSkill):
    """
    Lightweight skill backed by agent_skills/<name>/SKILL.md.

    This lets users add modular markdown guidance without writing Python code.
    The skill returns the skill document plus any caller input so the agent can
    use it as structured guidance while keeping prompt injection lightweight.
    """
    risk_level = "auto"
    category   = "docs"

    def __init__(self, name: str, description: str, icon: str, file_path: str) -> None:
        self.name = name
        self.description = description
        self.icon = icon
        self._file_path = file_path

    def _read_markdown(self) -> str:
        with open(self._file_path, encoding="utf-8") as f:
            return f.read().strip()

    async def execute(self, input_data: Dict[str, Any]) -> SkillResult:
        try:
            content = self._read_markdown()
            request = (input_data.get("request") or input_data.get("prompt") or input_data.get("topic") or "").strip()
            if request:
                output = f"## Skill Guidance\n{content}\n\n## Current Request\n{request}"
            else:
                output = content

            # Keep skill output bounded so markdown skills do not explode local context.
            if len(output) > 8000:
                output = output[:8000] + "\n\n[... skill output truncated ...]"

            return SkillResult(
                success=True,
                output=output,
                metadata={"kind": "markdown_skill", "path": self._file_path},
            )
        except Exception as e:
            return SkillResult(success=False, output="", error=str(e))

    def get_prompt(self) -> str:
        return f"{self.icon} **{self.name}**: {self.description}"


def _extract_markdown_skill_metadata(file_path: str) -> tuple[str, str, str]:
    content = open(file_path, encoding="utf-8").read()
    lines = [line.strip() for line in content.splitlines()]

    title = ""
    description = ""
    icon = "📘"

    heading = next((line[2:].strip() for line in lines if line.startswith("# ")), "")
    if heading:
        title = heading

    for line in lines:
        if line.lower().startswith("icon:"):
            icon = line.split(":", 1)[1].strip() or icon
            break

    for line in lines:
        if not line or line.startswith("#") or line.lower().startswith("icon:"):
            continue
        description = line
        break

    slug = os.path.basename(os.path.dirname(file_path)) or os.path.splitext(os.path.basename(file_path))[0]
    skill_name = re.sub(r"[^a-z0-9_]+", "_", (title or slug).lower()).strip("_") or "markdown_skill"
    summary = description[:160] if description else f"Markdown skill from {os.path.basename(file_path)}"
    return skill_name, summary, icon


# ── Async helper ─────────────────────────────────────────────────────────────

def _run_async(coro):
    """
    Run an async coroutine safely regardless of whether an event loop is already running.
    Falls back to a thread pool if running in an existing event loop.
    """
    import concurrent.futures
    try:
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        return asyncio.run(coro)


# ── Registry ──────────────────────────────────────────────────────────────────

class SkillRegistry:
    """
    Registry for external skills.

    Does NOT contain core tools (READ_FILE, WRITE_FILE, etc.) —
    those live in tools/core.py and are always available.
    """

    def __init__(self) -> None:
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[BaseSkill]:
        return self._skills.get(name)

    def list_skills(self) -> List[BaseSkill]:
        return list(self._skills.values())

    def execute_sync(self, name: str, input_data: Dict[str, Any]) -> SkillResult:
        """Synchronous wrapper for use from non-async contexts."""
        skill = self._skills.get(name)
        if not skill:
            return SkillResult(success=False, output="", error=f"Unknown skill: {name}")
        return _run_async(skill.execute(input_data))

    async def execute(self, name: str, input_data: Dict[str, Any]) -> SkillResult:
        skill = self._skills.get(name)
        if not skill:
            return SkillResult(success=False, output="", error=f"Unknown skill: {name}")
        return await skill.execute(input_data)


# ── Default registry ──────────────────────────────────────────────────────────

# ── Lazy skill stub ──────────────────────────────────────────────────────────

class _LazySkill(BaseSkill):
    """
    A zero-cost placeholder registered at startup.

    Holds only the skill name, icon, and a one-line prompt string.
    The real skill module is NOT imported until the first execute() call.
    This keeps startup fast and avoids burning tokens on skills that are
    never invoked in a session.
    """

    def __init__(
        self,
        name: str,
        icon: str,
        prompt_line: str,
        file_path: str,
        class_name: str,
        risk_level: str = "confirm",
        category: str = "skill",
        description: str = "",
    ) -> None:
        self.name        = name
        self.icon        = icon
        self.description = description or f"{name} skill"
        self.risk_level  = risk_level
        self.category    = category
        self._prompt     = prompt_line
        self._file_path  = file_path
        self._class_name = class_name
        self._real: Optional[BaseSkill] = None  # populated on first call

    # Called every message via get_all_prompts() — must be free.
    def get_prompt(self) -> str:
        return self._prompt

    def _load(self) -> BaseSkill:
        """Import the real module and instantiate the skill class."""
        if self._real is not None:
            return self._real
        import importlib.util, sys
        module_name = f"_lazy_{self.name}"
        spec = importlib.util.spec_from_file_location(module_name, self._file_path)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load skill from {self._file_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        cls = getattr(module, self._class_name)
        self._real = cls()
        return self._real

    async def execute(self, input_data: Dict[str, Any]) -> SkillResult:
        """Trigger real load on first call, then delegate."""
        try:
            real = self._load()
            return await real.execute(input_data)
        except Exception as e:
            return SkillResult(success=False, output="", error=f"Skill load error: {e}")


def create_default_registry() -> SkillRegistry:
    """
    Build the default SkillRegistry with built-in skills,
    then register lazy stubs for any external skills in agent_skills/*.py.

    External skills are NOT imported at startup — the module is loaded only
    on the first execute() call. This keeps startup fast and avoids injecting
    unnecessary tokens for skills that are never used in a session.
    """
    import sys, importlib.util, inspect, ast as _ast

    registry = SkillRegistry()

    # ── Built-in skills (always loaded — tiny, always relevant) ──────────────
    registry.register(GitSkill())
    registry.register(CalculatorSkill())

    # ── External skills — lazy stubs ──────────────────────────────────────────
    cwd        = os.getcwd()
    skills_dir = os.path.join(cwd, "agent_skills")

    if not os.path.isdir(skills_dir):
        return registry

    if skills_dir not in sys.path:
        sys.path.insert(0, skills_dir)

    for filename in sorted(os.listdir(skills_dir)):
        full_path = os.path.join(skills_dir, filename)

        if os.path.isdir(full_path):
            skill_md = os.path.join(full_path, "SKILL.md")
            if os.path.isfile(skill_md):
                try:
                    skill_name, description, icon = _extract_markdown_skill_metadata(skill_md)
                    registry.register(MarkdownDocumentSkill(
                        name=skill_name,
                        description=description,
                        icon=icon,
                        file_path=skill_md,
                    ))
                except Exception as e:
                    print(f"⚠️  Failed to load markdown skill from {skill_md}: {e}")
            continue

        if not filename.endswith(".py") or filename.startswith("__"):
            continue

        file_path = full_path

        # ── Fast AST scan — read the file without executing it ────────────────
        # We extract three things without importing the module:
        #   1. The class name that subclasses BaseSkill
        #   2. The `name` class attribute (used as the registry key)
        #   3. The `icon` class attribute
        # If scanning fails for any reason we fall back to eager loading.
        try:
            source = open(file_path, encoding="utf-8").read()
            tree   = _ast.parse(source, filename=filename)

            skill_classes = []  # (class_name, name_val, icon_val, risk_level, category)
            for node in _ast.walk(tree):
                if not isinstance(node, _ast.ClassDef):
                    continue
                # Only classes that inherit from BaseSkill (by name)
                bases = [getattr(b, "id", None) for b in node.bases]
                if "BaseSkill" not in bases:
                    continue

                name_val = icon_val = risk_val = cat_val = desc_val = None
                for stmt in node.body:
                    if not isinstance(stmt, _ast.Assign):
                        continue
                    for target in stmt.targets:
                        if not isinstance(target, _ast.Name):
                            continue
                        if target.id == "name" and isinstance(stmt.value, _ast.Constant):
                            name_val = stmt.value.value
                        if target.id == "icon" and isinstance(stmt.value, _ast.Constant):
                            icon_val = stmt.value.value
                        if target.id == "risk_level" and isinstance(stmt.value, _ast.Constant):
                            risk_val = stmt.value.value
                        if target.id == "category" and isinstance(stmt.value, _ast.Constant):
                            cat_val = stmt.value.value
                        if target.id == "description" and isinstance(stmt.value, _ast.Constant):
                            desc_val = stmt.value.value

                if name_val:
                    skill_classes.append((
                        node.name, 
                        name_val, 
                        icon_val or "🔧",
                        risk_val or "confirm",
                        cat_val or "skill",
                        desc_val or f"{name_val} skill"
                    ))

            for class_name, skill_name, icon, risk_level, category, description in skill_classes:
                # Build a one-line prompt by scanning get_prompt() return value
                # — just grab the first string constant, falling back to skill_name.
                prompt_line = f"{icon} **{skill_name}**: {description}"
                for node in _ast.walk(tree):
                    if (
                        isinstance(node, _ast.FunctionDef)
                        and node.name == "get_prompt"
                    ):
                        for child in _ast.walk(node):
                            if isinstance(child, _ast.Constant) and isinstance(child.value, str):
                                first_line = child.value.splitlines()[0].strip()
                                if first_line:
                                    prompt_line = first_line
                                    break
                        break

                stub = _LazySkill(
                    name        = skill_name,
                    icon        = icon,
                    prompt_line = prompt_line,
                    file_path   = file_path,
                    class_name  = class_name,
                    risk_level  = risk_level,
                    category    = category,
                    description = description,
                )
                registry.register(stub)

        except Exception:
            # AST scan failed — fall back to eager load so the skill still works
            try:
                spec = importlib.util.spec_from_file_location(filename[:-3], file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[filename[:-3]] = module
                    spec.loader.exec_module(module)  # type: ignore[union-attr]
                    for _, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, BaseSkill)
                            and obj is not BaseSkill
                            and obj not in (GitSkill, CalculatorSkill)
                        ):
                            try:
                                registry.register(obj())
                            except Exception:
                                pass
            except Exception as e:
                print(f"⚠️  Failed to load skill from {filename}: {e}")

    return registry
