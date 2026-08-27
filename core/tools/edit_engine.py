"""File editing engine, AST diff chunk parser, fuzzy symbol boundary matcher, and code quality repair."""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional, Union

from core.tools.fs_tools import (
    _global_memory_mgr,
    _resolve_path,
    _truncate,
    tool_read_file_impl,
    _extract_symbols,
)
from core.tools.code_validator import (
    _normalize_whitespace,
    _detect_stubs,
    _format_code_on_save,
    _check_syntax,
    _detect_truncation_stubs,
    _auto_repair,
    _check_compile,
    _clean_copied_file_text,
    _strip_leading_filename_header,
    _validate_and_repair,
    _detect_symptom_patching,
    _is_test_file,
    _sync_ast_graph,
    _REJECT_ON_STUB_DEFAULT,
    _TAB_PRESERVE_EXTS,
    _TAB_PRESERVE_BASENAMES,
)
from core.tools.diff_parser import (
    _CONFLICT_MARKER_RE,
    _DIFFSTAT_RE,
    _edit_succeeded,
    _parse_diff_block,
    _get_symbol_bounds_ast,
    _get_symbol_bounds_general,
    _reindent_block,
)
from core.tools.write_engine import (
    tool_write_file_impl,
    _commit_edit_file,
    _commit_edit_and_format_result,
    _MAX_TOOL_OUTPUT,
)


