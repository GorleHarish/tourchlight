"""Pure text-formatting helpers for the Torchlight TUI.

No engine / App state, no Textual dependency — importable and testable in
isolation. Rendered strings use Rich markup so they can be fed directly into
``Static`` widgets.
"""

import json
import os
import re

from rich.markup import escape


def build_plan_text(project_root: str, is_goal: bool = False) -> str:
    """Render the implementation plan / task graph as rich-markup text.

    Mirrors the historical ``TorchlightApp._build_plan_text`` output verbatim
    (bar widths, glyphs, and section labels are intentional).
    """
    plan_path = os.path.join(project_root, "implementation_plan.md")
    alt_tasks_path = os.path.join(project_root, ".torchlight", "tasks.md")
    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")

    target_file = None
    file_type = None

    if os.path.exists(plan_path):
        target_file = plan_path
        file_type = "markdown"
    elif os.path.exists(alt_tasks_path):
        target_file = alt_tasks_path
        file_type = "markdown"
    elif os.path.exists(alt_goal_path):
        target_file = alt_goal_path
        file_type = "json"

    mode_hdr = (
        "[bold bright_green]🎯 GOAL_MODE[/bold bright_green]"
        if is_goal
        else "[bold cyan]💬 CHAT_MODE[/bold cyan]"
    )

    tasks = []
    completed = 0
    total = 0
    seen: set[str] = set()

    def _norm(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().lower())

    if target_file and os.path.exists(target_file):
        try:
            if file_type == "json":
                with open(target_file, "r", encoding="utf-8") as f:
                    goal_data = json.load(f)
                raw_tasks = goal_data.get("tasks", [])
                for t in raw_tasks:
                    st = t.get("status", "pending")
                    desc_raw = str(t.get("description") or t.get("id") or "Task")
                    if _norm(desc_raw) in seen:
                        continue
                    seen.add(_norm(desc_raw))
                    desc = escape(desc_raw)
                    if st in ("verified", "completed"):
                        completed += 1
                        tasks.append(f"[bold green]☑ {desc}[/bold green]")
                    elif st == "in_progress":
                        tasks.append(f"[bold yellow]■ {desc} █[/bold yellow]")
                    else:
                        tasks.append(f"[dim]☐ {desc}[/dim]")
                total = len(tasks)
            else:
                with open(target_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                chk_regex = re.compile(
                    r"^(?:[-*+>]|\d+[\.\)])?\s*\[([ xX/\-v✓~])\]\s*(.*)$"
                )
                for line in lines:
                    stripped = line.strip()
                    m = chk_regex.match(stripped)
                    if m:
                        state, task_raw = m.group(1), m.group(2).strip()
                        if task_raw.lower().startswith("progress:"):
                            continue
                        if _norm(task_raw) in seen:
                            continue
                        seen.add(_norm(task_raw))
                        total += 1
                        task_text = escape(task_raw)
                        if state in ("x", "X", "v", "✓"):
                            completed += 1
                            tasks.append(f"[bold green]☑ {task_text}[/bold green]")
                        elif state in ("/", "-", "~"):
                            tasks.append(f"[bold yellow]■ {task_text} █[/bold yellow]")
                        else:
                            tasks.append(f"[dim]☐ {task_text}[/dim]")
        except Exception:  # noqa: BLE001, S110
            pass

    if total == 0:
        return (
            f"{mode_hdr}\n[dim]No active plan checkboxes found.[/dim]\n\n"
            f"[bold cyan]📋 TASKS[/bold cyan]\n[dim]Waiting for goal initialization...[/dim]"
        )

    pct = int((completed / total) * 100) if total > 0 else 0
    bar_width = 12
    filled = min(bar_width, round((pct / 100.0) * bar_width))
    bar = "█" * filled + "░" * (bar_width - filled)

    prog_str = (
        f"[{bar}] [bold green]{pct}%[/bold green] [dim]({completed}/{total})[/dim]"
    )
    tree_header = "[bold cyan]📋 IMPLEMENTATION PLAN[/bold cyan]"
    body = "\n".join(tasks[:10])
    if len(tasks) > 10:
        body += f"\n[dim]...+{len(tasks) - 10} more[/dim]"

    return f"{mode_hdr}\n{prog_str}\n\n{tree_header}\n{body}"
