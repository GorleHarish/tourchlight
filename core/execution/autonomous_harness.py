"""
Autonomous Harness Driver for Torchlight.

Enables continuous, multi-epoch execution of long-running coding goals (up to 24+ hours)
without context window overflow, using disk-backed task management, context flushing,
and test-driven Git checkpointing.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from core.execution.feedback_loop import ExecutionFeedbackLoop, TestRunResult
from core.execution.git_checkpoints import GitCheckpointMixin
from core.execution.goal_spec_manager import GoalSpecManagerMixin
from core.execution.harness_models import GoalSpec, HarnessConfig, TaskSpec, TaskStatus
from core.execution.micro_epoch_runner import MicroEpochRunnerMixin
from core.memory.manager import TieredMemory
from core.tools.implementations import set_ctx_window

logger = logging.getLogger(__name__)


class AutonomousHarness(
    GitCheckpointMixin, GoalSpecManagerMixin, MicroEpochRunnerMixin
):
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
        self.feedback_loop = feedback_loop or ExecutionFeedbackLoop(
            project_root=self.project_root
        )
        self.config = config or HarnessConfig()

        self.torchlight_dir = self.project_root / ".torchlight"
        self.goal_json_path = self.torchlight_dir / "goal_spec.json"
        self.tasks_md_path = self.torchlight_dir / "tasks.md"
        self.torchlight_dir.mkdir(parents=True, exist_ok=True)

        self.goal_spec: Optional[GoalSpec] = self.load_goal_spec()
        self._ensure_local_git()
        if self.memory and hasattr(self.memory, "config") and self.memory.config:
            set_ctx_window(self.memory.config.max_tokens)


__all__ = [
    "TaskStatus",
    "TaskSpec",
    "GoalSpec",
    "HarnessConfig",
    "AutonomousHarness",
]
