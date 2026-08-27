"""Data models for automated test execution results and status tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

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
