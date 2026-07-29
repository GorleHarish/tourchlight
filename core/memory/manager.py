"""
Tiered Memory Manager for Torchlight.

L0-L3 memory hierarchy with progressive compression.
"""

import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable

from .models import Message, MessageRole, SessionState, ContextSnapshot, MemoryNeedle, MemoryObject, WorkingSetSnapshot
from .token_counter import TokenCounter, get_token_counter
from .selective_compression import SelectiveCompressor, CompressionConfig, CompressionLevel


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
    max_messages: int = 50

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

        if max_tokens <= 2000:
            return cls(
                max_tokens=history_budget, recent_window=1,
                recent_tokens=int(history_budget * 0.4), pinned_token_budget=200, compression_threshold=0.5,
                summary_trigger_tokens=int(history_budget * 0.4), message_compact_threshold=200,
                metadata_overhead=metadata_overhead, max_messages=max_messages,
            )
        elif max_tokens <= 4000:
            return cls(
                max_tokens=history_budget, recent_window=2,
                recent_tokens=int(history_budget * 0.35), pinned_token_budget=300, compression_threshold=0.6,
                summary_trigger_tokens=int(history_budget * 0.5), message_compact_threshold=300,
                metadata_overhead=metadata_overhead, max_messages=max_messages,
            )
        elif max_tokens <= 8000:
            return cls(
                max_tokens=history_budget, recent_window=3,
                recent_tokens=int(history_budget * 0.25), pinned_token_budget=600, compression_threshold=0.7,
                summary_trigger_tokens=int(history_budget * 0.75), message_compact_threshold=500,
                metadata_overhead=metadata_overhead, max_messages=max_messages,
            )
        else:
            return cls(
                max_tokens=history_budget, recent_window=5,
                recent_tokens=int(history_budget * 0.2), pinned_token_budget=1000, compression_threshold=0.7,
                summary_trigger_tokens=int(history_budget * 0.75), message_compact_threshold=800,
                metadata_overhead=metadata_overhead, max_messages=max_messages,
            )


