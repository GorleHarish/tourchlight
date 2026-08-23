import sys
import argparse
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from rich.rule import Rule
from rich.live import Live
from rich.spinner import Spinner

from rlm_optimized.config import MODEL_NAME, MAX_RECURSION_DEPTH, PROVIDER
from rlm_optimized.rlm_engine import RLMEngine, Step

DEPTH_COLORS = ["cyan", "yellow", "magenta", "green", "red"]
DEPTH_ICONS = ["🔵", "🟡", "🟣", "🟢", "🔴"]

console = Console()

def get_depth_style(depth: int) -> tuple:
    idx = min(depth, len(DEPTH_COLORS) - 1)
    return DEPTH_COLORS[idx], DEPTH_ICONS[idx]

def display_step(step: Step):
    color, icon = get_depth_style(step.depth)
    indent = "  " * step.depth

    action_labels = {
        "code": "⚡ Code Execution",
        "sub_query": "🔄 Sub-Query (Recursive)",
        "final_answer": "✅ Final Answer",
        "thinking": "💭 Thinking",
    }
    label = action_labels.get(step.action, step.action)
    header = f"{icon} Depth {step.depth} │ Step {step.step_number} │ {label}"

    if step.thinking and step.thinking != "(forced by iteration limit)":
        thinking_panel = Panel(
            Markdown(step.thinking),
            title=f"{indent}💭 Reasoning",
            border_style="dim",
            padding=(0, 1),
        )
        console.print(thinking_panel)

    if step.action == "code":
        code_panel = Panel(
            Syntax(step.content, "python", theme="monokai", line_numbers=True),
            title=f"{indent}{header}",
            border_style=color,
            padding=(0, 1),
        )
        console.print(code_panel)

        if step.result:
            result_style = "red" if step.result.startswith("ERROR") else "green"
            result_panel = Panel(
                Text(step.result),
                title=f"{indent}📤 Output",
                border_style=result_style,
                padding=(0, 1),
            )
            console.print(result_panel)

    elif step.action == "sub_query":
        query_panel = Panel(
            Markdown(step.content),
            title=f"{indent}{header}",
            border_style=color,
            padding=(0, 1),
        )
        console.print(query_panel)

        if step.result and step.result != "DEPTH LIMIT REACHED":
            result_panel = Panel(
                Markdown(step.result),
                title=f"{indent}📥 Sub-Query Result",
                border_style="dim green",
                padding=(0, 1),
            )
            console.print(result_panel)
        elif step.result == "DEPTH LIMIT REACHED":
            console.print(f"{indent}[bold red]⚠ Maximum recursion depth reached[/]")

    elif step.action == "final_answer":
        answer_panel = Panel(
            Markdown(step.content),
            title=f"{indent}{header}",
            border_style="bold green",
            padding=(1, 2),
        )
        console.print(answer_panel)

    elif step.action == "rejected_final_answer":
        rej_panel = Panel(
            Markdown(step.result or step.content),
            title=f"{indent}🔄 Auto-Advancing to Next Task (Continuing Execution)",
            border_style="cyan",
            padding=(1, 2),
        )
        console.print(rej_panel)

    elif step.action == "thinking":
        console.print(f"{indent}[dim]{step.result}[/]")

    console.print()

def print_banner():
    banner = """
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   ██████╗ ██╗     ███╗   ███╗                        ║
║   ██╔══██╗██║     ████╗ ████║                        ║
║   ██████╔╝██║     ██╔████╔██║                        ║
║   ██╔══██╗██║     ██║╚██╔╝██║                        ║
║   ██║  ██║███████╗██║ ╚═╝ ██║                        ║
║   ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝                        ║
║                                                      ║
║   Recursive Language Model — Local + Cloud           ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold cyan")

def print_help(model_name: str):
    help_text = """
[bold]Commands:[/]
  [cyan]quit[/]         Exit the RLM
  [cyan]reset[/]        Clear the sandbox state
  [cyan]depth <N>[/]    Set max recursion depth (current: {depth})
  [cyan]help[/]         Show this help message
  [cyan]status[/]       Show current configuration
 
[bold]Usage:[/]
  Just type a question or task and press Enter.
  The RLM will recursively reason through it.
