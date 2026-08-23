"""
Execution Feedback Loop for Torchlight.

Closes the loop between code changes and test verification.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import subprocess
import re
import logging
import concurrent.futures
import sys

from core.errors.types import TestFailureError

logger = logging.getLogger(__name__)

_speculative_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="TorchlightSpeculativeRunner"
)


class TestResultStatus(Enum):
    __test__ = False
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"
    UNKNOWN = "unknown"


@dataclass
class TestResult:
    __test__ = False
    name: str
    status: TestResultStatus
    duration_ms: float = 0
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TestRunResult:
    __test__ = False
    command: str
    return_code: int
    duration_ms: float
    results: list[TestResult]
    stdout: str = ""
    stderr: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    # True if a test/web command was actually attempted (or a detected command
    # failed to run). False when there was nothing to verify in the first place.
    ran: bool = False

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == TestResultStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(
            1
            for r in self.results
            if r.status in (TestResultStatus.FAIL, TestResultStatus.ERROR)
        )

    @property
    def all_passed(self) -> bool:
        """Return True only if a run succeeded. Uses exit code as the authoritative
        signal so quiet runners (e.g. `pytest -q` with no verbose markers) don't
        get misreported as failing when no per-test results could be parsed."""
        return self.return_code == 0 and self.failed == 0


def extract_surgical_traceback(
    output: str, command: str = "", max_lines: int = 20
) -> str:
    """Extract strictly surgical failure traceback from test output, removing passing test lists, ANSI codes, and noise."""
    if not output:
        return ""

    # Strip ANSI escape codes
    clean = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", output)
    lines = clean.splitlines()

    # 1. Pytest explicit FAILURES section
    pytest_failure_idx = -1
    for i, line in enumerate(lines):
        if re.search(r"=+\s+FAILURES\s+=+", line) or line.strip().startswith(
            "FAILURES"
        ):
            pytest_failure_idx = i
            break

    if pytest_failure_idx != -1:
        extracted = []
        for line in lines[pytest_failure_idx:]:
            if re.search(r"=+\s+short test summary info\s+=+", line):
                break
            extracted.append(line)
        if extracted:
            result = "\n".join(extracted[:max_lines])
            return result[:1500] + ("\n... [truncated]" if len(result) > 1500 else "")

    # 2. Python Traceback / SyntaxError search
    tb_idx = -1
    for i, line in enumerate(lines):
        if "Traceback (most recent call last):" in line or any(
            err in line
            for err in [
                "SyntaxError:",
                "IndentationError:",
                "TypeError:",
                "NameError:",
                "AttributeError:",
            ]
        ):
            tb_idx = i
            break

    if tb_idx != -1:
        result = "\n".join(lines[tb_idx : tb_idx + max_lines])
        return result[:1500] + ("\n... [truncated]" if len(result) > 1500 else "")

    # 3. Cargo / Jest / npm test failure search
    fail_indices = [
        i
        for i, line in enumerate(lines)
        if any(
            kw in line
            for kw in ["FAIL", "FAILED", "failures:", "panicked at", "AssertionError:"]
        )
    ]
    if fail_indices:
        start = max(0, fail_indices[0] - 2)
        end = min(len(lines), fail_indices[-1] + max_lines)
        result = "\n".join(lines[start:end])
        return result[:1500] + ("\n... [truncated]" if len(result) > 1500 else "")

    # Fallback to last max_lines
    result = "\n".join(lines[-max_lines:])
    return result[:1500] + ("\n... [truncated]" if len(result) > 1500 else "")


class ExecutionFeedbackLoop:
    """Auto-run tests and web outcome inspection after code changes and inject feedback into context."""

    def __init__(
        self,
        project_root: Path,
        enabled: bool = True,
        auto_run: bool = True,
        timeout: int = 60,
    ):
        self.project_root = Path(project_root).resolve()
        self.enabled = enabled
        self.auto_run = auto_run
        self.timeout = timeout
        self._last_test_result: Optional[TestRunResult] = None
        self._test_result_reported: bool = False
        self._last_web_result: Optional[Any] = None
        self._files_modified_since_test: set[str] = set()
        self._speculative_future: Optional[concurrent.futures.Future] = None
        self._on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None

    def set_event_callback(
        self, callback: Optional[Callable[[str, Dict[str, Any]], None]]
    ) -> None:
        """Register a callback for test lifecycle events (e.g. 'test_started', 'test_completed')."""
        self._on_event = callback

    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Safely invoke registered event callback."""
        if self._on_event:
            try:
                self._on_event(event_type, data)
            except Exception as e:
                logger.debug(f"Test event callback error: {e}")

    @property
    def has_failing_tests(self) -> bool:
        """Return True if the most recent test run actually ran and has failing or
        error tests. A run that was never attempted (no test framework / no web
        files to inspect) is NOT considered failing."""
        return (
            self._last_test_result is not None
            and self._last_test_result.ran
            and not self._last_test_result.all_passed
        )

    def on_tool_executed(
        self, tool_name: str, params: dict, output: str
    ) -> Optional[TestRunResult]:
        """Called after a tool is executed. Returns test results if tests were run."""
        if not self.enabled or not self.auto_run:
            return None

        tool_name = (tool_name or "").upper()
        if tool_name in ("WRITE_FILE", "EDIT_FILE"):
            path = params.get("path") or params.get("file", "")
            if path:
                self._files_modified_since_test.add(path)
                try:
                    from core.flashlight.graph_engine import update_project_graph_file

                    # Incrementally update AST graph nodes/edges for modified file
                    update_project_graph_file(str(self.project_root), path)
                except Exception:
                    pass

                # Launch speculative background test execution for zero-latency feedback
                try:
                    self._speculative_future = _speculative_executor.submit(self._run_tests_internal)
                except Exception:
                    pass

        if self._should_run_tests(tool_name):
            return self._run_tests()
        return None

    def _should_run_tests(self, tool_name: str) -> bool:
        tool_name = (tool_name or "").upper()
        if not self._files_modified_since_test:
            return False
        if tool_name in ("RUN_COMMAND", "WRITE_FILE", "EDIT_FILE"):
            return True
        return False

    def verify_pending_changes(self) -> bool:
        """Freshly verify any modified-but-unverified files and return True if
        everything passes. Returns True immediately when there is nothing pending
        to verify (no edits, or the latest edits already verified passing)."""
        if not self.enabled or not self._files_modified_since_test:
            return True
        result = self._run_tests()
        if not result.ran:
            return True
        return result.all_passed

    def _run_preflight_lint(self) -> None:
        """Run fast pre-flight auto-fixer/linter on modified files before test execution."""
        py_files = [f for f in self._files_modified_since_test if f.endswith(".py")]
        if not py_files:
            return
        abs_files = []
        for f in py_files:
            p = self.project_root / f if not Path(f).is_absolute() else Path(f)
            if p.exists():
                abs_files.append(str(p))
        if not abs_files:
            return

        try:
            subprocess.run(
                ["ruff", "check", "--fix"] + abs_files[:5],
                cwd=str(self.project_root),
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass

    def _run_tests(self) -> TestRunResult:
        """Fetch speculative background test result if running, else execute tests synchronously."""
        if self._speculative_future is not None:
            try:
                fut = self._speculative_future
                self._speculative_future = None
                return fut.result(timeout=self.timeout)
            except Exception:
                pass
        return self._run_tests_internal()

    def _record_and_emit_result(self, result: TestRunResult) -> TestRunResult:
        """Store test result and dispatch UI notification event if tests were executed."""
        self._last_test_result = result
        self._test_result_reported = False
        if result.ran:
            self._emit_event(
                "test_completed",
                {
                    "command": result.command,
                    "return_code": result.return_code,
                    "duration_ms": result.duration_ms,
                    "passed": result.passed,
                    "failed": result.failed,
                    "all_passed": result.all_passed,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "results": [
                        {"name": r.name, "status": r.status.value, "error": r.error_message}
                        for r in result.results
                    ],
                },
            )
        return result

    def _run_tests_internal(self) -> TestRunResult:
        """Detect and run the project's test suite or web inspector."""
        self._run_preflight_lint()
        test_cmd = self._detect_test_command()
        self._emit_event(
            "test_started",
            {
                "command": test_cmd or "web_inspector",
                "files": list(self._files_modified_since_test),
            },
        )
        if not test_cmd:
            # Check if any modified file is a web file (.html, .js, .jsx, .ts, .tsx, .vue, .svelte, .css)
            web_exts = (
                ".html",
                ".js",
                ".jsx",
                ".ts",
                ".tsx",
                ".vue",
                ".svelte",
                ".css",
            )
            modified_web = [
                f for f in self._files_modified_since_test if f.endswith(web_exts)
            ]

            html_files = [
                f for f in self._files_modified_since_test if f.endswith(".html")
            ]
            if not html_files and modified_web:
                # Find any index.html or main html in project root or src directories
                root_htmls = list(self.project_root.glob("*.html"))
                if not root_htmls:
                    ignored_dirs = {
                        "node_modules",
                        ".venv",
                        "venv",
                        ".git",
                        "dist",
                        "build",
                        ".torchlight",
                        "coverage",
                        ".next",
                    }
                    all_htmls = [
                        p
                        for p in self.project_root.glob("**/*.html")
                        if not any(part in ignored_dirs for part in p.parts)
                    ]
                    if all_htmls:
                        root_htmls = [all_htmls[0]]
                if root_htmls:
                    html_files = [str(root_htmls[0])]

            if html_files:
                try:
                    target_file = (
                        Path(html_files[0])
                        if Path(html_files[0]).is_absolute()
                        else self.project_root / html_files[0]
                    )
                    content_preview = ""
                    if target_file.exists():
                        content_preview = target_file.read_text(encoding="utf-8", errors="replace").lower()

                    # Check if HTML file is a game / canvas app
                    if "<canvas" in content_preview or "game" in target_file.name.lower() or "canvas" in target_file.name.lower():
                        from core.execution.game_inspector import HtmlGamePlayer
                        game_player = HtmlGamePlayer(
                            output_dir=self.project_root / ".torchlight" / "screenshots"
                        )
                        game_res = game_player.play_and_verify(file_path=str(target_file), duration_ms=2000)
                        if game_res.is_passed:
                            self._files_modified_since_test.clear()

                        status = (
                            TestResultStatus.PASS
                            if game_res.is_passed
                            else TestResultStatus.FAIL
                        )
                        tr = TestResult(
                            name=html_files[0],
                            status=status,
                            error_message="\n".join(
                                game_res.console_errors + game_res.failed_requests
                            ),
                        )
                        return self._record_and_emit_result(
                            TestRunResult(
                                command=f"PLAY_AND_VERIFY_GAME {html_files[0]}",
                                return_code=0 if game_res.is_passed else 1,
                                duration_ms=game_res.duration_ms,
                                results=[tr],
                                stdout=game_res.to_markdown(),
                                ran=True,
                            )
                        )

                    from core.execution.web_inspector import WebOutcomeInspector

                    inspector = WebOutcomeInspector(
                        output_dir=self.project_root / ".torchlight" / "screenshots"
                    )
                    res = inspector.inspect(file_path=str(target_file), wait_ms=1000)
                    self._last_web_result = res
                    if res.is_passed:
                        self._files_modified_since_test.clear()

                    status = (
                        TestResultStatus.PASS
                        if res.is_passed
                        else TestResultStatus.FAIL
                    )
                    tr = TestResult(
                        name=html_files[0],
                        status=status,
                        error_message="\n".join(
                            res.console_errors + res.failed_requests
                        ),
                    )
                    return self._record_and_emit_result(
                        TestRunResult(
                            command=f"INSPECT_WEB {html_files[0]}",
                            return_code=0 if res.is_passed else 1,
                            duration_ms=res.duration_ms,
                            results=[tr],
                            stdout=res.to_markdown(),
                            ran=True,
                        )
                    )
                except Exception as e:
                    logger.warning(f"Auto Web/Game Outcome Inspection failed: {e}")

            elif modified_web:
                # Standalone JavaScript/Node syntax verification fallback
                js_files = [
                    f for f in modified_web if f.endswith((".js", ".mjs", ".cjs"))
                ]
                for js_f in js_files[:3]:
                    js_p = (
                        Path(js_f)
                        if Path(js_f).is_absolute()
                        else self.project_root / js_f
                    )
                    if js_p.exists():
                        try:
                            chk = subprocess.run(
                                ["node", "--check", str(js_p)],
                                capture_output=True,
                                text=True,
                                timeout=3,
                            )
                            if chk.returncode != 0:
                                err_out = (
                                    chk.stderr.strip() or chk.stdout.strip()
                                )
                                tr = TestResult(
                                    name=js_f,
                                    status=TestResultStatus.FAIL,
                                    error_message=err_out,
                                )
                                res = TestRunResult(
                                    command=f"node --check {js_f}",
                                    return_code=chk.returncode,
                                    duration_ms=10,
                                    results=[tr],
                                    stdout=f"❌ JavaScript Syntax Error in {js_f}:\n```\n{err_out}\n```",
                                    stderr=err_out,
                                    ran=True,
                                )
                                return self._record_and_emit_result(res)
                        except Exception:
                            pass

            # Nothing to verify (no test framework and no web files): record a
            # non-run so the gate does not misreport it as a passing or failing
            # test run. Keep the dirty set so callers can still see unverified
            # edits instead of silently dropping them.
            result = TestRunResult(
                command="", return_code=-1, duration_ms=0, results=[], ran=False
            )
            return self._record_and_emit_result(result)

        try:
            start = datetime.now()
            r = subprocess.run(
                test_cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=self.timeout,
            )
            duration = (datetime.now() - start).total_seconds() * 1000
            results = self._parse_test_output(r.stdout + r.stderr, test_cmd)

            # Only consider changes verified once tests pass; a failing run keeps
            # the dirty set as a durable signal that edits are still unverified.
            if r.returncode == 0:
                self._files_modified_since_test.clear()
            result = TestRunResult(
                command=test_cmd,
                return_code=r.returncode,
                duration_ms=duration,
                results=results,
                stdout=r.stdout,
                stderr=r.stderr,
                ran=True,
            )
            return self._record_and_emit_result(result)
        except subprocess.TimeoutExpired:
            result = TestRunResult(
                command=test_cmd,
                return_code=-1,
                duration_ms=self.timeout * 1000,
                results=[
                    TestResult(
                        name="test_timeout",
                        status=TestResultStatus.FAIL,
                        error_message=f"Test run timed out after {self.timeout}s",
                    )
                ],
                ran=True,
                stderr=(
                    f"Test run timed out after {self.timeout}s\nCommand: {test_cmd}"
                ),
            )
            return self._record_and_emit_result(result)
        except Exception as e:
            result = TestRunResult(
                command=test_cmd,
                return_code=-1,
                duration_ms=0,
                results=[
                    TestResult(
                        name="test_run_error",
                        status=TestResultStatus.FAIL,
                        error_message=f"Test run crashed: {e}",
                    )
                ],
                ran=True,
                stderr=f"Test run crashed: {e}",
            )
            return self._record_and_emit_result(result)

    def _detect_test_command(self) -> str:
        py_bin = sys.executable or "python3"
        has_pyproject = (self.project_root / "pytest.ini").exists() or (
            self.project_root / "pyproject.toml"
        ).exists()

        if has_pyproject:
            # 1. Direct test files modified in this turn
            direct_test_files = [
                f
                for f in self._files_modified_since_test
                if ("test_" in Path(f).name or "_test" in Path(f).name)
                and f.endswith(".py")
            ]
            if direct_test_files:
                target = " ".join(direct_test_files[:3])
                return f"{py_bin} -m pytest {target} -x --tb=short -q"

            # 2. Associated test file lookup for modified Python source files
            modified_py = [
                f for f in self._files_modified_since_test if f.endswith(".py")
            ]
            matched_tests = []
            test_search_dirs = [
                self.project_root / "core" / "tests",
                self.project_root / "tests",
                self.project_root / "src" / "tests",
            ]
            for py_f in modified_py:
                stem = Path(py_f).stem
                if not stem or stem.startswith("__"):
                    continue
                for t_dir in test_search_dirs:
                    if not t_dir.exists():
                        continue
                    for cand_name in (
                        f"test_{stem}.py",
                        f"{stem}_test.py",
                        f"test_{stem}s.py",
                    ):
                        cand_p = t_dir / cand_name
                        if cand_p.exists():
                            rel = str(cand_p.relative_to(self.project_root))
                            if rel not in matched_tests:
                                matched_tests.append(rel)
                    if not matched_tests:
                        for cand_p in t_dir.glob(f"test_*{stem}*.py"):
                            rel = str(cand_p.relative_to(self.project_root))
                            if rel not in matched_tests:
                                matched_tests.append(rel)

            if matched_tests:
                target = " ".join(matched_tests[:3])
                return f"{py_bin} -m pytest {target} -x --tb=short -q"

            # 3. Scope to standard subproject test directory if modified file belongs to it
            for py_f in modified_py:
                p = Path(py_f)
                if (
                    "core" in p.parts
                    and (self.project_root / "core" / "tests").exists()
                ):
                    return f"{py_bin} -m pytest core/tests -x --tb=short -q"
                if (
                    "src" in p.parts
                    and (self.project_root / "src" / "tests").exists()
                ):
                    return f"{py_bin} -m pytest src/tests -x --tb=short -q"

            # 4. Scope to tests/ or core/tests/ if available
            if (self.project_root / "tests").exists():
                return f"{py_bin} -m pytest tests -x --tb=short -q"
            if (self.project_root / "core" / "tests").exists():
                return f"{py_bin} -m pytest core/tests -x --tb=short -q"

            return ""

        if (self.project_root / "package.json").exists():
            return "npm test --silent"
        if (self.project_root / "Cargo.toml").exists():
            return "cargo test --quiet"
        return ""

    def _parse_test_output(self, output: str, command: str) -> list[TestResult]:
        results = []
        if "pytest" in command:
            for m in re.finditer(r"(\S+::\w+)\s+(PASSED|FAILED|ERROR)", output):
                status = (
                    TestResultStatus.PASS
                    if m.group(2) == "PASSED"
                    else TestResultStatus.FAIL
                )
                results.append(TestResult(name=m.group(1), status=status))
            # If pytest returncode was failure but no PASSED/FAILED regex matched (e.g. syntax error before test collection)
            if not results and (
                "FAILED" in output
                or "ERROR" in output
                or "SyntaxError" in output
                or "Traceback" in output
            ):
                results.append(
                    TestResult(
                        name="pytest_collection",
                        status=TestResultStatus.FAIL,
                        error_message="Collection error",
                    )
                )
        elif "npm" in command or "jest" in command:
            if "FAIL" in output or "ERR!" in output:
                results.append(
                    TestResult(name="npm_test", status=TestResultStatus.FAIL)
                )
            elif "PASS" in output or "passed" in output:
                results.append(
                    TestResult(name="npm_test", status=TestResultStatus.PASS)
                )
        elif "cargo" in command:
            if "FAILED" in output:
                results.append(
                    TestResult(name="cargo_test", status=TestResultStatus.FAIL)
                )
            elif "ok" in output:
                results.append(
                    TestResult(name="cargo_test", status=TestResultStatus.PASS)
                )
        return results

    def get_test_failure_error(self) -> Optional[TestFailureError]:
        """Convert current failing TestRunResult into a structured TestFailureError for RecoveryEngine."""
        if (
            not self._last_test_result
            or not self._last_test_result.ran
            or self._last_test_result.all_passed
        ):
            return None
        r = self._last_test_result
        failing_names = [
            res.name
            for res in r.results
            if res.status in (TestResultStatus.FAIL, TestResultStatus.ERROR)
        ]
        surgical_tb = extract_surgical_traceback(r.stdout + "\n" + r.stderr, r.command)
        return TestFailureError(
            command=r.command,
            failing_tests=failing_names,
            surgical_traceback=surgical_tb,
            return_code=r.return_code,
        )

    def build_feedback_context(self) -> str:
        """Build feedback context string for the LLM with surgical error injection."""
        feedback_parts = []
        if (
            self._last_test_result
            and self._last_test_result.ran
            and not self._test_result_reported
        ):
            r = self._last_test_result
            if r.all_passed:
                feedback_parts.append(f"✅ Tests: {r.passed} passed ({r.command})")
            else:
                err = self.get_test_failure_error()
                from core.errors.recovery import get_recovery_hint

                hint = (
                    get_recovery_hint(err) if err else "Fix failing tests immediately."
                )

                surgical_tb = (
                    err.surgical_traceback
                    if err
                    else (r.stdout[-500:] if r.stdout else r.stderr[-500:])
                )
                feedback_parts.append(
                    f"❌ [POST-EDIT TEST FAILURE DETECTED]\n"
                    f"Command: {r.command}\n"
                    f"Passed: {r.passed}, Failed: {r.failed}\n"
                    f"Recovery Hint: {hint}\n\n"
                    f"Surgical Failure Traceback:\n```\n{surgical_tb}\n```"
                )
            self._test_result_reported = True
        if self._last_web_result:
            feedback_parts.append(self._last_web_result.to_markdown())
            self._last_web_result = (
                None  # Consume to prevent repeating stale feedback across turns
            )

        return "\n\n".join(feedback_parts)
