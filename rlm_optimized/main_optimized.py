import sys
import os
import argparse
import asyncio
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from rich.rule import Rule

from rlm_optimized.config import MODEL_NAME, MAX_RECURSION_DEPTH, PROVIDER
from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized, Step
from core.tools.classification import AUTO, CONFIRM, REVIEW

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
        "tool": "🔧 Tool Execution",
        "sub_queries": "🔄 Sub-Queries (Parallel)",
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

    if step.action == "tool":
        tool_label = step.tool_name or "TOOL"
        args_str = ""
        if step.tool_args:
            import json as _json
            args_str = _json.dumps(step.tool_args, indent=2)
        tool_panel = Panel(
            Text(f"{tool_label}\n{args_str}"),
            title=f"{indent}🔧 {tool_label}",
            border_style="bright_blue",
            padding=(0, 1),
        )
        console.print(tool_panel)

        if step.result:
            is_denied = "denied" in (step.result or "").lower()
            is_error = step.result.startswith("Error") or step.result.startswith("❌")
            if is_denied:
                result_style = "yellow"
                icon = "⚠"
            elif is_error:
                result_style = "red"
                icon = "❌"
            else:
                result_style = "green"
                icon = "📤"
            result_panel = Panel(
                Text(step.result),
                title=f"{indent}{icon} Tool Output",
                border_style=result_style,
                padding=(0, 1),
            )
            console.print(result_panel)

    elif step.action == "code":
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

    elif step.action == "sub_queries":
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
                title=f"{indent}📥 Sub-Queries Parallel Results",
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
            title=f"{indent}⚠️ Premature Final Answer Intercepted (Continuing Execution)",
            border_style="yellow",
            padding=(1, 2),
        )
        console.print(rej_panel)

    elif step.action == "thinking":
        console.print(f"{indent}[dim]{step.result}[/]")

    console.print()

def approval_prompt(tool_name: str, risk: str, args: dict) -> bool:
    """Interactive approval for CONFIRM/REVIEW tier tools."""
    import json as _json
    risk_colors = {CONFIRM: "yellow", REVIEW: "bold red"}
    risk_labels = {CONFIRM: "⚠ CONFIRM", REVIEW: "🛑 REVIEW"}
    style = risk_colors.get(risk, "yellow")
    label = risk_labels.get(risk, risk.upper())

    console.print()
    console.print(Panel(
        Text(f"{tool_name}\n{_json.dumps(args, indent=2)}"),
        title=f"{label} — Approve this tool call?",
        border_style=style,
        padding=(0, 1),
    ))
    try:
        answer = console.input(f"[{style}]  Allow? [Y/n]: [/]").strip().lower()
        return answer in ("", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ████████╗ ██████╗ ██████╗  ██████╗██╗  ██╗██╗     ██╗     ║
║      ██╔══╝██╔═══██╗██╔══██╗██╔════╝██║  ██║██║     ██║     ║
║      ██║   ██║   ██║██████╔╝██║     ███████║██║     ██║     ║
║      ██║   ██║   ██║██╔══██╗██║     ██╔══██║██║     ██║     ║
║      ██║   ╚██████╔╝██║  ██║╚██████╗██║  ██║███████╗██║     ║
║      ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝     ║
║                                                              ║
║   Torchlight Agent — Full Coding Agent TUI                   ║
║   Tools: READ_FILE · WRITE_FILE · GREP · RUN_COMMAND         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold cyan")

def create_client(args):
    provider = args.provider

    if provider == "llama-cpp":
        from rlm_optimized.llamacpp_client import LlamaCppClient
        model = args.model if args.model != MODEL_NAME else MODEL_NAME
        client = LlamaCppClient(model=model)
        return client, model, "llama.cpp (local optimized with GBNF)"
    elif provider == "ollama":
        from rlm_optimized.ollama_client import OllamaClient
        model = args.model if args.model != MODEL_NAME else MODEL_NAME
        client = OllamaClient(model=model)
        return client, model, "ollama (local)"
    else:
        from rlm_optimized.cloud_client import CloudClient
        client = CloudClient(
            provider=provider if provider != "cloud" else None,
            model=args.model if args.model != MODEL_NAME else None,
            base_url=args.base_url,
            api_key=args.api_key,
        )
        return client, client.model, f"{provider} (cloud)"

async def run_interactive(engine: RLMEngineOptimized, max_depth: int, model_name: str, provider_name: str):
    print_banner()
    console.print(f"  Provider: [bold]{provider_name}[/]")
    console.print(f"  Model: [bold]{model_name}[/]")
    console.print(f"  Max Depth: [bold]{max_depth}[/]")
    console.print(f"  Project Root: [bold]{engine.project_root}[/]")
    console.print(f"  Tools: [dim]READ_FILE, WRITE_FILE, LIST_DIR, GREP, RUN_COMMAND[/]")
    console.print()

    if not engine.client.is_running():
        console.print(f"[bold red]✗ Cannot connect to {provider_name}![/]\n  Verify service is running.\n")
        return

    console.print(f"[bold green]✓ Connected to {provider_name}[/]\n")

    while True:
        try:
            console.print(Rule(style="dim"))
            
            # Since console.input blocks, run it in an executor to keep asyncio loop healthy
            loop = asyncio.get_running_loop()
            user_input = await loop.run_in_executor(None, lambda: console.input("[bold cyan]RLM ❯ [/]").strip())

            if not user_input:
                continue

            if user_input.lower() == "quit":
                console.print("\n[dim]Goodbye! 👋[/]\n")
                break
            elif user_input.lower() == "reset":
                engine.sandbox.reset()
                console.print("[green]✓ Sandbox state cleared[/]")
                continue

            console.print()
            console.print(Panel(user_input, title="📝 Task", border_style="bold blue", padding=(0, 1)))
            console.print()

            result = await engine.solve_async(user_input)

            console.print(Rule(characters="─", style="dim"))
            console.print(f"  [dim]Completed in {result.total_llm_calls} LLM call(s), {len(result.steps)} step(s)[/]")

        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted. Type 'quit' to exit.[/]")
            continue
        except Exception as e:
            console.print(f"\n[bold red]Error:[/] {e}")

async def run_single_task(engine: RLMEngineOptimized, task: str):
    console.print(Panel(task, title="📝 Task", border_style="bold blue", padding=(0, 1)))
    console.print()
    result = await engine.solve_async(task)
    console.print(Rule(characters="─", style="dim"))
    console.print(f"  [dim]Completed in {result.total_llm_calls} LLM call(s), {len(result.steps)} step(s)[/]")

async def amain():
    parser = argparse.ArgumentParser(description="RLM Optimized — Async DAG (Local + Cloud)")
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

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    engine = RLMEngineOptimized(
        client=client,
        on_step=display_step,
        max_depth=args.depth,
        project_root=project_root,
        approval_fn=approval_prompt,
    )

    if args.task:
        await run_single_task(engine, args.task)
    else:
        await run_interactive(engine, args.depth, model_name, provider_name)

def main():
    asyncio.run(amain())

if __name__ == "__main__":
    main()
