"""
Anti-Looping Trajectory Lock and Tool Payload Signature Deduplication.

Provides payload normalization, SHA256 signature hashing, rolling-window duplicate
detection, and anti-loop hint generation.
"""

from collections import deque
import hashlib
import json
import os
import re
from typing import Any, List, Optional, Tuple, Deque


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
    Excludes volatile metadata keys (task_id, description, rationale) so semantic
    duplicates are accurately detected even if task/subtask IDs change.
    """
    tool_upper = (tool_name or "").strip().upper()
    norm_args = normalize_tool_args(args)
    if isinstance(norm_args, dict):
        volatile_keys = {
            "task_id",
            "description",
            "rationale",
            "thought",
            "step",
            "subtask_id",
            "comment",
        }
        filtered_args = {
            k: v
            for k, v in norm_args.items()
            if str(k).lower() not in volatile_keys
        }
    else:
        filtered_args = norm_args
    canonical_json = json.dumps(filtered_args, sort_keys=True, default=str)
    raw_key = f"{tool_upper}:{canonical_json}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_alternate_trajectory_hint(tool_name: str, prior_error: str = "", target_path: str = "") -> str:
    """
    Generate tool-specific actionable guidance for breaking trajectory lock when duplicate calls occur.
    
    Args:
        tool_name: The tool that was called
        prior_error: The error/output from the previous execution (if any), used to provide context-aware guidance
        target_path: Concrete target file or symbol path being operated on
    """
    t_upper = (tool_name or "").strip().upper()
    error_lower = prior_error.lower() if prior_error else ""
    path_arg = str(target_path).strip() if target_path else "target_file"

    if t_upper in ("EDIT_FILE", "EDIT"):
        if "no change" in error_lower or "identical" in error_lower:
            return (
                f"⛔ [DUPLICATE EDIT_FILE BLOCKED]: The old_text and new_text are identical for '{path_arg}'.\n"
                f"Next required action: Run READ_FILE to see current content, then provide different old_text vs new_text:\n"
                f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{path_arg}"}}}}</tool_call>'
            )
        if "not found" in error_lower or "could not locate" in error_lower:
            return (
                f"⛔ [DUPLICATE EDIT_FILE BLOCKED]: old_text was not found in '{path_arg}'.\n"
                f"Next required action: Run READ_FILE to inspect exact lines of '{path_arg}':\n"
                f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{path_arg}"}}}}</tool_call>'
            )
        if "matches" in error_lower and "location" in error_lower:
            return (
                f"⛔ [DUPLICATE EDIT_FILE BLOCKED]: old_text matches multiple locations in '{path_arg}'.\n"
                f"Next required action: Run READ_FILE to identify exact line numbers:\n"
                f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{path_arg}"}}}}</tool_call>'
            )
        return (
            f"⛔ [DUPLICATE EDIT_FILE BLOCKED]: You repeated the exact same EDIT_FILE call on '{path_arg}'.\n"
            f"Next required action: Run READ_FILE to inspect line numbers and indentation before retrying:\n"
            f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{path_arg}"}}}}</tool_call>'
        )

    if t_upper in ("WRITE_FILE", "WRITE"):
        if "already exists" in error_lower or "file exists" in error_lower:
            return (
                f"⛔ [DUPLICATE WRITE_FILE BLOCKED]: The file '{path_arg}' already exists.\n"
                f"Next required action: Run READ_FILE to inspect current content, then edit surgically with EDIT_FILE:\n"
                f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{path_arg}"}}}}</tool_call>'
            )
        return (
            f"⛔ [DUPLICATE WRITE_FILE BLOCKED]: You repeated the exact same WRITE_FILE payload on '{path_arg}'.\n"
            f"Next required action: Inspect the written file with READ_FILE, or move to the next task:\n"
            f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{path_arg}"}}}}</tool_call>'
        )

    if t_upper in ("RUN_COMMAND", "EXECUTE", "EXECUTE_SHELL", "SHELL", "COMMAND", "RUN"):
        return (
            "⛔ [DUPLICATE RUN_COMMAND BLOCKED]: You repeated the exact same command without code edits.\n"
            "Next required action: Inspect source files with READ_FILE to locate and fix errors before re-running:\n"
            f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{path_arg}"}}}}</tool_call>'
        )

    if t_upper in ("READ_FILE", "READ", "READ_SYMBOLS"):
        if "not found" in error_lower or "does not exist" in error_lower:
            return (
                f"⛔ [DUPLICATE READ_FILE BLOCKED]: '{path_arg}' does not exist on disk.\n"
                f"Next required action: Create the file now using WRITE_FILE:\n"
                f'<tool_call>{{"name": "WRITE_FILE", "arguments": {{"path": "{path_arg}", "content": "// Code implementation here\\n"}}}}</tool_call>'
            )
        return (
            f"⛔ [DUPLICATE READ_FILE BLOCKED]: You already read '{path_arg}'.\n"
            f"Next required action: Submit your code edits using EDIT_FILE or WRITE_FILE:\n"
            f'<tool_call>{{"name": "EDIT_FILE", "arguments": {{"path": "{path_arg}", "old_text": "...", "new_text": "..."}}}}</tool_call>'
        )

    if t_upper in ("SEARCH_AST", "GREP"):
        return (
            f"⛔ [DUPLICATE {t_upper} BLOCKED]: You repeated the exact same search query.\n"
            f"Next required action: Inspect target files directly with READ_FILE:\n"
            f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{path_arg}"}}}}</tool_call>'
        )

    if t_upper in ("LIST_DIR", "LIST", "LS", "DIR"):
        return (
            "⛔ [DUPLICATE LIST_DIR BLOCKED]: Directory contents were already returned.\n"
            f"Next required action: Inspect discovered files with READ_FILE:\n"
            f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{path_arg}"}}}}</tool_call>'
        )

    return (
        f"⛔ [DUPLICATE {t_upper} BLOCKED]: You repeated the exact same parameters.\n"
        f"Next required action: Emit an alternative tool call with updated parameters:\n"
        f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{path_arg}"}}}}</tool_call>'
    )


class TrajectoryLock:
    """
    Rolling-window deduplication lock for non-read-only tool calls.
    Prevents infinite execution loops caused by identical or near-identical tool payloads.
    """

    def __init__(self, window_size: int = 10, max_duplicates: int = 3):
        self.window_size = window_size
        self.max_duplicates = max_duplicates
        # Rolling ring-buffer history: (payload_hash, tool_name, normalized_args)
        self.history: Deque[Tuple[str, str, Any]] = deque(maxlen=window_size)
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

        # Anti-Pattern Detection: Sequential edit stepping & duplicate payload detection
        tool_upper = (tool_name or "").strip().upper()
        if tool_upper in ("EDIT_FILE", "EDIT") and isinstance(args, dict):
            cur_path = str(args.get("path", "")).strip()
            cur_s = args.get("start_line")
            cur_e = args.get("end_line")
            cur_new = str(args.get("new_text") or args.get("content") or "").strip()

            # 1. Check if identical new_text modification was already attempted on the same path
            if cur_new and len(cur_new) >= 15:
                for h in reversed(self.history):
                    if h[1] in ("EDIT_FILE", "EDIT") and isinstance(h[2], dict):
                        h_path = str(h[2].get("path", "")).strip()
                        h_new = str(h[2].get("new_text") or h[2].get("content") or "").strip()
                        if h_path == cur_path and h_new == cur_new:
                            hint = (
                                f"⛔ [DUPLICATE EDIT_FILE PAYLOAD BLOCKED]: You repeated the exact same 'new_text' modification on '{cur_path}'.\n"
                                f"Next required action: Run READ_FILE to inspect current file content before retrying or moving to the next task:\n"
                                f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{cur_path}"}}}}</tool_call>'
                            )
                            return True, 2, hint

            # 2. Check for sequential line-by-line or range stepping across turns
            if cur_s is not None or cur_e is not None:
                try:
                    s_digits = re.sub(r"[^\d]", "", str(cur_s or ""))
                    e_digits = re.sub(r"[^\d]", "", str(cur_e or ""))
                    if not s_digits and not e_digits:
                        raise ValueError("No line digits")
                    s_int = int(s_digits) if s_digits else int(e_digits)
                    e_int = int(e_digits) if e_digits else s_int
                    consec_stepping = 0
                    consec_1line = 0
                    curr_start = s_int

                    for h in reversed(self.history):
                        if h[1] in ("EDIT_FILE", "EDIT") and isinstance(h[2], dict):
                            h_path = str(h[2].get("path", "")).strip()
                            h_s = h[2].get("start_line")
                            h_e = h[2].get("end_line")
                            if h_path == cur_path and (h_s is not None or h_e is not None):
                                hs_digits = re.sub(r"[^\d]", "", str(h_s or ""))
                                he_digits = re.sub(r"[^\d]", "", str(h_e or ""))
                                if not hs_digits and not he_digits:
                                    break
                                hs_int = int(hs_digits) if hs_digits else int(he_digits)
                                he_int = int(he_digits) if he_digits else hs_int
                                if s_int == e_int and hs_int == he_int:
                                    consec_1line += 1
                                elif (hs_int < curr_start and curr_start <= he_int + 2) or (hs_int == hs_int and he_int == curr_start):
                                    consec_stepping += 1
                                    curr_start = hs_int
                                else:
                                    break
                            else:
                                break
                        else:
                            break

                    if consec_1line >= 2:
                        hint = (
                            f"⛔ [LINE-BY-LINE EDITING DETECTED]: You are modifying '{cur_path}' one line at a time across separate turns (L{s_int}-L{e_int}).\n"
                            f"Do NOT make sequential 1-line edits. Read '{cur_path}' to inspect the full function, then write the entire block in a single surgical EDIT_FILE call:\n"
                            f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{cur_path}"}}}}</tool_call>'
                        )
                        return True, consec_1line + 1, hint

                    if consec_stepping >= 2:
                        hint = (
                            f"⛔ [SEQUENTIAL RANGE STEPPING DETECTED]: You are modifying '{cur_path}' in small sequential chunks across separate turns (L{s_int}-L{e_int}).\n"
                            f"Do NOT simulate line-range stepping. Read '{cur_path}' to inspect the full function, then write the entire block in a single surgical EDIT_FILE call:\n"
                            f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{cur_path}"}}}}</tool_call>'
                        )
                        return True, consec_stepping + 1, hint
                except (ValueError, TypeError):
                    pass

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

            # Extract target path from args if available
            t_path = ""
            if isinstance(args, dict):
                t_path = str(
                    args.get("path")
                    or args.get("file")
                    or args.get("target")
                    or args.get("filename")
                    or args.get("file_path")
                    or args.get("filepath")
                    or ""
                ).strip()

            # Pass the prior error and target_path to get context-aware guidance
            alt_guidance = get_alternate_trajectory_hint(tool_name, last_out, target_path=t_path)
            hint = (
                f"⚠️ Trajectory Lock: Duplicate '{tool_upper}' call blocked ({dup_count} attempts with identical parameters).{prior_error_ctx}\n\n"
                f"{alt_guidance}\n\n"
                f"Do NOT repeat the exact same tool payload. Emit your next action inside <tool_call>...</tool_call> tags now."
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
        # Keep consecutive counts and payload outputs pruned to active window entries
        active_hashes = {h[0] for h in self.history}
        self.consecutive_counts = {
            k: v for k, v in self.consecutive_counts.items() if k in active_hashes
        }
        self.payload_outputs = {
            k: v for k, v in self.payload_outputs.items() if k in active_hashes
        }

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

