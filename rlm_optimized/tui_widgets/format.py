"""Pure text-formatting helpers for the Torchlight TUI.

No engine / App state, no Textual dependency — importable and testable in
isolation. Rendered strings use Rich markup so they can be fed directly into
``Static`` widgets.
"""

import json
import os
import re
from typing import Any, Optional

from rich.markup import escape


def build_plan_overview_text(project_root: str, is_goal: bool = False, mode: str = "") -> str:
    """Render Implementation Plan overview (title & mode badge)."""
    plan_path = os.path.join(project_root, "implementation_plan.md")
    alt_tasks_path = os.path.join(project_root, ".torchlight", "tasks.md")
    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")

    target_file = None
    if os.path.exists(plan_path):
        target_file = plan_path
    elif os.path.exists(alt_tasks_path):
        target_file = alt_tasks_path
    elif os.path.exists(alt_goal_path):
        target_file = alt_goal_path

    plan_title = "Active Development Goal"
    if target_file and os.path.exists(target_file):
        try:
            if target_file.endswith(".json"):
                with open(target_file, "r", encoding="utf-8") as f:
                    goal_data = json.load(f)
                plan_title = str(goal_data.get("goal") or goal_data.get("title") or "Active Goal Spec")
            else:
                with open(target_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("# "):
                            plan_title = line.lstrip("# ").strip()
                            break
        except Exception:
            pass

    m_lower = (mode or "").lower().strip()
    if m_lower == "code":
        return f"[bold blue]CODE MODE[/bold blue]\n[bold white]{escape(plan_title)}[/bold white]"
    elif m_lower == "plan":
        return f"[bold magenta]PLAN MODE[/bold magenta]\n[bold white]{escape(plan_title)}[/bold white]"
    elif is_goal or m_lower == "goal":
        return f"[bold green]GOAL MODE[/bold green]\n[bold white]{escape(plan_title)}[/bold white]"
    return f"[bold white]{escape(plan_title)}[/bold white]"


def build_task_checklist_text(project_root: str, is_goal: bool = False) -> str:
    """Render Task Checklist hierarchy & progress bar."""
    from core.tools.task_helpers import parse_all_tasks_from_markdown, sync_workspace_tasks

    plan_path = os.path.join(project_root, "implementation_plan.md")
    alt_tasks_path = os.path.join(project_root, ".torchlight", "tasks.md")
    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")

    candidates = [
        (plan_path, "markdown"),
        (alt_tasks_path, "markdown"),
        (alt_goal_path, "json"),
    ]

    active_tasks = []
    completed_tasks = []
    in_progress_tasks = []
    seen: set[str] = set()

    def _norm(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().lower())

    for target_file, file_type in candidates:
        if not os.path.exists(target_file):
            continue
        active_tasks.clear()
        completed_tasks.clear()
        in_progress_tasks.clear()
        seen.clear()

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
                    desc_clean = desc_raw[:47] + "..." if len(desc_raw) > 50 else desc_raw
                    desc = escape(desc_clean)
                    if st in ("verified", "completed"):
                        completed_tasks.append(f"[bold green]  [DONE] {desc}[/bold green]")
                    elif st in ("in_progress", "active"):
                        in_progress_tasks.append(f"[bold yellow]  [RUNNING] {desc}[/bold yellow]")
                    else:
                        active_tasks.append(f"[dim]  [ ] {desc}[/dim]")
            else:
                parsed = parse_all_tasks_from_markdown(target_file)
                for t in parsed:
                    desc_raw = t["description"]
                    if _norm(desc_raw) in seen:
                        continue
                    seen.add(_norm(desc_raw))
                    task_text_clean = desc_raw[:47] + "..." if len(desc_raw) > 50 else desc_raw
                    task_text = escape(task_text_clean)
                    if t["status"] == "completed":
                        completed_tasks.append(f"[bold green]  [DONE] {task_text}[/bold green]")
                    elif t["status"] == "in_progress":
                        in_progress_tasks.append(f"[bold yellow]  [RUNNING] {task_text}[/bold yellow]")
                    else:
                        active_tasks.append(f"[dim]  [ ] {task_text}[/dim]")
        except Exception:  # noqa: BLE001, S110
            pass

        if len(completed_tasks) + len(in_progress_tasks) + len(active_tasks) > 0:
            break

    total = len(completed_tasks) + len(in_progress_tasks) + len(active_tasks)
    if total == 0 and is_goal:
        # Trigger self-healing sync if 0 tasks found in Goal Mode
        try:
            sync_workspace_tasks(project_root)
            return build_task_checklist_text(project_root, is_goal=False)
        except Exception:
            pass

    completed = len(completed_tasks)

    if total == 0:
        return "[dim]No active plan checkboxes found.\nWaiting for goal initialization...[/dim]"

    pct = int((completed / total) * 100) if total > 0 else 0
    bar_width = 12
    filled = min(bar_width, round((pct / 100.0) * bar_width))
    bar = "#" * filled + "-" * (bar_width - filled)
    prog_str = (
        f"[{bar}] [bold green]{pct}%[/bold green] [dim]({completed}/{total})[/dim]"
    )

    sections = []
    if in_progress_tasks:
        sections.append("[bold yellow]IN PROGRESS[/bold yellow]\n" + "\n".join(in_progress_tasks))
    if active_tasks:
        if len(active_tasks) > 3:
            shown_up_next = active_tasks[:3]
            overflow = len(active_tasks) - 3
            shown_up_next.append(f"[dim]  + {overflow} more pending tasks (Press Ctrl+K)[/dim]")
            sections.append("[bold white]UP NEXT[/bold white]\n" + "\n".join(shown_up_next))
        else:
            sections.append("[bold white]UP NEXT[/bold white]\n" + "\n".join(active_tasks))
    if completed_tasks:
        if len(completed_tasks) > 2:
            shown_completed = completed_tasks[:2]
            overflow = len(completed_tasks) - 2
            shown_completed.append(f"[dim]  + {overflow} completed tasks collapsed[/dim]")
            sections.append(f"[bold green]COMPLETED ({len(completed_tasks)})[/bold green]\n" + "\n".join(shown_completed))
        else:
            sections.append(f"[bold green]COMPLETED ({len(completed_tasks)})[/bold green]\n" + "\n".join(completed_tasks))

    task_list_markup = "\n\n".join(sections)
    return f"{prog_str}\n\n{task_list_markup}"


def build_plan_text(project_root: str, is_goal: bool = False, mode: str = "") -> str:
    """Render Production-Grade Implementation Plan & Task Hierarchy."""
    from core.tools.task_helpers import parse_all_tasks_from_markdown, sync_workspace_tasks

    plan_path = os.path.join(project_root, "implementation_plan.md")
    alt_tasks_path = os.path.join(project_root, ".torchlight", "tasks.md")
    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")

    candidates = [
        (plan_path, "markdown"),
        (alt_tasks_path, "markdown"),
        (alt_goal_path, "json"),
    ]

    plan_title = "Active Development Goal"
    active_tasks = []
    completed_tasks = []
    in_progress_tasks = []
    seen: set[str] = set()

    def _norm(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().lower())

    for target_file, file_type in candidates:
        if not os.path.exists(target_file):
            continue
        active_tasks.clear()
        completed_tasks.clear()
        in_progress_tasks.clear()
        seen.clear()

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
                        completed_tasks.append(f"[bold green]  [DONE] {desc}[/bold green]")
                    elif st in ("in_progress", "active"):
                        in_progress_tasks.append(f"[bold yellow]  [RUNNING] {desc}[/bold yellow]")
                    else:
                        active_tasks.append(f"[dim]  [ ] {desc}[/dim]")
            else:
                parsed = parse_all_tasks_from_markdown(target_file)
                for t in parsed:
                    desc_raw = t["description"]
                    if _norm(desc_raw) in seen:
                        continue
                    seen.add(_norm(desc_raw))
                    task_text = escape(desc_raw)
                    if t["status"] == "completed":
                        completed_tasks.append(f"[bold green]  [DONE] {task_text}[/bold green]")
                    elif t["status"] == "in_progress":
                        in_progress_tasks.append(f"[bold yellow]  [RUNNING] {task_text}[/bold yellow]")
                    else:
                        active_tasks.append(f"[dim]  [ ] {task_text}[/dim]")
        except Exception:  # noqa: BLE001, S110
            pass

        if len(completed_tasks) + len(in_progress_tasks) + len(active_tasks) > 0:
            break

    total = len(completed_tasks) + len(in_progress_tasks) + len(active_tasks)
    if total == 0 and is_goal:
        # Trigger self-healing sync if 0 tasks found in Goal Mode
        try:
            sync_workspace_tasks(project_root)
            return build_plan_text(project_root, is_goal=False, mode=mode)
        except Exception:
            pass

    completed = len(completed_tasks)

    # 1. Header & Goal Title
    plan_header = "[bold cyan]PLAN & TASKS[/bold cyan]"
    m_lower = (mode or "").lower().strip()
    if m_lower == "code":
        goal_badge = "[bold blue]CODE MODE[/bold blue]\n"
    elif m_lower == "plan":
        goal_badge = "[bold magenta]PLAN MODE[/bold magenta]\n"
    elif is_goal or m_lower == "goal":
        goal_badge = "[bold green]GOAL MODE[/bold green]\n"
    else:
        goal_badge = ""
    plan_body = f"[bold white]{escape(plan_title)}[/bold white]"

    # 2. Progress Gauge & Task Hierarchy
    if total == 0:
        task_list_markup = "[dim]No active plan checkboxes found.\nWaiting for goal initialization...[/dim]"
        prog_str = "[dim]0/0 tasks completed[/dim]"
    else:
        pct = int((completed / total) * 100) if total > 0 else 0
        bar_width = 12
        filled = min(bar_width, round((pct / 100.0) * bar_width))
        bar = "#" * filled + "-" * (bar_width - filled)
        prog_str = (
            f"[{bar}] [bold green]{pct}%[/bold green] [dim]({completed}/{total})[/dim]"
        )

        sections = []
        if in_progress_tasks:
            sections.append("[bold yellow]IN PROGRESS[/bold yellow]\n" + "\n".join(in_progress_tasks))
        if active_tasks:
            sections.append("[bold white]UP NEXT[/bold white]\n" + "\n".join(active_tasks))
        if completed_tasks:
            sections.append(f"[bold green]COMPLETED ({len(completed_tasks)})[/bold green]\n" + "\n".join(completed_tasks))

        task_list_markup = "\n\n".join(sections)

    return (
        f"{plan_header}\n"
        f"{goal_badge}"
        f"{plan_body}\n\n"
        f"{prog_str}\n\n"
        f"{task_list_markup}"
    )


def _clean_scratchpad_item(text: str, max_chars: int = 2000) -> str:
    """Normalize a single scratchpad item for sidebar display, preserving full text."""
    cleaned = re.sub(r"[\t ]+", " ", str(text).strip())
    if len(cleaned) > max_chars:
        return cleaned[: max_chars - 3].rstrip() + "..."
    return cleaned



def build_agent_memory_scratchpad_text(
    mem: Any = None,
    project_root: Optional[str] = None,
    raw_text: Optional[str] = None,
    is_goal: bool = False,
) -> str:
    """Render UI/UX Pro formatted Agent Working Memory (L0 Scratchpad).

    Transforms internal TieredMemory state or raw scratchpad prompt text
    into a structured, color-coded, card-based terminal display.
    """
    goal: str = ""
    active_file: str = ""
    blocker: str = ""
    next_steps: list[str] = []
    errors: list[str] = []
    failing_tests: list[str] = []
    files_modified: list[str] = []
    files_stats: dict[str, list[int]] = {}
    files_symbols: dict[str, list[str]] = {}
    decisions: list[str] = []
    tried_and_failed: list[str] = []
    tech_stack: list[str] = []
    mem_facts: list[str] = []

    # 1. Direct State Extraction from TieredMemory / SessionState
    if mem is not None and hasattr(mem, "state") and mem.state is not None:
        st = mem.state
        goal = getattr(st, "current_task", "") or getattr(st, "intent", "")
        active_file = getattr(st, "active_file", "")
        blocker = getattr(st, "current_blocker", "")
        next_steps = list(getattr(st, "next_steps", []))
        errors = list(getattr(st, "errors_seen", []))
        failing_tests = list(getattr(st, "failing_tests", []))
        files_modified = list(getattr(st, "files_modified", []))
        files_stats = dict(getattr(st, "files_modified_stats", {}))
        files_symbols = dict(getattr(st, "files_modified_symbols", {}))
        decs_src = getattr(st, "arch_decisions", None) or getattr(st, "decisions", [])
        decisions = [str(d) for d in decs_src]
        tried_and_failed = list(getattr(st, "tried_and_failed", []))
        tech_stack = list(getattr(st, "tech_stack", []))

        # Memory Needles & Objects
        needles = getattr(st, "needle_ledger", [])
        for n in needles:
            val = getattr(n, "value", str(n))
            if val and val not in mem_facts:
                mem_facts.append(val)
        objects = getattr(st, "memory_objects", [])
        for o in objects:
            summary = getattr(o, "summary", str(o))
            if summary and summary not in mem_facts:
                mem_facts.append(summary)

    # 2. Text Parsing Fallback (from raw_text, mem string, or mem.format_l0_scratchpad)
    text_to_parse = raw_text
    if text_to_parse is None and isinstance(mem, str):
        text_to_parse = mem
    elif (
        text_to_parse is None
        and mem is not None
        and hasattr(mem, "format_l0_scratchpad")
        and not (goal or active_file or errors or failing_tests or files_modified or decisions or tried_and_failed)
    ):
        try:
            text_to_parse = mem.format_l0_scratchpad(project_root=project_root)
        except Exception:  # noqa: BLE001
            text_to_parse = ""

    if text_to_parse and isinstance(text_to_parse, str):
        for line in text_to_parse.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith(("[L0 WORKING MEMORY", "===")):
                continue
            if line_str.startswith("- Active Errors:"):
                raw_val = line_str[len("- Active Errors:") :].strip()
                for item in raw_val.split(";"):
                    if item.strip() and item.strip() not in errors:
                        errors.append(item.strip())
            elif line_str.startswith("- Failing Tests:"):
                raw_val = line_str[len("- Failing Tests:") :].strip()
                for item in raw_val.split(","):
                    if item.strip() and item.strip() not in failing_tests:
                        failing_tests.append(item.strip())
            elif line_str.startswith("- Active Goal:"):
                if not goal:
                    goal = line_str[len("- Active Goal:") :].strip()
            elif line_str.startswith("- Active File:"):
                if not active_file:
                    active_file = line_str[len("- Active File:") :].strip()
            elif line_str.startswith("- Key Decisions:"):
                raw_val = line_str[len("- Key Decisions:") :].strip()
                for item in raw_val.split(";"):
                    if item.strip() and item.strip() not in decisions:
                        decisions.append(item.strip())
            elif line_str.startswith("- Modified Files:"):
                raw_val = line_str[len("- Modified Files:") :].strip()
                for item in raw_val.split(","):
                    item_clean = item.strip()
                    if item_clean and item_clean not in files_modified:
                        files_modified.append(item_clean)
            elif line_str.startswith("- Tech Stack:"):
                raw_val = line_str[len("- Tech Stack:") :].strip()
                for item in raw_val.split(","):
                    if item.strip() and item.strip() not in tech_stack:
                        tech_stack.append(item.strip())
            elif line_str.startswith("- Tried & Failed:"):
                raw_val = line_str[len("- Tried & Failed:") :].strip()
                for item in raw_val.split(";"):
                    if item.strip() and item.strip() not in tried_and_failed:
                        tried_and_failed.append(item.strip())
            elif line_str.startswith("- Facts & Past Context:"):
                raw_val = line_str[len("- Facts & Past Context:") :].strip()
                for item in raw_val.split(";"):
                    if item.strip() and item.strip() not in mem_facts:
                        mem_facts.append(item.strip())
            elif line_str.startswith("Task [") and "in_progress" in line_str:
                if not goal:
                    goal = line_str

    # 3. Assemble UI/UX Pro Cards (Pure Text, No Emojis/Icons, Full Text with Scrollbars)
    card_sections: list[str] = []

    # Card 1: Active Objective & Target
    if goal or active_file or blocker or next_steps:
        obj_lines = ["[bold cyan]ACTIVE OBJECTIVE[/bold cyan]"]
        if goal:
            clean_goal = _clean_scratchpad_item(goal)
            obj_lines.append(f"  [bold white]Goal:[/] [cyan]{escape(clean_goal)}[/cyan]")
        if active_file:
            clean_file = _clean_scratchpad_item(active_file)
            obj_lines.append(f"  [dim]File:[/] [bold green]{escape(clean_file)}[/bold green]")
        if blocker:
            clean_blk = _clean_scratchpad_item(blocker)
            obj_lines.append(f"  [bold yellow]Blocker:[/] [yellow]{escape(clean_blk)}[/yellow]")
        if next_steps:
            for ns in next_steps[:3]:
                obj_lines.append(f"  [dim]Next:[/] [white]{escape(_clean_scratchpad_item(ns))}[/white]")
        card_sections.append("\n".join(obj_lines))

    # Card 2: Active Issues & Errors (Full un-truncated error text)
    if failing_tests or errors:
        issue_lines = ["[bold red]ACTIVE ISSUES[/bold red]"]
        if failing_tests:
            for ft in failing_tests[-4:]:
                clean_test = _clean_scratchpad_item(ft)
                issue_lines.append(f"  [bold red]- Failing:[/] [red]{escape(clean_test)}[/red]")
        if errors:
            unique_errors = list(dict.fromkeys(errors))[-4:]
            for err in unique_errors:
                clean_err = _clean_scratchpad_item(err)
                issue_lines.append(f"  [bold red]- Error:[/] [white]{escape(clean_err)}[/white]")
        card_sections.append("\n".join(issue_lines))

    # Card 3: Modified Files
    if files_modified:
        mod_lines = ["[bold yellow]MODIFIED FILES[/bold yellow]"]
        for f in files_modified[-6:]:
            f_clean = str(f).strip()
            # If line has stats embedded like "foo.py (+1, -2)"
            if "(" in f_clean and ")" in f_clean:
                mod_lines.append(f"  [bold white]- {escape(_clean_scratchpad_item(f_clean))}[/bold white]")
            else:
                stat_badge = ""
                if f_clean in files_stats:
                    st = files_stats[f_clean]
                    if len(st) == 2:
                        stat_badge = f" [bold green]+{st[0]}[/] [bold red]-{st[1]}[/]"
                sym_badge = ""
                if files_symbols.get(f_clean):
                    syms = ", ".join(files_symbols[f_clean][:3])
                    sym_badge = f" [dim cyan][{escape(syms)}][/dim cyan]"
                f_display = _clean_scratchpad_item(f_clean)
                mod_lines.append(f"  [bold white]- {escape(f_display)}[/bold white]{stat_badge}{sym_badge}")
        card_sections.append("\n".join(mod_lines))

    # Card 4: Key Decisions
    if decisions:
        dec_lines = ["[bold magenta]KEY DECISIONS[/bold magenta]"]
        for d in decisions[-5:]:
            dec_lines.append(f"  [dim]-[/dim] [white]{escape(_clean_scratchpad_item(d))}[/white]")
        card_sections.append("\n".join(dec_lines))

    # Card 5: Tried & Failed (Anti-Looping History)
    if tried_and_failed:
        tf_lines = ["[bold bright_yellow]ANTI-LOOP LOG[/bold bright_yellow]"]
        for tf in tried_and_failed[-4:]:
            tf_lines.append(f"  [yellow]-[/yellow] [dim yellow]{escape(_clean_scratchpad_item(tf))}[/dim yellow]")
        card_sections.append("\n".join(tf_lines))

    # Card 6: Tech Stack
    if tech_stack:
        badges = [f"[bold cyan]{escape(_clean_scratchpad_item(str(t)))}[/bold cyan]" for t in tech_stack[:8]]
        stack_lines = [
            "[bold blue]TECH STACK[/bold blue]",
            f"  [dim]Stack:[/] {', '.join(badges)}",
        ]
        card_sections.append("\n".join(stack_lines))

    # Card 7: Context & Facts
    if mem_facts:
        fact_lines = ["[bold green]CONTEXT & MEMORY[/bold green]"]
        for fact in mem_facts[-4:]:
            fact_lines.append(f"  [dim]- {escape(_clean_scratchpad_item(fact))}[/dim]")
        card_sections.append("\n".join(fact_lines))

    # Empty State
    if not card_sections:
        return (
            "[bold cyan]WORKING MEMORY (L0)[/bold cyan]\n"
            "[dim]State:[/] [bold green]Idle / Listening[/bold green]\n\n"
            "[dim]Dynamic scratchpad tracks active goals, errors, modified files, decisions, and anti-loop history during runs.[/dim]"
        )

    return "\n\n".join(card_sections)


def build_skills_overview_text(project_root: str, reload: bool = False) -> str:
    """Render structured rich markup summary of all discovered skills for the TUI."""
    try:
        from context_manager.skills.base import get_skill_directories
        from context_manager.skills.discovery import _load_skill_index
    except ImportError:
        import sys
        cli_src = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "context-manager-cli", "src")
        if cli_src not in sys.path:
            sys.path.insert(0, cli_src)
        from context_manager.skills.base import get_skill_directories
        from context_manager.skills.discovery import _load_skill_index

    dirs = get_skill_directories(project_root)
    skills_map = _load_skill_index(skills_dirs=dirs, reload=reload)

    if not skills_map:
        return (
            "[dim]No custom skills installed yet.[/dim]\n\n"
            "Click [bold cyan]'📥 Import Skill'[/] above to add external skills "
            "(e.g. [bold]SKILL.md[/] or [bold].py[/] files) into your workspace [bold green].agents/skills/[/]."
        )

    lines = []
    lines.append(f"[bold cyan]Total Available Skills:[/] [bold green]{len(skills_map)}[/]")
    lines.append("[dim]────────────────────────────────────────[/dim]")

    root_path = os.path.abspath(project_root)

    for key, info in sorted(skills_map.items(), key=lambda x: x[1].get("name", "")):
        name = info.get("name", key.lower())
        icon = info.get("icon", "🔧")
        desc = info.get("desc", "").strip() or "No description available"
        risk = str(info.get("risk_level", "auto")).upper()
        cat = str(info.get("category", "skill")).upper()
        path = info.get("path", "")

        # Determine scope badge
        rel_path = path
        if path.startswith(root_path):
            rel_path = os.path.relpath(path, root_path)
            scope_badge = "[bold green][WORKSPACE][/]"
        elif ".config" in path:
            scope_badge = "[bold blue][GLOBAL][/]"
        else:
            scope_badge = "[bold cyan][BUILT-IN][/]"

        # Risk badge color
        if risk == "AUTO":
            risk_badge = "[bold green][AUTO][/]"
        elif risk == "CONFIRM":
            risk_badge = "[bold yellow][CONFIRM][/]"
        else:
            risk_badge = "[bold red][REVIEW][/]"

        cat_badge = f"[bold magenta][{escape(cat)}][/]"

        lines.append(f"{icon} [bold white]{escape(name)}[/] {scope_badge} {risk_badge} {cat_badge}")
        lines.append(f"  [dim]{escape(desc[:120])}[/dim]")
        lines.append(f"  [dim]Path:[/] [dim cyan]{escape(rel_path)}[/]  │  [bold green]/{escape(name.lower())}[/]")
        lines.append("[dim]────────────────────────────────────────[/dim]")

    return "\n".join(lines)


