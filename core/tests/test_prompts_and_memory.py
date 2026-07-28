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
