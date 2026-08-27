"""Filesystem and AST symbol tool schemas."""

from typing import Any, Dict

FS_TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "READ_FILE": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path (supports :N-M range or :Symbol suffix, e.g. 'src/main.py:10-40')",
            },
            "start_line": {
                "type": "integer",
                "description": "Starting line number (1-based, inclusive)",
            },
            "end_line": {
                "type": "integer",
                "description": "Ending line number (1-based, inclusive)",
            },
            "symbol": {
                "type": "string",
                "description": "Function, class, or symbol name to inspect directly",
            },
        },
        "required": ["path"],
        "aliases": {
            "path": ["file", "filename", "filepath", "p"],
            "start_line": ["start", "from_line", "line_start", "line", "offset"],
            "end_line": ["end", "to_line", "line_end", "limit"],
            "symbol": ["symbol_name", "func", "function", "class_name"],
        },
    },
    "WRITE_FILE": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path to target file"},
            "content": {"type": "string", "description": "Full file content to write"},
            "task_id": {
                "type": "string",
                "description": "Optional task ID this write belongs to (e.g. '1.1')",
            },
            "description": {
                "type": "string",
                "description": "Concise sub-task description or intent of this change (e.g. 'Create HTML skeleton')",
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
        "required": ["path", "content"],
        "aliases": {
            "path": ["file", "filename", "filepath", "dest", "target", "p"],
            "content": ["code", "text", "data"],
            "task_id": ["task", "tid", "step"],
            "description": [
                "subtask",
                "sub_task",
                "intent",
                "focus",
                "summary",
                "reason",
                "message",
            ],
        },
    },
    "EDIT_FILE": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File to edit (supports path:N-M range)",
            },
            "old_text": {
                "type": "string",
                "description": "Exact text to find and replace",
            },
            "new_text": {"type": "string", "description": "Replacement text"},
            "task_id": {
                "type": "string",
                "description": "Optional task ID this edit belongs to (e.g. '1.1')",
            },
            "description": {
                "type": "string",
                "description": "Concise sub-task description or intent of this change (e.g. 'Fix canvas coordinate scaling')",
            },
            "diff": {
                "type": "string",
                "description": "Aider-style <<<<<<< SEARCH \\n old \\n ======= \\n new \\n >>>>>>> REPLACE block",
            },
            "start_line": {
                "type": "integer",
                "description": "Optional starting line number to constrain edit search scope",
            },
            "end_line": {
                "type": "integer",
                "description": "Optional ending line number to constrain edit search scope",
            },
            "symbol": {
                "type": "string",
                "description": "Optional AST symbol name (function/class/method) to target for replacement",
            },
            "chunks": {
                "type": "array",
                "description": "Optional list of multiple replacements: [{'old_text': '...', 'new_text': '...'}]",
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
            "task_id": ["task", "tid", "step"],
            "description": [
                "subtask",
                "sub_task",
                "intent",
                "focus",
                "summary",
                "reason",
                "message",
            ],
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
            "path": {
                "type": "string",
                "description": "Directory path to list (defaults to '.' if omitted)",
                "default": ".",
            },
        },
        "required": [],
        "aliases": {
            "path": [
                "dir",
                "directory",
                "folder",
                "p",
                "DirectoryPath",
                "dir_path",
            ],
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
    "SEARCH_AST": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language or symbol query for AST graph search",
            },
            "action": {
                "type": "string",
                "description": "Query action: search, path, subgraph, structure, update, summary",
            },
            "target": {
                "type": "string",
                "description": "Target symbol for pathfinding (when action is 'path')",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of search results (default: 5)",
            },
        },
        "required": [],
        "aliases": {
            "query": [
                "q",
                "name",
                "symbol",
                "search_text",
                "pattern",
                "source",
                "from",
            ],
            "action": ["cmd", "type", "mode"],
            "target": ["to", "dest", "end"],
            "top_k": ["limit", "k", "count"],
        },
    },
    "VIEW_IMAGE": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative or absolute path to the image file to inspect (.png, .jpg, .jpeg, .webp, .gif, .svg)",
            },
            "prompt": {
                "type": "string",
                "description": "Optional specific question or detail to inspect in the image",
            },
        },
        "required": ["path"],
        "aliases": {
            "path": [
                "file",
                "filename",
                "filepath",
                "image",
                "img",
                "image_path",
                "img_path",
                "target",
                "src",
                "url",
                "file_name",
                "p",
                "f",
            ],
            "prompt": ["query", "question", "ask", "instruction", "text", "description"],
        },
    }
}
