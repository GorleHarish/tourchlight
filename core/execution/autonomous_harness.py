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
from core.tools.implementations import set_ctx_window

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

    def _ensure_local_git(self) -> None:
        """Ensure target project has local git repository and persistent memory initialized."""
        ensure_project_initialized(self.project_root, create_git=True)

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

    def run_micro_epoch(self, task: TaskSpec) -> bool:
        """Run a single micro-epoch for a target task."""
        logger.info(f"Starting micro-epoch for task: {task.id}")

        # Check for file collisions
        collisions = self._validate_file_collisions(task)
        if collisions:
            logger.warning(f"File collisions detected for task {task.id}: {collisions}")

        task.status = TaskStatus.IN_PROGRESS
        task.attempts += 1
        self.save_goal_spec()

        # Step 1: Manage message memory for continuous session execution
        if getattr(self.config, "preserve_continuous_context", False):
            if hasattr(self.memory, "compact_between_tasks"):
                self.memory.compact_between_tasks()
            else:
                self.memory.clear()
        else:
            self.memory.clear()

        # Step 1.5: Pre-load Flashlight symbols for target files to avoid LLM needing an extra SEARCH_AST step
        symbol_summaries = []
        if task.target_files:
            try:
                from core.flashlight.indexer import SymbolIndex

                p_root = Path(self.project_root).resolve()
                index = SymbolIndex(project_dir=p_root)
                index.build()
                for tf in task.target_files:
                    tf_path = (p_root / tf).resolve()
                    try:
                        rel_key = str(tf_path.relative_to(p_root))
                    except ValueError:
                        rel_key = tf
                    entry = index.files.get(rel_key) or index.files.get(tf)
                    if entry and entry.symbols:
                        names = [
                            s[0]
                            if isinstance(s, (tuple, list))
                            else getattr(s, "name", str(s))
                            for s in entry.symbols
                        ]
                        symbol_summaries.append(f"- {rel_key}: {', '.join(names)}")
            except Exception as e:
                logger.debug(f"Pre-load AST symbol summary skipped: {e}")

        # Step 2: Inject system context + task prompt + inter-task pipeline memory
        prior_context = self._get_prior_verified_summaries(task)
        prompt_parts = [
            f"GOAL: {self.goal_spec.title}",
            f"GOAL DESCRIPTION: {self.goal_spec.description}",
            f"SUB-TASK ({task.id}): {task.description}",
            f"Target Files: {', '.join(task.target_files)}",
        ]
        if symbol_summaries:
            prompt_parts.append(
                f"Pre-loaded Symbols in Target Files:\n" + "\n".join(symbol_summaries)
            )
        if task.depends_on:
            prompt_parts.append(f"Dependencies: {', '.join(task.depends_on)}")
        if prior_context:
            prompt_parts.append(prior_context)
        if task.failure_reasons:
            prompt_parts.append(f"Previous Failure Note: {task.failure_reasons[-1]}")

        prompt = "\n".join(prompt_parts) + "\n"

        self.memory.add_system_message(
            "You are Torchlight continuous autonomous agent."
        )
        self.memory.add_user_message(prompt)

        # Step 3: Run LLM execution engine step loop up to max_epoch_steps
        success = True
        if self.llm_engine_step_fn:
            try:
                success = self.llm_engine_step_fn(prompt, self.config.max_epoch_steps)
            except Exception as e:
                logger.error(f"Error during LLM step execution: {e}")
                task.failure_reasons.append(str(e))
                success = False

        # Step 4: Verify via feedback loop tests. Only gate task success on tests
        # when the task actually produced unverified changes or there are failing
        # tests — passing pre-existing tests must never mask an LLM step failure
        # (BUG-08), and unrelated failures must not override a clean no-change task.
        if self.feedback_loop and self.feedback_loop.enabled:
            if (
                self.feedback_loop._files_modified_since_test
                or self.feedback_loop.has_failing_tests
            ):
                test_result = self.feedback_loop._run_tests()
                if test_result and test_result.command:
                    if test_result.all_passed:
                        success = success and True
                    else:
                        success = False
                        reason = f"Task {task.id} tests failed ({test_result.passed} passed, {test_result.failed} failed)"
                        task.failure_reasons.append(reason)
                        if hasattr(self.memory, "state") and hasattr(
                            self.memory.state, "tried_and_failed"
                        ):
                            if reason not in self.memory.state.tried_and_failed:
                                self.memory.state.tried_and_failed.append(reason)

        # Step 5: Checkpoint or Revert
        if success:
            task.status = TaskStatus.VERIFIED
            task.completed_at = datetime.now().isoformat()

            # Enrich outputs_summary with AST symbol signatures from target files
            symbol_summaries = []
            if task.target_files:
                try:
                    from core.flashlight.indexer import SymbolIndex

                    p_root = Path(self.project_root).resolve()
                    index = SymbolIndex(project_dir=p_root)
                    index.build()
                    for tf in task.target_files:
                        tf_path = (p_root / tf).resolve()
                        try:
                            rel_key = str(tf_path.relative_to(p_root))
                        except ValueError:
                            rel_key = tf
                        entry = index.files.get(rel_key) or index.files.get(tf)
                        if entry and entry.symbols:
                            names = [
                                s[0]
                                if isinstance(s, (tuple, list))
                                else getattr(s, "name", str(s))
                                for s in entry.symbols[:5]
                            ]
                            symbol_summaries.append(f"{rel_key} ({', '.join(names)})")
                except Exception as e:
                    logger.debug(f"AST symbol summary extraction skipped: {e}")

            sym_str = (
                f" [Symbols: {'; '.join(symbol_summaries)}]" if symbol_summaries else ""
            )
            task.outputs_summary = (
                f"Completed '{task.description}' targeting {task.target_files}{sym_str}"
            )

            if self.config.auto_git_commit:
                self._git_commit(
                    f"feat(torchlight-auto): pass task {task.id} - {task.description}"
                )
        else:
            if task.attempts >= task.max_attempts:
                task.status = TaskStatus.FAILED
                if self.config.revert_on_failure:
                    self._git_revert(task.target_files)
            else:
                task.status = TaskStatus.IN_PROGRESS

        self.save_goal_spec()
        return success

    def evaluate_candidate_branches(
        self, task: TaskSpec, candidates: list[dict]
    ) -> Optional[dict]:
        """Tree-of-Thoughts / Branching Evaluator: evaluate candidate implementation options
        and return the best-scoring candidate based on zero-context quality gates."""
        if not candidates:
            return None

        best_candidate = None
        best_score = -999.0

        for cand in candidates:
            code_patch = cand.get("patch", "")
            target_file = cand.get("file", "")
            score = 100.0

            # 1. Bracket balance & syntax validation
            open_b = (
                code_patch.count("{") + code_patch.count("(") + code_patch.count("[")
            )
            close_b = (
                code_patch.count("}") + code_patch.count(")") + code_patch.count("]")
            )
            if open_b != close_b:
                score -= 40.0

            # 2. Python AST validation if target is python
            if target_file.endswith(".py") and code_patch:
                try:
                    import ast

                    ast.parse(code_patch)
                except Exception:
                    score -= 50.0

            # 3. Stub detection penalty
            if "TODO" in code_patch or "pass  # placeholder" in code_patch:
                score -= 15.0

            cand["score"] = score
            if score > best_score:
                best_score = score
                best_candidate = cand

        return best_candidate

    def run_daemon(self) -> dict:
        """Run continuous autonomous daemon until completion or timeout."""
        if not self.goal_spec:
            self.load_goal_spec()
        if not self.goal_spec:
            raise ValueError(
                "No goal spec found. Call initialize_goal() or create .torchlight/goal_spec.json first."
            )

        start_time = datetime.now()
        completed = 0
        failed = 0

        while True:
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed >= self.config.max_duration_seconds:
                logger.info("Daemon reached max_duration_seconds limit.")
                break

            runnable_tasks = self._get_runnable_pending_tasks()
            if not runnable_tasks:
                pending_any = any(
                    t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
                    for t in self.goal_spec.tasks
                )
                if pending_any:
                    logger.warning(
                        "Pending tasks exist but their dependencies are not verified. Stopping daemon."
                    )
                else:
                    logger.info("All tasks completed or processed.")
                break

            task = runnable_tasks[0]
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
                else:
                    task.status = TaskStatus.PENDING
                self.save_goal_spec()

        return {
            "total_tasks": len(self.goal_spec.tasks),
            "verified": sum(
                1 for t in self.goal_spec.tasks if t.status == TaskStatus.VERIFIED
            ),
            "failed": sum(
                1 for t in self.goal_spec.tasks if t.status == TaskStatus.FAILED
            ),
            "pending": sum(
                1 for t in self.goal_spec.tasks if t.status == TaskStatus.PENDING
            ),
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

    def _git_commit(self, message: str) -> bool:
        try:
            ensure_git_repository(self.project_root)
            # Check if there are modified or untracked changes
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
            )
            if not status.stdout.strip():
                logger.info("Git working tree clean, nothing to commit.")
                return True

            subprocess.run(
                ["git", "add", "."],
                cwd=str(self.project_root),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(self.project_root),
                check=True,
                capture_output=True,
            )
            return True
        except Exception as e:
            logger.warning(f"Git commit failed: {e}")
            return False

    def _git_revert(self, target_files: Optional[list[str]] = None) -> bool:
        try:
            ensure_git_repository(self.project_root)
            if not target_files:
                logger.info("No target files to revert.")
                return True
            existing_targets = [
                tf for tf in target_files if (self.project_root / tf).exists()
            ]
            if existing_targets:
                subprocess.run(
                    ["git", "checkout", "--"] + existing_targets,
                    cwd=str(self.project_root),
                    check=False,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "clean", "-fd"] + existing_targets,
                    cwd=str(self.project_root),
                    check=False,
                    capture_output=True,
                )
                return True
            # Blanket workspace revert requires allow_blanket_revert=True AND a
            # .torchlight/.harness_managed marker proving the harness itself
            # initialized the repository. Pre-existing user repos never get the
            # marker, so a misconfigured flag cannot destroy user work.
            allow = getattr(self.config, "allow_blanket_revert", False)
            managed = (self.torchlight_dir / ".harness_managed").exists()
            if not (allow and managed):
                logger.warning(
                    "Blanket git revert skipped: requires allow_blanket_revert=True "
                    "and a .torchlight/.harness_managed marker."
                )
                return False

            subprocess.run(
                ["git", "checkout", "--", "."],
                cwd=str(self.project_root),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "clean", "-fd"],
                cwd=str(self.project_root),
                check=True,
                capture_output=True,
            )
            return True
        except Exception as e:
            logger.warning(f"Git revert failed: {e}")
            return False
