"""L0 Working Memory Scratchpad, file tracking, and session state pruning mixin."""

from __future__ import annotations

import difflib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Callable

from .models import (
    Message,
    MessageRole,
    SessionState,
    ContextSnapshot,
    MemoryNeedle,
    MemoryObject,
    WorkingSetSnapshot,
)
from .budget import ContextBudget


_SCRATCHPAD_MAX_CHARS = 1600
_SCRATCHPAD_ENTRY_LIMIT = 120
_SCRATCHPAD_HEADER = "[L0 WORKING MEMORY SCRATCHPAD]"


def _is_valid_decision(entry) -> bool:
    """Filter out empty, generic, or noisy session summary strings."""
    if not entry:
        return False
    val = str(entry).strip()
    if len(val) < 5:
        return False
    lower = val.lower()
    if lower.startswith("session on ") or "no summary to provide" in lower:
        return False
    if lower.startswith("- **") or lower.startswith("--") or lower == "- **":
        return False
    return True


def _scratchpad_clean(entry, limit: int = _SCRATCHPAD_ENTRY_LIMIT) -> str:
    """Flatten whitespace/newlines and truncate a scratchpad entry to a bounded length."""
    val = str(entry).strip()
    val = re.sub(r"^(?:[-*]\s*)+", "", val).strip()
    flat = " ".join(val.split())
    if len(flat) > limit:
        return flat[: limit - 3].rstrip() + "..."
    return flat


_NON_FILE_EXTENSIONS = {
    "name",
    "role",
    "state",
    "get",
    "set",
    "items",
    "keys",
    "values",
    "count",
    "data",
    "id",
    "type",
    "val",
    "arg",
    "args",
    "kwarg",
    "kwargs",
    "attr",
    "func",
    "self",
    "this",
    "parent",
    "child",
    "len",
    "split",
    "join",
    "strip",
    "lower",
    "upper",
    "append",
    "extend",
    "pop",
    "update",
    "clear",
    "group",
    "search",
    "match",
    "findall",
    "finditer",
    "sub",
    "replace",
    "start",
    "end",
    "stdout",
    "stderr",
    "stdin",
    "path",
    "result",
    "error",
    "status",
    "code",
    "message",
    "content",
    "text",
    "length",
    "format",
    "read",
    "write",
    "close",
    "open",
    "flush",
    "is_dir",
    "is_file",
    "exists",
    "copy",
    "move",
    "remove",
    "delete",
    "add",
    "sub",
    "mul",
    "div",
    "mod",
    "eq",
    "ne",
    "lt",
    "gt",
    "le",
    "ge",
    "target",
    "source",
    "output",
    "input",
    "params",
    "options",
    "config",
    "spec",
    "value",
    "key",
    "node",
    "element",
    "component",
    "class",
    "module",
    "object",
    "enabled",
    "active",
    "default",
    "factory",
    "args",
    "kwargs",
    "parent",
}

_VALID_FILE_EXTENSIONS = {
    "py",
    "js",
    "ts",
    "jsx",
    "tsx",
    "json",
    "md",
    "txt",
    "html",
    "css",
    "tcss",
    "rs",
    "go",
    "sh",
    "c",
    "cpp",
    "h",
    "hpp",
    "yml",
    "yaml",
    "toml",
    "xml",
    "ini",
    "cfg",
    "sql",
    "java",
    "rb",
    "php",
    "kt",
    "swift",
    "bat",
    "ps1",
    "log",
    "csv",
    "tsv",
    "diff",
    "patch",
    "lock",
    "rst",
    "env",
}

_VALID_EXACT_FILENAMES = {
    "makefile",
    "dockerfile",
    ".gitignore",
    ".env",
    "license",
    "docker-compose.yml",
}


