"""Web search, web fetching, and browser inspection tool schemas."""

from typing import Any, Dict

WEB_TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
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
    "INSPECT_WEB": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Target HTML/JS file relative path or HTTP URL",
            },
            "wait_ms": {
                "type": "integer",
                "description": "Wait time in ms for page load / game loop (default: 1500)",
            },
            "interact": {
                "type": "array",
                "description": "List of action steps: [{'type': 'click'|'fill'|'key_press'|'hover'|'wait_for_selector', 'selector': '...', 'key': '...', 'text': '...'}]",
            },
        },
        "required": ["path"],
        "aliases": {
            "path": ["file", "filename", "filepath", "target", "url", "p"],
            "wait_ms": ["wait", "timeout", "delay"],
            "interact": ["actions", "steps", "sequence"],
        },
    }
}
