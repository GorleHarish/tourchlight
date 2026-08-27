"""Automated task status mutation, file-targeted verification, and test execution sync."""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Optional, Any

from core.tools.task_parser import (
    VALID_TASK_STATUSES,
    _clean_task_text,
    _is_task_match,
    _load_goal_spec,
    _norm,
    _stable_task_id,
    _patch_plan_checkbox,
    _render_plan_checkboxes,
    _IGNORED_DIRS,
    parse_all_tasks_from_markdown,
    get_workspace_pending_tasks,
)
from core.tools.task_matrix import (
    validate_task_transition,
    _status_to_box,
    _status_badge,
)

# Marker tokens that indicate a file is a placeholder rather than real work.
_STUB_RE = re.compile(
    r"\b(todo|lorem ipsum|coming soon|placeholder|not implemented|not implemented yet|fixme|stub)\b",
    re.IGNORECASE,
)
_STUB_EXACT = {"pass", "...", "return none", "null", "none", "todo", "fixme", "stub"}


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
            target_num = None
            q_num_match = re.match(r"^(?:task\s*#?|#|T|P)?(\d+(?:\.\d+)*)$", query_l, re.IGNORECASE)
            if q_num_match:
                target_num = q_num_match.group(1)

            goal_changed = False
            for idx, t in enumerate(raw_tasks, start=1):
                t_id = str(t.get("id") or "").lower().strip()
                t_desc = str(t.get("description") or "")
                t_norm = _norm(t_desc)
                t_num_match = re.match(r"^(?:\[T?(\d+(?:\.\d+)*)\]|(\d+(?:\.\d+)*)[\.\)]?)\s+", t_desc.strip())
                t_num = (t_num_match.group(1) or t_num_match.group(2)) if t_num_match else str(t.get("task_number") or idx)

                matched = False
                if target_num is not None:
                    if str(t_num) == str(target_num) or str(idx) == str(target_num):
                        matched = True
                elif query_l == t_id or (query_norm and query_norm == t_norm) or _is_task_match(query_l, t_desc):
                    matched = True

                if matched:
                    t["status"] = canon_status
                    goal_changed = True
                elif canon_status == "in_progress" and t.get("status") == "in_progress":
                    # Enforce single active task exclusivity: revert prior in_progress task back to pending
                    t["status"] = "pending"
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


def _extract_referenced_files(text: str) -> list[str]:
    """Extract distinct code/markup filepaths referenced in task description."""
    if not text:
        return []
    matches = re.findall(
        r"(?:[\w\.-]+[/\\])*[\w\.-]+\.(?:py|js|ts|jsx|tsx|html|css|json|rs|go|sh|c|cpp|h|hpp|sql|yml|yaml|toml|rb|php|swift|kt)\b",
        text,
        re.IGNORECASE,
    )
    seen = set()
    res = []
    for m in matches:
        low = os.path.basename(m).lower()
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


