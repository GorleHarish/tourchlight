"""
HTML Game Autonomous Self-Improvement Engine for Torchlight.

Executes closed-loop game play verification, root-cause anomaly diagnosis,
surgical code repair, memory load monitoring, and re-verification without human intervention.
"""

from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional

from core.execution.game_inspector import (
    HtmlGamePlayer,
    GameOutcomeResult,
    GameInputEvent,
    get_process_memory_mb,
)

logger = logging.getLogger(__name__)


@dataclass
class ImprovementIteration:
    iteration: int
    result_before: GameOutcomeResult
    bug_category: str
    diagnostics: str
    code_modifications: List[str] = field(default_factory=list)
    result_after: Optional[GameOutcomeResult] = None
    success: bool = False


@dataclass
class GameSelfImprovementReport:
    game_file: str
    initial_status: str
    final_status: str
    total_iterations: int
    resolved: bool
    iterations: List[ImprovementIteration] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_markdown(self) -> str:
        status_icon = "✅" if self.resolved else "❌"
        lines = [
            f"## {status_icon} Autonomous HTML Game Self-Improvement Report",
            f"- **Game File:** `{self.game_file}`",
            f"- **Initial Status:** `{self.initial_status}` ➡️ **Final Status:** `{self.final_status}`",
            f"- **Iterations Run:** {self.total_iterations}",
            f"- **Outcome:** {'Successfully repaired & verified!' if self.resolved else 'Unresolved after max iterations'}",
        ]

        for it in self.iterations:
            mem_str = f" | Memory: `{it.result_after.memory_mb:.1f} MB`" if it.result_after else ""
            lines.append(f"\n### Iteration {it.iteration}: `{it.bug_category}`{mem_str}")
            lines.append(f"- **Diagnosis:** {it.diagnostics}")
            if it.code_modifications:
                lines.append("- **Applied Fixes:**")
                for mod in it.code_modifications:
                    lines.append(f"  - ✏️ {mod}")
            if it.result_after:
                lines.append(f"- **Re-Verification Status:** `{it.result_after.status}`")

        return "\n".join(lines)


