import pytest
from core.memory.selective_compression import SelectiveCompressor, CompressionLevel, CompressionConfig


def test_compression_levels():
    assert CompressionLevel.FULL.value == "full"
    assert CompressionLevel.COMPACT.value == "compact"
    assert CompressionLevel.SUMMARY.value == "summary"
    assert CompressionLevel.HINT.value == "hint"


def test_selective_compressor_defaults():
    sc = SelectiveCompressor()
    assert sc.config.full_window == 3
    assert sc.config.compact_threshold == 7


def test_selective_compressor_custom_config():
    config = CompressionConfig(full_window=5, compact_threshold=10)
    sc = SelectiveCompressor(config=config)
    assert sc.config.full_window == 5
    assert sc.config.compact_threshold == 10


def test_tiered_memory_compress_recent_summarizer():
    from core.memory.manager import TieredMemory, MemoryConfig
    from core.memory.models import Message
    tm = TieredMemory(config=MemoryConfig(max_tokens=1000, recent_window=1))
    tm.add_user_message("msg 1")
    tm.add_assistant_message("msg 2")
    tm.add_user_message("msg 3")

    received_msgs = []
    def dummy_summarizer(msgs):
        received_msgs.extend(msgs)
        return "summarized"

    tm.compress_recent(summarizer_fn=dummy_summarizer)
    assert len(received_msgs) == 2
    assert all(isinstance(m, Message) for m in received_msgs)
    assert received_msgs[0].content == "msg 1"

