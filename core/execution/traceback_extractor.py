"""Surgical traceback extraction and failure snippet compression."""

from __future__ import annotations

import re

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
