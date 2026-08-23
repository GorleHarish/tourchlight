"""
Tiered Memory Manager for Torchlight.

L0-L3 memory hierarchy with progressive compression.
"""

import difflib
import os
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Union

from .models import (
    Message,
    MessageRole,
    SessionState,
    ContextSnapshot,
    MemoryNeedle,
    MemoryObject,
    WorkingSetSnapshot,
    MemoryEvent,
    MemoryEventType,
)
from .token_counter import TokenCounter, get_token_counter
from .budget import ContextBudget
from .selective_compression import (
    SelectiveCompressor,
    CompressionConfig,
    CompressionLevel,
)
from .deduplication import DeduplicationEngine, DeduplicationStats
from rlm_optimized.config import ContextProfile, get_context_profile


# L0 scratchpad hygiene limits. These bound the dynamic working-memory block
# injected into system context every turn so it stays small for 7B-class models
# (~400 tokens worst case) regardless of how much state accumulates.
_SCRATCHPAD_MAX_CHARS = 1600
_SCRATCHPAD_ENTRY_LIMIT = 120
_SCRATCHPAD_HEADER = "[L0 WORKING MEMORY SCRATCHPAD]"


def _is_valid_decision(entry) -> bool:
    """Filter out empty, generic, or noisy session summary strings."""
    if not entry:
        return False
    val = str(entry).strip()
    if len(val) < 5:
        return False
    lower = val.lower()
    if lower.startswith("session on ") or "no summary to provide" in lower:
        return False
    if lower.startswith("- **") or lower.startswith("--") or lower == "- **":
        return False
    return True


def _scratchpad_clean(entry, limit: int = _SCRATCHPAD_ENTRY_LIMIT) -> str:
    """Flatten whitespace/newlines and truncate a scratchpad entry to a bounded length."""
    val = str(entry).strip()
    val = re.sub(r"^(?:[-*]\s*)+", "", val).strip()
    flat = " ".join(val.split())
    if len(flat) > limit:
        return flat[: limit - 3].rstrip() + "..."
    return flat


_NON_FILE_EXTENSIONS = {
    "name",
    "role",
    "state",
    "get",
    "set",
    "items",
    "keys",
    "values",
    "count",
    "data",
    "id",
    "type",
    "val",
    "arg",
    "args",
    "kwarg",
    "kwargs",
    "attr",
    "func",
    "self",
    "this",
    "parent",
    "child",
    "len",
    "split",
    "join",
    "strip",
    "lower",
    "upper",
    "append",
    "extend",
    "pop",
    "update",
    "clear",
    "group",
    "search",
    "match",
    "findall",
    "finditer",
    "sub",
    "replace",
    "start",
    "end",
    "stdout",
    "stderr",
    "stdin",
    "path",
    "result",
    "error",
    "status",
    "code",
    "message",
    "content",
    "text",
    "length",
    "format",
    "read",
    "write",
    "close",
    "open",
    "flush",
    "is_dir",
    "is_file",
    "exists",
    "copy",
    "move",
    "remove",
    "delete",
    "add",
    "sub",
    "mul",
    "div",
    "mod",
    "eq",
    "ne",
    "lt",
    "gt",
    "le",
    "ge",
    "target",
    "source",
    "output",
    "input",
    "params",
    "options",
    "config",
    "spec",
    "value",
    "key",
    "node",
    "element",
    "component",
    "class",
    "module",
    "object",
    "enabled",
    "active",
    "default",
    "factory",
    "args",
    "kwargs",
    "parent",
}

_VALID_FILE_EXTENSIONS = {
    "py",
    "js",
    "ts",
    "jsx",
    "tsx",
    "json",
    "md",
    "txt",
    "html",
    "css",
    "tcss",
    "rs",
    "go",
    "sh",
    "c",
    "cpp",
    "h",
    "hpp",
    "yml",
    "yaml",
    "toml",
    "xml",
    "ini",
    "cfg",
    "sql",
    "java",
    "rb",
    "php",
    "kt",
    "swift",
    "bat",
    "ps1",
    "log",
    "csv",
    "tsv",
    "diff",
    "patch",
    "lock",
    "rst",
    "env",
}

_VALID_EXACT_FILENAMES = {
    "makefile",
    "dockerfile",
    ".gitignore",
    ".env",
    "license",
    "docker-compose.yml",
}


def is_valid_file_path(path: str) -> bool:
    """Validate if a string is a genuine file path rather than code attribute access (e.g. context.name)."""
    if not path or not isinstance(path, str):
        return False
    path = path.strip().strip("'\"`()[],:;")
    if not path or len(path) < 3:
        return False
    if path.startswith(("http://", "https://", "ftp://")):
        return False
    if " " in path or "\n" in path or "\t" in path:
        return False

    base = path.split("/")[-1].split("\\")[-1]
    if not base:
        return False

    if base.lower() in _VALID_EXACT_FILENAMES:
        return True

    if "." not in base:
        return False

    parts = base.rsplit(".", 1)
    prefix = parts[0].lower()
    ext = parts[1].lower()

    if ext in _NON_FILE_EXTENSIONS:
        return False

    if prefix in {
        "self",
        "this",
        "msg",
        "context",
        "obj",
        "object",
        "item",
        "data",
        "res",
        "req",
        "response",
        "request",
        "node",
        "element",
        "e",
    }:
        return False

    return ext in _VALID_FILE_EXTENSIONS


def calculate_in_memory_diff(old_content: str, new_content: str) -> tuple[int, int]:
    """Calculate exact lines added and deleted between two string buffers in RAM."""
    if old_content == new_content:
        return 0, 0

    old_lines = (old_content or "").splitlines()
    new_lines = (new_content or "").splitlines()

    added = 0
    deleted = 0

    for line in difflib.unified_diff(old_lines, new_lines, lineterm=""):
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted += 1

    return added, deleted


def extract_modified_symbols(old_content: str, new_content: str) -> list[str]:
    """Extract function/class AST symbol names modified or added between old and new text."""
    def _find_symbols(text: str) -> dict[str, str]:
        if not text:
            return {}
        symbols = {}
        # Python def/class declarations
        for m in re.finditer(r"^(?:async\s+)?(?:def|class)\s+([a-zA-Z_]\w*)", text, re.MULTILINE):
            name = m.group(1)
            start = m.start()
            symbols[name] = text[start:start + 500]
        # JS/TS function/class/const function declarations
        for m in re.finditer(r"^(?:export\s+)?(?:function|class|const|let|var)\s+([a-zA-Z_]\w*)", text, re.MULTILINE):
            name = m.group(1)
            start = m.start()
            if name not in symbols:
                symbols[name] = text[start:start + 500]
        return symbols

    old_syms = _find_symbols(old_content or "")
    new_syms = _find_symbols(new_content or "")

    modified = []
    for name, snippet in new_syms.items():
        if name not in old_syms or old_syms[name] != snippet:
            modified.append(name)
    return modified[:5]


