"""File system inspection, reading, directory listing, grep, and image viewing tools."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

_MAX_TOOL_OUTPUT = 4000
_global_memory_mgr = None


def set_memory_manager(mgr) -> None:
    """Set global active TieredMemory instance for tool synchronization."""
    global _global_memory_mgr
    _global_memory_mgr = mgr


# ── Symbol extraction patterns ────────────────────────────────────────────

_SYM_PATTERNS = [
    (
        re.compile(r"^\s*(?:async\s+)?def\s+(\w+)(?:\[[^\]]+\])?\s*\(", re.MULTILINE),
        "fn",
    ),
    (re.compile(r"^\s*class\s+(\w+)\b", re.MULTILINE), "class"),
    (
        re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE),
        "fn",
    ),
    (re.compile(r"^\s*(?:export\s+)?class\s+(\w+)", re.MULTILINE), "class"),
    (
        re.compile(
            r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^\s=]+)\s*=>",
            re.MULTILINE,
        ),
        "fn",
    ),
    (re.compile(r"^\s*(?:export\s+)?interface\s+(\w+)", re.MULTILINE), "struct"),
    (re.compile(r"^\s*(?:pub\s+)?fn\s+(\w+)", re.MULTILINE), "fn"),
    (re.compile(r"^\s*(?:pub\s+)?(?:struct|enum)\s+(\w+)", re.MULTILINE), "struct"),
    (re.compile(r"^\s*(?:fun)\s+(\w+)\s*\(", re.MULTILINE), "fn"),
    (re.compile(r"^\s*type\s+(\w+)\s+struct", re.MULTILINE), "struct"),
]


def _extract_symbols(content: str, max_symbols: int = 40) -> list:
    """Return [(lineno_1based, kind, name), ...] sorted by line number."""
    found = []
    seen = set()
    for pattern, kind in _SYM_PATTERNS:
        for m in pattern.finditer(content):
            name = m.group(1)
            lineno = content[: m.start()].count("\n") + 1
            key = (lineno, name)
            if key in seen:
                continue
            found.append((lineno, kind, name))
            seen.add(key)
    found.sort(key=lambda x: x[0])
    return found[:max_symbols]


def _symbol_map(content: str, filename: str) -> str:
    """Compact symbol map prepended to READ_FILE output."""
    syms = _extract_symbols(content)
    if not syms:
        return ""
    lines = ["Symbols:"]
    for lineno, kind, name in syms:
        lines.append(f"  L{lineno:>4}  {kind:<6} {name}")
    lines.append("")
    return "\n".join(lines)


def _resolve_path(path: str, project_root: str) -> str:
    """Resolve a path relative to project root, handling ~ and absolute paths."""
    if not path:
        return project_root
    expanded = os.path.expanduser(path)
    p = Path(expanded)
    root_p = Path(project_root).resolve()

    if p.is_absolute():
        p_resolved = p.resolve()
        try:
            p_resolved.relative_to(root_p)
            return str(p_resolved)
        except ValueError:
            filename = p.name
            return str((root_p / filename).resolve())

    resolved = (root_p / p).resolve()
    return str(resolved)


def _truncate(
    text: str, limit: Optional[int] = None, tool_name: Optional[str] = None
) -> str:
    if limit is None:
        if tool_name:
            tool_upper = tool_name.upper().strip()
            if tool_upper == "RUN_COMMAND":
                limit = 3000
            elif tool_upper in ("GREP", "SEARCH_AST"):
                limit = 3500
            elif tool_upper == "READ_FILE":
                _, limit = _read_budget_for_ctx()
            else:
                limit = _MAX_TOOL_OUTPUT
        else:
            limit = _MAX_TOOL_OUTPUT

    if len(text) > limit:
        truncated_chars = len(text) - limit
        truncated_lines = text[limit:].count("\n")
        return (
            text[:limit]
            + f"\n... [Truncated {truncated_chars} chars / {truncated_lines} lines. Use line ranges or specific queries to narrow search.]"
        )
    return text


def _read_budget() -> tuple:
    """Return (MAX_LINES, MAX_CHARS) based on available context window."""
    return 100, 4_000


# ── Context-window budget ─────────────────────────────────────────────────

_CTX_WINDOW: int = 8000


def set_ctx_window(n: int) -> None:
    """Tell the tool layer what context window the current model has."""
    global _CTX_WINDOW
    _CTX_WINDOW = max(1024, int(n))


def _read_budget_for_ctx() -> tuple:
    """Return (MAX_LINES, MAX_CHARS) for the current context window."""
    w = _CTX_WINDOW
    if w <= 4096:
        return 60, 2_400
    if w <= 8192:
        return 100, 4_000
    if w <= 16384:
        return 150, 6_000
    return 250, 10_000


def tool_read_file_impl(args: dict, project_root: str) -> str:
    """READ_FILE — read a file with optional line-range or symbol syntax."""
    try:
        path = (args.get("path") or "").strip().lstrip("@")
        if not path:
            return "READ_FILE requires a file path. Use RUN_COMMAND('ls') to see directory contents."

        def _parse_line_int(val: Any) -> Optional[int]:
            if val is None:
                return None
            if isinstance(val, int):
                return max(1, val)
            s = str(val).strip()
            digits = re.sub(r"[^\d]", "", s)
            return max(1, int(digits)) if digits else None

        range_start = None
        range_end = None
        symbol_name = None

        m_range = re.match(r"^(.+?)\s*:\s*[Ll]?(\d+)\s*-\s*[Ll]?(\d+)\s*$", path)
        m_line = re.match(r"^(.+?)\s*:\s*[Ll]?(\d+)\s*$", path)
        m_sym = re.match(r"^(.+?)\s*:\s*([A-Za-z_]\w*)\s*$", path)

        if m_range:
            path, range_start, range_end = (
                m_range.group(1).strip(),
                max(1, int(m_range.group(2))),
                max(1, int(m_range.group(3))),
            )
        elif m_line:
            path, range_start = m_line.group(1).strip(), max(1, int(m_line.group(2)))
            range_end = range_start
        elif m_sym:
            path, symbol_name = m_sym.group(1).strip(), m_sym.group(2)
        else:
            range_val = args.get("range") or args.get("lines")
            if range_val and isinstance(range_val, str) and "-" in range_val:
                r_parts = range_val.split("-", 1)
                range_start = _parse_line_int(r_parts[0])
                range_end = _parse_line_int(r_parts[1])
            elif range_val and isinstance(range_val, (list, tuple)) and len(range_val) >= 2:
                range_start = _parse_line_int(range_val[0])
                range_end = _parse_line_int(range_val[1])
            else:
                if args.get("start_line") is not None or args.get("end_line") is not None:
                    range_start = _parse_line_int(args.get("start_line")) or 1
                    range_end = _parse_line_int(args.get("end_line"))
                elif args.get("symbol"):
                    symbol_name = str(args["symbol"]).strip()

        # Path resolution
        p = os.path.abspath(os.path.join(project_root, path))

        # Security check
        cwd_abs = os.path.abspath(project_root)
        cwd_prefix = cwd_abs if cwd_abs.endswith(os.sep) else cwd_abs + os.sep
        if not p.startswith(cwd_prefix) and p != cwd_abs:
            return f"Access denied: {path} is outside the workspace."

        if not os.path.exists(p):
            if ":" in path:
                base_path = path.split(":")[0]
                if os.path.exists(os.path.join(project_root, base_path)):
                    return (
                        f"Syntax error in READ_FILE: '{path}'\n"
                        f"The suffix after ':' was not recognized as a LINE, RANGE (N-M), or SYMBOL.\n"
                        f"Valid formats: '{base_path}:10-20', '{base_path}:15', or '{base_path}:ClassOrFunc'."
                    )
            return (
                f"File not found: '{path}'.\n"
                f"If you are creating a new file or starting a new task, use WRITE_FILE to create and write the code:\n"
                f'<tool_call>{{"name": "WRITE_FILE", "arguments": {{"path": "{path}", "content": "// Initial code implementation\\n"}}}}</tool_call>'
            )

        if os.path.isdir(p):
            return f"{path} is a directory. Use RUN_COMMAND('ls {path}') to list it."

        # Image file redirection
        image_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            ".bmp",
            ".ico",
            ".svg",
            ".tiff",
        }
        ext = os.path.splitext(p)[1].lower()
        if ext in image_extensions:
            return f"ℹ️ '{os.path.basename(p)}' is a binary image file. Use VIEW_IMAGE(path='{path}') to inspect this image visually."

        # Binary detection
        file_size = os.path.getsize(p)
        try:
            import psutil

            available_ram_gb = psutil.virtual_memory().available / (1024**3)
        except ImportError:
            available_ram_gb = 8
        if available_ram_gb <= 10:
            max_file_size = 500_000
        elif available_ram_gb <= 20:
            max_file_size = 1_000_000
        else:
            max_file_size = 2_000_000

        if file_size > max_file_size:
            return f"{os.path.basename(p)} ({file_size:,} bytes) — FILE TOO LARGE. Use RUN_COMMAND('head -n 100 {path}') for a preview."

        with open(p, "rb") as bf:
            chunk = bf.read(1024)
            if b"\x00" in chunk:
                return f"{os.path.basename(p)} ({file_size:,} bytes) — BINARY FILE, content omitted."

        # Read with encoding fallback
        try:
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(p, "r", encoding="latin-1") as f:
                    content = f.read()
            except Exception as e:
                return f"Error reading file: {e}"

        lines = content.splitlines()
        nlines = len(lines)
        ext = os.path.splitext(p)[1].lstrip(".")
        fname = os.path.basename(p)
        MAX_LINES, MAX_CHARS = _read_budget_for_ctx()

        # Symbol lookup
        if symbol_name:
            syms = _extract_symbols(content)
            target = next((s for s in syms if s[2] == symbol_name), None)
            if target:
                range_start = target[0]
                next_sym = next((s for s in syms if s[0] > range_start), None)
                range_end = (next_sym[0] - 1) if next_sym else nlines
            else:
                return (
                    f"Symbol '{symbol_name}' not found in {fname}.\n"
                    f"{_symbol_map(content, fname)}"
                    f'Use READ_FILE("{path}:<NAME>") with a name from the list above.'
                )

        # Line-range slice
        if range_start is not None:
            r0 = max(0, range_start - 1)
            r1 = min(nlines, range_end or nlines)
            sl = lines[r0:r1]
            if len(sl) > MAX_LINES:
                sl = sl[:MAX_LINES]
                trunc_note = (
                    f"\n... (capped at {MAX_LINES} lines — use a tighter range)"
                )
            else:
                trunc_note = ""
            start_num = r0 + 1
            max_num = r0 + len(sl)
            width = max(len(str(max_num)), 3)
            formatted = [
                f"{r0 + i + 1:>{width}} | {line}" for i, line in enumerate(sl)
            ]
            display = "\n".join(formatted)[:MAX_CHARS]
            return (
                f"{fname} lines {start_num}–{max_num} (of {nlines} total)\n"
                f"```{ext}\n{display}{trunc_note}\n```"
            )

        # Default: symbol map + top-N lines
        sym_hdr = _symbol_map(content, fname)
        sl = lines[:MAX_LINES]
        max_num = len(sl)
        width = max(len(str(max_num)), 3)
        formatted = [
            f"{i + 1:>{width}} | {line}" for i, line in enumerate(sl)
        ]
        display = "\n".join(formatted)[:MAX_CHARS]
        truncated = nlines > MAX_LINES or len(content) > MAX_CHARS
        next_start = MAX_LINES + 1
        next_end = min(nlines, MAX_LINES * 2)
        suffix = (
            (
                f"\n... ({nlines - MAX_LINES} more lines)"
                f' — use READ_FILE("{path}:{next_start}-{next_end}") for lines {next_start}-{next_end},'
                f' or READ_FILE("{path}:<SYMBOL>") to jump to a function.'
            )
            if truncated
            else ""
        )

        return f"{sym_hdr}{fname} ({nlines} lines)\n```{ext}\n{display}{suffix}\n```"

    except Exception as e:
        return f"READ_FILE error: {e}"


def tool_read_symbols_impl(args: dict, project_root: str) -> str:
    """READ_SYMBOLS — show file structure without loading content."""
    try:
        path = str(
            args.get(
                "path", args.get("file", args.get("filename", args.get("filepath", "")))
            )
        ).strip().lstrip("@")
        if not path:
            return "READ_SYMBOLS requires a file path. Use RUN_COMMAND('ls') to see directory contents."

        from core.utils.image_utils import is_image_file

        p = os.path.join(project_root, path) if not os.path.isabs(path) else path

        # Security
        cwd_abs = os.path.abspath(project_root)
        cwd_prefix = cwd_abs if cwd_abs.endswith(os.sep) else cwd_abs + os.sep
        if (
            not os.path.abspath(p).startswith(cwd_prefix)
            and os.path.abspath(p) != cwd_abs
        ):
            return f"Access denied: {path} is outside the workspace."

        if not os.path.exists(p):
            return f"File not found: {path}"
        if os.path.isdir(p):
            return f"{path} is a directory. Use RUN_COMMAND('ls {path}') to list it."

        if is_image_file(p):
            return f"ℹ️ '{os.path.basename(p)}' is an image file and does not contain AST code symbols. Visual context is attached for vision models, or use VIEW_IMAGE to inspect."

        try:
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(p, "r", encoding="latin-1") as f:
                content = f.read()
        except Exception as e:
            return f"Error reading symbols from {path}: {e}"

        nlines = content.count("\n") + 1
        fname = os.path.basename(p)
        syms = _extract_symbols(content, max_symbols=60)
        if not syms:
            return f"{fname} ({nlines} lines) — no symbols detected."
        lines = [f"{fname} ({nlines} lines) — {len(syms)} symbol(s):"]
        for lineno, kind, name in syms:
            lines.append(f"  L{lineno:>4}  {kind:<6} {name}")
        lines.append("")
        lines.append(f'READ_FILE("{path}:<SYMBOL>") — read one symbol')
        lines.append(f'READ_FILE("{path}:N-M")      — read lines N through M')
        return "\n".join(lines)
    except Exception as e:
        return f"READ_SYMBOLS error: {e}"


def tool_list_dir_impl(args: dict, project_root: str) -> str:
    """LIST_DIR — list directory contents."""
    path = args.get("path", ".")
    p = _resolve_path(path, project_root)

    try:
        entries = sorted(os.listdir(p))
        lines = []
        for entry in entries:
            full = os.path.join(p, entry)
            if os.path.isdir(full):
                lines.append(f"  {entry}/")
            else:
                try:
                    size = os.path.getsize(full)
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f}KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f}MB"
                    lines.append(f"  {entry}  ({size_str})")
                except OSError:
                    lines.append(f"  {entry}")

        header = f"{p} ({len(entries)} items)"
        return f"{header}\n" + _truncate("\n".join(lines))
    except FileNotFoundError:
        return f"Directory not found: {path}"
    except Exception as e:
        return f"Error listing {path}: {e}"


def tool_grep_impl(args: dict, project_root: str) -> str:
    """GREP — search for a pattern in files using ripgrep (rg) with Python fallback."""
    import shutil

    try:
        pattern = args.get("pattern", "")
        path = str(args.get("path", ".")).strip().lstrip("@")
        p = os.path.join(project_root, path) if not os.path.isabs(path) else path
        if not pattern:
            return "GREP requires a pattern. Usage: GREP(pattern='def ', path='src')"

        rg_path = shutil.which("rg")
        if rg_path:
            return _grep_rg(pattern, p, project_root, rg_path)

        return _grep_python(pattern, p, project_root)
    except Exception as e:
        return f"GREP error: {e}"


def _grep_rg(pattern: str, path: str, project_root: str, rg_path: str) -> str:
    """Search using ripgrep for maximum speed and accuracy."""
    MAX_MATCHES = 30
    CONTEXT = 2

    parts = [
        rg_path,
        "--line-number",
        "--context",
        str(CONTEXT),
        "--max-count",
        str(MAX_MATCHES),
        "--color",
        "never",
        "--hidden",
        "--glob",
        "!.git",
        "--glob",
        "!__pycache__",
        "--glob",
        "!node_modules",
        "--glob",
        "!venv",
        "--glob",
        "!.venv",
        "--glob",
        "!*.pyc",
        "--glob",
        "!*.pyo",
        "--glob",
        "!*.so",
        "--glob",
        "!*.o",
        "--glob",
        "!*.class",
        "--glob",
        "!build",
        "--glob",
        "!dist",
        "--glob",
        "!.gradle",
        "--glob",
        "!.idea",
    ]

    if os.path.isfile(path):
        parts.extend(["--no-ignore", "--", pattern, path])
    elif os.path.isdir(path):
        parts.extend(["--", pattern, path])
    else:
        return f"GREP: path not found: {path}"

    try:
        r = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=30,
        )
        output = (r.stdout or "").strip()
        if not output:
            return f"GREP: no matches for '{pattern}' in {os.path.relpath(path, project_root)}"

        match_count = sum(
            1
            for line in output.splitlines()
            if line and ":" in line and not line.startswith("--")
        )

        header = f"GREP '{pattern}' — {match_count} match(es) via ripgrep"
        if match_count >= MAX_MATCHES:
            header += f" (showing first {MAX_MATCHES})"

        return f"{header}:\n\n{output}"
    except subprocess.TimeoutExpired:
        return "GREP timed out (30s). Try a more specific pattern or path."
    except Exception:
        return _grep_python(pattern, path, project_root)


def _grep_python(pattern: str, path: str, project_root: str) -> str:
    """Pure Python grep fallback when ripgrep is not available."""
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        regex = re.compile(re.escape(pattern), re.IGNORECASE)

    MAX_MATCHES = 20
    CONTEXT = 2
    results = []

    def _search_file(filepath, relpath):
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                flines = f.readlines()
        except OSError:
            return
        match_idxs = [i for i, ln in enumerate(flines) if regex.search(ln)]
        if not match_idxs:
            return
        groups = []
        for idx in match_idxs:
            if groups and idx <= groups[-1][-1] + CONTEXT * 2 + 1:
                groups[-1].append(idx)
            else:
                groups.append([idx])
        for grp in groups:
            if len(results) >= MAX_MATCHES:
                break
            start = max(0, grp[0] - CONTEXT)
            end = min(len(flines), grp[-1] + CONTEXT + 1)
            block = [f"{relpath}:"]
            for i in range(start, end):
                marker = ">>> " if i in grp else "    "
                block.append(f"{marker}{i + 1:>4}: {flines[i].rstrip()}")
            results.append("\n".join(block))

    if os.path.isfile(path):
        rel = os.path.relpath(path, project_root) if os.path.isabs(path) else path
        _search_file(path, rel)
    elif os.path.isdir(path):
        SKIP = {
            ".git",
            "__pycache__",
            "node_modules",
            ".gradle",
            "build",
            "dist",
            ".idea",
            "venv",
            ".venv",
        }
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in SKIP]
            for fname in files:
                if len(results) >= MAX_MATCHES:
                    break
                fp = os.path.join(root, fname)
                rel = os.path.relpath(fp, project_root)
                _search_file(fp, rel)
    else:
        return f"GREP: path not found: {path}"

    if not results:
        return f"GREP: no matches for '{pattern}' in {path}"

    return (
        f"GREP '{pattern}' — {len(results)} match(es) via Python fallback:\n\n"
        + "\n\n".join(results)
    )


def tool_view_image_impl(args: dict, project_root: str) -> str:
    """VIEW_IMAGE — inspect an image visually and attach to memory context."""
    path = args.get("path") or args.get("file") or args.get("image") or ""
    prompt = args.get("prompt") or args.get("query") or args.get("instruction") or ""
    return view_image(path=path, prompt=prompt, project_root=project_root)


def view_image(
    path: str = "", prompt: str = "", project_root: str = ".", **kwargs: Any
) -> str:
    """Inspect an image file, validate its structure, and attach to active memory."""
    path = str(path or "").strip()
    global _global_memory_mgr
    if not path and _global_memory_mgr is not None and getattr(_global_memory_mgr, "state", None):
        active_imgs = getattr(_global_memory_mgr.state, "active_images", [])
        if active_imgs:
            path = active_imgs[-1]

    if not path:
        return "VIEW_IMAGE requires a 'path' parameter specifying the image file."

    from core.utils.image_utils import (
        is_image_file,
        get_image_metadata,
        get_image_mime_type,
    )

    full_p = (
        os.path.abspath(os.path.join(project_root, path))
        if not os.path.isabs(path)
        else path
    )

    cwd_abs = os.path.abspath(project_root)
    cwd_prefix = cwd_abs if cwd_abs.endswith(os.sep) else cwd_abs + os.sep
    if not full_p.startswith(cwd_prefix) and full_p != cwd_abs:
        return f"Access denied: {path} is outside the workspace."

    if not os.path.exists(full_p):
        return f"File not found: {path}."

    if os.path.isdir(full_p):
        return f"{path} is a directory, not an image file."

    if not is_image_file(full_p):
        mime = get_image_mime_type(full_p)
        if not mime.startswith("image/"):
            return f"File '{path}' is not a recognized image format."

    meta = get_image_metadata(full_p, project_root=project_root)

    if _global_memory_mgr is not None and hasattr(_global_memory_mgr, "record_file_read"):
        try:
            _global_memory_mgr.record_file_read(path)
        except Exception:
            pass

    dim_info = (
        f"{meta['width']}x{meta['height']}"
        if meta.get("width") and meta.get("height")
        else "vector/dynamic"
    )
    prompt_str = f" Prompt: '{prompt}'" if prompt else ""
    return (
        f"[IMG] [VIEW_IMAGE] Successfully loaded '{path}' ({dim_info} {meta.get('format', 'IMAGE')}, {meta.get('size_kb', 0)} KB).{prompt_str}\n"
        f"Image content has been attached to context for visual inspection."
    )