def is_valid_file_path(path: str) -> bool:
    """Validate if a string is a genuine file path rather than code attribute access (e.g. context.name)."""
    if not path or not isinstance(path, str):
        return False
    path = path.strip().strip("'\"`()[],:;")
    if not path or len(path) < 3:
        return False
    if path.startswith(("http://", "https://", "ftp://")):
        return False
    if " " in path or "\n" in path or "\t" in path:
        return False

    base = path.split("/")[-1].split("\\")[-1]
    if not base:
        return False

    if base.lower() in _VALID_EXACT_FILENAMES:
        return True

    if "." not in base:
        return False

    parts = base.rsplit(".", 1)
    prefix = parts[0].lower()
    ext = parts[1].lower()

    if ext in _NON_FILE_EXTENSIONS:
        return False

    if prefix in {
        "self",
        "this",
        "msg",
        "context",
        "obj",
        "object",
        "item",
        "data",
        "res",
        "req",
        "response",
        "request",
        "node",
        "element",
        "e",
    }:
        return False

    return ext in _VALID_FILE_EXTENSIONS


def calculate_in_memory_diff(old_content: str, new_content: str) -> tuple[int, int]:
    """Calculate exact lines added and deleted between two string buffers in RAM."""
    if old_content == new_content:
        return 0, 0

    old_lines = (old_content or "").splitlines()
    new_lines = (new_content or "").splitlines()

    added = 0
    deleted = 0

    for line in difflib.unified_diff(old_lines, new_lines, lineterm=""):
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted += 1

    return added, deleted


def extract_modified_symbols(old_content: str, new_content: str) -> list[str]:
    """Extract function/class AST symbol names modified or added between old and new text."""
    def _find_symbols(text: str) -> dict[str, str]:
        if not text:
            return {}
        symbols = {}
        # Python def/class declarations
        for m in re.finditer(r"^(?:async\s+)?(?:def|class)\s+([a-zA-Z_]\w*)", text, re.MULTILINE):
            name = m.group(1)
            start = m.start()
            symbols[name] = text[start:start + 500]
        # JS/TS function/class/const function declarations
        for m in re.finditer(r"^(?:export\s+)?(?:function|class|const|let|var)\s+([a-zA-Z_]\w*)", text, re.MULTILINE):
            name = m.group(1)
            start = m.start()
            if name not in symbols:
                symbols[name] = text[start:start + 500]
        return symbols

    old_syms = _find_symbols(old_content or "")
    new_syms = _find_symbols(new_content or "")

    modified = []
    for name, snippet in new_syms.items():
        if name not in old_syms or old_syms[name] != snippet:
            modified.append(name)
    return modified[:5]


