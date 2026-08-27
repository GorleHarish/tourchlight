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

    engine.execution_mode = "unified"
    assert engine.execution_mode == "unified"
    assert engine.memory.state.execution_mode == ExecutionMode.UNIFIED


def test_chat_mode_phase_detection_resilience():
    """Verify _detect_phase returns 'chat' in Chat Mode despite trigger keywords."""
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized

    engine = RLMEngineOptimized()
    engine.execution_mode = "chat"

    assert engine._detect_phase("Why is this error happening?") == "chat"
    assert engine._detect_phase("How to write a binary search algorithm in python?") == "chat"
    assert engine._detect_phase("What is the architecture plan for this project?") == "chat"
    assert engine._detect_phase("Explain src/main.py and fix the bug") == "chat"
    assert engine._detect_phase("Resume task and proceed") == "chat"


def test_chat_mode_verification_gate_bypassed(tmp_path):
    """Verify solve_async in Chat Mode delivers <FINAL_ANSWER> directly without verification gate rejection."""
    import asyncio
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized

    # Create workspace with pending tasks in implementation_plan.md
    plan_file = tmp_path / "implementation_plan.md"
    plan_file.write_text("# Plan\n- [ ] Task 1: Pending work\n")

    class MockClient:
        def __init__(self):
            self.model = "mock-model"
            self.temperature = 0.7
            self.stream_call_count = 0

        def chat_with_history(self, messages, *args, **kwargs):
            self.stream_call_count += 1
            return "<FINAL_ANSWER>Here is a direct answer explaining the logic.</FINAL_ANSWER>"

        async def stream_chat_async(self, messages, *args, **kwargs):
            self.stream_call_count += 1
            yield "<FINAL_ANSWER>Here is a direct answer explaining the logic.</FINAL_ANSWER>"

    engine = RLMEngineOptimized(project_root=str(tmp_path), client=MockClient())
    engine.execution_mode = "chat"

    res = asyncio.run(engine.solve_async("Explain how this function works and how to fix it"))
    assert res.answer == "Here is a direct answer explaining the logic."
    assert len(res.steps) == 1
    assert res.steps[0].action == "final_answer"


def test_goal_mode_system_prompt_and_phase_detection():
    """Verify Goal Mode phase detection and system prompt construction."""
    from core.prompts.system import get_phase_system_prompt
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized

    prompt = get_phase_system_prompt("goal")
    assert "AUTONOMOUS GOAL EXECUTION" in prompt
    assert "implementation_plan.md" in prompt
    assert "LIST_DIR" in prompt

    engine = RLMEngineOptimized()
    engine.execution_mode = "goal"
    assert engine._detect_phase("Create a snake game") == "goal"
    assert engine._detect_phase("Fix the login bug") == "goal"


def test_goal_mode_schemas_for_phase():
    """Verify get_schemas_for_phase returns the expected tool suite for goal phase."""
    from core.tools.schemas import get_schemas_for_phase

    schemas = get_schemas_for_phase("goal")
    assert "LIST_DIR" in schemas
    assert "SEARCH_AST" in schemas
    assert "WRITE_FILE" in schemas
    assert "EDIT_FILE" in schemas
    assert "RUN_COMMAND" in schemas


def test_goal_mode_verification_gate_rejects_premature_final_answer(tmp_path):
    """Verify solve_async in Goal Mode rejects premature FINAL_ANSWER when no plan or tools executed."""
    import asyncio
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized

    class MockPrematureClient:
        def __init__(self):
            self.model = "qwen2.5-coder-7b-instruct"
            self.temperature = 0.1
            self.call_count = 0

        def chat_with_history(self, messages, *args, **kwargs):
            self.call_count += 1
            if self.call_count == 1:
                return "<FINAL_ANSWER>I have completed the task successfully!</FINAL_ANSWER>"
            elif self.call_count == 2:
                return '<tool_call>{"name": "WRITE_FILE", "arguments": {"path": "implementation_plan.md", "content": "# Plan\\n- [x] Task 1\\n"}}</tool_call>'
            else:
                return "<FINAL_ANSWER>Plan created and all tasks completed.</FINAL_ANSWER>"

        async def stream_chat_async(self, messages, *args, **kwargs):
            self.call_count += 1
            if self.call_count == 1:
                # Premature final answer without executing tools or creating plan
                yield "<FINAL_ANSWER>I have completed the task successfully!</FINAL_ANSWER>"
            elif self.call_count == 2:
                # Second turn: properly calls write_file
                yield '<tool_call>{"name": "WRITE_FILE", "arguments": {"path": "implementation_plan.md", "content": "# Plan\\n- [x] Task 1\\n"}}</tool_call>'
            else:
                yield "<FINAL_ANSWER>Plan created and all tasks completed.</FINAL_ANSWER>"

    engine = RLMEngineOptimized(project_root=str(tmp_path), client=MockPrematureClient())
    engine.execution_mode = "goal"

    res = asyncio.run(engine.solve_async("Build the authentication feature"))
    assert len(res.steps) >= 2
    # First step should have been rejected by verification gate
    assert res.steps[0].action == "rejected_final_answer"
    assert "MISSING PLAN" in res.steps[0].result
    # Second step should be the tool call
    assert res.steps[1].action == "tool"
    assert res.steps[1].tool_name == "WRITE_FILE"


