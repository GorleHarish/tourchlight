from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable
import re

from .models import Message, MessageRole, SessionState, ContextSnapshot, MemoryNeedle, MemoryObject, WorkingSetSnapshot
from .token_counter import TokenCounter, get_token_counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .persistence import ProjectMemory
    from ..api.lmstudio import LMStudioClient

from .embeddings import build_embedder
from .selective_compression import create_progressive_compressor, SelectiveCompressor


@dataclass
class MemoryConfig:
    max_tokens: int = 8000
    recent_window: int = 3
    recent_tokens: int = 2000
    compression_threshold: float = 0.7
    summary_trigger_tokens: int = 6000
    message_compact_threshold: int = 500
    tool_result_budget_fraction: float = 0.35
    summary_budget_fraction: float = 0.20
    metadata_overhead: int = 0
    execution_policy: str = "auto"
    embedding_backend: str = "hybrid"
    use_selective_compression: bool = True  # Enable progressive compression
    max_messages: int = 50  # Max messages to prevent memory bloat on low-RAM systems

    @classmethod
    def auto_tune(cls, max_tokens: int, metadata_overhead: int = 0) -> "MemoryConfig":
        """Create a MemoryConfig automatically tuned for the given context window size and available RAM."""
        # Detect available RAM for adaptive settings
        try:
            import psutil
            available_ram_gb = psutil.virtual_memory().available / (1024**3)
        except ImportError:
            available_ram_gb = 8  # Default conservative
        
        # RAM-based limits
        if available_ram_gb <= 10:
            max_messages = 50
            use_selective = True
        elif available_ram_gb <= 20:
            max_messages = 100
            use_selective = True
        else:
            max_messages = 200
            use_selective = True
        
        if max_tokens <= 2000:
            safety_margin = 256
        elif max_tokens <= 5000:
            safety_margin = 512
        elif max_tokens <= 10000:
            safety_margin = 768
        else:
            safety_margin = 1024
        history_budget = max(500, max_tokens - metadata_overhead - safety_margin)

        if max_tokens <= 2000:
            return cls(
                max_tokens=history_budget, recent_window=1,
                recent_tokens=int(history_budget * 0.4), compression_threshold=0.5,
                summary_trigger_tokens=int(history_budget * 0.4), message_compact_threshold=200,
                tool_result_budget_fraction=0.35, summary_budget_fraction=0.20,
                metadata_overhead=metadata_overhead, execution_policy="auto", embedding_backend="hybrid",
                max_messages=max_messages, use_selective_compression=use_selective,
            )
        elif max_tokens <= 4000:
            return cls(
                max_tokens=history_budget, recent_window=2,
                recent_tokens=int(history_budget * 0.35), compression_threshold=0.6,
                summary_trigger_tokens=int(history_budget * 0.5), message_compact_threshold=300,
                tool_result_budget_fraction=0.35, summary_budget_fraction=0.20,
                metadata_overhead=metadata_overhead, execution_policy="auto", embedding_backend="hybrid",
                max_messages=max_messages, use_selective_compression=use_selective,
            )
        elif max_tokens <= 8000:
            return cls(
                max_tokens=history_budget, recent_window=3,
                recent_tokens=int(history_budget * 0.25), compression_threshold=0.7,
                summary_trigger_tokens=int(history_budget * 0.75), message_compact_threshold=500,
                tool_result_budget_fraction=0.35, summary_budget_fraction=0.20,
                metadata_overhead=metadata_overhead, execution_policy="auto", embedding_backend="hybrid",
                max_messages=max_messages, use_selective_compression=use_selective,
            )
        else:
            return cls(
                max_tokens=history_budget, recent_window=5,
                recent_tokens=int(history_budget * 0.2), compression_threshold=0.7,
                summary_trigger_tokens=int(history_budget * 0.75), message_compact_threshold=800,
                tool_result_budget_fraction=0.35, summary_budget_fraction=0.20,
                metadata_overhead=metadata_overhead, execution_policy="auto", embedding_backend="hybrid",
                max_messages=max_messages, use_selective_compression=use_selective,
            )


# ── Tech stack detection patterns ────────────────────────────────────────────

_TECH_PATTERNS: list[tuple[str, str]] = [
    (r'\bpython\b', "Python"),
    (r'\bjavascript\b|\bnode\.?js\b|\bts\b|\btypescript\b', "JavaScript/TypeScript"),
    (r'\brust\b', "Rust"),
    (r'\bgolang\b|\bgo\b', "Go"),
    (r'\bjava\b', "Java"),
    (r'\bc\+\+\b|\bcpp\b', "C++"),
    (r'\bfastapi\b', "FastAPI"),
    (r'\bdjango\b', "Django"),
    (r'\bflask\b', "Flask"),
    (r'\breact\b', "React"),
    (r'\bnext\.?js\b', "Next.js"),
    (r'\bvue\b', "Vue"),
    (r'\bsveltekit\b|\bsvelte\b', "Svelte"),
    (r'\bexpress\b', "Express"),
    (r'\bsqlalchemy\b', "SQLAlchemy"),
    (r'\bprisma\b', "Prisma"),
    (r'\bpytest\b', "pytest"),
    (r'\bjest\b', "Jest"),
    (r'\bvitest\b', "Vitest"),
    (r'\bdocker\b', "Docker"),
    (r'\bkubernetes\b|\bk8s\b', "Kubernetes"),
    (r'\bpostgres\b|\bpostgresql\b', "PostgreSQL"),
    (r'\bmysql\b', "MySQL"),
    (r'\bsqlite\b', "SQLite"),
    (r'\bredis\b', "Redis"),
    (r'\bstreamlit\b', "Streamlit"),
]

_DEP_INSTALL_RE = re.compile(
    r'(?:pip install|pip3 install|npm install|yarn add|cargo add|go get)\s+([\w@/\-\.]+)',
    re.IGNORECASE,
)

