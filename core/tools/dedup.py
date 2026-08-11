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


def get_alternate_trajectory_hint(tool_name: str) -> str:
    """
    Generate tool-specific actionable guidance for breaking trajectory lock when duplicate calls occur.
    """
    t_upper = (tool_name or "").strip().upper()

    if t_upper in ("EDIT_FILE", "EDIT"):
        return (
            "💡 Alternate trajectory guidance for EDIT_FILE:\n"
            "1. Use READ_FILE to inspect exact line numbers, indentation/whitespace, and surrounding context.\n"
            "2. Switch to WRITE_FILE to overwrite full file contents cleanly if surgical replacement/diff matching fails or returns 'No change'.\n"
            "3. If using EDIT_FILE, specify exact line ranges ('start_line'/'end_line') or target 'symbol_name'."
        )

    if t_upper in ("WRITE_FILE", "WRITE"):
        return (
            "💡 Alternate trajectory guidance for WRITE_FILE:\n"
            "1. Use READ_FILE to inspect current file content and verify whether your intended changes were already written.\n"
            "2. Switch to EDIT_FILE with targeted 'old_text'/'new_text' or 'start_line'/'end_line' ranges for surgical edits."
        )

    if t_upper in ("RUN_COMMAND", "EXECUTE", "EXECUTE_SHELL", "SHELL", "COMMAND", "RUN"):
        return (
            "💡 Alternate trajectory guidance for command execution:\n"
            "1. Do NOT re-run the exact same command payload without modifications.\n"
            "2. Use READ_FILE or GREP to inspect relevant source code, test tracebacks, or config files first.\n"
            "3. Modify command arguments/flags, fix underlying code errors, or run a targeted diagnostic command."
        )

    if t_upper in ("SEARCH_AST", "GREP"):
        return (
            f"💡 Alternate trajectory guidance for {t_upper}:\n"
            "1. Modify your search query, use regex patterns, or broaden search scope/directories.\n"
            "2. Use READ_FILE directly on target files if search results are unclear."
        )

    return (
        f"💡 Alternate trajectory guidance for {t_upper}:\n"
        "1. Try an alternative tool (e.g., READ_FILE, WRITE_FILE, SEARCH_AST, GREP).\n"
        "2. Modify parameter values or line ranges, or present findings with <FINAL_ANSWER>."
    )


class TrajectoryLock:
    """
    Rolling-window deduplication lock for non-read-only tool calls.
    Prevents infinite execution loops caused by identical or near-identical tool payloads.
    """

    def __init__(self, window_size: int = 10, max_duplicates: int = 3):
        self.window_size = window_size
        self.max_duplicates = max_duplicates
        # History entries: (payload_hash, tool_name, normalized_args)
        self.history: List[Tuple[str, str, Any]] = []
        self.consecutive_counts: dict[str, int] = {}
        self.payload_outputs: dict[str, str] = {}

    def is_duplicate(self, tool_name: str, args: Any, is_read_only: bool = False) -> Tuple[bool, int, str]:
        """
        Check if payload matches any entry in the recent rolling window.

        For read-only tools (is_read_only=True), allows up to 3 repeated reads,
        but soft-blocks on the 4th consecutive identical call to prevent context thrashing.

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

            # Read-only tools get a higher tolerance threshold (soft block after 3 calls)
            if is_read_only and dup_count <= 3:
                return False, 0, ""

            prior_error_ctx = ""
            last_out = self.payload_outputs.get(payload_hash, "")
            if last_out:
                out_snippet = last_out.strip()
                if len(out_snippet) > 350:
                    out_snippet = out_snippet[:350] + "..."
                prior_error_ctx = (
                    f"\n\nPrior execution output for this exact payload:\n"
                    f"```\n{out_snippet}\n```"
                )

            alt_guidance = get_alternate_trajectory_hint(tool_name)
            hint = (
                f"⚠️ Trajectory Lock: You previously called '{tool_upper}' with identical or "
                f"semantically-equivalent arguments {dup_count} time(s).{prior_error_ctx}\n\n"
                f"{alt_guidance}\n\n"
                f"Do NOT repeat the exact same parameters. Address any errors above by taking one of the alternate paths, or present your findings with <FINAL_ANSWER>."
            )
            return True, dup_count, hint

        return False, 0, ""

    def register(self, tool_name: str, args: Any) -> str:
        """
        Record an executed tool call payload into the rolling history window.
        """
        payload_hash = compute_payload_hash(tool_name, args)
        norm_args = normalize_tool_args(args)
        tool_upper = (tool_name or "").strip().upper()

        self.history.append((payload_hash, tool_upper, norm_args))
        if len(self.history) > self.window_size:
            evicted = self.history.pop(0)
            # Reset count and output if no longer in window
            if not any(h[0] == evicted[0] for h in self.history):
                self.consecutive_counts.pop(evicted[0], None)
                self.payload_outputs.pop(evicted[0], None)

        self.consecutive_counts[payload_hash] = self.consecutive_counts.get(payload_hash, 0) + 1
        return payload_hash

    def record_output(self, tool_name: str, args: Any, output: str) -> None:
        """
        Record execution output associated with a tool payload hash for error diagnostic feedback.
        """
        payload_hash = compute_payload_hash(tool_name, args)
        if output:
            self.payload_outputs[payload_hash] = str(output).strip()[:600]

    def reset(self) -> None:
        """Clear rolling trajectory history."""
        self.history.clear()
        self.consecutive_counts.clear()
        self.payload_outputs.clear()

