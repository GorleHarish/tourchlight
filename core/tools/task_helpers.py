"""Unified Task Helper Module for Torchlight.

Canonical task store: .torchlight/goal_spec.json is the SINGLE source of truth for
task identity/status. implementation_plan.md and .torchlight/tasks.md are rendered
views derived from it. Status flows goal_spec.json -> markdown (render); markdown is
never used to re-derive goal_spec backwards (except first-time bootstrap).

This module re-exports all task helpers from focused submodules:
- core.tools.task_parser: Task parsing, goal spec bootstrapping, and checkbox synchronization.
- core.tools.task_matrix: Compact task matrix formatting, status badges, and workspace summaries.
- core.tools.task_completion: Status mutation, file-targeted verification, and test execution sync.
"""

from __future__ import annotations

from core.tools.task_parser import (
    CHK_REGEX,
    EXECUTION_HEADER_REGEX,
    VALID_TASK_STATUSES,
    _IGNORED_DIRS,
    _clean_task_text,
    _is_task_match,
    parse_all_tasks_from_markdown,
    _load_goal_spec,
    _norm,
    _stable_task_id,
    get_workspace_pending_tasks,
    _patch_plan_checkbox,
    _render_plan_checkboxes,
    insert_task_into_plan,
)
from core.tools.task_matrix import (
    validate_task_transition,
    _status_to_box,
    _status_badge,
    get_compact_task_matrix,
    get_active_task_description,
    get_workspace_task_status_summary,
)
from core.tools.task_completion import (
    _STUB_RE,
    _STUB_EXACT,
    mark_task_status,
    mark_task_in_progress,
    _extract_referenced_files,
    _extract_task_file_and_scope,
    _find_file_in_project,
    _file_looks_complete,
    verify_task_preflight,
    verify_task_targeted,
    auto_mark_task_completed_by_file,
    auto_mark_task_completed_by_command,
    sync_workspace_tasks,
)

__all__ = [
    "CHK_REGEX",
    "EXECUTION_HEADER_REGEX",
    "VALID_TASK_STATUSES",
    "_IGNORED_DIRS",
    "_STUB_RE",
    "_STUB_EXACT",
    "_clean_task_text",
    "_is_task_match",
    "parse_all_tasks_from_markdown",
    "_load_goal_spec",
    "_norm",
    "_stable_task_id",
    "get_workspace_pending_tasks",
    "_patch_plan_checkbox",
    "_render_plan_checkboxes",
    "insert_task_into_plan",
    "validate_task_transition",
    "_status_to_box",
    "_status_badge",
    "get_compact_task_matrix",
    "get_active_task_description",
    "get_workspace_task_status_summary",
    "mark_task_status",
    "mark_task_in_progress",
    "_extract_referenced_files",
    "_extract_task_file_and_scope",
    "_find_file_in_project",
    "_file_looks_complete",
    "verify_task_preflight",
    "verify_task_targeted",
    "auto_mark_task_completed_by_file",
    "auto_mark_task_completed_by_command",
    "sync_workspace_tasks",
]
