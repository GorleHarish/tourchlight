"""
Structured error types for Torchlight.

Every error carries context for automated recovery strategies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class RecoveryAction(Enum):
    """What the recovery engine should do after an error."""
    RETRY = "retry"
    COMPRESS_AND_RETRY = "compress_and_retry"
    SKIP = "skip"
    ABORT = "abort"
    ASK_USER = "ask_user"


@dataclass
class TorchlightError(Exception):
    """Base error with structured context."""
    message: str = ""
    context: dict = field(default_factory=dict)
    recoverable: bool = True
    source: str = ""

    def __str__(self) -> str:
        prefix = f"[{self.source}] " if self.source else ""
        return f"{prefix}{self.message}"


@dataclass
class ToolError(TorchlightError):
    """Tool execution failed."""
    tool_name: str = ""
    tool_args: dict = field(default_factory=dict)
    reason: str = ""
    error_output: str = ""

    def __post_init__(self):
        if not self.message and self.reason:
            self.message = f"{self.tool_name}: {self.reason}"


@dataclass
class ParseError(TorchlightError):
    """LLM output could not be parsed into a valid tool call or response."""
    raw_output: str = ""
    parser_used: str = ""
    expected_format: str = ""


@dataclass
class ContextOverflowError(TorchlightError):
    """Context window exceeded."""
    token_count: int = 0
    max_tokens: int = 0

    def __post_init__(self):
        if not self.message:
            self.message = (
                f"Context overflow: {self.token_count:,} tokens used, "
                f"{self.max_tokens:,} max"
            )


@dataclass
class ConnectionError(TorchlightError):
    """LLM backend unreachable."""
    provider: str = ""
    base_url: str = ""
    attempt: int = 0
    max_attempts: int = 3

    def __post_init__(self):
        if not self.message:
            self.message = (
                f"Cannot connect to {self.provider} at {self.base_url} "
                f"(attempt {self.attempt}/{self.max_attempts})"
            )


@dataclass
class SecurityError(TorchlightError):
    """Path or command outside allowed scope."""
    attempted: str = ""
    allowed_scope: str = ""

    def __post_init__(self):
        self.recoverable = False
        if not self.message:
            self.message = (
                f"Access denied: '{self.attempted}' is outside "
                f"the allowed scope '{self.allowed_scope}'"
            )


@dataclass
class ToolValidationError(TorchlightError):
    """Tool call failed schema validation."""
    tool_name: str = ""
    missing_fields: list = field(default_factory=list)
    invalid_fields: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.message:
            parts = []
            if self.missing_fields:
                parts.append(f"missing: {self.missing_fields}")
            if self.invalid_fields:
                parts.append(f"invalid: {list(self.invalid_fields.keys())}")
            self.message = f"Validation failed for {self.tool_name}: {'; '.join(parts)}"


@dataclass
class TestFailureError(TorchlightError):
    """Post-edit auto-run test suite failure."""
    __test__ = False
    command: str = ""
    failing_tests: list[str] = field(default_factory=list)
    surgical_traceback: str = ""
    return_code: int = 1


    def __post_init__(self):
        if not self.message:
            fails_str = ", ".join(self.failing_tests) if self.failing_tests else "test suite"
            self.message = f"Post-edit test failure ({self.command}): {fails_str}"

