"""
Anti-Looping Trajectory Lock and Tool Payload Signature Deduplication.

Provides payload normalization, SHA256 signature hashing, rolling-window duplicate
detection, and anti-loop hint generation.
"""

import hashlib
import json
import os
from typing import Any, List, Optional, Tuple


def normalize_tool_args(args: Any, is_path_key: bool = False) -> Any:
    """
    Recursively normalize tool arguments to ensure semantic equality:
    - Dict keys sorted
    - String values stripped of leading/trailing whitespace
    - File path strings normalized (backslash conversion, slash collapsing)
    """
    if isinstance(args, dict):
        normalized = {}
        for k in sorted(args.keys()):
            v = args[k]
            key_lower = str(k).lower()
            looks_like_path = key_lower in ("path", "file", "filepath", "filename", "p", "target")
            normalized[k] = normalize_tool_args(v, is_path_key=looks_like_path)
        return normalized

    if isinstance(args, (list, tuple)):
        return [normalize_tool_args(item, is_path_key=is_path_key) for item in args]

    if isinstance(args, str):
        s = args.strip()
        if is_path_key and s:
            # Normalize path slashes and relative components
            s = os.path.normpath(s.replace("\\", "/"))
        return s

    return args


def compute_payload_hash(tool_name: str, args: Any) -> str:
    """
    Generate SHA256 hex digest of normalized tool payload.
    """
    tool_upper = (tool_name or "").strip().upper()
    norm_args = normalize_tool_args(args)
    canonical_json = json.dumps(norm_args, sort_keys=True, default=str)
    raw_key = f"{tool_upper}:{canonical_json}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class TrajectoryLock:
    """
    Rolling-window deduplication lock for non-read-only tool calls.
    Prevents infinite execution loops caused by identical or near-identical tool payloads.
    """

    def __init__(self, window_size: int = 5, max_duplicates: int = 3):
        self.window_size = window_size
        self.max_duplicates = max_duplicates
        # History entries: (payload_hash, tool_name, normalized_args)
        self.history: List[Tuple[str, str, Any]] = []
        self.consecutive_counts: dict[str, int] = {}

    def is_duplicate(self, tool_name: str, args: Any) -> Tuple[bool, int, str]:
        """
        Check if payload matches any entry in the recent rolling window.

        Returns:
            (is_duplicate, duplicate_count, anti_loop_hint)
        """
        payload_hash = compute_payload_hash(tool_name, args)
        count = self.consecutive_counts.get(payload_hash, 0)

        # Check if hash is in rolling history window
        in_history = any(h[0] == payload_hash for h in self.history)

        if in_history:
            dup_count = count + 1
            tool_upper = (tool_name or "").strip().upper()
            hint = (
                f"⚠️ Trajectory Lock: You previously called '{tool_upper}' with identical or "
                f"semantically-equivalent arguments {dup_count} time(s). "
                f"Do NOT repeat the exact same parameters. Try an alternative tool or approach, "
                f"or present your findings with <FINAL_ANSWER>."
            )
            return True, dup_count, hint

        return False, 0, ""

    def register(self, tool_name: str, args: Any) -> str:
        """
        Record a executed tool call payload into the rolling history window.
        """
        payload_hash = compute_payload_hash(tool_name, args)
        norm_args = normalize_tool_args(args)
        tool_upper = (tool_name or "").strip().upper()

        self.history.append((payload_hash, tool_upper, norm_args))
        if len(self.history) > self.window_size:
            evicted = self.history.pop(0)
            # Reset count if no longer in window
            if not any(h[0] == evicted[0] for h in self.history):
                self.consecutive_counts.pop(evicted[0], None)

        self.consecutive_counts[payload_hash] = self.consecutive_counts.get(payload_hash, 0) + 1
        return payload_hash

    def reset(self) -> None:
        """Clear rolling trajectory history."""
        self.history.clear()
        self.consecutive_counts.clear()
