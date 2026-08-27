"""Multi-language test runner auto-detection and output parsing."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List

from core.execution.test_models import TestResult, TestResultStatus


class TestDiscoveryMixin:
    """Mixin providing project test framework detection and stdout/stderr parsing."""

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