def test_verification_gate_single_path_tool_template_and_anti_echo(tmp_path):
    """Verify that when tasks exist on disk, verification gate injects single-path tool template and sanitizes echoing text."""
    import asyncio
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized

    plan_file = tmp_path / "implementation_plan.md"
    plan_file.write_text("# Plan\n- [ ] 1.1 Create HTML skeleton with canvas container\n")

    recorded_history = []

    class MockSLMClient:
        def __init__(self):
            self.model = "qwen2.5-coder-3b-instruct"
            self.call_count = 0

        def chat_with_history(self, messages, *args, **kwargs):
            self.call_count += 1
            recorded_history.append(list(messages))
            if self.call_count == 1:
                return "Given the repeated rejection, it seems that implementation_plan.md is still marked as a pending task.```json"
            else:
                return '<tool_call>{"name": "WRITE_FILE", "arguments": {"path": "index.html", "task_id": "1.1", "description": "Create HTML skeleton", "content": "<!DOCTYPE html><html></html>"}}</tool_call>'

        async def stream_chat_async(self, messages, *args, **kwargs):
            self.call_count += 1
            recorded_history.append(list(messages))
            if self.call_count == 1:
                # Simulated small model conversational answer with trailing unclosed json block
                yield "Given the repeated rejection, it seems that implementation_plan.md is still marked as a pending task.```json"
            else:
                # Receives single-path tool template and outputs valid tool call
                yield '<tool_call>{"name": "WRITE_FILE", "arguments": {"path": "index.html", "task_id": "1.1", "description": "Create HTML skeleton", "content": "<!DOCTYPE html><html></html>"}}</tool_call>'

    engine = RLMEngineOptimized(project_root=str(tmp_path), client=MockSLMClient())
    engine.execution_mode = "unified"

    res = asyncio.run(engine.solve_async("create html skeleton"))
    assert len(res.steps) >= 2
    # Step 0 triggers thinking loop or rejection with single-path template
    # In turn 2 messages, verify the single-path tool template was injected
    assert any('<tool_call>{"name": "WRITE_FILE"' in m["content"] for m in recorded_history[1])
    assert any('"path": "index.html"' in m["content"] for m in recorded_history[1])

    # In turn 2 messages, verify the conversational text was sanitized to prevent echoing
    turn_2_messages = recorded_history[1]
    assistant_msg = next((m for m in turn_2_messages if m["role"] == "assistant"), None)
    assert assistant_msg is not None
    assert "Given the repeated rejection" not in assistant_msg["content"]
    assert "without <tool_call>]" in assistant_msg["content"]


@pytest.mark.anyio
async def test_auto_mode_change_disabled_in_plan_code_chat(tmp_path):
    """Verify that auto mode change and phase transitions are completely disabled in Plan, Code, and Chat modes."""
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized

    engine = RLMEngineOptimized(project_root=str(tmp_path))

    # 1. Plan Mode
    engine.execution_mode = "plan"
    assert engine.execution_mode == "plan"
    assert engine._current_phase == "plan"
    assert engine._detect_phase("error: crash in main.py") == "plan"
    assert engine._detect_phase("write_file code for index.html") == "plan"
    assert engine._detect_phase("hello there") == "plan"
    engine._update_params("error: crash", "traceback")
    assert engine._current_phase == "plan"

    # 2. Code Mode
    engine.execution_mode = "code"
    assert engine.execution_mode == "code"
    assert engine._current_phase == "code"
    assert engine._detect_phase("brainstorm architecture plan") == "code"
    assert engine._detect_phase("error: fatal exception") == "code"
    assert engine._detect_phase("tell me a joke") == "code"
    engine._update_params("brainstorm plan", "")
    assert engine._current_phase == "code"

    # 3. Chat Mode
    engine.execution_mode = "chat"
    assert engine.execution_mode == "chat"
    assert engine._current_phase == "chat"
    assert engine._detect_phase("write_file server.py") == "chat"
    assert engine._detect_phase("error: segmentation fault") == "chat"
    assert engine._detect_phase("let's plan the migration") == "chat"
    engine._update_params("write_file server.py", "")
    assert engine._current_phase == "chat"

    # 4. Unified Mode (dynamic auto phase detection enabled)
    engine.execution_mode = "unified"
    assert engine.execution_mode == "unified"
    assert engine._detect_phase("let's plan the migration") == "plan"
    assert engine._detect_phase("error: crash in main.py") == "troubleshoot"
    assert engine._detect_phase("write_file index.html") == "code"
    assert engine._detect_phase("hello there") == "chat"






