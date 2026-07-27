"""
Test-Driven Development (TDD) Skill for Torchlight.

Implements a test-first workflow:
1. Analyze requirement → generate tests
2. Run tests (expect RED/failures)
3. Generate implementation
4. Run tests (expect GREEN/pass)
5. Report summary

Usage:
    TDD("create a function that adds two numbers")
    TDD("implement a cache with get/set/delete")
    TDD("build a parser for CSV files")
"""

import asyncio
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
try:
    from context_manager.skills.base import BaseSkill, SkillResult
except ImportError:
    from skills.base import BaseSkill, SkillResult


@dataclass
class TDDStep:
    phase: str  # "test_write" | "test_run" | "code_write" | "code_run"
    status: str  # "pending" | "running" | "pass" | "fail"
    output: str = ""
    duration_ms: float = 0


class TDDSkill(BaseSkill):
    name        = "TDD"
    description = "Test-driven development: write tests first, then implementation"
    icon        = "🔄"
    risk_level  = "confirm"
    category    = "workflow"

    def __init__(self):
        super().__init__()
        self.steps: List[TDDStep] = []
        self.test_file: Optional[str] = None
        self.code_file: Optional[str] = None

    def get_prompt(self) -> str:
        return (
            f"{self.icon} **{self.name}**: {self.description}\n"
            "  Input: {requirement: 'function to add numbers', test_file: 'test_math.py', code_file: 'math.py'}\n"
            "  Phases: TEST_RED → CODE_GREEN → SUMMARY"
        )

    async def execute(self, input_data: Dict[str, Any]) -> SkillResult:
        requirement = input_data.get("requirement", "")
        test_file   = input_data.get("test_file", "")
        code_file   = input_data.get("code_file", "")
        language    = input_data.get("language", "python")

        if not requirement:
            return SkillResult(success=False, output="", error="No requirement provided")

        self.steps = []
        output_parts = []

        output_parts.append("=" * 60)
        output_parts.append("🔄 TDD WORKFLOW STARTED")
        output_parts.append("=" * 60)
        output_parts.append(f"📝 Requirement: {requirement}")
        output_parts.append("")

        try:
            if language.lower() == "python":
                result = await self._tdd_python(requirement, test_file, code_file, output_parts)
            else:
                result = await self._tdd_generic(requirement, test_file, code_file, language, output_parts)

            output_parts.append("")
            output_parts.append("=" * 60)
            output_parts.append(self._build_summary())
            output_parts.append("=" * 60)

            return SkillResult(
                success=result,
                output="\n".join(output_parts),
                metadata={
                    "steps": [(s.phase, s.status, s.duration_ms) for s in self.steps],
                    "test_file": self.test_file,
                    "code_file": self.code_file,
                }
            )
        except Exception as e:
            return SkillResult(success=False, output="\n".join(output_parts), error=str(e))

    async def _tdd_python(self, requirement: str, test_file: str, code_file: str, output_parts: List[str]) -> bool:
        import time

        if not test_file:
            test_file = self._generate_test_filename(requirement)
        if not code_file:
            code_file = self._generate_code_filename(requirement)

        self.test_file = test_file
        self.code_file = code_file

        output_parts.append(f"📄 Test file: {test_file}")
        output_parts.append(f"📄 Code file: {code_file}")
        output_parts.append("")

        step1 = TDDStep(phase="test_write", status="running")
        self.steps.append(step1)
        output_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output_parts.append("🔴 PHASE 1: WRITE TESTS (Red)")
        output_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        test_code = self._generate_python_tests(requirement, code_file)
        with open(test_file, "w") as f:
            f.write(test_code)
        step1.status = "done"
        output_parts.append(f"✅ Tests written to {test_file}")

        step2 = TDDStep(phase="test_run", status="running")
        self.steps.append(step2)
        t0 = time.time()
        output_parts.append("")
        output_parts.append("🏃 Running tests (expect failures)...")

        run_result = subprocess.run(
            ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
            capture_output=True, text=True, timeout=30
        )
        step2.duration_ms = (time.time() - t0) * 1000
        step2.output = run_result.stdout + run_result.stderr

        if run_result.returncode != 0:
            step2.status = "fail"
            output_parts.append("✅ Tests FAILED as expected (RED)")
        else:
            output_parts.append("⚠️ Tests passed without implementation - unexpected!")
            step2.status = "pass"

        output_parts.append(f"   Duration: {step2.duration_ms:.0f}ms")
        for line in step2.output.splitlines()[-15:]:
            if line.strip():
                output_parts.append(f"   {line}")

        step3 = TDDStep(phase="code_write", status="running")
        self.steps.append(step3)
        output_parts.append("")
        output_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        output_parts.append("🟢 PHASE 2: WRITE CODE (Green)")
        output_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        code = self._generate_python_code(requirement, code_file)
        with open(code_file, "w") as f:
            f.write(code)
        step3.status = "done"
        output_parts.append(f"✅ Code written to {code_file}")

        step4 = TDDStep(phase="code_run", status="running")
        self.steps.append(step4)
        t0 = time.time()
        output_parts.append("")
        output_parts.append("🏃 Running tests again...")

        run_result = subprocess.run(
            ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
            capture_output=True, text=True, timeout=30
        )
        step4.duration_ms = (time.time() - t0) * 1000
        step4.output = run_result.stdout + run_result.stderr

        if run_result.returncode == 0:
            step4.status = "pass"
            output_parts.append("✅ Tests PASSED! (GREEN)")
        else:
            step4.status = "fail"
            output_parts.append("❌ Tests still failing - implementation incomplete")

        output_parts.append(f"   Duration: {step4.duration_ms:.0f}ms")
        for line in run_result.stdout.splitlines()[-15:]:
            if line.strip():
                output_parts.append(f"   {line}")

        return step4.status == "pass"

    async def _tdd_generic(self, requirement: str, test_file: str, code_file: str, language: str, output_parts: List[str]) -> bool:
        output_parts.append(f"⚠️ Language '{language}' not fully supported yet")
        output_parts.append("Please use language='python' for full TDD workflow")
        return False

    def _generate_test_filename(self, requirement: str) -> str:
        words = re.findall(r'[A-Za-z]+', requirement)
        if words:
            return f"test_{words[0].lower()}.py"
        return "test_feature.py"

    def _generate_code_filename(self, requirement: str) -> str:
        words = re.findall(r'[A-Za-z]+', requirement)
        if words:
            return f"{words[0].lower()}.py"
        return "feature.py"

    def _generate_python_tests(self, requirement: str, code_file: str) -> str:
        code_module = code_file.replace(".py", "").replace("/", ".")
        return f'''"""Tests for: {requirement}"""

import pytest
from {code_module} import *


class TestFeature:
    """Test cases for the feature."""

    def test_basic_case(self):
        """Basic test case - implement this first."""
        # TODO: Write assertion based on requirement
        pass

    def test_edge_case(self):
        """Edge case test."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''

    def _generate_python_code(self, requirement: str, code_file: str) -> str:
        return f'''"""Implementation for: {requirement}"""

# TODO: Implement based on the requirement
# {requirement}


def feature():
    """Main feature function."""
    raise NotImplementedError("Implement this feature")
'''

    def _build_summary(self) -> str:
        total_duration = sum(s.duration_ms for s in self.steps)
        passed = sum(1 for s in self.steps if s.status == "pass")
        failed = sum(1 for s in self.steps if s.status == "fail")

        summary = [
            "📊 TDD SUMMARY",
            f"   Total duration: {total_duration:.0f}ms",
            f"   Phases passed: {passed}/{len(self.steps)}",
        ]

        if all(s.status == "pass" for s in self.steps):
            summary.append("   🎉 ALL TESTS PASSING - TDD cycle complete!")
        else:
            summary.append("   ⚠️ Some phases failed - review implementation")

        return "\n".join(summary)
