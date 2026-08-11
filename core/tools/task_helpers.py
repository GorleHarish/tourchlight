"""
Unified Task Helper Module for Torchlight.

Canonical task store: .torchlight/goal_spec.json is the SINGLE source of truth for
task identity/status. implementation_plan.md and .torchlight/tasks.md are rendered
views derived from it. Status flows goal_spec.json -> markdown (render); markdown is
never used to re-derive goal_spec backwards (except first-time bootstrap).

The plan format contract is minimal and LLM-friendly:
  - Every actionable step MUST be a checkbox item: `- [ ]`, `* [ ]`, or `1. [ ]`
  - Everything else (headers, prose, bold, backticks, sub-bullets) is free-form
    and preserved verbatim.
  - Status is patched in-place by the machine; the LLM never regenerates the file
    just to tick boxes.
"""

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

# Marker tokens that indicate a file is a placeholder rather than real work.
_STUB_RE = re.compile(
    r"\b(todo|lorem ipsum|coming soon|placeholder|not implemented|not implemented yet|fixme|stub)\b",
    re.IGNORECASE,
)
_STUB_EXACT = {"pass", "...", "return none", "null", "none", "todo", "fixme", "stub"}


def _clean_task_text(text: str) -> str:
    """Normalize task text by stripping list bullets, numbers, markdown formatting, and extra spaces."""
    if not text:
        return ""
    cleaned = re.sub(r"^(?:\d+[\.\)]|[-*+>])\s*", "", text.strip())
    cleaned = re.sub(r"\[[ xX/\-v✓~>]\]\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def _is_task_match(query_norm: str, task_norm: str) -> bool:
    """Strictly verify if query matches a task line without false-positive subset matches."""
    q_clean = _clean_task_text(query_norm)
    t_clean = _clean_task_text(task_norm)
    if not q_clean or not t_clean:
        return False
    if q_clean == t_clean:
        return True
    if query_norm.lower().strip().startswith("task_"):
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
    Returns list of dicts: [{"description": str, "status": str, "raw_state": str}]
    where status is 'completed', 'in_progress', 'skipped', or 'pending'.
    """
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
    in_task_section = False

    # 1. First pass: Checkbox items (highest priority)
    for line in lines:
        stripped = line.strip()
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
            tasks.append(
                {
                    "description": task_raw,
                    "status": status,
                    "raw_state": state,
                }
            )

    # 2. Fallback pass: list items under explicit execution/task headers
    if not tasks:
        bullet_regex = re.compile(r"^(?:[-*+]|\d+[\.\)])\s+(.+)$")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                in_task_section = bool(EXECUTION_HEADER_REGEX.search(stripped))
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
                    tasks.append(
                        {
                            "description": task_raw,
                            "status": "pending",
                            "raw_state": " ",
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
                tasks.append(
                    {
                        "description": task_raw,
                        "status": "pending",
                        "raw_state": " ",
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
            r"^(\s*(?:[-*+>]|\d+[\.\)])\s*)(?:\[[ xX/\-v✓~]\]\s*)?(.*)$"
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


def _render_plan_checkboxes(project_root: str, tasks: list[dict]) -> None:
    """
    Patch checkbox states in implementation_plan.md in-place from goal_spec statuses.
    Preserves headers, prose, ordering. Never re-derives goal_spec.
    """
    plan_path = os.path.join(project_root, "implementation_plan.md")
    if not os.path.exists(plan_path):
        return

    status_map = {}
    for t in tasks:
        norm = _norm(t.get("description") or t.get("id") or "")
        if norm:
            status_map[norm] = t.get("status", "pending")

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
                st = status_map.get(norm)
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


def get_compact_task_matrix(project_root: str, budget=None) -> list[str]:
    """
    Generate an ultra-compact visual Task Matrix for LLM context injection.
    Adaptive: collapses to 1 line under context pressure (~25 tokens) and expands up to ~100 tokens
    when context headroom is ample.
    """
    if not project_root or not os.path.exists(project_root):
        return []

    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")
    gdata = _load_goal_spec(alt_goal_path)
    tasks = []
    if gdata and gdata.get("tasks"):
        for t in gdata.get("tasks", []):
            tasks.append({
                "id": t.get("id"),
                "description": str(t.get("description") or t.get("id") or "Task"),
                "status": str(t.get("status", "pending")),
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
                        "status": t.get("status", "pending"),
                        "depends_on": [],
                    })
                break

    if not tasks:
        return []

    total = len(tasks)
    done_count = sum(1 for t in tasks if t["status"] in ("completed", "verified", "done", "skipped"))
    percent = int((done_count / total) * 100) if total > 0 else 0
    filled = int((done_count / max(1, total)) * 10)
    bar = "█" * filled + "░" * (10 - filled)

    # Check budget pressure if budget object passed (compress to 1-line when context usage > 45%)
    is_tight = False
    if budget is not None:
        if hasattr(budget, "context_usage_ratio"):
            is_tight = budget.context_usage_ratio > 0.45
        elif hasattr(budget, "headroom_ratio"):
            is_tight = budget.headroom_ratio < 0.55
        elif hasattr(budget, "scratchpad_section_cap"):
            is_tight = budget.scratchpad_section_cap <= 3

    in_prog = [t for t in tasks if t["status"] in ("in_progress", "active", "verifying")]
    pending = [t for t in tasks if t["status"] == "pending"]

    if is_tight or total > 5:
        active_raw = _clean_task_text(in_prog[0]["description"]) if in_prog else (_clean_task_text(pending[0]["description"]) if pending else "None")
        next_raw = _clean_task_text(pending[0]["description"]) if (in_prog and pending) else (_clean_task_text(pending[1]["description"]) if len(pending) > 1 else "None")
        active_str = active_raw[:35] + "..." if len(active_raw) > 38 else active_raw
        next_str = next_raw[:35] + "..." if len(next_raw) > 38 else next_raw
        return [f"- Task Matrix: [{bar}] {done_count}/{total} Done ({percent}%) | Active: {active_str} | Next: {next_str}"]

    lines = [f"- Task Matrix: [{bar}] {done_count}/{total} Completed ({percent}%)"]
    section_cap = budget.scratchpad_section_cap if budget and hasattr(budget, "scratchpad_section_cap") else 3
    section_cap = min(section_cap, 3)  # Cap at max 3 shown tasks in context to prevent context budget tax

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
        lines.append(f"  • [{badge}] {desc}")

    return lines



def mark_task_status(
    project_root: str, task_id_or_desc: str, status: str = "completed"
) -> bool:
    """
    Mark a task as completed/in_progress/pending/skipped across all workspace task
    manifests. goal_spec.json is authoritative (exact id or exact normalized-desc
    match — no substring heuristics); implementation_plan.md and tasks.md are
    rendered views updated afterwards.
    """
    if not project_root or not os.path.exists(project_root) or not task_id_or_desc:
        return False

    box_char = _status_to_box(status)
    s_lower = (status or "").lower().strip()
    canon_status = (
        "verified"
        if s_lower in ("completed", "done", "verified")
        else "in_progress"
        if s_lower in ("in_progress", "active")
        else "skipped"
        if s_lower in ("skipped", "skip")
        else "pending"
    )
    updated_any = False

    # 1. Update .torchlight/goal_spec.json (canonical store)
    torchlight_dir = os.path.join(project_root, ".torchlight")
    alt_goal_path = os.path.join(torchlight_dir, "goal_spec.json")
    if os.path.exists(alt_goal_path):
        try:
            with open(alt_goal_path, "r", encoding="utf-8") as f:
                gdata = json.load(f)
            raw_tasks = gdata.get("tasks", [])
            query_l = str(task_id_or_desc).lower().strip()
            query_norm = _norm(query_l)
            goal_changed = False
            for t in raw_tasks:
                t_id = str(t.get("id") or "").lower().strip()
                t_norm = _norm(t.get("description") or "")
                if query_l == t_id or (query_norm and query_norm == t_norm):
                    t["status"] = canon_status
                    goal_changed = True
            if goal_changed:
                with open(alt_goal_path, "w", encoding="utf-8") as f:
                    json.dump(gdata, f, indent=2)
                updated_any = True
        except Exception:  # noqa: BLE001, S110
            pass

    # 2. Patch implementation_plan.md checkbox in-place (preserves prose)
    plan_path = os.path.join(project_root, "implementation_plan.md")
    if _patch_plan_checkbox(plan_path, task_id_or_desc, box_char):
        updated_any = True

    # 3. Reconcile tasks.md + re-render plan from canonical goal_spec
    try:
        sync_workspace_tasks(project_root)
    except Exception:  # noqa: BLE001, S110
        pass

    return updated_any


def mark_task_in_progress(project_root: str, task_id_or_desc: str) -> bool:
    """Mark a task as in_progress (started)."""
    return mark_task_status(project_root, task_id_or_desc, status="in_progress")


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


def _extract_referenced_files(text: str) -> list[str]:
    """Extract distinct code/markup filenames referenced in task description."""
    if not text:
        return []
    matches = re.findall(
        r"\b[\w\.-]+\.(?:py|js|ts|jsx|tsx|html|css|json|rs|go|sh|c|cpp|h|hpp|sql|yml|yaml|toml|rb|php|swift|kt)\b",
        text,
        re.IGNORECASE,
    )
    seen = set()
    res = []
    for m in matches:
        low = m.lower()
        if (
            low
            not in (
                "implementation_plan.md",
                "tasks.md",
                "goal_spec.json",
                "graph.json",
            )
            and low not in seen
        ):
            seen.add(low)
            res.append(m)
    return res


def _find_file_in_project(project_root: str, base: str) -> Optional[str]:
    """Locate a file by basename in the project, skipping junk/venv dirs."""
    if not base:
        return None
    direct = os.path.join(project_root, base)
    if os.path.isfile(direct):
        return direct
    try:
        for candidate in Path(project_root).rglob(base):
            if any(p in _IGNORED_DIRS for p in candidate.parts):
                continue
            return str(candidate)
    except Exception:  # noqa: BLE001, S110
        pass
    return None


def _file_looks_complete(path: Optional[str]) -> bool:
    """Heuristic: file exists, is non-empty, and is not an obvious placeholder/stub."""
    if not path or not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:  # noqa: BLE001, S110
        return False
    text = content.strip()
    if not text:
        return False
    if _norm(text) in _STUB_EXACT:
        return False
    if _STUB_RE.search(text[:2000]):
        return False
    return True


def verify_task_preflight(project_root: str, target_files: list[str]) -> tuple[bool, str]:
    """
    Zero-overhead in-memory syntax validation (<5ms).
    Checks Python files with ast.parse() and JSON files with json.loads().
    Returns (True, "Pre-flight syntax OK") or (False, "SyntaxError: ...").
    """
    if not project_root or not target_files:
        return True, "Pre-flight skipped (no target files)"

    import ast

    for tf in target_files:
        full_path = tf if os.path.isabs(tf) else _find_file_in_project(project_root, os.path.basename(tf))
        if not full_path or not os.path.isfile(full_path):
            continue

        base_low = os.path.basename(full_path).lower()
        if base_low.endswith(".py"):
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    source = f.read()
                ast.parse(source, filename=full_path)
            except SyntaxError as se:
                return False, f"SyntaxError in {base_low} line {se.lineno}: {se.msg}"
            except Exception as e:
                return False, f"Error reading {base_low}: {e}"

        elif base_low.endswith(".json"):
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    json.load(f)
            except json.JSONDecodeError as jde:
                return False, f"JSONDecodeError in {base_low} line {jde.lineno}: {jde.msg}"
            except Exception as e:
                return False, f"Error reading {base_low}: {e}"

    return True, "Pre-flight syntax OK"


def verify_task_targeted(project_root: str, task: dict, timeout: int = 5) -> tuple[bool, str]:
    """
    Surgical targeted task verification execution (<500ms wall-clock latency).
    1. Runs fast pre-flight syntax check (<5ms).
    2. Runs task verification_cmd or inferred targeted test file if available.
    Returns (is_verified: bool, details_or_traceback: str).
    """
    if not project_root or not task:
        return False, "Invalid task or project root"

    import subprocess
    from core.execution.feedback_loop import extract_surgical_traceback

    desc = str(task.get("description") or "")
    target_files = task.get("target_files") or _extract_referenced_files(desc)

    # 1. Zero-overhead pre-flight AST / JSON syntax check (<5ms)
    ok_syntax, msg_syntax = verify_task_preflight(project_root, target_files)
    if not ok_syntax:
        return False, msg_syntax

    # 2. Targeted test command execution
    vcmd = task.get("verification_cmd")
    if not vcmd:
        # Infer targeted test file from target_files or description
        for tf in target_files:
            bname = os.path.basename(tf)
            if bname.startswith("test_") or bname.endswith("_test.py"):
                vcmd = f"pytest {tf}"
                break

    if not vcmd:
        # No specific test command inferred, pre-flight syntax OK is sufficient
        return True, "Pre-flight syntax check passed"

    try:
        proc = subprocess.run(
            vcmd,
            shell=True,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode == 0:
            return True, "Targeted verification passed"
        
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        tb = extract_surgical_traceback(output, command=vcmd, max_lines=15)
        return False, tb or output[:300]
    except subprocess.TimeoutExpired:
        return False, f"Targeted verification timed out ({timeout}s)"
    except Exception as e:
        return False, f"Verification command execution error: {e}"


def auto_mark_task_completed_by_file(
    project_root: str, file_path: str, verified: bool = False
) -> bool:
    """
    Auto-detect open tasks that correspond to a written/edited file and mark their
    status. Matching is strict:
      - goal_spec `target_files` (exact basename), OR a whole-word filename token
        in the task description (word-boundary, not substring).
    Completion requires verification:
      - single-file task: file exists, non-empty, non-stub AND `verified` -> completed,
        otherwise in_progress.
      - multi-file task: completed only when all referenced files exist AND `verified`;
        in_progress when any exist; left pending otherwise.
    """
    if not project_root or not file_path:
        return False

    base_name = os.path.basename(file_path).strip()
    if not base_name or base_name.lower() in (
        "implementation_plan.md",
        "tasks.md",
        "goal_spec.json",
        "graph.json",
    ):
        return False

    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")
    plan_path = os.path.join(project_root, "implementation_plan.md")

    word_re = re.compile(
        rf"(?<![\.\w-]){re.escape(base_name)}(?![\.\w-])", re.IGNORECASE
    )
    candidates = []

    gdata = _load_goal_spec(alt_goal_path)
    if gdata:
        for t in gdata.get("tasks", []):
            if t.get("status", "pending") not in ("pending", "in_progress"):
                continue
            desc = str(t.get("description") or "")
            t_files = [os.path.basename(f).lower() for f in t.get("target_files", [])]
            if base_name.lower() in t_files or word_re.search(desc):
                candidates.append(t)
    else:
        if os.path.exists(plan_path):
            parsed = parse_all_tasks_from_markdown(plan_path)
            for t in parsed:
                if t["status"] not in ("pending", "in_progress"):
                    continue
                if word_re.search(t["description"]):
                    candidates.append(
                        {
                            "id": None,
                            "description": t["description"],
                            "target_files": _extract_referenced_files(t["description"]),
                            "status": t["status"],
                        }
                    )

    if not candidates:
        return False

    # Count how many tasks are currently in_progress across the whole project
    already_in_progress = any(
        c.get("status") == "in_progress" for c in candidates
    )

    marked_any = False
    for cand in candidates:
        desc = str(cand.get("description") or "")
        target_files = cand.get("target_files") or _extract_referenced_files(desc)
        refs = [os.path.basename(rf).lower() for rf in target_files]

        if len(refs) > 1:
            existing = [rf for rf in refs if _find_file_in_project(project_root, rf)]
            if len(existing) == len(refs) and verified:
                ok_ver, msg_ver = verify_task_targeted(project_root, cand)
                target_status = "completed" if ok_ver else "failed"
            elif existing:
                target_status = "in_progress"
            else:
                continue
        else:
            ref = refs[0] if refs else base_name.lower()
            full_path = _find_file_in_project(project_root, ref)
            if verified and full_path and _file_looks_complete(full_path):
                ok_ver, msg_ver = verify_task_targeted(project_root, cand)
                target_status = "completed" if ok_ver else "failed"
            else:
                target_status = "in_progress"

        if target_status == "in_progress" and already_in_progress and cand.get("status") != "in_progress":
            # Preserve strict serial execution: do not flip multiple pending tasks to in_progress at once
            continue

        if cand.get("status") == target_status:
            continue
        if mark_task_status(
            project_root, desc or cand.get("id", ""), status=target_status
        ):
            marked_any = True
            if target_status == "in_progress":
                already_in_progress = True

    return marked_any


def sync_workspace_tasks(
    project_root: str, default_goal_title: Optional[str] = None
) -> dict:
    """
    Synchronize the canonical goal_spec.json with the plan/task markdown views.

    - goal_spec.json is authoritative; implementation_plan.md / tasks.md are
      rendered views derived from it (never the reverse, except first bootstrap).
    - Merge, never rebuild: existing task fields (target_files, depends_on,
      outputs_summary, attempts, failure_reasons, completed_at) and stable ids are
      preserved; new plan tasks are added with fresh stable ids.
    - implementation_plan.md checkboxes are patched in-place, preserving prose.
    """
    if not project_root or not os.path.exists(project_root):
        return {"synced": False, "task_count": 0}

    torchlight_dir = os.path.join(project_root, ".torchlight")
    os.makedirs(torchlight_dir, exist_ok=True)

    plan_path = os.path.join(project_root, "implementation_plan.md")
    alt_tasks_path = os.path.join(torchlight_dir, "tasks.md")
    alt_goal_path = os.path.join(torchlight_dir, "goal_spec.json")

    gdata = _load_goal_spec(alt_goal_path)

    # --- Determine goal title -----------------------------------------------
    goal_title = None
    if gdata:
        goal_title = gdata.get("title")
    if not goal_title and default_goal_title:
        goal_title = default_goal_title
    if os.path.exists(plan_path):
        try:
            with open(plan_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("# "):
                        goal_title = line.lstrip("# ").strip()
                        break
        except Exception:  # noqa: BLE001, S110
            pass
    if not goal_title:
        goal_title = os.path.basename(os.path.abspath(project_root))

    # --- Load canonical existing tasks --------------------------------------
    existing = {}  # norm desc -> task dict
    if gdata and isinstance(gdata.get("tasks"), list):
        for t in gdata["tasks"]:
            norm = _norm(t.get("description") or t.get("id") or "")
            if norm:
                existing[norm] = t

    # --- Gather plan tasks (task list comes from the plan's checkbox items) --
    plan_tasks = []
    if os.path.exists(plan_path):
        plan_tasks = parse_all_tasks_from_markdown(plan_path)

    if not plan_tasks and not existing:
        title_task = (
            f"Execute goal: {goal_title}"
            if goal_title
            else "Initialize project & execute tasks"
        )
        plan_tasks = [
            {"description": title_task, "status": "pending", "raw_state": " "}
        ]
    elif not plan_tasks:
        # goal_spec exists with tasks but the plan has no checkbox items yet —
        # don't clobber the canonical store with a default task.
        plan_tasks = []

    if plan_path and os.path.exists(plan_path) and not plan_tasks and not existing:
        print(
            f"[task_helpers] WARNING: 0 tasks detected in {plan_path}. "
            "Ensure actionable steps are checkbox items like '- [ ] Task'.",
            file=sys.stderr,
        )

    # --- Merge: plan order first, then goal_spec-only tasks ------------------
    merged = []
    seen = set()
    all_ids = [str(t.get("id") or "") for t in existing.values()]
    for pt in plan_tasks:
        norm = _norm(pt["description"])
        if norm in seen:
            continue
        seen.add(norm)
        if norm in existing:
            merged.append(dict(existing[norm]))
        else:
            new_task = {
                "id": _stable_task_id(all_ids),
                "description": pt["description"],
                "status": (
                    "verified"
                    if pt["status"] == "completed"
                    else "in_progress"
                    if pt["status"] == "in_progress"
                    else "skipped"
                    if pt["status"] == "skipped"
                    else "pending"
                ),
                "target_files": [],
                "depends_on": [],
                "outputs_summary": None,
                "attempts": 0,
                "max_attempts": 3,
                "failure_reasons": [],
                "completed_at": None,
            }
            all_ids.append(new_task["id"])
            merged.append(new_task)
    for norm, t in existing.items():
        if norm not in seen:
            merged.append(dict(t))

    # --- Persist goal_spec.json (canonical) ----------------------------------
    goal_data = dict(gdata) if gdata else {}
    goal_data.update(
        {
            "goal_id": gdata.get("goal_id")
            if gdata
            else f"goal_{re.sub(r'[^a-zA-Z0-9_]', '_', goal_title.lower())}",
            "title": goal_title,
            "description": gdata.get("description") if gdata else goal_title,
            "tasks": merged,
        }
    )
    if "created_at" not in goal_data:
        goal_data["created_at"] = None
    goal_data["updated_at"] = None
    try:
        with open(alt_goal_path, "w", encoding="utf-8") as f:
            json.dump(goal_data, f, indent=2)
    except Exception:  # noqa: BLE001, S110
        pass

    # --- Render .torchlight/tasks.md view ------------------------------------
    try:
        md_lines = [
            f"# Goal: {goal_title}",
            "## Tasks Breakdown\n",
        ]
        for t in merged:
            box = _status_to_box(t.get("status", "pending"))
            md_lines.append(f"- [{box}] {t.get('description') or t.get('id')}")
        with open(alt_tasks_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines) + "\n")
    except Exception:  # noqa: BLE001, S110
        pass

    # --- Render implementation_plan.md checkboxes in-place -------------------
    _render_plan_checkboxes(project_root, merged)

    return {"synced": True, "task_count": len(merged)}


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
    result["completed_count"] = sum(1 for t in tasks if t["status"] in ("completed", "skipped"))

    # Determine current active task & next task
    in_prog = [t for t in tasks if t["status"] == "in_progress"]
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
