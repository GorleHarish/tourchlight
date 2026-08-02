"""
Schema definitions and validation for SLM tool calls.
Ensures Small Language Models (SLMs) strictly conform to expected tool schemas
without using unintended formats, missing fields, or invalid tool parameters.

This module re-exports from core/ when available, falling back to local implementations.
"""

# ── Import from core/ shared library ──────────────────────────────────────
try:
    from core.tools.schemas import (
        TOOL_SCHEMAS as TOOL_SCHEMAS,
        validate_tool_call as validate_and_normalize_tool_call,
        get_openai_tools_schema as get_openai_tools_schema,
    )

    _USE_CORE = True
except ImportError:
    _USE_CORE = False

from typing import Any, Optional, Tuple, Dict

# OpenAI-compatible JSON Schemas for each tool
TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "READ_FILE": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path (supports :N-M range or :Symbol suffix)",
            },
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
            "force": {
                "type": "boolean",
                "description": "Bypass syntax/compile/stub validation gates (scaffolding escape hatch; default false)",
            },
            "reject_on_stub": {
                "type": "boolean",
                "description": "Reject files containing truncation stubs (default true)",
            },
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
            "path": {"type": "string", "description": "File to edit"},
            "old_text": {
                "type": "string",
                "description": "Exact text to find and replace",
            },
            "new_text": {"type": "string", "description": "Replacement text"},
            "diff": {
                "type": "string",
                "description": "Aider-style <<<<<<< SEARCH \\n old \\n ======= \\n new \\n >>>>>>> REPLACE block",
            },
            "force": {
                "type": "boolean",
                "description": "Bypass syntax/compile/stub validation gates (scaffolding escape hatch; default false)",
            },
            "reject_on_stub": {
                "type": "boolean",
                "description": "Reject files containing truncation stubs (default true)",
            },
        },
        "required": ["path"],
        "aliases": {
            "path": ["file", "filename", "filepath", "dest", "target", "p", "f"],
            "old_text": [
                "old",
                "find",
                "search",
                "target",
                "original",
                "search_text",
                "old_code",
                "existing",
                "source",
                "before",
            ],
            "new_text": [
                "new",
                "replace",
                "replacement",
                "new_code",
                "replacement_text",
                "updated",
                "code",
                "text",
                "after",
            ],
            "diff": ["block", "diff_block", "search_replace"],
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
            "pattern": {
                "type": "string",
                "description": "Regex or string search pattern",
            },
            "path": {
                "type": "string",
                "description": "Directory or file path to search",
            },
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
            "category": {
                "type": "string",
                "description": "Category: fact, decision, tech, fail",
            },
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
            "expected_snippet": {
                "type": "string",
                "description": "Expected content to find",
            },
            "compile": {
                "type": "boolean",
                "description": "Run syntax + compile validation on the file (default false)",
            },
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
            "subcommand": {
                "type": "string",
                "description": "Git subcommand: status, diff, log, show, branch, blame, commit, add, restore, stash, remote, shortlog",
            },
            "message": {
                "type": "string",
                "description": "Commit message (for commit subcommand)",
            },
            "files": {"type": "string", "description": "File paths to operate on"},
            "flag": {
                "type": "string",
                "description": "Additional flag or ref (e.g., HEAD~3, --staged)",
            },
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
            "query": {
                "type": "string",
                "description": "Natural language or symbol query for AST graph search",
            },
            "action": {
                "type": "string",
                "description": "Query action: search (semantic), structure, signature, source, ast, subgraph",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of semantic search results (default: 3)",
            },
        },
        "required": ["query"],
        "aliases": {
            "query": ["q", "name", "symbol", "search_text", "pattern"],
            "action": ["cmd", "type", "mode"],
            "top_k": ["limit", "k", "count"],
        },
    },
}


def get_openai_tools_schema() -> list[dict]:
    """Generate OpenAI-style tools list for function calling / structured schema enforcement."""
    tools = []
    for tool_name, schema in TOOL_SCHEMAS.items():
        tools.append(
            {
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
            }
        )
    return tools


def validate_and_normalize_tool_call(
    tool_name: str, args: dict
) -> Tuple[bool, str, dict]:
    """Validate tool call against schema and normalize parameter aliases.

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
    missing = [
        req for req in required if req not in normalized or normalized[req] is None
    ]

    if missing:
        err_msg = (
            f"Schema Validation Error for '{tool_upper}': Missing required parameter(s): {missing}. "
            f"Expected schema required keys: {required}."
        )
        return False, err_msg, normalized

    return True, "Valid", normalized
