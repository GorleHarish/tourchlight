"""Data models and configuration for the Autonomous Harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List

from core.memory.models import ExecutionMode

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
    depends_on: list[str] = field(default_factory=list)
    outputs_summary: Optional[str] = None
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


from core.memory.models import ExecutionMode


@dataclass
class HarnessConfig:
    max_epoch_steps: int = 10
    max_task_attempts: int = 3
    revert_on_failure: bool = True
    auto_git_commit: bool = True
    max_duration_seconds: int = 86400  # Default 24 hours
    check_interval_seconds: float = 1.0
    preserve_continuous_context: bool = (
        False  # Preserve continuous session context between sub-tasks
    )
    mode: ExecutionMode = ExecutionMode.GOAL
    # Blanket `git checkout -- .` + `git clean -fd` requires BOTH this flag AND
    # a `.torchlight/.harness_managed` marker (proving the harness created the repo).
    allow_blanket_revert: bool = False
    protect_tests_during_recovery: bool = True
