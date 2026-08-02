"""
Unit tests for Tree-of-Thoughts / Branching Evaluator in AutonomousHarness.
"""

import tempfile
from pathlib import Path
from core.execution.autonomous_harness import AutonomousHarness, TaskSpec
from core.memory.manager import MemoryConfig, TieredMemory


def test_evaluate_candidate_branches_syntax_ranking():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        memory = TieredMemory(MemoryConfig())
        harness = AutonomousHarness(root, memory)
        task = TaskSpec(id="t1", description="Refactor auth", target_files=["auth.py"])

        candidates = [
            {
                "id": "c1",
                "file": "auth.py",
                "patch": "def auth():\n    print('unbalanced ('\n",
            },
            {
                "id": "c2",
                "file": "auth.py",
                "patch": "def auth():\n    return True\n",
            },
        ]

        best = harness.evaluate_candidate_branches(task, candidates)
        assert best is not None
        assert best["id"] == "c2"
        assert best["score"] == 100.0
