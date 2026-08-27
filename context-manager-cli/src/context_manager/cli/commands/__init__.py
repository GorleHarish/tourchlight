"""CLI commands registration package."""

from __future__ import annotations

from context_manager.cli.commands.chat import register_chat_commands
from context_manager.cli.commands.utilities import register_utility_commands

__all__ = [
    "register_chat_commands",
    "register_utility_commands",
]
