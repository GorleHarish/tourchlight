"""
Unified Task Helper Module for Torchlight.

Extracts pending tasks from implementation_plan.md, .torchlight/tasks.md,
or .torchlight/goal_spec.json across frontends and execution loops.
"""

import json
import os
import re

CHK_REGEX = re.compile(r"^(?:[-*+>]|\d+[\.\)])?\s*\[([ xX/\-v✓~])\]\s*(.*)$")


def parse_all_tasks_from_markdown(source: str) -> list[dict]:
    """
    Parse all task items from markdown content or file path.
    Returns list of dicts: [{"description": str, "status": str, "raw_state": str}]
    where status is 'completed', 'in_progress', or 'pending'.
    """
    lines = []
    if os.path.exists(source):
        try:
            with open(source, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return []
    else:
        lines = source.splitlines()

    tasks = []
    seen = set()
    in_task_section = False
    task_header_regex = re.compile(
        r"^#{1,6}\s*(?:tasks|plan|proposed changes|steps|action items|goal|todo)",
        re.IGNORECASE,
    )

    # 1. First pass: Checkbox items
    for line in lines:
        stripped = line.strip()
        m = CHK_REGEX.match(stripped)
        if m:
            state, task_raw = m.group(1), m.group(2).strip()
            if task_raw.lower().startswith("progress:"):
                continue
            norm = re.sub(r"\s+", " ", task_raw.lower()).strip()
            if norm in seen:
                continue
            seen.add(norm)
            if state in ("x", "X", "v", "✓"):
                status = "completed"
            elif state in ("/", "-", "~"):
                status = "in_progress"
            else:
                status = "pending"
            tasks.append({
                "description": task_raw,
                "status": status,
                "raw_state": state,
            })

    # 2. Fallback pass: bullet points under task/plan headers if no checkboxes found
    if not tasks:
        bullet_regex = re.compile(r"^(?:[-*+]|\d+[\.\)])\s+(.+)$")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                in_task_section = bool(task_header_regex.match(stripped))
                continue
            if in_task_section:
                bm = bullet_regex.match(stripped)
                if bm:
                    task_raw = bm.group(1).strip()
                    if task_raw.lower().startswith("progress:") or len(task_raw) < 3:
                        continue
                    norm = re.sub(r"\s+", " ", task_raw.lower()).strip()
                    if norm in seen:
                        continue
                    seen.add(norm)
                    tasks.append({
                        "description": task_raw,
                        "status": "pending",
                        "raw_state": " ",
                    })

    return tasks


def get_workspace_pending_tasks(project_root: str) -> list[str]:
    """
    Extract list of pending task descriptions from the workspace.
    Evaluates candidate task files sequentially until pending tasks are found:
    1. implementation_plan.md
    2. .torchlight/tasks.md
    3. .torchlight/goal_spec.json
    """
    if not project_root or not os.path.exists(project_root):
        return []

    plan_path = os.path.join(project_root, "implementation_plan.md")
    alt_tasks_path = os.path.join(project_root, ".torchlight", "tasks.md")
    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")

    # 1. Check markdown sources in priority order
    for md_path in (plan_path, alt_tasks_path):
        if os.path.exists(md_path):
            parsed = parse_all_tasks_from_markdown(md_path)
            pending = [t["description"] for t in parsed if t["status"] in ("pending", "in_progress")]
            if pending:
                return pending

    # 2. Check .torchlight/goal_spec.json
    if os.path.exists(alt_goal_path):
        try:
            with open(alt_goal_path, "r", encoding="utf-8") as f:
                gdata = json.load(f)
            raw_tasks = gdata.get("tasks", [])
            pending = []
            seen = set()
            for t in raw_tasks:
                st = t.get("status", "pending")
                if st in ("pending", "in_progress"):
                    desc = str(t.get("description") or t.get("id") or "Task")
                    norm = re.sub(r"\s+", " ", desc.lower()).strip()
                    if norm in seen:
                        continue
                    seen.add(norm)
                    pending.append(desc)
            if pending:
                return pending
        except Exception:  # noqa: BLE001, S110
            pass

    return []


from typing import Optional


def sync_workspace_tasks(
    project_root: str, default_goal_title: Optional[str] = None
) -> dict:
    """
    Synchronize workspace tasks across implementation_plan.md, .torchlight/tasks.md,
    and .torchlight/goal_spec.json. Ensures .torchlight/tasks.md and goal_spec.json
    are populated with checkboxes prior to and during code execution.
    """
    if not project_root or not os.path.exists(project_root):
        return {"synced": False, "task_count": 0}

    torchlight_dir = os.path.join(project_root, ".torchlight")
    os.makedirs(torchlight_dir, exist_ok=True)

    plan_path = os.path.join(project_root, "implementation_plan.md")
    alt_tasks_path = os.path.join(torchlight_dir, "tasks.md")
    alt_goal_path = os.path.join(torchlight_dir, "goal_spec.json")

    # Extract tasks from primary plan or existing tasks
    tasks = []
    goal_title = default_goal_title or os.path.basename(os.path.abspath(project_root))

    if os.path.exists(plan_path):
        tasks = parse_all_tasks_from_markdown(plan_path)
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("# "):
                        goal_title = line.lstrip("# ").strip()
                        break
        except Exception:
            pass
    elif os.path.exists(alt_tasks_path):
        tasks = parse_all_tasks_from_markdown(alt_tasks_path)
    elif os.path.exists(alt_goal_path):
        try:
            with open(alt_goal_path, "r", encoding="utf-8") as f:
                gdata = json.load(f)
            goal_title = gdata.get("title", goal_title)
            for t in gdata.get("tasks", []):
                st = t.get("status", "pending")
                desc = t.get("description") or t.get("id") or "Task"
                tasks.append({
                    "description": desc,
                    "status": "completed" if st in ("verified", "completed") else ("in_progress" if st in ("in_progress", "active") else "pending"),
                    "raw_state": "x" if st in ("verified", "completed") else ("/" if st in ("in_progress", "active") else " "),
                })
        except Exception:
            pass

    # If no tasks exist anywhere yet, initialize with default title task
    if not tasks:
        title_task = f"Execute goal: {goal_title}" if goal_title else "Initialize project & execute tasks"
        tasks = [{"description": title_task, "status": "pending", "raw_state": " "}]

    # Update .torchlight/tasks.md
    try:
        md_lines = [
            f"# Goal: {goal_title}",
            "## Tasks Breakdown\n",
        ]
        for t in tasks:
            box = "[x]" if t["status"] == "completed" else ("[/]" if t["status"] == "in_progress" else "[ ]")
            md_lines.append(f"- {box} {t['description']}")
        with open(alt_tasks_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines) + "\n")
    except Exception:
        pass

    # Update .torchlight/goal_spec.json
    try:
        json_tasks = []
        for i, t in enumerate(tasks):
            t_status = "completed" if t["status"] == "completed" else ("in_progress" if t["status"] == "in_progress" else "pending")
            json_tasks.append({
                "id": f"task_{i + 1:02d}",
                "description": t["description"],
                "status": t_status,
                "target_files": [],
                "depends_on": [],
            })
        goal_data = {
            "goal_id": f"goal_{re.sub(r'[^a-zA-Z0-9_]', '_', goal_title.lower())}",
            "title": goal_title,
            "description": goal_title,
            "tasks": json_tasks,
        }
        with open(alt_goal_path, "w", encoding="utf-8") as f:
            json.dump(goal_data, f, indent=2)
    except Exception:
        pass

    return {"synced": True, "task_count": len(tasks)}

