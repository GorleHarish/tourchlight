"""
Unified tool registry for Torchlight.

Single entry point for all tool execution, validation, and risk classification.
Used by both CLI and TUI frontends.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from .classification import AUTO, CONFIRM, REVIEW, classify_command
from .schemas import validate_tool_call, TOOL_SCHEMAS


# ── Result type ────────────────────────────────────────────────────────────

@dataclass
class ToolResult:
    """Structured result from tool execution."""
    success: bool
    output: str
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return self.output if self.success else (self.error or self.output)


@dataclass
class ToolDef:
    """Definition of a registered tool."""
    name: str
    icon: str
    description: str
    risk_level: str
    fn: Callable[[dict, str], str]  # fn(args, project_root) -> output
    category: str = "core"  # core, web, memory, debug

    @property
    def is_dangerous(self) -> bool:
        return self.risk_level != AUTO


# ── Registry ───────────────────────────────────────────────────────────────

class ToolRegistry:
    """
    Unified tool registry with validation, risk classification, and execution.

    Usage:
        registry = ToolRegistry()
        # Tools are registered during init
        result = registry.execute("READ_FILE", {"path": "main.py"}, project_root="/app")
    """

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef) -> None:
        """Register a tool definition."""
        self._tools[tool.name.upper()] = tool

    def get(self, name: str) -> Optional[ToolDef]:
        """Get a tool definition by name."""
        return self._tools.get(name.upper())

    def names(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def all(self) -> list[ToolDef]:
        """List all registered tool definitions."""
        return list(self._tools.values())

    def by_category(self, category: str) -> list[ToolDef]:
        """List tools in a specific category."""
        return [t for t in self._tools.values() if t.category == category]

    def icons(self) -> dict[str, str]:
        """Map tool names to their icons."""
        return {t.name: t.icon for t in self._tools.values()}

    def validate(self, name: str, args: dict) -> tuple[bool, str, dict]:
        """
        Validate a tool call against its schema.

        Returns (is_valid, error_msg, normalized_args).
        Skips validation for tools not in TOOL_SCHEMAS (custom tools).
        """
        tool_upper = name.upper().strip()
        if tool_upper not in TOOL_SCHEMAS:
            # Custom tool — skip schema validation, pass args through
            return True, "OK", dict(args) if isinstance(args, dict) else {}
        return validate_tool_call(name, args)

    def risk_level_for(self, name: str, args: Optional[dict] = None) -> str:
        """
        Get the risk tier for a tool call.

        For RUN_COMMAND, dynamically classifies based on the actual command.
        """
        tool = self._tools.get(name.upper())
        if not tool:
            return CONFIRM
        if name.upper() == "RUN_COMMAND" and args:
            cmd = args.get("cmd", "")
            return classify_command(cmd)
        return tool.risk_level

    def execute(self, name: str, args: dict, project_root: str = ".") -> ToolResult:
        """
        Execute a tool by name with given arguments.

        Validates args, executes, and wraps result in ToolResult.
        """
        tool = self._tools.get(name.upper())
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: {name}",
                metadata={"tool_name": name, "known_tools": list(self._tools.keys())},
            )

        # Validate against schema
        is_valid, msg, normalized_args = self.validate(name, args)
        if not is_valid:
            return ToolResult(
                success=False,
                output="",
                error=msg,
                metadata={"tool_name": name, "validation_error": msg},
            )

        try:
            output = tool.fn(normalized_args, project_root)
            
            # Determine success based on semantic output prefixes (fatal errors only)
            success = True
            error_prefixes = (
                "Error", "Edit failed", "File not found", "Directory not found", 
                "Exit ", "Command timed out", "EDIT_FILE requires", "WRITE_FILE requires",
                "READ_FILE requires", "Access denied", "Syntax error"
            )
            if any(output.startswith(prefix) for prefix in error_prefixes):
                success = False

            return ToolResult(
                success=success,
                output=output,
                metadata={"tool_name": name, "risk": tool.risk_level},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"{name} error: {e}",
                metadata={"tool_name": name, "exception": str(e)},
            )

    def preview_dry_run(self, name: str, args: dict, project_root: str = ".") -> str:
        """
        Generate a dry-run preview string for a tool call without executing mutations.
        Useful for UI pre-flight reviews and approval dialogs.
        """
        tool_name = name.upper()
        risk = self.risk_level_for(tool_name, args)
        path = args.get("path") or args.get("file", "")

        if tool_name == "WRITE_FILE":
            content = args.get("content") or args.get("code") or ""
            line_count = content.count("\n") + 1 if content else 0
            return f"[DRY-RUN PREVIEW] WRITE_FILE '{path}' ({line_count} lines) [Risk: {risk.upper()}]"

        if tool_name == "EDIT_FILE":
            old_text = args.get("old_text", "")
            new_text = args.get("new_text", "")
            return f"[DRY-RUN PREVIEW] EDIT_FILE '{path}' (replacing {len(old_text)} chars with {len(new_text)} chars) [Risk: {risk.upper()}]"

        if tool_name == "RUN_COMMAND":
            cmd = args.get("cmd", "")
            return f"[DRY-RUN PREVIEW] RUN_COMMAND '{cmd}' [Risk: {risk.upper()}]"

        return f"[DRY-RUN PREVIEW] {tool_name} (args: {list(args.keys())}) [Risk: {risk.upper()}]"

    def execute_batch(self, tool_calls: list[dict], project_root: str = ".", max_workers: int = 4) -> list[ToolResult]:
        """
        Execute multiple tool calls in parallel when safe (AUTO risk level).
        Falls back to sequential execution for mutating/confirm calls.

        tool_calls format: [{"name": "READ_FILE", "arguments": {"path": "a.py"}}, ...]
        """
        import concurrent.futures

        if not tool_calls:
            return []

        results = [None] * len(tool_calls)
        parallel_indices = []

        for idx, call in enumerate(tool_calls):
            if not isinstance(call, dict):
                continue
            name = call.get("name", "")
            args = call.get("arguments", call.get("args", {}))
            if not isinstance(args, dict):
                args = {}
            risk = self.risk_level_for(name, args)
            if risk == AUTO:
                parallel_indices.append(idx)

        if parallel_indices:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(parallel_indices))) as executor:
                future_map = {}
                for i in parallel_indices:
                    c = tool_calls[i]
                    name = c.get("name", "") if isinstance(c, dict) else ""
                    args = c.get("arguments", c.get("args", {})) if isinstance(c, dict) else {}
                    if not isinstance(args, dict):
                        args = {}
                    future = executor.submit(self.execute, name, args, project_root)
                    future_map[future] = i

                for future in concurrent.futures.as_completed(future_map):
                    i = future_map[future]
                    try:
                        results[i] = future.result()
                    except Exception as e:
                        results[i] = ToolResult(success=False, output="", error=str(e))

        for i, call in enumerate(tool_calls):
            if results[i] is None:
                if isinstance(call, dict):
                    name = call.get("name", "")
                    args = call.get("arguments", call.get("args", {}))
                    if not isinstance(args, dict):
                        args = {}
                    results[i] = self.execute(name, args, project_root)
                else:
                    results[i] = ToolResult(success=False, output="", error="Invalid tool call format")

        return results


    def get_description_block(self, max_tokens: int = 4096, phase: Optional[str] = None) -> str:
        """
        Generate tool descriptions for injection into the system prompt.

        Scales verbosity based on context window size and filters tools by active phase.
        """
        tools = list(self._tools.values())
        if phase:
            from .schemas import _PHASE_TOOL_VISIBILITY
            phase_key = phase.lower().strip()
            if phase_key in _PHASE_TOOL_VISIBILITY:
                allowed = _PHASE_TOOL_VISIBILITY[phase_key]
                tools = [t for t in tools if t.name in allowed]

        if max_tokens <= 5000:
            # Minimal: just names and one-line descriptions
            lines = ["Available tools:"]
            for tool in tools:
                lines.append(f"  {tool.icon} {tool.name}: {tool.description[:60]}")
            return "\n".join(lines)

        # Full descriptions
        lines = ["## Available Tools\n"]
        for tool in tools:
            risk_note = ""
            if tool.risk_level == CONFIRM:
                risk_note = " [requires approval]"
            elif tool.risk_level == REVIEW:
                risk_note = " [destructive - requires explicit approval]"
            lines.append(f"### {tool.icon} {tool.name}{risk_note}")
            lines.append(f"{tool.description}\n")
        return "\n".join(lines)


# ── Singleton ──────────────────────────────────────────────────────────────

_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _registry
    if _registry is None:
        _registry = _create_default_registry()
    return _registry


get_global_registry = get_tool_registry


def _create_default_registry() -> ToolRegistry:
    """Create the default tool registry with all built-in tools."""
    from .implementations import (
        tool_read_file_impl,
        tool_write_file_impl,
        tool_edit_file_impl,
        tool_read_symbols_impl,
        tool_list_dir_impl,
        tool_grep_impl,
        tool_run_command_impl,
        tool_web_search_impl,
        tool_web_fetch_impl,
        tool_doc_search_impl,
        tool_web_verify_impl,
        tool_save_memory_impl,
        tool_update_task_graph_impl,
        tool_format_code_impl,
        tool_verify_impl,
        tool_ask_user_impl,
        tool_git_impl,
        tool_search_ast_impl,
        tool_inspect_web_impl,
        tool_play_and_verify_game_impl,
        tool_self_improve_game_impl,
        tool_set_phase_impl,
    )

    registry = ToolRegistry()


    def _reg(name, icon, desc, risk, fn, cat="core"):
        registry.register(ToolDef(name=name, icon=icon, description=desc,
                                   risk_level=risk, fn=fn, category=cat))

    _reg("READ_FILE", "📖",
         "Read a file with optional line-range or symbol syntax. "
         "Formats: path, path:10-50, path:15, path:ClassName. "
         "Shows symbol map with all function/class names.",
         AUTO, tool_read_file_impl)

    _reg("WRITE_FILE", "💾",
         "Create or overwrite a file. Args: path (required), content (required, FULL file text).",
         CONFIRM, tool_write_file_impl)

    _reg("EDIT_FILE", "✂️",
         "Surgically replace a block of text. Provide enough context for unique match. "
         "Args: path, old_text, new_text.",
         CONFIRM, tool_edit_file_impl)

    _reg("READ_SYMBOLS", "📐",
         "Show file structure (all functions/classes with line numbers) without loading content. "
         "Very cheap — use on large files before READ_FILE.",
         AUTO, tool_read_symbols_impl)

    _reg("LIST_DIR", "📂",
         "List directory contents with file sizes.",
         AUTO, tool_list_dir_impl)

    _reg("GREP", "🔎",
         "Search for a pattern in files. Returns matching lines with context. "
         "Use BEFORE READ_FILE to find exact lines.",
         AUTO, tool_grep_impl)

    _reg("RUN_COMMAND", "⚡",
         "Execute a shell command. Risk level computed dynamically based on the command.",
         CONFIRM, tool_run_command_impl)

    _reg("WEB_SEARCH", "🔍",
         "General web search. Supports Brave, SerpAPI, or DuckDuckGo fallback.",
         AUTO, tool_web_search_impl, cat="web")

    _reg("WEB_FETCH", "🌐",
         "Fetch and return readable content of a URL.",
         AUTO, tool_web_fetch_impl, cat="web")

    _reg("DOC_SEARCH", "📚",
         "Search official documentation. Auto-routes to docs.python.org, MDN, etc.",
         AUTO, tool_doc_search_impl, cat="web")

    _reg("WEB_VERIFY", "✔",
         "Verify code snippet API calls against documentation. Reports VERIFIED/NOT FOUND.",
         AUTO, tool_web_verify_impl, cat="web")

    _reg("SAVE_MEMORY", "🧠",
         "Save a fact to project memory. Categories: fact, decision, tech, fail.",
         AUTO, tool_save_memory_impl, cat="memory")

    _reg("FORMAT_CODE", "🧹",
         "Beautify a code snippet using language-specific formatter.",
         AUTO, tool_format_code_impl, cat="debug")

    _reg("VERIFY", "✅",
         "Verify a file exists and optionally contains expected content.",
         AUTO, tool_verify_impl, cat="debug")

    _reg("ASK_USER", "❓",
         "Ask the user a question to clarify requirements.",
         AUTO, tool_ask_user_impl, cat="debug")

    _reg("GIT", "🔀",
         "Execute git operations: status, diff, log, show, branch, blame, commit, add, "
         "restore, stash, remote, shortlog. Safety: read ops are AUTO, write ops need approval.",
         CONFIRM, tool_git_impl, cat="vcs")

    _reg("SEARCH_AST", "🗺️",
         "Search code symbols with code snippets. Returns function/class signatures and first 5 lines of code. "
         "Use BEFORE READ_FILE to discover what to read. "
         "Examples: SEARCH_AST(query='build'), SEARCH_AST(action='subgraph', query='ProjectGraph'), "
         "SEARCH_AST(action='path', query='TieredMemory', target='Summarizer'), "
         "SEARCH_AST(action='structure'). Actions: search|path|subgraph|structure|update|summary.",
         AUTO, tool_search_ast_impl, cat="core")

    _reg("INSPECT_WEB", "🕸️",
         "Inspect runtime outcome of HTML/JS/CSS web pages or HTML5 games (captures console errors, 404s, DOM snapshot, screenshot). "
         "Args: path (required), wait_ms (default: 1500).",
         AUTO, tool_inspect_web_impl, cat="web")

    _reg("PLAY_AND_VERIFY_GAME", "🎮",
         "Play an HTML game autonomously, simulating inputs and verifying frame animation/runtime stability. "
         "Args: path (required), duration_ms (default: 3000).",
         AUTO, tool_play_and_verify_game_impl, cat="web")

    _reg("SELF_IMPROVE_GAME", "🛠️",
         "Run autonomous closed-loop diagnosis, surgical code repair, and re-verification on an HTML game. "
         "Args: path (required), max_iterations (default: 3), duration_ms (default: 2500).",
         CONFIRM, tool_self_improve_game_impl, cat="web")

    _reg("UPDATE_TASK_GRAPH", "📋",
         "Dynamically mutate sub-tasks in .torchlight/goal_spec.json. "
         "Actions: add_subtask, skip_task, update_status. Args: action (required), task_id, description, target_files, depends_on.",
         AUTO, tool_update_task_graph_impl, cat="core")

    _reg("SET_PHASE", "🔄",
         "Switch active agent phase ('code', 'plan', 'troubleshoot', 'chat'). Args: phase (required), reason.",
         AUTO, tool_set_phase_impl, cat="core")

    return registry


