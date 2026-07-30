"""
Unified Task Helper Module for Torchlight.

Extracts pending tasks from implementation_plan.md, .torchlight/tasks.md,
or .torchlight/goal_spec.json across frontends and execution loops.
"""

import os
import re
import json
from typing import List

CHK_REGEX = re.compile(r"^(?:[-*+>]|\d+[\.\)])?\s*\[([ xX/\-v✓~])\]\s*(.*)$")

def get_workspace_pending_tasks(project_root: str) -> List[str]:
    """
    Extract list of pending task descriptions from the workspace.
    Priority order:
    1. implementation_plan.md
    2. .torchlight/tasks.md
    3. .torchlight/goal_spec.json

    Returns empty list if no active pending tasks exist.
    """
    if not project_root or not os.path.exists(project_root):
        return []

    plan_path = os.path.join(project_root, "implementation_plan.md")
    alt_tasks_path = os.path.join(project_root, ".torchlight", "tasks.md")
    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")

    # 1. Check implementation_plan.md or .torchlight/tasks.md (markdown format)
    target_md = None
    if os.path.exists(plan_path):
        target_md = plan_path
    elif os.path.exists(alt_tasks_path):
        target_md = alt_tasks_path

    if target_md:
        try:
            pending = []
            with open(target_md, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    m = CHK_REGEX.match(stripped)
                    if m:
                        state, task_raw = m.group(1), m.group(2).strip()
                        if task_raw.lower().startswith("progress:"):
                            continue
                        # ' ' is unchecked/pending, '/', '-', '~' are in-progress
                        if state in (" ", "/", "-", "~"):
                            pending.append(task_raw)
            return pending
        except Exception:
            pass

    # 2. Check .torchlight/goal_spec.json (JSON format)
    if os.path.exists(alt_goal_path):
        try:
            with open(alt_goal_path, "r", encoding="utf-8") as f:
                gdata = json.load(f)
            raw_tasks = gdata.get("tasks", [])
            pending = []
            for t in raw_tasks:
                st = t.get("status", "pending")
                if st in ("pending", "in_progress"):
                    desc = str(t.get("description") or t.get("id") or "Task")
                    pending.append(desc)
            return pending
        except Exception:
            pass

    return []
