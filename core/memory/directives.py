"""
Directive tracker and constraint violation reinforcement module for Torchlight.
"""

from typing import Any, Dict, Optional


class DirectiveTracker:
    """
    Tracks model constraint violations during execution turns and dynamically
    injects directive reminders into the memory scratchpad.
    """

    def __init__(self):
        self.violations: Dict[str, int] = {}

    def record_violation(self, category: str, detail: str, memory: Optional[Any] = None) -> str:
        """
        Record a directive violation (e.g. 'cd_command', 'test_assertion_delete')
        and push reinforcement hint to memory scratchpad.
        """
        self.violations[category] = self.violations.get(category, 0) + 1
        count = self.violations[category]

        reinforcement_map = {
            "cd_command": (
                f"⚠️ DIRECTIVE VIOLATION ({count}x): Do NOT run 'cd' in shell commands. "
                f"Pass the directory using the 'cwd' tool argument instead."
            ),
            "symptom_patch": (
                f"⚠️ DIRECTIVE VIOLATION ({count}x): Anti-Symptom-Patching rule broken ({detail}). "
                f"Do not swallow exceptions or delete test assertions. Fix the root cause."
            ),
            "read_before_write": (
                f"⚠️ DIRECTIVE VIOLATION ({count}x): Inspect error logs/tracebacks using READ_FILE or GREP "
                f"before attempting code edits."
            ),
        }

        hint = reinforcement_map.get(
            category,
            f"⚠️ DIRECTIVE VIOLATION ({count}x): {detail}"
        )

        if memory is not None and hasattr(memory, "state") and memory.state is not None:
            if hasattr(memory.state, "tried_and_failed"):
                if hint not in memory.state.tried_and_failed:
                    memory.state.tried_and_failed.append(hint)

        return hint

    def reset(self) -> None:
        """Reset violation counts."""
        self.violations.clear()