class L0ScratchpadMixin:
    """Mixin providing dynamic L0 working memory formatting, file tracking, and session state pruning."""

    def format_l0_scratchpad(
        self,
        project_root: Optional[str] = None,
        budget: Optional[ContextBudget] = None,
    ) -> str:
        """Format current SessionState into a dynamic L0 working memory scratchpad.

        Enforces a maximum L0 budget cap (up to 1800 tokens / ~15% context window)
        and priority-weighted injection order. Each section surfaces up to
        `budget.scratchpad_section_cap` entries (3 tight ... 8 rich) so the
        scratchpad expands to use idle headroom and shrinks under pressure:
        1. Active errors_seen (most recent)
        2. Failing tests (names only, not full tracebacks)
        3. Active goal / current task
        4. Architecture decisions (most recent)
        5. Files modified in last 3 turns
        6. Tech stack (only if non-empty)
        7. Tried_and_failed (only if relevant to current file/task)
        8. Facts (skip entirely if budget exhausted)
        
        Enhanced with:
        - Content-aware entry selection (not just priority-ordered)
        - Deduplication within scratchpad
        - Dynamic sizing based on model profile
        """
        if budget is None:
            budget = self.get_effective_budget()
        entry_limit = budget.scratchpad_entry_limit
        section_cap = budget.scratchpad_section_cap
        max_chars = min(1800 * budget.chars_per_token, budget.l0_chars)
        sections = []

        # Track added content to avoid duplication
        added_content = set()

        def add_section(priority: float, line: str) -> bool:
            """Add a section if not duplicated and within budget."""
            content_key = line[:100]  # Use first 100 chars as dedup key
            if content_key in added_content:
                return False
            added_content.add(content_key)
            sections.append((priority, line))
            return True

        # Priority 1: Active errors_seen (most recent, up to section cap)
        if self.state.errors_seen:
            unique_errors = list(dict.fromkeys(self.state.errors_seen))[-section_cap:]
            shown = "; ".join(_scratchpad_clean(e, entry_limit) for e in unique_errors)
            add_section(1, f"- Active Errors: {shown}")

        # Priority 2: Failing tests (names only, not full tracebacks)
        if self.state.failing_tests:
            clean_test_names = []
            for t in self.state.failing_tests:
                t_str = str(t).split("\n")[0]
                t_name = t_str.split("::")[-1].strip()
                if t_name and t_name not in clean_test_names:
                    clean_test_names.append(t_name)
            if clean_test_names:
                shown = ", ".join(
                    _scratchpad_clean(tn, entry_limit)
                    for tn in clean_test_names[:section_cap]
                )
                add_section(2, f"- Failing Tests: {shown}")

        # Priority 2.5: Active image attachments & visual assets
        if getattr(self.state, "active_images", None):
            from core.utils.image_utils import get_image_metadata

            img_items = []
            for img_p in self.state.active_images[-section_cap:]:
                meta = get_image_metadata(img_p, project_root=project_root)
                w, h = meta.get("width", 0), meta.get("height", 0)
                dim_str = (
                    f" ({w}x{h} {meta.get('format', 'IMG')})"
                    if w > 0 and h > 0
                    else ""
                )
                img_items.append(f"{img_p}{dim_str}")
            if img_items:
                add_section(2.5, f"- Active Images: {', '.join(img_items)}")

        # Priority 3: Active task, status, next task, & active file (suppressed in Chat Mode)
        mode_val = getattr(self.state, "execution_mode", None)
        mode_str = mode_val.value if hasattr(mode_val, "value") else str(mode_val or "").lower()
        is_chat_mode = mode_str == "chat" or mode_str.endswith(".chat")

        if not is_chat_mode:
            if project_root:
                from core.tools.task_helpers import get_compact_task_matrix

                matrix_lines = get_compact_task_matrix(project_root, budget=budget)
                if matrix_lines:
                    for idx, line in enumerate(matrix_lines):
                        add_section(3.0 + idx * 0.1, line)
                elif self.state.current_task:
                    add_section(
                        3.0,
                        f"- Active Goal: {_scratchpad_clean(self.state.current_task, entry_limit)}",
                    )
            elif self.state.current_task:
                add_section(
                    3.0,
                    f"- Active Goal: {_scratchpad_clean(self.state.current_task, entry_limit)}",
                )

        if self.state.active_file:
            add_section(
                3.1,
                f"- Active File: {_scratchpad_clean(self.state.active_file, entry_limit)}",
            )

        # Priority 4: Architecture decisions (most recent, up to section cap)
        decs_source = self.state.arch_decisions or self.state.decisions
        if decs_source:
            decs_strs = [str(d) for d in decs_source]
            shown = "; ".join(
                _scratchpad_clean(d, entry_limit) for d in decs_strs[-section_cap:]
            )
            add_section(4, f"- Key Decisions: {shown}")

        # Priority 5: Files modified in last 3 turns
        if self.state.files_modified:
            recent_mod = self.state.files_modified[-3:]
            mod_items = []
            for f in recent_mod:
                clean_f = _scratchpad_clean(f, entry_limit)
                stats = self.state.files_modified_stats.get(f)
                if stats and len(stats) == 2:
                    clean_f += f" (+{stats[0]}, -{stats[1]})"
                syms = self.state.files_modified_symbols.get(f)
                if syms:
                    clean_f += f" [{', '.join(syms[:3])}]"
                mod_items.append(clean_f)
            shown = ", ".join(mod_items)
            add_section(5, f"- Modified Files: {shown}")

        # Priority 6: Tech stack (only if non-empty)
        if self.state.tech_stack:
            shown = ", ".join(
                _scratchpad_clean(t, entry_limit) for t in self.state.tech_stack[:4]
            )
            add_section(6, f"- Tech Stack: {shown}")

        # Priority 7: Tried_and_failed (up to section cap, only if relevant to current file/task)
        if self.state.tried_and_failed:
            tf_candidates = self.state.tried_and_failed
            if self.state.active_file:
                active_base = (
                    self.state.active_file.split("/")[-1].split(".")[0].lower()
                )
                rel_tf = [
                    t
                    for t in tf_candidates
                    if active_base and active_base in str(t).lower()
                ]
                if rel_tf:
                    tf_candidates = rel_tf
            shown = "; ".join(
                _scratchpad_clean(t, entry_limit)
                for t in list(dict.fromkeys(tf_candidates))[-section_cap:]
            )
            add_section(7, f"- Tried & Failed: {shown}")

        # Priority 8: Facts (skip entirely if budget exhausted)
        if self._project_memory and (self.state.current_task or self.state.intent):
            try:
                q_text = self.state.current_task or self.state.intent
                retrieved = self._project_memory.search_memory(q_text, top_k=3)
                if retrieved:
                    mem_texts = [
                        _scratchpad_clean(m[0].summary, entry_limit)
                        for m in retrieved
                        if m[0].summary
                    ]
                    if mem_texts:
                        add_section(
                            8, f"- Facts & Past Context: {'; '.join(mem_texts)}"
                        )
            except Exception:
                pass

        if not sections:
            return ""

        sections.sort(key=lambda s: s[0])
        lines = [_SCRATCHPAD_HEADER]
        used = len(_SCRATCHPAD_HEADER)
        for _, line in sections:
            if used + 1 + len(line) <= max_chars:
                lines.append(line)
                used += 1 + len(line)
                continue
            remaining = max_chars - used
            if remaining > 21:
                budget_chars = remaining - 1 - 4
                lines.append(line[:budget_chars].rstrip() + " ...")
            break
        return "\n".join(lines)

    def record_memory(
        self, entry: str, category: str = "decision", channel_id: str = "default"
    ) -> None:
        """Record an explicit memory entry into SessionState and persist to project memory."""
        entry = str(entry).strip()
        cat_lower = category.lower().strip()
        if cat_lower in ("tried_failed", "tried_and_failed", "failed"):
            if entry not in self.state.tried_and_failed:
                self.state.tried_and_failed.append(entry)
        elif cat_lower in ("arch_decision", "architectural"):
            if entry not in self.state.arch_decisions:
                self.state.arch_decisions.append(entry)
            if entry not in self.state.decisions:
                self.state.decisions.append(entry)
        else:
            if entry not in self.state.decisions:
                self.state.decisions.append(entry)

        from .embeddings import tokenize_text

        mo = MemoryObject(
            kind=category,
            summary=entry,
            source="user_record",
            channel_id=channel_id,
            vector_tokens=tokenize_text(entry),
            file_paths=list(self.state.files_modified),
            timestamp=datetime.now(),
        )
        self.state.memory_objects.append(mo)
        if self._project_memory and hasattr(self._project_memory, "add_memory_object"):
            try:
                self._project_memory.add_memory_object(mo)
            except Exception:
                pass

        # Explicit memory saves must be durable immediately (debounce bypassed).
        self.persist_to_project_memory(force=True)

    def get_available_headroom(self) -> int:
        """Calculate remaining token budget headroom before reaching max_tokens threshold."""
        used = self.total_tokens
        return max(0, self.config.max_tokens - used)

    def build_critical_context(self) -> str:
        """Build critical context block from session state."""
        return self.format_l0_scratchpad()

    def predict_next_tools(self) -> list[str]:
        """Predict likely next tools based on current state."""
        tools = []
        _EXPLORE_KEYWORDS = {
            "understand",
            "how",
            "what",
            "where",
            "find",
            "architecture",
            "depends",
            "explain",
            "structure",
            "callers",
            "relationship",
        }
        intent_lower = (self.state.intent or self.state.current_task or "").lower()
        # Suggest SEARCH_AST first for exploration or when no file is focused yet
        if (
            not self.state.active_file
            or not self.state.files_modified
            or any(kw in intent_lower for kw in _EXPLORE_KEYWORDS)
        ):
            tools.append("SEARCH_AST")
        if self.state.active_file:
            tools.append("READ_FILE")
        if self.state.errors_seen:
            tools.append("GREP")
        return tools

    def get_intent_for_retrieval(self) -> str:
        return self.state.intent or self.state.current_task

    def get_active_file_hint(self) -> str:
        return self.state.active_file

    def get_snapshot(self) -> ContextSnapshot:
        return ContextSnapshot(
            token_count=self.total_tokens,
            message_count=len(self.messages),
            compression_ratio=self.total_tokens / self.config.max_tokens
            if self.config.max_tokens > 0
            else 0,
            active_file=self.state.active_file,
            tech_stack=self.state.tech_stack,
            errors_seen=self.state.errors_seen,
            files_modified=self.state.files_modified,
            decisions=self.state.decisions,
        )

    def _prune_session_state(self) -> None:
        """Trim SessionState lists to configured maximum to prevent unbounded growth."""
        max_entries = self.config.max_session_state_entries
        
        # Lists to prune (keep most recent entries)
        lists_to_prune = [
            ("files_modified", max_entries),
            ("errors_seen", max_entries),
            ("decisions", max_entries),
            ("arch_decisions", max_entries),
            ("tried_and_failed", max_entries),
            ("tech_stack", max_entries),
            ("failing_tests", max_entries),
            ("dependencies_added", max_entries),
            ("files_read", max_entries),
        ]
        
        for attr_name, limit in lists_to_prune:
            lst = getattr(self.state, attr_name, None)
            if lst and len(lst) > limit:
                setattr(self.state, attr_name, lst[-limit:])
        
        # Also prune dicts that track file metadata
        dicts_to_prune = [
            "files_modified_stats",
            "files_modified_symbols",
            "files_baseline_content",
        ]
        for attr_name in dicts_to_prune:
            d = getattr(self.state, attr_name, None)
            if d and len(d) > max_entries:
                # Keep only entries for the most recently modified files
                recent_files = set(self.state.files_modified[-max_entries:])
                pruned = {k: v for k, v in d.items() if k in recent_files}
                setattr(self.state, attr_name, pruned)

    def record_file_modified(
        self,
        path: str,
        added: int = 0,
        deleted: int = 0,
        old_content: Optional[str] = None,
        new_content: Optional[str] = None,
    ) -> None:
        """Explicitly record a modified file, Net Delta line stats, and touched symbols in session state."""
        if is_valid_file_path(path):
            clean_p = path.strip().strip("'\"`()[],:;")
            if clean_p not in self.state.files_modified:
                self.state.files_modified.append(clean_p)

            # 1. Baseline tracking & Net Delta computation
            if old_content is not None and clean_p not in self.state.files_baseline_content:
                self.state.files_baseline_content[clean_p] = old_content

            if clean_p in self.state.files_baseline_content and new_content is not None:
                net_added, net_deleted = calculate_in_memory_diff(
                    self.state.files_baseline_content[clean_p], new_content
                )
                self.state.files_modified_stats[clean_p] = [net_added, net_deleted]
            else:
                if clean_p not in self.state.files_modified_stats:
                    self.state.files_modified_stats[clean_p] = [added, deleted]
                else:
                    prev = self.state.files_modified_stats[clean_p]
                    self.state.files_modified_stats[clean_p] = [prev[0] + added, prev[1] + deleted]

            # 2. Modified symbol tracking
            if old_content is not None and new_content is not None:
                syms = extract_modified_symbols(old_content, new_content)
                if syms:
                    if clean_p not in self.state.files_modified_symbols:
                        self.state.files_modified_symbols[clean_p] = []
                    for s in syms:
                        if s not in self.state.files_modified_symbols[clean_p]:
                            self.state.files_modified_symbols[clean_p].append(s)

            self.state.active_file = clean_p
            self.persist_to_project_memory()

    def record_file_read(self, path: str) -> None:
        """Explicitly record a read file in session state if it is a valid file path."""
        if is_valid_file_path(path):
            clean_p = path.strip().strip("'\"`()[],:;")
            if clean_p not in self.state.files_read:
                self.state.files_read.append(clean_p)
            self.state.active_file = clean_p
            self.persist_to_project_memory()

    def _update_state_from_message(self, msg: Message) -> None:
        content = msg.content
        role_str = (
            msg.role.value
            if isinstance(msg.role, MessageRole)
            else str(msg.role).lower()
        )

        # User messages: extract explicit valid file paths requested/read
        if role_str == "user":
            candidates = re.findall(
                r"(?:[a-zA-Z0-9_\-/\\]+\.)+[a-zA-Z0-9_\-]+", content
            )
            for p in candidates:
                if is_valid_file_path(p) and p not in self.state.files_read:
                    self.state.files_read.append(p)

        # Assistant messages: scan ONLY for explicit tool calls (JSON or XML or tool syntax) writing/editing files
        elif role_str == "assistant":
            # 1. JSON tool calls: <tool_call>{"name": "WRITE_FILE", "arguments": {"path": "..."}}</tool_call>
            for match in re.finditer(
                r"<tool_call>\s*({[\s\S]*?})\s*</tool_call>", content
            ):
                try:
                    import json

                    data = json.loads(match.group(1))
                    name = (data.get("name") or "").upper()
                    if name in (
                        "WRITE_FILE",
                        "EDIT_FILE",
                        "WRITE_FILE_IMPL",
                        "EDIT_FILE_IMPL",
                    ):
                        args = data.get("arguments") or data.get("params") or {}
                        fpath = args.get("path") or args.get("file")
                        if fpath and is_valid_file_path(fpath):
                            self.record_file_modified(fpath)
                except Exception:
                    pass

            # 2. XML tool calls: <WRITE_FILE path="..."> or <EDIT_FILE path="...">
            for xml_call in re.finditer(
                r'<(?:WRITE_FILE|EDIT_FILE)\s+path=["\']([^"\'\n]+)["\']',
                content,
                re.IGNORECASE,
            ):
                if is_valid_file_path(xml_call.group(1)):
                    self.record_file_modified(xml_call.group(1))

        # Tool result messages: check for tool execution results of WRITE_FILE / EDIT_FILE / READ_FILE
        elif role_str in ("tool", "tool_result"):
            tool_name = (msg.metadata.get("tool_name") or "").upper()
            if tool_name in (
                "WRITE_FILE",
                "EDIT_FILE",
                "WRITE_FILE_IMPL",
                "EDIT_FILE_IMPL",
            ):
                for p in re.findall(
                    r"(?:[a-zA-Z0-9_\-/\\]+\.)+[a-zA-Z0-9_\-]+", content
                ):
                    if is_valid_file_path(p):
                        self.record_file_modified(p)
            elif tool_name in ("READ_FILE", "READ_FILE_IMPL"):
                for p in re.findall(
                    r"(?:[a-zA-Z0-9_\-/\\]+\.)+[a-zA-Z0-9_\-]+", content
                ):
                    if is_valid_file_path(p):
                        self.record_file_read(p)

        # Extract errors
        error_matches = re.findall(
            r"(?:Error|Exception|FAILED)[:\s]+([^\n]{10,100})", content
        )
        for err in error_matches[:2]:
            if err not in self.state.errors_seen:
                self.state.errors_seen.append(err)

        self.persist_to_project_memory()
