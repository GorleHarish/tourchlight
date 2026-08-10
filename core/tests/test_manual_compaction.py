"""
Unit tests for manual context compaction trigger and 85%/91% threshold logic.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../context-manager-cli/src")))

from core.memory.manager import TieredMemory as CoreTieredMemory, MemoryConfig as CoreMemoryConfig
from context_manager.memory.manager import TieredMemory as CLITieredMemory, MemoryConfig as CLIMemoryConfig
from context_manager.memory.models import MessageRole
from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized


def test_core_should_compress_high_ratio_low_message_count():
    # Setup memory with small recent_window=3 (so recent_window + 2 = 5)
    config = CoreMemoryConfig(max_tokens=1000, recent_window=3, compression_threshold=0.7, enable_auto_compaction=False)
    mem = CoreTieredMemory(config=config)

    # Add system prompt + 1 huge message (2 messages total, < 5 messages)
    mem.add_system_message("System prompt")
    mem.add_user_message("word " * 900)  # ~900 tokens = 90% of max_tokens

    # Verify should_compress() triggers because ratio >= 0.85
    assert mem.total_tokens / config.max_tokens >= 0.85
    assert mem.should_compress() is True


def test_core_compress_recent_force():
    config = CoreMemoryConfig(max_tokens=1000, recent_window=3, enable_auto_compaction=False)
    mem = CoreTieredMemory(config=config)

    mem.add_system_message("System prompt")
    mem.add_user_message("Turn 1 " * 50)
    mem.add_assistant_message("Response 1 " * 50)
    mem.add_user_message("Turn 2 " * 50)

    assert len(mem.messages) == 4
    # Normally recent_window=3 + preserve_first=1 requires > 4 messages to compress.
    # Without force, compress_recent does nothing:
    mem.compress_recent(preserve_first=1, force=False)
    assert len(mem.messages) == 4

    # With force=True, force compaction compresses older turns down to 1 recent message
    mem.compress_recent(preserve_first=1, force=True)
    assert any("[Context" in m.content for m in mem.messages)


def test_cli_should_compress_emergency_threshold():
    config = CLIMemoryConfig(max_tokens=1000, compression_threshold=0.7, enable_auto_compaction=False)
    mem = CLITieredMemory(config=config)

    # Simulate active cooldown
    mem._compression_cooldown_tokens = 900
    mem._total_tokens = 910  # 91% capacity

    # Previously 91% was blocked because emergency threshold was 92%. Now >= 85% triggers emergency override.
    assert mem.should_compress() is True


def test_cli_compress_recent_force():
    config = CLIMemoryConfig(max_tokens=1000, recent_window=3, enable_auto_compaction=False)
    mem = CLITieredMemory(config=config)

    mem.add_message(MessageRole.SYSTEM, "System prompt")
    mem.add_user_message("Turn 1 " * 30)
    mem.add_assistant_message("Response 1 " * 30)

    assert len(mem.messages) == 3
    # Without force, message count <= recent_window (3) prevents compression
    result_normal = mem.compress_recent(lambda msgs: "Summary text", force=False)
    assert result_normal == ""

    # With force=True, forces compression
    result_forced = mem.compress_recent(lambda msgs: "Summary text", force=True)
    assert result_forced == "Summary text"
    assert len(mem.messages) == 2  # summary + 1 recent message


def test_engine_compact_context():
    class DummyClient:
        pass

    engine = RLMEngineOptimized(client=DummyClient())
    config = CoreMemoryConfig(max_tokens=1000, recent_window=3, enable_auto_compaction=False)
    mem = CoreTieredMemory(config=config)

    mem.add_system_message("System prompt")
    mem.add_user_message("Task description")
    mem.add_user_message("Turn 1 " * 100)
    mem.add_assistant_message("Response 1 " * 100)
    mem.add_user_message("Turn 2 " * 50)

    msg_count_before = len(mem.messages)
    before, after, freed = engine.compact_context(memory=mem, force=True)

    assert msg_count_before == 5
    assert any("[Context" in m.content for m in mem.messages)
    assert before > 0


def test_total_tokens_includes_l0_scratchpad():
    config = CoreMemoryConfig(max_tokens=2000, enable_auto_compaction=False)
    mem = CoreTieredMemory(config=config)
    mem.add_system_message("System prompt")
    mem.state.errors_seen.append("SyntaxError: invalid syntax in test.py line 42")
    
    raw_msg_tokens = mem._cached_msg_tokens
    total = mem.total_tokens
    # total_tokens must include dynamic L0 scratchpad tokens
    assert total > raw_msg_tokens


def test_should_compress_triggers_on_ratio_above_threshold_with_few_messages():
    config = CoreMemoryConfig(max_tokens=1000, compression_threshold=0.70, enable_auto_compaction=False)
    mem = CoreTieredMemory(config=config)
    mem.add_system_message("System prompt")
    mem.add_user_message("Big payload line\n" * 250)  # > 750 tokens
    
    assert mem.total_tokens / config.max_tokens >= 0.70
    # Must trigger compaction even with only 2 messages
    assert mem.should_compress() is True


def test_compress_recent_truncates_oversized_tool_output_when_older_empty():
    config = CoreMemoryConfig(max_tokens=1000, recent_window=3, enable_auto_compaction=False)
    mem = CoreTieredMemory(config=config)
    mem.add_system_message("System prompt")
    # Massive single tool result message
    huge_tool_output = "Line output " * 50 + "\n"
    mem.add_tool_result(huge_tool_output * 30, tool_name="LIST_DIR")
    
    tokens_before = mem.total_tokens
    res = mem.compress_recent(force=True)
    tokens_after = mem.total_tokens
    
    assert tokens_after < tokens_before
    assert "truncated" in mem.messages[1].content


def test_event_based_memory_listeners():
    from core.memory.models import MemoryEventType

    config = CoreMemoryConfig(max_tokens=1000)
    mem = CoreTieredMemory(config=config)
    events_received = []

    def on_event(evt):
        events_received.append(evt)

    mem.add_event_listener(on_event)
    mem.add_system_message("System prompt")
    mem.add_user_message("Hello world")

    assert len(events_received) == 2
    assert events_received[0].event_type == MemoryEventType.MESSAGE_ADDED
    assert events_received[1].event_type == MemoryEventType.MESSAGE_ADDED


def test_event_based_reactive_compaction():
    from core.memory.models import MemoryEventType

    config = CoreMemoryConfig(max_tokens=1000, compression_threshold=0.70)
    mem = CoreTieredMemory(config=config)
    compaction_events = []

    def listener(evt):
        if evt.event_type == MemoryEventType.COMPACTION_TRIGGERED:
            compaction_events.append(evt)

    mem.add_event_listener(listener)
    mem.add_system_message("System prompt")

    # Adding large tool result reactively triggers compaction immediately at add_tool_result call time
    mem.add_tool_result("Massive tool output line\n" * 200, tool_name="GREP")

    # Compaction event must have fired reactively
    assert len(compaction_events) >= 1
    assert compaction_events[0].token_ratio > 0.70


