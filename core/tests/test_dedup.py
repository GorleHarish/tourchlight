"""
Unit tests for core/tools/dedup.py argument normalization & TrajectoryLock.
"""

import pytest
from core.tools.dedup import normalize_tool_args, compute_payload_hash, TrajectoryLock


def test_normalize_tool_args():
    # 1. Whitespace & dict key sorting
    args1 = {"path": "  foo/bar.py  ", "b": 2, "a": 1}
    args2 = {"a": 1, "path": "foo/bar.py", "b": 2}
    norm1 = normalize_tool_args(args1)
    norm2 = normalize_tool_args(args2)
    assert norm1 == norm2

    # 2. Path normalization with backslashes
    args_win = {"path": "foo\\bar\\baz.py"}
    args_posix = {"path": "foo/bar/baz.py"}
    assert normalize_tool_args(args_win) == normalize_tool_args(args_posix)


def test_compute_payload_hash():
    h1 = compute_payload_hash("WRITE_FILE", {"path": "foo.py", "content": "  hello  "})
    h2 = compute_payload_hash("write_file", {"content": "hello", "path": "foo.py"})
    assert h1 == h2


def test_trajectory_lock():
    lock = TrajectoryLock(window_size=3, max_duplicates=2)

    tool = "WRITE_FILE"
    args = {"path": "app.py", "content": "print(1)"}

    # First call: not duplicate
    is_dup, count, hint = lock.is_duplicate(tool, args)
    assert is_dup is False
    lock.register(tool, args)

    # Second call: 2nd attempt (duplicate count 2)
    is_dup, count, hint = lock.is_duplicate(tool, args)
    assert is_dup is True
    assert count == 2
    assert "Trajectory Lock" in hint
    lock.register(tool, args)

    # Third call: 3rd attempt (duplicate count 3)
    is_dup, count, hint = lock.is_duplicate(tool, args)
    assert is_dup is True
    assert count == 3
