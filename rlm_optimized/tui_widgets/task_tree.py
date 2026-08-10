"""
TaskTreeWidget: High-performance, non-blocking task tree widget for Torchlight TUI.

Renders hierarchical task progress, active subtask focus, status badges,
and progress indicators using Rich markup and Textual layout.
"""

from __future__ import annotations

import os
from typing import Optional

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static


def build_task_tree_markup(project_root: Optional[str]) -> str:
    """Build Rich-markup formatted text representation of workspace tasks."""
    if not project_root or not os.path.exists(project_root):
        return "[dim]No active workspace task spec found.[/]"

    from core.tools.task_helpers import (
        _load_goal_spec,
        parse_all_tasks_from_markdown,
        _clean_task_text,
    )

    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")
    gdata = _load_goal_spec(alt_goal_path)

    tasks = []
    goal_title = "Workspace Execution Goal"

    if gdata and gdata.get("tasks"):
        goal_title = gdata.get("title") or goal_title
        for t in gdata.get("tasks", []):
            tasks.append({
                "id": t.get("id"),
                "description": str(t.get("description") or t.get("id") or "Task"),
                "status": str(t.get("status", "pending")).lower(),
                "depends_on": t.get("depends_on", []),
            })
    else:
        for md_name in ("implementation_plan.md", os.path.join(".torchlight", "tasks.md")):
            md_path = os.path.join(project_root, md_name)
            if os.path.exists(md_path):
                parsed = parse_all_tasks_from_markdown(md_path)
                for t in parsed:
                    tasks.append({
                        "id": None,
                        "description": t.get("description", "Task"),
                        "status": t.get("status", "pending").lower(),
                        "depends_on": [],
                    })
                break

    if not tasks:
        return "[dim]No tasks defined in implementation plan.[/]"

    total = len(tasks)
    completed_count = sum(1 for t in tasks if t["status"] in ("completed", "verified", "done", "skipped"))
    percent = int((completed_count / total) * 100) if total > 0 else 0
    filled = int((completed_count / max(1, total)) * 10)
    bar = "█" * filled + "░" * (10 - filled)

    lines = [
        f"[bold cyan]🎯 Goal: {escape(goal_title)}[/]",
        f"[bold yellow]Progress: [{bar}] {completed_count}/{total} ({percent}%)[/]\n",
    ]

    status_styles = {
        "completed": ("✅", "green", "bold green"),
        "verified": ("✅", "green", "bold green"),
        "done": ("✅", "green", "bold green"),
        "in_progress": ("⏳", "yellow", "bold yellow"),
        "active": ("⏳", "yellow", "bold yellow"),
        "verifying": ("🔍", "cyan", "bold cyan"),
        "blocked": ("🔒", "gray", "dim white"),
        "failed": ("❌", "red", "bold red"),
        "skipped": ("⏭️", "gray", "strike dim"),
        "pending": ("⚪", "white", "white"),
    }

    for idx, t in enumerate(tasks, 1):
        st = t["status"]
        icon, _, style = status_styles.get(st, ("⚪", "white", "white"))
        desc = escape(_clean_task_text(t["description"]))
        if st in ("in_progress", "active"):
            lines.append(f"  [{style}]{icon} [{idx}] {desc} [bold yellow]← Active Focus[/][/]")
        elif st in ("completed", "verified", "done"):
            lines.append(f"  [{style}]{icon} [{idx}] [strike]{desc}[/][/]")
        else:
            lines.append(f"  [{style}]{icon} [{idx}] {desc}[/]")

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

    def __init__(self, project_root: Optional[str] = None, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.project_root = project_root

    def compose(self) -> ComposeResult:
        yield Static(build_task_tree_markup(self.project_root), id="task-tree-content")

    def update_tasks(self, project_root: Optional[str] = None) -> None:
        if project_root is not None:
            self.project_root = project_root
        markup = build_task_tree_markup(self.project_root)
        try:
            content = self.query_one("#task-tree-content", Static)
            content.update(markup)
        except Exception:  # noqa: BLE001, S110
            pass
