"""System, execution, and environment tool schemas."""

from typing import Any, Dict

SYSTEM_TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "RUN_COMMAND": {
        "type": "object",
        "properties": {
            "cmd": {"type": "string", "description": "Shell command line to execute"},
            "cwd": {
                "type": "string",
                "description": "Optional working directory path for execution",
            },
        },
        "required": ["cmd"],
        "aliases": {
            "cmd": ["command", "shell", "exec", "c"],
            "cwd": ["dir", "path", "directory", "working_dir"],
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
            "question": {"type": "string", "description": "Question to ask the user for review/feedback"},
            "questions": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of structured review questions to ask the user",
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of options for the user to choose from (place (Recommended) option first)",
            },
            "is_multi_select": {
                "type": "boolean",
                "description": "True for checkbox/multiple choice, False for radio/single choice",
            },
            "allow_custom_input": {
                "type": "boolean",
                "description": "Whether to allow custom text input from the user (default True)",
            },
        },
        "required": ["question"],
        "aliases": {
            "question": ["q", "prompt", "ask"],
            "questions": ["items", "review_questions", "question_list"],
            "options": ["choices", "opts", "items_list"],
            "is_multi_select": ["multi_select", "multiple", "multiselect", "is_multiple"],
            "allow_custom_input": ["custom_input", "allow_custom"],
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
    "PLAY_AND_VERIFY_GAME": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Target HTML game file relative path or HTTP URL",
            },
            "duration_ms": {
                "type": "integer",
                "description": "Duration in ms to play and verify the game (default: 3000)",
            },
        },
        "required": ["path"],
        "aliases": {
            "path": ["file", "filename", "filepath", "game_file", "target", "url", "p"],
            "duration_ms": ["duration", "wait_ms", "time"],
        },
    },
    "SELF_IMPROVE_GAME": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Target HTML game file relative path",
            },
            "max_iterations": {
                "type": "integer",
                "description": "Maximum autonomous repair iterations (default: 3)",
            },
            "duration_ms": {
                "type": "integer",
                "description": "Game playing test duration per iteration in ms (default: 2500)",
            },
        },
        "required": ["path"],
        "aliases": {
            "path": ["file", "filename", "filepath", "game_file", "target", "p"],
            "max_iterations": ["iterations", "epochs", "max_epochs", "retries"],
            "duration_ms": ["duration", "wait_ms"],
        },
    },
    "SET_PHASE": {
        "type": "object",
        "properties": {
            "phase": {
                "type": "string",
                "description": "Target phase to switch to: 'code', 'plan', 'troubleshoot', or 'chat'",
            },
            "reason": {
                "type": "string",
                "description": "Short explanation for changing phase",
            },
        },
        "required": ["phase"],
        "aliases": {
            "phase": ["mode", "target_phase", "p"],
            "reason": ["why", "explanation"],
        },
    }
}
