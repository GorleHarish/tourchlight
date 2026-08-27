"""Verification gate helpers, test failure warning construction, and mode guardrails."""

from __future__ import annotations


class VerificationGateMixin:
    """Provides verification gate checks and failure diagnostics for RLMEngine."""

    def _build_unresolved_failures_warning(self) -> str:
        """Build an explicit warning attached to an accepted final answer when the
        verification gate was bypassed but test state is still failing/unverified.
        Returns an empty string when there is nothing unresolved to surface."""
        parts = []
        try:
            if getattr(self.feedback_loop, "has_failing_tests", False):
                detail = ""
                try:
                    err = self.feedback_loop.get_test_failure_error()
                    if err is not None and err.surgical_traceback:
                        detail = f"\n{err.surgical_traceback[:400]}"
                except Exception:
                    pass
                parts.append(
                    "[UNRESOLVED TEST FAILURES] This final answer was accepted with "
                    f"post-edit tests still failing or unverified.{detail}"
                )
        except Exception:
            pass
        try:
            if getattr(self.feedback_loop, "_files_modified_since_test", None):
                parts.append(
                    "[UNVERIFIED CHANGES] Recent edits have not been verified by passing tests."
                )
        except Exception:
            pass
        if not parts:
            return ""
        return "\n\n⚠️ " + "\n⚠️ ".join(parts)
