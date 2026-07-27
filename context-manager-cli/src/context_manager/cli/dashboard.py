from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.columns import Columns
from datetime import datetime
from typing import Optional
import time
import threading


class ContextDashboard:
    def __init__(self):
        self.console = Console()
        self._live: Optional[Live] = None

    def render_status(
        self,
        tokens: int,
        max_tokens: int,
        messages: int,
        compression_ratio: float,
    ) -> Layout:
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )

        usage_pct = (tokens / max_tokens) * 100 if max_tokens > 0 else 0
        if usage_pct < 50:
            status_color = "green"
        elif usage_pct < 70:
            status_color = "yellow"
        else:
            status_color = "red"

        layout["header"].update(
            Panel(
                f"[bold]Context Manager CLI[/bold] | "
                f"[{status_color}]Tokens: {tokens:,}/{max_tokens:,} ({usage_pct:.0f}%)[/{status_color}] | "
                f"Messages: {messages}",
                style="blue",
            )
        )

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Context Tokens", f"{tokens:,}")
        table.add_row("Max Tokens", f"{max_tokens:,}")
        table.add_row("Usage", f"{usage_pct:.1f}%")
        table.add_row("Messages", str(messages))
        table.add_row("Compression", f"{compression_ratio:.1f}x")
        table.add_row("Status", self._get_status_text(usage_pct))

        layout["main"].update(Panel(table, title="Session Status"))
        layout["footer"].update(
            Panel(
                f"Press Ctrl+C to exit | /help for commands | {datetime.now().strftime('%H:%M:%S')}"
            )
        )

        return layout

    def _get_status_text(self, usage_pct: float) -> str:
        if usage_pct < 50:
            return "[green]Healthy[/green]"
        elif usage_pct < 70:
            return "[yellow]Monitoring[/yellow]"
        elif usage_pct < 85:
            return "[red]Compression Recommended[/red]"
        else:
            return "[bold red]Critical - Compress Now[/bold red]"

    def show_snapshot(self, snapshot) -> None:
        table = Table(title="Context Snapshot", show_header=False)
        table.add_column("Metric")
        table.add_column("Value")

        table.add_row("Message Count", str(snapshot.message_count))
        table.add_row("Token Count", f"{snapshot.token_count:,}")
        table.add_row("Compression Ratio", f"{snapshot.compression_ratio:.2f}x")
        table.add_row("Time", snapshot.timestamp.strftime("%H:%M:%S"))
        table.add_row("Oldest Message", f"{snapshot.oldest_message_age:.0f}s ago")

        self.console.print(table)

    def render_task_progress(self, summary: dict) -> Panel:
        """Render a Rich Panel displaying sub-agent goal progress and task status breakdown."""
        goal_title = summary.get("title") or "No Active Goal"
        goal_id = summary.get("goal_id") or "N/A"
        progress_pct = summary.get("progress_pct", 0.0)
        total = summary.get("total_tasks", 0)
        verified = summary.get("verified", 0)
        in_progress = summary.get("in_progress", 0)
        pending = summary.get("pending", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)

        # Build progress bar string e.g. [██████░░░░] 60%
        bar_width = 20
        filled = int(round((progress_pct / 100.0) * bar_width)) if total > 0 else 0
        filled = min(filled, bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Header metrics
        header_text = (
            f"[bold cyan]Goal:[/bold cyan] [bold]{goal_title}[/bold] (ID: {goal_id})\n"
            f"[bold yellow]Progress:[/bold yellow] [{bar}] [bold green]{progress_pct:.1f}%[/bold green] ({verified}/{total} verified)\n"
            f"[bold white]Breakdown:[/bold white] "
            f"[green]✓ Verified: {verified}[/green] | "
            f"[cyan]● Running: {in_progress}[/cyan] | "
            f"[yellow]⏳ Pending: {pending}[/yellow] | "
            f"[red]✗ Failed: {failed}[/red]"
        )
        if skipped > 0:
            header_text += f" | [dim]⏭ Skipped: {skipped}[/dim]"

        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Task ID", style="bold cyan", width=10)
        table.add_column("Description", style="white")
        table.add_column("Status", width=14)
        table.add_column("Attempts", style="dim", width=10)
        table.add_column("Target Files", style="dim cyan")

        tasks = summary.get("tasks", [])
        if not tasks:
            table.add_row("-", "[dim italic]No sub-agent tasks defined[/dim italic]", "-", "-", "-")
        else:
            for t in tasks:
                st = t.get("status", "pending")
                if st == "verified":
                    status_badge = "[bold green]✓ VERIFIED[/bold green]"
                elif st == "in_progress":
                    status_badge = "[bold cyan]● IN_PROGRESS[/bold cyan]"
                elif st == "failed":
                    status_badge = "[bold red]✗ FAILED[/bold red]"
                elif st == "skipped":
                    status_badge = "[dim]⏭ SKIPPED[/dim]"
                else:
                    status_badge = "[yellow]⏳ PENDING[/yellow]"

                attempts_str = f"{t.get('attempts', 0)}/{t.get('max_attempts', 3)}"
                files_str = ", ".join(t.get("target_files", [])) or "-"

                desc = t.get("description", "")
                failures = t.get("failure_reasons", [])
                if failures:
                    desc += f"\n  [dim red]└─ Error: {failures[-1]}[/dim red]"

                table.add_row(t.get("id", ""), desc, status_badge, attempts_str, files_str)

        from rich.console import Group as RichGroup
        content = RichGroup(
            Panel(header_text, style="blue", border_style="cyan"),
            table,
        )
        return Panel(content, title="🤖 Sub-Agent Task Execution & Telemetry", border_style="bright_cyan")

    def show_task_progress(self, summary: dict) -> None:
        """Print sub-agent task progress to the console."""
        self.console.print(self.render_task_progress(summary))

    def print_compression_summary(self, summary: str) -> None:
        self.console.print("\n[bold cyan]Compressed Context Summary:[/bold cyan]")
        self.console.print(Panel(summary, style="cyan"))

    def print_error(self, error: str) -> None:
        from rich.markup import escape
        self.console.print(f"[bold red]Error:[/bold red] {escape(error)}")

    def print_success(self, message: str) -> None:
        from rich.markup import escape
        self.console.print(f"[bold green]✓[/bold green] {escape(message)}")

    def print_warning(self, message: str) -> None:
        from rich.markup import escape
        self.console.print(f"[bold yellow]⚠[/bold yellow] {escape(message)}")

    def print_info(self, message: str) -> None:
        from rich.markup import escape
        self.console.print(f"[cyan]ℹ[/cyan] {escape(message)}")

    def print_critique_start(self, tool_name: Optional[str] = None) -> None:
        from rich.markup import escape
        label = f" for {escape(tool_name)}" if tool_name else ""
        self.console.print(f"[bold yellow]🔍 Critic Pass:[/bold yellow] Evaluating proposal{label}...")

    def print_refined(self, flaws: list[str], tool_name: Optional[str] = None) -> None:
        from rich.markup import escape
        target = f" ({escape(tool_name)})" if tool_name else ""
        escaped_flaws = [escape(f) for f in flaws]
        flaw_str = f" [dim](Fixed: {', '.join(escaped_flaws)})[/dim]" if flaws else ""
        self.console.print(f"[bold green]✨ Refined Proposal{target}[/bold green]{flaw_str}")


    def start_live(self, render_fn) -> None:
        self.stop_live()
        self._live = Live(render_fn(), console=self.console, refresh_per_second=4)
        self._live.start()

    def update_live(self, render_fn) -> None:
        if self._live:
            self._live.update(render_fn())

    def stop_live(self) -> None:
        if self._live:
            self._live.stop()
            self._live = None

    def print_response(self, response: str) -> None:
        self.console.print("\n[bold green]Assistant:[/bold green]")
        self.console.print(Panel(response, style="green"))

    def print_user_input(self, user_input: str) -> None:
        from rich.markup import escape
        self.console.print(f"\n[bold blue]You:[/bold blue] {escape(user_input)}")

    def spinner(self, text: str) -> Progress:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        )
        progress.add_task(text)
        return progress

    def action_tracker(self) -> "ActionTracker":
        """Return a new ActionTracker bound to this dashboard's console."""
        return ActionTracker(self.console)


