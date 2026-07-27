import sys
from pathlib import Path

# Add project root and src directory to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import tempfile
import pytest
from rich.console import Console

from context_manager.cli.dashboard import ContextDashboard
try:
    from core.execution.autonomous_harness import AutonomousHarness, TaskStatus
except ImportError:
    AutonomousHarness = None
    TaskStatus = None


def test_render_task_progress_empty():
    dash = ContextDashboard()
    summary = {
        "goal_id": None,
        "title": None,
        "total_tasks": 0,
        "verified": 0,
        "in_progress": 0,
        "pending": 0,
        "failed": 0,
        "skipped": 0,
        "progress_pct": 0.0,
        "tasks": [],
    }
    panel = dash.render_task_progress(summary)
    assert panel is not None
    console = Console(record=True, width=120)
    console.print(panel)
    output = console.export_text()
    assert "No Active Goal" in output
    assert "No sub-agent tasks defined" in output


def test_render_task_progress_with_tasks():
    dash = ContextDashboard()
    summary = {
        "goal_id": "g-test-1",
        "title": "Refactor Memory System",
        "total_tasks": 3,
        "verified": 1,
        "in_progress": 1,
        "pending": 1,
        "failed": 0,
        "skipped": 0,
        "progress_pct": 33.3,
        "tasks": [
            {
                "id": "t1",
                "description": "Create memory models",
                "status": "verified",
                "attempts": 1,
                "max_attempts": 3,
                "target_files": ["models.py"],
                "failure_reasons": [],
            },
            {
                "id": "t2",
                "description": "Implement token counter",
                "status": "in_progress",
                "attempts": 2,
                "max_attempts": 3,
                "target_files": ["token_counter.py"],
                "failure_reasons": ["Token limit exceeded"],
            },
            {
                "id": "t3",
                "description": "Add persistence layer",
                "status": "pending",
                "attempts": 0,
                "max_attempts": 3,
                "target_files": ["persistence.py"],
                "failure_reasons": [],
            },
        ],
    }
    panel = dash.render_task_progress(summary)
    assert panel is not None
    console = Console(record=True, width=120)
    console.print(panel)
    output = console.export_text()
    assert "Refactor Memory System" in output
    assert "33.3%" in output
    assert "t1" in output
    assert "VERIFIED" in output
    assert "t2" in output
    assert "IN_PROGRESS" in output
    assert "Token limit exceeded" in output
