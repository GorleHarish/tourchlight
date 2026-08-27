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
    PLAN = "plan"
    CODE = "code"

    @property
    def is_fixed(self) -> bool:
        """Return True if auto phase detection and mode switching are disabled."""
        return self in (ExecutionMode.CHAT, ExecutionMode.PLAN, ExecutionMode.CODE)


FIXED_EXECUTION_MODES = frozenset({"plan", "code", "chat"})



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
class SessionState:
    # ── Core intent ───────────────────────────────────────────────────────────
    intent: str = ""
    current_task: str = ""
    next_steps: list[str] = field(default_factory=list)

    # ── File tracking ─────────────────────────────────────────────────────────
    files_modified: list[str] = field(default_factory=list)
    files_read: list[str] = field(default_factory=list)

    # ── Decision & architecture log ───────────────────────────────────────────
    decisions: list[str] = field(default_factory=list)
    # Architectural decisions are higher-value than general decisions and are
    # kept separately so they survive more compression cycles.
    arch_decisions: list[str] = field(default_factory=list)

    # ── Dev-session specific ──────────────────────────────────────────────────
    # Detected languages / frameworks / tools (e.g. ["Python", "FastAPI", "pytest"])
    tech_stack: list[str] = field(default_factory=list)
    # Currently failing tests — preserved verbatim across compressions
    failing_tests: list[str] = field(default_factory=list)
    # Recent errors/exceptions seen — helps model not re-hit the same wall
    errors_seen: list[str] = field(default_factory=list)
    # Packages/deps added this session (e.g. "pip install httpx")
    dependencies_added: list[str] = field(default_factory=list)
    # Approaches that were tried and failed — critical for avoiding context rot
    # where the model re-suggests something you already discarded.
    tried_and_failed: list[str] = field(default_factory=list)
    # The file currently being actively worked on
    active_file: str = ""
    # Short description of the current blocker / problem being solved
    current_blocker: str = ""

    # ── Long-term memory (from SaveMemory skill) ──────────────────────────────
    semantic_context: list[str] = field(default_factory=list)
    needle_ledger: list[MemoryNeedle] = field(default_factory=list)
    memory_objects: list[MemoryObject] = field(default_factory=list)

    # ── Execution Mode (UNIFIED, CHAT, GOAL, PLAN, CODE) ─────────────────────
    execution_mode: ExecutionMode = ExecutionMode.UNIFIED


@dataclass
class ContextSnapshot:
    timestamp: datetime
    message_count: int
    token_count: int
    compression_ratio: float
    oldest_message_age: float


@dataclass
class WorkingSetSnapshot:
    query: str
    budget_tokens: int
    used_tokens: int
    recent_messages_count: int
    included_messages_count: int
    included_message_tokens: int
    retrieval_tokens: int
    state_summary_tokens: int
    included_files: list[str] = field(default_factory=list)
    included_symbols: list[str] = field(default_factory=list)
    included_commands: list[str] = field(default_factory=list)
    included_errors: list[str] = field(default_factory=list)
    top_memory_summaries: list[str] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)
    truncated: bool = False
