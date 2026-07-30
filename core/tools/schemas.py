"""
Tool schemas and validation for Torchlight.

Defines OpenAI-compatible JSON schemas for each tool,
with alias resolution and required-field checking.
"""

from typing import Any, Optional, Tuple, Dict


# ── Tool schemas ───────────────────────────────────────────────────────────

TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "READ_FILE": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path (supports :N-M range or :Symbol suffix)"},
        },
        "required": ["path"],
        "aliases": {
            "path": ["file", "filename", "filepath", "p"],
        },
    },
    "WRITE_FILE": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path to target file"},
            "content": {"type": "string", "description": "Full file content to write"},
        },
        "required": ["path", "content"],
        "aliases": {
            "path": ["file", "filename", "filepath", "dest", "target", "p"],
            "content": ["code", "text", "data"],
        },
    },
    "EDIT_FILE": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File to edit (supports path:N-M range)"},
            "old_text": {"type": "string", "description": "Exact text to find and replace"},
            "new_text": {"type": "string", "description": "Replacement text"},
            "diff": {"type": "string", "description": "Aider-style <<<<<<< SEARCH \\n old \\n ======= \\n new \\n >>>>>>> REPLACE block"},
            "start_line": {"type": "integer", "description": "Optional starting line number to constrain edit search scope"},
            "end_line": {"type": "integer", "description": "Optional ending line number to constrain edit search scope"},
            "symbol": {"type": "string", "description": "Optional AST symbol name (function/class/method) to target for replacement"},
            "chunks": {"type": "array", "description": "Optional list of multiple replacements: [{'old_text': '...', 'new_text': '...'}]"},
        },
        "required": ["path"],
        "aliases": {
            "path": ["file", "filename", "filepath", "dest", "target", "p", "f"],
            "old_text": ["old", "find", "search", "target", "original", "search_text", "old_code", "existing", "source", "before"],
            "new_text": ["new", "replace", "replacement", "new_code", "replacement_text", "updated", "code", "text", "after"],
            "diff": ["block", "diff_block", "search_replace"],
            "start_line": ["start", "line_start", "from_line", "start_l"],
            "end_line": ["end", "line_end", "to_line", "end_l"],
            "symbol": ["symbol_name", "function", "method", "class_name"],
            "chunks": ["replacements", "diff_chunks", "edits"],
        },
    },
    "READ_SYMBOLS": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to show symbols for"},
        },
        "required": ["path"],
        "aliases": {
            "path": ["file", "filename", "filepath", "p"],
        },
    },
    "LIST_DIR": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path to list"},
        },
        "required": ["path"],
        "aliases": {
            "path": ["dir", "directory", "folder", "p"],
        },
    },
    "GREP": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex or string search pattern"},
            "path": {"type": "string", "description": "Directory or file path to search"},
        },
        "required": ["pattern"],
        "aliases": {
            "pattern": ["query", "search", "regex"],
            "path": ["dir", "file", "p"],
        },
    },
    "RUN_COMMAND": {
        "type": "object",
        "properties": {
            "cmd": {"type": "string", "description": "Shell command line to execute"},
        },
        "required": ["cmd"],
        "aliases": {
            "cmd": ["command", "shell", "exec", "c"],
        },
    },
    "WEB_SEARCH": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
        },
        "required": ["query"],
        "aliases": {
            "query": ["q", "search", "term"],
        },
    },
    "WEB_FETCH": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
        },
        "required": ["url"],
        "aliases": {
            "url": ["u", "link", "address"],
        },
    },
    "DOC_SEARCH": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Documentation search query"},
        },
        "required": ["query"],
        "aliases": {
            "query": ["q", "search", "term"],
        },
    },
    "WEB_VERIFY": {
        "type": "object",
        "properties": {
            "snippet": {"type": "string", "description": "Code snippet to verify"},
            "language": {"type": "string", "description": "Programming language"},
        },
        "required": ["snippet"],
        "aliases": {
            "snippet": ["code", "text"],
            "language": ["lang"],
        },
    },
    "SAVE_MEMORY": {
        "type": "object",
        "properties": {
            "fact": {"type": "string", "description": "Fact to save to project memory"},
            "category": {"type": "string", "description": "Category: fact, decision, tech, fail"},
        },
        "required": ["fact"],
        "aliases": {
            "fact": ["content", "text", "value"],
            "category": ["cat", "type"],
        },
    },
    "FORMAT_CODE": {
        "type": "object",
        "properties": {
            "snippet": {"type": "string", "description": "Code snippet to format"},
            "language": {"type": "string", "description": "Programming language"},
        },
        "required": ["snippet"],
        "aliases": {
            "snippet": ["code", "text"],
            "language": ["lang"],
        },
    },
    "VERIFY": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to verify"},
            "expected_snippet": {"type": "string", "description": "Expected content to find"},
        },
        "required": ["path"],
        "aliases": {
            "path": ["file", "filename", "filepath", "p"],
            "expected_snippet": ["expected", "content", "text"],
        },
    },
    "ASK_USER": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Question to ask the user"},
        },
        "required": ["question"],
        "aliases": {
            "question": ["q", "prompt", "ask"],
        },
    },
    "GIT": {
        "type": "object",
        "properties": {
            "subcommand": {"type": "string", "description": "Git subcommand: status, diff, log, show, branch, blame, commit, add, restore, stash, remote, shortlog"},
            "message": {"type": "string", "description": "Commit message (for commit subcommand)"},
            "files": {"type": "string", "description": "File paths to operate on"},
            "flag": {"type": "string", "description": "Additional flag or ref (e.g., HEAD~3, --staged)"},
            "staged": {"type": "boolean", "description": "Operate on staged changes"},
            "count": {"type": "string", "description": "Number of log entries to show"},
        },
        "required": ["subcommand"],
        "aliases": {
            "subcommand": ["cmd", "action", "op"],
            "message": ["msg", "m"],
            "files": ["path", "file", "filepath"],
            "flag": ["f", "ref", "option"],
            "count": ["n", "limit", "num"],
        },
    },
    "SEARCH_AST": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural language or symbol query for AST graph search"},
            "action": {"type": "string", "description": "Query action: search, path, subgraph, structure, update, summary"},
            "target": {"type": "string", "description": "Target symbol for pathfinding (when action is 'path')"},
            "top_k": {"type": "integer", "description": "Number of search results (default: 5)"},
        },
        "required": [],
        "aliases": {
            "query": ["q", "name", "symbol", "search_text", "pattern", "source", "from"],
            "action": ["cmd", "type", "mode"],
            "target": ["to", "dest", "end"],
            "top_k": ["limit", "k", "count"],
        },
    },
    "INSPECT_WEB": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Target HTML or JS file relative path"},
            "wait_ms": {"type": "integer", "description": "Wait time in ms for page load / game loop (default: 1500)"},
        },
        "required": ["path"],
        "aliases": {
            "path": ["file", "filename", "filepath", "target", "url", "p"],
            "wait_ms": ["wait", "timeout", "delay"],
        },
    },
    "SAVE_MEMORY": {
        "type": "object",
        "properties": {
            "entry": {"type": "string", "description": "Memory entry text (fact, key decision, or failed strategy)"},
            "category": {"type": "string", "description": "Memory category: 'decision' (default), 'arch_decision', 'tried_failed'"},
        },
        "required": ["entry"],
        "aliases": {
            "entry": ["text", "content", "note", "fact", "item", "val"],
            "category": ["cat", "kind", "type"],
        },
    },
    "UPDATE_TASK_GRAPH": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "Action: 'add_subtask', 'skip_task', 'update_status', 'set_description'"},
            "task_id": {"type": "string", "description": "ID of the target task"},
            "description": {"type": "string", "description": "Task description for new task or update"},
            "depends_on": {"type": "array", "description": "List of task IDs this subtask depends on"},
            "target_files": {"type": "array", "description": "List of target file paths for the task"},
        },
        "required": ["action"],
        "aliases": {
            "action": ["cmd", "op", "type"],
            "task_id": ["id", "task", "name"],
            "description": ["desc", "details", "text"],
            "depends_on": ["deps", "dependencies"],
            "target_files": ["files", "targets"],
        },
    },
}



