"""Chat, plan, and goal interactive CLI commands."""

from __future__ import annotations

import asyncio
from typing import Optional
import typer
from rich.console import Console

from context_manager.cli.session.flashlight_helper import _SMALL_CTX

console = Console()


def register_chat_commands(app: typer.Typer, session_cls, harness_cls=None) -> None:
    """Register chat, plan, and goal commands with the Typer app."""

    @app.command()
    def chat(
        url: str = typer.Option("http://localhost:1234/v1", "--url", "-u", help="LM Studio API URL"),
        model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name"),
        image: Optional[str] = typer.Option(
            None, "--image", "-i", help="Initial image file path to inspect (PNG, JPG, WEBP, etc.)"
        ),
        max_tokens: int = typer.Option(
            4096,
            "--max-tokens",
            "-t",
            help="Context window size. Match your model's actual n_ctx in LM Studio (default: 4096).",
            min=100,
            max=200000,
        ),
        repeat_penalty: Optional[float] = typer.Option(
            None,
            "--repeat-penalty",
            "--repetition-penalty",
            "--rep",
            help="Repetition penalty for generation (e.g. 1.05). Prevents repeating text or code loops.",
        ),
        no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming"),
        project: Optional[str] = typer.Option(
            None, "--project", "-p", help="Project directory (default: CWD)"
        ),
        mode: str = typer.Option(
            "chat",
            "--mode",
            "-mode",
            help="Execution mode: 'chat' (lightweight Q&A), 'plan' (brainstorm & plan), or 'goal' (task tracking & harness)",
        ),
    ):
        """Start an interactive chat session with context management and flashlight."""
        console.print("[bold cyan]Context Manager CLI — Torchlight[/bold cyan]")
        console.print(f"Connecting to: {url}")
        console.print(f"[dim]Context window: {max_tokens:,} tokens[/dim]")

        m_str = (mode or "chat").lower().strip()
        if m_str == "goal":
            console.print(
                "[bold green]🎯 Mode: Goal Mode[/bold green] [dim](Autonomous task tracking in .torchlight/tasks.md)[/dim]"
            )
        elif m_str == "plan":
            console.print(
                "[bold cyan]📋 Mode: Plan Mode[/bold cyan] [dim](Brainstorm architecture & write/update implementation_plan.md)[/dim]"
            )
        else:
            console.print(
                "[bold cyan]💬 Mode: Chat Mode[/bold cyan] [dim](Lightweight Q&A & ad-hoc code edits, no task files)[/dim]"
            )

        if max_tokens <= _SMALL_CTX:
            console.print(
                f"[yellow]Small context mode ({max_tokens} tok): "
                f"skills prompts skipped, beam=1×50 lines[/yellow]"
            )

        session = session_cls(
            base_url=url,
            model=model,
            max_tokens=max_tokens,
            stream=not no_stream,
            project_dir=project,
            mode=m_str,
            repeat_penalty=repeat_penalty,
        )
        asyncio.run(session.start())

    @app.command()
    def plan(
        title: Optional[str] = typer.Argument(None, help="Target feature or task description to plan"),
        url: str = typer.Option("http://localhost:1234/v1", "--url", "-u", help="LM Studio API URL"),
        model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name"),
        max_tokens: int = typer.Option(4096, "--max-tokens", "-t", help="Context window size"),
        repeat_penalty: Optional[float] = typer.Option(
            None,
            "--repeat-penalty",
            "--repetition-penalty",
            "--rep",
            help="Repetition penalty for generation (e.g. 1.05).",
        ),
        project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    ):
        """Start a planning session to brainstorm and write/update implementation_plan.md."""
        if title:
            console.print(f"[bold cyan]📋 Starting Plan Mode:[/bold cyan] {title}")
        else:
            console.print(
                "[bold cyan]📋 Starting Plan Mode[/bold cyan] [dim](Brainstorm architecture & write/update implementation_plan.md)[/dim]"
            )
        session = session_cls(
            base_url=url,
            model=model,
            max_tokens=max_tokens,
            stream=True,
            project_dir=project,
            mode="plan",
            repeat_penalty=repeat_penalty,
        )
        asyncio.run(session.start())

    @app.command()
    def goal(
        title: str = typer.Argument(..., help="Goal title or target feature description"),
        url: str = typer.Option("http://localhost:1234/v1", "--url", "-u", help="LM Studio API URL"),
        model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name"),
        max_tokens: int = typer.Option(4096, "--max-tokens", "-t", help="Context window size"),
        repeat_penalty: Optional[float] = typer.Option(
            None,
            "--repeat-penalty",
            "--repetition-penalty",
            "--rep",
            help="Repetition penalty for generation (e.g. 1.05).",
        ),
        project: Optional[str] = typer.Option(None, "--project", "-p", help="Project directory"),
    ):
        """Start an autonomous goal execution session driven by .torchlight task tracking."""
        console.print(f"[bold green]🎯 Starting Goal Mode:[/bold green] {title}")
        session = session_cls(
            base_url=url,
            model=model,
            max_tokens=max_tokens,
            stream=True,
            project_dir=project,
            mode="goal",
            repeat_penalty=repeat_penalty,
        )
        if harness_cls:
            harness = harness_cls(project_root=session.project_path, memory=session.memory)
            harness.ensure_goal_spec_initialized(title=title, description=title)
            console.print("[dim]✓ Goal spec initialized in .torchlight/goal_spec.json & tasks.md[/dim]")
        asyncio.run(session.start())
