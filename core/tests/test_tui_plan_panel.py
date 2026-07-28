import os
import tempfile
import pytest
from unittest.mock import MagicMock

def _build_plan_text_isolated(project_root: str) -> str:
    """Isolated plan builder matching TorchlightApp logic."""
    from rich.markup import escape
    plan_path = os.path.join(project_root, "implementation_plan.md")
    if not os.path.exists(plan_path):
        return "[dim]No active implementation_plan.md[/dim]"

    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        tasks = []
        completed = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
                completed += 1
                task_text = escape(stripped[5:].strip())
                tasks.append(f"[bold green]✅ {task_text}[/bold green]")
            elif stripped.startswith("- [ ]"):
                task_text = escape(stripped[5:].strip())
                tasks.append(f"[yellow]⏳ {task_text}[/yellow]")
            elif stripped.startswith("##"):
                title = escape(stripped.lstrip("#").strip())
                tasks.append(f"[bold cyan]📌 {title}[/bold cyan]")

        total = sum(1 for line in lines if line.strip().startswith(("- [ ]", "- [x]", "- [X]")))
        if total == 0:
            return "[dim]implementation_plan.md exists (0 tasks)[/dim]"

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
            f.write("## Phase 1\n- [x] Done Task\n- [ ] Pending Task\n")

        res = _build_plan_text_isolated(tmpdir)
        assert "Progress:" in res
        assert "50%" in res
        assert "✅ Done Task" in res
        assert "⏳ Pending Task" in res
        assert "📌 Phase 1" in res

def test_build_plan_text_all_done():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("- [x] Done 1\n- [X] Done 2\n")

        res = _build_plan_text_isolated(tmpdir)
        assert "100%" in res
        assert "(2/2)" in res