# ── Validation ─────────────────────────────────────────────────────────────

def validate_tool_call(tool_name: str, args: dict) -> Tuple[bool, str, dict]:
    """
    Validate a tool call against its schema and resolve parameter aliases.

    Returns:
        (is_valid, error_or_success_msg, normalized_args)
    """
    tool_upper = (tool_name or "").strip().upper()
    if tool_upper not in TOOL_SCHEMAS:
        allowed = list(TOOL_SCHEMAS.keys())
        return False, f"Unknown tool '{tool_name}'. Allowed tools are: {allowed}", args

    schema = TOOL_SCHEMAS[tool_upper]
    normalized = dict(args) if isinstance(args, dict) else {}

    # Map parameter aliases to canonical schema keys
    aliases = schema.get("aliases", {})
    for target_key, alias_list in aliases.items():
        if target_key not in normalized or not normalized[target_key]:
            for alias in alias_list:
                if alias in normalized and normalized[alias]:
                    normalized[target_key] = normalized[alias]
                    break

    # Check required fields
    required = schema.get("required", [])
    missing = [req for req in required if req not in normalized or normalized[req] is None]

    if missing:
        err_msg = (
            f"Schema Validation Error for '{tool_upper}': "
            f"Missing required parameter(s): {missing}. "
            f"Expected schema required keys: {required}."
        )
        return False, err_msg, normalized

    return True, "Valid", normalized


def get_openai_tools_schema() -> list[dict]:
    """Generate OpenAI-style tools list for function calling."""
    tools = []
    for tool_name, schema in TOOL_SCHEMAS.items():
        tools.append({
            "type": "function",
            "function": {
                "name": tool_name,
                "description": f"Tool call: {tool_name}",
                "parameters": {
                    "type": schema["type"],
                    "properties": schema["properties"],
                    "required": schema["required"],
                },
            },
        })
    return tools
