"""
Execution Feedback Loop for Torchlight.

Closes the loop between code changes and test verification:
- Track file modifications
- Auto-run tests after code changes
- Inject failure analysis into context
- Enable fix-verification cycles
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
import subprocess
import re


class TestResultStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"
    UNKNOWN = "unknown"


@dataclass
class TestResult:
    name: str
    status: TestResultStatus
    duration_ms: float = 0
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FileChange:
    path: str
    action: str  # "created", "modified", "deleted"
    timestamp: datetime = field(default_factory=datetime.now)
    line_changes: Optional[tuple[int, int]] = None  # (start_line, end_line)
    hash_before: Optional[str] = None
    hash_after: Optional[str] = None


@dataclass
class TestRunResult:
    command: str
    return_code: int
    duration_ms: float
    results: list[TestResult]
    stdout: str = ""
    stderr: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == TestResultStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == TestResultStatus.FAIL)

    @property
    def errors(self) -> int:
        return sum(1 for r in self.results if r.status == TestResultStatus.ERROR)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def all_passed(self) -> bool:
        return self.total > 0 and self.failed == 0 and self.errors == 0


class TestRunner:
    """Run tests and parse results for various test frameworks."""

    FRAMEWORKS = {
        "pytest": {
            "command": ["pytest", "-v", "--tb=short", "--no-header"],
            "json": ["pytest", "-v", "--json-report", "--json-report-file={path}"],
            "pattern": r"(PASSED|FAILED|ERROR|SKIPPED)\s+(.*?)(?:\s+---|\s*$)",
        },
        "unittest": {
            "command": ["python", "-m", "pytest", "-v"],
            "pattern": r"(OK|FAILED|ERROR)\s+(.*)",
        },
        "npm": {
            "command": ["npm", "test"],
            "pattern": r"(✓|✗|PASS|FAIL)\s+(.*)",
        },
        "cargo": {
            "command": ["cargo", "test", "--", "--nocapture"],
            "pattern": r"(test\s+\w+\s+\.\.\.\s+)(ok|FAILED|running)",
        },
    }

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self._detected_framework: Optional[str] = None

    def detect_framework(self) -> Optional[str]:
        """Auto-detect test framework from project structure."""
        if self._detected_framework:
            return self._detected_framework

        root = self.project_root

        if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
            if (root / "pytest.ini").exists() or any(root.glob("tests/**/*.py")):
                self._detected_framework = "pytest"
                return "pytest"

        if (root / "package.json").exists():
            self._detected_framework = "npm"
            return "npm"

        if (root / "Cargo.toml").exists():
            self._detected_framework = "cargo"
            return "cargo"

        if any(root.glob("**/test_*.py")) or any(root.glob("**/*_test.py")):
            self._detected_framework = "pytest"
            return "pytest"

        return None

    def run_tests(
        self,
        test_path: Optional[str] = None,
        timeout: int = 60,
        framework: Optional[str] = None,
    ) -> TestRunResult:
        """Run tests and return parsed results."""
        framework = framework or self.detect_framework()

        if not framework:
            return TestRunResult(
                command="unknown",
                return_code=-1,
                duration_ms=0,
                results=[],
                stderr="No test framework detected",
            )

        start_time = datetime.now()

        try:
            if framework == "pytest":
                return self._run_pytest(test_path, timeout, start_time)
            elif framework == "npm":
                return self._run_npm_test(test_path, timeout, start_time)
            elif framework == "cargo":
                return self._run_cargo_test(test_path, timeout, start_time)
            else:
                return TestRunResult(
                    command=framework,
                    return_code=-1,
                    duration_ms=0,
                    results=[],
                    stderr=f"Unknown framework: {framework}",
                )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return TestRunResult(
                command=framework,
                return_code=-1,
                duration_ms=duration,
                results=[],
                stderr=str(e),
            )

    def _run_pytest(
        self,
        test_path: Optional[str],
        timeout: int,
        start_time: datetime,
    ) -> TestRunResult:
        """Run pytest tests."""
        cmd = ["pytest", "-v", "--tb=short", "--no-header"]
        if test_path:
            cmd.append(test_path)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            duration = (datetime.now() - start_time).total_seconds() * 1000
            output = result.stdout + result.stderr

            results = self._parse_pytest_output(output)

            return TestRunResult(
                command=" ".join(cmd),
                return_code=result.returncode,
                duration_ms=duration,
                results=results,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except subprocess.TimeoutExpired:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return TestRunResult(
                command=" ".join(cmd),
                return_code=-1,
                duration_ms=duration,
                results=[],
                stderr=f"Test timeout after {timeout}s",
            )

    def _parse_pytest_output(self, output: str) -> list[TestResult]:
        """Parse pytest output to extract test results."""
        results = []
        lines = output.splitlines()

        for line in lines:
            # Parse: test_file.py::test_name PASSED
            match = re.match(r"(.*)::(\S+)\s+(PASSED|FAILED|ERROR|SKIPPED)", line)
            if match:
                file_path, test_name, status = match.groups()
                status_map = {
                    "PASSED": TestResultStatus.PASS,
                    "FAILED": TestResultStatus.FAIL,
                    "ERROR": TestResultStatus.ERROR,
                    "SKIPPED": TestResultStatus.SKIP,
                }

                # Extract error info if failed
                error_msg = None
                error_tb = None
                line_no = None

                results.append(
                    TestResult(
                        name=test_name,
                        status=status_map.get(status, TestResultStatus.UNKNOWN),
                        file_path=file_path,
                        error_message=error_msg,
                        error_traceback=error_tb,
                        line_number=line_no,
                    )
                )

        # Also try to parse summary line
        # e.g., "=== 5 passed, 2 failed, 1 error in 2.5s ==="
        summary_match = re.search(
            r"(\d+)\s+passed[,\s]*(\d+)?\s*failed[,\s]*(\d+)?\s*error", output, re.IGNORECASE
        )

        return results

    def _run_npm_test(
        self,
        test_path: Optional[str],
        timeout: int,
        start_time: datetime,
    ) -> TestRunResult:
        """Run npm test."""
        cmd = ["npm", "test"]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            duration = (datetime.now() - start_time).total_seconds() * 1000
            output = result.stdout + result.stderr

            results = self._parse_npm_output(output)

            return TestRunResult(
                command="npm test",
                return_code=result.returncode,
                duration_ms=duration,
                results=results,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except subprocess.TimeoutExpired:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return TestRunResult(
                command="npm test",
                return_code=-1,
                duration_ms=duration,
                results=[],
                stderr=f"Test timeout after {timeout}s",
            )

    def _parse_npm_output(self, output: str) -> list[TestResult]:
        """Parse npm test output."""
        results = []

        for line in output.splitlines():
            # Parse: "✓ test_name (50ms)"
            match = re.match(r"[✓✗✔✕]\s+(.+?)(?:\s+\(\d+ms\))?$", line.strip())
            if match:
                test_name = match.group(1).strip()
                status = (
                    TestResultStatus.PASS if "✓" in line or "✔" in line else TestResultStatus.FAIL
                )
                results.append(TestResult(name=test_name, status=status))

        return results

    def _run_cargo_test(
        self,
        test_path: Optional[str],
        timeout: int,
        start_time: datetime,
    ) -> TestRunResult:
        """Run cargo test."""
        cmd = ["cargo", "test", "--", "--nocapture"]
        if test_path:
            cmd.insert(2, test_path)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            duration = (datetime.now() - start_time).total_seconds() * 1000
            output = result.stdout + result.stderr

            results = self._parse_cargo_output(output)

            return TestRunResult(
                command=" ".join(cmd),
                return_code=result.returncode,
                duration_ms=duration,
                results=results,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except subprocess.TimeoutExpired:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return TestRunResult(
                command=" ".join(cmd),
                return_code=-1,
                duration_ms=duration,
                results=[],
                stderr=f"Test timeout after {timeout}s",
            )

    def _parse_cargo_output(self, output: str) -> list[TestResult]:
        """Parse cargo test output."""
        results = []

        for line in output.splitlines():
            # Parse: "test test_name ... ok" or "test test_name ... FAILED"
            match = re.match(r"test\s+(\S+)\s+\.\.\.\s+(ok|FAILED|running)", line)
            if match:
                test_name, status = match.groups()
                status_map = {
                    "ok": TestResultStatus.PASS,
                    "FAILED": TestResultStatus.FAIL,
                    "running": TestResultStatus.UNKNOWN,
                }
                results.append(
                    TestResult(
                        name=test_name,
                        status=status_map.get(status, TestResultStatus.UNKNOWN),
                    )
                )

        return results


class WorkingMemory:
    """Track changes and test results across the session."""

    def __init__(self, max_changes: int = 50, max_test_results: int = 20):
        self.max_changes = max_changes
        self.max_test_results = max_test_results
        self.file_changes: list[FileChange] = []
        self.test_runs: list[TestRunResult] = []
        self.pending_fixes: list[str] = []

        # Map files to their test files
        self._test_file_map: dict[str, list[str]] = {}

    def add_file_change(self, path: str, action: str = "modified") -> None:
        """Record a file change."""
        change = FileChange(path=path, action=action)
        self.file_changes.append(change)

        if len(self.file_changes) > self.max_changes:
            self.file_changes = self.file_changes[-self.max_changes :]

    def add_test_run(self, result: TestRunResult) -> None:
        """Record a test run."""
        self.test_runs.append(result)

        if len(self.test_runs) > self.max_test_results:
            self.test_runs = self.test_runs[-self.max_test_results :]

        # Update working state
        if not result.all_passed:
            # Add failing tests to pending fixes
            for test_result in result.results:
                if test_result.status in (TestResultStatus.FAIL, TestResultStatus.ERROR):
                    self.pending_fixes.append(
                        f"{test_result.name}: {test_result.error_message or 'test failed'}"
                    )

    def get_failing_tests(self) -> list[TestResult]:
        """Get all currently failing tests."""
        failing = []
        for run in reversed(self.test_runs):
            for result in run.results:
                if result.status in (TestResultStatus.FAIL, TestResultStatus.ERROR):
                    failing.append(result)
        return failing[:10]  # Limit to 10 most recent

    def get_recent_changes(self) -> list[FileChange]:
        """Get recent file changes."""
        return self.file_changes[-10:]

    def get_test_file_for_source(self, source_file: str) -> Optional[str]:
        """Guess test file path from source file."""
        path = Path(source_file)
        stem = path.stem

        # Common patterns
        patterns = [
            f"test_{stem}.py",
            f"{stem}_test.py",
            f"tests/{stem}.py",
            f"tests/test_{stem}.py",
            f"__tests__/{stem}.py",
            f"{stem}.spec.ts",
            f"{stem}.test.ts",
            f"{stem}.spec.js",
            f"{stem}.test.js",
        ]

        for pattern in patterns:
            test_path = path.parent / pattern
            if test_path.exists():
                return str(test_path)

        return None

    def clear(self) -> None:
        """Clear all working memory."""
        self.file_changes.clear()
        self.test_runs.clear()
        self.pending_fixes.clear()


class ExecutionFeedbackLoop:
    """
    Closes the loop between code changes and test verification.

    Flow:
    1. Detect code change (WRITE_FILE, EDIT_FILE)
    2. Identify related test file
    3. Run tests
    4. Parse results
    5. Inject failure analysis into context
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        enabled: bool = True,
        auto_run: bool = True,
        timeout: int = 60,
    ):
        self.project_root = project_root or Path.cwd()
        self.enabled = enabled
        self.auto_run = auto_run
        self.timeout = timeout

        self.test_runner = TestRunner(self.project_root)
        self.working_memory = WorkingMemory()

        self._last_test_run: Optional[TestRunResult] = None

    def on_tool_executed(
        self,
        tool_name: str,
        tool_args: dict,
        tool_result: str,
    ) -> Optional[TestRunResult]:
        """
        Called after a tool is executed.

        Returns TestRunResult if tests were run, None otherwise.
        """
        if not self.enabled:
            return None

        # Track file changes
        if tool_name in ("WRITE_FILE", "EDIT_FILE", "write_file"):
            file_path = tool_args.get("file_path") or tool_args.get("path")
            if file_path:
                self.working_memory.add_file_change(file_path, "modified")

                # Auto-run tests if enabled
                if self.auto_run:
                    return self.run_related_tests(file_path)

        elif tool_name in ("RUN_COMMAND", "run_command", "bash"):
            # Check if this was a test command
            cmd = tool_args.get("command", "") or tool_args.get("cmd", "")
            if self._is_test_command(cmd):
                # Parse the output as test results
                result = self._parse_test_command_output(cmd, tool_result)
                if result:
                    self.working_memory.add_test_run(result)
                    self._last_test_run = result
                    return result

        return None

    def run_related_tests(self, source_file: str) -> Optional[TestRunResult]:
        """Run tests related to a source file."""
        # Find test file
        test_file = self.working_memory.get_test_file_for_source(source_file)

        if test_file:
            result = self.test_runner.run_tests(test_file, timeout=self.timeout)
        else:
            # Run all tests if no specific test file found
            result = self.test_runner.run_tests(timeout=self.timeout)

        self.working_memory.add_test_run(result)
        self._last_test_run = result
        return result

    def run_all_tests(self) -> TestRunResult:
        """Run all tests in the project."""
        result = self.test_runner.run_tests(timeout=self.timeout)
        self.working_memory.add_test_run(result)
        self._last_test_run = result
        return result

    def _is_test_command(self, cmd: str) -> bool:
        """Check if command is a test command."""
        test_commands = [
            "pytest",
            "python -m pytest",
            "python -m unittest",
            "npm test",
            "yarn test",
            "pnpm test",
            "cargo test",
            "go test",
            "rspec",
            "jest",
        ]
        return any(cmd.strip().startswith(c) for c in test_commands)

    def _parse_test_command_output(
        self,
        cmd: str,
        output: str,
    ) -> Optional[TestRunResult]:
        """Parse test command output."""
        duration_match = re.search(r"in\s+([\d.]+)s", output)
        duration_ms = float(duration_match.group(1)) * 1000 if duration_match else 0

        results = []

        # Parse pytest-style output
        for line in output.splitlines():
            match = re.match(r"(.*)::(\S+)\s+(PASSED|FAILED|ERROR)", line)
            if match:
                file_path, test_name, status = match.groups()
                status_map = {
                    "PASSED": TestResultStatus.PASS,
                    "FAILED": TestResultStatus.FAIL,
                    "ERROR": TestResultStatus.ERROR,
                }
                results.append(
                    TestResult(
                        name=test_name,
                        status=status_map.get(status, TestResultStatus.UNKNOWN),
                        file_path=file_path,
                    )
                )

        if not results:
            return None

        # Determine return code
        return_code = 0 if all(r.status == TestResultStatus.PASS for r in results) else 1

        return TestRunResult(
            command=cmd,
            return_code=return_code,
            duration_ms=duration_ms,
            results=results,
            stdout=output,
        )

    def build_feedback_context(self) -> str:
        """
        Build context string from test feedback.

        This is injected into the system prompt to inform the LLM
        about test results after code changes.
        """
        if not self._last_test_run:
            return ""

        result = self._last_test_run
        parts = []

        parts.append("=" * 50)
        parts.append("TEST RESULTS:")
        parts.append("=" * 50)

        if result.all_passed:
            parts.append(f"✓ ALL TESTS PASSED ({result.passed}/{result.total})")
        else:
            parts.append(
                f"✗ {result.failed} FAILED, {result.errors} ERRORS, {result.passed} PASSED"
            )

        # Show failing tests with details
        failing = [
            r for r in result.results if r.status in (TestResultStatus.FAIL, TestResultStatus.ERROR)
        ]
        if failing:
            parts.append("\nFAILING TESTS:")
            for test in failing[:5]:  # Limit to 5
                parts.append(f"  - {test.name}")
                if test.error_message:
                    parts.append(f"    Error: {test.error_message[:100]}")
                if test.file_path:
                    parts.append(f"    File: {test.file_path}")
                    if test.line_number:
                        parts.append(f"    Line: {test.line_number}")

        # Show context from working memory
        recent_changes = self.working_memory.get_recent_changes()
        if recent_changes:
            parts.append("\nRECENT CHANGES:")
            for change in recent_changes[-5:]:
                parts.append(f"  - {change.action}: {change.path}")

        parts.append("=" * 50)

        return "\n".join(parts)

    def get_status_summary(self) -> dict:
        """Get a summary of current state."""
        failing = self.working_memory.get_failing_tests()

        return {
            "enabled": self.enabled,
            "auto_run": self.auto_run,
            "total_test_runs": len(self.working_memory.test_runs),
            "failing_tests_count": len(failing),
            "recent_changes_count": len(self.working_memory.file_changes),
            "last_test_passed": self._last_test_run.all_passed if self._last_test_run else None,
        }


# ── Parity delegation to the shared core/ library ─────────────────────────
# The canonical feedback loop lives in core/execution/feedback_loop.py and
# receives all fixes (e.g. `ran` semantics, timeout/crash fallbacks,
# verify_pending_changes). When core/ is importable, rebind the shared symbols
# to the fixed core implementations so both frontends stay in lock-step. The
# legacy classes below remain available only as a no-core fallback.
try:
    from core.execution.feedback_loop import (  # type: ignore
        ExecutionFeedbackLoop as ExecutionFeedbackLoop,
        TestResult as TestResult,
        TestRunResult as TestRunResult,
        TestResultStatus as TestResultStatus,
        extract_surgical_traceback as extract_surgical_traceback,
    )
except ImportError:  # pragma: no cover - only when core/ is not installed
    pass