"""
    console.print(help_text.format(depth=MAX_RECURSION_DEPTH))

def create_client(args):
    provider = args.provider

    if provider == "ollama":
        from rlm_optimized.ollama_client import OllamaClient
        model = args.model if args.model != MODEL_NAME else MODEL_NAME
        client = OllamaClient(model=model)
        return client, model, "ollama (local)"
    elif provider == "llama-cpp":
        from rlm_optimized.llamacpp_client import LlamaCppClient
        model = args.model if args.model != MODEL_NAME else MODEL_NAME
        client = LlamaCppClient(model=model)
        return client, model, "llama.cpp (local optimized)"
    else:
        from rlm_optimized.cloud_client import CloudClient
        client = CloudClient(
            provider=provider if provider != "cloud" else None,
            model=args.model if args.model != MODEL_NAME else None,
            base_url=args.base_url,
            api_key=args.api_key,
        )
        return client, client.model, f"{provider} (cloud)"

def run_interactive(engine: RLMEngine, max_depth: int, model_name: str, provider_name: str):
    print_banner()
    console.print(f"  Provider: [bold]{provider_name}[/]")
    console.print(f"  Model: [bold]{model_name}[/]")
    console.print(f"  Max Depth: [bold]{max_depth}[/]")
    console.print(f"  Type [cyan]help[/] for commands\n")

    if not engine.client.is_running():
        if "ollama" in provider_name:
            console.print("[bold red]✗ Ollama is not running![/]\n  Start it with: [cyan]open -a Ollama[/]\n")
        elif "llama.cpp" in provider_name:
            console.print("[bold red]✗ llama-server is not running![/]\n  Start it with: [cyan]. /rlm_optimized/start_optimized_local.sh[/]\n")
        else:
            console.print(f"[bold red]✗ Cannot connect to {provider_name}![/]\n  Check API key and network.\n")
        return

    if not engine.client.is_model_available():
        if "ollama" in provider_name:
            console.print(f"[bold red]✗ Model '{model_name}' not found![/]\n  Pull it with: [cyan]ollama pull {model_name}[/]\n")
        else:
            console.print(f"[bold red]✗ Model '{model_name}' not available![/]\n  Check model name for: {provider_name}\n")
        return

    console.print(f"[bold green]✓ Connected to {provider_name}[/]\n")

    while True:
        try:
            console.print(Rule(style="dim"))
            user_input = console.input("[bold cyan]RLM ❯ [/]").strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                console.print("\n[dim]Goodbye! 👋[/]\n")
                break
            elif user_input.lower() == "reset":
                engine.reset()
                console.print("[green]✓ Sandbox state cleared[/]")
                continue
            elif user_input.lower().startswith("depth "):
                try:
                    new_depth = int(user_input.split()[1])
                    if 1 <= new_depth <= 10:
                        engine.max_depth = new_depth
                        console.print(f"[green]✓ Max depth set to {new_depth}[/]")
                    else:
                        console.print("[red]Depth must be between 1 and 10[/]")
                except (ValueError, IndexError):
                    console.print("[red]Usage: depth <number>[/]")
                continue
            elif user_input.lower() == "help":
                print_help(model_name)
                continue
            elif user_input.lower() == "status":
                console.print(f"  Provider: [bold]{provider_name}[/]")
                console.print(f"  Model: [bold]{model_name}[/]")
                console.print(f"  Max Depth: [bold]{engine.max_depth}[/]")
                variables = engine.sandbox.get_variables()
                if variables:
                    console.print(f"  Sandbox Variables: [bold]{len(variables)}[/]")
                    for k, v in list(variables.items())[:5]:
                        console.print(f"    {k} = {v[:80]}")
                continue

            console.print()
            console.print(Panel(user_input, title="📝 Task", border_style="bold blue", padding=(0, 1)))
            console.print()

            with console.status("[bold cyan]Thinking...[/]", spinner="dots"):
                result = engine.solve(user_input)

            console.print(Rule(characters="─", style="dim"))
            console.print(f"  [dim]Completed in {result.total_llm_calls} LLM call(s), {len(result.steps)} step(s)[/]")

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted. Type 'quit' to exit.[/]")
            continue
        except Exception as e:
            console.print(f"\n[bold red]Error:[/] {e}")

def run_single_task(engine: RLMEngine, task: str):
    console.print(Panel(task, title="📝 Task", border_style="bold blue", padding=(0, 1)))
    console.print()
    result = engine.solve(task)
    console.print(Rule(characters="─", style="dim"))
    console.print(f"  [dim]Completed in {result.total_llm_calls} LLM call(s), {len(result.steps)} step(s)[/]")

def main():
    parser = argparse.ArgumentParser(description="RLM — Recursive Language Model POC (Local + Cloud)")
    parser.add_argument("--task", type=str, default=None, help="Run a single task instead of interactive mode")
    parser.add_argument("--depth", type=int, default=MAX_RECURSION_DEPTH, help="Maximum recursion depth")
    parser.add_argument("--model", type=str, default=MODEL_NAME, help="Model to use")
    parser.add_argument("--provider", type=str, default=PROVIDER, choices=["ollama", "groq", "together", "openrouter", "openai", "cloud", "llama-cpp"], help="LLM provider")
    parser.add_argument("--base-url", type=str, default=None, help="Custom API base URL")
    parser.add_argument("--api-key", type=str, default=None, help="API key")

    args = parser.parse_args()

    try:
        client, model_name, provider_name = create_client(args)
    except Exception as e:
        console.print(f"[bold red]Setup error:[/] {e}")
        sys.exit(1)

    engine = RLMEngine(client=client, on_step=display_step, max_depth=args.depth)

    if args.task:
        run_single_task(engine, args.task)
    else:
        run_interactive(engine, args.depth, model_name, provider_name)

if __name__ == "__main__":
    main()
