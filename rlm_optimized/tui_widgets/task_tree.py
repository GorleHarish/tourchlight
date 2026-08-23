"""
TaskTreeWidget: High-performance, non-blocking task tree widget for Torchlight TUI.

Renders hierarchical task progress, active subtask focus, status badges,
and progress indicators using Rich markup and Textual layout.
"""

from __future__ import annotations

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


from core.memory.persistence import ProjectMemory


def _clean_task_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("- [ ] "):
        cleaned = cleaned[6:]
    elif cleaned.startswith("- [/] "):
        cleaned = cleaned[6:]
    elif cleaned.startswith("- [x] ") or cleaned.startswith("- [X] "):
        cleaned = cleaned[6:]
    return cleaned.strip()


def build_task_tree_markup(project_root: str) -> str:
    """Build a Rich markup string representing the active task breakdown."""
    mem = ProjectMemory.load(project_root)
    spec = mem.goal_spec or {}

    goal_title = spec.get("goal") or spec.get("title") or "No active goal"
    tasks = list(spec.get("tasks", []))

    if not tasks:
        plan_path = os.path.join(project_root, "implementation_plan.md")
        if os.path.isfile(plan_path):
            try:
                with open(plan_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                parsed = []
                for line in content.splitlines():
                    line_str = line.strip()
                    if line_str.startswith("- [ ]") or line_str.startswith("- [/]") or line_str.startswith("- [x]") or line_str.startswith("- [X]"):
                        st = "completed" if line_str.lower().startswith("- [x]") else ("in_progress" if line_str.startswith("- [/]") else "pending")
                        parsed.append({"description": _clean_task_text(line_str), "status": st})
                for t in parsed:
                    tasks.append({
                        "id": None,
                        "description": t.get("description", "Task"),
                        "status": t.get("status", "pending").lower(),
                        "depends_on": [],
                    })
            except Exception:
                pass

    if not tasks:
        return "[dim]No tasks defined in implementation plan.[/]"

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