# ── ActionTracker ─────────────────────────────────────────────────────────────

# Action icons — shown in the live panel, not content
_ACTION_ICONS = {
    "web_search":   "🔍",
    "web_fetch":    "🌐",
    "doc_search":   "📚",
    "web_verify":   "✔",
    "read_file":    "📖",
    "write_file":   "💾",
    "run_command":  "⚡",
    "save_memory":  "🧠",
    "compress":     "🗜",
    "flashlight":   "◉",
    "thinking":     "💭",
    "default":      "→",
}

_ACTION_COLORS = {
    "web_search":   "cyan",
    "web_fetch":    "blue",
    "doc_search":   "magenta",
    "web_verify":   "green",
    "read_file":    "white",
    "write_file":   "yellow",
    "run_command":  "orange3",
    "save_memory":  "bright_magenta",
    "compress":     "dim cyan",
    "flashlight":   "bright_cyan",
    "thinking":     "dim white",
    "default":      "white",
}


class ActionEntry:
    """A single recorded action with its status and elapsed time."""

    __slots__ = ("kind", "label", "status", "started_at", "ended_at")

    # status: "running" | "done" | "error"
    def __init__(self, kind: str, label: str):
        self.kind       = kind
        self.label      = label
        self.status     = "running"
        self.started_at = time.time()
        self.ended_at:  Optional[float] = None

    def finish(self, ok: bool = True) -> None:
        self.ended_at = time.time()
        self.status   = "done" if ok else "error"

    @property
    def elapsed_ms(self) -> int:
        end = self.ended_at or time.time()
        return int((end - self.started_at) * 1000)

    def render(self, is_current: bool = False) -> Text:
        icon  = _ACTION_ICONS.get(self.kind, _ACTION_ICONS["default"])
        color = _ACTION_COLORS.get(self.kind, _ACTION_COLORS["default"])

        if self.status == "running":
            status_mark = "[bold cyan]●[/bold cyan]"
            label_style = f"[bold {color}]"
        elif self.status == "done":
            status_mark = "[green]✓[/green]"
            label_style = f"[dim {color}]"
        else:
            status_mark = "[red]✗[/red]"
            label_style = "[dim red]"

        elapsed = f"[dim]{self.elapsed_ms}ms[/dim]" if self.ended_at else ""
        label   = self.label[:60] + "…" if len(self.label) > 60 else self.label
        from rich.markup import escape
        escaped_label = escape(label)

        line = Text.from_markup(
            f"  {status_mark} {icon}  {label_style}{escaped_label}[/]  {elapsed}"
        )
        return line


