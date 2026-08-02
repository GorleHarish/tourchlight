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
    """Render Production-Grade Implementation Plan (top) and Task Hierarchy (bottom)."""
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

    plan_title = "Active Development Goal"
    active_tasks = []
    completed_tasks = []
    in_progress_tasks = []
    seen: set[str] = set()

    def _norm(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().lower())

    if target_file and os.path.exists(target_file):
        try:
            if file_type == "json":
                with open(target_file, "r", encoding="utf-8") as f:
                    goal_data = json.load(f)
                plan_title = str(goal_data.get("goal") or goal_data.get("title") or "Active Goal Spec")
                raw_tasks = goal_data.get("tasks", [])
                for t in raw_tasks:
                    st = t.get("status", "pending")
                    desc_raw = str(t.get("description") or t.get("id") or "Task")
                    if _norm(desc_raw) in seen:
                        continue
                    seen.add(_norm(desc_raw))
                    desc = escape(desc_raw)
                    if st in ("verified", "completed"):
                        completed_tasks.append(f"[bold green]  [✓] {desc}[/bold green]")
                    elif st in ("in_progress", "active"):
                        in_progress_tasks.append(f"[bold yellow]  [►] {desc} █[/bold yellow]")
                    else:
                        active_tasks.append(f"[dim]  [ ] {desc}[/dim]")
            else:
                with open(target_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line in lines:
                    if line.startswith("# "):
                        plan_title = line.lstrip("# ").strip()
                        break

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
                        task_text = escape(task_raw)
                        if state in ("x", "X", "v", "✓"):
                            completed_tasks.append(f"[bold green]  [✓] {task_text}[/bold green]")
                        elif state in ("/", "-", "~"):
                            in_progress_tasks.append(f"[bold yellow]  [►] {task_text} █[/bold yellow]")
                        else:
                            active_tasks.append(f"[dim]  [ ] {task_text}[/dim]")
        except Exception:  # noqa: BLE001, S110
            pass

    total = len(completed_tasks) + len(in_progress_tasks) + len(active_tasks)
    completed = len(completed_tasks)

    # 1. Top Section: Implementation Plan & Mode Badge
    mode_badge = "[bold green]🎯 GOAL MODE[/bold green]" if is_goal else "[bold cyan]💬 CHAT MODE[/bold cyan]"
    plan_header = f"[bold cyan]📄 IMPLEMENTATION PLAN[/bold cyan]  {mode_badge}"
    plan_body = f"[bold white]{escape(plan_title)}[/bold white]"

    # 2. Bottom Section: Tasks & TODO Hierarchy
    task_header = "[bold cyan]☑ ACTIVE TASKS & TODO[/bold cyan]"
    if total == 0:
        task_list_markup = "[dim]No active plan checkboxes found.\nWaiting for goal initialization...[/dim]"
        prog_str = "[dim]0/0 tasks completed[/dim]"
    else:
        pct = int((completed / total) * 100) if total > 0 else 0
        bar_width = 12
        filled = min(bar_width, round((pct / 100.0) * bar_width))
        bar = "█" * filled + "░" * (bar_width - filled)
        prog_str = (
            f"[{bar}] [bold green]{pct}%[/bold green] [dim]({completed}/{total})[/dim]"
        )

        sections = []
        if in_progress_tasks:
            sections.append("[bold yellow]► IN PROGRESS[/bold yellow]\n" + "\n".join(in_progress_tasks))
        if active_tasks:
            sections.append("[bold white]UP NEXT[/bold white]\n" + "\n".join(active_tasks[:8]))
        if completed_tasks:
            sections.append(f"[bold green]✓ COMPLETED ({len(completed_tasks)})[/bold green]\n" + "\n".join(completed_tasks[:8]))

        task_list_markup = "\n\n".join(sections)

    return (
        f"{plan_header}\n"
        f"{plan_body}\n\n"
        f"───────────────────────────────\n"
        f"{task_header}\n"
        f"{prog_str}\n\n"
        f"{task_list_markup}"
    )
