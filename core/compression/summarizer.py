"""
Conversation Summarizer for Torchlight.

Extracts key information from conversation turns for compression.
"""

import re
from typing import Optional

from ..memory.models import Message, MessageRole


def _role_label(msg: Message) -> str:
    if isinstance(msg.role, MessageRole):
        return msg.role.value.upper()
    return str(msg.role).upper()


_FILE_PATH_RE = re.compile(
    r'(?:^|[\s"\'`(])([\/~\.]?[\w\-\.]+(?:\/[\w\-\.]+)+\.\w{1,10})', re.MULTILINE,
)
_ERROR_RE = re.compile(
    r'(?:TypeError|ValueError|AttributeError|ImportError|ModuleNotFoundError|'
    r'KeyError|IndexError|RuntimeError|SyntaxError|NameError|OSError|IOError)'
    r'[:\s]+([^\n]{10,100})',
)


class ConversationSummarizer:
    """Summarize conversation turns for compression using high-density structured templates."""

    def structured_summarize(self, messages: list[Message], state=None) -> str:
        """Generate a high-density structured compaction template preserving key context in minimal tokens."""
        file_paths = set()
        errors = set()
        user_intents = []
        tool_summaries = []

        for msg in messages:
            content = msg.content if hasattr(msg, "content") else str(msg)
            role = _role_label(msg)

            key_info = self.extract_key_info(content)
            file_paths.update(key_info["file_paths"])
            errors.update(key_info["errors"])

            if role == "USER":
                clean_intent = " ".join(content.split())[:120]
                if clean_intent and clean_intent not in user_intents:
                    user_intents.append(clean_intent)
            elif role in ("TOOL_RESULT", "ASSISTANT"):
                tool_name = ""
                if hasattr(msg, "metadata") and isinstance(msg.metadata, dict):
                    tool_name = msg.metadata.get("tool_name", "")
                if not tool_name:
                    tool_name = role
                if "Error" in content or "failed" in content.lower():
                    tool_summaries.append(f"{tool_name}: Error")
                else:
                    lines = [l.strip() for l in content.splitlines() if l.strip()]
                    first_line = lines[0][:60] if lines else "Done"
                    tool_summaries.append(f"{tool_name}: {first_line}")

        parts = ["[COMPACTED TRAJECTORY SUMMARY]"]
        if user_intents:
            parts.append(f"• User Goal/Intent: {user_intents[0]}")
        if file_paths:
            paths_str = ", ".join(sorted(file_paths)[:8])
            parts.append(f"• Touched Files: {paths_str}")
        if errors:
            err_str = "; ".join(sorted(errors)[:3])
            parts.append(f"• Errors Encountered: {err_str}")
        if state and hasattr(state, "decisions") and state.decisions:
            dec_str = "; ".join(state.decisions[-3:])
            parts.append(f"• Architecture Decisions: {dec_str}")
        if state and hasattr(state, "tried_and_failed") and state.tried_and_failed:
            tf_str = "; ".join(state.tried_and_failed[-3:])
            parts.append(f"• Anti-Loop (Tried & Failed): {tf_str}")
        if tool_summaries:
            recent_tools = "; ".join(tool_summaries[-5:])
            parts.append(f"• Recent Trajectory: {recent_tools}")

        return "\n".join(parts)

    def simple_summarize(self, messages: list[Message]) -> str:
        """Create a compact structured summary of messages."""
        return self.structured_summarize(messages)

    def extract_key_info(self, text: str) -> dict:
        """Extract key information from text."""
        return {
            "file_paths": list(set(_FILE_PATH_RE.findall(text)))[:10],
            "errors": list(set(m.group(0)[:100] for m in _ERROR_RE.finditer(text)))[:5],
            "has_code": "```" in text,
            "has_error": bool(_ERROR_RE.search(text)),
        }
