import pytest
from core.memory.models import (
    Message,
    MessageRole,
    ContentType,
    ContentChunk,
    SessionState,
    ContextSnapshot,
    MemoryNeedle,
    MemoryObject,
    WorkingSetSnapshot,
)


def test_message_defaults():
    msg = Message(role=MessageRole.USER, content="hello")
    assert msg.role == MessageRole.USER
    assert msg.content == "hello"
    assert msg.token_count == 0


def test_session_state_defaults():
    s = SessionState()
    assert s.intent == ""
    assert s.active_file == ""
    assert s.files_modified == []
    assert s.errors_seen == []


def test_session_state_populated():
    s = SessionState(
        intent="code",
        current_task="fix bug",
        files_modified=["a.py"],
        errors_seen=["Error"],
    )
    assert s.intent == "code"
    assert s.files_modified == ["a.py"]


def test_context_snapshot():
    cs = ContextSnapshot(token_count=1000, message_count=5)
    assert cs.token_count == 1000
    assert cs.message_count == 5


def test_memory_needle():
    n = MemoryNeedle(kind="fact", value="test", source="test")
    assert n.kind == "fact"
    assert n.value == "test"


def test_memory_object():
    m = MemoryObject(kind="decision", summary="use X")
    assert m.kind == "decision"
    assert m.summary == "use X"


def test_working_set_snapshot():
    ws = WorkingSetSnapshot(active_file="main.py")
    assert ws.active_file == "main.py"
    assert ws.recent_files == []


def test_content_chunk():
    cc = ContentChunk(content="code here", content_type=ContentType.CODE)
    assert cc.content == "code here"
    assert cc.content_type == ContentType.CODE
    assert cc.importance == 0.5


def test_tiered_memory_pinned_files_without_system_message():
    from core.memory.manager import TieredMemory, MemoryConfig

    mem = TieredMemory(config=MemoryConfig())
    mem.pin_file("test.py", "def foo(): pass")
    mem.add_user_message("hello")
    ctx = mem.get_context_for_llm()
    assert len(ctx) == 2
    assert ctx[0]["role"] == "user"
    assert ctx[1]["role"] == "system"
    assert "test.py" in ctx[1]["content"]