@dataclass
class MemoryConfig:
    max_tokens: int = 8000
    recent_window: int = 3
    recent_tokens: int = 2000
    pinned_token_budget: int = 600
    compression_threshold: float = 0.7
    summary_trigger_tokens: int = 6000
    message_compact_threshold: int = 500
    tool_result_budget_fraction: float = 0.35
    summary_budget_fraction: float = 0.20
    metadata_overhead: int = 0
    execution_policy: str = "auto"
    embedding_backend: str = "hybrid"
    use_selective_compression: bool = True
    enable_auto_compaction: bool = True
    max_messages: int = 50
    # Maximum entries to retain in SessionState lists to prevent unbounded growth
    max_session_state_entries: int = 50
    # Context profile for model-aware budget allocation
    context_profile: ContextProfile = ContextProfile.LARGE_12K

    @classmethod
    def auto_tune(cls, max_tokens: int, metadata_overhead: int = 0) -> "MemoryConfig":
        try:
            import psutil

            available_ram_gb = psutil.virtual_memory().available / (1024**3)
        except ImportError:
            available_ram_gb = 8

        if available_ram_gb <= 10:
            max_messages = 50
        elif available_ram_gb <= 20:
            max_messages = 100
        else:
            max_messages = 200

        if max_tokens <= 2000:
            safety_margin = 256
        elif max_tokens <= 5000:
            safety_margin = 512
        elif max_tokens <= 10000:
            safety_margin = 768
        else:
            safety_margin = 1024

        history_budget = max(500, max_tokens - metadata_overhead - safety_margin)

        # Get context profile for model-aware defaults
        profile = ContextProfile.from_context_size(max_tokens)
        
        if max_tokens <= 2000:
            return cls(
                max_tokens=history_budget,
                recent_window=1,
                recent_tokens=int(history_budget * 0.4),
                pinned_token_budget=200,
                compression_threshold=0.8,
                summary_trigger_tokens=int(history_budget * 0.4),
                message_compact_threshold=200,
                metadata_overhead=metadata_overhead,
                max_messages=max_messages,
                max_session_state_entries=30,
                context_profile=profile,
            )
        elif max_tokens <= 4000:
            return cls(
                max_tokens=history_budget,
                recent_window=2,
                recent_tokens=int(history_budget * 0.35),
                pinned_token_budget=300,
                compression_threshold=0.8,
                summary_trigger_tokens=int(history_budget * 0.5),
                message_compact_threshold=300,
                metadata_overhead=metadata_overhead,
                max_messages=max_messages,
                max_session_state_entries=40,
                context_profile=profile,
            )
        elif max_tokens <= 8000:
            return cls(
                max_tokens=history_budget,
                recent_window=3,
                recent_tokens=int(history_budget * 0.25),
                pinned_token_budget=600,
                compression_threshold=0.8,
                summary_trigger_tokens=int(history_budget * 0.75),
                message_compact_threshold=500,
                metadata_overhead=metadata_overhead,
                max_messages=max_messages,
                max_session_state_entries=50,
                context_profile=profile,
            )
        else:
            return cls(
                max_tokens=history_budget,
                recent_window=5,
                recent_tokens=int(history_budget * 0.2),
                pinned_token_budget=1000,
                compression_threshold=0.8,
                summary_trigger_tokens=int(history_budget * 0.75),
                message_compact_threshold=800,
                metadata_overhead=metadata_overhead,
                max_messages=max_messages,
                max_session_state_entries=80,
                context_profile=profile,
            )


