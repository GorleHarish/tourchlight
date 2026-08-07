"""
Unit tests for Torchlight Session Modes (Chat vs Goal) and .gitignore auto-patching.
"""

from pathlib import Path
import json
import pytest

from core.memory.models import ExecutionMode, SessionState
from core.memory.persistence import ensure_project_initialized
from core.execution.autonomous_harness import AutonomousHarness, HarnessConfig
from core.memory.manager import TieredMemory, MemoryConfig


def test_session_state_execution_mode_default():
    """Verify default session state execution mode is UNIFIED."""
    state = SessionState()
    assert state.execution_mode == ExecutionMode.UNIFIED
    assert state.execution_mode.value == "unified"


def test_ensure_project_initialized_patches_gitignore(tmp_path):
    """Verify ensure_project_initialized automatically appends .torchlight/ to .gitignore."""
    project_dir = tmp_path / "test_proj"
    project_dir.mkdir()

    # Pre-populate gitignore without .torchlight
    gitignore = project_dir / ".gitignore"
    gitignore.write_text("*.pyc\n__pycache__/\n")

    ensure_project_initialized(project_dir)

    content = gitignore.read_text()
    assert ".torchlight/" in content
    assert "*.pyc" in content


def test_chat_mode_suppresses_task_files(tmp_path):
    """Verify Chat Mode creates .context-memory.json but does not create goal_spec.json."""
    project_dir = tmp_path / "chat_proj"
    project_dir.mkdir()

    # Chat mode initialization
    ensure_project_initialized(project_dir)

    assert (project_dir / ".context-memory.json").exists()
    assert not (project_dir / ".torchlight" / "goal_spec.json").exists()
    assert not (project_dir / ".torchlight" / "tasks.md").exists()


def test_goal_mode_initializes_task_files(tmp_path):
    """Verify Goal Mode explicitly initializes goal_spec.json and tasks.md in .torchlight/."""
    project_dir = tmp_path / "goal_proj"
    project_dir.mkdir()

    memory = TieredMemory(config=MemoryConfig())
    harness = AutonomousHarness(project_root=project_dir, memory=memory)
    spec = harness.ensure_goal_spec_initialized(title="Feature Auth")

    assert spec is not None
    assert (project_dir / ".torchlight" / "goal_spec.json").exists()
    assert (project_dir / ".torchlight" / "tasks.md").exists()

    data = json.loads((project_dir / ".torchlight" / "goal_spec.json").read_text())
    assert data["title"] == "Feature Auth"
    assert isinstance(data["tasks"], list)

    tasks_md = (project_dir / ".torchlight" / "tasks.md").read_text()
    assert "Feature Auth" in tasks_md


def test_execution_mode_normalization_and_sync():
    """Verify RLMEngineOptimized normalizes string and Enum execution mode values."""
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized

    engine = RLMEngineOptimized()
    engine.execution_mode = ExecutionMode.GOAL
    assert engine.execution_mode == "goal"

    engine.execution_mode = "chat"
    assert engine.execution_mode == "chat"