class GameSelfImprover:
    """
    Closed-loop autonomous harness that plays HTML games, detects errors/bugs,
    synthesizes surgical repairs, and verifies resolution.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.player = HtmlGamePlayer(output_dir=self.project_root / ".torchlight" / "screenshots")

    def run_self_improvement_cycle(
        self,
        file_path: str,
        max_iterations: int = 3,
        duration_ms: int = 2500,
        input_events: Optional[List[GameInputEvent]] = None,
        on_progress: Optional[Callable[[str, str], None]] = None
    ) -> GameSelfImprovementReport:
        """
        Executes autonomous self-improvement loop on target game file with live progress indicators.
        """
        target_file = (
            Path(file_path)
            if Path(file_path).is_absolute()
            else (self.project_root / file_path).resolve()
        )

        def _emit(stage: str, msg: str):
            logger.info(f"[{stage}] {msg}")
            if on_progress:
                on_progress(stage, msg)

        if not target_file.exists():
            return GameSelfImprovementReport(
                game_file=file_path,
                initial_status="FAIL",
                final_status="FAIL",
                total_iterations=0,
                resolved=False,
                iterations=[]
            )

        _emit("CYCLE_START", f"🛠️ Starting Self-Improvement Loop for `{target_file.name}` (Max Epochs: {max_iterations})")

        # Initial Play & Verification Run
        current_res = self.player.play_and_verify(
            file_path=str(target_file),
            duration_ms=duration_ms,
            input_events=input_events,
            on_progress=_emit
        )

        if current_res.is_passed:
            _emit("CYCLE_PASS", f"✅ Initial run passed! No repairs needed for `{target_file.name}` (Memory: {current_res.memory_mb:.1f} MB).")
            return GameSelfImprovementReport(
                game_file=str(target_file),
                initial_status="PASS",
                final_status="PASS",
                total_iterations=0,
                resolved=True,
                iterations=[]
            )

        initial_status = current_res.status
        iterations_log: List[ImprovementIteration] = []
        resolved = False

        for epoch in range(1, max_iterations + 1):
            category, diagnosis = self._classify_game_bug(current_res, target_file)
            _emit("DIAGNOSE", f"🔍 [Epoch {epoch}/{max_iterations}] Category: `{category}` | Diagnosis: {diagnosis}")

            _emit("REPAIR", f"✏️ [Epoch {epoch}/{max_iterations}] Synthesizing surgical code modifications...")
            modifications = self._apply_autonomous_repair(target_file, current_res, category)

            # Re-play to verify fix
            _emit("VERIFY", f"🎮 [Epoch {epoch}/{max_iterations}] Re-playing game to verify repair outcome...")
            verify_res = self.player.play_and_verify(
                file_path=str(target_file),
                duration_ms=duration_ms,
                input_events=input_events,
                on_progress=_emit
            )

            success = verify_res.is_passed
            iteration_entry = ImprovementIteration(
                iteration=epoch,
                result_before=current_res,
                bug_category=category,
                diagnostics=diagnosis,
                code_modifications=modifications,
                result_after=verify_res,
                success=success
            )
            iterations_log.append(iteration_entry)

            current_res = verify_res
            if success:
                resolved = True
                _emit("SUCCESS", f"🎉 [Epoch {epoch}/{max_iterations}] Game successfully repaired & verified! (Memory: {verify_res.memory_mb:.1f} MB)")
                break

        final_status = current_res.status
        report = GameSelfImprovementReport(
            game_file=str(target_file),
            initial_status=initial_status,
            final_status=final_status,
            total_iterations=len(iterations_log),
            resolved=resolved,
            iterations=iterations_log
        )

        self._persist_improvement_log(report)
        _emit("CYCLE_DONE", f"🏁 Self-Improvement Complete: Resolved={resolved} (Initial: {initial_status} -> Final: {final_status})")
        return report

    def _classify_game_bug(self, res: GameOutcomeResult, target_file: Path) -> tuple[str, str]:
        """Classifies the primary root cause of failure from diagnostic output."""
        if res.console_errors:
            err_str = " ".join(res.console_errors)
            if "is not a function" in err_str or "is not defined" in err_str or "TypeError" in err_str:
                return "RUNTIME_EXCEPTION", f"JavaScript Runtime Error: {res.console_errors[0]}"
            if "Cannot read propert" in err_str or "null" in err_str:
                return "NULL_REFERENCE", f"Null Property Access: {res.console_errors[0]}"
            return "CONSOLE_ERROR", f"Uncaught Console Error: {res.console_errors[0]}"

        if res.blank_canvas_detected:
            return "BLANK_CANVAS", "Canvas element found, but 0 pixels drawn (render engine failed to draw)."

        if res.frozen_canvas_detected:
            return "FROZEN_CANVAS", "Game loop frozen (canvas pixel delta = 0.0 under input simulation)."

        if res.failed_requests:
            return "MISSING_ASSET", f"404 / Missing static assets: {res.failed_requests[0]}"

        return "UNSPECIFIED_ANOMALY", "Game verification failed without explicit stack trace."

    def _apply_autonomous_repair(
        self, target_file: Path, res: GameOutcomeResult, category: str
    ) -> List[str]:
        """Synthesizes and applies targeted source fixes for diagnosed game bugs."""
        modifications: List[str] = []
        content = target_file.read_text(encoding="utf-8", errors="replace")
        new_content = content

        if category == "BLANK_CANVAS" or category == "FROZEN_CANVAS":
            # Check common causes: missing call to requestAnimationFrame or draw function, or missing getContext
            if "requestAnimationFrame" not in content and "setInterval" not in content:
                # Add auto game loop ticker if missing
                if "function draw" in content or "function render" in content or "function update" in content:
                    target_func = "draw" if "function draw" in content else ("render" if "function render" in content else "update")
                    loop_snippet = f"\nfunction gameLoop() {{ {target_func}(); requestAnimationFrame(gameLoop); }}\nrequestAnimationFrame(gameLoop);\n"
                    new_content += loop_snippet
                    modifications.append(f"Injected missing `requestAnimationFrame` game loop for `{target_func}()`.")

            if "addEventListener" not in content and "onkeydown" not in content:
                # Inject basic keydown listener if missing
                listener_snippet = "\ndocument.addEventListener('keydown', (e) => { if (typeof handleInput === 'function') handleInput(e.key); });\n"
                new_content += listener_snippet
                modifications.append("Added default `keydown` event listener bindings.")

        elif category in ("RUNTIME_EXCEPTION", "NULL_REFERENCE", "CONSOLE_ERROR"):
            err_msg = res.console_errors[0] if res.console_errors else ""
            # Handle common typo: e.g., getContext("2D") -> getContext("2d")
            if 'getContext("2D")' in content or "getContext('2D')" in content:
                new_content = new_content.replace('getContext("2D")', 'getContext("2d")').replace("getContext('2D')", "getContext('2d')")
                modifications.append("Fixed case sensitivity in `getContext('2d')`.")

            # Handle misspelled method typos like requestAniamtionFrame
            if "requestAniamtionFrame" in new_content:
                new_content = new_content.replace("requestAniamtionFrame", "requestAnimationFrame")
                modifications.append("Corrected typo `requestAniamtionFrame` -> `requestAnimationFrame`.")

            # Handle unhandled undefined variable in game canvas context setup
            match = re.search(r"(\w+) is not defined", err_msg)
            if match:
                var_name = match.group(1)
                if f"var {var_name}" not in new_content and f"let {var_name}" not in new_content and f"const {var_name}" not in new_content:
                    decl_snippet = f"\nlet {var_name} = 0;\n"
                    new_content = decl_snippet + new_content
                    modifications.append(f"Declared missing global variable `let {var_name} = 0;`.")

        if new_content != content:
            target_file.write_text(new_content, encoding="utf-8")
            if not modifications:
                modifications.append(f"Updated `{target_file.name}` with automated repair patch.")
        else:
            modifications.append("No automatic text replacement matched; requires LLM structural refactoring.")

        return modifications

    def _persist_improvement_log(self, report: GameSelfImprovementReport) -> None:
        """Persists the self-improvement run metrics into project memory."""
        log_dir = self.project_root / ".torchlight"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "game_improvement_log.json"

        data = []
        if log_file.exists():
            try:
                data = json.loads(log_file.read_text(encoding="utf-8"))
            except Exception:
                data = []

        data.append({
            "game_file": report.game_file,
            "initial_status": report.initial_status,
            "final_status": report.final_status,
            "resolved": report.resolved,
            "iterations": report.total_iterations,
            "timestamp": report.timestamp
        })

        log_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
