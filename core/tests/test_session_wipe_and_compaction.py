"""
Unit tests for session context wiping and manual context compaction option.
"""

import os
import sys
import pytest

from core.memory.manager import TieredMemory, MemoryConfig
from core.memory.models import MessageRole
from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
from rlm_optimized.tui_widgets.command_palette import slash_command_list


class DummyClient:
    pass


def test_engine_reset_session():
    engine = RLMEngineOptimized(client=DummyClient())
    config = MemoryConfig(max_tokens=1000, enable_auto_compaction=False)
    mem = TieredMemory(config=config)
    mem.add_system_message("System prompt")
    mem.add_user_message("User query 1")
    engine._memory = mem
    engine._messages = [{"role": "user", "content": "hello"}]
    engine._current_phase = "code"
    engine._total_llm_calls = 5
    engine._final_answer_rejections = 2
    engine._inline_code_counter = 3
    engine._prompt_hash_ring.append("some_hash")

    # Wipe session
    engine.reset_session()

    assert engine._memory is None
    assert engine._messages is None
    assert engine._current_phase is None
    assert engine._total_llm_calls == 0
    assert engine._final_answer_rejections == 0
    assert engine._inline_code_counter == 0
    assert len(engine._prompt_hash_ring) == 0


def test_engine_compact_context_tiered_memory():
    engine = RLMEngineOptimized(client=DummyClient())
    config = MemoryConfig(max_tokens=2000, recent_window=2, enable_auto_compaction=False)
    mem = TieredMemory(config=config)
    mem.add_system_message("System prompt")
    mem.add_user_message("Turn 1 " * 80)
    mem.add_assistant_message("Response 1 " * 80)
    mem.add_user_message("Turn 2 " * 80)
    mem.add_assistant_message("Response 2 " * 80)
    mem.add_user_message("Turn 3 " * 40)

    engine._memory = mem
    before, after, freed = engine.compact_context(force=True)

    assert before > 0
    assert after < before
    assert freed > 0
    assert any("[Context" in m.content for m in mem.messages)


def test_engine_compact_context_fallback_messages():
    engine = RLMEngineOptimized(client=DummyClient())
    engine._messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Turn 1 " * 50},
        {"role": "assistant", "content": "Response 1 " * 50},
        {"role": "user", "content": "Turn 2 " * 50},
    ]

    before, after, freed = engine.compact_context(force=True)
    assert before > 0
    assert after < before
    assert freed > 0
    assert len(engine._messages) == 3
    assert "[Context compacted" in engine._messages[1]["content"]


def test_slash_command_list_has_wipe_and_compact():
    cmds = slash_command_list()
    cmd_names = [c for c, _, _ in cmds]
    assert "/new" in cmd_names
    assert "/wipe" in cmd_names
    assert "/compact" in cmd_names
    assert "/compress" in cmd_names
    assert "/clear" in cmd_names
    assert "/reset" in cmd_names


@pytest.mark.anyio
async def test_tui_app_wipe_and_compact_buttons_exist():
    try:
        from rlm_optimized.tui_app import TorchlightApp
        from textual.widgets import Button
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed or environment skip: {e}")

    engine = RLMEngineOptimized(client=DummyClient())
    app = TorchlightApp(engine=engine, model_name="test-model", provider_name="test-provider")
    app._test_runner = True

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # Top HUD buttons
        wipe_btn = app.query_one("#wipe-context-btn", Button)
        compact_btn = app.query_one("#compact-btn", Button)
        assert wipe_btn is not None
        assert compact_btn is not None

        # Agent Tab buttons next to context bar
        agent_compact_btn = app.query_one("#agent-compact-btn", Button)
        agent_wipe_btn = app.query_one("#agent-wipe-btn", Button)
        assert agent_compact_btn is not None
        assert agent_wipe_btn is not None

        # Test clicking Wipe Context button resets memory
        config = MemoryConfig(max_tokens=1000, enable_auto_compaction=False)
        mem = TieredMemory(config=config)
        mem.add_system_message("System prompt")
        mem.add_user_message("Hello world")
        engine._memory = mem

        app.action_wipe_session()
        assert engine._memory is None or len(engine._memory.messages) == 0

        # Test compact action
        mem2 = TieredMemory(config=config)
        mem2.add_system_message("System prompt")
        mem2.add_user_message("Turn 1 " * 50)
        mem2.add_assistant_message("Ans 1 " * 50)
        mem2.add_user_message("Turn 2 " * 50)
        engine._memory = mem2

        app.action_compact_context()
        assert any("[Context" in m.content for m in mem2.messages)
