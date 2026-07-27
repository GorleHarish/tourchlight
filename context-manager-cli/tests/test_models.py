from datetime import datetime
from context_manager.memory.models import (
    Message, ContentChunk, MemoryNeedle, MemoryObject,
    SessionState, ContextSnapshot, WorkingSetSnapshot,
    MessageRole, ContentType,
)


# ── Message ──────────────────────────────────────────────────────────────────

def test_message_defaults():
    msg = Message(role=MessageRole.USER, content="hello")
    assert msg.timestamp is not None
    assert isinstance(msg.timestamp, datetime)
    assert msg.token_count == 0
    assert msg.content_chunks == []
    assert msg.metadata == {}


def test_message_custom_fields():
    chunk = ContentChunk(content="x", content_type=ContentType.CODE, importance=0.9)
    msg = Message(
        role=MessageRole.ASSISTANT,
        content="done",
        timestamp=datetime(2025, 1, 1),
        token_count=42,
        content_chunks=[chunk],
        metadata={"key": "val"},
    )
    assert msg.timestamp.year == 2025
    assert msg.token_count == 42
    assert len(msg.content_chunks) == 1
    assert msg.metadata["key"] == "val"


def test_message_role_enum():
    assert MessageRole.USER.value == "user"
    assert MessageRole.ASSISTANT.value == "assistant"
    assert MessageRole.SYSTEM.value == "system"
    assert MessageRole.TOOL_RESULT.value == "tool_result"
    assert len(MessageRole) == 4


# ── ContentChunk ─────────────────────────────────────────────────────────────

def test_content_chunk_defaults():
    chunk = ContentChunk(content="hello")
    assert chunk.content_type == ContentType.GENERAL
    assert chunk.importance == 0.5
    assert chunk.source_file is None
    assert chunk.line_start is None
    assert chunk.line_end is None


def test_content_chunk_custom():
    chunk = ContentChunk(
        content="x = 1",
        content_type=ContentType.CODE,
        importance=0.9,
        source_file="app.py",
        line_start=10,
        line_end=20,
    )
    assert chunk.content_type == ContentType.CODE
    assert chunk.importance == 0.9
    assert chunk.source_file == "app.py"
    assert chunk.line_start == 10
    assert chunk.line_end == 20


# ── MemoryNeedle ─────────────────────────────────────────────────────────────

def test_memory_needle_defaults():
    n = MemoryNeedle(kind="fact", value="some fact")
    assert n.weight == 1.0
    assert isinstance(n.timestamp, datetime)
    assert n.source == ""


def test_memory_needle_custom():
    n = MemoryNeedle(kind="error", value="KeyError", source="app.py", weight=1.1)
    assert n.kind == "error"
    assert n.value == "KeyError"
    assert n.source == "app.py"
    assert n.weight == 1.1


# ── MemoryObject ─────────────────────────────────────────────────────────────

def test_memory_object_defaults():
    obj = MemoryObject(kind="arch", summary="use FastAPI")
    assert obj.file_paths == []
    assert obj.symbols == []
    assert obj.commands == []
    assert obj.errors == []
    assert obj.text == ""
    assert obj.score == 1.0
    assert obj.embedding == []


def test_memory_object_full():
    obj = MemoryObject(
        kind="error",
        summary="NPE in handler",
        source="Handler.java",
        file_paths=["src/Handler.java"],
        symbols=["handleRequest"],
        commands=["mvn test"],
        errors=["NullPointerException"],
        text="full text",
        score=0.8,
        embedding=[0.1, 0.2],
    )
    assert obj.file_paths == ["src/Handler.java"]
    assert obj.symbols == ["handleRequest"]
    assert obj.commands == ["mvn test"]
    assert obj.errors == ["NullPointerException"]
    assert obj.score == 0.8
    assert len(obj.embedding) == 2


# ── SessionState ─────────────────────────────────────────────────────────────

def test_session_state_defaults():
    s = SessionState()
    assert s.intent == ""
    assert s.current_task == ""
    assert s.files_modified == []
    assert s.files_read == []
    assert s.decisions == []
    assert s.tech_stack == []
    assert s.failing_tests == []
    assert s.errors_seen == []
    assert s.active_file == ""
    assert s.current_blocker == ""


def test_session_state_populated():
    s = SessionState(
        intent="fix login bug",
        current_task="debug auth flow",
        files_modified=["auth.py"],
        errors_seen=["TokenExpiredError"],
        tech_stack=["Python", "FastAPI"],
    )
    assert s.intent == "fix login bug"
    assert s.current_task == "debug auth flow"
    assert "auth.py" in s.files_modified
    assert "TokenExpiredError" in s.errors_seen
    assert "Python" in s.tech_stack


# ── ContextSnapshot ──────────────────────────────────────────────────────────

def test_context_snapshot_fields():
    snap = ContextSnapshot(
        timestamp=datetime(2025, 6, 1),
        message_count=10,
        token_count=4096,
        compression_ratio=0.65,
        oldest_message_age=120.0,
    )
    assert snap.message_count == 10
    assert snap.token_count == 4096
    assert snap.compression_ratio == 0.65
    assert snap.oldest_message_age == 120.0


# ── WorkingSetSnapshot ───────────────────────────────────────────────────────

def test_working_set_snapshot_defaults():
    ws = WorkingSetSnapshot(
        query="fix bug",
        budget_tokens=4096,
        used_tokens=1000,
        recent_messages_count=5,
        included_messages_count=3,
        included_message_tokens=600,
        retrieval_tokens=200,
        state_summary_tokens=100,
    )
    assert ws.truncated is False
    assert ws.included_files == []
    assert ws.included_symbols == []
    assert ws.included_commands == []
    assert ws.included_errors == []
    assert ws.top_memory_summaries == []
    assert ws.messages == []