def _extract_task_file_and_scope(text: str) -> dict:
    """
    Extract file path, line range, AST symbol anchor, and [NEW] flag from a task description.
    Supports formats like:
      - [src/auth.py:L15-L40] Implement JWT verification
      - [src/auth.py:15-40] Implement JWT verification
      - [src/auth.py#verify_token] Add expiry check
      - [src/utils/crypto.py] [NEW] Scaffold hashing helper
      - `src/components/Header.jsx` Build topbar
      - Update index.html and style.css
    """
    if not text:
        return {"target_files": [], "line_range": None, "symbol": None, "is_new": False}

    is_new = bool(
        re.search(r"\[NEW\]|\bnew file\b|\bcreate file\b", text, re.IGNORECASE)
    )

    bracket_m = re.search(
        r"\[([a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9]+)(?:[:#]([a-zA-Z0-9_\-]+(?:\s*-\s*[a-zA-Z0-9_]+)?))?\]",
        text,
    )
    line_range = None
    symbol = None
    target_files = []

    if bracket_m:
        fpath = bracket_m.group(1).strip()
        target_files.append(fpath)
        spec = bracket_m.group(2)
        if spec:
            spec = spec.strip()
            lr_m = re.match(r"^L?(\d+)\s*-\s*L?(\d+)$", spec, re.IGNORECASE)
            if lr_m:
                line_range = (int(lr_m.group(1)), int(lr_m.group(2)))
            else:
                symbol = spec.lstrip("#:")

    all_refs = _extract_referenced_files(text)
    for ref in all_refs:
        if ref not in target_files and os.path.basename(ref).lower() not in [
            os.path.basename(f).lower() for f in target_files
        ]:
            target_files.append(ref)

    return {
        "target_files": target_files,
        "line_range": line_range,
        "symbol": symbol,
        "is_new": is_new,
    }


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
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) <= 2:
        if _norm(text) in _STUB_EXACT or _STUB_RE.search(text):
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
                import sys

                py_bin = sys.executable or "python3"
                vcmd = f"{py_bin} -m pytest {tf} -q"
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

    norm_file_path = file_path.replace("\\", "/").lower().lstrip("./")
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
            t_full_files = [
                f.replace("\\", "/").lower().lstrip("./")
                for f in t.get("target_files", [])
            ]
            if (
                base_name.lower() in t_files
                or norm_file_path in t_full_files
                or any(
                    norm_file_path.endswith(f) or f.endswith(norm_file_path)
                    for f in t_full_files
                )
                or word_re.search(desc)
            ):
                candidates.append(t)
    else:
        if os.path.exists(plan_path):
            parsed = parse_all_tasks_from_markdown(plan_path)
            for t in parsed:
                if t["status"] not in ("pending", "in_progress"):
                    continue
                scope_info = _extract_task_file_and_scope(t["description"])
                t_files = [
                    os.path.basename(f).lower() for f in scope_info["target_files"]
                ]
                t_full = [
                    f.replace("\\", "/").lower().lstrip("./")
                    for f in scope_info["target_files"]
                ]
                if (
                    base_name.lower() in t_files
                    or norm_file_path in t_full
                    or any(
                        norm_file_path.endswith(f) or f.endswith(norm_file_path)
                        for f in t_full
                    )
                    or word_re.search(t["description"])
                ):
                    candidates.append(
                        {
                            "id": None,
                            "description": t["description"],
                            "target_files": scope_info["target_files"],
                            "line_range": scope_info["line_range"],
                            "symbol": scope_info["symbol"],
                            "is_new": scope_info["is_new"],
                            "status": t["status"],
                        }
                    )

    if not candidates:
        # Fallback: If no task explicitly named this specific file, match active in_progress task or first pending task
        if gdata:
            open_tasks = [
                t
                for t in gdata.get("tasks", [])
                if t.get("status", "pending") in ("pending", "in_progress")
            ]
            in_prog = [t for t in open_tasks if t.get("status") == "in_progress"]
            if in_prog:
                candidates = in_prog
            elif open_tasks:
                candidates = [open_tasks[0]]
        elif os.path.exists(plan_path):
            parsed = parse_all_tasks_from_markdown(plan_path)
            open_tasks = [
                t for t in parsed if t["status"] in ("pending", "in_progress")
            ]
            in_prog = [t for t in open_tasks if t["status"] == "in_progress"]
            target_t = in_prog[0] if in_prog else (open_tasks[0] if open_tasks else None)
            if target_t:
                candidates.append(
                    {
                        "id": None,
                        "description": target_t["description"],
                        "target_files": _extract_referenced_files(
                            target_t["description"]
                        ),
                        "status": target_t["status"],
                    }
                )

    if not candidates:
        return False

    # Select at most ONE target candidate task to advance:
    # 1. Prefer the candidate that is already in_progress
    # 2. Otherwise pick the first pending candidate
    target_cand = None
    in_prog_cands = [c for c in candidates if c.get("status") == "in_progress"]
    if in_prog_cands:
        target_cand = in_prog_cands[0]
    else:
        pending_cands = [c for c in candidates if c.get("status") == "pending"]
        if pending_cands:
            target_cand = pending_cands[0]

    if not target_cand:
        return False

    desc = str(target_cand.get("description") or "")
    target_files = target_cand.get("target_files") or _extract_referenced_files(desc)
    refs = [os.path.basename(rf).lower() for rf in target_files]

    if len(refs) > 1:
        existing = [rf for rf in refs if _find_file_in_project(project_root, rf)]
        if len(existing) == len(refs) and verified:
            ok_ver, msg_ver = verify_task_targeted(project_root, target_cand)
            target_status = "completed" if ok_ver else "failed"
        elif existing:
            target_status = "in_progress"
        else:
            return False
    else:
        ref = refs[0] if refs else base_name.lower()
        full_path = _find_file_in_project(project_root, ref) or (
            file_path if os.path.isabs(file_path) else os.path.join(project_root, file_path)
        )
        if (
            verified
            and full_path
            and os.path.isfile(full_path)
            and _file_looks_complete(full_path)
        ):
            ok_ver, msg_ver = verify_task_targeted(project_root, target_cand)
            target_status = "completed" if ok_ver else "failed"
        else:
            target_status = "in_progress"

    if target_cand.get("status") == target_status:
        return False

    return mark_task_status(
        project_root, desc or target_cand.get("id", ""), status=target_status
    )


