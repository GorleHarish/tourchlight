"""Task markdown parsing, goal spec bootstrapping, and checkbox synchronization."""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Optional

CHK_REGEX = re.compile(r"^(?:[-*+>]|\d+[\.\)])?\s*\[([ xX/\-v✓~>])\]\s*(.*)$")

EXECUTION_HEADER_REGEX = re.compile(
    r"^#{1,6}\s*.*(?:execution|steps|tasks|action|to[- ]?do|proposed changes|implementation steps|roadmap)",
    re.IGNORECASE,
)

_IGNORED_DIRS = (
    ".git",
    ".torchlight",
    "node_modules",
    "venv",
    "__pycache__",
    "site-packages",
    ".venv",
)


def _clean_task_text(text: str) -> str:
    """Normalize task text by stripping list bullets, numbers, markdown formatting, and extra spaces."""
    if not text:
        return ""
    cleaned = re.sub(r"^(?:\[T?\d+(?:\.\d+)*\]|\d+(?:\.\d+)*[\.\)]?|[-*+>])\s*", "", text.strip())
    cleaned = re.sub(r"\[[ xX/\-v✓~>]\]\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def _is_task_match(query_norm: str, task_norm: str) -> bool:
    """Strictly verify if query matches a task line without false-positive subset matches."""
    q_str = str(query_norm or "").strip()
    t_str = str(task_norm or "").strip()
    if not q_str or not t_str:
        return False

    # Check for direct integer, hierarchical index, or tag match (e.g., "1", "1.1", "task 1.1", "T1.1", "#1")
    q_match = re.match(r"^(?:task\s*#?|#|T|P)?(\d+(?:\.\d+)*)$", q_str, re.IGNORECASE)
    if q_match:
        target_id = q_match.group(1)
        t_num_match = re.match(r"^(?:\[T?(\d+(?:\.\d+)*)\]|(\d+(?:\.\d+)*)[\.\)]?)\s+", t_str)
        if t_num_match:
            found_id = t_num_match.group(1) or t_num_match.group(2)
            if found_id == target_id:
                return True

    # Check for exact task hash match (e.g. "task_1_1", "task_a1b2c3d4")
    if q_str.startswith("task_") and t_str.startswith("task_") and q_str == t_str:
        return True

    q_clean = _clean_task_text(q_str)
    t_clean = _clean_task_text(t_str)
    if not q_clean or not t_clean:
        return False
    if q_clean == t_clean:
        return True
    # If both strings are long enough, allow high-overlap prefix/substring match
    if len(q_clean) >= 8 and len(t_clean) >= 8:
        if q_clean in t_clean:
            return True
        if t_clean in q_clean and len(t_clean) >= 0.75 * len(q_clean):
            return True
    return False


def parse_all_tasks_from_markdown(source: str) -> list[dict]:
    """
    Parse all task items from markdown content or file path.
    Returns list of dicts: [{"description": str, "status": str, "raw_state": str, "task_number": Optional[str|int], "phase": Optional[str], "task_hash": str}]
    where status is 'completed', 'in_progress', 'skipped', or 'pending'.
    """
    import hashlib

    lines = []
    if os.path.exists(source):
        try:
            with open(source, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:  # noqa: BLE001, S110
            return []
    else:
        lines = source.splitlines()

    tasks = []
    seen = set()
    current_phase = None
    in_task_section = False

    # 1. First pass: Checkbox items (highest priority)
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            pm = re.search(r"\bPhase\s*(\d+(?:\.\d+)?|[IVXLCDM]+)?\s*[:\-–]?\s*([^\n]*)", stripped, re.IGNORECASE)
            if pm:
                current_phase = stripped.lstrip("#* ").strip()
            continue

        m = CHK_REGEX.match(stripped)
        if m:
            state, task_raw = m.group(1), m.group(2).strip()
            if task_raw.lower().startswith("progress:"):
                continue
            norm = _clean_task_text(task_raw)
            if norm in seen:
                continue
            seen.add(norm)
            if state in ("x", "X", "v", "✓"):
                status = "completed"
            elif state in ("/", "~", ">"):
                status = "in_progress"
            elif state == "-":
                status = "skipped"
            else:
                status = "pending"
            num_m = re.match(r"^(?:\[T?(\d+(?:\.\d+)*)\]|(\d+(?:\.\d+)*)[\.\)]?)\s+", task_raw)
            task_num_str = num_m.group(1) or num_m.group(2) if num_m else None
            try:
                task_number = int(task_num_str) if task_num_str and task_num_str.isdigit() else task_num_str
            except Exception:
                task_number = task_num_str

            raw_seed = f"{current_phase or ''}_{task_num_str or ''}_{norm}"
            task_hash = f"task_{hashlib.md5(raw_seed.encode('utf-8')).hexdigest()[:8]}"

            tasks.append(
                {
                    "description": task_raw,
                    "status": status,
                    "raw_state": state,
                    "task_number": task_number,
                    "phase": current_phase,
                    "task_hash": task_hash,
                }
            )

    # 2. Fallback pass: list items under explicit execution/task headers
    if not tasks:
        bullet_regex = re.compile(r"^(?:[-*+]|\d+(?:\.\d+)*[\.\)])\s+(.+)$")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                in_task_section = bool(EXECUTION_HEADER_REGEX.search(stripped))
                pm = re.search(r"\bPhase\s*(\d+(?:\.\d+)?|[IVXLCDM]+)?\s*[:\-–]?\s*([^\n]*)", stripped, re.IGNORECASE)
                if pm:
                    current_phase = stripped.lstrip("#* ").strip()
                continue
            if in_task_section:
                bm = bullet_regex.match(stripped)
                if bm:
                    task_raw = bm.group(1).strip()
                    if task_raw.lower().startswith("progress:") or len(task_raw) < 3:
                        continue
                    norm = _clean_task_text(task_raw)
                    if norm in seen:
                        continue
                    seen.add(norm)
                    num_m = re.match(r"^(?:\[T?(\d+(?:\.\d+)*)\]|(\d+(?:\.\d+)*)[\.\)]?)\s+", task_raw)
                    task_num_str = num_m.group(1) or num_m.group(2) if num_m else None
                    try:
                        task_number = int(task_num_str) if task_num_str and task_num_str.isdigit() else task_num_str
                    except Exception:
                        task_number = task_num_str

                    raw_seed = f"{current_phase or ''}_{task_num_str or ''}_{norm}"
                    task_hash = f"task_{hashlib.md5(raw_seed.encode('utf-8')).hexdigest()[:8]}"

                    tasks.append(
                        {
                            "description": task_raw,
                            "status": "pending",
                            "raw_state": " ",
                            "task_number": task_number,
                            "phase": current_phase,
                            "task_hash": task_hash,
                        }
                    )

    # 3. Last fallback pass: any numbered/bullet item if no execution headers were found anywhere
    if not tasks and not any(
        EXECUTION_HEADER_REGEX.search(l) for l in lines if l.strip().startswith("#")
    ):
        bullet_regex = re.compile(r"^(?:[-*+]|\d+[\.\)])\s+(.+)$")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            bm = bullet_regex.match(stripped)
            if bm:
                task_raw = bm.group(1).strip()
                if (
                    task_raw.lower().startswith("progress:")
                    or len(task_raw) < 3
                    or task_raw.startswith("`")
                ):
                    continue
                norm = _clean_task_text(task_raw)
                if norm in seen:
                    continue
                seen.add(norm)
                num_m = re.match(r"^(\d+)[\.\)]\s*", task_raw)
                task_number = int(num_m.group(1)) if num_m else None
                tasks.append(
                    {
                        "description": task_raw,
                        "status": "pending",
                        "raw_state": " ",
                        "task_number": task_number,
                    }
                )

    return tasks


def _load_goal_spec(goal_path: str) -> Optional[dict]:
    """Load goal_spec.json; returns None if missing or invalid."""
    if not os.path.exists(goal_path):
        return None
    try:
        with open(goal_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001, S110
        return None


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _stable_task_id(existing_ids) -> str:
    """Generate a collision-free stable task id (never index-based)."""
    ids = {str(i) for i in (existing_ids or []) if i}
    candidate = f"task_{uuid.uuid4().hex[:8]}"
    while candidate in ids:
        candidate = f"task_{uuid.uuid4().hex[:8]}"
    return candidate


def get_workspace_pending_tasks(project_root: str) -> list[str]:
    """
    Extract list of pending task descriptions from the workspace.

    Canonical source is .torchlight/goal_spec.json when present; markdown sources
    (implementation_plan.md, .torchlight/tasks.md) are used as fallback for
    plan-only projects. 'skipped' tasks are never reported as pending.
    """
    if not project_root or not os.path.exists(project_root):
        return []

    plan_path = os.path.join(project_root, "implementation_plan.md")
    alt_tasks_path = os.path.join(project_root, ".torchlight", "tasks.md")
    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")

    # 1. Canonical structured source: goal_spec.json
    gdata = _load_goal_spec(alt_goal_path)
    if gdata:
        try:
            from core.memory.task_graph import TaskDAG
            dag = TaskDAG.from_dict(gdata)
            ready_nodes = dag.get_ready_tasks()
            if ready_nodes:
                return [n.description for n in ready_nodes]
        except Exception:
            pass

        pending = []
        seen = set()
        for t in gdata.get("tasks", []):
            st = t.get("status", "pending")
            if st in ("pending", "in_progress"):
                desc = str(t.get("description") or t.get("id") or "Task")
                norm = _norm(desc)
                if norm in seen:
                    continue
                seen.add(norm)
                pending.append(desc)
        if pending:
            return pending

    # 2. Fallback: markdown sources (plan-only projects / not yet synced)
    for md_path in (plan_path, alt_tasks_path):
        if os.path.exists(md_path):
            parsed = parse_all_tasks_from_markdown(md_path)
            pending = [
                t["description"]
                for t in parsed
                if t["status"] in ("pending", "in_progress")
            ]
            if pending:
                return pending

    return []


def _patch_plan_checkbox(plan_path: str, query_norm: str, box_char: str) -> bool:
    """Rewrite the checkbox state for a matching task line in implementation_plan.md,
    preserving markdown structure/prose. Returns True if a line was patched."""
    if not os.path.exists(plan_path) or not query_norm:
        return False
    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        file_changed = False
        list_item_regex = re.compile(
            r"^(\s*(?:[-*+>]|\d+(?:\.\d+)*[\.\)]|\[T\d+(?:\.\d+)*\])\s*)(?:\[[ xX/\-v✓~]\]\s*)?(.*)$"
        )
        for line in lines:
            m_chk = CHK_REGEX.match(line.strip())
            if m_chk:
                task_raw = m_chk.group(2).strip()
                if _is_task_match(query_norm, task_raw):
                    updated_line = re.sub(
                        r"\[[ xX/\-v✓~]\]", f"[{box_char}]", line, count=1
                    )
                    new_lines.append(updated_line)
                    file_changed = True
                    continue
            else:
                m_list = list_item_regex.match(line)
                if m_list:
                    prefix, task_raw = m_list.group(1), m_list.group(2).strip()
                    if task_raw and _is_task_match(query_norm, task_raw):
                        updated_line = f"{prefix}[{box_char}] {task_raw}\n"
                        new_lines.append(updated_line)
                        file_changed = True
                        continue
            new_lines.append(line)

        if file_changed:
            with open(plan_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            return True
    except Exception:  # noqa: BLE001, S110
        pass
    return False


def _status_to_box(status: str) -> str:
    """Map canonical task status to markdown checkbox character."""
    s = (status or "").lower().strip()
    if s in ("completed", "verified"):
        return "x"
    if s in ("in_progress", "verifying"):
        return "/"
    if s in ("failed", "blocked"):
        return "-"
    if s == "skipped":
        return "~"
    return " "


def _render_plan_checkboxes(project_root: str, tasks: list[dict]) -> None:
    """
    Patch checkbox states in implementation_plan.md in-place from goal_spec statuses.
    Preserves headers, prose, ordering. Never re-derives goal_spec.
    """
    plan_path = os.path.join(project_root, "implementation_plan.md")
    if not os.path.exists(plan_path):
        return

    status_map = {}
    num_status_map = {}
    for idx, t in enumerate(tasks, start=1):
        desc = str(t.get("description") or t.get("id") or "")
        norm = _norm(desc)
        st = t.get("status", "pending")
        if norm:
            status_map[norm] = st
        t_num_match = re.match(r"^(?:\[T?(\d+(?:\.\d+)*)\]|(\d+(?:\.\d+)*)[\.\)]?)\s+", desc.strip())
        t_num = (t_num_match.group(1) or t_num_match.group(2)) if t_num_match else str(t.get("task_number") or idx)
        if t_num is not None:
            num_status_map[str(t_num)] = st

    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        new_lines = []
        file_changed = False
        for line in lines:
            m = CHK_REGEX.match(line.strip())
            if m:
                task_raw = m.group(2).strip()
                norm = _norm(task_raw)
                m_num = re.match(r"^(?:\[T?(\d+(?:\.\d+)*)\]|(\d+(?:\.\d+)*)[\.\)]?)\s+", task_raw)
                t_num = (m_num.group(1) or m_num.group(2)) if m_num else None
                st = status_map.get(norm) or (num_status_map.get(str(t_num)) if t_num is not None else None)
                if st:
                    box = _status_to_box(st)
                    updated_line = re.sub(r"\[[ xX/\-v✓~]\]", f"[{box}]", line, count=1)
                    if updated_line != line:
                        file_changed = True
                    new_lines.append(updated_line)
                    continue
            new_lines.append(line)
        if file_changed:
            with open(plan_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
    except Exception:  # noqa: BLE001, S110
        pass


VALID_TASK_STATUSES = {
    "pending",
    "blocked",
    "in_progress",
    "verifying",
    "failed",
    "completed",
    "verified",
    "skipped",
}


def insert_task_into_plan(
    project_root: str, description: str, status: str = "pending"
) -> bool:
    """
    Insert a new checkbox line for an added subtask into implementation_plan.md,
    placed in the plan's task/execution section. Returns True on success.
    """
    if not project_root or not description:
        return False
    plan_path = os.path.join(project_root, "implementation_plan.md")
    if not os.path.exists(plan_path):
        return False

    box = _status_to_box(status)
    line = f"- [{box}] {description}"

    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        insert_idx = None
        for i, l in enumerate(lines):
            stripped = l.strip()
            if stripped.startswith("#") and EXECUTION_HEADER_REGEX.search(stripped):
                insert_idx = i
                break

        if insert_idx is None:
            # No task section: append one at the end
            new_lines = lines
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] += "\n"
            new_lines.append(f"\n## Execution Steps\n{line}\n")
        else:
            # Find section end (next header or EOF), skipping trailing blanks
            end = insert_idx + 1
            while end < len(lines) and not lines[end].strip().startswith("#"):
                end += 1
            j = end
            while j > insert_idx + 1 and not lines[j - 1].strip():
                j -= 1
            new_lines = lines[:j] + [line + "\n"] + lines[j:]

        with open(plan_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    except Exception:  # noqa: BLE001, S110
        return False
