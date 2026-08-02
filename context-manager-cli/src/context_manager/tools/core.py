"""
Core Tools — built-in, always available, called via TOOL_NAME("arg") syntax.

This module re-exports tools and classifications directly from the shared core library (core.tools).
"""

from typing import Any

from core.tools.classification import (
    AUTO,
    CONFIRM,
    REVIEW,
    classify_command,
)
from core.tools.registry import (
    ToolRegistry,
    ToolDef as CoreTool,
    get_global_registry,
    TOOL_SCHEMAS,
)
from core.tools.implementations import (
    tool_read_file_impl as tool_read_file,
    tool_write_file_impl as tool_write_file,
    tool_edit_file_impl as tool_edit_file,
    tool_read_symbols_impl as tool_read_symbols,
    tool_list_dir_impl as tool_list_dir,
    tool_grep_impl as tool_grep,
    tool_run_command_impl as tool_run_command,
    tool_web_search_impl as tool_web_search,
    tool_web_fetch_impl as tool_web_fetch,
    tool_doc_search_impl as tool_doc_search,
    tool_web_verify_impl as tool_web_verify,
    tool_save_memory_impl as tool_save_memory,
    tool_format_code_impl as tool_format_code,
    tool_verify_impl as tool_verify,
    _extract_symbols,
    _symbol_map,
    _read_budget,
    _read_budget_for_ctx,
    set_ctx_window,
)


class CoreToolRegistry(ToolRegistry):
    """Compatibility subclass of ToolRegistry providing CLI-specific execute/dangerous_tools wrappers."""

    def execute(self, name: str, args: Any = None, cwd: str = ".", project_root: str = ".") -> str:
        root = cwd or project_root
        arg_dict = {}
        if isinstance(args, dict):
            arg_dict = args
        elif isinstance(args, list):
            if len(args) == 1:
                arg_dict = {"path": args[0], "query": args[0], "command": args[0]}
            elif len(args) >= 2:
                arg_dict = {"query": args[0], "path": args[1], "command": args[0]}

        if name not in self._tools and name.upper() not in self._tools:
            return f"Unknown tool: {name}"

        res = super().execute(name, arg_dict, project_root=root)
        return str(res)

    def dangerous_tools(self) -> list:
        return [t.name for t in self._tools.values() if t.is_dangerous]


def get_core_registry() -> CoreToolRegistry:
    from core.tools.registry import get_global_registry

    reg = CoreToolRegistry()
    for tool in get_global_registry().all():
        reg.register(tool)
    return reg


__all__ = [
    "AUTO",
    "CONFIRM",
    "REVIEW",
    "classify_command",
    "CoreTool",
    "CoreToolRegistry",
    "get_core_registry",
    "ToolRegistry",
    "get_global_registry",
    "TOOL_SCHEMAS",
    "tool_read_file",
    "tool_write_file",
    "tool_edit_file",
    "tool_read_symbols",
    "tool_list_dir",
    "tool_grep",
    "tool_run_command",
    "tool_web_search",
    "tool_web_fetch",
    "tool_doc_search",
    "tool_web_verify",
    "tool_save_memory",
    "tool_format_code",
    "tool_verify",
    "_extract_symbols",
    "_symbol_map",
    "_read_budget",
    "_read_budget_for_ctx",
    "set_ctx_window",
]
