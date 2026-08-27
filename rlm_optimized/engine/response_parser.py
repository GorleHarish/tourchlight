"""Response parsing, tool call extraction, markdown JSON repair, and unannotated code block interception."""

from __future__ import annotations

import collections
import json
import os
import re
from typing import Optional

from core.tools.dedup import TrajectoryLock, get_alternate_trajectory_hint
from core.tools.parser import (
    clean_and_parse_json as _clean_and_parse_json,
    extract_balanced_json_object as _extract_balanced_json_object,
    parse_tool_call_payload,
    repair_unclosed_tool_call_tag,
    strip_interleaved_prose,
    tolerant_json_repair as _tolerant_json_repair,
    unwrap_double_encoded_json,
)
from core.tools.registry import get_tool_registry
from rlm_optimized.engine.models import Step
from rlm_optimized.tool_schemas import validate_and_normalize_tool_call


def _looks_like_prose_or_outline(content: str) -> bool:
    """Heuristic gate for inline code interception (step 6b of _parse_response).

    Returns True when a bare ``` block is likely a plan/outline/prose dump
    rather than actual code. Small models frequently emit their step-by-step
    plan inside a ``` block during plan/code phases; auto-WRITE_FILE'ing that
    prose verbatim produced the "gibberish file" bug (e.g. inline_code_output_N.txt).
    """
    text = (content or "").strip()
    if not text:
        return True
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return True
    joined = text

    code_tokens = re.findall(
        r"\b(?:def|class|function|const|let|var|import|from|return|print|echo|"
        r"SELECT|INSERT|UPDATE|DELETE|CREATE)\b",
        joined,
        re.IGNORECASE,
    )
    # Exclude markdown formatting chars (*, -, `, #, /) from structural code punctuation
    code_punct = len(re.findall(r"[{}();\[\]=<>+]", joined))

    # Outline markers: "### Heading", "1. ...", "## Step ...", "- [ ] ...", "* Item"
    outline_lines = re.findall(
        r"^\s*(?:#{1,6}\s+\S|\d+[\.\)]\s+\S|[-*+]\s+(?:\[\s*\]\s+)?\S)",
        joined,
        re.MULTILINE,
    )
    # Plan lead-ins at line starts (step-by-step prose).
    has_plan_leadin = bool(
        re.search(
            r"^\s*(?:first|next|then|finally|step\s*\d+|approach|overview|summary|"
            r"goal|objective|we\s+will|i\s+will|let'?s)\b(?=[\s\:\,])",
            joined,
            re.IGNORECASE | re.MULTILINE,
        )
    )
    # Sentence-like majority: wordy lines ending in sentence punctuation.
    sentence_like = sum(
        1
        for ln in lines
        if len(ln) >= 16
        and re.search(r"[.!?]\s*$", ln)
        and len(re.findall(r"[{}();\[\]=<>+]", ln)) <= 2
    )

    # 1. Strong code signals (tokens + structural punctuation) -> definitely code.
    if (code_tokens or code_punct >= 4) and not outline_lines and not has_plan_leadin:
        return False

    # 2. Outlined plan beats weak code signals ("# 1. ...", "## Step ...").
    if outline_lines and code_punct < 12 and len(code_tokens) <= 1:
        return True

    # 3. Plan lead-ins / sentence-style prose with no code tokens.
    if not code_tokens and (has_plan_leadin or sentence_like or outline_lines):
        return True

    # 4. No code tokens and almost no code punctuation -> prose.
    return bool(not code_tokens and code_punct < 4)


def _looks_like_full_file(content: str, path: str = "", project_root: str = "") -> bool:
    """Helper to check if content looks like a complete standalone file rather than a small snippet."""
    if not content:
        return False
    lines = [ln for ln in content.strip().splitlines() if ln.strip()]

    # If target file exists on disk, compare snippet size with existing file
    full_p = (
        os.path.join(project_root, path)
        if project_root and not os.path.isabs(path)
        else path
    )
    if os.path.exists(full_p) and os.path.isfile(full_p):
        try:
            with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                existing_lines = [ln for ln in f.read().splitlines() if ln.strip()]
            if (
                len(existing_lines) >= 10
                and len(lines) < 15
                and len(lines) < len(existing_lines) * 0.5
            ):
                # Snippet is significantly smaller than existing file -> partial snippet!
                return False
        except Exception:
            pass

    if len(lines) >= 15:
        return True
    ext = os.path.splitext(path)[1].lower() if path else ""
    if ext in (
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".c",
        ".cpp",
        ".rb",
        ".php",
    ):
        # Check for top-level code declarations / imports
        if re.search(
            r"^\s*(?:import|from|require|package|use|#include)\b", content, re.MULTILINE
        ):
            return True
        if re.search(
            r"^\s*(?:def|class|function|const|let|var|pub\s+fn|func)\b",
            content,
            re.MULTILINE,
        ):
            return True
    elif ext in (".html", ".json", ".yaml", ".yml", ".md", ".toml", ".xml"):
        return True
    return False


