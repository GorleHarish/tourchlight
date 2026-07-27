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
    """Summarize conversation turns for compression."""

    def simple_summarize(self, messages: list[Message]) -> str:
        """Create a simple summary of messages."""
        parts = []
        for msg in messages[-5:]:
            role = _role_label(msg)
            content = msg.content[:200]
            parts.append(f"[{role}] {content}")
        return "\n".join(parts)

    def extract_key_info(self, text: str) -> dict:
        """Extract key information from text."""
        return {
            "file_paths": list(set(_FILE_PATH_RE.findall(text)))[:10],
            "errors": list(set(m.group(0)[:100] for m in _ERROR_RE.finditer(text)))[:5],
            "has_code": "```" in text,
            "has_error": bool(_ERROR_RE.search(text)),
        }
