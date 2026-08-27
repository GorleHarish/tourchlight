"""Micro-epoch execution loop, context reset, multi-branch evaluation, and 24-hour daemon runner."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.execution.harness_models import GoalSpec, TaskSpec, TaskStatus
from core.memory.models import ExecutionMode
from core.tools.implementations import set_ctx_window

logger = logging.getLogger(__name__)


class MicroEpochRunnerMixin:
    """Mixin providing micro-epoch task execution, candidate branch evaluation, and daemon loops."""

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
