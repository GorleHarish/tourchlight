"""Full file write operations, atomic file commits, backups, and result formatting."""

from __future__ import annotations

import difflib
import hashlib
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Optional, Union

from core.tools.fs_tools import (
    _global_memory_mgr,
    _resolve_path,
    _truncate,
    _extract_symbols,
)
from core.tools.code_validator import (
    _clean_copied_file_text,
    _is_test_file,
    _validate_and_repair,
    _detect_stubs,
    _detect_symptom_patching,
    _sync_ast_graph,
    _REJECT_ON_STUB_DEFAULT,
)

_MAX_TOOL_OUTPUT = 4000

def tool_write_file_impl(args: dict, project_root: str) -> str:
    """WRITE_FILE — create or overwrite a file."""
    if not isinstance(args, dict):
        args = {"raw": str(args)}

    path_raw = (
        args.get("path")
        or args.get("file")
        or args.get("filepath")
        or args.get("filename")
        or args.get("dest")
        or args.get("target")
        or args.get("p")
    )

    content = args.get("content")
    if content is None:
        content = args.get("code") or args.get("text") or args.get("data") or ""

    # Fallback: extract from raw string
    if not path_raw and "raw" in args:
        raw_text = str(args["raw"])
        p_match = re.search(
            r'["\']?(?:path|file|filename|filepath)["\']?\s*:\s*["\']([^"\']+)["\']',
            raw_text,
        )
        if p_match:
            path_raw = p_match.group(1)
        c_match = re.search(
            r'["\']?(?:content|code|text)["\']?\s*:\s*["\']([\s\S]*)["\']\s*\}?$',
            raw_text,
        )
        if c_match:
            content = c_match.group(1)

    if not path_raw or not str(path_raw).strip():
        return "Error: Missing required 'path' parameter for WRITE_FILE."

    if content is not None:
        content = _clean_copied_file_text(str(content), str(path_raw))

    path_str = str(path_raw).strip()
    protect_tests = (
        args.get("protect_tests", False)
        or os.environ.get("TORCHLIGHT_PROTECT_TESTS") == "1"
    )
    if protect_tests and _is_test_file(path_str):
        return "Error: Test files are protected during automated recovery. Fix the source code instead."

    p = (
        os.path.join(project_root, path_str)
        if not os.path.isabs(path_str)
        else path_str
    )

    if os.path.isdir(p):
        return f"Error: Specified path '{path_str}' is a directory, not a file."

    try:
        parent_dir = os.path.dirname(p)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        force = bool(args.get("force", False))
        reject_on_stub = bool(args.get("reject_on_stub", _REJECT_ON_STUB_DEFAULT))
        status, payload = _validate_and_repair(
            content, p, project_root, force=force, reject_on_stub=reject_on_stub
        )
        if status != "ok":
            return payload
        content = payload

        existing_content = ""
        if os.path.exists(p) and os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as existing_f:
                    existing_content = existing_f.read()
                if (
                    hashlib.sha256(existing_content.encode("utf-8")).hexdigest()
                    == hashlib.sha256(content.encode("utf-8")).hexdigest()
                ):
                    return (
                        f"No change: file content of {path_str} is already identical. "
                        f"Hint: Use READ_FILE to verify current contents, or WRITE_FILE if you need to overwrite."
                    )

                # Accidental Code Deletion Guard:
                # If target file already has substantial code (>= 8 lines) and the new write
                # provides significantly fewer lines (< 60% of existing lines), reject unless force=True.
                existing_lines = [l for l in existing_content.splitlines() if l.strip()]
                new_lines = [l for l in content.splitlines() if l.strip()]
                if len(existing_lines) >= 8 and len(new_lines) < int(len(existing_lines) * 0.6) and not force:
                    return (
                        f"⛔ [ACCIDENTAL CODE OVERWRITE BLOCKED]: Target file '{path_str}' already has {len(existing_lines)} lines of code, "
                        f"but WRITE_FILE was called with only {len(new_lines)} line(s) without 'force: true'.\n"
                        f"This would overwrite and destroy previous progress/functions.\n"
                        f"Next required action: Use EDIT_FILE to surgically insert or modify code:\n"
                        f'<tool_call>{{"name": "EDIT_FILE", "arguments": {{"path": "{path_str}", "old_text": "...", "new_text": "..."}}}}</tool_call>\n'
                        f"Or if you genuinely intend to replace the entire file, pass 'force': true."
                    )
            except Exception:
                pass

        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        _sync_ast_graph(project_root, p)
        line_count = content.count("\n") + (
            1 if content and not content.endswith("\n") else 0
        )
        from core.memory.manager import calculate_in_memory_diff

        added, deleted = calculate_in_memory_diff(existing_content, content)
        stub_note = _detect_stubs(content) or ""
        return f"Written {line_count} lines to {p} (+{added}, -{deleted}){stub_note}"
    except Exception as e:
        return f"Error writing {p}: {e}"


def _commit_edit_file(
    p: str,
    new_content: str,
    original_content: str,
    project_root: str,
    force: bool,
    reject_on_stub: bool,
) -> tuple[bool, str, int, int]:
    if (
        hashlib.sha256(original_content.encode("utf-8")).hexdigest()
        == hashlib.sha256(new_content.encode("utf-8")).hexdigest()
    ):
        return False, "No change: file content is already identical.", 0, 0
    status, payload = _validate_and_repair(
        new_content, p, project_root, force=force, reject_on_stub=reject_on_stub
    )
    if status != "ok":
        return False, payload, 0, 0
    new_content = payload
    with open(p, "w", encoding="utf-8") as f:
        f.write(new_content)
    _sync_ast_graph(project_root, p)
    from core.memory.manager import calculate_in_memory_diff

    added, deleted = calculate_in_memory_diff(original_content, new_content)
    return True, new_content, added, deleted


def _commit_edit_and_format_result(
    p: str,
    new_content: str,
    original_content: str,
    project_root: str,
    force: bool,
    reject_on_stub: bool,
    prefix_msg: str,
) -> str:
    from core.memory.manager import calculate_in_memory_diff
    from core.tools.task_helpers import get_active_task_description

    if (
        hashlib.sha256(original_content.encode("utf-8")).hexdigest()
        == hashlib.sha256(new_content.encode("utf-8")).hexdigest()
    ):
        return "No change: file content is already identical."

    status, payload = _validate_and_repair(
        new_content, p, project_root, force=force, reject_on_stub=reject_on_stub
    )
    if status != "ok":
        return payload
    new_content = payload

    with open(p, "w", encoding="utf-8") as f:
        f.write(new_content)
    _sync_ast_graph(project_root, p)

    added, deleted = calculate_in_memory_diff(original_content, new_content)
    stub_note = _detect_stubs(new_content) or ""
    active_task = get_active_task_description(project_root)
    task_suffix = f" • 🎯 Task: {active_task}" if active_task else ""

    return f"{prefix_msg} (+{added}, -{deleted}){task_suffix}.{stub_note}"
