"""Progressive compression and inter-task compaction mixin for TieredMemory."""

from __future__ import annotations

from typing import Optional, Callable

from .models import (
    Message,
    MessageRole,
    MemoryEvent,
    MemoryEventType,
)


class CompactionMixin:
    """Mixin providing progressive history compression and task boundary compaction."""

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