_FILE_PATH_RE = re.compile(r'(?:^|[\s"])([\/~\.]?[\w\-\.]+(?:\/[\w\-\.]+)+\.\w+)', re.MULTILINE)
_SYMBOL_RE = re.compile(
    r'\b(?:def|async def|class|function|interface|type|fn|pub fn)\s+([A-Za-z_][A-Za-z0-9_]*)'
)
_COMMAND_RE = re.compile(
    r'(?:^|\n)\s*(?:\$|RUN_COMMAND\(|git |npm |pnpm |yarn |pytest|python -m pytest|cargo |uv |make )([^\n]*)',
    re.IGNORECASE,
)
_TEST_FAIL_RE = re.compile(
    r'(?:FAILED|ERROR|FAIL)\s+([\w/\.::\-]+)|'
    r'([\w/]+\.py)::\w+.*FAILED|'
    r'✗\s+([\w\s]+)|'
    r'× ([\w\s]+)',
    re.MULTILINE,
)
_ARCH_KEYWORDS = [
    "decided to use", "going with", "chose", "will use", "architecture",
    "instead of", "rather than", "switched to", "migrated to", "refactor",
    "pattern", "approach", "design", "strategy", "we'll use", "let's use",
]
_TRIED_FAIL_RE = re.compile(
    r"(?:tried|attempted|doesn't work|didn't work|failed to|not working|"
    r"gave up on|abandoned|reverted|that approach|this approach)[^\n.]{0,120}",
    re.IGNORECASE,
)
_BLOCKER_RE = re.compile(
    r"(?:stuck on|blocked by|can't figure out|issue with|problem with|"
    r"error:|exception:|failing because|not sure how to)[^\n.]{0,120}",
    re.IGNORECASE,
)
_SUMMARY_SECTION_KEYWORDS = {
    "ARCH DECISION":  "arch_decisions",
    "TRIED":          "tried_and_failed",
    "FAILED":         "tried_and_failed",
    "ERRORS SEEN":    "errors_seen",
    "RECENT ERROR":   "errors_seen",
    "KNOWN ERROR":    "errors_seen",
    "FAILING TEST":   "failing_tests",
    "DEPS ADDED":     "dependencies_added",
    "DEPENDENCIES":   "dependencies_added",
    "TECH STACK":     "tech_stack",
}


def _extract_file_paths(text: str) -> list[str]:
    raw = _FILE_PATH_RE.findall(text)
    emoji_paths = re.findall(r'📄\s*([\w/\.\-]+)', text)
    written_paths = re.findall(r'(?:Written|written|Saved|saved).*?to\s+([\w/\.\-]+)', text, re.IGNORECASE)
    all_paths = list(dict.fromkeys(raw + emoji_paths + written_paths))
    return [p for p in all_paths if '.' in p.split('/')[-1] and len(p) > 3 and not p.startswith('http')]


def _extract_tech_stack(text: str) -> list[str]:
    found = []
    lower = text.lower()
    for pattern, label in _TECH_PATTERNS:
        if re.search(pattern, lower) and label not in found:
            found.append(label)
    return found


def _extract_failing_tests(text: str) -> list[str]:
    matches = _TEST_FAIL_RE.findall(text)
    results = []
    for groups in matches:
        for g in groups:
            g = g.strip()
            if g and len(g) > 3:
                results.append(g)
    return list(dict.fromkeys(results))[:5]


def _extract_errors(text: str) -> list[str]:
    errors = []
    for pattern in [
        r'(?:Error|Exception|TypeError|ValueError|AttributeError|ImportError|'
        r'ModuleNotFoundError|KeyError|IndexError|RuntimeError)[:\s]+([^\n]{10,120})',
        r'Traceback \(most recent call last\):\s*\n(?:.*\n){0,5}(\w+Error[^\n]*)',
    ]:
        for m in re.finditer(pattern, text, re.MULTILINE):
            err = m.group(0)[:120].strip()
            if err not in errors:
                errors.append(err)
    return errors[:3]


def _extract_dep_installs(text: str) -> list[str]:
    return list(dict.fromkeys(_DEP_INSTALL_RE.findall(text)))[:10]


