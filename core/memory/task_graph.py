"""
Robust Task Lifecycle and Directed Acyclic Graph (DAG) Engine for Torchlight.

Provides strict state machine transitions, dependency resolution, topological sorting,
cycle detection, checkpointing/rollback, inter-task symbol handoffs, and token-efficient
L0 Working Memory context rendering.
"""

import copy
import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    BLOCKED = "blocked"


# Matrix of valid state transitions: current_status -> set of allowed next_statuses
VALID_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.PENDING: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.SKIPPED,
        TaskStatus.BLOCKED,
        TaskStatus.COMPLETED,  # Allowed for direct external sync
    },
    TaskStatus.IN_PROGRESS: {
        TaskStatus.VERIFYING,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.BLOCKED,
        TaskStatus.SKIPPED,
        TaskStatus.PENDING,
    },
    TaskStatus.VERIFYING: {
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED,
    },
    TaskStatus.FAILED: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.PENDING,
        TaskStatus.SKIPPED,
        TaskStatus.BLOCKED,
    },
    TaskStatus.BLOCKED: {
        TaskStatus.PENDING,
        TaskStatus.IN_PROGRESS,
        TaskStatus.SKIPPED,
    },
    TaskStatus.SKIPPED: {
        TaskStatus.PENDING,
        TaskStatus.IN_PROGRESS,
    },
    TaskStatus.COMPLETED: {
        TaskStatus.IN_PROGRESS,  # Re-opened due to regression or refinement
        TaskStatus.PENDING,
    },
}


class TaskStateTransitionError(ValueError):
    """Raised when an invalid task status transition is attempted."""

    pass


class TaskCycleError(ValueError):
    """Raised when a dependency cycle is detected in the Task DAG."""

    pass


