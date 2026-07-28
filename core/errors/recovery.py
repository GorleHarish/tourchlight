"""
Recovery engine for Torchlight errors.

Provides structured recovery strategies and hint generation for the LLM.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from .types import (
    TorchlightError,
    ToolError,
    ParseError,
    ContextOverflowError,
    ConnectionError,
    SecurityError,
    ToolValidationError,
    TestFailureError,
    RecoveryAction,
)



# ── Recovery hints per error type ──────────────────────────────────────────

_TOOL_ERROR_HINTS: dict[str, Callable[[ToolError], str]] = {
    "FileNotFound": lambda e: (
        f"File '{e.tool_args.get('path', '')}' not found. "
        "Use GREP or RUN_COMMAND('find . -name ...') to locate it first."
    ),
    "PermissionDenied": lambda e: (
        "Permission denied. Check directory permissions with RUN_COMMAND('ls -la')."
    ),
    "IsADirectory": lambda e: (
        f"'{e.tool_args.get('path', '')}' is a directory, not a file. "
        "Use RUN_COMMAND('ls <path>') to list it."
    ),
    "BinaryFile": lambda e: (
        "This is a binary file and cannot be read as text."
    ),
    "FileTooLarge": lambda e: (
        "File is too large to read entirely. Use READ_FILE with a line range (e.g. path:1-50)."
    ),
    "CommandTimeout": lambda e: (
        "Command timed out. Try a simpler command or increase timeout."
    ),
    "CommandFailed": lambda e: (
        f"Command exited with code {e.context.get('returncode', '?')}. "
        "Check stderr for details."
    ),
    "UnknownTool": lambda e: (
        f"Unknown tool '{e.tool_name}'. "
        f"Available tools: READ_FILE, WRITE_FILE, EDIT_FILE, GREP, RUN_COMMAND, etc."
    ),
}

_PARSE_ERROR_HINTS: dict[str, Callable[[ParseError], str]] = {
    "malformed_json": lambda e: (
        "Could not parse tool call JSON. "
        "Retry with explicit format: <tool_call>{\"name\": \"TOOL\", \"arguments\": {...}}</tool_call>"
    ),
    "missing_tool_tag": lambda e: (
        "No tool call tag found. "
        "Output tool calls as: <tool_call>{\"name\": \"TOOL\", \"arguments\": {...}}</tool_call>"
    ),
    "truncated_response": lambda e: (
        "Response was truncated. Increase max_tokens or shorten the request."
    ),
    "bare_call_syntax": lambda e: (
        "For small context models, use bare call syntax at end of response: "
        "TOOL_NAME(\"arg\")"
    ),
}


def get_recovery_hint(error: TorchlightError) -> str:
    """Return a one-line hint for the LLM on how to recover from this error."""
    if isinstance(error, ToolError):
        # Match by error message keywords
        msg_lower = (error.reason or error.message).lower()
        for keyword, hint_fn in _TOOL_ERROR_HINTS.items():
            # Match camelCase keyword against space-separated words in message
            # e.g., "FileNotFound" matches "file not found"
            # Split camelCase on uppercase boundaries: "FileNotFound" -> ["File", "Not", "Found"]
            import re as _re
            words = _re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', keyword)
            words_lower = [w.lower() for w in words]
            # Check if all words appear in the message
            if all(w in msg_lower for w in words_lower):
                return hint_fn(error)
        # Generic tool error hint
        return f"Tool '{error.tool_name}' failed. Try a different approach or adjust arguments."

    if isinstance(error, ParseError):
        for keyword, hint_fn in _PARSE_ERROR_HINTS.items():
            if keyword in (error.parser_used or "").lower():
                return hint_fn(error)
        return "Could not parse response. Retry with explicit tool call format."

    if isinstance(error, ContextOverflowError):
        return "Context is full. Compress older messages or start a new session."

    if isinstance(error, ConnectionError):
        return f"Cannot reach {error.provider}. Check if the server is running."

    if isinstance(error, SecurityError):
        return "That path is outside the workspace. Use a relative path instead."

    if isinstance(error, ToolValidationError):
        hints = []
        if error.missing_fields:
            hints.append(f"Missing required fields: {error.missing_fields}")
        if error.invalid_fields:
            hints.append(f"Invalid fields: {list(error.invalid_fields.keys())}")
        return " ".join(hints) if hints else "Tool call failed validation."

    if isinstance(error, TestFailureError):
        fails_str = ", ".join(error.failing_tests[:3]) if error.failing_tests else "test suite"
        return (
            f"Post-edit test failure in {fails_str}. "
            "Inspect the surgical traceback and fix the syntax or logic error immediately."
        )

    return "An error occurred. Try a different approach."



# ── Recovery engine ────────────────────────────────────────────────────────

@dataclass
class RecoveryState:
    """Tracks retry state for a specific error pattern."""
    error_key: str
    count: int = 0
    last_action: Optional[RecoveryAction] = None


class RecoveryEngine:
    """
    Manages recovery strategies across the agentic loop.

    Tracks per-error-type retry counts and escalates through:
    RETRY → COMPRESS_AND_RETRY → SKIP → ABORT
    """

    MAX_RETRIES = 3
    MAX_COMPRESS_RETRIES = 1

    def __init__(self):
        self._states: dict[str, RecoveryState] = {}

    def _error_key(self, error: TorchlightError) -> str:
        """Generate a dedup key for this error type."""
        if isinstance(error, ToolError):
            reason_str = (error.reason or error.message or "")[:50]
            return f"tool:{error.tool_name}:{reason_str}"
        if isinstance(error, ParseError):
            return f"parse:{error.parser_used}"
        return f"error:{type(error).__name__}"

    def handle(self, error: TorchlightError) -> RecoveryAction:
        """
        Decide what to do after an error.

        Returns a RecoveryAction indicating the next step.
        """
        if not error.recoverable:
            return RecoveryAction.ABORT

        key = self._error_key(error)
        state = self._states.get(key)
        if state is None:
            state = RecoveryState(error_key=key)
            self._states[key] = state

        state.count += 1

        # Escalation ladder
        if state.count <= self.MAX_RETRIES:
            state.last_action = RecoveryAction.RETRY
            return RecoveryAction.RETRY

        if state.count <= self.MAX_RETRIES + self.MAX_COMPRESS_RETRIES:
            state.last_action = RecoveryAction.COMPRESS_AND_RETRY
            return RecoveryAction.COMPRESS_AND_RETRY

        if isinstance(error, SecurityError):
            state.last_action = RecoveryAction.ABORT
            return RecoveryAction.ABORT

        state.last_action = RecoveryAction.SKIP
        return RecoveryAction.SKIP

    def reset(self) -> None:
        """Reset all retry state (e.g., on new conversation turn)."""
        self._states.clear()

    def reset_error(self, error_key: str) -> None:
        """Reset retry state for a specific error."""
        self._states.pop(error_key, None)

    def should_ask_user(self, error: TorchlightError) -> bool:
        """Check if we should escalate to the user after exhausting retries."""
        key = self._error_key(error)
        state = self._states.get(key)
        if state is None:
            return False
        return state.count > self.MAX_RETRIES + self.MAX_COMPRESS_RETRIES