def _trim_trailing_prose(content: str, path: str = "") -> str:
    """Trim prose a model appended after the file body when </WRITE_FILE> was
    consumed as a stop token (the regex's `$` alternative swallows trailing text).

    Only applied to code targets to avoid corrupting legitimately prose-based
    files (README.md, plan docs, notes, etc.)."""
    ext = os.path.splitext(path)[1].lower() if path else ""
    code_ext = ext in (
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".mjs",
        ".cjs",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".java",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".sh",
        ".bash",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".sql",
        ".html",
        ".css",
        ".scss",
        ".vue",
        ".svelte",
    )
    if not code_ext:
        return content
    lines = content.rstrip("\n").splitlines()
    cut = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        ln = lines[i].strip()
        if not ln:
            break
        if (
            len(ln) >= 20
            and ln[-1] in ".!?"
            and len(re.findall(r"[{}();\[\]=<>+*/\\]", ln)) <= 2
            and not re.search(
                r"^\s*(?:def|class|function|const|let|var|import|return|print|echo)\b",
                ln,
            )
        ):
            cut = i
        else:
            break
    if cut < len(lines):
        trimmed = "\n".join(lines[:cut])
        if trimmed.strip():
            return trimmed
    return content


class ResponseParserMixin:
    """Provides LLM response parsing and tool-call interception for RLMEngine."""

    def _parse_response(
        self, response: str
    ) -> tuple[str, str, str, list[str], Optional[str], Optional[dict]]:
        """Parse the LLM response for action tags.
        Returns: (action, thinking, content, extra_queries, tool_name, tool_args)
        """
        # 0. Extract explicit <think>...</think> or <thought>...</thought> or unwrapped reasoning prefixes
        explicit_thinking = ""
        think_match = re.search(
            r"<(?:think|thought|thinking|reasoning)>(.*?)(?:</(?:think|thought|thinking|reasoning)>|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if think_match:
            explicit_thinking = think_match.group(1).strip()
        else:
            prefix_match = re.match(
                r"^\s*(?:thought\s+|\[(?:thought|thinking|reasoning|plan)\][:\s]*|(?:thought|thinking|reasoning|plan)(?:\s+process)?\s*[\n\r:]\s*|(?:chain\s*of\s*thought)[:\s]+)(.*)",
                response,
                re.DOTALL | re.IGNORECASE,
            )
            if prefix_match:
                explicit_thinking = prefix_match.group(1).strip()

        def _get_thinking(tag_start_pos: int) -> str:
            pre_tag_text = response[:tag_start_pos].strip()
            cleaned_pre = re.sub(
                r"<(?:think|thought|thinking|reasoning)>[\s\S]*?(?:</(?:think|thought|thinking|reasoning)>|$)",
                "",
                pre_tag_text,
                flags=re.IGNORECASE,
            ).strip()
            cleaned_pre = re.sub(
                r"^\s*(?:thought\s+|\[(?:thought|thinking|reasoning|plan)\][:\s]*|(?:thought|thinking|reasoning|plan)(?:\s+process)?\s*[\n\r:]\s*|(?:chain\s*of\s*thought)[:\s]+)",
                "",
                cleaned_pre,
                flags=re.IGNORECASE,
            ).strip()
            if (
                explicit_thinking
                and cleaned_pre
                and cleaned_pre not in explicit_thinking
            ):
                return f"{explicit_thinking}\n\n{cleaned_pre}"
            return explicit_thinking or cleaned_pre

        # 1. Check for <tool_call>...</tool_call> (standard tag for Qwen / Llama models)
        tool_call_match = re.search(
            r"<tool_call>\s*(.*?)(?:</tool_call>|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if tool_call_match and tool_call_match.group(1).strip():
            raw_payload = tool_call_match.group(1).strip()
            thinking = _get_thinking(tool_call_match.start())
            parsed_json = _clean_and_parse_json(raw_payload)

            tool_name = (
                parsed_json.get("name")
                or parsed_json.get("tool")
                or parsed_json.get("action")
            )
            tool_args = (
                parsed_json.get("arguments") or parsed_json.get("args") or parsed_json
            )

            if tool_name:
                t_name = str(tool_name).upper()
                if isinstance(tool_args, str):
                    tool_args = _clean_and_parse_json(tool_args)
                return (
                    "tool",
                    thinking,
                    f"{t_name}({json.dumps(tool_args)})",
                    [],
                    t_name,
                    tool_args,
                )
            else:
                return (
                    "tool",
                    thinking,
                    "MALFORMED_TOOL_CALL",
                    [],
                    "UNKNOWN_TOOL",
                    {"error": f"Failed to parse tool call from payload: {raw_payload}. Ensure you provide valid JSON with 'name' and 'arguments'."},
                )

        # 1b. Check for MLX / Qwen special token format: <|tool_call_start|>...<|tool_call_end|>
        mlx_tool_match = re.search(
            r"<\|tool_call_start\|>\s*(.*?)(?:<\|tool_call_end\|>|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if mlx_tool_match and mlx_tool_match.group(1).strip():
            raw_payload = mlx_tool_match.group(1).strip()
            thinking = _get_thinking(mlx_tool_match.start())
            tool_name = None
            tool_args = {}

            if raw_payload.startswith("{") and raw_payload.endswith("}"):
                parsed_json = _clean_and_parse_json(raw_payload)
                tool_name = parsed_json.get("name") or parsed_json.get("tool") or parsed_json.get("action")
                tool_args = parsed_json.get("arguments") or parsed_json.get("args") or parsed_json
            else:
                fn_match = re.search(r"\[?\s*([a-zA-Z0-9_]+)\s*(?:\((.*?)\))?\s*\]?", raw_payload, re.DOTALL)
                if fn_match:
                    candidate_name = fn_match.group(1).strip().upper()
                    arg_str = (fn_match.group(2) or "").strip()
                    if candidate_name not in (
                        "WORKING_MEMORY",
                        "WORKING_MEMORY_SCRATCHPAD",
                        "SCRATCHPAD",
                        "L0_WORKING_MEMORY_SCRATCHPAD",
                        "THINKING",
                        "PLAN",
                    ):
                        tool_name = candidate_name
                        if arg_str:
                            for kv in re.finditer(
                                r'([a-zA-Z0-9_]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s]+))',
                                arg_str,
                            ):
                                k = kv.group(1)
                                v = (
                                    kv.group(2)
                                    if kv.group(2) is not None
                                    else (kv.group(3) if kv.group(3) is not None else kv.group(4))
                                )
                                tool_args[k] = v

            if tool_name:
                t_name = str(tool_name).upper()
                return (
                    "tool",
                    thinking,
                    f"{t_name}({json.dumps(tool_args)})",
                    [],
                    t_name,
                    tool_args,
                )
            else:
                return (
                    "tool",
                    thinking,
                    "MALFORMED_TOOL_CALL",
                    [],
                    "UNKNOWN_TOOL",
                    {"error": f"Failed to parse MLX tool call: {raw_payload}. Provide valid JSON."},
                )

        # 2. Check for <TOOL name="...">JSON</TOOL> or <tool name="...">JSON</tool>
        tool_match = re.search(
            r'<TOOL\s+name=["\'](\w+)["\']>\s*(.*?)(?:</TOOL>|$)',
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if tool_match and tool_match.group(2).strip():
            tool_name = tool_match.group(1).upper()
            raw_args = tool_match.group(2).strip()
            thinking = _get_thinking(tool_match.start())
            tool_args = _clean_and_parse_json(raw_args)
            return (
                "tool",
                thinking,
                f"{tool_name}({raw_args})",
                [],
                tool_name,
                tool_args,
            )

        # 2b. Check for <action>NAME {JSON}</action> — fallback shape when grammar is off
        action_tag_match = re.search(
            r"<action>\s*(\w+)\s*(.*?)(?:</action>|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if action_tag_match and action_tag_match.group(1).strip():
            tool_name = action_tag_match.group(1).upper()
            thinking = _get_thinking(action_tag_match.start())
            # Extract the first balanced JSON object from inside the tag so we
            # never lose args to an unclosed <action> tag or grab trailing prose.
            json_obj = _extract_balanced_json_object(action_tag_match.group(0))
            if json_obj:
                tool_args = _clean_and_parse_json(json_obj)
            else:
                tool_args = {}
            return (
                "tool",
                thinking,
                f"{tool_name}({json.dumps(tool_args)})",
                [],
                tool_name,
                tool_args,
            )

        # 3. Check for direct XML tool tags (e.g. <EDIT_FILE path="..." .../>, <WRITE_FILE path="...">content</WRITE_FILE>, <READ_FILE path="..."/>, <RUN_COMMAND cmd="..."/>)
        xml_tool_pattern = re.search(
            r'<([a-zA-Z0-9_]+)\s+([^>]*?)(?:/>|>\s*([\s\S]*?)(?:</\1>|$))',
            response,
            re.IGNORECASE,
        )
        if xml_tool_pattern:
            candidate_name = xml_tool_pattern.group(1).upper()
            from core.tools.schemas import TOOL_SCHEMAS

            if candidate_name in TOOL_SCHEMAS or candidate_name in (
                "WRITE_FILE",
                "EDIT_FILE",
                "READ_FILE",
                "SEARCH_AST",
                "GREP",
                "RUN_COMMAND",
                "LIST_DIR",
                "VERIFY",
                "INSPECT_WEB",
                "PLAY_AND_VERIFY_GAME",
                "SELF_IMPROVE_GAME",
                "GIT",
                "SAVE_MEMORY",
                "UPDATE_TASK_GRAPH",
                "ASK_USER",
                "VIEW_IMAGE",
                "READ_SYMBOLS",
            ):
                attr_str = xml_tool_pattern.group(2) or ""
                body_content = xml_tool_pattern.group(3)
                thinking = _get_thinking(xml_tool_pattern.start())
                tool_args = {}

                # Parse attributes from tag
                for kv in re.finditer(
                    r'([a-zA-Z0-9_]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^>\s]+))',
                    attr_str,
                ):
                    k = kv.group(1)
                    if kv.group(2) is not None:
                        v = kv.group(2)
                    elif kv.group(3) is not None:
                        v = kv.group(3)
                    else:
                        v = kv.group(4)
                        if v.isdigit():
                            v = int(v)
                        elif v.lower() == "true":
                            v = True
                        elif v.lower() == "false":
                            v = False
                    tool_args[k] = v

                # If there is body content and content is not specified in attributes
                if body_content and body_content.strip():
                    if candidate_name == "WRITE_FILE" and "content" not in tool_args:
                        path_val = str(tool_args.get("path", ""))
                        if not re.search(r"</WRITE_FILE>", xml_tool_pattern.group(0), re.IGNORECASE):
                            body_content = _trim_trailing_prose(body_content, path_val)
                        body_lines = body_content.splitlines(keepends=True)
                        if body_lines and path_val:
                            first_ln = body_lines[0].strip().strip("`'\"#/*- ")
                            if (
                                first_ln.lower() == os.path.basename(path_val).lower()
                                or first_ln.lower().endswith("/" + os.path.basename(path_val).lower())
                            ):
                                body_content = "".join(body_lines[1:]).lstrip("\r\n")
                        tool_args["content"] = body_content
                    elif candidate_name == "EDIT_FILE" and "new_text" not in tool_args and "content" not in tool_args:
                        tool_args["new_text"] = body_content

                t_name = candidate_name
                summary_str = f"{t_name}({tool_args.get('path', tool_args.get('cmd', json.dumps(tool_args)))})"
                return (
                    "tool",
                    thinking,
                    summary_str,
                    [],
                    t_name,
                    tool_args,
                )

        # 3b. Check for JSON array output (fallback for Qwen JSON outputs)
        json_array_match = re.search(
            r'(?:```(?:json)?\s*)?(\[\s*\{\s*["\'](?:tool_name|name|action|tool)["\'].*?\}\s*\])(?:\s*```)?',
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if json_array_match:
            try:
                first_tool = _clean_and_parse_json(json_array_match.group(1))
                if first_tool and isinstance(first_tool, dict):
                    t_name = (
                        first_tool.get("tool_name")
                        or first_tool.get("name")
                        or first_tool.get("action")
                        or first_tool.get("tool")
                        or ""
                    ).upper()
                    if t_name:
                        t_args = (
                            first_tool.get("params")
                            or first_tool.get("arguments")
                            or first_tool.get("args")
                        )
                        if t_args is None:
                            t_args = dict(first_tool)
                            t_args.pop("tool_name", None)
                            t_args.pop("name", None)
                            t_args.pop("action", None)
                            t_args.pop("tool", None)

                        thinking = _get_thinking(json_array_match.start())
                        return (
                            "tool",
                            thinking,
                            f"{t_name}({json.dumps(t_args)})",
                            [],
                            t_name,
                            t_args,
                        )
            except Exception:
                pass

        # 3c. Check for single bare JSON tool call object (e.g. {"name": "EDIT_FILE", ...} or {"path": "...", "content": "..."})
        if "{" in response and any(
            k in response
            for k in (
                '"name"',
                '"tool"',
                '"action"',
                '"tool_name"',
                '"path"',
                '"new_text"',
                '"old_text"',
                '"cmd"',
                '"command"',
            )
        ):
            try:
                json_str = None
                codeblock_match = re.search(
                    r"```(?:json)?\s*([\s\S]*?)```", response, re.IGNORECASE
                )
                if not codeblock_match:
                    codeblock_match = re.search(
                        r"```(?:json)?\s*([\s\S]*)$", response, re.IGNORECASE
                    )
                if codeblock_match:
                    json_str = _extract_balanced_json_object(codeblock_match.group(1))
                if not json_str:
                    json_str = _extract_balanced_json_object(response)
                if json_str:
                    p_name, p_args, _ = parse_tool_call_payload(json_str)
                    if p_name:
                        t_name = str(p_name).upper()
                        from core.tools.schemas import TOOL_SCHEMAS

                        if t_name in TOOL_SCHEMAS or t_name in (
                            "WRITE_FILE",
                            "EDIT_FILE",
                            "READ_FILE",
                            "SEARCH_AST",
                            "GREP",
                            "RUN_COMMAND",
                            "VERIFY",
                            "INSPECT_WEB",
                            "PLAY_AND_VERIFY_GAME",
                            "SELF_IMPROVE_GAME",
                            "GIT",
                            "SAVE_MEMORY",
                            "UPDATE_TASK_GRAPH",
                            "ASK_USER",
                        ):
                            start_pos = (
                                response.find(json_str)
                                if json_str in response
                                else response.find("{")
                            )
                            thinking = _get_thinking(max(0, start_pos))
                            return (
                                "tool",
                                thinking,
                                f"{t_name}({json.dumps(p_args)})",
                                [],
                                t_name,
                                p_args,
                            )
            except Exception:
                pass

        # 3d. Check for bracket-format or CLI-style tool calls (e.g. [LIST_DIR], [READ_FILE(path="game.js")], [EDIT_FILE: {...}])
        # Note: If a full implementation plan with checkboxes is present, inline plan interception takes precedence.
        has_full_plan = (
            "# Implementation Plan" in response
            or ("## Proposed Changes" in response and "- [ ]" in response)
        )
        bracket_match = (
            None
            if has_full_plan
            else re.search(
                r'(?:\[|\$)\s*([a-zA-Z0-9_]+)\s*(?::\s*(\{[\s\S]*?\})|\(([\s\S]*?)\))?\s*\]?',
                response,
                re.IGNORECASE,
            )
        )
        if bracket_match:
            cand_name = bracket_match.group(1).upper()
            from core.tools.schemas import TOOL_SCHEMAS

            if cand_name in TOOL_SCHEMAS or cand_name in (
                "WRITE_FILE",
                "EDIT_FILE",
                "READ_FILE",
                "SEARCH_AST",
                "GREP",
                "RUN_COMMAND",
                "LIST_DIR",
                "VERIFY",
                "INSPECT_WEB",
                "PLAY_AND_VERIFY_GAME",
                "SELF_IMPROVE_GAME",
                "GIT",
                "SAVE_MEMORY",
                "UPDATE_TASK_GRAPH",
                "ASK_USER",
                "VIEW_IMAGE",
                "READ_SYMBOLS",
            ):
                thinking = _get_thinking(bracket_match.start())
                t_args = {}
                json_part = bracket_match.group(2)
                args_part = bracket_match.group(3)

                if json_part:
                    t_args = _clean_and_parse_json(json_part)
                elif args_part:
                    if args_part.strip().startswith("{") and args_part.strip().endswith("}"):
                        t_args = _clean_and_parse_json(args_part.strip())
                    else:
                        for kv in re.finditer(
                            r'([a-zA-Z0-9_]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s\)]+))',
                            args_part,
                        ):
                            k = kv.group(1)
                            v = (
                                kv.group(2)
                                if kv.group(2) is not None
                                else (kv.group(3) if kv.group(3) is not None else kv.group(4))
                            )
                            t_args[k] = v
                elif cand_name == "LIST_DIR":
                    t_args = {"path": "."}

                return (
                    "tool",
                    thinking,
                    f"{cand_name}({json.dumps(t_args)})",
                    [],
                    cand_name,
                    t_args,
                )

        # 4. Check for <CODE>...</CODE>, <REPL>...</REPL>, or <PYTHON>...</PYTHON>
        code_match = re.search(
            r"<(?:CODE|REPL|PYTHON)(?:\s+[^>]*)?>(.*?)(?:</(?:CODE|REPL|PYTHON)>|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if not code_match:
            code_match = re.search(
                r"(?<!`)<(?:CODE|REPL|PYTHON)(?:\s+[^>]*)?>(.*?)</(?:CODE|REPL|PYTHON|code|repl|python)>",
                response,
                re.DOTALL | re.IGNORECASE,
            )

        if code_match and code_match.group(1).strip():
            content = code_match.group(1).strip()
            # Clean up any surrounding markdown code fences (e.g. ```python ... ```) inside <CODE>
            content = re.sub(
                r"^\s*```(?:python|py)?\s*\n?", "", content, flags=re.IGNORECASE
            )
            content = re.sub(r"\n?\s*```\s*$", "", content).strip()

            thinking = _get_thinking(code_match.start())

            # Check if code block specifies a target file writing intent (e.g. # file: path/foo.py or # filename: foo.py)
            file_match = re.search(
                r"^(?:#|//)\s*(?:file|filename|filepath|path)\s*:\s*([^\n\r]+)",
                content,
                re.IGNORECASE,
            )
            if file_match:
                target_path = file_match.group(1).strip()
                # Remove header line from content
                cleaned_content = re.sub(
                    r"^(?:#|//)\s*(?:file|filename|filepath|path)\s*:\s*[^\n\r]+\n?",
                    "",
                    content,
                ).strip()
                return (
                    "tool",
                    thinking,
                    f"WRITE_FILE({target_path})",
                    [],
                    "WRITE_FILE",
                    {"path": target_path, "content": cleaned_content},
                )

            # Validate if content actually looks like executable code or code file declaration
            import ast

            is_valid_code = False
            try:
                ast.parse(content)
                is_valid_code = True
            except SyntaxError:
                words = content.split()
                prose_indicators = sum(
                    1
                    for w in words
                    if w.lower().strip("`'\",.")
                    in {
                        "the",
                        "is",
                        "are",
                        "was",
                        "were",
                        "will",
                        "would",
                        "should",
                        "could",
                        "have",
                        "has",
                        "had",
                        "been",
                        "being",
                        "this",
                        "that",
                        "with",
                        "from",
                        "into",
                        "since",
                        "because",
                        "however",
                        "therefore",
                        "i",
                        "we",
                        "they",
                        "he",
                        "she",
                        "it",
                        "my",
                        "your",
                        "executing",
                        "here",
                        "generating",
                        "result",
                        "file",
                        "asking",
                    }
                )
                is_prose = (
                    len(words) > 3 and (prose_indicators / max(len(words), 1)) > 0.1
                )
                if not is_prose and re.search(
                    r"\b(?:def|class|import|from|return|const|let|function|fn)\b",
                    content,
                ):
                    is_valid_code = True

            if is_valid_code:
                return ("code", thinking, content, [], None, None)
            else:
                # Content inside <CODE> tag is natural language/prose, reclassify as thinking
                thinking_text = (
                    f"{thinking}\n\n{content}".strip() if thinking else content
                )
                return ("thinking", thinking_text, "", [], None, None)

        # 5. Check for <SUB_QUERY>...</SUB_QUERY>
        sub_query_matches = re.findall(
            r"<SUB_QUERY>(.*?)(?:</SUB_QUERY>|$)", response, re.DOTALL | re.IGNORECASE
        )
        if sub_query_matches:
            first_tag_pos = response.lower().find("<sub_query>")
            thinking = (
                _get_thinking(first_tag_pos)
                if first_tag_pos != -1
                else explicit_thinking
            )
            return (
                "sub_queries",
                thinking,
                sub_query_matches[0].strip(),
                [q.strip() for q in sub_query_matches[1:]],
                None,
                None,
            )

        # 6. Check for <FINAL_ANSWER>...</FINAL_ANSWER>
        final_match = re.search(
            r"<FINAL_ANSWER>(.*?)(?:</FINAL_ANSWER>|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if final_match:
            raw_content = final_match.group(1).strip()
            pre_text = response[: final_match.start()].strip()

            is_template = bool(
                re.match(
                    r"^(?:your|the)?\s*(?:complete\s+)?answer$", raw_content.lower()
                )
            )
            is_mid_sentence = bool(
                re.search(
                    r"\b(?:use|using|with|by|in|written|into|output|tag|provide|format|wrap)\s*[`'\"]*$",
                    pre_text,
                    re.IGNORECASE,
                )
            )

            if not is_template and not is_mid_sentence and raw_content:
                current_mode = getattr(self, "execution_mode", "unified")
                current_phase = getattr(self, "_current_phase", "code")

                # If in Plan Mode (or Goal Mode), auto-intercept plan content before returning FINAL_ANSWER
                if current_mode in ("plan", "goal") or current_phase == "plan":
                    plan_candidate = raw_content if ("- [ ]" in raw_content or "Phase 1" in raw_content or "Proposed Changes" in raw_content) else response
                    if "- [ ]" in plan_candidate or re.search(r"#{1,6}\s*(?:Phase\s*1|Proposed Changes|Implementation Plan)", plan_candidate, re.IGNORECASE):
                        clean_plan = re.sub(r"</?FINAL_ANSWER>", "", plan_candidate).strip()
                        thinking = _get_thinking(final_match.start())
                        return (
                            "tool",
                            thinking,
                            "WRITE_FILE(implementation_plan.md)",
                            [("WRITE_FILE", {"path": "implementation_plan.md", "content": clean_plan})],
                            "WRITE_FILE",
                            {"path": "implementation_plan.md", "content": clean_plan},
                        )

                thinking = _get_thinking(final_match.start())
                return ("final_answer", thinking, raw_content, [], None, None)

        # 6b. Inline code interception (Auto-WRITE_FILE for bare markdown blocks with target paths)
        if not re.search(
            r"<(?:TOOL|CODE|SUB_QUERY|WRITE_FILE|action)\b", response, re.IGNORECASE
        ):
            current_mode = getattr(self, "execution_mode", "unified")
            current_phase = getattr(self, "_current_phase", "code")

            code_blocks = list(
                re.finditer(
                    r"```(?:\w+)?\n?(.*?)```", response, re.DOTALL | re.IGNORECASE
                )
            )
            intercepted_tools = []
            thinking = ""

            for block_match in code_blocks:
                content = block_match.group(1).strip()
                if not thinking:
                    thinking = _get_thinking(block_match.start())

                # 1. Try to extract file path from comment inside block
                file_match = re.search(
                    r"^(?:#|//|/\*|<!--)\s*(?:file|filename|filepath|path)\s*[:=]?\s*([^\n\r]+)",
                    content,
                    re.IGNORECASE,
                )

                if not file_match:
                    # Also match bare first-line filename comment (e.g. "// game.js", "/* src/app.js */", "# main.py")
                    first_lines = content.splitlines()
                    if first_lines:
                        first_line_cleaned = first_lines[0].strip()
                        first_line_match = re.match(
                            r"^(?:#|//|/\*|<!--)\s*`?([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]+)`?\s*(?:\*/|-->)?$",
                            first_line_cleaned,
                        )
                        if first_line_match:
                            file_match = first_line_match

                file_match_pre = None
                if not file_match:
                    # 2. Try to extract from text preceding the block
                    if current_phase not in (
                        "chat",
                        "troubleshoot",
                        "plan",
                    ) or current_mode in ("unified", "goal"):
                        pre_text = response[: block_match.start()].strip()
                        recent_pre = (
                            "\n".join(pre_text.splitlines()[-6:]) if pre_text else ""
                        )
                        file_match_pre = re.search(
                            r"(?:#{1,6}\s*`?|file|filename|filepath|path|save\s+to|write\s+to|writing\s+file|created?\s+file|creating|output\s+to|here\s+is\s+(?:the\s+)?(?:file\s+)?|update\s+file|modify\s+file|edit\s+file|in\s+file|for\s+file)\s*[:=]?\s*`?([\w\.\-/]+\.\w+)`?",
                            recent_pre,
                            re.IGNORECASE,
                        )

                intercept = False
                target_path = ""
                if file_match and current_mode != "chat":
                    # Explicit in-block annotation ALWAYS triggers unless session mode is explicitly Chat
                    target_path = (
                        file_match.group(1).replace("*/", "").replace("-->", "").strip("`'\" ")
                    )
                    # Remove only the explicit file annotation line
                    content = re.sub(
                        r"^(?:#|//|/\*|<!--)\s*(?:(?:file|filename|filepath|path)\s*[:=]?\s*)?[^\n\r]+\n?",
                        "",
                        content,
                        count=1,
                        flags=re.IGNORECASE,
                    ).strip()
                    intercept = True
                elif file_match_pre and current_mode != "chat":
                    target_path = file_match_pre.group(1).strip()
                    if target_path.lower().endswith(".md") or not _looks_like_prose_or_outline(content):
                        intercept = True
                elif current_mode != "chat" and (
                    "# Implementation Plan" in content
                    or ("## Proposed Changes" in content and "- [ ]" in content)
                    or 'WRITE_FILE("implementation_plan.md"' in response
                    or "WRITE_FILE('implementation_plan.md'" in response
                ):
                    if "# Implementation Plan" in content or "## Proposed Changes" in content:
                        target_path = "implementation_plan.md"
                        intercept = True
                elif current_mode != "chat":
                    # Fallback: check if the active pending task targets a specific file
                    try:
                        from core.tools.task_helpers import get_workspace_pending_tasks
                        pending = (
                            get_workspace_pending_tasks(self.project_root)
                            if getattr(self, "project_root", None)
                            else []
                        )
                        if pending:
                            next_t = pending[0]
                            file_m = re.search(
                                r"([a-zA-Z0-9_\-\.\/]+\.(?:html|css|js|py|ts|jsx|tsx|json|md|go|rs))",
                                next_t,
                            )
                            if file_m:
                                cand_path = file_m.group(1).strip()
                                full_cand = os.path.join(self.project_root or "", cand_path)
                                if not os.path.exists(full_cand) or not _looks_like_prose_or_outline(content):
                                    target_path = cand_path
                                    intercept = True
                    except Exception:
                        pass

                if intercept and target_path:
                    # Safeguard: check if target file exists in workspace
                    full_p = (
                        os.path.join(self.project_root, target_path)
                        if hasattr(self, "project_root") and self.project_root
                        else target_path
                    )
                    proj_r = getattr(self, "project_root", "") or ""
                    if os.path.exists(full_p) and not _looks_like_full_file(
                        content, target_path, proj_r
                    ):
                        # Skip destructive overwrite of an existing file by a small snippet or prose
                        continue

                    intercepted_tools.append(
                        ("WRITE_FILE", {"path": target_path, "content": content})
                    )

            if not intercepted_tools and current_mode != "chat":
                # Check for unblocked markdown plan with checkbox tasks
                plan_match = re.search(
                    r"(#\s+Implementation Plan[\s\S]*?)(?:```plaintext|\$\s*WRITE_FILE|\Z)",
                    response,
                    re.IGNORECASE,
                )
                if plan_match:
                    plan_content = plan_match.group(1).strip()
                    if "- [ ]" in plan_content or "## Proposed Changes" in plan_content:
                        thinking = _get_thinking(plan_match.start())
                        return (
                            "tool",
                            thinking,
                            "WRITE_FILE(implementation_plan.md)",
                            [("WRITE_FILE", {"path": "implementation_plan.md", "content": plan_content})],
                            "WRITE_FILE",
                            {"path": "implementation_plan.md", "content": plan_content},
                        )

            if intercepted_tools:
                first_name, first_args = intercepted_tools[0]
                first_path = first_args.get("path", "")
                summary = (
                    f"{first_name}({first_path})"
                    if len(intercepted_tools) == 1
                    else f"INTERCEPTED_{len(intercepted_tools)}_FILES"
                )
                return (
                    "tool",
                    thinking,
                    summary,
                    intercepted_tools,
                    first_name,
                    first_args,
                )

        # 7. Direct answer / non-tool response handling
        cleaned_body = re.sub(
            r"<(?:think|thought|thinking|reasoning)>[\s\S]*?(?:</(?:think|thought|thinking|reasoning)>|$)",
            "",
            response,
            flags=re.IGNORECASE,
        ).strip()
        has_unclosed_tool_attempt = bool(
            re.search(
                r"<(?:TOOL|CODE|SUB_QUERY|WRITE_FILE|action)\b",
                cleaned_body,
                re.IGNORECASE,
            )
        )

        reasoning_prefix_match = re.match(
            r"^\s*(?:system\s+thought[:\s]*|thought\s+|\[(?:thought|thinking|reasoning|plan)\][:\s]*|(?:thought|thinking|reasoning|plan)(?:\s+process)?\s*[\n\r:]\s*|(?:chain\s*of\s*thought)[:\s]+)",
            response.strip(),
            re.IGNORECASE,
        )

        execution_intent = bool(
            re.search(
                r"\b(?:I\s+will|let\s*me|I\s+need\s+to|going\s+to|will\s+start\s+by|create|write|inspect|play|verify)\s+.*?\b(?:LIST_DIR|READ_FILE|EDIT_FILE|WRITE_FILE|GREP|SEARCH_AST|RUN_COMMAND|INSPECT_WEB|PLAY_AND_VERIFY_GAME|SELF_IMPROVE_GAME|WEB_SEARCH|WEB_FETCH)\b",
                cleaned_body,
                re.IGNORECASE,
            )
        )

        plan_action_start = bool(
            re.match(
                r"^(?:1[\.\s]|step\s*1|first,|I\s+will\s+start|I\s+need\s+to\s+first)\s*(?:I\s+will|let\s*me|use|call|run|create|write|read|inspect|list|search|find|edit|check|verify)",
                cleaned_body,
                re.IGNORECASE,
            )
        )

        # ── Fix: Only classify as "thinking" if the response is SHORT.
        # For 3B models, conversational text like "I will use READ_FILE to..."
        # is normal output, not internal reasoning.  If the body is > 200 chars
        # and doesn't start with an explicit reasoning prefix, treat it as a
        # final answer rather than trapping it in a thinking loop.
        is_short_response = len(cleaned_body) < 200

        is_planning_cot = (
            bool(reasoning_prefix_match)
            or (execution_intent and is_short_response)
            or (plan_action_start and is_short_response)
        )

        if is_planning_cot and not has_unclosed_tool_attempt:
            combined_thinking = (
                f"{explicit_thinking}\n\n{cleaned_body}".strip()
                if explicit_thinking
                else cleaned_body
            )
            if reasoning_prefix_match:
                combined_thinking = re.sub(
                    r"^\s*(?:system\s+thought[:\s]*|thought\s+|\[(?:thought|thinking|reasoning|plan)\][:\s]*|(?:thought|thinking|reasoning|plan)(?:\s+process)?\s*[\n\r:]\s*|(?:chain\s*of\s*thought)[:\s]+)",
                    "",
                    combined_thinking,
                    flags=re.IGNORECASE,
                ).strip()
            return ("thinking", combined_thinking or cleaned_body, "", [], None, None)

        if not has_unclosed_tool_attempt and cleaned_body:
            if explicit_thinking:
                return ("final_answer", explicit_thinking, cleaned_body, [], None, None)

            final_cleaned = re.sub(
                r"</?FINAL_ANSWER>", "", cleaned_body, flags=re.IGNORECASE
            ).strip()
            if final_cleaned:
                return ("final_answer", "", final_cleaned, [], None, None)

        return ("thinking", response.strip(), "", [], None, None)
