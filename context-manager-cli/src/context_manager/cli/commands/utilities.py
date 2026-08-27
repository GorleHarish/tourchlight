"""Utility CLI commands: compress_file, count_tokens, and sessions."""

from __future__ import annotations

from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from context_manager.compression.compactor import CompressionConfig, VerbatimCompactor
from core.memory.token_counter import get_token_counter

console = Console()


def register_utility_commands(app: typer.Typer) -> None:
    """Register utility commands with the Typer app."""

    @app.command()
    def compress_file(
        input_file: str = typer.Argument(..., help="File to compress"),
        output_file: Optional[str] = typer.Option(None, "--output", "-o"),
        aggressive: bool = typer.Option(False, "--aggressive", "-a"),
    ):
        """Compress a file using verbatim compaction."""
        try:
            with open(input_file, "r") as f:
                content = f.read()
            config = CompressionConfig(aggressive_mode=aggressive)
            compactor = VerbatimCompactor(config)
            compressed = compactor.compress(content)
            if output_file:
                with open(output_file, "w") as f:
                    f.write(compressed)
                ratio = len(content) / max(len(compressed), 1)
                console.print(f"[green]✓[/green] {input_file} -> {output_file}")
                console.print(
                    f"Original: {len(content):,} | Compressed: {len(compressed):,} | Ratio: {ratio:.2f}x"
                )
            else:
                print(compressed)
        except FileNotFoundError:
            console.print(f"[red]Error:[/red] File not found: {input_file}")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")

    @app.command()
    def count_tokens(text: str = typer.Argument(..., help="Text to count tokens")):
        """Count tokens in text."""
        counter = get_token_counter()
        count = counter.count(text)
        console.print(f"[cyan]Tokens:[/cyan] {count:,}")
        console.print(f"[cyan]Chars:[/cyan] {len(text):,}")
        console.print(f"[cyan]Ratio:[/cyan] {len(text) / max(count, 1):.2f} chars/token")

    @app.command()
    def sessions(
        action: str = typer.Argument("list", help="Action: list, show, delete"),
        name: Optional[str] = typer.Option(None, "--name", "-n"),
    ):
        """Manage saved sessions."""
        from context_manager.memory.persistence import SessionPersistence

        persistence = SessionPersistence()

        if action == "list":
            sessions_list = persistence.list_sessions()
            if not sessions_list:
                console.print("[yellow]No saved sessions[/yellow]")
                return
            table = Table(title="Saved Sessions", show_header=True)
            table.add_column("Name", style="cyan")
            table.add_column("Created", style="white")
            table.add_column("Messages", style="green")
            table.add_column("Tokens", style="yellow")
            for s in sessions_list:
                table.add_row(
                    s["name"],
                    s["created"][:19] if s["created"] else "N/A",
                    str(s["message_count"]),
                    f"{s['total_tokens']:,}",
                )
            console.print(table)

        elif action == "show" and name:
            from context_manager.memory.manager import TieredMemory

            memory = TieredMemory(tokenizer=get_token_counter())
            if persistence.load_session(name, memory):
                console.print(f"[green]Loaded:[/green] {name}")
                console.print(f"Messages: {memory.message_count}")
                console.print(f"Tokens: {memory.total_tokens:,}")
            else:
                console.print(f"[red]Not found:[/red] {name}")

        elif action == "delete" and name:
            if persistence.delete_session(name):
                console.print(f"[green]Deleted:[/green] {name}")
            else:
                console.print(f"[red]Not found:[/red] {name}")
        else:
            console.print("[yellow]Usage: sessions [list|show|delete] [--name NAME][/yellow]")