class _EvictingDeque(deque):
    """Deque that fires a callback when an item is evicted due to maxlen."""

    def __init__(self, *args, on_evict=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_evict = on_evict

    def append(self, item):
        if self._on_evict and self.maxlen is not None and len(self) == self.maxlen:
            self._on_evict(self[0])
        super().append(item)

    def appendleft(self, item):
        if self._on_evict and self.maxlen is not None and len(self) == self.maxlen:
            self._on_evict(self[-1])
        super().appendleft(item)

    def extend(self, iterable):
        for item in iterable:
            self.append(item)

    def extendleft(self, iterable):
        for item in iterable:
            self.appendleft(item)


class TieredMemory:
    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        tokenizer: Optional[TokenCounter] = None,
        project_memory: Optional["ProjectMemory"] = None,
        llm_client: Optional["LMStudioClient"] = None,
    ):
        self.config = config or MemoryConfig()
        self.tokenizer = tokenizer or get_token_counter()
        self.project_memory = project_memory
        self._total_tokens: int = 0
        self.state = SessionState()
        self._compactor = None
        self._embedder = build_embedder(
            backend=self.config.embedding_backend,
            execution_policy=self.config.execution_policy,
            llm_client=llm_client,
        )
        self._embedding_cache: dict[str, list[float]] = {}
        self._embedding_cache_max_size = 50

        self._llm_extractor = None
        if llm_client is not None:
            from .llm_extractor import LLMStateExtractor
            enabled = (config.max_tokens if config else 8000) > 5000
            self._llm_extractor = LLMStateExtractor(llm_client, enabled=enabled)

        # Selective compressor for progressive context reduction.
        # FIX 3: inject the real tokenizer so compact/summary/hint budgets are
        #         enforced in TOKENS, not characters.
        self._selective_compressor: Optional[SelectiveCompressor] = None
        if self.config.use_selective_compression:
            self._selective_compressor = create_progressive_compressor(
                self.config.max_tokens,
                tokenizer=self.tokenizer,   # ← FIX 3
            )

        self._token_breakdown = {"system": 0, "user": 0, "assistant": 0, "tool": 0}
        self.messages: _EvictingDeque = _EvictingDeque(
            maxlen=1000,
            on_evict=self._on_message_evicted,
        )

        # Active file pinning: keeps recently-read file content in context
        # even after compression. Max 2 files (FIFO eviction).
        self._pinned_files: deque[tuple[str, str]] = deque(maxlen=2)
        self._pinned_token_budget: int = 2000

        # FIX 4: Token-based compression cooldown.
        # After compression we record _total_tokens at that point.
        # Re-compression is only allowed once at least _compression_min_new_tokens
        # of NEW content has been added — regardless of how many messages that takes.
        # (The old counter fired after 3 messages, which could be 3 × 400 = 1200 new
        #  tokens on a 4K model — way too slow — or 3 × 10-token acks — way too fast.)
        self._compression_cooldown_tokens: int = 0      # tokens at last compression
        self._compression_min_new_tokens:  int = self._cooldown_token_threshold()

        # Auto-load historical findings from project memory
        if self.project_memory:
            pm = self.project_memory.load()
            self.state.arch_decisions = pm.get("arch_decisions", [])
            self.state.tried_and_failed = pm.get("tried_and_failed", [])
            self.state.tech_stack = pm.get("tech_stack", [])
            self.state.semantic_context = pm.get("facts", [])
            self.state.needle_ledger = [
                MemoryNeedle(
                    kind=item.get("kind", "general"),
                    value=item.get("value", ""),
                    source=item.get("source", ""),
                    weight=item.get("weight", 1.0),
                    timestamp=datetime.fromisoformat(item["timestamp"]) if item.get("timestamp") else datetime.now(),
                )
                for item in pm.get("needle_ledger", [])
                if item.get("value")
            ]
            self.state.memory_objects = [
                MemoryObject(
                    kind=item.get("kind", "summary"),
                    summary=item.get("summary", ""),
                    source=item.get("source", ""),
                    file_paths=item.get("file_paths", []),
                    symbols=item.get("symbols", []),
                    commands=item.get("commands", []),
                    errors=item.get("errors", []),
                    text=item.get("text", ""),
                    score=item.get("score", 1.0),
                    embedding=item.get("embedding", []),
                    timestamp=datetime.fromisoformat(item["timestamp"]) if item.get("timestamp") else datetime.now(),
                )
                for item in pm.get("memory_objects", [])
                if item.get("summary")
            ]
            # Prune non-existent files from loaded state
            self.sync_with_filesystem()

    def sync_with_filesystem(self) -> None:
        """
        Validate all tracked file paths against the actual filesystem.
        Prunes non-existent files from SessionState and long-term memory.
        """
        if not self.config or not self.project_memory or not self.project_memory.project_path:
            return

        base_path = self.project_memory.project_path

        def _exists(path_str: str) -> bool:
            try:
                # Handle relative or absolute paths within workspace
                p = Path(path_str)
                if not p.is_absolute():
                    p = base_path / p
                return p.exists()
            except Exception:
                return False

        # 1. Prune simple lists
        self.state.files_read = [f for f in self.state.files_read if _exists(f)]
        self.state.files_modified = [f for f in self.state.files_modified if _exists(f)]
        if self.state.active_file and not _exists(self.state.active_file):
            self.state.active_file = ""

        # 2. Prune NeedleLedger
        self.state.needle_ledger = [
            n for n in self.state.needle_ledger
            if n.kind != "file" or _exists(n.value)
        ]

        # 3. Prune MemoryObjects (filter the file_paths internal list)
        for obj in self.state.memory_objects:
            if obj.file_paths:
                obj.file_paths = [f for f in obj.file_paths if _exists(f)]
                # If the summary was purely file names and all are gone, it might be stale,
                # but we keep the object for symbols/text context.


    # ── FIX 4 helper ─────────────────────────────────────────────────────────

    def _cooldown_token_threshold(self) -> int:
        """Minimum NEW tokens that must arrive before re-compression is allowed.

        Scaled to context window so the cooldown is proportionate:
        ≤ 4K → 400 tokens  (one large tool result)
        ≤ 8K → 700 tokens
        > 8K → 1000 tokens
        """
        w = self.config.max_tokens
        if w <= 4000: return 400
        if w <= 8000: return 700
        return 1000

    # ── helpers ───────────────────────────────────────────────────────────────

    def configure_embedding_runtime(self, llm_client: Optional["LMStudioClient"] = None) -> None:
        self._embedder = build_embedder(
            backend=self.config.embedding_backend,
            execution_policy=self.config.execution_policy,
            llm_client=llm_client,
        )

    def _get_role_bucket(self, role) -> str:
        """Get the token breakdown bucket for a role."""
        rval = role.value if isinstance(role, MessageRole) else str(role)
        if rval == "system": return "system"
        if rval == "user": return "user"
        if rval == "assistant": return "assistant"
        return "tool"  # tool_result or tool

    def _update_token_breakdown_add(self, tokens: int, role) -> None:
        """Add tokens to the token breakdown."""
        bucket = self._get_role_bucket(role)
        self._token_breakdown[bucket] += tokens

    def _update_token_breakdown_remove(self, tokens: int, role) -> None:
        """Remove tokens from the token breakdown."""
        bucket = self._get_role_bucket(role)
        self._token_breakdown[bucket] = max(0, self._token_breakdown[bucket] - tokens)

    def _reset_token_breakdown(self) -> None:
        """Reset token breakdown to zero."""
        self._token_breakdown = {"system": 0, "user": 0, "assistant": 0, "tool": 0}

    def _on_message_evicted(self, msg: Message) -> None:
        self._total_tokens = max(0, self._total_tokens - msg.token_count)
        self._update_token_breakdown_remove(msg.token_count, msg.role)

    def _get_compactor(self):
        if self._compactor is None:
            from ..compression.compactor import VerbatimCompactor, CompressionConfig
            self._compactor = VerbatimCompactor(CompressionConfig(
                aggressive_mode=(self.config.max_tokens <= 4000)
            ))
        return self._compactor

    def _compact_content(self, content: str, max_tokens: int = 0) -> str:
        token_count = self.tokenizer.count(content)
        threshold = max_tokens if max_tokens > 0 else self.config.message_compact_threshold
        if token_count <= threshold:
            return content
        compacted = self._get_compactor().compress(content)
        if max_tokens > 0:
            compacted = self.tokenizer.truncate(compacted, max_tokens)
        return compacted

    def add_message(self, role: MessageRole, content: str) -> Message:
        if role != MessageRole.SYSTEM:
            content = self._compact_content(content)
        msg = Message(
            role=role,
            content=content,
            token_count=self.tokenizer.count(content),
        )
        self.messages.append(msg)
        self._total_tokens += msg.token_count
        self._update_token_breakdown_add(msg.token_count, role)
        self._update_state_from_message(msg)
        
        # Prune old messages if we exceed max_messages (prevents memory bloat)
        max_msgs = getattr(self.config, 'max_messages', 0)
        if max_msgs > 0 and len(self.messages) > max_msgs:
            self._prune_old_messages()
        
        return msg
    
    def _prune_old_messages(self):
        """Remove oldest non-system messages to stay under max_messages limit."""
        max_msgs = getattr(self.config, 'max_messages', 0)
        if max_msgs <= 0:
            return
        
        # Keep system messages, prune oldest from the beginning
        system_msgs = [m for m in self.messages if m.role == MessageRole.SYSTEM]
        other_msgs = [m for m in self.messages if m.role != MessageRole.SYSTEM]
        
        if len(other_msgs) > max_msgs - len(system_msgs):
            other_msgs = other_msgs[-(max_msgs - len(system_msgs)):]
        
        self.messages = system_msgs + other_msgs
        self._total_tokens = sum(m.token_count for m in self.messages)
        self._reset_token_breakdown()
        for m in self.messages:
            self._update_token_breakdown_add(m.token_count, m.role)

    def add_user_message(self, content: str) -> Message:
        return self.add_message(MessageRole.USER, content)

    def add_assistant_message(self, content: str) -> Message:
        return self.add_message(MessageRole.ASSISTANT, content)

    def add_tool_result(self, content: str, tool_name: str = "") -> Message:
        w = self.config.max_tokens
        if w <= 2000:   _hard_cap = 250
        elif w <= 4000: _hard_cap = 400
        elif w <= 8000: _hard_cap = 700
        else:           _hard_cap = 1200
        max_tool_tokens = min(
            int(self.config.max_tokens * self.config.tool_result_budget_fraction),
            _hard_cap,
        )
        content = self._get_compactor().compress_with_budget(content, max_tool_tokens, self.tokenizer)
        msg = self.add_message(MessageRole.TOOL_RESULT, content)
        msg.metadata["tool_name"] = tool_name
        self._update_state_from_message(msg)
        return msg

    def pin_file(self, path: str, content: str) -> None:
        """Pin a recently-read file so it survives compression.

        If the file is already pinned, update its content. Otherwise add it
        to the FIFO queue (oldest evicted when full).
        """
        for i, (p, _) in enumerate(self._pinned_files):
            if p == path:
                self._pinned_files[i] = (path, content)
                return
        self._pinned_files.append((path, content))

    def unpin_file(self, path: str) -> None:
        """Remove a file from pinned memory if deleted or stale."""
        from collections import deque
        self._pinned_files = deque(
            [(p, c) for p, c in self._pinned_files if p != path],
            maxlen=self._pinned_files.maxlen if hasattr(self._pinned_files, 'maxlen') else 2
        )

    def refresh_pin(self, path: str, project_root: str) -> None:
        """Re-read an edited file from disk and update its pin in memory."""
        try:
            from core.tools.implementations import tool_read_file_impl
            res = tool_read_file_impl({"path": path}, project_root)
            if res and not res.startswith("Error") and not res.startswith("File not found"):
                self.pin_file(path, res)
            else:
                self.unpin_file(path)
        except Exception:
            self.unpin_file(path)

    def get_pinned_files(self) -> list[tuple[str, str]]:
        """Return list of (path, content) for pinned files."""
        return list(self._pinned_files)

    def clear_pins(self) -> None:
        """Remove all pinned files."""
        self._pinned_files.clear()

    def get_context_for_llm(self, query: str = "") -> list[dict]:
        return self.build_working_set(query).messages

    def build_working_set(self, query: str = "", budget_tokens: Optional[int] = None) -> WorkingSetSnapshot:
        if not self.messages:
            return WorkingSetSnapshot(
                query=query or "",
                budget_tokens=budget_tokens or self.config.max_tokens,
                used_tokens=0,
                recent_messages_count=0,
                included_messages_count=0,
                included_message_tokens=0,
                retrieval_tokens=0,
                state_summary_tokens=0,
                messages=[],
            )

        context: list[dict] = []
        total = 0
        budget = budget_tokens or self.config.max_tokens
        truncated = False
        included_count = 0
        included_files: list[str] = []
        included_symbols: list[str] = []
        included_commands: list[str] = []
        included_errors: list[str] = []
        top_memory_summaries: list[str] = []
        retrieval_tokens = 0
        state_summary_tokens = 0

        # ── FIX 1: Wire selective compressor into the history assembly path ──
        # Old behaviour: reverse scan until budget hit → older msgs silently dropped.
        # New behaviour:
        #   1. Always include recent_window messages verbatim.
        #   2. Pass REMAINING budget to SelectiveCompressor for older messages so
        #      they are compressed (FULL → COMPACT → SUMMARY → HINT) rather than
        #      just dropped.  This makes the whole investment in SelectiveCompressor
        #      actually count.
        all_msgs   = list(self.messages)
        n_recent   = min(len(all_msgs), self.config.recent_window)
        recent_msgs = all_msgs[-n_recent:]
        older_msgs  = all_msgs[:-n_recent] if len(all_msgs) > n_recent else []

        # Recent turns — verbatim, newest last (preserve chronological order)
        for msg in recent_msgs:
            context.append(self._message_to_dict(msg))
            total += msg.token_count
            included_count += 1

        # ── HYBRID RETRIEVAL: Rank older messages by relevance ──
        # Instead of just taking the most recent older messages, we rank the pool
        # of older messages by relevance to the query so the compressor sees the
        # best bits first.
        if older_msgs and (query or self.state.current_task):
            q = query or self.state.current_task or self.state.intent
            terms = self._normalize_terms(q)
            scored_older = []
            for msg in older_msgs:
                score = 0.0
                msg_lower = msg.content.lower()
                for term in terms:
                    if term in msg_lower: score += 1.0
                # Boost messages with artifacts (likely more important)
                score += 0.1 * len(_FILE_PATH_RE.findall(msg.content))
                score += 0.1 * len(_SYMBOL_RE.findall(msg.content))
                scored_older.append((score, msg))
            
            # Sort by score (desc) then original index (preserve chron order within same score)
            # Actually for compression we might want to keep chron order but filter.
            # Here we just re-order the older_msgs list for the compressor.
            scored_older.sort(key=lambda x: x[0], reverse=True)
            older_msgs = [x[1] for x in scored_older]

        # Older turns — selectively compressed into remaining budget
        if older_msgs and self._selective_compressor is not None:
            remaining = max(0, budget - total)
            if remaining > 50:
                compressed_history_list = self.build_selective_context(
                    messages=older_msgs, budget_tokens=remaining
                )
                if compressed_history_list:
                    # Prepend as a system block so it sits before recent turns
                    history_msg = compressed_history_list[0]
                    history_msg["content"] = f"[COMPRESSED HISTORY]\n{history_msg['content']}"
                    
                    history_tokens = self.tokenizer.count(history_msg["content"])
                    context.insert(0, history_msg)
                    total += history_tokens
                    # Mark truncated only if the compressor had to skip turns
                    truncated = truncated or "[... " in history_msg["content"]
        elif older_msgs:
            # Fallback: simple reverse scan (no compressor available)
            for msg in reversed(older_msgs):
                if total + msg.token_count > budget:
                    truncated = True
                    break
                context.insert(0, self._message_to_dict(msg))
                total += msg.token_count
                included_count += 1

        retrieval_details = self._build_retrieval_memory_details(query or self.state.current_task or self.state.intent)
        retrieval_message = retrieval_details["message"]
        if retrieval_message:
            context.insert(0, retrieval_message)
            retrieval_tokens = retrieval_details["token_count"]
            top_memory_summaries = retrieval_details["memory_summaries"]
            included_files = retrieval_details["files"]
            included_symbols = retrieval_details["symbols"]
            included_commands = retrieval_details["commands"]
            included_errors = retrieval_details["errors"]

        state_summary = self._build_state_summary()
        state_summary_tokens = self.tokenizer.count(state_summary["content"])
        if state_summary["content"].strip():
            context.insert(0, state_summary)
        else:
            state_summary_tokens = 0

        # Inject pinned files after state summary so the model always has
        # exact file content available for EDIT_FILE, even after compression.
        if self._pinned_files:
            pinned_lines = ["[Pinned file contents — use for EDIT_FILE old_text:]"]
            pinned_tokens = 0
            for path, content in self._pinned_files:
                entry = f"\n--- {path} ---\n{content}\n--- end {path} ---"
                entry_tokens = self.tokenizer.count(entry)
                if pinned_tokens + entry_tokens > self._pinned_token_budget:
                    break
                pinned_lines.append(entry)
                pinned_tokens += entry_tokens
            if len(pinned_lines) > 1:
                pinned_msg = {"role": "system", "content": "\n".join(pinned_lines)}
                # Insert after state summary (index 0) but before retrieval
                context.insert(1, pinned_msg)

        return WorkingSetSnapshot(
            query=query or "",
            budget_tokens=budget,
            used_tokens=total + retrieval_tokens + state_summary_tokens,
            recent_messages_count=n_recent,
            included_messages_count=included_count,
            included_message_tokens=total,
            retrieval_tokens=retrieval_tokens,
            state_summary_tokens=state_summary_tokens,
            included_files=included_files,
            included_symbols=included_symbols,
            included_commands=included_commands,
            included_errors=included_errors,
            top_memory_summaries=top_memory_summaries,
            messages=context,
            truncated=truncated,
        )

    def build_selective_context(self, messages: Optional[list[Message]] = None, budget_tokens: Optional[int] = None) -> list[dict]:
        """
        Build context using selective progressive compression.

        Kept as a standalone method for callers that need a pure compressed
        string without the retrieval/state-summary layers.
        """
        msgs = messages if messages is not None else list(self.messages)
        if not msgs or not self._selective_compressor:
            return []

        budget = budget_tokens or self.config.max_tokens
        raw_messages = [
            {
                "role": (
                    msg.role.value
                    if isinstance(msg.role, MessageRole)
                    else str(msg.role)
                ),
                "content": msg.content,
            }
            for msg in msgs
        ]
        compressed_text = self._selective_compressor.build_compressed_context(
            raw_messages, max_tokens=budget
        )
        if not compressed_text.strip():
            return []
        return [{"role": "system", "content": compressed_text}]

    def should_compress(self) -> bool:
        # FIX 4: Token-based cooldown.
        # Only allow re-compression once enough NEW tokens have accumulated
        # since the last compression event.
        new_since = self._total_tokens - self._compression_cooldown_tokens
        if new_since < self._compression_min_new_tokens:
            # Emergency override: compress anyway if severely over the hard ceiling (>=85%)
            return self._total_tokens > self.config.max_tokens * 0.85
        effective_max = self.config.max_tokens - self.config.metadata_overhead
        if self.config.max_tokens <= 5000:
            return self._total_tokens > effective_max * 0.60
        return self._total_tokens > self.config.max_tokens * self.config.compression_threshold

    def needs_summary(self) -> bool:
        # FIX 4: same token-based gate
        new_since = self._total_tokens - self._compression_cooldown_tokens
        if new_since < self._compression_min_new_tokens:
            return False
        return self._total_tokens > self.config.summary_trigger_tokens

    def get_token_breakdown(self) -> dict[str, int]:
        return dict(self._token_breakdown)

    def get_snapshot(self) -> ContextSnapshot:
        return ContextSnapshot(
            timestamp=datetime.now(),
            message_count=len(self.messages),
            token_count=self._total_tokens,
            compression_ratio=self._total_tokens / self.config.max_tokens,
            oldest_message_age=(
                (datetime.now() - self.messages[0].timestamp).total_seconds()
                if self.messages else 0
            ),
        )

    def _message_to_dict(self, msg: Message) -> dict:
        role = msg.role.value if isinstance(msg.role, MessageRole) else str(msg.role)
        content = msg.content
        if role == "tool_result" or role == MessageRole.TOOL_RESULT:
            role = "user"
            tname = msg.metadata.get("tool_name") or "TOOL"
            content = f"[{tname}]\n{content}"
        return {"role": role, "content": content}

    def _build_state_summary(self) -> dict:
        """Build a compact dev-session state summary injected at context head."""
        s = self.state
        parts = []
        if s.intent:                parts.append(f"PROJECT GOAL: {s.intent}")
        if s.active_file:           parts.append(f"ACTIVE FILE: {s.active_file}")
        if s.current_blocker:       parts.append(f"CURRENT BLOCKER: {s.current_blocker}")
        if s.tech_stack:            parts.append(f"TECH STACK: {', '.join(s.tech_stack)}")
        if s.arch_decisions:
            parts.append("ARCHITECTURE DECISIONS:")
            for d in s.arch_decisions[-4:]: parts.append(f"  - {d}")
        if s.decisions:
            parts.append("OTHER DECISIONS:")
            for d in s.decisions[-3:]:      parts.append(f"  - {d}")
        if s.failing_tests:         parts.append(f"FAILING TESTS: {', '.join(s.failing_tests[:3])}")
        if s.errors_seen:
            parts.append("RECENT ERRORS:")
            for e in s.errors_seen[-2:]:    parts.append(f"  - {e}")
        if s.tried_and_failed:
            parts.append("ALREADY TRIED (do not re-suggest):")
            for t in s.tried_and_failed[-4:]: parts.append(f"  - {t}")
        modified = list(dict.fromkeys(s.files_modified))[-8:]
        if modified:                parts.append(f"FILES MODIFIED: {', '.join(modified)}")
        if s.dependencies_added:    parts.append(f"DEPS ADDED: {', '.join(s.dependencies_added[-5:])}")
        if s.next_steps:            parts.append(f"NEXT STEP: {s.next_steps[0]}")
        if s.semantic_context:
            parts.append("LONG-TERM RULES:")
            for sc in s.semantic_context: parts.append(f"  - {sc}")
        if s.needle_ledger:
            parts.append("NEEDLE LEDGER:")
            for needle in s.needle_ledger[-8:]:
                parts.append(f"  - [{needle.kind}] {needle.value}")
        return {"role": "system", "content": "\n".join(parts)}

    def build_critical_context(self) -> str:
        s = self.state
        parts = []
        if s.failing_tests:
            parts.append("CRITICAL - FAILING TESTS:")
            for t in s.failing_tests[:3]: parts.append(f"  - {t}")
            parts.append("These tests MUST pass after your changes.")
        if s.errors_seen:
            parts.append("ACTIVE ERRORS:")
            for e in s.errors_seen[-3:]: parts.append(f"  - {e}")
        if s.tried_and_failed:
            parts.append("DO NOT RE-SUGGEST:")
            for t in s.tried_and_failed[-4:]: parts.append(f"  - {t}")
        return "\n".join(parts) if parts else ""

    def get_intent_for_retrieval(self) -> str:
        parts = []
        if self.state.intent:          parts.append(self.state.intent)
        if self.state.active_file:     parts.append(f"current: {self.state.active_file}")
        if self.state.current_blocker: parts.append(f"blocked: {self.state.current_blocker}")
        return " | ".join(parts) if parts else ""

    def predict_next_tools(self) -> list[str]:
        predictions: list[str] = []
        seen = set()
        s = self.state
        if s.failing_tests:           predictions.extend(["RUN_COMMAND", "READ_FILE"])
        elif s.errors_seen:           predictions.extend(["GREP", "READ_FILE"])
        elif s.current_blocker:       predictions.extend(["GREP", "READ_FILE"])
        if not s.files_read:          predictions.append("READ_FILE")
        elif s.active_file:
            predictions.append("READ_FILE")
            predictions.append("WRITE_FILE")
        if s.current_task:
            task_lower = s.current_task.lower()
            if any(kw in task_lower for kw in ["add", "create", "implement", "new"]):
                if "WRITE_FILE" not in predictions: predictions.append("WRITE_FILE")
            elif any(kw in task_lower for kw in ["fix", "debug", "error", "bug"]):
                if "RUN_COMMAND" not in predictions: predictions.append("RUN_COMMAND")
        result = []
        for tool in predictions:
            if tool not in seen:
                seen.add(tool)
                result.append(tool)
        return result[:3]

    def get_active_file_hint(self) -> str:
        if not self.state.active_file: return ""
        parts = [self.state.active_file]
        if self.state.current_blocker: parts.append(f"error: {self.state.current_blocker[:50]}")
        if self.state.intent:          parts.append(self.state.intent[:50])
        return " ".join(parts)

    def _update_state_from_message(self, msg: Message) -> None:
        content = msg.content
        role = msg.role if isinstance(msg.role, MessageRole) else MessageRole(msg.role)

        if role == MessageRole.USER:
            if not self.state.intent:
                self.state.intent = content[:200]
            self.state.current_task = content[:500]
            for tech in _extract_tech_stack(content):
                if tech not in self.state.tech_stack:
                    self.state.tech_stack.append(tech)
            blocker = _BLOCKER_RE.search(content)
            if blocker:
                self.state.current_blocker = blocker.group(0)[:150]
            for m in _TRIED_FAIL_RE.finditer(content):
                entry = m.group(0).strip()
                if entry and entry not in self.state.tried_and_failed:
                    self.state.tried_and_failed.append(entry)

        elif role == MessageRole.ASSISTANT:
            lower = content.lower()
            if any(kw in lower for kw in _ARCH_KEYWORDS):
                for sentence in re.split(r'[.!?\n]', content):
                    if any(kw in sentence.lower() for kw in _ARCH_KEYWORDS):
                        entry = sentence.strip()[:200]
                        if entry and entry not in self.state.arch_decisions:
                            self.state.arch_decisions.append(entry)
                            break
            elif "decision" in lower[:100]:
                self.state.decisions.append(content[:200])
            for tech in _extract_tech_stack(content):
                if tech not in self.state.tech_stack:
                    self.state.tech_stack.append(tech)
            for path in _extract_file_paths(content):
                if path not in self.state.files_read:
                    self.state.files_read.append(path)
                    if len(self.state.files_read) > 20:
                        self.state.files_read = self.state.files_read[-20:]

        elif role == MessageRole.TOOL_RESULT:
            tool_name = msg.metadata.get("tool_name", "")
            if tool_name in ("read_file", "READ_FILE"):
                for path in _extract_file_paths(content):
                    if path not in self.state.files_read:
                        self.state.files_read.append(path)
                    self.state.active_file = path
            elif tool_name in ("write_file", "WRITE_FILE", "edit_file"):
                for path in _extract_file_paths(content):
                    if path not in self.state.files_modified:
                        self.state.files_modified.append(path)
                    self.state.active_file = path
            elif tool_name in ("bash", "RUN_COMMAND"):
                failing = _extract_failing_tests(content)
                for t in failing:
                    if t not in self.state.failing_tests:
                        self.state.failing_tests.append(t)
                if re.search(r'(?:passed|all tests pass|ok\b)', content, re.IGNORECASE):
                    self.state.failing_tests = []
                for err in _extract_errors(content):
                    if err not in self.state.errors_seen:
                        self.state.errors_seen.append(err)
                self.state.errors_seen = self.state.errors_seen[-5:]
                for dep in _extract_dep_installs(content):
                    if dep not in self.state.dependencies_added:
                        self.state.dependencies_added.append(dep)
                for tech in _extract_tech_stack(content):
                    if tech not in self.state.tech_stack:
                        self.state.tech_stack.append(tech)
            for path in _extract_file_paths(content):
                if path not in self.state.files_read and path not in self.state.files_modified:
                    self.state.files_read.append(path)

        self._capture_memory_artifacts(msg)

    def _capture_memory_artifacts(self, msg: Message) -> None:
        paths = _extract_file_paths(msg.content)
        symbols = list(dict.fromkeys(_SYMBOL_RE.findall(msg.content)))[:6]
        commands = self._extract_commands(msg.content)
        errors = _extract_errors(msg.content)
        tool_name = msg.metadata.get("tool_name", "")
        source = tool_name or (msg.role.value if isinstance(msg.role, MessageRole) else str(msg.role))

        for path in paths[:6]:   self._append_needle("file",    path,    source, 1.0)
        for sym  in symbols[:6]: self._append_needle("symbol",  sym,     source, 0.9)
        for cmd  in commands[:4]: self._append_needle("command", cmd,     source, 0.8)
        for err  in errors[:4]:  self._append_needle("error",   err,     source, 1.1)

        if not any([paths, symbols, commands, errors]):
            return

        summary_parts = []
        if paths:    summary_parts.append(f"files: {', '.join(paths[:3])}")
        if symbols:  summary_parts.append(f"symbols: {', '.join(symbols[:3])}")
        if commands: summary_parts.append(f"commands: {', '.join(commands[:2])}")
        if errors:   summary_parts.append(f"errors: {', '.join(errors[:2])}")
        summary = " | ".join(summary_parts)[:320]

        obj = MemoryObject(
            kind="tool" if msg.role == MessageRole.TOOL_RESULT else "dialogue",
            summary=summary, source=source,
            file_paths=paths[:6], symbols=symbols[:6], commands=commands[:4], errors=errors[:4],
            text=msg.content[:1200],
            score=1.0 + (0.2 * len(errors)) + (0.1 * len(paths)),
        )
        self.state.memory_objects.append(obj)
        self.state.memory_objects = self.state.memory_objects[-120:]

    def _append_needle(self, kind: str, value: str, source: str, weight: float) -> None:
        value = value.strip()
        if not value:
            return
        
        # Validation: Don't track non-existent files
        if kind == "file" and self.project_memory and self.project_memory.project_path:
            p = Path(value)
            if not p.is_absolute():
                p = self.project_memory.project_path / p
            if not p.exists():
                return

        if any(item.kind == kind and item.value == value for item in self.state.needle_ledger):
            return
        self.state.needle_ledger.append(MemoryNeedle(kind=kind, value=value[:240], source=source, weight=weight))
        self.state.needle_ledger = self.state.needle_ledger[-240:]

    @staticmethod
    def _extract_commands(text: str) -> list[str]:
        commands = []
        for match in _COMMAND_RE.finditer(text):
            line = match.group(0).strip().lstrip("$").strip()
            if line and line not in commands:
                commands.append(line[:160])
        return commands[:4]

    def _build_retrieval_memory(self, query: str) -> Optional[dict]:
        return self._build_retrieval_memory_details(query)["message"]

    def _build_retrieval_memory_details(self, query: str) -> dict:
        terms = self._normalize_terms(query)
        if not terms:
            return {
                "message": None, "token_count": 0,
                "memory_summaries": [], "files": [], "symbols": [], "commands": [], "errors": [],
            }

        lines: list[str] = []
        recent_objects = self._rank_memory_objects(query, top_k=4)
        memory_summaries = [item.summary for item in recent_objects]
        files: list[str] = []
        symbols: list[str] = []
        commands: list[str] = []
        errors: list[str] = []

        if recent_objects:
            lines.append("RETRIEVED WORKING SET:")
            for item in recent_objects:
                lines.append(f"- {item.summary}")
                for path in item.file_paths:
                    if path not in files: files.append(path)
                for symbol in item.symbols:
                    if symbol not in symbols: symbols.append(symbol)
                for command in item.commands:
                    if command not in commands: commands.append(command)
                for error in item.errors:
                    if error not in errors: errors.append(error)

        needles = self._rank_needles(query, top_k=8)
        if needles:
            lines.append("RETRIEVED NEEDLES:")
            for needle in needles:
                lines.append(f"- [{needle.kind}] {needle.value}")
                if needle.kind == "file"    and needle.value not in files:    files.append(needle.value)
                elif needle.kind == "symbol"  and needle.value not in symbols:  symbols.append(needle.value)
                elif needle.kind == "command" and needle.value not in commands: commands.append(needle.value)
                elif needle.kind == "error"   and needle.value not in errors:   errors.append(needle.value)

        if self.project_memory:
            query_embedding = self._safe_embed(query)
            project_hits = self.project_memory.hybrid_search(query, query_embedding=query_embedding, top_k=3)
            if project_hits:
                lines.append("PROJECT MEMORY HITS:")
                for item in project_hits:
                    lines.append(f"- {item.get('summary', item.get('text', ''))[:220]}")

        if not lines:
            return {
                "message": None, "token_count": 0,
                "memory_summaries": memory_summaries,
                "files": files[:8], "symbols": symbols[:8], "commands": commands[:6], "errors": errors[:6],
            }

        content = "\n".join(lines)
        max_tokens = max(180, int(self.config.max_tokens * 0.12))
        if self.tokenizer.count(content) > max_tokens:
            content = self.tokenizer.truncate(content, max_tokens)
        return {
            "message": {"role": "system", "content": content},
            "token_count": self.tokenizer.count(content),
            "memory_summaries": memory_summaries[:4],
            "files": files[:8], "symbols": symbols[:8], "commands": commands[:6], "errors": errors[:6],
        }

    def _rank_memory_objects(self, query: str, top_k: int = 4) -> list[MemoryObject]:
        terms = self._normalize_terms(query)
        if not terms: return []
        query_embedding = self._safe_embed(query)
        scored: list[tuple[float, MemoryObject]] = []
        for item in self.state.memory_objects:
            haystack = " ".join([item.summary, item.text,
                " ".join(item.file_paths), " ".join(item.symbols),
                " ".join(item.commands), " ".join(item.errors)])
            semantic = self._cosine(query_embedding, item.embedding) if query_embedding and item.embedding else 0.0
            score = self._lexical_score(terms, haystack) + semantic * 0.35 + item.score * 0.05
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def _rank_needles(self, query: str, top_k: int = 8) -> list[MemoryNeedle]:
        terms = self._normalize_terms(query)
        if not terms: return []
        scored: list[tuple[float, MemoryNeedle]] = []
        for needle in self.state.needle_ledger:
            score = self._lexical_score(terms, f"{needle.kind} {needle.value} {needle.source}") + needle.weight * 0.05
            if score > 0:
                scored.append((score, needle))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    @staticmethod
    def _normalize_terms(text: str) -> list[str]:
        return [term for term in re.findall(r"[A-Za-z0-9_./:-]+", (text or "").lower()) if len(term) > 2]

    @staticmethod
    def _lexical_score(terms: list[str], haystack: str) -> float:
        if not terms or not haystack: return 0.0
        lower = haystack.lower()
        score = 0.0
        for term in terms:
            if term in lower:
                score += 1.0
                if "/" in term or "." in term or "::" in term:
                    score += 0.8
        return score

    def _safe_embed(self, text: str) -> list[float]:
        if not text: return []
        cache_key = text[:100]
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        try:
            embedding = self._embedder.embed_sync(text)
            if len(self._embedding_cache) >= self._embedding_cache_max_size:
                oldest = next(iter(self._embedding_cache))
                del self._embedding_cache[oldest]
            self._embedding_cache[cache_key] = embedding
            return embedding
        except Exception:
            return []

    @staticmethod
    def _cosine(v1: list[float], v2: list[float]) -> float:
        if not v1 or not v2: return 0.0
        dot   = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        return dot / (norm1 * norm2) if norm1 and norm2 else 0.0

    # ── Compression ───────────────────────────────────────────────────────────

    def compress_recent(self, compress_fn: Callable[[list[Message]], str], force: bool = False) -> str:
        min_messages = 1 if force else self.config.recent_window
        if len(self.messages) <= min_messages:
            return ""

        window_size = 1 if force else self.config.recent_window
        recent = list(self.messages)[-window_size:] if window_size > 0 else []
        older  = list(self.messages)[:-window_size] if window_size > 0 else list(self.messages)

        summary = compress_fn(older)

        self._merge_summary_into_state(summary)
        self.state.memory_objects.append(MemoryObject(
            kind="summary", summary=summary[:320], source="compression",
            file_paths=list(dict.fromkeys(self.state.files_modified[-4:] + self.state.files_read[-4:])),
            symbols=[needle.value for needle in self.state.needle_ledger if needle.kind == "symbol"][-6:],
            commands=[needle.value for needle in self.state.needle_ledger if needle.kind == "command"][-4:],
            errors=self.state.errors_seen[-4:],
            text=summary[:1200], score=1.4,
            embedding=self._safe_embed(summary[:1200]),
        ))
        self.state.memory_objects = self.state.memory_objects[-120:]

        max_summary_tokens = int(self.config.max_tokens * self.config.summary_budget_fraction)
        if self.tokenizer.count(summary) > max_summary_tokens:
            summary = self._get_compactor().compress(summary)
            summary = self.tokenizer.truncate(summary, max_summary_tokens)

        self.messages = _EvictingDeque(recent, maxlen=1000, on_evict=self._on_message_evicted)
        self._total_tokens = sum(m.token_count for m in self.messages)

        summary_content = f"[Earlier conversation summarized]\n{summary}"
        summary_msg = Message(
            role=MessageRole.SYSTEM, content=summary_content,
            token_count=self.tokenizer.count(summary_content),
            metadata={"is_summary": True},
        )
        self._total_tokens += summary_msg.token_count
        self.messages.appendleft(summary_msg)

        # FIX 4: Record token level at compression time.
        self._compression_cooldown_tokens = self._total_tokens if not force else 0

        return summary

    async def compress_recent_async(self, compress_fn: Callable[[list[Message]], str], force: bool = False) -> str:
        import asyncio

        min_messages = 1 if force else self.config.recent_window
        if len(self.messages) <= min_messages:
            return ""

        window_size = 1 if force else self.config.recent_window
        recent = list(self.messages)[-window_size:] if window_size > 0 else []
        older  = list(self.messages)[:-window_size] if window_size > 0 else list(self.messages)

        if self._llm_extractor is not None:
            summary, _ = await asyncio.gather(
                asyncio.to_thread(compress_fn, older),
                self._llm_extractor.extract_and_merge(older, self.state),
                return_exceptions=True,
            )
            if isinstance(summary, BaseException):
                summary = compress_fn(older)
        else:
            summary = compress_fn(older)

        self._merge_summary_into_state(summary)
        self.state.memory_objects.append(MemoryObject(
            kind="summary", summary=summary[:320], source="compression",
            file_paths=list(dict.fromkeys(self.state.files_modified[-4:] + self.state.files_read[-4:])),
            symbols=[needle.value for needle in self.state.needle_ledger if needle.kind == "symbol"][-6:],
            commands=[needle.value for needle in self.state.needle_ledger if needle.kind == "command"][-4:],
            errors=self.state.errors_seen[-4:],
            text=summary[:1200], score=1.4,
            embedding=self._safe_embed(summary[:1200]),
        ))
        self.state.memory_objects = self.state.memory_objects[-120:]

        max_summary_tokens = int(self.config.max_tokens * self.config.summary_budget_fraction)
        if self.tokenizer.count(summary) > max_summary_tokens:
            summary = self._get_compactor().compress(summary)
            summary = self.tokenizer.truncate(summary, max_summary_tokens)

        self.messages = _EvictingDeque(recent, maxlen=1000, on_evict=self._on_message_evicted)
        self._total_tokens = sum(m.token_count for m in self.messages)

        summary_content = f"[Earlier conversation summarized]\n{summary}"
        summary_msg = Message(
            role=MessageRole.SYSTEM, content=summary_content,
            token_count=self.tokenizer.count(summary_content),
            metadata={"is_summary": True},
        )
        self._total_tokens += summary_msg.token_count
        self.messages.appendleft(summary_msg)

        # FIX 4: same token-based cooldown as synchronous path
        self._compression_cooldown_tokens = self._total_tokens if not force else 0

        return summary

    def _merge_summary_into_state(self, summary: str) -> None:
        if not summary:
            return
        try:
            s     = self.state
            lines = summary.splitlines()

            SECTION_MAP = {
                "ARCH DECISION":  ("arch_decisions",    200),
                "TRIED":          ("tried_and_failed",  150),
                "FAILED TO":      ("tried_and_failed",  150),
                "NOT WORKING":    ("tried_and_failed",  150),
                "ERRORS SEEN":    ("errors_seen",       120),
                "RECENT ERROR":   ("errors_seen",       120),
                "KNOWN ERROR":    ("errors_seen",       120),
                "FAILING TEST":   ("failing_tests",     100),
                "DEPS ADDED":     ("dependencies_added", 80),
                "DEPENDENCIES":   ("dependencies_added", 80),
                "TECH STACK":     ("tech_stack",         50),
            }

            def _classify(header: str) -> Optional[tuple]:
                upper = header.upper()
                for keyword, mapping in SECTION_MAP.items():
                    if keyword in upper:
                        return mapping
                return None

            def _add_to_field(field: str, value: str, max_len: int) -> None:
                value = value.strip(" -•·*").strip()[:max_len]
                if not value: return
                target: list = getattr(s, field, [])
                if value not in target:
                    target.append(value)

            current_field: Optional[str] = None
            current_max:   int           = 200

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                is_header = (
                    (stripped.upper() == stripped or re.match(r'^\d+\.', stripped))
                    and len(stripped) < 80
                    and not stripped.startswith("-")
                )
                if is_header:
                    mapping = _classify(stripped)
                    if mapping:
                        current_field, current_max = mapping
                        sep = max(stripped.find(":"), stripped.find("—"), stripped.find("-", 3))
                        if sep != -1:
                            inline = stripped[sep + 1:].strip()
                            if inline:
                                for item in inline.split(","):
                                    _add_to_field(current_field, item, current_max)
                    continue
                if current_field and stripped.startswith(("-", "•", "·", "*")):
                    _add_to_field(current_field, stripped, current_max)
                    continue
                if current_field and not is_header:
                    if not (stripped.upper() == stripped and len(stripped) < 40):
                        _add_to_field(current_field, stripped, current_max)

            for line in lines:
                stripped = line.strip()
                upper    = stripped.upper()
                if upper.startswith("GOAL:") and not s.intent:
                    s.intent = stripped[5:].strip()[:200]
                elif upper.startswith("ACTIVE FILE:"):
                    val = stripped[12:].strip()
                    if val: s.active_file = val[:200]
                elif upper.startswith("CURRENT BLOCKER:"):
                    val = stripped[16:].strip()
                    if val: s.current_blocker = val[:200]

            s.arch_decisions     = s.arch_decisions[-20:]
            s.tried_and_failed   = s.tried_and_failed[-20:]
            s.errors_seen        = s.errors_seen[-10:]
            s.failing_tests      = s.failing_tests[-10:]
            s.dependencies_added = s.dependencies_added[-20:]

        except Exception:
            pass

    def clear(self) -> None:
        self.messages = _EvictingDeque(maxlen=1000, on_evict=self._on_message_evicted)
        self._pinned_files.clear()
        self.state = SessionState()
        self._total_tokens = 0
        self._reset_token_breakdown()

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    @property
    def message_count(self) -> int:
        return len(self.messages)
