"""Tiered Memory Manager for Torchlight.

L0-L3 memory hierarchy with progressive compression, active pinning, and deduplication.
"""

from __future__ import annotations

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

from .scratchpad import (
    _SCRATCHPAD_MAX_CHARS,
    _SCRATCHPAD_ENTRY_LIMIT,
    _SCRATCHPAD_HEADER,
    _NON_FILE_EXTENSIONS,
    _VALID_FILE_EXTENSIONS,
    _VALID_EXACT_FILENAMES,
    _is_valid_decision,
    _scratchpad_clean,
    is_valid_file_path,
    calculate_in_memory_diff,
    extract_modified_symbols,
    L0ScratchpadMixin,
)
from .pinning import FilePinningMixin
from .compactor_handler import CompactionMixin

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


class TieredMemory(L0ScratchpadMixin, FilePinningMixin, CompactionMixin):
    """Three-tier memory manager with progressive compression and active file pinning."""

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

    def clear(self) -> None:
        self.messages.clear()
        self._pinned_files.clear()
        self._cached_msg_tokens = 0
        self.state = SessionState()
