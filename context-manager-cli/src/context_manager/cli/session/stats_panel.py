"""Stats panel and context breakdown display for CLI session."""

from __future__ import annotations

import time
from rich.console import Console
from rich.panel import Panel

console = Console()


class StatsPanelMixin:
    """Provides Live Stats and per-section context breakdown formatting for StreamingChatSession."""

    def _create_stats_panel(
        self,
        response_preview: str = "",
        tokens_per_sec: float = 0,
    ) -> Panel:
        snapshot = self.memory.get_snapshot()
        ctx_tokens = snapshot.token_count + self._response_tokens
        usage_pct = (ctx_tokens / self.max_tokens) * 100 if self.max_tokens > 0 else 0
        bar_color = "green" if usage_pct < 50 else ("yellow" if usage_pct < 70 else "red")
        fill = int(usage_pct / 2)
        bar = "█" * fill + "░" * (50 - fill)
        preview = response_preview[:40] + "..." if len(response_preview) > 40 else response_preview

        lock_str = " 🔒" if self._params_locked else ""
        content = (
            f"[cyan]Context[/cyan]: {ctx_tokens:,}/{self.max_tokens:,} "
            f"tokens ({usage_pct:.0f}%)\n"
            f"[{bar_color}]{bar}[/{bar_color}]\n"
            f"[cyan]Messages[/cyan]: {snapshot.message_count} | "
            f"[cyan]Response[/cyan]: {self._response_tokens} tokens\n"
            f"[cyan]Phase[/cyan]: {self._current_phase}{lock_str}  "
            f"[dim]{self._params.describe()}[/dim]"
        )
        if tokens_per_sec > 0:
            content += f" | [cyan]Speed[/cyan]: {tokens_per_sec:.1f} tok/s"
        if preview:
            from rich.markup import escape

            content += f"\n[dim]Streaming:[/dim] {escape(preview)}"

        # Per-section context breakdown
        breakdown = self._context_section_breakdown(
            ctx_tokens=ctx_tokens,
            response_tokens=self._response_tokens,
        )
        if breakdown:
            content += f"\n\n[dim]─ Context Breakdown ─────────────────[/dim]\n{breakdown}"

        return Panel(content, title="[bold]Live Stats[/bold]", border_style="blue")

    def _context_section_breakdown(self, ctx_tokens: int = 0, response_tokens: int = 0) -> str:
        """Return a compact Rich markup string showing per-section token estimates.

        Sections: System Prompt, Scratchpad/L0, Flashlight Beam, Chat History, Pins, Streaming.
        Results are cached for 2.0s to avoid redundant formatting during streaming.
        """
        ctx_max = self.max_tokens
        if ctx_max <= 0:
            return ""

        # ── 2.0s TTL cache — only recompute static sections once per 2 seconds ──
        now = time.monotonic()
        cached_static = getattr(self, "_ctx_breakdown_cache", None)
        cached_ts = getattr(self, "_ctx_breakdown_ts", 0.0)
        SPARK_W = 10
        if cached_static is not None and (now - cached_ts) < 2.0:
            # Still in cache window: only update streaming row (cheap, no I/O)
            if response_tokens > 0:
                pct = min(100.0, (response_tokens / ctx_max) * 100)
                filled = min(SPARK_W, round((pct / 100.0) * SPARK_W))
                spark = "\u25aa" * filled + "\u00b7" * (SPARK_W - filled)
                stream_row = (
                    f"[dim]{'Streaming':<11}[/dim]"
                    f"[yellow]{spark}[/yellow] "
                    f"[bold]{response_tokens:>5,}[/bold] "
                    f"[dim]{pct:>4.1f}%[/dim]"
                )
                return cached_static + "\n" + stream_row
            return cached_static

        # ── Full recompute (at most every 2s, O(1) in memory) ──
        # 1. System prompt estimate per phase
        _SYSTEM_SIZES = {"chat": 900, "plan": 1100, "code": 1050, "goal": 1000, "troubleshoot": 950}
        system_tok = _SYSTEM_SIZES.get(self._current_phase, 1000) + 300  # +300 tool syntax

        # 2. Scratchpad/L0 — fast estimate from memory state
        scratchpad_tok = getattr(self.memory, "_estimate_l0_tokens", lambda: 150)()
        if scratchpad_tok == 0:
            scratchpad_tok = 50

        # 3. Flashlight beam — heuristic
        beam_tok = 600 if ctx_max >= 8000 else 250

        # 4. Chat history — committed message tokens in memory
        chat_tok = getattr(self.memory, "_cached_msg_tokens", 0)

        # 5. Pinned files
        pinned_tok = getattr(self.memory, "_cached_pinned_tokens", 0)

        total_static = system_tok + scratchpad_tok + beam_tok + chat_tok + pinned_tok
        if total_static <= 0:
            return ""

        def _row(label: str, tok: int, color: str) -> str:
            pct = min(100.0, (tok / ctx_max) * 100)
            filled = min(SPARK_W, round((pct / 100.0) * SPARK_W))
            spark = "\u25aa" * filled + "\u00b7" * (SPARK_W - filled)
            return (
                f"[dim]{label:<11}[/dim]"
                f"[{color}]{spark}[/{color}] "
                f"[bold]{tok:>5,}[/bold] "
                f"[dim]{pct:>4.1f}%[/dim]"
            )

        row_list = [
            _row("System",     system_tok,     "blue"),
            _row("Scratchpad",  scratchpad_tok, "cyan"),
            _row("Beam",        beam_tok,       "bright_cyan"),
            _row("Chat",        chat_tok,       "green"),
        ]
        if pinned_tok > 0:
            row_list.append(_row("Pins", pinned_tok, "magenta"))

        static_rows = "\n".join(row_list)

        # Cache the static rows (no streaming row) for 2s
        self._ctx_breakdown_cache = static_rows  # type: ignore[attr-defined]
        self._ctx_breakdown_ts = now              # type: ignore[attr-defined]

        if response_tokens > 0:
            pct = min(100.0, (response_tokens / ctx_max) * 100)
            filled = min(SPARK_W, round((pct / 100.0) * SPARK_W))
            spark = "\u25aa" * filled + "\u00b7" * (SPARK_W - filled)
            stream_row = (
                f"[dim]{'Streaming':<11}[/dim]"
                f"[yellow]{spark}[/yellow] "
                f"[bold]{response_tokens:>5,}[/bold] "
                f"[dim]{pct:>4.1f}%[/dim]"
            )
            return static_rows + "\n" + stream_row
        return static_rows
