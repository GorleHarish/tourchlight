"""
Tool schemas and validation for Torchlight.

Defines OpenAI-compatible JSON schemas for each tool,
with alias resolution and required-field checking.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.tools.definitions.fs_schemas import FS_TOOL_SCHEMAS
from core.tools.definitions.system_schemas import SYSTEM_TOOL_SCHEMAS
from core.tools.definitions.web_schemas import WEB_TOOL_SCHEMAS
from core.tools.definitions.memory_schemas import MEMORY_TOOL_SCHEMAS

# Unified registry of all tool schemas
TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    **FS_TOOL_SCHEMAS,
    **SYSTEM_TOOL_SCHEMAS,
    **WEB_TOOL_SCHEMAS,
    **MEMORY_TOOL_SCHEMAS,
}

from core.tools.schema_validator import (
    _PHASE_TOOL_VISIBILITY,
    _coerce_param,
    get_openai_tools_schema,
    get_schemas_for_phase,
    validate_tool_call,
)

__all__ = [
    "TOOL_SCHEMAS",
    "FS_TOOL_SCHEMAS",
    "SYSTEM_TOOL_SCHEMAS",
    "WEB_TOOL_SCHEMAS",
    "MEMORY_TOOL_SCHEMAS",
    "_PHASE_TOOL_VISIBILITY",
    "_coerce_param",
    "validate_tool_call",
    "get_openai_tools_schema",
    "get_schemas_for_phase",
]
