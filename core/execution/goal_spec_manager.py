"""Goal specification lifecycle, task dependency ordering, and status summary generation."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from core.execution.harness_models import GoalSpec, TaskSpec, TaskStatus

logger = logging.getLogger(__name__)


class GoalSpecManagerMixin:
    """Mixin providing GoalSpec bootstrapping, JSON/Markdown persistence, and dependency validation."""

    def ensure_goal_spec_initialized(
        self, title: Optional[str] = None, description: Optional[str] = None
    ) -> bool:
        """Ensure a goal spec exists on disk in .torchlight, initializing a default workspace goal if absent.
        
        Returns True if successful (files created and verified), False otherwise.
        """
        spec = self.load_goal_spec()
        if spec:
            self.goal_spec = spec
            # Verify files exist
            return self.goal_json_path.exists() and self.tasks_md_path.exists()

        safe_name = self.project_root.name.lower().replace(" ", "_")
        goal_title = title or f"{self.project_root.name} Autonomous Goal"
        self.initialize_goal(
            goal_id=f"goal_{safe_name}",
            title=goal_title,
            description=description
            or title
            or "Continuous codebase maintenance, debugging, and feature development.",
            tasks=[],
        )

        try:
            from core.tools.task_helpers import sync_workspace_tasks

            sync_workspace_tasks(self.project_root, default_goal_title=goal_title)
        except Exception:
            pass

        # Verify files were created
        return self.goal_json_path.exists() and self.tasks_md_path.exists()

    def initialize_goal(
        self, goal_id: str, title: str, description: str, tasks: list[dict]
    ) -> GoalSpec:
        task_specs = []
        for i, t in enumerate(tasks):
            t_id = t.get("id", f"task_{i + 1:02d}")
            desc = t.get("description", "")
            files = t.get("target_files", [])
            deps = t.get("depends_on", [])
            outputs = t.get("outputs_summary")
            max_att = t.get("max_attempts", self.config.max_task_attempts)
            task_specs.append(
                TaskSpec(
                    id=t_id,
                    description=desc,
                    target_files=files,
                    depends_on=deps,
                    outputs_summary=outputs,
                    max_attempts=max_att,
                )
            )

        self.goal_spec = GoalSpec(
            goal_id=goal_id,
            title=title,
            description=description,
            tasks=task_specs,
        )
        self.save_goal_spec()
        return self.goal_spec

    def load_goal_spec(self) -> Optional[GoalSpec]:
        if not self.goal_json_path.exists():
            return None
        try:
            with open(self.goal_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tasks = []
            for t in data.get("tasks", []):
                try:
                    status = TaskStatus(t.get("status", "pending"))
                except ValueError:
                    status = TaskStatus.PENDING

                tasks.append(
                    TaskSpec(
                        id=t["id"],
                        description=t["description"],
                        target_files=t.get("target_files") or [],
                        depends_on=t.get("depends_on") or [],
                        outputs_summary=t.get("outputs_summary"),
                        status=status,
                        attempts=t.get("attempts", 0),
                        max_attempts=t.get("max_attempts", 3),
                        failure_reasons=t.get("failure_reasons") or [],
                        completed_at=t.get("completed_at"),
                    )
                )
            self.goal_spec = GoalSpec(
                goal_id=data["goal_id"],
                title=data["title"],
                description=data["description"],
                tasks=tasks,
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
            )
            return self.goal_spec
        except Exception as e:
            logger.error(f"Failed to load goal spec: {e}")
            return None

    def save_goal_spec(self) -> None:
        if not self.goal_spec:
            return
        self.goal_spec.updated_at = datetime.now().isoformat()

        # Save JSON
        data = {
            "goal_id": self.goal_spec.goal_id,
            "title": self.goal_spec.title,
            "description": self.goal_spec.description,
            "created_at": self.goal_spec.created_at,
            "updated_at": self.goal_spec.updated_at,
            "tasks": [
                {
                    "id": t.id,
                    "description": t.description,
                    "target_files": t.target_files,
                    "depends_on": t.depends_on,
                    "outputs_summary": t.outputs_summary,
                    "status": t.status.value,
                    "attempts": t.attempts,
                    "max_attempts": t.max_attempts,
                    "failure_reasons": t.failure_reasons,
                    "completed_at": t.completed_at,
                }
                for t in self.goal_spec.tasks
            ],
        }
        with open(self.goal_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Render Markdown tasks.md
        md_lines = [
            f"# Goal: {self.goal_spec.title}",
            f"**Goal ID**: {self.goal_spec.goal_id}",
            f"**Updated**: {self.goal_spec.updated_at}\n",
            f"{self.goal_spec.description}\n",
            "## Tasks Breakdown\n",
        ]
        for t in self.goal_spec.tasks:
            checkbox = (
                "[x]"
                if t.status == TaskStatus.VERIFIED
                else (
                    "[-]"
                    if t.status in (TaskStatus.FAILED, TaskStatus.SKIPPED)
                    else "[ ]"
                )
            )
            md_lines.append(
                f"- {checkbox} **{t.id}**: {t.description} (`{t.status.value}` - attempts: {t.attempts}/{t.max_attempts})"
            )
            if t.target_files:
                md_lines.append(f"  - Target Files: {', '.join(t.target_files)}")
            if t.failure_reasons:
                md_lines.append(f"  - Failure Notes: {t.failure_reasons[-1]}")
        with open(self.tasks_md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines) + "\n")

    def _get_runnable_pending_tasks(self) -> list[TaskSpec]:
        """Return pending tasks whose dependencies are all VERIFIED."""
        if not self.goal_spec:
            return []
        verified_ids = {
            t.id for t in self.goal_spec.tasks if t.status == TaskStatus.VERIFIED
        }
        runnable = []
        for t in self.goal_spec.tasks:
            if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                # Dependencies met if all depends_on IDs are in verified_ids
                if all(dep_id in verified_ids for dep_id in t.depends_on):
                    runnable.append(t)
        return runnable

    def _validate_file_collisions(self, task: TaskSpec) -> list[str]:
        """Return list of target files that collide with active or failed tasks."""
        if not self.goal_spec or not task.target_files:
            return []
        target_set = set(task.target_files)
        collisions = []
        for other in self.goal_spec.tasks:
            if other.id != task.id and other.status == TaskStatus.IN_PROGRESS:
                overlap = target_set.intersection(set(other.target_files))
                if overlap:
                    collisions.extend(list(overlap))
        return sorted(list(set(collisions)))

    def _get_prior_verified_summaries(self, task: TaskSpec) -> str:
        """Construct inter-task memory prompt summarizing prior verified tasks and dependencies."""
        if not self.goal_spec:
            return ""
        verified_tasks = [
            t for t in self.goal_spec.tasks if t.status == TaskStatus.VERIFIED
        ]
        if not verified_tasks:
            return ""

        summary_lines = ["Prior Completed Sub-Tasks Context:"]
        for t in verified_tasks:
            dep_tag = " (Direct Dependency)" if t.id in task.depends_on else ""
            out = f" - {t.id}{dep_tag}: {t.description}"
            if t.outputs_summary:
                out += f" | Output: {t.outputs_summary}"
            summary_lines.append(out)

        return "\n".join(summary_lines)

    def get_status_summary(self) -> dict:
        """
        Return structured status summary of current goal and sub-agent tasks.
        """
        if not self.goal_spec:
            self.load_goal_spec()
        if not self.goal_spec:
            return {
                "goal_id": None,
                "title": None,
                "description": None,
                "total_tasks": 0,
                "verified": 0,
                "in_progress": 0,
                "pending": 0,
                "failed": 0,
                "skipped": 0,
                "progress_pct": 0.0,
                "tasks": [],
            }

        total = len(self.goal_spec.tasks)
        verified = sum(
            1 for t in self.goal_spec.tasks if t.status == TaskStatus.VERIFIED
        )
        in_progress = sum(
            1 for t in self.goal_spec.tasks if t.status == TaskStatus.IN_PROGRESS
        )
        pending = sum(1 for t in self.goal_spec.tasks if t.status == TaskStatus.PENDING)
        failed = sum(1 for t in self.goal_spec.tasks if t.status == TaskStatus.FAILED)
        skipped = sum(1 for t in self.goal_spec.tasks if t.status == TaskStatus.SKIPPED)

        progress_pct = (verified / total * 100.0) if total > 0 else 0.0

        task_list = []
        for t in self.goal_spec.tasks:
            task_list.append(
                {
                    "id": t.id,
                    "description": t.description,
                    "status": t.status.value,
                    "attempts": t.attempts,
                    "max_attempts": t.max_attempts,
                    "target_files": t.target_files,
                    "failure_reasons": t.failure_reasons,
                    "completed_at": t.completed_at,
                }
            )

        return {
            "goal_id": self.goal_spec.goal_id,
            "title": self.goal_spec.title,
            "description": self.goal_spec.description,
            "created_at": self.goal_spec.created_at,
            "updated_at": self.goal_spec.updated_at,
            "total_tasks": total,
            "verified": verified,
            "in_progress": in_progress,
            "pending": pending,
            "failed": failed,
            "skipped": skipped,
            "progress_pct": round(progress_pct, 1),
            "tasks": task_list,
        }
