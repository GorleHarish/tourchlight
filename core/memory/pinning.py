"""Active file pinning and FIFO cache mixin for TieredMemory."""

from __future__ import annotations

from collections import deque
from typing import Optional

from .models import MemoryEvent, MemoryEventType


class FilePinningMixin:
    """Mixin providing active file slice pinning that survives compression."""

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
