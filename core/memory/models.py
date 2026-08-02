"""
Memory models for Torchlight.

Shared data structures for message, session state, and memory objects.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL_RESULT = "tool_result"


class ExecutionMode(str, Enum):
    UNIFIED = "unified"
    CHAT = "chat"
    GOAL = "goal"



class ContentType(Enum):
    CODE = "code"
    ERROR = "error"
    FILE_PATH = "file_path"
    COMMAND = "command"
    EXPLANATION = "explanation"
    DECISION = "decision"
    GENERAL = "general"


@dataclass
class ContentChunk:
    content: str
    content_type: ContentType = ContentType.GENERAL
    importance: float = 0.5
    source_file: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None


@dataclass
class Message:
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    token_count: int = 0
    content_chunks: list[ContentChunk] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class MemoryNeedle:
    kind: str
    value: str
    source: str = ""
    weight: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MemoryObject:
    kind: str
    summary: str
    source: str = ""
    file_paths: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    text: str = ""
    score: float = 1.0
    embedding: list[float] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WorkingSetSnapshot:
    active_file: str = ""
    recent_files: list[str] = field(default_factory=list)
    pending_writes: list[str] = field(default_factory=list)


@dataclass
class SessionState:
    # Core intent
    intent: str = ""
    current_task: str = ""
    next_steps: list[str] = field(default_factory=list)

    # File tracking
    files_modified: list[str] = field(default_factory=list)
    files_read: list[str] = field(default_factory=list)

    # Decision & architecture log
    decisions: list[str] = field(default_factory=list)
    arch_decisions: list[str] = field(default_factory=list)

    # Dev-session specific
    tech_stack: list[str] = field(default_factory=list)
    failing_tests: list[str] = field(default_factory=list)
    errors_seen: list[str] = field(default_factory=list)
    dependencies_added: list[str] = field(default_factory=list)
    tried_and_failed: list[str] = field(default_factory=list)
    active_file: str = ""
    current_blocker: str = ""

    # Long-term memory
    semantic_context: str = ""
    needle_ledger: list[MemoryNeedle] = field(default_factory=list)
    memory_objects: list[MemoryObject] = field(default_factory=list)

    # Execution Mode (UNIFIED, CHAT, GOAL)
    execution_mode: ExecutionMode = ExecutionMode.UNIFIED

    # Working set
    working_set: WorkingSetSnapshot = field(default_factory=WorkingSetSnapshot)


@dataclass
class ContextSnapshot:
    """Snapshot of current memory state for display."""
    token_count: int = 0
    message_count: int = 0
    compression_ratio: float = 0.0
    recent_messages: int = 0
    compressed_messages: int = 0
    active_file: str = ""
    current_phase: str = "chat"
    execution_mode: str = "unified"
    tech_stack: list[str] = field(default_factory=list)
    errors_seen: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)

