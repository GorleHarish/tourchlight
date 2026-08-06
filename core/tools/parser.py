"""
Tolerant Tool Call Parser and Fuzzy Repair Engine.

Provides robust parsing, unclosed-tag repair, prose stripping, double-encoded JSON
unwrapping, and tolerant schema validation for LLM tool invocations.
"""

import json
import re
from typing import Any, Dict, Optional, Tuple, Union


def tolerant_json_repair(raw: str) -> str:
    """
    Repair common LLM JSON corruption inside string values:
    raw (unescaped) newlines/tabs, and a trailing unterminated string.
    Existing escape sequences are preserved.
    """
    out = []
    in_str = False
    esc = False
    for ch in raw:
        if in_str:
            if esc:
                esc = False
                if ch == "\n":
                    out.append("n")  # backslash already emitted -> forms \n
                elif ch == "\r":
                    out.append("r")
                else:
                    out.append(ch)
                continue
            if ch == "\\":
                out.append(ch)
                esc = True
                continue
            if ch == '"':
                in_str = False
                out.append(ch)
                continue
            if ch == "\n" or ch == "\r":
                out.append("\\n")
                continue
            if ch == "\t":
                out.append("\\t")
                continue
            out.append(ch)
        else:
            if ch == '"':
                in_str = True
            out.append(ch)
    if in_str:
        out.append('"')
    return "".join(out)


def extract_balanced_json_object(text: str) -> Optional[str]:
    """
    Return the first balanced top-level JSON object literal in text.
    Handles nested braces and braces inside string values, and stops cleanly
    at the `}` that closes the object instead of swallowing trailing prose.
    """
    if not text:
        return None
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return text[start:]


def repair_unclosed_tool_call_tag(text: str) -> str:
    """
    Detect unclosed <tool_call> tags (e.g. truncated output) and auto-append </tool_call>.
    """
    if not text:
        return text
    if "<tool_call>" in text and "</tool_call>" not in text:
        return text.strip() + "</tool_call>"
    return text


def strip_interleaved_prose(text: str) -> str:
    """
    Isolate <tool_call>...</tool_call> block from surrounding conversational prose.
    If no tags are present, returns the original text.
    """
    if not text:
        return ""
    match = re.search(r"<tool_call>([\s\S]*?)(?:</tool_call>|$)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def unwrap_double_encoded_json(args: Any) -> Dict[str, Any]:
    """
    Detect double-encoded JSON strings in tool arguments (e.g. "arguments": "{\"path\": ...}")
    and parse them into a dict if possible.
    """
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        raw_str = args.strip()
        if (raw_str.startswith("{") and raw_str.endswith("}")) or (
            raw_str.startswith("[") and raw_str.endswith("]")
        ):
            try:
                parsed = json.loads(raw_str)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                try:
                    repaired = tolerant_json_repair(raw_str)
                    parsed = json.loads(repaired)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    pass
    return {}


def clean_and_parse_json(raw_str: str) -> dict:
    """
    4-tier parse cascade for raw JSON / tool payloads:
    1. Direct JSON parse
    2. Double-encoded unwrapping
    3. Tolerant repair (unescaped newlines/tabs, unterminated strings)
    4. Balanced JSON object extraction & regex fallback key extraction
    """
    raw = (raw_str or "").strip()
    if not raw:
        return {}

    def _extract_dict(data):
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            return data[0]
        if isinstance(data, str):
            unwrapped = unwrap_double_encoded_json(data)
            if unwrapped:
                return unwrapped
        return None

    last_parsed = None

    # 1. Direct JSON parse
    try:
        data = json.loads(raw)
        last_parsed = data
        extracted = _extract_dict(data)
        if extracted is not None:
            return extracted
    except Exception:
        pass

    # 2. Tolerant repair
    try:
        repaired = tolerant_json_repair(raw)
        data = json.loads(repaired)
        last_parsed = data
        extracted = _extract_dict(data)
        if extracted is not None:
            return extracted
    except Exception:
        pass

    # 3. Extract balanced JSON object
    balanced = extract_balanced_json_object(raw)
    if balanced and balanced != raw:
        try:
            data = json.loads(balanced)
            last_parsed = data
            extracted = _extract_dict(data)
            if extracted is not None:
                return extracted
        except Exception:
            try:
                data = json.loads(tolerant_json_repair(balanced))
                last_parsed = data
                extracted = _extract_dict(data)
                if extracted is not None:
                    return extracted
            except Exception:
                pass

    # 4. Regex fallback extraction for key properties
    result = {}
    path_match = re.search(
        r'["\']?(?:path|file|filepath|filename)["\']?\s*:\s*["\']([^"\']+)["\']', raw
    )
    if path_match:
        result["path"] = path_match.group(1)

    content_match = re.search(
        r'["\']?(?:content|code|text)["\']?\s*:\s*["\']([\s\S]*?)["\']\s*(?:,|\}|\])?$',
        raw,
    )
    if content_match:
        result["content"] = content_match.group(1)

    if not result:
        if isinstance(last_parsed, dict):
            return last_parsed
        if (
            isinstance(last_parsed, list)
            and len(last_parsed) > 0
            and isinstance(last_parsed[0], dict)
        ):
            return last_parsed[0]
        result = {"raw": raw}

    return result


def parse_tool_call_payload(
    raw_text: str,
) -> Tuple[Optional[str], Dict[str, Any], Dict[str, Any]]:
    """
    Parse a tool call from LLM output.

    Handles:
    - Unclosed <tool_call> tags
    - Interleaved prose
    - Double-encoded JSON arguments
    - Standard tool call dicts: {"name": ..., "arguments": ...} or {"tool": ..., "parameters": ...}

    Returns:
        (tool_name, arguments_dict, metadata)
    """
    repaired_text = repair_unclosed_tool_call_tag(raw_text)
    isolated_body = strip_interleaved_prose(repaired_text)
    parsed_dict = clean_and_parse_json(isolated_body)

    tool_name = (
        parsed_dict.get("name")
        or parsed_dict.get("tool")
        or parsed_dict.get("tool_name")
        or parsed_dict.get("action")
    )
    arguments = (
        parsed_dict.get("arguments")
        or parsed_dict.get("parameters")
        or parsed_dict.get("args")
        or parsed_dict.get("params")
        or {}
    )

    if isinstance(arguments, str):
        arguments = unwrap_double_encoded_json(arguments)

    if not tool_name and isinstance(parsed_dict, dict):
        # Check if single top-level key is a known tool or action
        keys = list(parsed_dict.keys())
        if len(keys) == 1 and isinstance(parsed_dict[keys[0]], dict):
            tool_name = keys[0]
            arguments = parsed_dict[keys[0]]

    metadata = {
        "raw_text": raw_text,
        "is_repaired": repaired_text != raw_text,
        "is_isolated": isolated_body != raw_text,
    }

    return tool_name, arguments if isinstance(arguments, dict) else {}, metadata
