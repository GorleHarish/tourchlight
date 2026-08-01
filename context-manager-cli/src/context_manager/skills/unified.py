import ast
import json
import re
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
import asyncio

from .base import BaseSkill, SkillResult, SkillRegistry, _run_async
from ..tools.core import get_core_registry, CoreTool, classify_command, REVIEW

@dataclass
class UnifiedToolResult:
    success: bool
    output:  str
    error:   Optional[str] = None
    name:    str           = ""

class UnifiedSkillRegistry(SkillRegistry):
    """
    A single registry for ALL tools and skills.
    Bridges the gap between core tools (tools/core.py) and external skills.
    
    Provides unified parsing and execution logic for the CLI.
    """

    def __init__(self) -> None:
        super().__init__()
        self._core_reg = get_core_registry()
        # Merge core tools into the searchable skills list for prompt generation
        self._legacy_parser_names = self._core_reg.names()

    # Compact tool descriptions for small context (~150 tokens total)
    _COMPACT_TOOLS = {
        "READ_FILE": "READ_FILE(path) — read file, path:10-50 for lines, path:Func for symbol",
        "WRITE_FILE": "WRITE_FILE(path, content) — create/overwrite file",
        "EDIT_FILE": "EDIT_FILE(path, old, new) — replace text in file",
        "GREP": "GREP(pattern, path) — search for pattern",
        "RUN_COMMAND": "RUN_COMMAND(cmd) — execute shell",
        "VERIFY": "VERIFY(path) — check file exists",
        "RUN_CODE": "RUN_CODE(snippet) — run code snippet",
        "FORMAT_CODE": "FORMAT_CODE(snippet) — format/beautify code",
        "GENERATE_DIFF": "GENERATE_DIFF(old, new) — create diff",
        "READ_SYMBOLS": "READ_SYMBOLS(path) — show file structure",
        "WEB_SEARCH": "WEB_SEARCH(query) — search web",
        "WEB_FETCH": "WEB_FETCH(url) — fetch URL content",
        "DOC_SEARCH": "DOC_SEARCH(query) — search docs",
        "SAVE_MEMORY": "SAVE_MEMORY(fact, cat) — save fact to memory",
        "ASK_USER": "ASK_USER(question) — ask user a question",
    }

    # Compact protocol for small context
    _COMPACT_PROTOCOL = "Format: <tool_call>{'name': 'TOOL', 'arguments': {'k': 'v'}}</tool_call>"

    def get_all_prompts(self, max_tokens: int = 0, allowed_tools: Optional[List[str]] = None) -> str:
        """
        Condensed tool documentation injected into the system prompt.
        
        Uses adaptive strategy based on context window:
        - Small (≤4k): Compact tools + minimal skills (~200 tokens)
        - Medium (4k-8k): Full tool list + top skills (~650 tokens)
        - Large (8k+): Full descriptions + all skills (~650 tokens)
        """
        if max_tokens <= 4096:
            # Ultra-compact for small context
            prompts = ["## TOOLS", self._COMPACT_PROTOCOL, ""]
            for name, desc in self._COMPACT_TOOLS.items():
                if allowed_tools is None or name in allowed_tools:
                    prompts.append(f"- {desc}")
            prompts.extend([
                "",
                "## SKILLS",
                "- /tdd: TDD | /plan: Planning | /calculate: Math | /git: Git",
                "(Use /<name> to invoke skills)",
            ])
            return "\n".join(prompts)
        
        # Medium/Large context: full tool list
        prompts = [
            "## TOOLS",
            "Format: <tool_call>{'name': 'TOOL_NAME', 'arguments': {'key': 'value'}}</tool_call>",
            ""
        ]
        for t in self._core_reg.all():
            if allowed_tools is None or t.name in allowed_tools:
                prompts.append(f"- {t.name}: {t.description}")

        skills = self.list_skills()
        if not skills:
            return "\n".join(prompts)

        if max_tokens <= 8000:
            prompts.append("\n## SKILLS")
            for s in skills[:5]:
                line = s.get_prompt().splitlines()[0] if s.get_prompt() else ""
                if line:
                    prompts.append(f"- {line}")
            if len(skills) > 5:
                prompts.append(f"(Use /<name> to invoke other skills)")
        else:
            prompts.append("\n## SKILLS")
            for s in skills:
                line = s.get_prompt().splitlines()[0] if s.get_prompt() else ""
                if line:
                    prompts.append(f"- {line}")

        return "\n".join(prompts)

    def parse_skills(self, text: str) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Robustly parses tool calls from text.
        Supports:
          1. JSON format: <tool_call> {"name": "...", "arguments": {...}} </tool_call>
          2. Legacy format: TOOL_NAME("arg")

        Deduplicates: if the model stutters and emits the same call twice, only
        the first occurrence is returned.
        """
        # Remove thinking blocks first - handle both thought and think tags
        text = re.sub(r"<(?:think|thought)>[\s\S]*?(?:</(?:think|thought)>|$)", "", text, flags=re.IGNORECASE)
        
        results: List[Tuple[str, Dict[str, Any]]] = []
        seen: set = set()

        def _coerce_payload(raw_payload: str) -> Optional[dict]:
            payload = (raw_payload or "").strip()
            if not payload:
                return None
            try:
                data = json.loads(payload)
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                pass
            try:
                data = ast.literal_eval(payload)
                return data if isinstance(data, dict) else None
            except (ValueError, SyntaxError):
                return None

        def _extract_name_and_args(data: dict) -> tuple[str, dict]:
            name = str(data.get("name", "") or data.get("tool", "")).upper()
            args = data.get("arguments", data.get("args", {}))
            if not isinstance(args, dict):
                args = {}
            return name, args

        def _parse_xml_args(raw_args: str) -> dict:
            payload = (raw_args or "").strip()
            if not payload:
                return {}

            data = _coerce_payload(payload)
            if data:
                nested_args = data.get("arguments", data.get("args"))
                if isinstance(nested_args, dict):
                    return nested_args
                return data

            params: dict[str, Any] = {}
            for child in re.finditer(r"<([a-zA-Z_][\w-]*)>\s*([\s\S]*?)\s*</\1>", payload, re.IGNORECASE):
                key = child.group(1).strip().lower()
                value = child.group(2).strip()
                if key in {"name", "tool", "command", "args", "arguments"}:
                    continue
                if value:
                    params[key] = value
            if params:
                return params

            return {"arg": payload}

        def _coerce_xml_tool_call(raw_payload: str) -> Optional[tuple[str, dict]]:
            payload = (raw_payload or "").strip()
            if not payload:
                return None

            while True:
                wrapped = re.fullmatch(r"<tool_call>\s*([\s\S]*?)\s*</tool_call>", payload, re.IGNORECASE)
                if not wrapped:
                    break
                payload = wrapped.group(1).strip()

            name_match = re.search(r"<(?:name|tool|command)>\s*([^<]+?)\s*</(?:name|tool|command)>", payload, re.IGNORECASE)
            if not name_match:
                return None

            args_match = re.search(r"<(?:args|arguments)>\s*([\s\S]*?)\s*</(?:args|arguments)>", payload, re.IGNORECASE)
            args = _parse_xml_args(args_match.group(1) if args_match else "")

            if not args:
                direct_params: dict[str, Any] = {}
                for child in re.finditer(r"<(cmd|path|pattern|arg|snippet|language|old_text|new_text|old|new)>\s*([\s\S]*?)\s*</\1>", payload, re.IGNORECASE):
                    direct_params[child.group(1).strip().lower()] = child.group(2).strip()
                args = direct_params

            return name_match.group(1).strip(), args

        def _normalize_invocation(name: str, params: dict) -> tuple[str, dict]:
            name_u = (name or "").strip().upper()
            args = dict(params or {})

            if name_u in {"LS", "DIR"}:
                cmd = str(args.get("cmd") or args.get("arg") or "ls -la").strip() or "ls -la"
                return "RUN_COMMAND", {"cmd": cmd}
            if name_u == "PWD":
                return "RUN_COMMAND", {"cmd": "pwd"}
            if name_u in {"FS_FILETREE", "FILETREE", "LIST_FILES"}:
                return "RUN_COMMAND", {"cmd": "find . -type f | grep -v __pycache__ | grep -v .git | head -60"}
            if name_u in {"FS_READ", "READ"} and args.get("path"):
                return "READ_FILE", {"path": str(args.get("path"))}
            if name_u == "CAT" and args.get("path"):
                return "READ_FILE", {"path": str(args.get("path"))}
            return name_u, args

        def _add(name: str, params: dict) -> None:
            name, params = _normalize_invocation(name, params)
            # Sort params for stable deduplication key
            key = (name.upper(), tuple(sorted(
                (k, str(v)) for k, v in params.items() if k != "content"
            )))
            if key not in seen:
                seen.add(key)
                results.append((name, params))
        
        # ── 1. Parse <tool_call> JSON tags (Primary) ─────────────────────────
        tag_matches = re.finditer(r"<tool_call>\s*(.*?)\s*</tool_call>", text, re.DOTALL | re.IGNORECASE)
        for match in tag_matches:
            raw_payload = match.group(1).strip()
            data = _coerce_payload(raw_payload)
            if data:
                name, args = _extract_name_and_args(data)
                if name:
                    _add(name, args)
            else:
                xml_call = _coerce_xml_tool_call(raw_payload)
                if xml_call:
                    xml_name, xml_args = xml_call
                    _add(xml_name, xml_args)
                elif raw_payload and "<" not in raw_payload and ">" not in raw_payload and classify_command(raw_payload) != REVIEW:
                    _add("RUN_COMMAND", {"cmd": raw_payload})

        # ── 2. Parse ```json {"name": ...} ``` fences ────────────────────────
        fence_matches = re.finditer(
            r"```(?:json)?\s*(\{[\s\S]*?\})\s*```",
            text, re.DOTALL | re.IGNORECASE
        )
        for match in fence_matches:
            data = _coerce_payload(match.group(1))
            if data:
                name, args = _extract_name_and_args(data)
                if name:
                    _add(name, args)

        # --- 1. JSON Path: {"type": "tool_call", ...} ---
        # Robust balanced-brace search for JSON objects
        i = 0
        while i < len(text):
            if text[i] == '{':
                start_json = i
                depth = 0
                in_str = None
                content_end = -1
                j = i
                while j < len(text):
                    c = text[j]
                    if in_str:
                        if c == in_str and (j == 0 or text[j-1] != '\\'):
                            in_str = None
                    else:
                        if c in ('"', "'"):
                            in_str = c
                        elif c == '{':
                            depth += 1
                        elif c == '}':
                            depth -= 1
                            if depth == 0:
                                content_end = j
                                break
                    j += 1
                
                if content_end != -1:
                    raw_json = text[start_json:content_end+1]
                    try:
                        data = json.loads(raw_json)
                        if isinstance(data, dict) and data.get("type") == "tool_call":
                            name = data.get("name", "")
                            args = data.get("args", data.get("arguments", {}))
                            if name:
                                _add(str(name), args if isinstance(args, dict) else {})
                    except:
                        pass
                    i = content_end
            i += 1

        # --- 2. Functional Path: NAME(args) ---
        # Broadly find potential tool names
        for am in re.finditer(r"\b([A-Z][A-Z0-9_]{2,})\s*\(", text):
            name = am.group(1)
            if name not in self._legacy_parser_names and name not in (
                "PATCH_FILE", "RUN_CODE", "FORMAT_CODE", "GENERATE_DIFF", "ASK_USER", "ASK_TOOL"
            ):
                continue

            # Find the balanced closing paren starting from the ( index
            start_idx = am.end()
            depth = 1
            in_quote = None # ' " or """ '''
            content_end = -1
            
            i = start_idx
            while i < len(text):
                char = text[i]
                
                # Simple quote tracking to ignore parens inside strings
                if in_quote:
                    # Check for closing quote
                    if text[i:i+len(in_quote)] == in_quote:
                        i += len(in_quote) - 1
                        in_quote = None
                else:
                    if text[i:i+3] in ('"""', "'''"):
                        in_quote = text[i:i+3]
                        i += 2
                    elif char in ('"', "'"):
                        in_quote = char
                    elif char == "(":
                        depth += 1
                    elif char == ")":
                        depth -= 1
                        if depth == 0:
                            content_end = i
                            break
                i += 1
            
            if content_end == -1:
                continue
                
            args_raw = text[start_idx:content_end]
            params = {}
            pos_idx = 0
            
            # Explicitly match: triple-double, triple-single, double, single, word, list, dict
            arg_pattern = re.compile(
                r'(?:(\w+)\s*=\s*)?'
                r'(?:"""(.*?)"""|\'\'\'(.*?)\'\'\'|"(.*?)"|\'(.*?)\'|(\w+)|(\[.*?\])|(\{.*?\}))',
                re.DOTALL
            )
            
            for am in arg_pattern.finditer(args_raw):
                g = am.groups()
                key = g[0]
                val = next((v for v in g[1:] if v is not None), "")
                
                # Convert booleans/None
                if isinstance(val, str):
                    lval = val.lower()
                    if lval == "true": val = True
                    elif lval == "false": val = False
                    elif lval == "none": val = None
                
                if key:
                    params[key] = val
                else:
                    # Positional mapping based on tool
                    if name == "WRITE_FILE":
                        if pos_idx == 0: params["path"] = val
                        elif pos_idx == 1: params["content"] = val
                        elif pos_idx == 2: params["preview"] = val
                    elif name == "PATCH_FILE":
                        if pos_idx == 0: params["path"] = val
                        elif pos_idx == 1: params["diff"] = val
                        elif pos_idx == 2: params["preview"] = val
                    elif name in ("READ_FILE", "READ_SYMBOLS"):
                        if pos_idx == 0: params["path"] = val
                    elif name == "GREP":
                        if pos_idx == 0: params["pattern"] = val
                        elif pos_idx == 1: params["path"] = val
                    elif name in ("RUN_CODE", "FORMAT_CODE"):
                        if pos_idx == 0: params["snippet"] = val
                        elif pos_idx == 1: params["language"] = val
                    elif name == "GENERATE_DIFF":
                        if pos_idx == 0: params["old"] = val
                        elif pos_idx == 1: params["new"] = val
                        elif pos_idx == 2: params["path"] = val
                    elif name == "RUN_COMMAND":
                        if pos_idx == 0: params["cmd"] = val
                    else:
                        params[f"arg{pos_idx}"] = val
                    pos_idx += 1
            
            if params:
                _add(name, params)

        return results

    def execute_skill_sync(self, name: str, params: Dict[str, Any], cwd: str = ".") -> UnifiedToolResult:
        """Synchronous wrapper for execute_skill."""
        return _run_async(self.execute_skill(name, params, cwd))

    async def execute_skill(self, name: str, params: Dict[str, Any], cwd: str = ".") -> UnifiedToolResult:
        """
        Unified execution bridge.
        Routes to core tools or external skills as appropriate.
        """
        name_u = name.upper()

        # Operations handled by the CLI directly (sentinel for dispatch).
        if name_u in ("REINDEX", "BEAM", "FILES"):
            return UnifiedToolResult(success=True, output=f"[{name_u}_SENTINEL]", name=name_u)
        
        # 1. Try Core Tools first
        core_tool = self._core_reg.get(name_u)
        if core_tool:
            # ASK_USER is a UI sentinel — never actually execute it here.
            if name_u == "ASK_USER":
                return UnifiedToolResult(success=True, output="[ASK_USER sentinel]", name=name_u)

            # Map params dict back to positional args for legacy core tool functions
            args = []
            if name_u == "WRITE_FILE":
                args = [params.get("path", ""), params.get("content", ""), params.get("preview", False)]
            elif name_u == "PATCH_FILE":
                args = [params.get("path", ""), params.get("diff", ""), params.get("preview", False)]
            elif name_u == "EDIT_FILE":
                args = [
                    params.get("path", ""),
                    params.get("old_text", params.get("old", "")),
                    params.get("new_text", params.get("new", "")),
                ]
            elif name_u == "WEB_VERIFY":
                args = [params.get("snippet", ""), params.get("language", "python")]
            elif name_u == "SAVE_MEMORY":
                # Preserve category so tool_save_memory routes to the right field
                args = [
                    params.get("fact", params.get("arg", list(params.values())[0] if params else "")),
                    params.get("category", params.get("cat", "fact")),
                ]
            elif name_u == "VERIFY":
                # VERIFY takes path + optional expected_snippet — pass both
                path_val = params.get("path", params.get("arg", list(params.values())[0] if params else ""))
                expected  = params.get("expected", params.get("expected_snippet"))
                args = [path_val] if expected is None else [path_val, expected]
            elif name_u == "RUN_COMMAND":
                args = [params.get("cmd", params.get("arg", list(params.values())[0] if params else ""))]
            elif name_u == "GREP":
                args = [params.get("pattern", params.get("arg", "")), params.get("path", ".")]
            elif name_u in ("READ_FILE", "READ_SYMBOLS"):
                args = [params.get("path", params.get("arg", list(params.values())[0] if params else ""))]
            elif name_u in ("RUN_CODE", "FORMAT_CODE"):
                args = [params.get("snippet", ""), params.get("language", "python")]
            elif name_u == "GENERATE_DIFF":
                args = [params.get("old", ""), params.get("new", ""), params.get("path", "")]
            else:
                # For single-arg tools, take the first value or "arg"
                args = [params.get("arg", list(params.values())[0] if params else "")]
            
            try:
                # Core tools are sync; run them off the event loop so timeout
                # control in the caller remains meaningful for larger writes.
                output = await asyncio.to_thread(core_tool.fn, args, cwd)
                success = not output.startswith("❌")
                return UnifiedToolResult(
                    success=success,
                    output=output,
                    error=output if not success else None,
                    name=name_u
                )
            except Exception as e:
                return UnifiedToolResult(success=False, output="", error=str(e), name=name_u)

        # 2. Try External Skills (case-insensitive lookup)
        skill = self.get(name) or self.get(name.lower()) or self.get(name.upper())
        if skill:
            res = await skill.execute(params)
            return UnifiedToolResult(
                success=res.success,
                output=res.output,
                error=res.error,
                name=skill.name
            )

        return UnifiedToolResult(success=False, output="", error=f"Unknown tool/skill: {name}", name=name)

def create_unified_registry() -> UnifiedSkillRegistry:
    """Factory to create and bootstrap the unified registry.

    Reuses create_default_registry() for skill loading so that fixes to the
    loader (error handling, path logic) only need to be made in one place.
    """
    from .base import create_default_registry

    registry = UnifiedSkillRegistry()

    # Bootstrap via the canonical loader, then migrate all skills into the
    # UnifiedSkillRegistry so we get its richer execute_skill / parse_skills.
    base = create_default_registry()
    for skill in base.list_skills():
        registry.register(skill)

    return registry
