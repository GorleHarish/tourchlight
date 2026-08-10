"""
Unit tests for Surgical Targeted Task Verification in Torchlight.
"""

import os
import tempfile
from core.tools.task_helpers import (
    verify_task_preflight,
    verify_task_targeted,
    auto_mark_task_completed_by_file,
    sync_workspace_tasks,
    _load_goal_spec,
)


def test_verify_task_preflight_valid_python():
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = os.path.join(tmpdir, "valid_sample.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("def foo():\n    return 42\n")

        ok, msg = verify_task_preflight(tmpdir, ["valid_sample.py"])
        assert ok is True
        assert "OK" in msg


def test_verify_task_preflight_syntax_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = os.path.join(tmpdir, "broken_sample.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("def foo(\n    return 42\n")

        ok, msg = verify_task_preflight(tmpdir, ["broken_sample.py"])
        assert ok is False
        assert "SyntaxError" in msg


def test_verify_task_preflight_invalid_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        json_file = os.path.join(tmpdir, "config.json")
        with open(json_file, "w", encoding="utf-8") as f:
            f.write("{\n  \"key\": \"value\",\n}\n")  # trailing comma invalid in std json

        ok, msg = verify_task_preflight(tmpdir, ["config.json"])
        assert ok is False
        assert "JSONDecodeError" in msg


def test_verify_task_targeted_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = os.path.join(tmpdir, "module.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("x = 100\n")

        task = {
            "description": "Implement module",
            "target_files": ["module.py"],
            "verification_cmd": "python3 -c 'import sys; sys.exit(0)'",
        }

        ok, msg = verify_task_targeted(tmpdir, task)
        assert ok is True
        assert "passed" in msg.lower()


def test_auto_mark_task_completed_triggers_verification():
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "implementation_plan.md")
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write("- [ ] Create worker.py\n")

        sync_workspace_tasks(tmpdir)

        # Write valid worker.py
        worker_path = os.path.join(tmpdir, "worker.py")
        with open(worker_path, "w", encoding="utf-8") as f:
            f.write("def work(): pass\n")

        # Mark completed with verification enabled
        marked = auto_mark_task_completed_by_file(tmpdir, "worker.py", verified=True)
        assert marked is True

        goal_spec = _load_goal_spec(os.path.join(tmpdir, ".torchlight", "goal_spec.json"))
        tasks = goal_spec.get("tasks", [])
        assert len(tasks) == 1
        assert tasks[0]["status"] in ("completed", "verified")
