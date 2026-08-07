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
