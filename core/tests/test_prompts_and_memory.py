"""
Unit tests for phase-tailored system prompts, anti-symptom-patching rules, and L0 working memory scratchpad.
"""

from core.prompts.system import get_phase_system_prompt, SYSTEM_PROMPT
from core.memory.manager import TieredMemory, MemoryConfig


def test_phase_system_prompt_generation():
    plan_prompt = get_phase_system_prompt("plan")
    assert "[PHASE: PLANNING]" in plan_prompt
    assert "implementation_plan.md" in plan_prompt

    code_prompt = get_phase_system_prompt("code")
    assert "[PHASE: SURGICAL CODING]" in code_prompt
    assert "EDIT_FILE" in code_prompt

    troubleshoot_prompt = get_phase_system_prompt("troubleshoot")
    assert "[PHASE: TROUBLESHOOTING & DEBUGGING]" in troubleshoot_prompt
    assert "Inspect full, un-truncated error logs" in troubleshoot_prompt

    chat_prompt = get_phase_system_prompt("chat")
    assert "[PHASE: CHAT & EXPLORATION]" in chat_prompt


def test_anti_symptom_patching_directive():
    assert "ANTI-SYMPTOM-PATCHING" in SYSTEM_PROMPT
    assert "Never resolve errors by masking symptoms" in SYSTEM_PROMPT


def test_verification_gate_parity_in_system_prompt():
    assert "UNRESOLVED TEST FAILURES" in SYSTEM_PROMPT
    assert "UNVERIFIED CHANGES" in SYSTEM_PROMPT
    assert "re-verifies your pending changes" in SYSTEM_PROMPT
    assert "REVERT your broken edits" in SYSTEM_PROMPT


def test_goal_mode_pre_planning_context_check_directives():
    assert "In Goal Mode, FIRST check available files" in SYSTEM_PROMPT
    plan_prompt = get_phase_system_prompt("plan")
    assert "FIRST check available workspace files" in plan_prompt

    from rlm_optimized.prompts import build_system_prompt
    opt_prompt = build_system_prompt(".")
    assert "FIRST check available workspace files" in opt_prompt


def test_l0_scratchpad_formatting():
    config = MemoryConfig(max_tokens=4000)
    memory = TieredMemory(config=config)

    # Initially empty
    assert memory.format_l0_scratchpad() == ""

    # Populate state
    memory.state.current_task = "Implement auth middleware"
    memory.state.active_file = "src/auth.py"
    memory.state.files_modified.append("src/auth.py")
    memory.state.errors_seen.append("KeyError: token")
    memory.state.decisions.append("Use JWT for session validation")

    scratchpad = memory.format_l0_scratchpad()
    assert "[L0 WORKING MEMORY SCRATCHPAD]" in scratchpad
    assert "- Active Goal: Implement auth middleware" in scratchpad
    assert "- Active File: src/auth.py" in scratchpad
    assert "- Modified Files: src/auth.py" in scratchpad
    assert "- Active Errors: KeyError: token" in scratchpad
    assert "- Key Decisions: Use JWT for session validation" in scratchpad


def test_headroom_calculation():
    config = MemoryConfig(max_tokens=4000)
    memory = TieredMemory(config=config)

    headroom = memory.get_available_headroom()
    assert headroom > 0
    assert headroom <= 4000

    memory.add_user_message("Hello world " * 100)
    new_headroom = memory.get_available_headroom()
    assert new_headroom < headroom


def test_persistent_memory_loading_and_prompt_inclusion():
    import os
    import tempfile
    from pathlib import Path
    from core.memory.persistence import ProjectMemory
    from rlm_optimized.prompts import build_system_prompt

    with tempfile.TemporaryDirectory() as tmpdir:
        pm = ProjectMemory(Path(tmpdir))
        pm.update("Fact: Project uses SQLite for storage")
        pm.update_tech_stack(["Python 3.9", "FastAPI"])

        # 1. Verify system prompt includes persistent project memory
        prompt = build_system_prompt(tmpdir)
        assert "Persistent Project State (.context-memory.json)" in prompt
        assert "Fact: Project uses SQLite for storage" in prompt
        assert "Python 3.9" in prompt

        # 2. Verify TieredMemory loads persistent state into SessionState
        memory = TieredMemory(config=MemoryConfig(max_tokens=4000), project_memory=pm)
        assert "Fact: Project uses SQLite for storage" in memory.state.decisions
        assert "Python 3.9" in memory.state.tech_stack

        # 3. Verify persistence on state save
        memory.state.decisions.append("Decision: Adopt async workers")
        memory.persist_to_project_memory()

        # Reload in a new instance
        pm2 = ProjectMemory(Path(tmpdir))
        memory2 = TieredMemory(config=MemoryConfig(max_tokens=4000), project_memory=pm2)
        assert "Decision: Adopt async workers" in memory2.state.decisions