class TieredMemory:
    """
    Tiered memory system with L0-L3 hierarchy:
    - L0: Active prompt (current context)
    - L1: Recent messages (full detail)
    - L2: Compressed summaries
    - L3: Persistent project memory
    """

    def __init__(
        self,
        config: MemoryConfig,
        tokenizer: Optional[TokenCounter] = None,
        project_memory=None,
        llm_client=None,
    ):
        self.config = config
        # Note: Context profile is applied in MemoryConfig.auto_tune(), not here.
        # This allows users to create custom MemoryConfig instances with specific values.
        
        self.tokenizer = tokenizer or get_token_counter()
        self.state = SessionState()
        self.messages: deque[Message] = deque(maxlen=config.max_messages)
        self._project_memory = project_memory
        if self._project_memory:
            self.load_project_memory()
        self._llm_extractor = None
        self._compressor = SelectiveCompressor(
            config=CompressionConfig(),
            tokenizer=self.tokenizer,
        )
        # Active file pinning: keeps recently-read file content in context
        # even after compression. Max 4 files (FIFO eviction).
        self._pinned_files: deque[tuple[str, str]] = deque(maxlen=4)
        self._pinned_token_budget: int = config.pinned_token_budget
        self._cached_pinned_tokens: int = 0
        self._cached_msg_tokens: int = 0
        self._last_persist_ts: float = 0.0
        self._event_listeners: list[Callable[[MemoryEvent], None]] = []
        self._is_compacting: bool = False
        self.enable_auto_compaction: bool = getattr(config, "enable_auto_compaction", True)
        
        # Deduplication engine
        self._deduplication_engine = DeduplicationEngine(tokenizer=self.tokenizer)
        self._enable_deduplication: bool = True
        self._last_deduplication_stats: Optional[DeduplicationStats] = None
        
        # Load persisted dedup cache and user preferences
        if self._project_memory:
            self.load_dedup_cache()
            prefs = self.load_user_preferences()
            if prefs:
                self._enable_deduplication = prefs.get("enable_deduplication", True)
                if "dedup_similarity_threshold" in prefs:
                    self._deduplication_engine.similarity_detector.threshold = prefs["dedup_similarity_threshold"]

    def add_event_listener(self, listener: Callable[[MemoryEvent], None]) -> None:
        """Register a callback for memory events (MESSAGE_ADDED, PIN_ADDED, COMPACTION_TRIGGERED, etc.)."""
        if listener not in self._event_listeners:
            self._event_listeners.append(listener)

    def remove_event_listener(self, listener: Callable[[MemoryEvent], None]) -> None:
        """Unregister a memory event callback."""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)

    def _dispatch_event(self, event: MemoryEvent) -> None:
        """Dispatch a memory event to registered listeners safely."""
        for listener in list(getattr(self, "_event_listeners", [])):
            try:
                listener(event)
            except Exception:
                pass

    def _check_event_compaction(self, cause_message: Optional[Message] = None) -> bool:
        """Reactive event-driven compaction trigger. Automatically runs when token ratio crosses threshold."""
        if not getattr(self, "enable_auto_compaction", True) or getattr(self, "_is_compacting", False):
            return False

        tot = max(self.total_tokens, getattr(self, "_total_tokens", 0))
        ratio = tot / self.config.max_tokens if self.config.max_tokens > 0 else 0
        if ratio > self.config.compression_threshold and len(self.messages) > 1:
            self._is_compacting = True
            try:
                self._dispatch_event(
                    MemoryEvent(
                        event_type=MemoryEventType.COMPACTION_TRIGGERED,
                        message=cause_message,
                        total_tokens=tot,
                        token_ratio=ratio,
                    )
                )
                self.compress_recent(force=True)
                return True
            finally:
                self._is_compacting = False
        return False

    def load_project_memory(self) -> None:
        """Load persistent project memory (.context-memory.json) into L0 working state."""
        if not self._project_memory:
            return
        try:
            data = self._project_memory.load()
            if data:
                for d in data.get("arch_decisions", []) + data.get("decisions", []):
                    if not isinstance(d, str):
                        d = d.get("text") if isinstance(d, dict) else str(d)
                    d = d.strip() if d else ""
                    if _is_valid_decision(d) and d not in self.state.decisions:
                        self.state.decisions.append(d)
                for f in data.get("files_modified", []):
                    if f and f not in self.state.files_modified:
                        self.state.files_modified.append(f)
                for t in data.get("tech_stack", []):
                    if t and t not in self.state.tech_stack:
                        self.state.tech_stack.append(t)
                for tf in data.get("tried_and_failed", []):
                    if tf and tf not in self.state.tried_and_failed:
                        self.state.tried_and_failed.append(tf)
                for e in data.get("errors_seen", []):
                    if e and e not in self.state.errors_seen:
                        self.state.errors_seen.append(e)
                for f in data.get("facts", []):
                    if isinstance(f, dict):
                        f = f.get("text") or f.get("summary") or ""
                    if _is_valid_decision(f) and f not in self.state.decisions:
                        self.state.decisions.append(f)
        except Exception:
            pass

    def persist_to_project_memory(self, force: bool = False) -> None:
        """Persist L0 working state to disk in .context-memory.json (debounced)."""
        if not self._project_memory:
            return
        now = datetime.now().timestamp()
        if not force and (now - self._last_persist_ts) < 5.0:
            return
        self._last_persist_ts = now
        # Prune session state before persisting to keep serialized size manageable
        self._prune_session_state()
        try:
            self._project_memory.persist_session_state(self.state)
        except Exception:
            pass

    def _estimate_l0_tokens(self) -> int:
        """Fast O(1) estimate of dynamic L0 scratchpad tokens without disk I/O or recursion."""
        chars = 0
        if self.state.errors_seen:
            chars += sum(len(e) for e in self.state.errors_seen[-5:])
        if self.state.failing_tests:
            chars += sum(len(str(t)) for t in self.state.failing_tests[-5:])
        if self.state.current_task:
            chars += len(self.state.current_task)
        if self.state.decisions:
            chars += sum(len(d) for d in self.state.decisions[-5:])
        if self.state.arch_decisions:
            chars += sum(len(d) for d in self.state.arch_decisions[-5:])
        if self.state.files_modified:
            chars += sum(len(f) + 20 for f in self.state.files_modified[-3:])
        if self.state.active_file:
            chars += len(self.state.active_file) + 20
        if chars == 0:
            return 0
        return max(15, chars // 4)

    @property
    def total_tokens(self) -> int:
        return self._cached_msg_tokens + self._cached_pinned_tokens + self._estimate_l0_tokens()

    def _append_message(self, msg: Message) -> None:
        if len(self.messages) == self.messages.maxlen and self.messages:
            old = self.messages[0]
            self._cached_msg_tokens = max(0, self._cached_msg_tokens - old.token_count)
        self.messages.append(msg)
        self._cached_msg_tokens += msg.token_count

        if not getattr(self, "_is_compacting", False):
            tot = max(self.total_tokens, getattr(self, "_total_tokens", 0))
            ratio = tot / self.config.max_tokens if self.config.max_tokens > 0 else 0
            self._dispatch_event(
                MemoryEvent(
                    event_type=MemoryEventType.MESSAGE_ADDED,
                    message=msg,
                    total_tokens=tot,
                    token_ratio=ratio,
                )
            )
            self._check_event_compaction(cause_message=msg)

    def add_system_message(self, content: str) -> None:
        msg = Message(
            role=MessageRole.SYSTEM,
            content=content,
            token_count=self.tokenizer.count(content),
        )
        self._append_message(msg)
        self._update_state_from_message(msg)

    def update_system_prompt(self, content: str) -> None:
        """Update or set the primary system prompt (first system message in history)."""
        token_count = self.tokenizer.count(content)
        for msg in self.messages:
            role = (
                msg.role.value if isinstance(msg.role, MessageRole) else str(msg.role)
            )
            if role == "system":
                self._cached_msg_tokens = max(
                    0, self._cached_msg_tokens - msg.token_count + token_count
                )
                msg.content = content
                msg.token_count = token_count
                return
        self.add_system_message(content)

    def record_image_attached(
        self, path: Union[str, Path], project_root: Optional[str] = None
    ) -> None:
        """Record an attached image in SessionState, normalizing to a relative workspace path."""
        if not path:
            return
        p_str = str(path).strip()
        if p_str.startswith("data:image/"):
            return
        # Normalize to relative path if within project_root
        if project_root and os.path.isabs(p_str):
            try:
                rel = os.path.relpath(p_str, project_root)
                if not rel.startswith(".."):
                    p_str = rel
            except Exception:
                pass
        if p_str not in self.state.active_images:
            self.state.active_images.append(p_str)
            if len(self.state.active_images) > 5:
                self.state.active_images = self.state.active_images[-5:]

    def add_user_message(
        self,
        content: str,
        images: Optional[list[str]] = None,
        project_root: Optional[str] = None,
    ) -> None:
        img_list = list(images) if images else []
        tok_count = self.tokenizer.count(content)
        if img_list:
            for img in img_list:
                tok_count += self.tokenizer.count_image(img)
                self.record_image_attached(img, project_root=project_root)
        msg = Message(
            role=MessageRole.USER,
            content=content,
            images=img_list,
            token_count=tok_count,
        )
        self._append_message(msg)
        self._update_state_from_message(msg)

    def add_assistant_message(self, content: str) -> None:
        msg = Message(
            role=MessageRole.ASSISTANT,
            content=content,
            token_count=self.tokenizer.count(content),
        )
        self._append_message(msg)
        self._update_state_from_message(msg)

    def add_tool_result(
        self, content: str, tool_name: str = "", images: Optional[list[str]] = None
    ) -> None:
        img_list = list(images) if images else []
        tok_count = self.tokenizer.count(content)
        if img_list:
            for img in img_list:
                tok_count += self.tokenizer.count_image(img)
        msg = Message(
            role=MessageRole.TOOL_RESULT,
            content=content,
            images=img_list,
            token_count=tok_count,
            metadata={"tool_name": tool_name},
        )
        self._append_message(msg)

    def get_effective_budget(self) -> ContextBudget:
        """Return headroom-aware budget allocations for the current turn."""
        return ContextBudget(
            max_tokens=self.config.max_tokens,
            used_tokens=self._cached_msg_tokens + self._cached_pinned_tokens,
            base_pinned_tokens=self.config.pinned_token_budget,
            metadata_overhead=self.config.metadata_overhead,
        )

    def pin_file(self, path: str, content: str) -> None:
        """Pin a recently-read file slice so it survives compression without bloating context.

        If the file is already pinned, update its content. Otherwise add it
        to the FIFO queue (oldest evicted when full).
        """
        # Truncate content to the headroom-aware pinned budget if necessary
        budget_tokens = self.get_effective_budget().pinned_tokens
        tokens = self.tokenizer.count(content)
        if tokens > budget_tokens:
            lines = content.splitlines()
            truncated_lines = []
            current_tokens = 0
            for line in lines:
                l_tokens = self.tokenizer.count(line + "\n")
                if current_tokens + l_tokens > budget_tokens:
                    truncated_lines.append("... [truncated to fit context budget] ...")
                    break
                truncated_lines.append(line)
                current_tokens += l_tokens
            content = "\n".join(truncated_lines)

        # Update existing pin
        for i, (p, _) in enumerate(self._pinned_files):
            if p == path:
                self._pinned_files[i] = (path, content)
                self._cached_pinned_tokens = sum(self.tokenizer.count(c) for _, c in self._pinned_files)
                self._notify_pin_event(path)
                return
        # New pin — FIFO eviction when deque is full
        self._pinned_files.append((path, content))
        self._cached_pinned_tokens = sum(self.tokenizer.count(c) for _, c in self._pinned_files)
        self._notify_pin_event(path)

    def _notify_pin_event(self, path: str) -> None:
        if not getattr(self, "_is_compacting", False):
            tot = max(self.total_tokens, getattr(self, "_total_tokens", 0))
            ratio = tot / self.config.max_tokens if self.config.max_tokens > 0 else 0
            self._dispatch_event(
                MemoryEvent(
                    event_type=MemoryEventType.PIN_ADDED,
                    total_tokens=tot,
                    token_ratio=ratio,
                    metadata={"path": path},
                )
            )
            self._check_event_compaction()

    def unpin_file(self, path: str) -> None:
        """Remove a file from pinned memory if deleted or stale."""
        self._pinned_files = deque(
            [(p, c) for p, c in self._pinned_files if p != path],
            maxlen=self._pinned_files.maxlen,
        )
        self._cached_pinned_tokens = sum(self.tokenizer.count(c) for _, c in self._pinned_files)

    def refresh_pin(self, path: str, project_root: str) -> None:
        """Re-read an edited file from disk and update its pin in memory."""
        try:
            from core.tools.implementations import tool_read_file_impl

            res = tool_read_file_impl({"path": path}, project_root)
            if (
                res
                and not res.startswith("Error")
                and not res.startswith("File not found")
            ):
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
        self._cached_pinned_tokens = 0

    def add_message(
        self, role: MessageRole, content: str, metadata: Optional[dict] = None
    ) -> None:
        """Generic add_message method for role-based message addition."""
        msg = Message(
            role=role,
            content=content,
            token_count=self.tokenizer.count(content),
            metadata=metadata or {},
        )
        self._append_message(msg)
        self._update_state_from_message(msg)

    def should_compress(self) -> bool:
        override = getattr(self, "_total_tokens", 0)
        tot = max(self.total_tokens, override)
        ratio = tot / self.config.max_tokens if self.config.max_tokens > 0 else 0
        # Emergency ratio override at >= 0.85 (85%) token usage even if message count is small
        if ratio >= 0.85:
            return True
        if len(self.messages) <= 1 and override == 0:
            return False
        return ratio > self.config.compression_threshold

    def compress_recent(
        self,
        summarizer_fn: Optional[Callable] = None,
        preserve_first: int = 0,
        force: bool = False,
    ) -> str:
        """Compress older messages, preserving the first N messages. Truncates oversized messages if needed."""
        # Run deduplication first to reduce context before compression
        # Only run when there's actual context pressure (not just for testing)
        if self._enable_deduplication and len(self.messages) > 1:
            current_ratio = self.total_tokens / self.config.max_tokens if self.config.max_tokens > 0 else 0
            # Only deduplicate when context is getting full or forced
            if current_ratio >= 0.6 or force:
                self.deduplicate_context()
        
        # Auto-upgrade force to True if overall context ratio is high
        current_ratio = self.total_tokens / self.config.max_tokens if self.config.max_tokens > 0 else 0
        if current_ratio >= 0.75:
            force = True

        min_messages = 1 if force else (self.config.recent_window + preserve_first)
        window_size = 1 if force else self.config.recent_window
        recent = list(self.messages)[-window_size:] if window_size > 0 else []
        preserved = list(self.messages)[:preserve_first]
        older = (
            list(self.messages)[preserve_first:-window_size]
            if window_size > 0 and len(self.messages) > (preserve_first + window_size)
            else list(self.messages)[preserve_first:]
        )

        summary = ""
        if older and len(self.messages) > min_messages:
            self.messages.clear()
            self._cached_msg_tokens = 0
            for msg in preserved:
                self._append_message(msg)

            if summarizer_fn:
                try:
                    raw_sum = summarizer_fn(older, state=self.state)
                except TypeError:
                    raw_sum = summarizer_fn(older)
                summary = str(raw_sum) if raw_sum is not None else ""
                sys_msg = Message(
                    role=MessageRole.SYSTEM,
                    content=f"[Context summary of older turns]\n{summary}",
                    token_count=self.tokenizer.count(summary) + 10,
                )
                self._append_message(sys_msg)
            else:
                summary = (
                    f"[Context compacted. {len(older)} turns omitted to save memory.]"
                )
                sys_msg = Message(
                    role=MessageRole.SYSTEM,
                    content=summary,
                    token_count=self.tokenizer.count(summary),
                )
                self._append_message(sys_msg)

            for msg in recent:
                self._append_message(msg)

        # Fallback payload compaction: if older turns could not be summarized or context ratio remains high,
        # compact oversized individual messages in history (e.g. giant tool results or output dumps)
        post_ratio = self.total_tokens / self.config.max_tokens if self.config.max_tokens > 0 else 0
        if (not summary or post_ratio >= 0.70) and len(self.messages) > 1:
            max_msg_budget = max(400, int(self.config.max_tokens * 0.20))
            modified_any = False
            for i in range(1, len(self.messages)):
                msg = self.messages[i]
                if msg.token_count > max_msg_budget:
                    lines = msg.content.splitlines()
                    if len(lines) > 20:
                        head = lines[:10]
                        tail = lines[-10:]
                        omitted_count = len(lines) - 20
                        new_content = "\n".join(head) + f"\n... [{omitted_count} lines / tool output payload truncated to fit context budget] ...\n" + "\n".join(tail)
                    else:
                        new_content = self.tokenizer.truncate(msg.content, max_msg_budget)
                    new_tokens = self.tokenizer.count(new_content)
                    self._cached_msg_tokens = max(0, self._cached_msg_tokens - msg.token_count + new_tokens)
                    msg.content = new_content
                    msg.token_count = new_tokens
                    modified_any = True
            if modified_any and not summary:
                summary = "[Oversized tool results and output payloads compacted to fit context budget]"

        return summary

    async def compress_recent_async(
        self,
        summarizer_fn: Optional[Callable] = None,
        preserve_first: int = 0,
        force: bool = False,
    ) -> None:
        """Async wrapper for compress_recent."""
        self.compress_recent(summarizer_fn, preserve_first, force=force)

    def compact_between_tasks(self, summarizer_fn: Optional[Callable] = None) -> None:
        """Compact context between tasks while preserving continuous session state.

        Unlike clear(), this retains SessionState (files_modified, errors_seen,
        decisions, tech_stack, etc.) and pinned files, while compressing message
        history into an L2 context summary so context budget remains under control
        without losing debug and code improvement history.
        """
        if not self.messages:
            return

        older_messages = list(self.messages)
        self.messages.clear()

        # Prune session state to prevent unbounded growth
        self._prune_session_state()

        summary_content = None
        if summarizer_fn:
            try:
                summary_content = summarizer_fn(older_messages)
            except Exception:
                summary_content = None

        if summary_content:
            self.messages.append(
                Message(
                    role=MessageRole.SYSTEM,
                    content=f"[Continuous Session Summary of Prior Tasks]\n{summary_content}",
                    token_count=self.tokenizer.count(summary_content) + 10,
                )
            )
        else:
            state_parts = []
            if self.state.files_modified:
                state_parts.append(
                    f"Modified files: {', '.join(list(self.state.files_modified)[-5:])}"
                )
            if self.state.errors_seen:
                state_parts.append(
                    f"Errors seen: {', '.join(list(self.state.errors_seen)[-3:])}"
                )
            if self.state.decisions:
                state_parts.append(
                    f"Key decisions: {', '.join(str(d) for d in list(self.state.decisions)[-3:])}"
                )

            summary_text = (
                "; ".join(state_parts)
                if state_parts
                else f"{len(older_messages)} prior turns"
            )
            self.messages.append(
                Message(
                    role=MessageRole.SYSTEM,
                    content=f"[Continuous Session Summary: {summary_text}]",
                    token_count=self.tokenizer.count(summary_text) + 10,
                )
            )

    def get_context_for_llm(
        self,
        user_query: str = "",
        project_root: Optional[str] = None,
        format: str = "openai",
        vision_supported: bool = True,
    ) -> list[dict]:
        """Build the message list for the LLM.

        Pinned files and dynamic L0 Scratchpad are appended as trailing system
        messages AFTER the conversation history so the stable system + history
        prefix stays byte-identical across agent iterations. This lets the
        inference server reuse its cached KV prefix (cached_tokens > 0) instead
        of re-evaluating the full context on every tool call, while keeping exact
        file content and goal progress visible to the model right before it
        generates.
        
        Deduplication is applied to messages before context building to save tokens.
        """
        # Apply deduplication to LLM context payload without mutating active history
        messages_to_render = self.messages
        if self._enable_deduplication and len(self.messages) > 1:
            deduplicated_messages, stats = self._deduplication_engine.process_messages(list(self.messages))
            self._last_deduplication_stats = stats
            messages_to_render = deduplicated_messages
        
        context = []
        pinned_budget = self.get_effective_budget().pinned_tokens
        l0_scratchpad = self.format_l0_scratchpad(project_root=project_root)

        for msg in messages_to_render:
            if hasattr(msg, "to_dict"):
                context.append(
                    msg.to_dict(
                        format=format,
                        project_root=project_root,
                        vision_supported=vision_supported,
                    )
                )
            else:
                role = (
                    msg.role.value if isinstance(msg.role, MessageRole) else str(msg.role)
                )
                context.append({"role": role, "content": msg.content})

        # Append L0 Scratchpad and pinned files after history (trailing system blocks)
        if l0_scratchpad:
            context.append({"role": "system", "content": l0_scratchpad})
        if self._pinned_files:
            pinned_lines = ["[Pinned file contents — use for EDIT_FILE old_text:]"]
            pinned_tokens = 0
            for path, content in self._pinned_files:
                entry = f"\n--- {path} ---\n{content}\n--- end {path} ---"
                entry_tokens = self.tokenizer.count(entry)
                if pinned_tokens + entry_tokens > pinned_budget:
                    break
                pinned_lines.append(entry)
                pinned_tokens += entry_tokens
            if len(pinned_lines) > 1:
                context.append({"role": "system", "content": "\n".join(pinned_lines)})

        return context

    def deduplicate_context(self, force: bool = False) -> DeduplicationStats:
        """Run semantic deduplication on current message history.
        
        Args:
            force: Force deduplication even if recently run
            
        Returns:
            DeduplicationStats with details on what was deduplicated
        """
        if not self._enable_deduplication:
            return DeduplicationStats()
        
        if len(self.messages) <= 1:
            return DeduplicationStats()
        
        deduplicated_messages, stats = self._deduplication_engine.process_messages(list(self.messages))
        
        if stats.deduplicated_messages > 0 or force:
            self.messages.clear()
            self._cached_msg_tokens = 0
            for msg in deduplicated_messages:
                self._append_message(msg)
            self._last_deduplication_stats = stats
            # Persist updated cache
            self.save_dedup_cache()
        
        return stats

    def enable_deduplication(self, enabled: bool = True) -> None:
        """Enable or disable semantic deduplication."""
        self._enable_deduplication = enabled
        if not enabled:
            self._deduplication_engine.reset()

    def get_deduplication_stats(self) -> Optional[DeduplicationStats]:
        """Get the last deduplication statistics."""
        return self._last_deduplication_stats

    def save_dedup_cache(self) -> None:
        """Persist deduplication cache to project memory."""
        if not self._project_memory:
            return
        try:
            cache = self._deduplication_engine.get_cache()
            self._project_memory.save_dedup_cache(cache)
        except Exception:
            pass

    def load_dedup_cache(self) -> None:
        """Load deduplication cache from project memory."""
        if not self._project_memory:
            return
        try:
            cache = self._project_memory.load_dedup_cache()
            self._deduplication_engine.load_cache(cache)
        except Exception:
            pass

    def save_user_preferences(self, preferences: dict) -> None:
        """Persist user preferences to project memory."""
        if not self._project_memory:
            return
        try:
            self._project_memory.save_user_preferences(preferences)
        except Exception:
            pass

    def load_user_preferences(self) -> dict:
        """Load user preferences from project memory."""
        if not self._project_memory:
            return {}
        try:
            return self._project_memory.load_user_preferences()
        except Exception:
            return {}

    def format_l0_scratchpad(
        self,
        project_root: Optional[str] = None,
        budget: Optional[ContextBudget] = None,
    ) -> str:
        """Format current SessionState into a dynamic L0 working memory scratchpad.

        Enforces a maximum L0 budget cap (up to 1800 tokens / ~15% context window)
        and priority-weighted injection order. Each section surfaces up to
        `budget.scratchpad_section_cap` entries (3 tight ... 8 rich) so the
        scratchpad expands to use idle headroom and shrinks under pressure:
        1. Active errors_seen (most recent)
        2. Failing tests (names only, not full tracebacks)
        3. Active goal / current task
        4. Architecture decisions (most recent)
        5. Files modified in last 3 turns
        6. Tech stack (only if non-empty)
        7. Tried_and_failed (only if relevant to current file/task)
        8. Facts (skip entirely if budget exhausted)
        
        Enhanced with:
        - Content-aware entry selection (not just priority-ordered)
        - Deduplication within scratchpad
        - Dynamic sizing based on model profile
        """
        if budget is None:
            budget = self.get_effective_budget()
        entry_limit = budget.scratchpad_entry_limit
        section_cap = budget.scratchpad_section_cap
        max_chars = min(1800 * budget.chars_per_token, budget.l0_chars)
        sections = []

        # Track added content to avoid duplication
        added_content = set()

        def add_section(priority: float, line: str) -> bool:
            """Add a section if not duplicated and within budget."""
            content_key = line[:100]  # Use first 100 chars as dedup key
            if content_key in added_content:
                return False
            added_content.add(content_key)
            sections.append((priority, line))
            return True

        # Priority 1: Active errors_seen (most recent, up to section cap)
        if self.state.errors_seen:
            unique_errors = list(dict.fromkeys(self.state.errors_seen))[-section_cap:]
            shown = "; ".join(_scratchpad_clean(e, entry_limit) for e in unique_errors)
            add_section(1, f"- Active Errors: {shown}")

        # Priority 2: Failing tests (names only, not full tracebacks)
        if self.state.failing_tests:
            clean_test_names = []
            for t in self.state.failing_tests:
                t_str = str(t).split("\n")[0]
                t_name = t_str.split("::")[-1].strip()
                if t_name and t_name not in clean_test_names:
                    clean_test_names.append(t_name)
            if clean_test_names:
                shown = ", ".join(
                    _scratchpad_clean(tn, entry_limit)
                    for tn in clean_test_names[:section_cap]
                )
                add_section(2, f"- Failing Tests: {shown}")

        # Priority 2.5: Active image attachments & visual assets
        if getattr(self.state, "active_images", None):
            from core.utils.image_utils import get_image_metadata

            img_items = []
            for img_p in self.state.active_images[-section_cap:]:
                meta = get_image_metadata(img_p, project_root=project_root)
                w, h = meta.get("width", 0), meta.get("height", 0)
                dim_str = (
                    f" ({w}x{h} {meta.get('format', 'IMG')})"
                    if w > 0 and h > 0
                    else ""
                )
                img_items.append(f"{img_p}{dim_str}")
            if img_items:
                add_section(2.5, f"- Active Images: {', '.join(img_items)}")

        # Priority 3: Active task, status, next task, & active file (suppressed in Chat Mode)
        mode_val = getattr(self.state, "execution_mode", None)
        mode_str = mode_val.value if hasattr(mode_val, "value") else str(mode_val or "").lower()
        is_chat_mode = mode_str == "chat" or mode_str.endswith(".chat")

        if not is_chat_mode:
            if project_root:
                from core.tools.task_helpers import get_compact_task_matrix

                matrix_lines = get_compact_task_matrix(project_root, budget=budget)
                if matrix_lines:
                    for idx, line in enumerate(matrix_lines):
                        add_section(3.0 + idx * 0.1, line)
                elif self.state.current_task:
                    add_section(
                        3.0,
                        f"- Active Goal: {_scratchpad_clean(self.state.current_task, entry_limit)}",
                    )
            elif self.state.current_task:
                add_section(
                    3.0,
                    f"- Active Goal: {_scratchpad_clean(self.state.current_task, entry_limit)}",
                )

        if self.state.active_file:
            add_section(
                3.1,
                f"- Active File: {_scratchpad_clean(self.state.active_file, entry_limit)}",
            )

        # Priority 4: Architecture decisions (most recent, up to section cap)
        decs_source = self.state.arch_decisions or self.state.decisions
        if decs_source:
            decs_strs = [str(d) for d in decs_source]
            shown = "; ".join(
                _scratchpad_clean(d, entry_limit) for d in decs_strs[-section_cap:]
            )
            add_section(4, f"- Key Decisions: {shown}")

        # Priority 5: Files modified in last 3 turns
        if self.state.files_modified:
            recent_mod = self.state.files_modified[-3:]
            mod_items = []
            for f in recent_mod:
                clean_f = _scratchpad_clean(f, entry_limit)
                stats = self.state.files_modified_stats.get(f)
                if stats and len(stats) == 2:
                    clean_f += f" (+{stats[0]}, -{stats[1]})"
                syms = self.state.files_modified_symbols.get(f)
                if syms:
                    clean_f += f" [{', '.join(syms[:3])}]"
                mod_items.append(clean_f)
            shown = ", ".join(mod_items)
            add_section(5, f"- Modified Files: {shown}")

        # Priority 6: Tech stack (only if non-empty)
        if self.state.tech_stack:
            shown = ", ".join(
                _scratchpad_clean(t, entry_limit) for t in self.state.tech_stack[:4]
            )
            add_section(6, f"- Tech Stack: {shown}")

        # Priority 7: Tried_and_failed (up to section cap, only if relevant to current file/task)
        if self.state.tried_and_failed:
            tf_candidates = self.state.tried_and_failed
            if self.state.active_file:
                active_base = (
                    self.state.active_file.split("/")[-1].split(".")[0].lower()
                )
                rel_tf = [
                    t
                    for t in tf_candidates
                    if active_base and active_base in str(t).lower()
                ]
                if rel_tf:
                    tf_candidates = rel_tf
            shown = "; ".join(
                _scratchpad_clean(t, entry_limit)
                for t in list(dict.fromkeys(tf_candidates))[-section_cap:]
            )
            add_section(7, f"- Tried & Failed: {shown}")

        # Priority 8: Facts (skip entirely if budget exhausted)
        if self._project_memory and (self.state.current_task or self.state.intent):
            try:
                q_text = self.state.current_task or self.state.intent
                retrieved = self._project_memory.search_memory(q_text, top_k=3)
                if retrieved:
                    mem_texts = [
                        _scratchpad_clean(m[0].summary, entry_limit)
                        for m in retrieved
                        if m[0].summary
                    ]
                    if mem_texts:
                        add_section(
                            8, f"- Facts & Past Context: {'; '.join(mem_texts)}"
                        )
            except Exception:
                pass

        if not sections:
            return ""

        sections.sort(key=lambda s: s[0])
        lines = [_SCRATCHPAD_HEADER]
        used = len(_SCRATCHPAD_HEADER)
        for _, line in sections:
            if used + 1 + len(line) <= max_chars:
                lines.append(line)
                used += 1 + len(line)
                continue
            remaining = max_chars - used
            if remaining > 21:
                budget_chars = remaining - 1 - 4
                lines.append(line[:budget_chars].rstrip() + " ...")
            break
        return "\n".join(lines)

    def record_memory(
        self, entry: str, category: str = "decision", channel_id: str = "default"
    ) -> None:
        """Record an explicit memory entry into SessionState and persist to project memory."""
        entry = str(entry).strip()
        cat_lower = category.lower().strip()
        if cat_lower in ("tried_failed", "tried_and_failed", "failed"):
            if entry not in self.state.tried_and_failed:
                self.state.tried_and_failed.append(entry)
        elif cat_lower in ("arch_decision", "architectural"):
            if entry not in self.state.arch_decisions:
                self.state.arch_decisions.append(entry)
            if entry not in self.state.decisions:
                self.state.decisions.append(entry)
        else:
            if entry not in self.state.decisions:
                self.state.decisions.append(entry)

        from .embeddings import tokenize_text

        mo = MemoryObject(
            kind=category,
            summary=entry,
            source="user_record",
            channel_id=channel_id,
            vector_tokens=tokenize_text(entry),
            file_paths=list(self.state.files_modified),
            timestamp=datetime.now(),
        )
        self.state.memory_objects.append(mo)
        if self._project_memory and hasattr(self._project_memory, "add_memory_object"):
            try:
                self._project_memory.add_memory_object(mo)
            except Exception:
                pass

        # Explicit memory saves must be durable immediately (debounce bypassed).
        self.persist_to_project_memory(force=True)

    def get_available_headroom(self) -> int:
        """Calculate remaining token budget headroom before reaching max_tokens threshold."""
        used = self.total_tokens
        return max(0, self.config.max_tokens - used)

    def build_critical_context(self) -> str:
        """Build critical context block from session state."""
        return self.format_l0_scratchpad()

    def predict_next_tools(self) -> list[str]:
        """Predict likely next tools based on current state."""
        tools = []
        _EXPLORE_KEYWORDS = {
            "understand",
            "how",
            "what",
            "where",
            "find",
            "architecture",
            "depends",
            "explain",
            "structure",
            "callers",
            "relationship",
        }
        intent_lower = (self.state.intent or self.state.current_task or "").lower()
        # Suggest SEARCH_AST first for exploration or when no file is focused yet
        if (
            not self.state.active_file
            or not self.state.files_modified
            or any(kw in intent_lower for kw in _EXPLORE_KEYWORDS)
        ):
            tools.append("SEARCH_AST")
        if self.state.active_file:
            tools.append("READ_FILE")
        if self.state.errors_seen:
            tools.append("GREP")
        return tools

    def get_intent_for_retrieval(self) -> str:
        return self.state.intent or self.state.current_task

    def get_active_file_hint(self) -> str:
        return self.state.active_file

    def get_snapshot(self) -> ContextSnapshot:
        return ContextSnapshot(
            token_count=self.total_tokens,
            message_count=len(self.messages),
            compression_ratio=self.total_tokens / self.config.max_tokens
            if self.config.max_tokens > 0
            else 0,
            active_file=self.state.active_file,
            tech_stack=self.state.tech_stack,
            errors_seen=self.state.errors_seen,
            files_modified=self.state.files_modified,
            decisions=self.state.decisions,
        )

    def _prune_session_state(self) -> None:
        """Trim SessionState lists to configured maximum to prevent unbounded growth."""
        max_entries = self.config.max_session_state_entries
        
        # Lists to prune (keep most recent entries)
        lists_to_prune = [
            ("files_modified", max_entries),
            ("errors_seen", max_entries),
            ("decisions", max_entries),
            ("arch_decisions", max_entries),
            ("tried_and_failed", max_entries),
            ("tech_stack", max_entries),
            ("failing_tests", max_entries),
            ("dependencies_added", max_entries),
            ("files_read", max_entries),
        ]
        
        for attr_name, limit in lists_to_prune:
            lst = getattr(self.state, attr_name, None)
            if lst and len(lst) > limit:
                setattr(self.state, attr_name, lst[-limit:])
        
        # Also prune dicts that track file metadata
        dicts_to_prune = [
            "files_modified_stats",
            "files_modified_symbols",
            "files_baseline_content",
        ]
        for attr_name in dicts_to_prune:
            d = getattr(self.state, attr_name, None)
            if d and len(d) > max_entries:
                # Keep only entries for the most recently modified files
                recent_files = set(self.state.files_modified[-max_entries:])
                pruned = {k: v for k, v in d.items() if k in recent_files}
                setattr(self.state, attr_name, pruned)

    def clear(self) -> None:
        self.messages.clear()
        self._pinned_files.clear()
        self._cached_msg_tokens = 0
        self.state = SessionState()

    def record_file_modified(
        self,
        path: str,
        added: int = 0,
        deleted: int = 0,
        old_content: Optional[str] = None,
        new_content: Optional[str] = None,
    ) -> None:
        """Explicitly record a modified file, Net Delta line stats, and touched symbols in session state."""
        if is_valid_file_path(path):
            clean_p = path.strip().strip("'\"`()[],:;")
            if clean_p not in self.state.files_modified:
                self.state.files_modified.append(clean_p)

            # 1. Baseline tracking & Net Delta computation
            if old_content is not None and clean_p not in self.state.files_baseline_content:
                self.state.files_baseline_content[clean_p] = old_content

            if clean_p in self.state.files_baseline_content and new_content is not None:
                net_added, net_deleted = calculate_in_memory_diff(
                    self.state.files_baseline_content[clean_p], new_content
                )
                self.state.files_modified_stats[clean_p] = [net_added, net_deleted]
            else:
                if clean_p not in self.state.files_modified_stats:
                    self.state.files_modified_stats[clean_p] = [added, deleted]
                else:
                    prev = self.state.files_modified_stats[clean_p]
                    self.state.files_modified_stats[clean_p] = [prev[0] + added, prev[1] + deleted]

            # 2. Modified symbol tracking
            if old_content is not None and new_content is not None:
                syms = extract_modified_symbols(old_content, new_content)
                if syms:
                    if clean_p not in self.state.files_modified_symbols:
                        self.state.files_modified_symbols[clean_p] = []
                    for s in syms:
                        if s not in self.state.files_modified_symbols[clean_p]:
                            self.state.files_modified_symbols[clean_p].append(s)

            self.state.active_file = clean_p
            self.persist_to_project_memory()

    def record_file_read(self, path: str) -> None:
        """Explicitly record a read file in session state if it is a valid file path."""
        if is_valid_file_path(path):
            clean_p = path.strip().strip("'\"`()[],:;")
            if clean_p not in self.state.files_read:
                self.state.files_read.append(clean_p)
            self.state.active_file = clean_p
            self.persist_to_project_memory()

    def _update_state_from_message(self, msg: Message) -> None:
        content = msg.content
        role_str = (
            msg.role.value
            if isinstance(msg.role, MessageRole)
            else str(msg.role).lower()
        )

        # User messages: extract explicit valid file paths requested/read
        if role_str == "user":
            candidates = re.findall(
                r"(?:[a-zA-Z0-9_\-/\\]+\.)+[a-zA-Z0-9_\-]+", content
            )
            for p in candidates:
                if is_valid_file_path(p) and p not in self.state.files_read:
                    self.state.files_read.append(p)

        # Assistant messages: scan ONLY for explicit tool calls (JSON or XML or tool syntax) writing/editing files
        elif role_str == "assistant":
            # 1. JSON tool calls: <tool_call>{"name": "WRITE_FILE", "arguments": {"path": "..."}}</tool_call>
            for match in re.finditer(
                r"<tool_call>\s*({[\s\S]*?})\s*</tool_call>", content
            ):
                try:
                    import json

                    data = json.loads(match.group(1))
                    name = (data.get("name") or "").upper()
                    if name in (
                        "WRITE_FILE",
                        "EDIT_FILE",
                        "WRITE_FILE_IMPL",
                        "EDIT_FILE_IMPL",
                    ):
                        args = data.get("arguments") or data.get("params") or {}
                        fpath = args.get("path") or args.get("file")
                        if fpath and is_valid_file_path(fpath):
                            self.record_file_modified(fpath)
                except Exception:
                    pass

            # 2. XML tool calls: <WRITE_FILE path="..."> or <EDIT_FILE path="...">
            for xml_call in re.finditer(
                r'<(?:WRITE_FILE|EDIT_FILE)\s+path=["\']([^"\'\n]+)["\']',
                content,
                re.IGNORECASE,
            ):
                if is_valid_file_path(xml_call.group(1)):
                    self.record_file_modified(xml_call.group(1))

        # Tool result messages: check for tool execution results of WRITE_FILE / EDIT_FILE / READ_FILE
        elif role_str in ("tool", "tool_result"):
            tool_name = (msg.metadata.get("tool_name") or "").upper()
            if tool_name in (
                "WRITE_FILE",
                "EDIT_FILE",
                "WRITE_FILE_IMPL",
                "EDIT_FILE_IMPL",
            ):
                for p in re.findall(
                    r"(?:[a-zA-Z0-9_\-/\\]+\.)+[a-zA-Z0-9_\-]+", content
                ):
                    if is_valid_file_path(p):
                        self.record_file_modified(p)
            elif tool_name in ("READ_FILE", "READ_FILE_IMPL"):
                for p in re.findall(
                    r"(?:[a-zA-Z0-9_\-/\\]+\.)+[a-zA-Z0-9_\-]+", content
                ):
                    if is_valid_file_path(p):
                        self.record_file_read(p)

        # Extract errors
        error_matches = re.findall(
            r"(?:Error|Exception|FAILED)[:\s]+([^\n]{10,100})", content
        )
        for err in error_matches[:2]:
            if err not in self.state.errors_seen:
                self.state.errors_seen.append(err)

        self.persist_to_project_memory()
