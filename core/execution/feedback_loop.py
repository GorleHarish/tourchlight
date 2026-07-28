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

from core.errors.types import TestFailureError

logger = logging.getLogger(__name__)


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
        return sum(1 for r in self.results if r.status in (TestResultStatus.FAIL, TestResultStatus.ERROR))

    @property
    def all_passed(self) -> bool:
        return len(self.results) > 0 and self.failed == 0


def extract_surgical_traceback(output: str, command: str = "") -> str:
    """Extract strictly surgical failure traceback from test output, removing passing test lists, ANSI codes, and noise."""
    if not output:
        return ""

    # Strip ANSI escape codes
    clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', output)
    lines = clean.splitlines()

    # 1. Pytest explicit FAILURES section
    pytest_failure_idx = -1
    for i, line in enumerate(lines):
        if re.search(r'=+\s+FAILURES\s+=+', line) or line.strip().startswith("FAILURES"):
            pytest_failure_idx = i
            break

    if pytest_failure_idx != -1:
        extracted = []
        for line in lines[pytest_failure_idx:]:
            if re.search(r'=+\s+short test summary info\s+=+', line):
                break
            extracted.append(line)
        if extracted:
            return "\n".join(extracted[:40])

    # 2. Python Traceback / SyntaxError search
    tb_idx = -1
    for i, line in enumerate(lines):
        if "Traceback (most recent call last):" in line or any(
            err in line for err in ["SyntaxError:", "IndentationError:", "TypeError:", "NameError:", "AttributeError:"]
        ):
            tb_idx = i
            break

    if tb_idx != -1:
        return "\n".join(lines[tb_idx:tb_idx + 35])

    # 3. Cargo / Jest / npm test failure search
    fail_indices = [
        i for i, line in enumerate(lines)
        if any(kw in line for kw in ["FAIL", "FAILED", "failures:", "panicked at", "AssertionError:"])
    ]
    if fail_indices:
        start = max(0, fail_indices[0] - 2)
        end = min(len(lines), fail_indices[-1] + 15)
        return "\n".join(lines[start:end])

    # Fallback to last 20 lines
    return "\n".join(lines[-20:])



class ExecutionFeedbackLoop:
    """Auto-run tests and web outcome inspection after code changes and inject feedback into context."""

    def __init__(self, project_root: Path, enabled: bool = True, auto_run: bool = True, timeout: int = 60):
        self.project_root = Path(project_root).resolve()
        self.enabled = enabled
        self.auto_run = auto_run
        self.timeout = timeout
        self._last_test_result: Optional[TestRunResult] = None
        self._last_web_result: Optional[Any] = None
        self._files_modified_since_test: set[str] = set()

    def on_tool_executed(self, tool_name: str, params: dict, output: str) -> Optional[TestRunResult]:
        """Called after a tool is executed. Returns test results if tests were run."""
        if not self.enabled or not self.auto_run:
            return None

        if tool_name in ("WRITE_FILE", "EDIT_FILE"):
            path = params.get("path") or params.get("file", "")
            if path:
                self._files_modified_since_test.add(path)
                try:
                    from core.flashlight.graph_engine import _graphs
                    # Invalidate cached graph so it rebuilds lazily on next query
                    root_key = str(self.project_root)
                    _graphs.pop(root_key, None)
                except Exception:
                    pass

        if self._should_run_tests(tool_name):
            return self._run_tests()
        return None

    def _should_run_tests(self, tool_name: str) -> bool:
        if not self._files_modified_since_test:
            return False
        if tool_name in ("RUN_COMMAND", "WRITE_FILE", "EDIT_FILE"):
            return True
        return False

    def _run_tests(self) -> TestRunResult:
        """Detect and run the project's test suite or web inspector."""
        test_cmd = self._detect_test_command()
        if not test_cmd:
            # Check if any modified file is a web file (.html, .js, .css)
            html_files = [f for f in self._files_modified_since_test if f.endswith(".html")]
            if not html_files:
                # Find any index.html or main html in project root
                root_htmls = list(self.project_root.glob("*.html"))
                if root_htmls:
                    html_files = [str(root_htmls[0])]

            if html_files:
                try:
                    from core.execution.web_inspector import WebOutcomeInspector
                    inspector = WebOutcomeInspector(output_dir=self.project_root / ".torchlight" / "screenshots")
                    target_file = Path(html_files[0]) if Path(html_files[0]).is_absolute() else self.project_root / html_files[0]
                    res = inspector.inspect(file_path=str(target_file), wait_ms=1000)
                    self._last_web_result = res
                    self._files_modified_since_test.clear()
                    
                    status = TestResultStatus.PASS if res.is_passed else TestResultStatus.FAIL
                    tr = TestResult(name=html_files[0], status=status, error_message="\n".join(res.console_errors))
                    return TestRunResult(
                        command=f"INSPECT_WEB {html_files[0]}",
                        return_code=0 if res.is_passed else 1,
                        duration_ms=res.duration_ms,
                        results=[tr],
                        stdout=res.to_markdown()
                    )
                except Exception as e:
                    logger.warning(f"Auto Web Outcome Inspection failed: {e}")

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
            # If pytest returncode was failure but no PASSED/FAILED regex matched (e.g. syntax error before test collection)
            if not results and ("FAILED" in output or "ERROR" in output or "SyntaxError" in output or "Traceback" in output):
                results.append(TestResult(name="pytest_collection", status=TestResultStatus.FAIL, error_message="Collection error"))
        elif "npm" in command or "jest" in command:
            if "FAIL" in output or "ERR!" in output:
                results.append(TestResult(name="npm_test", status=TestResultStatus.FAIL))
            elif "PASS" in output or "passed" in output:
                results.append(TestResult(name="npm_test", status=TestResultStatus.PASS))
        elif "cargo" in command:
            if "FAILED" in output:
                results.append(TestResult(name="cargo_test", status=TestResultStatus.FAIL))
            elif "ok" in output:
                results.append(TestResult(name="cargo_test", status=TestResultStatus.PASS))
        return results

    def get_test_failure_error(self) -> Optional[TestFailureError]:
        """Convert current failing TestRunResult into a structured TestFailureError for RecoveryEngine."""
        if not self._last_test_result or self._last_test_result.all_passed:
            return None
        r = self._last_test_result
        failing_names = [res.name for res in r.results if res.status in (TestResultStatus.FAIL, TestResultStatus.ERROR)]
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
        if self._last_test_result:
            r = self._last_test_result
            if r.all_passed:
                feedback_parts.append(f"✅ Tests: {r.passed} passed ({r.command})")
            else:
                err = self.get_test_failure_error()
                from core.errors.recovery import get_recovery_hint
                hint = get_recovery_hint(err) if err else "Fix failing tests immediately."

                surgical_tb = err.surgical_traceback if err else (r.stdout[-500:] if r.stdout else r.stderr[-500:])
                feedback_parts.append(
                    f"❌ [POST-EDIT TEST FAILURE DETECTED]\n"
                    f"Command: {r.command}\n"
                    f"Passed: {r.passed}, Failed: {r.failed}\n"
                    f"Recovery Hint: {hint}\n\n"
                    f"Surgical Failure Traceback:\n```\n{surgical_tb}\n```"
                )
        if self._last_web_result:
            feedback_parts.append(self._last_web_result.to_markdown())
            self._last_web_result = None  # Consume to prevent repeating stale feedback across turns

        return "\n\n".join(feedback_parts)
