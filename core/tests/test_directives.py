"""
Unit tests for CRITICAL_DIRECTIVES system prompt lock and DirectiveTracker.
"""

import pytest
from core.prompts.system import get_phase_system_prompt, CRITICAL_DIRECTIVES
from core.memory.directives import DirectiveTracker


def test_critical_directives_in_system_prompt():
    prompt = get_phase_system_prompt("code")
    assert "[CRITICAL NEGATIVE CONSTRAINTS & DIRECTIVE LOCK]" in prompt
    assert "NEVER run `cd` in RUN_COMMAND" in prompt
    assert "NEVER mask symptoms or swallow exceptions" in prompt


def test_directive_tracker():
    tracker = DirectiveTracker()

    class MockMemoryState:
        def __init__(self):
            self.tried_and_failed = []

    class MockMemory:
        def __init__(self):
            self.state = MockMemoryState()

    mem = MockMemory()

    hint = tracker.record_violation("cd_command", "cd src", mem)
    assert "DIRECTIVE VIOLATION" in hint
    assert "cd" in hint
    assert len(mem.state.tried_and_failed) == 1
    assert "DIRECTIVE VIOLATION" in mem.state.tried_and_failed[0]
