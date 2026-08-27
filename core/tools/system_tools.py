"""
System command execution, git operations, memory persistence, task graphs, and AST querying tools.

Facade re-exporting operations from core.tools.system.* submodules.
"""

from __future__ import annotations

from core.tools.system.git_ops import (
    _GIT_DESTRUCTIVE_SUBCOMMANDS,
    _GIT_SAFE_SUBCOMMANDS,
    _GIT_WRITE_SUBCOMMANDS,
    _git_run,
    tool_git_impl,
)
from core.tools.system.memory_ops import (
    tool_save_memory_impl,
    tool_search_ast_impl,
    tool_update_task_graph_impl,
)
from core.tools.system.shell_runner import (
    _LONG_CMDS,
    _SAFE_COMMANDS_SET,
    tool_run_command_impl,
)
from core.tools.system.verification_ops import (
    play_and_verify_game,
    self_improve_game,
    tool_ask_user_impl,
    tool_format_code_impl,
    tool_play_and_verify_game_impl,
    tool_self_improve_game_impl,
    tool_set_phase_impl,
    tool_verify_impl,
)

__all__ = [
    "_SAFE_COMMANDS_SET",
    "_LONG_CMDS",
    "tool_run_command_impl",
    "_GIT_SAFE_SUBCOMMANDS",
    "_GIT_WRITE_SUBCOMMANDS",
    "_GIT_DESTRUCTIVE_SUBCOMMANDS",
    "_git_run",
    "tool_git_impl",
    "tool_format_code_impl",
    "tool_verify_impl",
    "tool_ask_user_impl",
    "tool_set_phase_impl",
    "tool_save_memory_impl",
    "tool_update_task_graph_impl",
    "tool_search_ast_impl",
    "tool_play_and_verify_game_impl",
    "tool_self_improve_game_impl",
    "play_and_verify_game",
    "self_improve_game",
]