def test_tiered_memory_update_system_prompt():
    config = MemoryConfig(max_tokens=4000)
    memory = TieredMemory(config=config)
    memory.add_system_message("Initial System Prompt")
    memory.add_user_message("Hello")

    # Verify initial system prompt
    ctx1 = memory.get_context_for_llm()
    assert ctx1[0]["role"] == "system"
    assert ctx1[0]["content"] == "Initial System Prompt"

    # Update system prompt dynamically (e.g. on phase change)
    memory.update_system_prompt("Updated Phase System Prompt")

    # Verify system prompt was updated in memory and context
    ctx2 = memory.get_context_for_llm()
    assert ctx2[0]["role"] == "system"
    assert ctx2[0]["content"] == "Updated Phase System Prompt"


def test_sanitize_assistant_text():
    from core.prompts.system import sanitize_assistant_text

    raw = """[CRITICAL NEGATIVE CONSTRAINTS & DIRECTIVE LOCK]
1. NEVER run `cd` in RUN_COMMAND shell calls. Pass the target directory via the `cwd` argument instead.
2. NEVER mask symptoms or swallow exceptions
3. ALWAYS inspect full error logs
4. Replace placeholders
[ACTIVE PHASE TOOLS (GOAL): LIST_DIR, WRITE_FILE]
Writing code to file: index.html (14 lines, Basic HTML structure for Snake game)
Params: path: index.html
Result: Written 12 lines to /Users/harishgorle/Desktop/agent test/index.html
Updating index.html with Snake game structure."""

    cleaned = sanitize_assistant_text(raw)
    assert "[CRITICAL NEGATIVE CONSTRAINTS" not in cleaned
    assert "[ACTIVE PHASE TOOLS" not in cleaned
    assert "1. NEVER run `cd`" not in cleaned
    assert "Params:" not in cleaned
    assert "Result:" not in cleaned
    assert "Writing code to file:" not in cleaned
    assert "Updating index.html with Snake game structure." in cleaned


def test_non_verbose_directives_in_prompt():
    from core.prompts.system import get_phase_system_prompt, SYSTEM_PROMPT

    assert "NON-VERBOSE CODE DISCIPLINE" in SYSTEM_PROMPT
    assert 'Params: ...' in SYSTEM_PROMPT or 'Params:' in SYSTEM_PROMPT
    code_prompt = get_phase_system_prompt("code")
    assert "Params:" in code_prompt or "Result:" in code_prompt


def test_is_valid_file_path():
    from core.memory.manager import is_valid_file_path

    # Code attribute lookups / non-file strings must be rejected
    assert not is_valid_file_path("context.name")
    assert not is_valid_file_path("self.state")
    assert not is_valid_file_path("msg.role")
    assert not is_valid_file_path("item.id")
    assert not is_valid_file_path("response.data")
    assert not is_valid_file_path("e.message")
    assert not is_valid_file_path("http://example.com/test.py")
    assert not is_valid_file_path("invalid path with spaces.py")

    # Real file paths must be accepted
    assert is_valid_file_path("core/memory/manager.py")
    assert is_valid_file_path("rlm_optimized/prompts.py")
    assert is_valid_file_path("implementation_plan.md")
    assert is_valid_file_path("test_schemas.py")
    assert is_valid_file_path("tui_app.tcss")
    assert is_valid_file_path("Makefile")
    assert is_valid_file_path(".gitignore")