def tool_edit_file_impl(args: dict, project_root: str) -> str:
    """EDIT_FILE — surgically replace a block of text in a file with multi-tiered resilient matching."""
    try:
        # Multi-chunk batch edit processing
        chunks = args.get("chunks") or args.get("replacements") or args.get("edits")
        if chunks and isinstance(chunks, list) and len(chunks) > 0:
            path = args.get("path", "")
            if not path:
                return "EDIT_FILE requires a file path."
            p = os.path.join(project_root, path) if not os.path.isabs(path) else path
            original_content = None
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    original_content = f.read()

            def _rollback(reason: str, idx: int, results: list) -> str:
                if original_content is not None:
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(original_content)
                    _sync_ast_graph(project_root, p)
                    restored = " Rolled back to original state."
                else:
                    restored = ""
                return (
                    f"Multi-chunk edit aborted at Chunk {idx + 1} ({reason}).{restored}\n"
                    + "\n".join(results)
                )

            # Only these keys carry over to every chunk. Copying the whole args
            # dict leaked a top-level old_text/new_text/diff into chunks that
            # never named one, editing locations the chunk did not request.
            shared_keys = ("path", "force", "reject_on_stub", "protect_tests")
            base_args = {k: args[k] for k in shared_keys if k in args}

            results = []
            for idx, chunk in enumerate(chunks):
                if not isinstance(chunk, dict):
                    results.append(f"Chunk {idx + 1}: not an object, skipped")
                    return _rollback("malformed chunk", idx, results)
                chunk_args = dict(base_args)
                chunk_args.update(chunk)
                res = tool_edit_file_impl(chunk_args, project_root)
                results.append(f"Chunk {idx + 1}: {res}")
                if not _edit_succeeded(res):
                    # Any non-success — failure, rejection, or no-op — aborts the
                    # batch. Substring checks for "Error"/"Edit failed" missed
                    # rejections and left the batch half-applied.
                    return _rollback("chunk did not apply", idx, results)
            return "\n".join(results)

        path = args.get("path", "")
        old_text = args.get("old_text", "")
        new_text = args.get("new_text", "")
        if not old_text and "content" in args and new_text:
            old_text = args.get("content", "")
        elif not new_text and "content" in args and old_text:
            new_text = args.get("content", "")
        diff_text = (
            args.get("diff") or args.get("block") or args.get("diff_block") or ""
        )
        start_line = args.get("start_line") or args.get("start")
        end_line = args.get("end_line") or args.get("end")
        symbol_name = (
            args.get("symbol") or args.get("symbol_name") or args.get("function")
        )
        force = bool(args.get("force", False))
        reject_on_stub = bool(args.get("reject_on_stub", _REJECT_ON_STUB_DEFAULT))

        # Parse line range suffix from path (e.g. "path/to/file.py:20-45")
        if ":" in path and not os.path.exists(
            os.path.join(project_root, path) if not os.path.isabs(path) else path
        ):
            parts = path.rsplit(":", 1)
            possible_path = parts[0]
            range_part = parts[1]
            if "-" in range_part and range_part.replace("-", "").isdigit():
                try:
                    s_str, e_str = range_part.split("-", 1)
                    start_line = start_line or int(s_str)
                    end_line = end_line or int(e_str)
                    path = possible_path
                except ValueError:
                    pass

        # Check for Aider-style Search/Replace blocks in diff, old_text, or raw inputs.
        # Only a real conflict marker at the start of a line counts. Matching the
        # bare words "SEARCH" or "=======" anywhere in the payload misfires on
        # ordinary source (SEARCH_PATTERN = ..., "# =======" separators) and routes
        # a valid edit into the diff parser.
        diff_attempted = False
        for candidate in [
            diff_text,
            old_text,
            args.get("content", ""),
            args.get("raw", ""),
        ]:
            if candidate and _CONFLICT_MARKER_RE.search(str(candidate)):
                diff_attempted = True
                s_parsed, r_parsed = _parse_diff_block(str(candidate))
                if s_parsed is not None and r_parsed is not None:
                    old_text = s_parsed
                    new_text = r_parsed
                    diff_attempted = False
                    break

        if old_text:
            old_text = _clean_copied_file_text(str(old_text), path)
        if new_text:
            new_text = _clean_copied_file_text(str(new_text), path)

        if not path:
            return "EDIT_FILE requires a file path."

        protect_tests = (
            args.get("protect_tests", False)
            or os.environ.get("TORCHLIGHT_PROTECT_TESTS") == "1"
        )
        if protect_tests and _is_test_file(path):
            return "Error: Test files are protected during automated recovery. Fix the source code instead."

        p = os.path.join(project_root, path) if not os.path.isabs(path) else path

        # Auto-fallback 1: If content/code/new_text was passed to EDIT_FILE without old_text in args, diff, start_line, or symbol:
        has_old_text_arg = bool(old_text) or "old_text" in args or "old" in args or "search" in args
        if not has_old_text_arg and not diff_attempted and not start_line and not symbol_name:
            content_arg = (
                args.get("content")
                or args.get("code")
                or args.get("text")
                or args.get("new_text")
            )
            if content_arg:
                content_arg = _clean_copied_file_text(str(content_arg), path)
                if os.path.exists(p):
                    try:
                        with open(p, "r", encoding="utf-8", errors="replace") as f_curr:
                            existing_content = f_curr.read()
                        existing_lines = [l.strip() for l in existing_content.splitlines() if l.strip()]
                        new_lines = [l.strip() for l in str(content_arg).replace("\\n", "\n").splitlines() if l.strip()]
                        # Any non-empty file counts. The old `> 2` threshold let an
                        # unanchored partial-content edit silently overwrite every
                        # file of two lines or fewer. Genuinely empty files are
                        # handled by the empty-file fallback further down.
                        if existing_lines and len(new_lines) < len(existing_lines) and not force:
                            # Check if content_arg defines a symbol that already exists in the file
                            ext = os.path.splitext(p)[1]
                            new_syms = _extract_symbols(str(content_arg))
                            if new_syms:
                                for _, kind, sym_name in new_syms:
                                    bounds = _get_symbol_bounds_general(existing_content, sym_name, ext)
                                    if bounds:
                                        s_l, e_l = bounds
                                        ex_lines = existing_content.splitlines(keepends=True)
                                        s_idx = s_l - 1
                                        e_idx = min(len(ex_lines), e_l)
                                        new_content = "".join(ex_lines[:s_idx]) + (str(content_arg) if str(content_arg).endswith("\n") else str(content_arg) + "\n") + "".join(ex_lines[e_idx:])
                                        return _commit_edit_and_format_result(
                                            p, new_content, existing_content, project_root, force, reject_on_stub,
                                            f"Surgically replaced {kind} '{sym_name}' in {path} (lines {s_l}-{e_l})"
                                        )

                            return (
                                f"⛔ Edit rejected: You called EDIT_FILE with partial content ({len(new_lines)} lines), "
                                f"which is smaller than existing file '{path}' ({len(existing_lines)} lines) with no 'old_text' or line numbers.\n"
                                f"To safely edit without losing existing code, read '{path}' first to obtain exact 'old_text' anchors:\n"
                                f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{path}"}}}}</tool_call>'
                            )
                    except Exception:
                        pass
                return tool_write_file_impl(
                    {"path": path, "content": content_arg, "force": force}, project_root
                )

        if not os.path.exists(p):
            # Auto-fallback 2: If file does not exist and new_text/content is provided without old_text, auto-create via WRITE_FILE
            content_arg = (
                args.get("content") or args.get("code") or args.get("text") or new_text
            )
            if content_arg and not old_text and not diff_attempted:
                return tool_write_file_impl(
                    {"path": path, "content": content_arg, "force": force}, project_root
                )
            fallback_content = (
                new_text
                or args.get("content")
                or args.get("code")
                or args.get("text")
                or old_text
                or "// Initial code implementation\n"
            )
            return (
                f"File not found: '{path}'.\n"
                f"To create this file from scratch, use WRITE_FILE:\n"
                f'<tool_call>{{"name": "WRITE_FILE", "arguments": {{"path": "{path}", "content": {json.dumps(fallback_content)}}}}}</tool_call>'
            )

        with open(p, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            # Auto-fallback 3: If existing file is empty (0-bytes / template placeholder), populate directly
            new_val = (
                new_text
                or args.get("content")
                or args.get("code")
                or args.get("text")
                or ""
            )
            if new_val:
                return tool_write_file_impl(
                    {"path": path, "content": new_val, "force": force}, project_root
                )

        # AST Symbol-anchored replacement mode
        if symbol_name:
            bounds = _get_symbol_bounds_ast(content, str(symbol_name))
            if bounds:
                s_l, e_l = bounds
                lines = content.splitlines(keepends=True)
                new_content = "".join(lines[: s_l - 1]) + new_text
                if new_text and not new_text.endswith("\n") and e_l < len(lines):
                    new_content += "\n"
                new_content += "".join(lines[e_l:])
                status, payload = _validate_and_repair(
                    new_content,
                    p,
                    project_root,
                    force=force,
                    reject_on_stub=reject_on_stub,
                )
                if status != "ok":
                    return payload
                new_content = payload
                with open(p, "w", encoding="utf-8") as f:
                    f.write(new_content)
                _sync_ast_graph(project_root, p)
                stub_note = _detect_stubs(new_content) or ""
                return f"Surgically replaced symbol '{symbol_name}' in {path} (lines {s_l}-{e_l}).{stub_note}"

        # Line-bounded search window handling
        parsed_s = None
        parsed_e = None
        if start_line is not None or end_line is not None:
            def _parse_l_int(val: Any) -> Optional[int]:
                """Parse a line number, or return None if it is not one.

                Stripping non-digits turned "10-20" into 1020 and "-2" into 2,
                silently editing a range nobody asked for. A malformed bound is
                a hard error, not something to guess at.
                """
                if val is None:
                    return None
                if isinstance(val, bool):
                    return None
                if isinstance(val, int):
                    return val if val >= 1 else None
                text = str(val).strip()
                # Accept the line references models actually emit ("106", "L106",
                # "line 106") but nothing ambiguous: "10-20" is a range, "-2" is
                # signed, "1e5" is a float. Those must fail, not be digit-scraped.
                m = re.fullmatch(r"(?:[Ll](?:ine)?[\s.:#]*)?(\d+)", text)
                if not m:
                    return None
                parsed = int(m.group(1))
                return parsed if parsed >= 1 else None

            parsed_s = _parse_l_int(start_line)
            parsed_e = _parse_l_int(end_line)

            if start_line is not None and parsed_s is None:
                return (
                    f"Edit failed: start_line must be a positive integer, got "
                    f"{start_line!r}. Run READ_FILE('{path}') to get real line numbers."
                )
            if end_line is not None and parsed_e is None:
                return (
                    f"Edit failed: end_line must be a positive integer, got "
                    f"{end_line!r}. Run READ_FILE('{path}') to get real line numbers."
                )
            if parsed_s is None and parsed_e is not None:
                return (
                    f"Edit failed: end_line={parsed_e} was given without start_line, "
                    f"so the edit range is undefined. Provide both bounds, or provide "
                    f"'old_text' to anchor the change."
                )
            if parsed_s is not None and parsed_e is None:
                parsed_e = parsed_s

        if parsed_s is not None and parsed_e is not None:
            try:
                s_l = parsed_s
                e_l = parsed_e
                lines = content.splitlines(keepends=True)
                total_lines = len(lines)

                if s_l > e_l:
                    return f"Edit failed: start_line ({s_l}) cannot be greater than end_line ({e_l})."

                # Strict bounds check: if old_text is not provided, start_line cannot exceed total lines
                if not old_text and s_l > total_lines:
                    return (
                        f"Edit failed: start_line {s_l} is out of bounds for '{path}' which currently has only {total_lines} line(s).\n"
                        f"Next required action: Run READ_FILE to inspect the actual line numbers:\n"
                        f'<tool_call>{{"name": "READ_FILE", "arguments": {{"path": "{path}"}}}}</tool_call>'
                    )

                s_idx = s_l - 1
                e_idx = min(total_lines, e_l)
                target_slice = "".join(lines[s_idx:e_idx])
                if old_text:
                    if old_text in target_slice:
                        new_slice = target_slice.replace(old_text, new_text, 1)
                        new_content = (
                            "".join(lines[:s_idx]) + new_slice + "".join(lines[e_idx:])
                        )
                        new_total = len(new_content.splitlines())
                        return _commit_edit_and_format_result(
                            p,
                            new_content,
                            content,
                            project_root,
                            force,
                            reject_on_stub,
                            f"Surgically edited {path} within line range {s_l}-{e_l} (file now has {new_total} lines)",
                        )
                    elif old_text in content:
                        # Line drift auto-recovery with proximity matching:
                        # If old_text appears multiple times, pick the occurrence closest to the requested s_l
                        matches = []
                        start_search = 0
                        while True:
                            idx = content.find(old_text, start_search)
                            if idx == -1:
                                break
                            line_no = content[:idx].count("\n") + 1
                            matches.append((abs(line_no - s_l), idx, line_no))
                            start_search = idx + len(old_text)

                        matches.sort(key=lambda m: m[0])
                        _, loc_idx, actual_start = matches[0]
                        actual_end = actual_start + old_text.count("\n")
                        new_content = (
                            content[:loc_idx]
                            + new_text
                            + content[loc_idx + len(old_text) :]
                        )
                        new_total = len(new_content.splitlines())
                        return _commit_edit_and_format_result(
                            p,
                            new_content,
                            content,
                            project_root,
                            force,
                            reject_on_stub,
                            f"Surgically edited {path} (relocated from lines {s_l}-{e_l} to lines {actual_start}-{actual_end} due to line drift, file now has {new_total} lines)",
                        )
                    else:
                        return (
                            f"Edit failed: 'old_text' not found within line range {s_l}-{e_l} of {path}. "
                            f"READ_FILE('{path}') first, then provide the exact text from the file as old_text."
                        )
                elif s_l == e_l:
                    return (
                        f"Edit failed: Single-line edit on '{path}:{s_l}' requires 'old_text' to safely anchor the change. "
                        f"Provide 'old_text' with the current line content to replace, or use WRITE_FILE to update the file in full."
                    )
                else:
                    new_content = "".join(lines[:s_idx]) + new_text
                    if new_text and not new_text.endswith("\n") and e_idx < total_lines:
                        new_content += "\n"
                    new_content += "".join(lines[e_idx:])
                    new_total = len(new_content.splitlines())
                    return _commit_edit_and_format_result(
                        p,
                        new_content,
                        content,
                        project_root,
                        force,
                        reject_on_stub,
                        f"Surgically edited {path} within line range {s_l}-{e_l} (file now has {new_total} lines)",
                    )
            except ValueError:
                pass

        ext = os.path.splitext(p)[1]
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)
        content_lines = lines

        if diff_attempted and not old_text:
            return (
                "Edit failed: Malformed diff block syntax in 'diff'. Could not locate valid SEARCH block, '=======' divider, and '>>>>>>> REPLACE' footer.\n"
                "Ensure your diff block follows this exact format:\n"
                "<<<<<<< SEARCH\n"
                "<exact text to replace>\n"
                "=======\n"
                "<new replacement text>\n"
                ">>>>>>> REPLACE\n\n"
                f'Or use exact JSON arguments: {{"path": "{path}", "old_text": "...", "new_text": "..."}}'
            )

        # ── Solution 1: Handle empty, whitespace, or single-char old_text (insert / symbol replace / append mode) ──
        if not old_text or len(old_text.strip()) == 0:
            if not new_text or not new_text.strip():
                return "EDIT_FILE requires non-empty new_text to modify or append to the file."

            # Case A: parsed start line provided -> insert at parsed_s
            if parsed_s is not None:
                s_idx = max(0, min(total_lines, parsed_s - 1))
                new_content = "".join(lines[:s_idx]) + (new_text if new_text.endswith("\n") else new_text + "\n") + "".join(lines[s_idx:])
                return _commit_edit_and_format_result(
                    p, new_content, content, project_root, force, reject_on_stub,
                    f"Surgically inserted new code at line {parsed_s} in {path}"
                )

            # Case B: new_text declares a function/class that already exists in content -> replace that symbol
            new_syms = _extract_symbols(new_text)
            if new_syms:
                for _, kind, sym_name in new_syms:
                    bounds = _get_symbol_bounds_general(content, sym_name, ext)
                    if bounds:
                        s_l, e_l = bounds
                        s_idx = s_l - 1
                        e_idx = min(total_lines, e_l)
                        new_content = "".join(lines[:s_idx]) + (new_text if new_text.endswith("\n") else new_text + "\n") + "".join(lines[e_idx:])
                        return _commit_edit_and_format_result(
                            p, new_content, content, project_root, force, reject_on_stub,
                            f"Surgically replaced {kind} '{sym_name}' in {path} (lines {s_l}-{e_l})"
                        )

            # Case C: Smart insert before trailing listeners / export statements
            listener_match = re.search(r"(\n\s*(?:window\.|document\.)?addEventListener\s*\(|\n\s*(?:export\s+default|module\.exports\s*=))", content)
            if listener_match:
                ins_idx = listener_match.start()
                new_content = content[:ins_idx] + "\n\n" + new_text.strip() + "\n" + content[ins_idx:]
                return _commit_edit_and_format_result(
                    p, new_content, content, project_root, force, reject_on_stub,
                    f"Surgically inserted code before event listeners/exports in {path}"
                )

            # Case D: Append to the end of the file
            sep = "\n\n" if not content.endswith("\n\n") else ""
            if not content.endswith("\n"):
                sep = "\n\n"
            new_content = content + sep + new_text.strip() + "\n"
            return _commit_edit_and_format_result(
                p, new_content, content, project_root, force, reject_on_stub,
                f"Surgically appended new code to {path}"
            )

        if new_text == old_text:
            return (
                "No change: old_text and new_text are identical — the edit would make zero modifications.\n"
                "Action required: Provide DIFFERENT old_text and new_text values, or:\n"
                "1. Use READ_FILE first to see the exact current content\n"
                "2. Then copy the EXACT text you want to replace as old_text\n"
                "3. Provide the NEW replacement text as new_text\n"
                "4. Or use WRITE_FILE to overwrite the entire file\n"
                "5. Or use 'symbol' parameter to target a specific function/class"
            )
        if content.strip() and old_text.strip() == content.strip() and not new_text.strip():
            return f"Edit failed: Attempted to replace entire content of '{path}' with empty text via EDIT_FILE. Use WRITE_FILE if you explicitly intend to overwrite or clear a file."

        # Handle unescaped literal \\n and \\t from raw JSON outputs
        if "\\n" in old_text and "\n" not in old_text:
            old_text = old_text.replace("\\n", "\n").replace("\\t", "\t")
        if "\\n" in new_text and "\n" not in new_text:
            new_text = new_text.replace("\\n", "\n").replace("\\t", "\t")

        # Strip line number prefixes if model copied from READ_FILE output (e.g. "  1 | <style>")
        if re.search(r"^\s*\d+\s*\|\s*", old_text, re.MULTILINE):
            old_text = re.sub(r"^\s*\d+\s*\|\s*", "", old_text, flags=re.MULTILINE)

        # Normalize typographic smart quotes and non-breaking spaces if exact match not immediately found
        def _clean_smart_chars(s: str) -> str:
            return (
                s.replace("“", '"')
                .replace("”", '"')
                .replace("‘", "'")
                .replace("’", "'")
                .replace("\u00a0", " ")
            )

        if old_text not in content:
            cleaned_candidate = _clean_smart_chars(old_text)
            if cleaned_candidate in content:
                old_text = cleaned_candidate

        # ── Solution 2: Exact string match with smart disambiguation ──
        if old_text in content:
            count = content.count(old_text)
            if count > 1:
                # 1. If start_line is provided, pick the occurrence nearest to parsed_s
                if parsed_s is not None:
                    matches = []
                    start_search = 0
                    while True:
                        idx = content.find(old_text, start_search)
                        if idx == -1:
                            break
                        line_no = content[:idx].count("\n") + 1
                        matches.append((abs(line_no - parsed_s), idx, line_no))
                        start_search = idx + len(old_text)
                    matches.sort(key=lambda m: m[0])
                    _, loc_idx, actual_start = matches[0]
                    new_content = content[:loc_idx] + new_text + content[loc_idx + len(old_text):]
                    return _commit_edit_and_format_result(
                        p, new_content, content, project_root, force, reject_on_stub,
                        f"Surgically edited {path} (disambiguated match nearest line {parsed_s})"
                    )

                # 2. If old_text is very short (<= 3 chars, e.g. "}", "\n", ";") and new_text has a symbol declaration
                if len(old_text.strip()) <= 3:
                    new_syms = _extract_symbols(new_text)
                    if new_syms:
                        for _, kind, sym_name in new_syms:
                            bounds = _get_symbol_bounds_general(content, sym_name, ext)
                            if bounds:
                                s_l, e_l = bounds
                                s_idx = s_l - 1
                                e_idx = min(total_lines, e_l)
                                new_content = "".join(lines[:s_idx]) + (new_text if new_text.endswith("\n") else new_text + "\n") + "".join(lines[e_idx:])
                                return _commit_edit_and_format_result(
                                    p, new_content, content, project_root, force, reject_on_stub,
                                    f"Surgically replaced {kind} '{sym_name}' in {path} (lines {s_l}-{e_l})"
                                )

                return f"Edit failed: 'old_text' matches {count} locations. Provide line numbers (start_line/end_line) or more context to make it unique."

            idx = content.find(old_text)
            reindented_new_text = _reindent_block(old_text, new_text, content, idx)
            new_content = content[:idx] + reindented_new_text + content[idx + len(old_text):]
            return _commit_edit_and_format_result(
                p,
                new_content,
                content,
                project_root,
                force,
                reject_on_stub,
                f"Surgically edited {path} (replaced {len(old_text)} chars with {len(reindented_new_text)} chars)",
            )

        # Helper: Normalize lines for line-based matching
        def normalize_line(l):
            return l.strip()

        # Tier 2: Fuzzy whitespace-agnostic line matching
        old_norm = [
            normalize_line(l) for l in old_text.splitlines() if normalize_line(l)
        ]
        if not old_norm:
            return "Edit failed: 'old_text' is empty or contains only whitespace."

        def _fuzzy_match_at(i: int) -> Optional[int]:
            """If old_norm matches content starting exactly at line i, return the
            exclusive end index. Interior blank lines are skipped, but line i
            itself must be the first real line of the block — otherwise every
            blank line preceding a block counts as a separate match and a unique
            block is reported as ambiguous (PEP 8 puts blank lines before almost
            every function, so this rejected most valid edits)."""
            if not content_lines[i].strip():
                return None
            match_count = 0
            j = i
            while j < len(content_lines) and match_count < len(old_norm):
                if not content_lines[j].strip():
                    j += 1
                    continue
                if content_lines[j].strip() == old_norm[match_count]:
                    match_count += 1
                    j += 1
                else:
                    return None
            return j if match_count == len(old_norm) else None

        fuzzy_matches = []  # [(start_idx, end_idx), ...]
        for i in range(len(content_lines)):
            end = _fuzzy_match_at(i)
            if end is not None:
                fuzzy_matches.append((i, end))

        matches_found = len(fuzzy_matches)
        best_start = -1
        best_end = -1
        if matches_found == 1:
            best_start, best_end = fuzzy_matches[0]
        elif matches_found > 1:
            if parsed_s is not None:
                # Genuinely ambiguous: pick the occurrence nearest the hinted line.
                best_start, best_end = min(
                    fuzzy_matches, key=lambda m: abs((m[0] + 1) - parsed_s)
                )
            else:
                lines_hint = ", ".join(str(m[0] + 1) for m in fuzzy_matches[:5])
                return (
                    f"Edit failed: 'old_text' fuzzy-matches {matches_found} locations "
                    f"in {path} (lines {lines_hint}). Provide start_line/end_line or "
                    f"more surrounding context to disambiguate."
                )

        if best_start != -1:
            new_content = "".join(content_lines[:best_start]) + new_text
            if (
                new_text
                and not new_text.endswith("\n")
                and best_end < len(content_lines)
            ):
                new_content += "\n"
            new_content += "".join(content_lines[best_end:])

            return _commit_edit_and_format_result(
                p,
                new_content,
                content,
                project_root,
                force,
                reject_on_stub,
                f"Surgically edited {path} (fuzzy replaced {len(old_norm)} lines ignoring whitespace)",
            )

        # Tier 3: Ellipsis / Wildcard matching (e.g. header \n ... \n footer)
        old_raw_lines = [l.strip() for l in old_text.splitlines()]
        wildcard_indices = [
            idx
            for idx, l in enumerate(old_raw_lines)
            if l in ("...", "…", "# ...", "// ...", "/* ... */")
        ]
        if len(wildcard_indices) == 1:
            w_idx = wildcard_indices[0]
            head_norm = [
                normalize_line(l)
                for l in old_text.splitlines()[:w_idx]
                if normalize_line(l)
            ]
            tail_norm = [
                normalize_line(l)
                for l in old_text.splitlines()[w_idx + 1 :]
                if normalize_line(l)
            ]

            if head_norm and tail_norm:
                # Find head match
                head_match_idx = -1
                for i in range(len(content_lines)):
                    if content_lines[i].strip() == head_norm[0]:
                        if all(
                            i + k < len(content_lines)
                            and content_lines[i + k].strip() == head_norm[k]
                            for k in range(len(head_norm))
                        ):
                            head_match_idx = i
                            break

                # Find tail match after head
                if head_match_idx != -1:
                    tail_match_idx = -1
                    for i in range(head_match_idx + len(head_norm), len(content_lines)):
                        if content_lines[i].strip() == tail_norm[0]:
                            if all(
                                i + k < len(content_lines)
                                and content_lines[i + k].strip() == tail_norm[k]
                                for k in range(len(tail_norm))
                            ):
                                tail_match_idx = i + len(tail_norm)
                                break

                    if tail_match_idx != -1:
                        new_content = "".join(content_lines[:head_match_idx]) + new_text
                        if (
                            new_text
                            and not new_text.endswith("\n")
                            and tail_match_idx < len(content_lines)
                        ):
                            new_content += "\n"
                        new_content += "".join(content_lines[tail_match_idx:])

                        return _commit_edit_and_format_result(
                            p,
                            new_content,
                            content,
                            project_root,
                            force,
                            reject_on_stub,
                            f"Surgically edited {path} (wildcard replaced block from line {head_match_idx + 1} to {tail_match_idx})",
                        )

        # ── Solution 5: Multi-Anchor Matching (Entry & Exit Anchor) ──
        if len(old_norm) >= 2:
            first_l = old_norm[0]
            last_l = old_norm[-1]

            first_matches = [
                i for i, l in enumerate(content_lines) if l.strip() == first_l
            ]
            last_matches = [
                i for i, l in enumerate(content_lines) if l.strip() == last_l
            ]

            # Find valid (first, last) pair
            valid_pairs = []
            for f_i in first_matches:
                for l_i in last_matches:
                    if f_i < l_i and (l_i - f_i) <= len(old_norm) + 15:
                        valid_pairs.append((f_i, l_i))

            if len(valid_pairs) == 1:
                f_idx, l_idx = valid_pairs[0]
                new_content = "".join(content_lines[:f_idx]) + new_text
                if (
                    new_text
                    and not new_text.endswith("\n")
                    and (l_idx + 1) < len(content_lines)
                ):
                    new_content += "\n"
                new_content += "".join(content_lines[l_idx + 1 :])

                return _commit_edit_and_format_result(
                    p,
                    new_content,
                    content,
                    project_root,
                    force,
                    reject_on_stub,
                    f"Surgically edited {path} (anchor replaced block between lines {f_idx + 1} and {l_idx + 1})",
                )

        # Tier 5: Difflib similarity ratio matching (>= 85% similarity)
        # real_quick_ratio() and quick_ratio() are cheap upper bounds on ratio(),
        # so skipping a window whose upper bound is already below the acceptance
        # threshold cannot change the outcome — it only avoids the O(n*m) compare.
        # Holding old_text as seq2 also lets SequenceMatcher reuse its b-chain
        # across windows instead of rebuilding it for every candidate.
        _SIMILARITY_THRESHOLD = 0.85
        best_ratio = 0.0
        best_diff_start = -1
        best_diff_end = -1
        window_size = len(old_norm)

        _sm = difflib.SequenceMatcher(None, "", old_text)
        for w_size in range(max(1, window_size - 4), window_size + 5):
            for i in range(len(content_lines) - w_size + 1):
                block = "".join(content_lines[i : i + w_size])
                _sm.set_seq1(block)
                if _sm.real_quick_ratio() < _SIMILARITY_THRESHOLD:
                    continue
                if _sm.quick_ratio() < _SIMILARITY_THRESHOLD:
                    continue
                ratio = _sm.ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_diff_start = i
                    best_diff_end = i + w_size

        if best_ratio >= _SIMILARITY_THRESHOLD and best_diff_start != -1:
            new_content = "".join(content_lines[:best_diff_start]) + new_text
            if (
                new_text
                and not new_text.endswith("\n")
                and best_diff_end < len(content_lines)
            ):
                new_content += "\n"
            new_content += "".join(content_lines[best_diff_end:])

            return _commit_edit_and_format_result(
                p,
                new_content,
                content,
                project_root,
                force,
                reject_on_stub,
                f"Surgically edited {path} (similarity replaced block with {int(best_ratio * 100)}% match at lines {best_diff_start + 1}-{best_diff_end})",
            )

        # There was a Tier 6 here: character-level subsequence matching over every
        # window in the file. It was removed rather than optimised. It never fired
        # across the whole test suite, it accounted for ~38s of a 41s failed edit,
        # and its acceptance condition (a contiguous common run of >=85% of
        # old_text) is strictly harder to satisfy than the similarity tier directly
        # above it (window ratio >= 0.85) — so that tier already subsumes it. The
        # matching it was there to rescue was really being lost to the blank-line
        # bug in the fuzzy tier above, which is now fixed.

        # ── Solution 3: Symbol-Level Replacement Fallback ──
        new_syms = _extract_symbols(new_text)
        if new_syms and len(new_syms) == 1:
            for _, kind, sym_name in new_syms:
                bounds = _get_symbol_bounds_general(content, sym_name, ext)
                if bounds:
                    s_l, e_l = bounds
                    s_idx = s_l - 1
                    e_idx = min(total_lines, e_l)
                    new_content = "".join(lines[:s_idx]) + (new_text if new_text.endswith("\n") else new_text + "\n") + "".join(lines[e_idx:])
                    return _commit_edit_and_format_result(
                        p, new_content, content, project_root, force, reject_on_stub,
                        f"Surgically replaced {kind} '{sym_name}' in {path} (lines {s_l}-{e_l})"
                    )

        # All tiers failed — point the model at where to look next.
        #
        # This used to re-scan every 10-line window in the file with difflib to
        # report a "closest match" percentage: 9.5s of a 10s failed edit, spent
        # entirely on an error string. It was also poor advice, since a 48% match
        # is a coincidentally-similar block, not the intended target.
        #
        # Two signals that cost nothing are better. The similarity tier above has
        # already scored correctly-sized windows, so reuse its winner when it found
        # one. Otherwise locate the first line the caller actually named with a
        # single C-speed str.find, which answers the more useful question: where
        # does your anchor appear at all?
        closest_line = None
        if best_ratio > 0 and best_diff_start != -1:
            closest_line = best_diff_start + 1
            hint = f"closest block ~L{closest_line} ({int(best_ratio * 100)}% match)"
        else:
            first_line = next(
                (ln.strip() for ln in old_text.splitlines() if ln.strip()), ""
            )
            found = content.find(first_line) if len(first_line) >= 4 else -1
            if found != -1:
                closest_line = content[:found].count("\n") + 1
                hint = f"first line of old_text found at L{closest_line}"
            else:
                hint = "no part of old_text occurs in this file"

        nxt = (
            f"READ_FILE('{path}:{max(1, closest_line - 5)}-{closest_line + 15}')"
            if closest_line
            else f"READ_FILE('{path}')"
        )
        return (
            f"Edit failed: Could not find matching block for 'old_text' in {path}. "
            f"EDIT_FAIL: '{path}' — {hint}. "
            f"NEXT: {nxt} to copy exact text, or WRITE_FILE to replace the file."
        )
    except Exception as e:
        return f"Error editing file: {e}"


__all__ = [
    "_normalize_whitespace",
    "_detect_stubs",
    "_format_code_on_save",
    "_check_syntax",
    "_detect_truncation_stubs",
    "_auto_repair",
    "_check_compile",
    "_clean_copied_file_text",
    "_strip_leading_filename_header",
    "_validate_and_repair",
    "_detect_symptom_patching",
    "_is_test_file",
    "_sync_ast_graph",
    "_REJECT_ON_STUB_DEFAULT",
    "_edit_succeeded",
    "_parse_diff_block",
    "_get_symbol_bounds_ast",
    "_get_symbol_bounds_general",
    "_reindent_block",
    "tool_write_file_impl",
    "_commit_edit_file",
    "_commit_edit_and_format_result",
    "tool_edit_file_impl",
]

