import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "context-manager-cli" / "src"))

import pytest
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text
from rich.console import Console
from context_manager.cli.dashboard import ActionEntry, ActionTracker


def test_escape_raw_brackets_and_json():
    raw_text = '[ERROR] Failed on line [10:20]: {"tool_name": "WRITE_FILE", "args": [1, 2, 3]}'
    escaped = escape(raw_text)
    # Ensure Rich Panel renders escaped text without StyleSyntaxError
    console = Console(quiet=True)
    panel = Panel(escaped, title="Test")
    console.print(panel)


def test_action_entry_markup_safety():
    entry = ActionEntry("read_file", "Reading file [main.py] with range [1:50]")
    line = entry.render(is_current=True)
    assert isinstance(line, Text)
    assert "[main.py]" in line.plain


def test_action_tracker_print_action_safety():
    console = Console(quiet=True)
    tracker = ActionTracker(console)
    # Should execute without throwing StyleSyntaxError on unescaped brackets
    tracker.print_action("edit_file", "Editing file [core/memory/manager.py] with replacement [1, 2]")


def test_tui_markup_escaping_safety():
    console = Console(quiet=True)
    # Test model name with GGUF quantization brackets
    model_name = "llama-3.2-1b-instruct[q4_k_m]"
    panel1 = Panel(f"[bold cyan]{escape(model_name)}[/]", title="Model Test")
    console.print(panel1)

    # Test error message with truncation tag
    raw_err = "[context_length_exceeded] error in model evaluation"
    if len(raw_err) > 20:
        raw_err = raw_err[:20] + "... [truncated]"
    err_str = escape(raw_err)
    panel2 = Panel(f"[bold red]Error:[/] {err_str}", title="Error Test")
    console.print(panel2)

    # Test path with brackets
    path_str = "/Users/user/project[v1]/src"
    panel3 = Panel(f"Selected: [bold green]{escape(path_str)}[/]", title="Path Test")
    console.print(panel3)

