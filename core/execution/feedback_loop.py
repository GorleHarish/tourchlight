"""
Execution Feedback Loop for Torchlight.

Closes the loop between code changes and test verification.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
import subprocess
import re
import logging
import concurrent.futures

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


def extract_surgical_traceback(output: str, command: str = "") -> str:
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
            return "\n".join(extracted[:40])

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
        return "\n".join(lines[tb_idx : tb_idx + 35])

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
        end = min(len(lines), fail_indices[-1] + 15)
        return "\n".join(lines[start:end])

    # Fallback to last 20 lines
    return "\n".join(lines[-20:])


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

    def _run_tests_internal(self) -> TestRunResult:
        """Detect and run the project's test suite or web inspector."""
        self._run_preflight_lint()
        test_cmd = self._detect_test_command()
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
                    from core.execution.web_inspector import WebOutcomeInspector

                    inspector = WebOutcomeInspector(
                        output_dir=self.project_root / ".torchlight" / "screenshots"
                    )
                    target_file = (
                        Path(html_files[0])
                        if Path(html_files[0]).is_absolute()
                        else self.project_root / html_files[0]
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
                    return TestRunResult(
                        command=f"INSPECT_WEB {html_files[0]}",
                        return_code=0 if res.is_passed else 1,
                        duration_ms=res.duration_ms,
                        results=[tr],
                        stdout=res.to_markdown(),
                        ran=True,
                    )
                except Exception as e:
                    logger.warning(f"Auto Web Outcome Inspection failed: {e}")

            # Nothing to verify (no test framework and no web files): record a
            # non-run so the gate does not misreport it as a passing or failing
            # test run. Keep the dirty set so callers can still see unverified
            # edits instead of silently dropping them.
            result = TestRunResult(
                command="", return_code=-1, duration_ms=0, results=[], ran=False
            )
            self._last_test_result = result
            self._test_result_reported = False
            return result

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
            self._last_test_result = result
            self._test_result_reported = False
            return result
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
            self._last_test_result = result
            self._test_result_reported = False
            return result
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
            self._last_test_result = result
            self._test_result_reported = False
            return result

    def _detect_test_command(self) -> str:
        if (self.project_root / "pytest.ini").exists() or (
            self.project_root / "pyproject.toml"
        ).exists():
            test_files = [
                f
                for f in self._files_modified_since_test
                if ("test_" in Path(f).name or "_test" in Path(f).name)
                and f.endswith(".py")
            ]
            if test_files:
                target = " ".join(test_files[:3])
                return f"python -m pytest {target} -x --tb=short -q"
            return "python -m pytest -x --tb=short -q"
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
