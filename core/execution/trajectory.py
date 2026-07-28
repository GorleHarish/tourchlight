"""
Session Trajectory Logger & Audit Exporter for Torchlight.

Records full agent execution trajectories to disk in JSONL format:
`.torchlight/trajectories/<session_id>.jsonl`

Enables offline evaluation, post-mortem analysis, and benchmarking.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import os


@dataclass
class TrajectoryStep:
    step_index: int
    phase: str
    prompt: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    test_status: Optional[str] = None
    duration_ms: float = 0.0
    tokens_used: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class TrajectoryLogger:
    """Session trajectory recorder writing structured JSONL steps to disk."""

    def __init__(self, project_root: str, session_id: Optional[str] = None):
        self.project_root = Path(project_root).resolve()
        if not session_id:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = session_id
        self.trajectories_dir = self.project_root / ".torchlight" / "trajectories"
        self.file_path = self.trajectories_dir / f"{self.session_id}.jsonl"
        self._step_counter = 0

    def record_step(
        self,
        phase: str,
        prompt: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        test_status: Optional[str] = None,
        duration_ms: float = 0.0,
        tokens_used: int = 0,
    ) -> TrajectoryStep:
        self._step_counter += 1
        step = TrajectoryStep(
            step_index=self._step_counter,
            phase=phase,
            prompt=prompt[:500],  # Truncate prompt for compact log
            tool_calls=tool_calls or [],
            tool_results=tool_results or [],
            test_status=test_status,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
        )

        try:
            self.trajectories_dir.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(step)) + "\n")
        except Exception:
            pass

        return step
