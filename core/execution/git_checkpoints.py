"""Local Git repository provisioning, commit checkpoints, and safe revert mechanisms."""

from __future__ import annotations

import logging
import subprocess
from typing import Optional, List

from core.memory.persistence import ensure_project_initialized, ensure_git_repository

logger = logging.getLogger(__name__)


class GitCheckpointMixin:
    """Mixin providing automated Git checkpoint commits and targeted rollback capabilities."""

    def _ensure_local_git(self) -> None:
        """Ensure target project has local git repository and persistent memory initialized."""
        ensure_project_initialized(self.project_root, create_git=True)

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