class TieredMemory:
    """
    Tiered memory system with L0-L3 hierarchy:
    - L0: Active prompt (current context)
    - L1: Recent messages (full detail)
    - L2: Compressed summaries
    - L3: Persistent project memory
    """

    def __init__(self, config: MemoryConfig, tokenizer: Optional[TokenCounter] = None,
                 project_memory=None, llm_client=None):
        self.config = config
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
        # even after compression. Max 2 files (FIFO eviction).
        self._pinned_files: deque[tuple[str, str]] = deque(maxlen=2)
        self._pinned_token_budget: int = config.pinned_token_budget

    def load_project_memory(self) -> None:
        """Load persistent project memory (.context-memory.json) into L0 working state."""
        if not self._project_memory:
            return
        try:
            data = self._project_memory.load()
            if data:
                for d in data.get("arch_decisions", []) + data.get("decisions", []):
                    if d and d not in self.state.decisions:
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
                    if f and f not in self.state.decisions:
                        self.state.decisions.append(f)
        except Exception:
            pass

    def persist_to_project_memory(self) -> None:
        """Persist L0 working state to disk in .context-memory.json."""
        if not self._project_memory:
            return
        try:
            self._project_memory.persist_session_state(self.state)
        except Exception:
            pass


    @property
    def total_tokens(self) -> int:
        msg_tokens = sum(self.tokenizer.count(m.content) for m in self.messages)
        pinned_tokens = sum(self.tokenizer.count(c) for _, c in self._pinned_files)
        return msg_tokens + pinned_tokens

    def add_system_message(self, content: str) -> None:
        msg = Message(role=MessageRole.SYSTEM, content=content, token_count=self.tokenizer.count(content))
        self.messages.append(msg)
        self._update_state_from_message(msg)

    def add_user_message(self, content: str) -> None:
        msg = Message(role=MessageRole.USER, content=content, token_count=self.tokenizer.count(content))
        self.messages.append(msg)
        self._update_state_from_message(msg)

    def add_assistant_message(self, content: str) -> None:
        msg = Message(role=MessageRole.ASSISTANT, content=content, token_count=self.tokenizer.count(content))
        self.messages.append(msg)
        self._update_state_from_message(msg)

    def add_tool_result(self, content: str, tool_name: str = "") -> None:
        msg = Message(
            role=MessageRole.TOOL_RESULT, content=content,
            token_count=self.tokenizer.count(content),
            metadata={"tool_name": tool_name},
        )
        self.messages.append(msg)

    def pin_file(self, path: str, content: str) -> None:
        """Pin a recently-read file slice so it survives compression without bloating context.

        If the file is already pinned, update its content. Otherwise add it
        to the FIFO queue (oldest evicted when full).
        """
        # Truncate content to fit inside token budget if necessary
        tokens = self.tokenizer.count(content)
        if tokens > self._pinned_token_budget:
            lines = content.splitlines()
            truncated_lines = []
            current_tokens = 0
            for line in lines:
                l_tokens = self.tokenizer.count(line + "\n")
                if current_tokens + l_tokens > self._pinned_token_budget:
                    truncated_lines.append("... [truncated to fit context budget] ...")
                    break
                truncated_lines.append(line)
                current_tokens += l_tokens
            content = "\n".join(truncated_lines)

        # Update existing pin
        for i, (p, _) in enumerate(self._pinned_files):
            if p == path:
                self._pinned_files[i] = (path, content)
                return
        # New pin — FIFO eviction when deque is full
        self._pinned_files.append((path, content))

    def unpin_file(self, path: str) -> None:
        """Remove a file from pinned memory if deleted or stale."""
        self._pinned_files = deque(
            [(p, c) for p, c in self._pinned_files if p != path],
            maxlen=self._pinned_files.maxlen
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

    def should_compress(self) -> bool:
        if len(self.messages) <= 1:
            return False
        ratio = self.total_tokens / self.config.max_tokens
        # Emergency ratio override at >= 0.85 (85%) token usage even if message count is small
        if ratio >= 0.85:
            return True
        if len(self.messages) < self.config.recent_window + 2:
            return False
        return ratio > self.config.compression_threshold

    def compress_recent(self, summarizer_fn: Optional[Callable] = None, preserve_first: int = 0, force: bool = False) -> None:
        """Compress older messages, preserving the first N messages."""
        min_messages = 1 if force else (self.config.recent_window + preserve_first)
        if len(self.messages) <= min_messages:
            return
        
        window_size = 1 if force else self.config.recent_window
        recent = list(self.messages)[-window_size:] if window_size > 0 else []
        preserved = list(self.messages)[:preserve_first]
        older = list(self.messages)[preserve_first:-window_size] if window_size > 0 else list(self.messages)[preserve_first:]
        
        if older:
            self.messages.clear()
            for msg in preserved:
                self.messages.append(msg)
                
            if summarizer_fn:
                summary = summarizer_fn(older)
                self.messages.append(Message(role=MessageRole.SYSTEM, content=f"[Context summary of older turns]\n{summary}"))
            else:
                self.messages.append(Message(role=MessageRole.SYSTEM, content=f"[Context compacted. {len(older)} turns omitted to save memory.]"))
                
            for msg in recent:
                self.messages.append(msg)

    async def compress_recent_async(self, summarizer_fn: Optional[Callable] = None, preserve_first: int = 0, force: bool = False) -> None:
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

        summary_content = None
        if summarizer_fn:
            try:
                summary_content = summarizer_fn(older_messages)
            except Exception:
                summary_content = None

        if summary_content:
            self.messages.append(Message(
                role=MessageRole.SYSTEM,
                content=f"[Continuous Session Summary of Prior Tasks]\n{summary_content}"
            ))
        else:
            state_parts = []
            if self.state.files_modified:
                state_parts.append(f"Modified files: {', '.join(list(self.state.files_modified)[-5:])}")
            if self.state.errors_seen:
                state_parts.append(f"Errors seen: {', '.join(list(self.state.errors_seen)[-3:])}")
            if self.state.decisions:
                state_parts.append(f"Key decisions: {', '.join(list(self.state.decisions)[-3:])}")
            
            summary_text = "; ".join(state_parts) if state_parts else f"{len(older_messages)} prior turns"
            self.messages.append(Message(
                role=MessageRole.SYSTEM,
                content=f"[Continuous Session Summary: {summary_text}]"
            ))


    def get_context_for_llm(self, user_query: str = "", project_root: Optional[str] = None) -> list[dict]:
        """Build the message list for the LLM.

        Pinned files and dynamic L0 Scratchpad are injected into system context
        so the model always has exact file content and goal progress available,
        even after compression.
        """
        context = []
        pinned_injected = False
        l0_scratchpad = self.format_l0_scratchpad(project_root=project_root)

        for msg in self.messages:
            role = msg.role.value if isinstance(msg.role, MessageRole) else str(msg.role)
            context.append({"role": role, "content": msg.content})
            # Inject L0 Scratchpad and pinned files after the first system message
            if not pinned_injected and role == "system":
                if l0_scratchpad:
                    context.append({"role": "system", "content": l0_scratchpad})
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
                        context.append({"role": "system", "content": "\n".join(pinned_lines)})
                pinned_injected = True

        if not pinned_injected:
            if l0_scratchpad:
                context.insert(0, {"role": "system", "content": l0_scratchpad})
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
                    context.insert(0, {"role": "system", "content": "\n".join(pinned_lines)})

        return context

    def format_l0_scratchpad(self, project_root: Optional[str] = None) -> str:
        """Format current SessionState into a dynamic L0 working memory scratchpad for system context."""
        parts = ["[L0 WORKING MEMORY SCRATCHPAD]"]
        if self.state.current_task:
            parts.append(f"- Active Goal: {self.state.current_task}")
        elif project_root:
            import os, json
            g_path = os.path.join(project_root, ".torchlight", "goal_spec.json")
            if os.path.exists(g_path):
                try:
                    with open(g_path, "r", encoding="utf-8") as f:
                        gdata = json.load(f)
                    parts.append(f"- Active Goal: {gdata.get('title', 'Autonomous Goal')}")
                    pending = [t.get('id') for t in gdata.get("tasks", []) if t.get("status") in ("pending", "in_progress")]
                    if pending:
                        parts.append(f"- Pending Tasks: {', '.join(pending[:5])}")
                except Exception:
                    pass

        if self.state.active_file:
            parts.append(f"- Active File: {self.state.active_file}")
        if self.state.files_modified:
            parts.append(f"- Modified Files: {', '.join(self.state.files_modified[-5:])}")
        if self.state.failing_tests:
            parts.append(f"- Failing Tests: {', '.join(self.state.failing_tests[:3])}")
        if self.state.errors_seen:
            parts.append(f"- Active Errors: {'; '.join(self.state.errors_seen[-3:])}")
        if self.state.decisions:
            parts.append(f"- Key Decisions: {'; '.join(self.state.decisions[-3:])}")
        
        if len(parts) == 1:
            return ""
        return "\n".join(parts)

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
        _EXPLORE_KEYWORDS = {"understand", "how", "what", "where", "find", "architecture",
                             "depends", "explain", "structure", "callers", "relationship"}
        intent_lower = (self.state.intent or self.state.current_task or "").lower()
        # Suggest SEARCH_AST first for exploration or when no file is focused yet
        if not self.state.active_file or not self.state.files_modified or \
                any(kw in intent_lower for kw in _EXPLORE_KEYWORDS):
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
            compression_ratio=self.total_tokens / self.config.max_tokens if self.config.max_tokens > 0 else 0,
            active_file=self.state.active_file,
            tech_stack=self.state.tech_stack,
            errors_seen=self.state.errors_seen,
            files_modified=self.state.files_modified,
            decisions=self.state.decisions,
        )

    def clear(self) -> None:
        self.messages.clear()
        self._pinned_files.clear()
        self.state = SessionState()

    def _update_state_from_message(self, msg: Message) -> None:
        content = msg.content
        # Extract file paths
        paths = re.findall(r'[\w/\.\-]+\.\w{1,10}', content)
        for p in paths[:3]:
            if p not in self.state.files_read and msg.role == MessageRole.USER:
                self.state.files_read.append(p)
            if p not in self.state.files_modified and msg.role == MessageRole.ASSISTANT:
                self.state.files_modified.append(p)
        # Extract errors
        error_matches = re.findall(
            r'(?:Error|Exception|FAILED)[:\s]+([^\n]{10,100})', content
        )
        for err in error_matches[:2]:
            if err not in self.state.errors_seen:
                self.state.errors_seen.append(err)

        self.persist_to_project_memory()

