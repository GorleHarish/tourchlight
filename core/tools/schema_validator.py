"""Tool call parameter coercion, schema validation, and phase filtering."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.tools.definitions.fs_schemas import FS_TOOL_SCHEMAS
from core.tools.definitions.system_schemas import SYSTEM_TOOL_SCHEMAS
from core.tools.definitions.web_schemas import WEB_TOOL_SCHEMAS
from core.tools.definitions.memory_schemas import MEMORY_TOOL_SCHEMAS

TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    **FS_TOOL_SCHEMAS,
    **SYSTEM_TOOL_SCHEMAS,
    **WEB_TOOL_SCHEMAS,
    **MEMORY_TOOL_SCHEMAS,
}

def _coerce_param(value, expected_type: str):
    """Attempt safe type coercion for common LLM parameter formats."""
    if value is None:
        return None
    if expected_type == "string" and isinstance(value, str):
        return value
    if expected_type == "string" and isinstance(value, (dict, list)):
        import json

        try:
            return json.dumps(value)
        except Exception:
            return str(value)
    if expected_type in ("integer", "number", "boolean") and isinstance(
        value, (dict, list)
    ):
        return None
    if expected_type in ("array", "object") and not isinstance(
        value, (list, dict, str)
    ):
        if expected_type != "string":
            return None
    if expected_type == "integer" and isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            pass
    if expected_type == "number" and isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            pass
    if expected_type == "boolean" and isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    if expected_type == "string" and not isinstance(value, str):
        return str(value)
    if expected_type == "array":
        if isinstance(value, (list, tuple)):
            return list(value)
        if isinstance(value, str):
            import json

            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [value]
        return [value]
    if expected_type == "object" and isinstance(value, str):
        import json

        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return value


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
    if isinstance(args, str):
        from core.tools.parser import unwrap_double_encoded_json

        raw_str = args.strip()
        if raw_str and not raw_str.startswith(("{", "[")):
            # Direct string argument passed (e.g. "snake_game.png" or "src/main.py")
            if tool_upper in ("VIEW_IMAGE", "READ_FILE", "READ_SYMBOLS", "LIST_DIR"):
                normalized = {"path": raw_str}
            elif tool_upper in ("SEARCH_AST", "DOC_SEARCH", "WEB_SEARCH"):
                normalized = {"query": raw_str}
            elif tool_upper == "GREP":
                normalized = {"pattern": raw_str}
            else:
                normalized = {"path": raw_str}
        else:
            normalized = unwrap_double_encoded_json(args)
    elif isinstance(args, dict):
        normalized = dict(args)
    else:
        normalized = {}

    # Map parameter aliases to canonical schema keys
    aliases = schema.get("aliases", {})
    for target_key, alias_list in aliases.items():
        if target_key not in normalized or normalized[target_key] is None or (isinstance(normalized[target_key], str) and not normalized[target_key].strip()):
            for alias in alias_list:
                if alias in normalized and normalized[alias] is not None and (not isinstance(normalized[alias], str) or normalized[alias].strip()):
                    normalized[target_key] = normalized[alias]
                    break

    # Auto-heal VIEW_IMAGE missing path from other parameter values
    if tool_upper == "VIEW_IMAGE" and (not normalized.get("path") or not str(normalized.get("path")).strip()):
        img_exts = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg")
        for k, v in list(normalized.items()):
            if isinstance(v, str) and any(v.lower().endswith(ext) for ext in img_exts):
                normalized["path"] = v.strip()
                break

    # Auto-heal EDIT_FILE SLM parameter mismatches (content -> old_text or content -> new_text)
    if tool_upper == "EDIT_FILE":
        if "content" in normalized and normalized["content"] is not None:
            if "new_text" in normalized and normalized["new_text"] and not normalized.get("old_text"):
                normalized["old_text"] = normalized.pop("content")
            elif "old_text" in normalized and normalized["old_text"] and not normalized.get("new_text"):
                normalized["new_text"] = normalized.pop("content")

    # Auto-heal ASK_USER when questions array is passed instead of single question
    if tool_upper == "ASK_USER":
        if ("questions" in normalized and normalized["questions"]) and not normalized.get("question"):
            normalized["question"] = "Plan review / agent questions"

    # Coerce parameter types and inject defaults
    properties = schema.get("properties", {})
    for key, prop_def in properties.items():
        if key not in normalized or normalized[key] is None:
            if "default" in prop_def:
                normalized[key] = prop_def["default"]
        if key in normalized and normalized[key] is not None:
            expected = prop_def.get("type", "string")
            normalized[key] = _coerce_param(normalized[key], expected)

    # Check required fields
    required = schema.get("required", [])
    missing = [
        req for req in required if req not in normalized or normalized[req] is None or (isinstance(normalized[req], str) and not normalized[req].strip() and req == "path")
    ]

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


_PHASE_TOOL_VISIBILITY = {
    "plan": {
        "READ_FILE",
        "WRITE_FILE",
        "EDIT_FILE",
        "READ_SYMBOLS",
        "GREP",
        "SEARCH_AST",
        "LIST_DIR",
        "RUN_COMMAND",
        "VERIFY",
        "GIT",
        "INSPECT_WEB",
        "VIEW_IMAGE",
        "PLAY_AND_VERIFY_GAME",
        "SELF_IMPROVE_GAME",
        "FORMAT_CODE",
        "SAVE_MEMORY",
        "UPDATE_TASK_GRAPH",
        "SET_PHASE",
        "ASK_USER",
        "WEB_SEARCH",
        "WEB_FETCH",
        "DOC_SEARCH",
        "WEB_VERIFY",
    },
    "chat": {
        "READ_FILE",
        "READ_SYMBOLS",
        "GREP",
        "SEARCH_AST",
        "LIST_DIR",
        "VIEW_IMAGE",
        "ASK_USER",
        "SAVE_MEMORY",
        "SET_PHASE",
        "WEB_SEARCH",
        "WEB_FETCH",
        "DOC_SEARCH",
        "WEB_VERIFY",
    },
    "code": {
        "READ_FILE",
        "WRITE_FILE",
        "EDIT_FILE",
        "READ_SYMBOLS",
        "GREP",
        "SEARCH_AST",
        "LIST_DIR",
        "RUN_COMMAND",
        "VERIFY",
        "GIT",
        "INSPECT_WEB",
        "VIEW_IMAGE",
        "PLAY_AND_VERIFY_GAME",
        "SELF_IMPROVE_GAME",
        "FORMAT_CODE",
        "SAVE_MEMORY",
        "UPDATE_TASK_GRAPH",
        "SET_PHASE",
        "ASK_USER",
    },
    "goal": {
        "READ_FILE",
        "WRITE_FILE",
        "EDIT_FILE",
        "READ_SYMBOLS",
        "GREP",
        "SEARCH_AST",
        "LIST_DIR",
        "RUN_COMMAND",
        "VERIFY",
        "GIT",
        "INSPECT_WEB",
        "VIEW_IMAGE",
        "PLAY_AND_VERIFY_GAME",
        "SELF_IMPROVE_GAME",
        "FORMAT_CODE",
        "SAVE_MEMORY",
        "UPDATE_TASK_GRAPH",
        "SET_PHASE",
        "ASK_USER",
    },
    "troubleshoot": {
        "READ_FILE",
        "WRITE_FILE",
        "EDIT_FILE",
        "READ_SYMBOLS",
        "GREP",
        "SEARCH_AST",
        "LIST_DIR",
        "RUN_COMMAND",
        "INSPECT_WEB",
        "VIEW_IMAGE",
        "PLAY_AND_VERIFY_GAME",
        "SELF_IMPROVE_GAME",
        "GIT",
        "VERIFY",
        "SAVE_MEMORY",
        "UPDATE_TASK_GRAPH",
        "SET_PHASE",
        "ASK_USER",
    },
}


def get_schemas_for_phase(phase: str = "code") -> dict:
    """Filter TOOL_SCHEMAS based on the active agent phase to save context tokens."""
    phase_key = (phase or "code").lower().strip()
    if phase_key in _PHASE_TOOL_VISIBILITY:
        allowed = _PHASE_TOOL_VISIBILITY[phase_key]
        return {
            name: schema for name, schema in TOOL_SCHEMAS.items() if name in allowed
        }
    return TOOL_SCHEMAS