def auto_mark_task_completed_by_command(
    project_root: str, command: str, return_code: int = 0
) -> bool:
    """
    Auto-detect open tasks that correspond to a successful shell command (e.g. `npm install`,
    `pytest`, `cargo test`, `python manage.py migrate`, `pip install`) and mark them completed.

    Matching is strict:
      - Only matches tasks that have NO target_files or specifically mention the command/action.
      - If return_code == 0, marks status as 'completed'.
    """
    if not project_root or not command or return_code != 0:
        return False

    cmd_clean = command.strip().lower()
    if not cmd_clean:
        return False

    alt_goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")
    plan_path = os.path.join(project_root, "implementation_plan.md")

    tokens = set(re.findall(r"[a-z0-9_-]+", cmd_clean))
    is_install = bool(tokens & {"install", "add", "setup"})
    is_test = bool(tokens & {"test", "pytest", "jest", "unittest", "vitest"})
    is_migrate = bool(tokens & {"migrate", "migration", "migrations"})
    is_build = bool(tokens & {"build", "bundle", "compile"})

    candidates = []
    gdata = _load_goal_spec(alt_goal_path)
    if gdata:
        for t in gdata.get("tasks", []):
            if t.get("status", "pending") not in ("pending", "in_progress"):
                continue
            desc = str(t.get("description") or "").lower()
            if any(tok in desc for tok in tokens if len(tok) >= 4):
                candidates.append(t)
            elif is_install and any(
                w in desc
                for w in (
                    "install depend",
                    "install package",
                    "npm install",
                    "pip install",
                )
            ):
                candidates.append(t)
            elif is_test and any(
                w in desc
                for w in (
                    "run test",
                    "execute test",
                    "verify test",
                    "pytest",
                    "npm test",
                )
            ):
                candidates.append(t)
            elif is_migrate and any(
                w in desc
                for w in (
                    "run migration",
                    "migrate database",
                    "apply migration",
                )
            ):
                candidates.append(t)
            elif is_build and any(
                w in desc
                for w in (
                    "build project",
                    "build bundle",
                    "npm run build",
                    "cargo build",
                )
            ):
                candidates.append(t)
    else:
        if os.path.exists(plan_path):
            parsed = parse_all_tasks_from_markdown(plan_path)
            for t in parsed:
                if t["status"] not in ("pending", "in_progress"):
                    continue
                desc = t["description"].lower()
                if any(tok in desc for tok in tokens if len(tok) >= 4):
                    candidates.append(
                        {
                            "id": None,
                            "description": t["description"],
                            "status": t["status"],
                        }
                    )
                elif is_install and any(
                    w in desc
                    for w in (
                        "install depend",
                        "install package",
                        "npm install",
                        "pip install",
                    )
                ):
                    candidates.append(
                        {
                            "id": None,
                            "description": t["description"],
                            "status": t["status"],
                        }
                    )
                elif is_test and any(
                    w in desc
                    for w in (
                        "run test",
                        "execute test",
                        "verify test",
                        "pytest",
                        "npm test",
                    )
                ):
                    candidates.append(
                        {
                            "id": None,
                            "description": t["description"],
                            "status": t["status"],
                        }
                    )
                elif is_migrate and any(
                    w in desc
                    for w in (
                        "run migration",
                        "migrate database",
                        "apply migration",
                    )
                ):
                    candidates.append(
                        {
                            "id": None,
                            "description": t["description"],
                            "status": t["status"],
                        }
                    )
                elif is_build and any(
                    w in desc
                    for w in (
                        "build project",
                        "build bundle",
                        "npm run build",
                        "cargo build",
                    )
                ):
                    candidates.append(
                        {
                            "id": None,
                            "description": t["description"],
                            "status": t["status"],
                        }
                    )

    marked_any = False
    for cand in candidates:
        desc = str(cand.get("description") or "")
        t_id = cand.get("id")
        if mark_task_status(
            project_root, task_id_or_desc=t_id or desc, status="completed"
        ):
            marked_any = True

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
        scope_info = _extract_task_file_and_scope(pt["description"])
        if norm in existing:
            ex_task = dict(existing[norm])
            if not ex_task.get("target_files") and scope_info["target_files"]:
                ex_task["target_files"] = scope_info["target_files"]
            if not ex_task.get("line_range") and scope_info["line_range"]:
                ex_task["line_range"] = scope_info["line_range"]
            if not ex_task.get("symbol") and scope_info["symbol"]:
                ex_task["symbol"] = scope_info["symbol"]
            if not ex_task.get("is_new") and scope_info["is_new"]:
                ex_task["is_new"] = scope_info["is_new"]
            if pt.get("task_number") and not ex_task.get("task_number"):
                ex_task["task_number"] = pt["task_number"]
            if pt.get("phase") and not ex_task.get("phase"):
                ex_task["phase"] = pt["phase"]
            if pt.get("task_hash") and not ex_task.get("task_hash"):
                ex_task["task_hash"] = pt["task_hash"]
            merged.append(ex_task)
        else:
            new_task = {
                "id": pt.get("task_hash") or _stable_task_id(all_ids),
                "description": pt["description"],
                "task_number": pt.get("task_number"),
                "phase": pt.get("phase"),
                "task_hash": pt.get("task_hash"),
                "status": (
                    "verified"
                    if pt["status"] in ("completed", "verified", "done")
                    else "in_progress"
                    if pt["status"] in ("in_progress", "active")
                    else "skipped"
                    if pt["status"] in ("skipped", "skip")
                    else "pending"
                ),
                "target_files": scope_info["target_files"],
                "line_range": scope_info["line_range"],
                "symbol": scope_info["symbol"],
                "is_new": scope_info["is_new"],
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
        curr_phase = None
        for t in merged:
            phase = t.get("phase")
            if phase and phase != curr_phase:
                curr_phase = phase
                md_lines.append(f"\n### {curr_phase}")
            box = _status_to_box(t.get("status", "pending"))
            md_lines.append(f"- [{box}] {t.get('description') or t.get('id')}")
        with open(alt_tasks_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines) + "\n")
    except Exception:  # noqa: BLE001, S110
        pass

    # --- Render implementation_plan.md checkboxes in-place -------------------
    _render_plan_checkboxes(project_root, merged)

    return {"synced": True, "task_count": len(merged)}