def import_skill_file(
    source_path: str,
    custom_name: Optional[str] = None,
    workspace_root: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Import an external skill file (SKILL.md, .md, .py) or directory into
    the project's standard .agents/skills/ location.
    """
    import shutil
    from pathlib import Path

    root = Path(workspace_root or os.getcwd()).resolve()
    target_skills_dir = root / ".agents" / "skills"
    target_skills_dir.mkdir(parents=True, exist_ok=True)

    src = Path(os.path.expanduser(source_path.strip())).resolve()
    if not src.exists():
        return False, f"Source path not found: {source_path}"

    # Determine standard skill name slug
    if custom_name and custom_name.strip():
        slug = re.sub(r"[^a-z0-9_]+", "_", custom_name.strip().lower()).strip("_")
    elif src.is_dir():
        slug = re.sub(r"[^a-z0-9_]+", "_", src.name.lower()).strip("_")
    else:
        slug = re.sub(r"[^a-z0-9_]+", "_", src.stem.lower()).strip("_")

    if not slug:
        slug = "custom_skill"

    try:
        if src.is_dir():
            dest = target_skills_dir / slug
            shutil.copytree(src, dest, dirs_exist_ok=True)
            installed_path = f".agents/skills/{slug}/"
        elif src.suffix.lower() == ".py":
            dest = target_skills_dir / f"{slug}.py"
            shutil.copy2(src, dest)
            installed_path = f".agents/skills/{slug}.py"
        else:
            # Markdown skill (.md or SKILL.md)
            dest_dir = target_skills_dir / slug
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / "SKILL.md"
            shutil.copy2(src, dest)
            installed_path = f".agents/skills/{slug}/SKILL.md"

        # Invalidate and reload skill cache
        try:
            from context_manager.skills.base import get_skill_directories
            from context_manager.skills.discovery import _load_skill_index
            _load_skill_index(skills_dirs=get_skill_directories(str(root)), reload=True)
        except Exception:
            pass

        return True, f"Successfully imported '{slug}' into {installed_path}"
    except Exception as e:
        return False, f"Failed to import skill: {e}"