def test_modified_files_not_picking_context_name():
    from core.memory.manager import TieredMemory, MemoryConfig

    memory = TieredMemory(config=MemoryConfig(max_tokens=4000))

    # Assistant message referencing code attributes like context.name
    memory.add_assistant_message(
        "I analyzed context.name and self.state inside core/memory/manager.py."
    )

    # context.name and self.state must NOT be added to files_modified
    assert "context.name" not in memory.state.files_modified
    assert "self.state" not in memory.state.files_modified
    assert "msg.role" not in memory.state.files_modified

    # Explicit record_file_modified must work
    memory.record_file_modified("core/memory/manager.py")
    assert "core/memory/manager.py" in memory.state.files_modified

    # Explicit tool call JSON must record modified file
    memory.add_assistant_message(
        '<tool_call>{"name": "WRITE_FILE", "arguments": {"path": "src/new_feature.py", "content": "print(1)"}}</tool_call>'
    )
    assert "src/new_feature.py" in memory.state.files_modified


def test_calculate_in_memory_diff():
    from core.memory.manager import calculate_in_memory_diff

    old_code = "def foo():\n    return 1\n"
    new_code = "def foo():\n    print('hello')\n    return 2\n"

    added, deleted = calculate_in_memory_diff(old_code, new_code)
    assert added == 2
    assert deleted == 1

    # Identical text
    assert calculate_in_memory_diff(old_code, old_code) == (0, 0)

    # Empty old text (new file creation)
    assert calculate_in_memory_diff("", "line1\nline2\n") == (2, 0)


def test_extract_modified_symbols():
    from core.memory.manager import extract_modified_symbols

    old_code = "def existing_func():\n    pass\n"
    new_code = "def existing_func():\n    pass\n\ndef new_func():\n    return 42\n"

    syms = extract_modified_symbols(old_code, new_code)
    assert "new_func" in syms


def test_multi_edit_net_baseline_scratchpad():
    from core.memory.manager import TieredMemory, MemoryConfig

    memory = TieredMemory(config=MemoryConfig(max_tokens=4000))

    # Turn 1 edit
    code_v1 = "def login():\n    return True\n"
    memory.record_file_modified("src/auth.py", old_content="", new_content=code_v1)

    # Turn 2 edit (adding logout)
    code_v2 = "def login():\n    return True\n\ndef logout():\n    return False\n"
    memory.record_file_modified("src/auth.py", old_content=code_v1, new_content=code_v2)

    scratchpad = memory.format_l0_scratchpad()
    assert "- Modified Files:" in scratchpad
    assert "src/auth.py (+5, -0) [login, logout]" in scratchpad


def test_chat_system_prompt_isolation():
    """Verify chat system prompt does NOT command writing files, plans, or write gates."""
    chat_prompt = get_phase_system_prompt("chat")
    assert "[PHASE: CHAT & EXPLORATION]" in chat_prompt
    assert "<FINAL_ANSWER>your answer</FINAL_ANSWER>" in chat_prompt
    assert "Do NOT create `implementation_plan.md`" in chat_prompt
    assert "WRITE GATE" not in chat_prompt
    assert "NO PREMATURE FINAL ANSWERS" not in chat_prompt

    code_prompt = get_phase_system_prompt("code")
    assert "[PHASE: SURGICAL CODING]" in code_prompt
    assert "WRITE GATE" in code_prompt
    assert "NO PREMATURE FINAL ANSWERS" in code_prompt


def test_l0_scratchpad_suppresses_task_matrix_in_chat_mode(tmp_path):
    """Verify L0 scratchpad does not inject disk task matrices when in Chat Mode."""
    from core.memory.models import ExecutionMode
    project_dir = tmp_path / "scratchpad_proj"
    project_dir.mkdir()

    # Create leftover implementation plan on disk
    plan_file = project_dir / "implementation_plan.md"
    plan_file.write_text("# Plan\n- [ ] Step 1: Add authentication\n- [ ] Step 2: Add tests\n")

    memory = TieredMemory(config=MemoryConfig(max_tokens=4000))

    # In Unified / Goal mode, tasks from disk appear in scratchpad
    memory.state.execution_mode = ExecutionMode.UNIFIED
    sp_unified = memory.format_l0_scratchpad(project_root=str(project_dir))
    assert "step 1: add authentication" in sp_unified.lower()

    # In Chat mode, tasks from disk are suppressed
    memory.state.execution_mode = ExecutionMode.CHAT
    sp_chat = memory.format_l0_scratchpad(project_root=str(project_dir))
    assert "step 1: add authentication" not in sp_chat.lower()
    assert "active goal" not in sp_chat.lower()




