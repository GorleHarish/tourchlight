"""
TaskTreeWidget: High-performance, non-blocking task tree widget for Torchlight TUI.

Renders hierarchical task progress, active subtask focus, status badges,
and progress indicators using Rich markup and Textual layout.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static


def escape_markup(text: str) -> str:
    """Safely escape text for Textual markup parsing."""
    if not text:
        return ""
    return str(text).replace("\\", "\\\\").replace("[", "\\[")


def _clean_task_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith(("- [ ] ", "- [/] ", "- [x] ", "- [X] ")):
        cleaned = cleaned[6:]
    return cleaned.strip()


def build_task_tree_markup(project_root: str | None = None) -> str:
    """Build a Rich markup string representing the active task breakdown."""
    root = str(project_root or os.getcwd())
    goal_json_path = os.path.join(root, ".torchlight", "goal_spec.json")
    tasks_md_path = os.path.join(root, ".torchlight", "tasks.md")
    plan_path = os.path.join(root, "implementation_plan.md")

    goal_title = "Active Development Goal"
    tasks: list[dict] = []


    # 1. Primary source: .torchlight/goal_spec.json
    if os.path.isfile(goal_json_path):
        try:
            with open(goal_json_path, "r", encoding="utf-8") as f:
                spec = json.load(f)
            if isinstance(spec, dict):
                goal_title = spec.get("goal") or spec.get("title") or goal_title
                for t in spec.get("tasks", []):
                    if isinstance(t, dict):
                        tasks.append(
                            {
                                "id": t.get("id"),
                                "description": t.get("description", "Task"),
                                "status": str(t.get("status", "pending")).lower(),
                            }
                        )
        except Exception:
            pass

    # 2. Secondary source: .torchlight/tasks.md or implementation_plan.md
    if not tasks:
        target_md = (
            tasks_md_path
            if os.path.isfile(tasks_md_path)
            else (plan_path if os.path.isfile(plan_path) else None)
        )
        if target_md:
            from core.tools.task_helpers import parse_all_tasks_from_markdown

            parsed = parse_all_tasks_from_markdown(target_md)
            for t in parsed:
                tasks.append(
                    {
                        "id": t.get("id"),
                        "description": t.get("description", "Task"),
                        "status": str(t.get("status", "pending")).lower(),
                    }
                )
            try:
                with open(target_md, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if line.startswith("# "):
                            goal_title = line.lstrip("# ").strip()
                            break
            except Exception:
                pass

    if not tasks:
        return "[dim]No active tasks defined in workspace.[/]"


    total = len(tasks)
    completed_count = sum(1 for t in tasks if t["status"] in ("completed", "verified", "done", "skipped"))
    percent = int((completed_count / total) * 100) if total > 0 else 0
    filled = int((completed_count / max(1, total)) * 10)
    bar = "#" * filled + "-" * (10 - filled)

    lines = [
        f"[bold cyan]Goal: {escape_markup(goal_title)}[/bold cyan]",
        f"[bold yellow]Progress: \\[{bar}\\] {completed_count}/{total} ({percent}%)[/bold yellow]\n",
    ]

    status_styles = {
        "completed": ("[DONE]", "green", "bold green"),
        "verified": ("[DONE]", "green", "bold green"),
        "done": ("[DONE]", "green", "bold green"),
        "in_progress": ("[RUNNING]", "yellow", "bold yellow"),
        "active": ("[RUNNING]", "yellow", "bold yellow"),
        "verifying": ("[VERIFY]", "cyan", "bold cyan"),
        "blocked": ("[BLOCKED]", "gray", "dim white"),
        "failed": ("[FAILED]", "red", "bold red"),
        "skipped": ("[SKIPPED]", "gray", "strike dim"),
        "pending": ("[TODO]", "white", "white"),
    }

    for idx, t in enumerate(tasks, 1):
        st = t["status"]
        icon, _, style = status_styles.get(st, ("[TODO]", "white", "white"))
        desc = escape_markup(_clean_task_text(t["description"]))
        if st in ("in_progress", "active"):
            lines.append(f"  [{style}]{icon} \\[{idx}\\] {desc} [bold yellow]<-- Active Focus[/bold yellow][/{style}]")
        elif st in ("completed", "verified", "done"):
            lines.append(f"  [{style}]{icon} \\[{idx}\\] [strike]{desc}[/strike][/{style}]")
        else:
            lines.append(f"  [{style}]{icon} \\[{idx}\\] {desc}[/{style}]")

    return "\n".join(lines)



class TaskTreeWidget(VerticalScroll):
    """Widget rendering real-time workspace task progression."""

    DEFAULT_CSS = """
    TaskTreeWidget {
        height: auto;
        max-height: 14;
        background: $surface;
        border: solid $accent;
        padding: 1 2;
        margin-bottom: 1;
        overflow-y: auto;
    }
    """

    def __init__(self, project_root: str | None = None, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.project_root = project_root

    def compose(self) -> ComposeResult:
        yield Static(build_task_tree_markup(self.project_root), id="task-tree-content")

    def update_tasks(self, project_root: str | None = None) -> None:
        if project_root is not None:
            self.project_root = project_root
        markup = build_task_tree_markup(self.project_root)
        try:
            content = self.query_one("#task-tree-content", Static)
            content.update(markup)
        except Exception:  # noqa: BLE001, S110
            pass

