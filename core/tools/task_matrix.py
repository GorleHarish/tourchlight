"""Compact task matrix formatting, status badges, and workspace task summaries."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional, Any

from core.memory.budget import ContextBudget
from core.tools.task_parser import (
    VALID_TASK_STATUSES,
    _load_goal_spec,
    _clean_task_text,
    _is_task_match,
    parse_all_tasks_from_markdown,
    get_workspace_pending_tasks,
)


def validate_task_transition(current_status: str, target_status: str) -> bool:
    """Validate if a task transition is valid according to the status state machine."""
    curr = (current_status or "pending").lower().strip()
    targ = (target_status or "pending").lower().strip()
    if targ not in VALID_TASK_STATUSES:
        return False
    if curr == targ:
        return True
    # Disallow un-skipping or un-completing verified tasks back to blocked directly without going through pending/in_progress
    if curr in ("completed", "verified") and targ in ("blocked",):
        return False
    return True


def _status_to_box(status: str) -> str:
    s = (status or "").lower().strip()
    if s in ("completed", "verified", "done"):
        return "x"
    if s in ("in_progress", "active"):
        return "/"
    if s in ("verifying",):
        return "v"
    if s in ("blocked",):
        return "~"
    if s in ("failed",):
        return "!"
    if s in ("skipped", "skip"):
        return "-"
    return " "


def _status_badge(status: str) -> str:
    s = (status or "").lower().strip()
    if s in ("completed", "verified", "done"):
        return "✅ COMPLETED"
    if s in ("in_progress", "active"):
        return "⏳ IN_PROGRESS"
    if s in ("verifying",):
        return "🔍 VERIFYING"
    if s in ("blocked",):
        return "🔒 BLOCKED"
    if s in ("failed",):
        return "❌ FAILED"
    if s in ("skipped", "skip"):
        return "⏭️ SKIPPED"
    return "⚪ PENDING"


_COMPACT_MATRIX_CACHE: dict = {}


def get_compact_task_matrix(project_root: str, budget=None) -> list[str]:
    """
    Generate an ultra-compact visual Task Matrix for LLM context injection.
    Adaptive: collapses to 1 line under context pressure (~25 tokens) and expands up to ~100 tokens
    when context headroom is ample.
    """
    if not project_root or not os.path.exists(project_root):
        return []

    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")
    plan_path = os.path.join(project_root, "implementation_plan.md")
    alt_tasks_path = os.path.join(project_root, ".torchlight", "tasks.md")

    # Fast-path: Check file mtimes to avoid reading/parsing disk files when unchanged
    max_mtime = 0.0
    for p in (alt_goal_path, plan_path, alt_tasks_path):
        try:
            if os.path.exists(p):
                max_mtime = max(max_mtime, os.path.getmtime(p))
        except OSError:
            pass

    # Check budget pressure if budget object passed (compress to 1-line when context usage > 45%)
    is_tight = False
    section_cap = 3
    if budget is not None:
        if hasattr(budget, "context_usage_ratio"):
            is_tight = budget.context_usage_ratio > 0.45
        elif hasattr(budget, "headroom_ratio"):
            is_tight = budget.headroom_ratio < 0.55
        elif hasattr(budget, "scratchpad_section_cap"):
            is_tight = budget.scratchpad_section_cap <= 3
        if hasattr(budget, "scratchpad_section_cap"):
            section_cap = min(budget.scratchpad_section_cap, 3)

    cache_key = (project_root, is_tight, section_cap)
    if cache_key in _COMPACT_MATRIX_CACHE:
        cached_mtime, cached_res = _COMPACT_MATRIX_CACHE[cache_key]
        if cached_mtime == max_mtime:
            return cached_res

    gdata = _load_goal_spec(alt_goal_path)
    tasks = []
    if gdata and gdata.get("tasks"):
        for t in gdata.get("tasks", []):
            tasks.append({
                "id": t.get("id"),
                "description": str(t.get("description") or t.get("id") or "Task"),
                "status": str(t.get("status", "pending")),
                "depends_on": t.get("depends_on", []),
                "phase": t.get("phase"),
                "task_number": t.get("task_number"),
                "task_hash": t.get("task_hash"),
            })
    else:
        for md_name in ("implementation_plan.md", os.path.join(".torchlight", "tasks.md")):
            md_path = os.path.join(project_root, md_name)
            if os.path.exists(md_path):
                parsed = parse_all_tasks_from_markdown(md_path)
                for t in parsed:
                    tasks.append({
                        "id": t.get("task_hash"),
                        "description": t.get("description", "Task"),
                        "status": t.get("status", "pending"),
                        "depends_on": [],
                        "phase": t.get("phase"),
                        "task_number": t.get("task_number"),
                        "task_hash": t.get("task_hash"),
                    })
                break

    if not tasks:
        _COMPACT_MATRIX_CACHE[cache_key] = (max_mtime, [])
        return []

    total = len(tasks)
    done_count = sum(1 for t in tasks if t["status"] in ("completed", "verified", "done", "skipped"))
    percent = int((done_count / total) * 100) if total > 0 else 0
    filled = int((done_count / max(1, total)) * 10)
    bar = "█" * filled + "░" * (10 - filled)

    in_prog = [t for t in tasks if t["status"] in ("in_progress", "active", "verifying")]
    pending = [t for t in tasks if t["status"] == "pending"]

    active_phase = in_prog[0].get("phase") if in_prog else (pending[0].get("phase") if pending else None)
    phase_hdr = f" | {active_phase}" if active_phase else ""

    if is_tight or total > 5:
        active_raw = _clean_task_text(in_prog[0]["description"]) if in_prog else (_clean_task_text(pending[0]["description"]) if pending else "None")
        next_raw = _clean_task_text(pending[0]["description"]) if (in_prog and pending) else (_clean_task_text(pending[1]["description"]) if len(pending) > 1 else "None")
        active_str = active_raw[:35] + "..." if len(active_raw) > 38 else active_raw
        next_str = next_raw[:35] + "..." if len(next_raw) > 38 else next_raw
        res_lines = [f"- Task Matrix: [{bar}] {done_count}/{total} Done ({percent}%){phase_hdr} | Active: {active_str} | Next: {next_str}"]
        _COMPACT_MATRIX_CACHE[cache_key] = (max_mtime, res_lines)
        return res_lines

    lines = [f"- Task Matrix: [{bar}] {done_count}/{total} Completed ({percent}%){phase_hdr}"]

    # Priority: active/verifying task -> next pending tasks -> blocked/failed tasks
    shown_tasks = []
    for t in in_prog:
        if len(shown_tasks) < section_cap:
            shown_tasks.append(t)
    for t in pending:
        if len(shown_tasks) < section_cap:
            shown_tasks.append(t)
    for t in tasks:
        if t not in shown_tasks and len(shown_tasks) < section_cap:
            shown_tasks.append(t)

    for t in shown_tasks:
        desc = _clean_task_text(t["description"])
        if len(desc) > 38:
            desc = desc[:35] + "..."
        badge = _status_badge(t["status"])
        num_prefix = f"#{t['task_number']} " if t.get("task_number") else ""
        lines.append(f"  • [{badge}] {num_prefix}{desc}")

    _COMPACT_MATRIX_CACHE[cache_key] = (max_mtime, lines)
    return lines


def get_active_task_description(project_root: str) -> Optional[str]:
    """Retrieve the title/description of the current active (in_progress) task, or first pending task."""
    if not project_root or not os.path.exists(project_root):
        return None

    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")
    gdata = _load_goal_spec(alt_goal_path)
    if gdata:
        for t in gdata.get("tasks", []):
            if t.get("status") == "in_progress":
                return str(t.get("description") or t.get("id"))
        for t in gdata.get("tasks", []):
            if t.get("status") == "pending":
                return str(t.get("description") or t.get("id"))

    for md_name in ("implementation_plan.md", os.path.join(".torchlight", "tasks.md")):
        md_path = os.path.join(project_root, md_name)
        if os.path.exists(md_path):
            parsed = parse_all_tasks_from_markdown(md_path)
            for t in parsed:
                if t.get("status") == "in_progress":
                    return t.get("description")
            for t in parsed:
                if t.get("status") == "pending":
                    return t.get("description")
    return None


_TASK_SUMMARY_CACHE: dict = {}


def get_workspace_task_status_summary(project_root: str) -> dict:
    """
    Extract structured task progress status:
    - current_task: {"description": str, "status": str} or None
    - next_task: {"description": str, "status": str} or None
    - completed_count: int
    - total_count: int
    - remaining_tasks: list[str]
    """
    result = {
        "current_task": None,
        "next_task": None,
        "completed_count": 0,
        "total_count": 0,
        "remaining_tasks": [],
    }
    if not project_root or not os.path.exists(project_root):
        return result

    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")
    plan_path = os.path.join(project_root, "implementation_plan.md")
    alt_tasks_path = os.path.join(project_root, ".torchlight", "tasks.md")

    # Fast-path: Check file mtimes to avoid reading/parsing disk files when unchanged
    max_mtime = 0.0
    for p in (alt_goal_path, plan_path, alt_tasks_path):
        try:
            if os.path.exists(p):
                max_mtime = max(max_mtime, os.path.getmtime(p))
        except OSError:
            pass

    if project_root in _TASK_SUMMARY_CACHE:
        cached_mtime, cached_res = _TASK_SUMMARY_CACHE[project_root]
        if cached_mtime == max_mtime:
            return cached_res

    tasks = []
    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")
    gdata = _load_goal_spec(alt_goal_path)
    if gdata and gdata.get("tasks"):
        for t in gdata.get("tasks", []):
            tasks.append({
                "description": str(t.get("description") or t.get("id") or "Task"),
                "status": str(t.get("status", "pending")),
            })
    else:
        for md_name in ("implementation_plan.md", os.path.join(".torchlight", "tasks.md")):
            md_path = os.path.join(project_root, md_name)
            if os.path.exists(md_path):
                parsed = parse_all_tasks_from_markdown(md_path)
                if parsed:
                    for t in parsed:
                        tasks.append({
                            "description": t.get("description", "Task"),
                            "status": t.get("status", "pending"),
                        })
                    break

    if not tasks:
        return result

    result["total_count"] = len(tasks)
    result["completed_count"] = sum(
        1 for t in tasks if t["status"] in ("completed", "verified", "done", "skipped")
    )

    # Determine current active task & next task
    in_prog = [
        t for t in tasks if t["status"] in ("in_progress", "active", "verifying")
    ]
    pending = [t for t in tasks if t["status"] == "pending"]

    if in_prog:
        result["current_task"] = in_prog[0]
        if pending:
            result["next_task"] = pending[0]
    elif pending:
        result["current_task"] = pending[0]
        if len(pending) > 1:
            result["next_task"] = pending[1]

    current_desc = result["current_task"]["description"] if result["current_task"] else None
    result["remaining_tasks"] = [t["description"] for t in pending if t["description"] != current_desc]
    _TASK_SUMMARY_CACHE[project_root] = (max_mtime, result)
    return result