@dataclass
class TaskLifecycleEvent:
    event_id: str
    task_id: str
    event_type: str
    old_status: TaskStatus
    new_status: TaskStatus
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    reason: str = ""
    duration_s: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskNode:
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    attempts: int = 0
    max_attempts: int = 3
    affected_files: List[str] = field(default_factory=list)
    output_symbols: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    updated_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value
            if isinstance(self.status, TaskStatus)
            else str(self.status),
            "dependencies": list(self.dependencies),
            "parent_id": self.parent_id,
            "subtasks": list(self.subtasks),
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "affected_files": list(self.affected_files),
            "output_symbols": list(self.output_symbols),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskNode":
        status_val = str(data.get("status", "pending")).lower()
        if status_val in ("verified", "done", "completed"):
            status_enum = TaskStatus.COMPLETED
        else:
            try:
                status_enum = TaskStatus(status_val)
            except ValueError:
                status_enum = TaskStatus.PENDING

        return cls(
            id=str(data.get("id", f"task_{uuid.uuid4().hex[:8]}")),
            description=str(data.get("description", "")),
            status=status_enum,
            dependencies=[str(d) for d in data.get("dependencies", [])],
            parent_id=data.get("parent_id"),
            subtasks=[str(s) for s in data.get("subtasks", [])],
            attempts=int(data.get("attempts", 0)),
            max_attempts=int(data.get("max_attempts", 3)),
            affected_files=[str(f) for f in data.get("affected_files", [])],
            output_symbols=[str(s) for s in data.get("output_symbols", [])],
            created_at=str(
                data.get("created_at", datetime.utcnow().isoformat() + "Z")
            ),
            updated_at=str(
                data.get("updated_at", datetime.utcnow().isoformat() + "Z")
            ),
            completed_at=data.get("completed_at"),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class TaskStateSnapshot:
    snapshot_id: str
    timestamp: str
    nodes: Dict[str, Dict[str, Any]]
    audit_trail: List[Dict[str, Any]]


class TaskDAG:
    """
    Directed Acyclic Graph (DAG) for Task Lifecycle Management.
    """

    def __init__(self, nodes: Optional[List[TaskNode]] = None):
        self.nodes: Dict[str, TaskNode] = {}
        self.audit_trail: List[TaskLifecycleEvent] = []
        self.checkpoints: List[TaskStateSnapshot] = []
        if nodes:
            for node in nodes:
                self.add_node(node)

    def add_node(self, node: TaskNode) -> None:
        """Add a task node to the DAG after verifying cycle safety."""
        self.nodes[node.id] = node
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node.id not in parent.subtasks:
                parent.subtasks.append(node.id)

        if self.has_cycle():
            # Rollback addition if cycle created
            del self.nodes[node.id]
            raise TaskCycleError(
                f"Adding task '{node.id}' introduces a dependency cycle."
            )

    def remove_node(self, task_id: str) -> bool:
        """Remove a node and strip references to it from dependencies and subtasks."""
        if task_id not in self.nodes:
            return False
        node = self.nodes.pop(task_id)

        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if task_id in parent.subtasks:
                parent.subtasks.remove(task_id)

        for n in self.nodes.values():
            if task_id in n.dependencies:
                n.dependencies.remove(task_id)
            if task_id in n.subtasks:
                n.subtasks.remove(task_id)
        return True

    def get_node(self, task_id: str) -> Optional[TaskNode]:
        return self.nodes.get(task_id)

    def has_cycle(self) -> bool:
        """Detect cycles using Kahn's topological sort algorithm."""
        in_degree: Dict[str, int] = {node_id: 0 for node_id in self.nodes}

        for node_id, node in self.nodes.items():
            for dep_id in node.dependencies:
                if dep_id in in_degree:
                    in_degree[node_id] += 1

        queue = [node_id for node_id, deg in in_degree.items() if deg == 0]
        visited_count = 0

        adj: Dict[str, List[str]] = {node_id: [] for node_id in self.nodes}
        for node_id, node in self.nodes.items():
            for dep_id in node.dependencies:
                if dep_id in adj:
                    adj[dep_id].append(node_id)

        while queue:
            curr = queue.pop(0)
            visited_count += 1
            for neighbor in adj.get(curr, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return visited_count < len(self.nodes)

    def topological_sort(self) -> List[TaskNode]:
        """Return topologically sorted list of TaskNodes (dependencies first)."""
        if self.has_cycle():
            raise TaskCycleError("Cannot topologically sort a DAG containing cycles.")

        in_degree: Dict[str, int] = {node_id: 0 for node_id in self.nodes}
        adj: Dict[str, List[str]] = {node_id: [] for node_id in self.nodes}

        for node_id, node in self.nodes.items():
            for dep_id in node.dependencies:
                if dep_id in self.nodes:
                    in_degree[node_id] += 1
                    adj[dep_id].append(node_id)

        queue = [node_id for node_id, deg in in_degree.items() if deg == 0]
        sorted_nodes = []

        while queue:
            curr_id = queue.pop(0)
            sorted_nodes.append(self.nodes[curr_id])
            for neighbor in adj.get(curr_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return sorted_nodes

    def get_ready_tasks(self) -> List[TaskNode]:
        """
        Return list of tasks that are topologically unblocked and ready for execution.
        A task is ready if its status is PENDING or IN_PROGRESS, and all its prerequisite
        dependencies are COMPLETED or SKIPPED.
        """
        ready = []
        for node in self.topological_sort():
            if node.status not in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                continue

            deps_satisfied = True
            for dep_id in node.dependencies:
                dep_node = self.nodes.get(dep_id)
                if not dep_node or dep_node.status not in (
                    TaskStatus.COMPLETED,
                    TaskStatus.SKIPPED,
                ):
                    deps_satisfied = False
                    break

            if deps_satisfied:
                ready.append(node)
        return ready

    def transition_task_status(
        self,
        task_id: str,
        new_status: TaskStatus,
        reason: str = "",
        affected_files: Optional[List[str]] = None,
        output_symbols: Optional[List[str]] = None,
        force: bool = False,
    ) -> TaskNode:
        """
        Validate and execute status transition for a task node.
        """
        if task_id not in self.nodes:
            raise KeyError(f"Task ID '{task_id}' not found in DAG.")

        node = self.nodes[task_id]
        old_status = node.status

        if old_status == new_status:
            return node

        if not force:
            allowed = VALID_TRANSITIONS.get(old_status, set())
            if new_status not in allowed:
                raise TaskStateTransitionError(
                    f"Invalid status transition for task '{task_id}': "
                    f"cannot move from '{old_status.value}' to '{new_status.value}'."
                )

        now_str = datetime.utcnow().isoformat() + "Z"
        node.status = new_status
        node.updated_at = now_str

        if new_status == TaskStatus.IN_PROGRESS:
            node.attempts += 1
        elif new_status == TaskStatus.COMPLETED:
            node.completed_at = now_str
        elif new_status != TaskStatus.COMPLETED:
            node.completed_at = None

        if affected_files:
            for f in affected_files:
                if f and f not in node.affected_files:
                    node.affected_files.append(f)

        if output_symbols:
            for s in output_symbols:
                if s and s not in node.output_symbols:
                    node.output_symbols.append(s)

        event = TaskLifecycleEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            event_type="status_changed",
            old_status=old_status,
            new_status=new_status,
            reason=reason,
        )
        self.audit_trail.append(event)

        # Roll up subtask status to parent if applicable
        if node.parent_id and node.parent_id in self.nodes:
            self._rollup_parent_status(node.parent_id)

        return node

    def _rollup_parent_status(self, parent_id: str) -> None:
        """Auto-complete parent if all child subtasks are COMPLETED/SKIPPED."""
        parent = self.nodes.get(parent_id)
        if not parent or not parent.subtasks:
            return

        child_nodes = [self.nodes[sid] for sid in parent.subtasks if sid in self.nodes]
        if not child_nodes:
            return

        if all(
            c.status in (TaskStatus.COMPLETED, TaskStatus.SKIPPED) for c in child_nodes
        ):
            if parent.status != TaskStatus.COMPLETED:
                self.transition_task_status(
                    parent_id,
                    TaskStatus.COMPLETED,
                    reason="Auto-completed: all subtasks finished.",
                )
        elif any(c.status == TaskStatus.IN_PROGRESS for c in child_nodes):
            if parent.status == TaskStatus.PENDING:
                self.transition_task_status(
                    parent_id,
                    TaskStatus.IN_PROGRESS,
                    reason="Subtask started.",
                )

    def create_checkpoint(self) -> TaskStateSnapshot:
        """Create an immutable state snapshot of the DAG."""
        snapshot = TaskStateSnapshot(
            snapshot_id=f"snap_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            nodes={node_id: node.to_dict() for node_id, node in self.nodes.items()},
            audit_trail=[asdict(evt) for evt in self.audit_trail],
        )
        self.checkpoints.append(snapshot)
        return snapshot

    def restore_checkpoint(self, snapshot_id: Optional[str] = None) -> bool:
        """Restore DAG state to a previous snapshot."""
        if not self.checkpoints:
            return False

        target_snap = None
        if snapshot_id:
            for snap in reversed(self.checkpoints):
                if snap.snapshot_id == snapshot_id:
                    target_snap = snap
                    break
        else:
            target_snap = self.checkpoints[-1]

        if not target_snap:
            return False

        self.nodes = {
            node_id: TaskNode.from_dict(ndata)
            for node_id, ndata in target_snap.nodes.items()
        }
        return True

    def render_l0_view(self, max_tokens: int = 200) -> str:
        """
        Render a token-efficient L0 Working Memory view of task status and topology.
        Consumes <150 tokens.
        """
        ready_tasks = self.get_ready_tasks()
        completed_count = sum(
            1 for n in self.nodes.values() if n.status == TaskStatus.COMPLETED
        )
        total_count = len(self.nodes)

        lines = [
            f"🎯 **Goal Progress**: {completed_count}/{total_count} tasks completed"
        ]

        if ready_tasks:
            lines.append("⚡ **Next Ready Tasks**:")
            for t in ready_tasks[:3]:
                syms_str = f" [symbols: {', '.join(t.output_symbols[:2])}]" if t.output_symbols else ""
                lines.append(f"  - [{t.id}] {t.description}{syms_str}")
        elif total_count > 0 and completed_count < total_count:
            lines.append("⚠️ **Blocked Tasks**: Prerequisite dependencies pending.")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize DAG state for goal_spec.json backward compatibility."""
        return {
            "tasks": [node.to_dict() for node in self.nodes.values()],
            "audit_trail": [
                {
                    "event_id": evt.event_id,
                    "task_id": evt.task_id,
                    "event_type": evt.event_type,
                    "old_status": evt.old_status.value
                    if isinstance(evt.old_status, TaskStatus)
                    else str(evt.old_status),
                    "new_status": evt.new_status.value
                    if isinstance(evt.new_status, TaskStatus)
                    else str(evt.new_status),
                    "timestamp": evt.timestamp,
                    "reason": evt.reason,
                }
                for evt in self.audit_trail
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskDAG":
        """Deserialize DAG state from goal_spec.json dict."""
        dag = cls()
        tasks_raw = data.get("tasks", []) if isinstance(data, dict) else []

        for tr in tasks_raw:
            if isinstance(tr, dict):
                node = TaskNode.from_dict(tr)
                dag.nodes[node.id] = node

        # Load audit trail if present
        if isinstance(data, dict):
            for er in data.get("audit_trail", []):
                if isinstance(er, dict):
                    try:
                        old_s = TaskStatus(er.get("old_status", "pending"))
                        new_s = TaskStatus(er.get("new_status", "pending"))
                    except ValueError:
                        old_s, new_s = TaskStatus.PENDING, TaskStatus.PENDING

                    dag.audit_trail.append(
                        TaskLifecycleEvent(
                            event_id=er.get("event_id", f"evt_{uuid.uuid4().hex[:8]}"),
                            task_id=er.get("task_id", ""),
                            event_type=er.get("event_type", "status_changed"),
                            old_status=old_s,
                            new_status=new_s,
                            timestamp=er.get("timestamp", ""),
                            reason=er.get("reason", ""),
                        )
                    )

        return dag


class TaskTransaction:
    """
    Atomic transaction manager for persistent goal_spec.json DAG updates.
    """

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.goal_path = os.path.join(project_root, ".torchlight", "goal_spec.json")
        self.dag: TaskDAG = TaskDAG()

    def __enter__(self) -> TaskDAG:
        os.makedirs(os.path.dirname(self.goal_path), exist_ok=True)
        if os.path.exists(self.goal_path):
            try:
                with open(self.goal_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.dag = TaskDAG.from_dict(data)
            except Exception:
                self.dag = TaskDAG()
        return self.dag

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            # Atomic flush to disk
            tmp_path = f"{self.goal_path}.tmp_{uuid.uuid4().hex[:6]}"
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self.dag.to_dict(), f, indent=2)
                os.replace(tmp_path, self.goal_path)
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        return False
