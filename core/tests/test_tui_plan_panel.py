import os
import json
import tempfile
import pytest
from unittest.mock import MagicMock

def _build_plan_text_isolated(project_root: str) -> str:
    """Isolated plan builder matching TorchlightApp logic."""
    from rich.markup import escape
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
    else:
        return "[dim]No active implementation_plan.md[/dim]"

    try:
        if file_type == "json":
            with open(target_file, "r", encoding="utf-8") as f:
                goal_data = json.load(f)
            goal_title = goal_data.get("title", "Autonomous Goal")
            raw_tasks = goal_data.get("tasks", [])
            tasks = [f"[bold cyan]📌 {escape(goal_title)}[/bold cyan]"]
            completed = 0
            for t in raw_tasks:
                st = t.get("status", "pending")
                desc = escape(str(t.get("description") or t.get("id") or "Task"))
                if st in ("verified", "completed"):
                    completed += 1
                    tasks.append(f"[bold green]✅ {desc}[/bold green]")
                elif st == "in_progress":
                    tasks.append(f"[bold cyan]● {desc}[/bold cyan]")
                else:
                    tasks.append(f"[yellow]⏳ {desc}[/yellow]")
            total = len(raw_tasks)
        else:
            with open(target_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            tasks = []
            completed = 0
            total = 0
            import re
            chk_regex = re.compile(r"^(?:[-*]|\d+\.)\s*\[([ xX/\-])\]\s*(.*)$")

            for line in lines:
                stripped = line.strip()
                m = chk_regex.match(stripped)
                if m:
                    state, task_raw = m.group(1), m.group(2).strip()
                    total += 1
                    task_text = escape(task_raw)
                    if state in ("x", "X"):
                        completed += 1
                        tasks.append(f"[bold green]✅ {task_text}[/bold green]")
                    elif state in ("/", "-"):
                        tasks.append(f"[bold cyan]● {task_text}[/bold cyan]")
                    else:
                        tasks.append(f"[yellow]⏳ {task_text}[/yellow]")
                elif stripped.startswith("##"):
                    title = escape(stripped.lstrip("#").strip())
                    tasks.append(f"[bold cyan]📌 {title}[/bold cyan]")

        if total == 0:
            basename = os.path.basename(target_file)
            return f"[dim]{basename} exists (0 tasks)[/dim]"

        pct = int((completed / total) * 100) if total > 0 else 0
        bar_width = 10
        filled = min(bar_width, int(round((pct / 100.0) * bar_width)))
        bar = "█" * filled + "░" * (bar_width - filled)

        header = f"[bold white]Progress:[/] [{bar}] [bold green]{pct}%[/] [dim]({completed}/{total})[/dim]"
        body = "\n".join(tasks[:12])
        if len(tasks) > 12:
            body += f"\n[dim]...+{len(tasks)-12} more[/dim]"

        return f"{header}\n\n{body}"
    except Exception:
        return "[dim red]Error reading plan file[/dim red]"


def test_build_plan_text_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        res = _build_plan_text_isolated(tmpdir)
        assert "No active implementation_plan.md" in res

def test_build_plan_text_with_tasks():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("## Phase 1\n- [x] Done Task\n* [ ] Pending Task\n1. [/] In-progress Task\n")

        res = _build_plan_text_isolated(tmpdir)
        assert "Progress:" in res
        assert "33%" in res
        assert "✅ Done Task" in res
        assert "⏳ Pending Task" in res
        assert "● In-progress Task" in res
        assert "📌 Phase 1" in res

def test_build_plan_text_all_done():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("- [x] Done 1\n- [X] Done 2\n")

        res = _build_plan_text_isolated(tmpdir)
        assert "100%" in res
        assert "(2/2)" in res

def test_build_plan_text_goal_spec_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".torchlight"), exist_ok=True)
        goal_path = os.path.join(tmpdir, ".torchlight", "goal_spec.json")
        with open(goal_path, "w", encoding="utf-8") as f:
            json.dump({
                "title": "Build Agent",
                "tasks": [
                    {"id": "t1", "description": "Design UI", "status": "verified"},
                    {"id": "t2", "description": "Implement feature", "status": "in_progress"},
                ]
            }, f)

        res = _build_plan_text_isolated(tmpdir)
        assert "50%" in res
        assert "📌 Build Agent" in res
        assert "✅ Design UI" in res
        assert "● Implement feature" in res
def test_tui_app_tcss_valid_syntax():
    tcss_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "rlm_optimized", "tui_app.tcss"))
    assert os.path.exists(tcss_path), f"tui_app.tcss not found at {tcss_path}"
    with open(tcss_path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        from textual.css.parse import parse
        parse("tui_app.tcss", content)
    except ImportError:
        pytest.skip("textual not installed in test environment")
