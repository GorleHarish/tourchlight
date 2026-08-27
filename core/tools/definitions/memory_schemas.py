"""Memory and dynamic task graph management tool schemas."""

from typing import Any, Dict

MEMORY_TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "SAVE_MEMORY": {
        "type": "object",
        "properties": {
            "entry": {
                "type": "string",
                "description": "Memory entry text (fact, key decision, or failed strategy)",
            },
            "category": {
                "type": "string",
                "description": "Memory category: 'decision' (default), 'arch_decision', 'tried_failed'",
            },
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
            "action": {
                "type": "string",
                "description": "Action: 'add_subtask', 'skip_task', 'update_status', 'set_description'",
            },
            "task_id": {"type": "string", "description": "ID of the target task"},
            "description": {
                "type": "string",
                "description": "Task description for new task or update",
            },
            "depends_on": {
                "type": "array",
                "description": "List of task IDs this subtask depends on",
            },
            "target_files": {
                "type": "array",
                "description": "List of target file paths for the task",
            },
        },
        "required": ["action"],
        "aliases": {
            "action": ["cmd", "op", "type"],
            "task_id": ["id", "task", "name"],
            "description": ["desc", "details", "text"],
            "depends_on": ["deps", "dependencies"],
            "target_files": ["files", "targets"],
        },
    }
}
