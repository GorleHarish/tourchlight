"""
Autonomous Harness Driver for Torchlight.

Enables continuous, multi-epoch execution of long-running coding goals (up to 24+ hours)
without context window overflow, using disk-backed task management, context flushing,
and test-driven Git checkpointing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import logging
from pathlib import Path
from typing import Optional, Callable
import subprocess

from core.memory.manager import TieredMemory
from core.memory.persistence import ensure_project_initialized, ensure_git_repository
from core.execution.feedback_loop import ExecutionFeedbackLoop, TestRunResult

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskSpec:
    id: str
    description: str
    target_files: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    failure_reasons: list[str] = field(default_factory=list)
    completed_at: Optional[str] = None


@dataclass
class GoalSpec:
    goal_id: str
    title: str
    description: str
    tasks: list[TaskSpec] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class HarnessConfig:
    max_epoch_steps: int = 10
    max_task_attempts: int = 3
    revert_on_failure: bool = True
    auto_git_commit: bool = True
    max_duration_seconds: int = 86400  # Default 24 hours
    check_interval_seconds: float = 1.0


class AutonomousHarness:
    """
    Autonomous Harness Engine driving long-running continuous execution.
    """

    def __init__(
        self,
        project_root: Path,
        memory: TieredMemory,
        llm_engine_step_fn: Optional[Callable[[str, int], bool]] = None,
        feedback_loop: Optional[ExecutionFeedbackLoop] = None,
        config: Optional[HarnessConfig] = None,
    ):
        self.project_root = Path(project_root).resolve()
        self.memory = memory
        self.llm_engine_step_fn = llm_engine_step_fn
        self.feedback_loop = feedback_loop or ExecutionFeedbackLoop(project_root=self.project_root)
        self.config = config or HarnessConfig()

        self.torchlight_dir = self.project_root / ".torchlight"
        self.goal_json_path = self.torchlight_dir / "goal_spec.json"
        self.tasks_md_path = self.torchlight_dir / "tasks.md"
        self.torchlight_dir.mkdir(parents=True, exist_ok=True)

        self.goal_spec: Optional[GoalSpec] = None
        self._ensure_local_git()

    def _ensure_local_git(self) -> None:
        """Ensure target project has local git repository and persistent memory initialized."""
        ensure_project_initialized(self.project_root, create_git=True)


    def initialize_goal(self, goal_id: str, title: str, description: str, tasks: list[dict]) -> GoalSpec:
        task_specs = []
        for i, t in enumerate(tasks):
            t_id = t.get("id", f"task_{i+1:02d}")
            desc = t.get("description", "")
            files = t.get("target_files", [])
            max_att = t.get("max_attempts", self.config.max_task_attempts)
            task_specs.append(TaskSpec(id=t_id, description=desc, target_files=files, max_attempts=max_att))

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

                tasks.append(TaskSpec(
                    id=t["id"],
                    description=t["description"],
                    target_files=t.get("target_files") or [],
                    status=status,
                    attempts=t.get("attempts", 0),
                    max_attempts=t.get("max_attempts", 3),
                    failure_reasons=t.get("failure_reasons") or [],
                    completed_at=t.get("completed_at"),
                ))
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
            checkbox = "[x]" if t.status == TaskStatus.VERIFIED else ("[-]" if t.status in (TaskStatus.FAILED, TaskStatus.SKIPPED) else "[ ]")
            md_lines.append(f"- {checkbox} **{t.id}**: {t.description} (`{t.status.value}` - attempts: {t.attempts}/{t.max_attempts})")
            if t.target_files:
                md_lines.append(f"  - Target Files: {', '.join(t.target_files)}")
            if t.failure_reasons:
                md_lines.append(f"  - Failure Notes: {t.failure_reasons[-1]}")
        with open(self.tasks_md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines) + "\n")

    def run_micro_epoch(self, task: TaskSpec) -> bool:
        """Run a single micro-epoch for a target task."""
        logger.info(f"Starting micro-epoch for task: {task.id}")
        task.status = TaskStatus.IN_PROGRESS
        task.attempts += 1
        self.save_goal_spec()

        # Step 1: Flush L0 message memory to keep context budget under control
        self.memory.clear()

        # Step 2: Inject system context + task prompt
        prompt = (
            f"GOAL: {self.goal_spec.title}\n"
            f"SUB-TASK ({task.id}): {task.description}\n"
            f"Target Files: {', '.join(task.target_files)}\n"
        )
        if task.failure_reasons:
            prompt += f"Previous Failure Note: {task.failure_reasons[-1]}\n"

        self.memory.add_system_message("You are Torchlight continuous autonomous agent.")
        self.memory.add_user_message(prompt)

        # Step 3: Run LLM execution engine step loop up to max_epoch_steps
        success = False
        if self.llm_engine_step_fn:
            try:
                success = self.llm_engine_step_fn(prompt, self.config.max_epoch_steps)
            except Exception as e:
                logger.error(f"Error during LLM step execution: {e}")
                task.failure_reasons.append(str(e))

        # Step 4: Verify via feedback loop tests
        if self.feedback_loop and self.feedback_loop.enabled:
            test_result = self.feedback_loop._run_tests()
            if test_result and test_result.command:
                if test_result.all_passed:
                    success = True
                else:
                    success = False
                    task.failure_reasons.append(
                        f"Tests failed ({test_result.passed} passed, {test_result.failed} failed)"
                    )

        # Step 5: Checkpoint or Revert
        if success:
            task.status = TaskStatus.VERIFIED
            task.completed_at = datetime.now().isoformat()
            if self.config.auto_git_commit:
                self._git_commit(f"feat(torchlight-auto): pass task {task.id} - {task.description}")
        else:
            if task.attempts >= task.max_attempts:
                task.status = TaskStatus.FAILED
                if self.config.revert_on_failure:
                    self._git_revert()

        self.save_goal_spec()
        return success

    def run_daemon(self) -> dict:
        """Run continuous autonomous daemon until completion or timeout."""
        if not self.goal_spec:
            self.load_goal_spec()
        if not self.goal_spec:
            raise ValueError("No goal spec found. Call initialize_goal() or create .torchlight/goal_spec.json first.")

        start_time = datetime.now()
        completed = 0
        failed = 0

        while True:
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed >= self.config.max_duration_seconds:
                logger.info("Daemon reached max_duration_seconds limit.")
                break

            pending_tasks = [t for t in self.goal_spec.tasks if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)]
            if not pending_tasks:
                logger.info("All tasks completed or processed.")
                break

            task = pending_tasks[0]
            try:
                success = self.run_micro_epoch(task)
                if success:
                    completed += 1
                else:
                    if task.status == TaskStatus.FAILED:
                        failed += 1
            except Exception as e:
                logger.error(f"Micro-epoch exception for task {task.id}: {e}")
                task.failure_reasons.append(str(e))
                if task.attempts >= task.max_attempts:
                    task.status = TaskStatus.FAILED
                    failed += 1
                self.save_goal_spec()

        return {
            "total_tasks": len(self.goal_spec.tasks),
            "verified": sum(1 for t in self.goal_spec.tasks if t.status == TaskStatus.VERIFIED),
            "failed": sum(1 for t in self.goal_spec.tasks if t.status == TaskStatus.FAILED),
            "pending": sum(1 for t in self.goal_spec.tasks if t.status == TaskStatus.PENDING),
            "elapsed_seconds": (datetime.now() - start_time).total_seconds(),
        }

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
        verified = sum(1 for t in self.goal_spec.tasks if t.status == TaskStatus.VERIFIED)
        in_progress = sum(1 for t in self.goal_spec.tasks if t.status == TaskStatus.IN_PROGRESS)
        pending = sum(1 for t in self.goal_spec.tasks if t.status == TaskStatus.PENDING)
        failed = sum(1 for t in self.goal_spec.tasks if t.status == TaskStatus.FAILED)
        skipped = sum(1 for t in self.goal_spec.tasks if t.status == TaskStatus.SKIPPED)

        progress_pct = (verified / total * 100.0) if total > 0 else 0.0

        task_list = []
        for t in self.goal_spec.tasks:
            task_list.append({
                "id": t.id,
                "description": t.description,
                "status": t.status.value,
                "attempts": t.attempts,
                "max_attempts": t.max_attempts,
                "target_files": t.target_files,
                "failure_reasons": t.failure_reasons,
                "completed_at": t.completed_at,
            })

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

    def _git_commit(self, message: str) -> bool:
        try:
            ensure_git_repository(self.project_root)
            # Check if there are modified or untracked changes
            status = subprocess.run(["git", "status", "--porcelain"], cwd=str(self.project_root), capture_output=True, text=True)
            if not status.stdout.strip():
                logger.info("Git working tree clean, nothing to commit.")
                return True

            subprocess.run(["git", "add", "."], cwd=str(self.project_root), check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", message], cwd=str(self.project_root), check=True, capture_output=True)
            return True
        except Exception as e:
            logger.warning(f"Git commit failed: {e}")
            return False

    def _git_revert(self) -> bool:
        try:
            ensure_git_repository(self.project_root)
            subprocess.run(["git", "checkout", "--", "."], cwd=str(self.project_root), check=True, capture_output=True)
            subprocess.run(["git", "clean", "-fd"], cwd=str(self.project_root), check=True, capture_output=True)
            return True
        except Exception as e:
            logger.warning(f"Git revert failed: {e}")
            return False