class ActionTracker:
    """
    Shows a live panel of what the agent is doing — actions only, no content.

    Mirrors the Claude interface pattern:
      ● 🔍  Searching "asyncio.gather python 3.11 syntax"
      ✓ 📚  Reading docs.python.org/3/library/asyncio-task.html   142ms
      ✓ ✔   Verifying: asyncio.gather(*coros, return_exceptions=…) 89ms
      ● ⚡  Running pytest tests/test_memory.py

    Usage:
        tracker = dashboard.action_tracker()
        with tracker:
            act = tracker.start("web_search", 'asyncio.gather python docs')
            result = do_the_search(...)
            act.finish(ok=True)

    Or as a context manager per action:
        with tracker.action("read_file", "memory/manager.py") as act:
            content = read(...)
    """

    HISTORY_LIMIT = 6   # how many completed actions to keep visible

    def __init__(self, console: Console):
        self._console  = console
        self._history:  list[ActionEntry] = []
        self._current:  Optional[ActionEntry] = None
        self._live:     Optional[Live] = None
        self._lock      = threading.Lock()

    # ── Context manager (wraps the whole agent turn) ──────────────────────────

    def __enter__(self) -> "ActionTracker":
        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=12,
            transient=True,       # erases the panel when we exit — clean handoff
        )
        self._live.__enter__()
        return self

    def __exit__(self, *args) -> None:
        if self._live:
            self._live.__exit__(*args)
            self._live = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, kind: str, label: str) -> ActionEntry:
        """Register a new running action and refresh the display."""
        entry = ActionEntry(kind, label)
        with self._lock:
            if self._current:
                # Auto-finish previous action if caller forgot
                self._current.finish(ok=True)
                self._history.append(self._current)
                self._history = self._history[-self.HISTORY_LIMIT:]
            self._current = entry
        self._refresh()
        return entry

    def finish(self, entry: ActionEntry, ok: bool = True) -> None:
        """Mark an action done and move it to history."""
        entry.finish(ok)
        with self._lock:
            if self._current is entry:
                self._current = None
            if entry not in self._history:
                self._history.append(entry)
                self._history = self._history[-self.HISTORY_LIMIT:]
        self._refresh()

    def print_action(self, kind: str, label: str) -> None:
        """
        Single-shot: print a completed action line without needing a Live
        context. Used outside the with-block for one-off status lines.
        """
        icon  = _ACTION_ICONS.get(kind, _ACTION_ICONS["default"])
        color = _ACTION_COLORS.get(kind, _ACTION_COLORS["default"])
        from rich.markup import escape
        escaped_label = escape(label)
        self._console.print(
            f"  [green]✓[/green] {icon}  [{color}]{escaped_label}[/{color}]"
        )

    def action(self, kind: str, label: str) -> "_ActionContext":
        """
        Per-action context manager:

            with tracker.action("read_file", "src/foo.py") as act:
                content = read_file("src/foo.py")
        """
        return _ActionContext(self, kind, label)

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render(self) -> Panel:
        lines: list[Text] = []

        with self._lock:
            history  = list(self._history)
            current  = self._current

        for entry in history:
            lines.append(entry.render(is_current=False))

        if current:
            lines.append(current.render(is_current=True))

        if not lines:
            lines.append(Text.from_markup("  [dim]Waiting for action...[/dim]"))

        from rich.console import Group as RichGroup
        content = RichGroup(*lines)
        return Panel(
            content,
            title="[bold]Torchlight[/bold]",
            subtitle="[dim]actions[/dim]",
            border_style="bright_cyan",
            padding=(0, 1),
        )

    def _refresh(self) -> None:
        if self._live:
            self._live.update(self._render())


class _ActionContext:
    """Context manager returned by ActionTracker.action()."""

    def __init__(self, tracker: ActionTracker, kind: str, label: str):
        self._tracker = tracker
        self._kind    = kind
        self._label   = label
        self._entry:  Optional[ActionEntry] = None

    def __enter__(self) -> ActionEntry:
        self._entry = self._tracker.start(self._kind, self._label)
        return self._entry

    def __exit__(self, exc_type, *args) -> None:
        if self._entry:
            self._tracker.finish(self._entry, ok=(exc_type is None))
