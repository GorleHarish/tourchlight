"""
Execution Feedback Loop for Torchlight.

Closes the loop between code changes and test verification.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
import subprocess
import re


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


    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == TestResultStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == TestResultStatus.FAIL)

    @property
    def all_passed(self) -> bool:
        return len(self.results) > 0 and self.failed == 0


class ExecutionFeedbackLoop:
    """Auto-run tests after code changes and inject feedback into context."""

    def __init__(self, project_root: Path, enabled: bool = True, auto_run: bool = True, timeout: int = 60):
        self.project_root = project_root
        self.enabled = enabled
        self.auto_run = auto_run
        self.timeout = timeout
        self._last_test_result: Optional[TestRunResult] = None
        self._files_modified_since_test: set[str] = set()

    def on_tool_executed(self, tool_name: str, params: dict, output: str) -> Optional[TestRunResult]:
        """Called after a tool is executed. Returns test results if tests were run."""
        if not self.enabled or not self.auto_run:
            return None

        if tool_name in ("WRITE_FILE", "EDIT_FILE"):
            path = params.get("path", "")
            if path:
                self._files_modified_since_test.add(path)

        if self._should_run_tests(tool_name):
            return self._run_tests()
        return None

    def _should_run_tests(self, tool_name: str) -> bool:
        if not self._files_modified_since_test:
            return False
        if tool_name == "RUN_COMMAND":
            return True
        return False

    def _run_tests(self) -> TestRunResult:
        """Detect and run the project's test suite."""
        test_cmd = self._detect_test_command()
        if not test_cmd:
            return TestRunResult(command="", return_code=-1, duration_ms=0, results=[])

        try:
            start = datetime.now()
            r = subprocess.run(
                test_cmd, shell=True, capture_output=True, text=True,
                cwd=str(self.project_root), timeout=self.timeout,
            )
            duration = (datetime.now() - start).total_seconds() * 1000
            results = self._parse_test_output(r.stdout + r.stderr, test_cmd)

            self._files_modified_since_test.clear()
            result = TestRunResult(
                command=test_cmd, return_code=r.returncode,
                duration_ms=duration, results=results,
                stdout=r.stdout, stderr=r.stderr,
            )
            self._last_test_result = result
            return result
        except subprocess.TimeoutExpired:
            return TestRunResult(command=test_cmd, return_code=-1, duration_ms=self.timeout * 1000, results=[])
        except Exception:
            return TestRunResult(command=test_cmd, return_code=-1, duration_ms=0, results=[])

    def _detect_test_command(self) -> str:
        if (self.project_root / "pytest.ini").exists() or (self.project_root / "pyproject.toml").exists():
            return "python -m pytest -x --tb=short -q"
        if (self.project_root / "package.json").exists():
            return "npm test --silent"
        if (self.project_root / "Cargo.toml").exists():
            return "cargo test --quiet"
        return ""

    def _parse_test_output(self, output: str, command: str) -> list[TestResult]:
        results = []
        if "pytest" in command:
            for m in re.finditer(r'(\S+::\w+)\s+(PASSED|FAILED|ERROR)', output):
                status = TestResultStatus.PASS if m.group(2) == "PASSED" else TestResultStatus.FAIL
                results.append(TestResult(name=m.group(1), status=status))
        return results

    def build_feedback_context(self) -> str:
        """Build feedback context string for the LLM."""
        if not self._last_test_result:
            return ""
        r = self._last_test_result
        if r.all_passed:
            return f"Tests: {r.passed} passed ({r.command})"
        return (
            f"Tests: {r.passed} passed, {r.failed} failed ({r.command})\n"
            f"{r.stdout[-500:] if r.stdout else ''}"
        )
