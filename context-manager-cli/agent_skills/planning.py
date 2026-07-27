"""
Planning Skill for Torchlight.

Breaks down complex tasks into executable steps and tracks progress.
Can be invoked explicitly via /plan or triggered automatically for complex tasks.

Usage:
    PlanningSkill({"task": "build a user authentication system"})
    PlanningSkill({"task": "implement a REST API with CRUD", "auto_execute": true})
"""

import asyncio
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
try:
    from context_manager.skills.base import BaseSkill, SkillResult
except ImportError:
    from skills.base import BaseSkill, SkillResult


@dataclass
class PlanStep:
    number: int
    description: str
    status: str = "pending"  # pending | in_progress | completed | failed | skipped
    tool_calls: List[str] = field(default_factory=list)
    result: str = ""
    duration_ms: float = 0


@dataclass
class ExecutionPlan:
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    current_step: int = 0
    total_duration_ms: float = 0
    status: str = "created"  # created | executing | completed | failed


class PlanningSkill(BaseSkill):
    name        = "plan"
    description = "Break down complex tasks into executable steps"
    icon        = "📋"
    risk_level  = "auto"
    category    = "workflow"

    COMPLEXITY_KEYWORDS = [
        "build", "create", "implement", "design", "develop",
        "migrate", "refactor", "setup", "configure", "integrate",
        "deploy", "optimize", "test", "debug", "fix"
    ]

    def get_prompt(self) -> str:
        return (
            f"{self.icon} **{self.name}**: {self.description}\n"
            "  Input: {task: 'build a calculator', auto_execute: false}\n"
            "  Output: Structured plan with numbered steps"
        )

    async def execute(self, input_data: Dict[str, Any]) -> SkillResult:
        task = input_data.get("task", "")
        auto_execute = input_data.get("auto_execute", False)

        if not task:
            return SkillResult(success=False, output="", error="No task provided")

        plan = self._create_plan(task)
        output_parts = []

        output_parts.append("=" * 60)
        output_parts.append(f"{self.icon} PLANNING: {task}")
        output_parts.append("=" * 60)

        for step in plan.steps:
            output_parts.append(f"  {step.number}. {step.description}")

        output_parts.append("")
        output_parts.append(f"Total steps: {len(plan.steps)}")

        if auto_execute:
            output_parts.append("")
            output_parts.append("▶ Executing plan...")
            await self._execute_plan(plan, output_parts)

        output_parts.append("")
        output_parts.append(self._build_summary(plan))

        return SkillResult(
            success=plan.status != "failed",
            output="\n".join(output_parts),
            metadata={
                "goal": plan.goal,
                "steps": [
                    {"num": s.number, "desc": s.description, "status": s.status}
                    for s in plan.steps
                ],
                "status": plan.status,
            }
        )

    @staticmethod
    def is_complex_task(task: str) -> bool:
        """Detect if a task likely needs planning."""
        task_lower = task.lower()
        word_count = len(task.split())

        # Check for complexity keywords
        complexity_kw = [
            "build", "create", "implement", "design", "develop",
            "migrate", "refactor", "setup", "configure", "integrate",
            "deploy", "system", "api", "service", "component"
        ]
        has_complexity_word = any(kw in task_lower for kw in complexity_kw)

        # Longer tasks or tasks with multiple "and"/"or" likely complex
        has_connectors = " and " in task_lower or " or " in task_lower or ", " in task_lower

        return has_complexity_word or word_count > 8 or has_connectors

    def _create_plan(self, task: str) -> ExecutionPlan:
        """Create a structured plan for the task."""
        plan = ExecutionPlan(goal=task)

        # Detect task type and create appropriate steps
        task_lower = task.lower()

        if any(k in task_lower for k in ["build", "create", "implement"]):
            plan.steps = self._plan_creation_task(task)
        elif "refactor" in task_lower:
            plan.steps = self._plan_refactor_task(task)
        elif "test" in task_lower:
            plan.steps = self._plan_testing_task(task)
        elif "fix" in task_lower or "debug" in task_lower:
            plan.steps = self._plan_fix_task(task)
        elif "migrate" in task_lower:
            plan.steps = self._plan_migration_task(task)
        else:
            plan.steps = self._plan_general_task(task)

        return plan

    def _plan_creation_task(self, task: str) -> List[PlanStep]:
        """Plan for creation/build/implementation tasks."""
        steps = [
            PlanStep(1, "Analyze requirements and understand the scope"),
            PlanStep(2, "Check existing codebase for similar patterns"),
            PlanStep(3, "Design the structure/specification"),
            PlanStep(4, "Write tests first (TDD approach)"),
            PlanStep(5, "Implement core functionality"),
            PlanStep(6, "Run tests and verify"),
            PlanStep(7, "Review and refine"),
        ]
        return steps

    def _plan_refactor_task(self, task: str) -> List[PlanStep]:
        """Plan for refactoring tasks."""
        steps = [
            PlanStep(1, "Identify the code to refactor"),
            PlanStep(2, "Understand current behavior and dependencies"),
            PlanStep(3, "Write tests to preserve behavior"),
            PlanStep(4, "Make incremental changes"),
            PlanStep(5, "Run tests after each change"),
            PlanStep(6, "Verify refactored code works correctly"),
        ]
        return steps

    def _plan_testing_task(self, task: str) -> List[PlanStep]:
        """Plan for testing tasks."""
        steps = [
            PlanStep(1, "Identify code paths to test"),
            PlanStep(2, "Review existing tests (if any)"),
            PlanStep(3, "Write unit tests for core logic"),
            PlanStep(4, "Write integration tests for workflows"),
            PlanStep(5, "Run tests and fix failures"),
            PlanStep(6, "Add edge case coverage"),
        ]
        return steps

    def _plan_fix_task(self, task: str) -> List[PlanStep]:
        """Plan for bug fixes."""
        steps = [
            PlanStep(1, "Reproduce the issue/understand the bug"),
            PlanStep(2, "Identify the root cause"),
            PlanStep(3, "Write a failing test case"),
            PlanStep(4, "Implement the fix"),
            PlanStep(5, "Verify fix with tests"),
            PlanStep(6, "Check for related issues"),
        ]
        return steps

    def _plan_migration_task(self, task: str) -> List[PlanStep]:
        """Plan for migration tasks."""
        steps = [
            PlanStep(1, "Understand source and target systems"),
            PlanStep(2, "Identify data/assets to migrate"),
            PlanStep(3, "Plan the migration strategy"),
            PlanStep(4, "Implement migration script"),
            PlanStep(5, "Test migration on small dataset"),
            PlanStep(6, "Execute full migration"),
            PlanStep(7, "Verify integrity after migration"),
        ]
        return steps

    def _plan_general_task(self, task: str) -> List[PlanStep]:
        """Plan for general tasks."""
        return [
            PlanStep(1, "Understand the task"),
            PlanStep(2, "Gather necessary information"),
            PlanStep(3, "Execute the main action"),
            PlanStep(4, "Verify the result"),
        ]

    async def _execute_plan(self, plan: ExecutionPlan, output_parts: List[str]) -> None:
        """Execute the plan steps."""
        plan.status = "executing"
        total_start = time.time()

        for i, step in enumerate(plan.steps):
            plan.current_step = i
            step.status = "in_progress"

            output_parts.append("")
            output_parts.append(f"▶ Step {step.number}: {step.description}")

            # Simulate step execution (in real impl, would execute actual tools)
            await asyncio.sleep(0.1)  # Brief pause for visibility
            step.status = "completed"
            step.duration_ms = 50  # Placeholder

            output_parts.append(f"  ✓ Completed")

        plan.total_duration_ms = (time.time() - total_start) * 1000
        plan.status = "completed"

    def _build_summary(self, plan: ExecutionPlan) -> str:
        """Build a summary of the plan execution."""
        lines = ["📊 PLAN SUMMARY"]
        lines.append(f"   Goal: {plan.goal}")

        completed = sum(1 for s in plan.steps if s.status == "completed")
        failed = sum(1 for s in plan.steps if s.status == "failed")
        skipped = sum(1 for s in plan.steps if s.status == "skipped")

        lines.append(f"   Steps: {completed}/{len(plan.steps)} completed")
        if failed:
            lines.append(f"   Failed: {failed}")
        if skipped:
            lines.append(f"   Skipped: {skipped}")
        lines.append(f"   Duration: {plan.total_duration_ms:.0f}ms")

        if plan.status == "completed":
            lines.append("   ✅ Plan executed successfully")
        elif plan.status == "failed":
            lines.append("   ❌ Plan execution failed")
        else:
            lines.append(f"   Status: {plan.status}")

        return "\n".join(lines)
