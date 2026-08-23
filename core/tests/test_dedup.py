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


def test_trajectory_lock_error_feedback():
    lock = TrajectoryLock(window_size=3, max_duplicates=2)
    tool = "EDIT_FILE"
    args = {"path": "game.js", "old_text": "foo", "new_text": "bar}"}
    err_output = "Syntax error in game.js: (line 135): Unmatched closing bracket '}'. File NOT written."

    # First attempt: register call and record error output
    assert lock.is_duplicate(tool, args)[0] is False
    lock.register(tool, args)
    lock.record_output(tool, args, err_output)

    # Second attempt: duplicate call should include exact error output in hint and alternate guidance
    is_dup, count, hint = lock.is_duplicate(tool, args)
    assert is_dup is True
    assert count == 2
    assert "Prior execution output for this exact payload:" in hint
    assert "Unmatched closing bracket '}'" in hint
    assert "File NOT written" in hint
    assert "DUPLICATE EDIT_FILE BLOCKED" in hint
    assert "READ_FILE" in hint
    assert "<tool_call>" in hint


def test_edit_file_alternate_trajectory_hint():
    from core.tools.dedup import get_alternate_trajectory_hint

    edit_hint = get_alternate_trajectory_hint("EDIT_FILE", target_path="index.html")
    assert "DUPLICATE EDIT_FILE BLOCKED" in edit_hint
    assert "READ_FILE" in edit_hint
    assert "index.html" in edit_hint
    assert '<tool_call>{"name": "READ_FILE", "arguments": {"path": "index.html"}}</tool_call>' in edit_hint

    write_hint = get_alternate_trajectory_hint("WRITE_FILE", target_path="app.py")
    assert "DUPLICATE WRITE_FILE BLOCKED" in write_hint
    assert "READ_FILE" in write_hint
    assert "app.py" in write_hint
    assert "<tool_call>" in write_hint

    cmd_hint = get_alternate_trajectory_hint("RUN_COMMAND", target_path="main.py")
    assert "DUPLICATE RUN_COMMAND BLOCKED" in cmd_hint
    assert "READ_FILE" in cmd_hint
    assert "<tool_call>" in cmd_hint


def test_sequential_1line_edit_stepping_blocked():
    lock = TrajectoryLock(window_size=5, max_duplicates=2)

    # Turn 1: edit line 1
    call1 = {"path": "game.js", "start_line": 1, "end_line": 1, "new_text": "console.log(1);"}
    is_dup, _, _ = lock.is_duplicate("EDIT_FILE", call1)
    assert is_dup is False
    lock.register("EDIT_FILE", call1)

    # Turn 2: edit line 2
    call2 = {"path": "game.js", "start_line": 2, "end_line": 2, "new_text": "console.log(2);"}
    is_dup, _, _ = lock.is_duplicate("EDIT_FILE", call2)
    assert is_dup is False
    lock.register("EDIT_FILE", call2)

    # Turn 3: edit line 3 -> should trigger sequential 1-line stepping detector!
    call3 = {"path": "game.js", "start_line": 3, "end_line": 3, "new_text": "console.log(3);"}
    is_dup, count, hint = lock.is_duplicate("EDIT_FILE", call3)
    assert is_dup is True
    assert "LINE-BY-LINE EDITING DETECTED" in hint
    assert "EDIT_FILE" in hint


def test_volatile_keys_filtered_in_payload_hash():
    # task_id and description differences should NOT change the semantic hash
    h1 = compute_payload_hash(
        "EDIT_FILE",
        {
            "path": "index.html",
            "task_id": "1.12",
            "description": "Add initial snake setup",
            "start_line": 106,
            "end_line": 115,
            "new_text": "const snake = [{ x: 200, y: 300 }, direction: 'right' }",
        },
    )
    h2 = compute_payload_hash(
        "EDIT_FILE",
        {
            "path": "index.html",
            "task_id": "1.13",
            "description": "Another description",
            "start_line": 106,
            "end_line": 115,
            "new_text": "const snake = [{ x: 200, y: 300 }, direction: 'right' }",
        },
    )
    assert h1 == h2


def test_sequential_range_stepping_blocked():
    lock = TrajectoryLock(window_size=5, max_duplicates=2)

    # Turn 1: edit lines 1-10
    call1 = {"path": "game.js", "start_line": 1, "end_line": 10, "new_text": "// chunk 1"}
    is_dup, _, _ = lock.is_duplicate("EDIT_FILE", call1)
    assert is_dup is False
    lock.register("EDIT_FILE", call1)

    # Turn 2: edit lines 11-20
    call2 = {"path": "game.js", "start_line": 11, "end_line": 20, "new_text": "// chunk 2"}
    is_dup, _, _ = lock.is_duplicate("EDIT_FILE", call2)
    assert is_dup is False
    lock.register("EDIT_FILE", call2)

    # Turn 3: edit lines 21-30 -> should trigger sequential range stepping detector!
    call3 = {"path": "game.js", "start_line": 21, "end_line": 30, "new_text": "// chunk 3"}
    is_dup, count, hint = lock.is_duplicate("EDIT_FILE", call3)
    assert is_dup is True
    assert "SEQUENTIAL RANGE STEPPING DETECTED" in hint
    assert "EDIT_FILE" in hint


def test_duplicate_new_text_payload_blocked():
    lock = TrajectoryLock(window_size=5, max_duplicates=2)

    # Turn 1: add snake setup
    call1 = {
        "path": "index.html",
        "task_id": "1.12",
        "start_line": 106,
        "end_line": 115,
        "new_text": "const snake = [{ x: 200, y: 300 }, direction: 'right' };",
    }
    is_dup, _, _ = lock.is_duplicate("EDIT_FILE", call1)
    assert is_dup is False
    lock.register("EDIT_FILE", call1)

    # Turn 2: different task_id and line numbers, but identical new_text modification on same file
    call2 = {
        "path": "index.html",
        "task_id": "1.13",
        "start_line": 116,
        "end_line": 125,
        "new_text": "const snake = [{ x: 200, y: 300 }, direction: 'right' };",
    }
    is_dup, count, hint = lock.is_duplicate("EDIT_FILE", call2)
    assert is_dup is True
    assert "DUPLICATE EDIT_FILE PAYLOAD BLOCKED" in hint
    assert "READ_FILE" in hint




