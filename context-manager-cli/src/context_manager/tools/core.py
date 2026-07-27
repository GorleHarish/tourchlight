"""
Core Tools — built-in, always available, called via TOOL_NAME("arg") syntax.

Risk levels (used by app.py for the approval UI):
  AUTO    — safe reads and searches, execute immediately without asking
  CONFIRM — writes and installs, show what will happen, one-click approve
  REVIEW  — destructive or irreversible operations, show full detail, explicit approve

This module re-exports from core/ when available, falling back to local implementations.
"""

# ── Import from core/ shared library ──────────────────────────────────────
try:
    from core.tools.classification import AUTO, CONFIRM, REVIEW, classify_command
    from core.tools.implementations import (
        tool_read_file as tool_read_file,
        tool_write_file as tool_write_file,
        tool_edit_file as tool_edit_file,
        tool_read_symbols as tool_read_symbols,
        tool_list_dir as tool_list_dir,
        tool_grep as tool_grep,
        tool_run_command as tool_run_command,
        tool_web_search as tool_web_search,
        tool_web_fetch as tool_web_fetch,
        tool_doc_search as tool_doc_search,
        tool_web_verify as tool_web_verify,
        tool_save_memory as tool_save_memory,
        tool_format_code as tool_format_code,
        tool_verify as tool_verify,
        tool_patch_file as tool_patch_file,
        tool_run_code as tool_run_code,
        tool_generate_diff as tool_generate_diff,
        _extract_symbols as _extract_symbols,
        _symbol_map as _symbol_map,
        _read_budget as _read_budget,
        _read_budget_for_ctx as _read_budget_for_ctx,
        set_ctx_window as set_ctx_window,
    )
    _USE_CORE = True
except ImportError:
    _USE_CORE = False

import os
import re
import subprocess
import httpx
import difflib
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


if not _USE_CORE:
    # ── Risk classification (local fallback) ─────────────────────────────────
    AUTO    = "auto"
    CONFIRM = "confirm"
    REVIEW  = "review"

    _SAFE_COMMANDS = {
        "ls", "la", "ll", "cat", "head", "tail", "echo", "pwd", "which",
        "find", "grep", "rg", "awk", "sed", "wc", "diff", "file",
        "python -m pytest", "pytest", "python -m mypy", "mypy",
        "python -m flake8", "flake8", "ruff check",
        "git status", "git log", "git diff", "git show", "git branch",
        "git stash list", "git remote", "git fetch",
        "npm test", "npm run test", "npx jest",
        "cargo test", "cargo check", "cargo clippy",
        "sysctl", "vm_stat", "top -l", "df", "diskutil list",
        "pip list", "pip show", "pip freeze",
        "cat package.json", "cat Cargo.toml", "cat pyproject.toml",
        "node --version", "python --version", "python3 --version",
    }

    _DESTRUCTIVE_PATTERNS = [
        r'\brm\s', r'\bgit\s+push\b', r'\bgit\s+reset\b', r'\bgit\s+rebase\b',
        r'\bgit\s+commit\b', r'\bgit\s+merge\b', r'\bgit\s+clean\b',
        r'\bdrop\s+table\b', r'\btruncate\s+table\b', r'\bchmod\b', r'\bchown\b',
        r'\bsudo\b', r'>\s*/', r'\bmkfs\b', r'\bdd\b', r'\bkill\b', r'\bpkill\b',
        r'\bshutdown\b', r'\breboot\b',
    ]
    _DESTRUCTIVE_RE = re.compile("|".join(_DESTRUCTIVE_PATTERNS), re.IGNORECASE)

    _CONFIRM_PATTERNS = [
        r'\bpip\s+install\b', r'\bpip3\s+install\b', r'\bnpm\s+install\b',
        r'\byarn\s+add\b', r'\bcargo\s+add\b', r'\bbrew\s+install\b',
        r'\bgit\s+add\b', r'\bgit\s+stash\b', r'\bgit\s+checkout\b',
        r'\bgit\s+switch\b', r'\bgit\s+restore\b', r'\bpython\s+.*\.py\b',
        r'\bnode\s+', r'\btouch\b', r'\bmkdir\b', r'\bcp\b', r'\bmv\b',
    ]
    _CONFIRM_RE = re.compile("|".join(_CONFIRM_PATTERNS), re.IGNORECASE)


    def classify_command(cmd: str) -> str:
        cmd_stripped = cmd.strip()
        if _DESTRUCTIVE_RE.search(cmd_stripped):
            return REVIEW
        for safe in _SAFE_COMMANDS:
            if cmd_stripped.startswith(safe) or cmd_stripped == safe:
                return AUTO
        if _CONFIRM_RE.search(cmd_stripped):
            return CONFIRM
        return CONFIRM


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class ToolResult:
    success: bool
    output:  str
    error:   Optional[str] = None


# ── Context-window budget ─────────────────────────────────────────────────────
#
# READ_FILE scales its output based on the model's context window so that a
# single file read never consumes more than ~20% of available tokens.
# Call set_ctx_window() once you know the model's n_ctx:
#
#   import context_manager.tools.core as _core_tools
#   _core_tools.set_ctx_window(8192)
#
#   4k  model → 60 lines  / 2 400 chars  (~600 tokens)
#   8k  model → 100 lines / 4 000 chars  (~1 000 tokens)
#   16k model → 150 lines / 6 000 chars  (~1 500 tokens)
#   32k+       → 250 lines / 10 000 chars (~2 500 tokens)

_CTX_WINDOW: int = 8000


def set_ctx_window(n: int) -> None:
    """Tell the tool layer what context window the current model has."""
    global _CTX_WINDOW
    _CTX_WINDOW = max(1024, int(n))


def _read_budget() -> tuple:
    """Return (MAX_LINES, MAX_CHARS) for the current context window."""
    w = _CTX_WINDOW
    if w <= 4096:  return 60,  2_400
    if w <= 8192:  return 100, 4_000
    if w <= 16384: return 150, 6_000
    return 250, 10_000


# ── Symbol extractor ──────────────────────────────────────────────────────────

_SYM_PATTERNS = [
    (re.compile(r'^(?:async )?def\s+(\w+)\s*\(', re.MULTILINE),  "fn"),
    (re.compile(r'^class\s+(\w+)[:(]', re.MULTILINE),            "class"),
    (re.compile(r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)', re.MULTILINE), "fn"),
    (re.compile(r'^(?:export\s+)?class\s+(\w+)', re.MULTILINE),  "class"),
    (re.compile(r'^\s*(?:pub\s+)?fn\s+(\w+)', re.MULTILINE),     "fn"),
    (re.compile(r'^\s*(?:fun)\s+(\w+)\s*\(', re.MULTILINE),      "fn"),
]


def _extract_symbols(content: str, max_symbols: int = 40) -> list:
    """Return [(lineno_1based, kind, name), ...] sorted by line number."""
    found = []
    seen = set()
    for pattern, kind in _SYM_PATTERNS:
        for m in pattern.finditer(content):
            name = m.group(1)
            if name in seen:
                continue
            lineno = content[:m.start()].count("\n") + 1
            found.append((lineno, kind, name))
            seen.add(name)
    found.sort(key=lambda x: x[0])
    return found[:max_symbols]


def _symbol_map(content: str, filename: str) -> str:
    """Compact symbol map prepended to READ_FILE output."""
    syms = _extract_symbols(content)
    if not syms:
        return ""
    lines = ["📐 Symbols:"]
    for lineno, kind, name in syms:
        lines.append(f"  L{lineno:>4}  {kind:<6} {name}")
    lines.append("")
    return "\n".join(lines)


# ── Documentation source registry ─────────────────────────────────────────────

_DOC_SOURCES: list = [
    (r'\bpython\b|\bpytest\b|\basyncio\b|\btyping\b|\bpathlib\b|\bdataclass\b',
     "https://docs.python.org/3/search.html?q=%s", "docs.python.org"),
    (r'\bfastapi\b', "https://fastapi.tiangolo.com/search/?q=%s", "fastapi.tiangolo.com"),
    (r'\bpydantic\b', "https://docs.pydantic.dev/latest/search/?q=%s", "docs.pydantic.dev"),
    (r'\bsqlalchemy\b', "https://docs.sqlalchemy.org/en/20/search.html?q=%s", "docs.sqlalchemy.org"),
    (r'\bhttpx\b', "https://www.python-httpx.org/search/?q=%s", "python-httpx.org"),
    (r'\brich\b', "https://rich.readthedocs.io/en/stable/search.html?q=%s", "rich.readthedocs.io"),
    (r'\bnode(js)?\b|\bnpm\b|\bjavascript\b|\btypescript\b|\bexpress\b',
     "https://nodejs.org/en/search/?query=%s", "nodejs.org"),
    (r'\bmdn\b|\bjavascript\b|\bcss\b|\bhtml\b|\bfetch\b|\bpromise\b',
     "https://developer.mozilla.org/en-US/search?q=%s", "developer.mozilla.org"),
    (r'\brust\b|\bcargo\b|\bcrates?\b|\btokio\b|\bserde\b',
     "https://doc.rust-lang.org/std/?search=%s", "doc.rust-lang.org"),
    (r'\bgolang\b|\bgo\b', "https://pkg.go.dev/search?q=%s", "pkg.go.dev"),
    (r'\bdocker\b|\bdocker-compose\b', "https://docs.docker.com/search/?q=%s", "docs.docker.com"),
    (r'\bgithub\s+actions?\b|\bworkflow\b',
     "https://docs.github.com/en/search?query=%s", "docs.github.com"),
]


def _detect_doc_source(query: str) -> tuple:
    import urllib.parse
    lower   = query.lower()
    encoded = urllib.parse.quote_plus(query)
    for pattern, url_tpl, label in _DOC_SOURCES:
        if re.search(pattern, lower):
            return url_tpl % encoded, label
    return (
        f"https://html.duckduckgo.com/html/?q={encoded}+documentation+syntax",
        "duckduckgo (docs)",
    )


# ── Individual tool implementations ───────────────────────────────────────────

def tool_read_file(path: str, cwd: str = ".") -> str:
    """
    READ_FILE — read a file with optional line-range or symbol syntax.

    Formats:
        READ_FILE("app.py")             plain read (up to budget lines)
        READ_FILE("app.py:40-90")       lines 40-90, 1-based inclusive
        READ_FILE("app.py:MyClass")     jump directly to a named symbol

    A compact symbol map is always prepended so the model can see all
    function/class names and their line numbers without reading the full file.
    """
    try:
        path = (path or "").strip()
        if not path:
            return "📁 READ_FILE requires a file path. Use RUN_COMMAND('ls') to see directory contents."

        # Parse optional :N-M or :SymbolName suffix
        range_start: Optional[int] = None
        range_end:   Optional[int] = None
        symbol_name: Optional[str] = None

        # Robust regex: allows optional spaces around colon and at start/end
        m_range = re.match(r'^(.+?)\s*:\s*(\d+)-(\d+)\s*$', path)
        m_line  = re.match(r'^(.+?)\s*:\s*(\d+)\s*$', path) # Single line: path:N
        m_sym   = re.match(r'^(.+?)\s*:\s*([A-Za-z_]\w*)\s*$', path)

        if m_range:
            path, range_start, range_end = (
                m_range.group(1).strip(),
                int(m_range.group(2)),
                int(m_range.group(3)),
            )
        elif m_line:
            path, range_start = m_line.group(1).strip(), int(m_line.group(2))
            range_end = range_start
        elif m_sym:
            path, symbol_name = m_sym.group(1).strip(), m_sym.group(2)

        # ── Path resolution ───────────────────────────────────────────────────
        p = os.path.abspath(os.path.join(cwd, path))
        
        # Security: ensure path is within cwd or its subdirectories
        cwd_abs = os.path.abspath(cwd)
        # Add a trailing separator to prevent prefix collision attacks 
        # (e.g., /project vs /project-secrets)
        cwd_prefix = cwd_abs if cwd_abs.endswith(os.sep) else cwd_abs + os.sep
        
        if not p.startswith(cwd_prefix) and p != cwd_abs:
            # Allow absolute paths ONLY if they are inside the workspace
            return f"❌ Access denied: {path} is outside the workspace."

        if not os.path.exists(p):
            # Heuristic: if path contains a colon and doesn't exist, but prefix DOES exist, 
            # it's likely a malformed syntax call.
            if ":" in path:
                base_path = path.split(":")[0]
                if os.path.exists(os.path.join(cwd, base_path)):
                    return (
                        f"❌ Syntax error in READ_FILE: '{path}'\n"
                        f"The suffix after ':' was not recognized as a LINE, RANGE (N-M), or SYMBOL.\n"
                        f"Valid formats: '{base_path}:10-20', '{base_path}:15', or '{base_path}:ClassOrFunc'."
                    )
            
            # Suggest current files if not found
            files_hint = ""
            try:
                # Get up to 5 files in current directory as a hint
                local_files = [f for f in os.listdir(cwd) if os.path.isfile(os.path.join(cwd, f))][:5]
                if local_files:
                    files_hint = f"\nFiles in current directory: {', '.join(local_files)}"
            except Exception:
                pass
                
            return f"❌ File not found: {path}.{files_hint}\nUse RUN_COMMAND('ls -R') to verify the correct path."
        if os.path.isdir(p):
            return f"❌ {path} is a directory. Use RUN_COMMAND('ls {path}') to list it."

        # ── Image file rejection ───────────────────────────────────────────────
        # Explicit rejection of image files since local models often don't support vision
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg", ".tiff"}
        ext = os.path.splitext(p)[1].lower()
        if ext in image_extensions:
            return f"❌ Cannot read image file: {os.path.basename(p)}. This is an image and cannot be read as text."

        # ── Binary detection ──────────────────────────────────────────────────
        # Check file size first - reject very large files to prevent memory issues
        # Adaptive limit based on available RAM
        file_size = os.path.getsize(p)
        # Auto-detect available RAM and set limit accordingly
        # 8GB: 500KB, 16GB: 1MB, 24GB+: 2MB
        try:
            import psutil
            available_ram_gb = psutil.virtual_memory().available / (1024**3)
        except ImportError:
            available_ram_gb = 8  # Default conservative limit
        if available_ram_gb <= 10:
            max_file_size = 500_000    # 500KB for <=10GB
        elif available_ram_gb <= 20:
            max_file_size = 1_000_000  # 1MB for <=20GB
        else:
            max_file_size = 2_000_000  # 2MB for >20GB
        
        if file_size > max_file_size:
            return f"📄 {os.path.basename(p)} ({file_size:,} bytes) — [FILE TOO LARGE, max {max_file_size//1024}KB]. Use RUN_COMMAND('head -n 100 {path}') for a preview."
        
        # Read the first 1kb to check for null bytes
        with open(p, "rb") as bf:
            chunk = bf.read(1024)
            if b"\x00" in chunk:
                return f"📄 {os.path.basename(p)} ({file_size:,} bytes) — [BINARY FILE, content omitted]"

        # ── Read with encoding fallback ───────────────────────────────────────
        try:
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                # Fallback to latin-1 (always succeeds for byte-oriented data)
                with open(p, "r", encoding="latin-1") as f:
                    content = f.read()
            except Exception as e:
                return f"❌ Error reading file: {e}"

        lines  = content.splitlines()
        nlines = len(lines)
        ext    = os.path.splitext(p)[1].lstrip(".")
        fname  = os.path.basename(p)
        MAX_LINES, MAX_CHARS = _read_budget()

        # ── Symbol lookup: find the named symbol and its line range ───────────
        if symbol_name:
            syms   = _extract_symbols(content)
            target = next((s for s in syms if s[2] == symbol_name), None)
            if target:
                range_start = target[0]
                next_sym    = next((s for s in syms if s[0] > range_start), None)
                range_end   = (next_sym[0] - 1) if next_sym else nlines
            else:
                return (
                    f"⚠️ Symbol '{symbol_name}' not found in {fname}.\n"
                    f"{_symbol_map(content, fname)}"
                    f'Use READ_FILE("{path}:<NAME>") with a name from the list above.'
                )

        # ── Line-range slice ──────────────────────────────────────────────────
        if range_start is not None:
            r0 = max(0, range_start - 1)          # 0-based start
            r1 = min(nlines, range_end or nlines)  # 0-based exclusive end
            sl = lines[r0:r1]
            if len(sl) > MAX_LINES:
                sl        = sl[:MAX_LINES]
                trunc_note = f"\n... (capped at {MAX_LINES} lines — use a tighter range)"
            else:
                trunc_note = ""
            display = "\n".join(sl)[:MAX_CHARS]
            return (
                f"📄 {fname} lines {r0+1}–{r0+len(sl)} (of {nlines} total)\n"
                f"```{ext}\n{display}{trunc_note}\n```"
            )

        # ── Default: symbol map + top-N lines ─────────────────────────────────
        sym_hdr   = _symbol_map(content, fname)
        display   = "\n".join(lines[:MAX_LINES])[:MAX_CHARS]
        truncated = nlines > MAX_LINES or len(content) > MAX_CHARS
        suffix = (
            f"\n... ({nlines - MAX_LINES} more lines)"
            f' — use READ_FILE("{path}:N-M") for a range,'
            f' READ_FILE("{path}:N") for one line,'
            f' or READ_FILE("{path}:<SYMBOL>") to jump to a function.'
        ) if truncated else ""

        return (
            f"{sym_hdr}"
            f"📄 {fname} ({nlines} lines)\n"
            f"```{ext}\n{display}{suffix}\n```"
        )

    except Exception as e:
        return f"❌ Error reading file: {e}"


def tool_grep(pattern: str, path: str = ".", cwd: str = ".") -> str:
    """
    GREP — fast targeted search inside a file or directory.

    Returns only the matching lines with 2 lines of context.  Output is
    always compact regardless of file size — use this BEFORE READ_FILE
    to locate the exact lines you need without loading the whole file.

    Examples:
        GREP("def handle_error", "src/")
        GREP("NullPointerException", "crash.log")
        GREP("TODO", ".")
    """
    try:
        p = os.path.join(cwd, path) if not os.path.isabs(path) else path
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            regex = re.compile(re.escape(pattern), re.IGNORECASE)

        MAX_MATCHES = 20
        CONTEXT     = 2
        results: list = []

        def _search_file(filepath: str, relpath: str) -> None:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    flines = f.readlines()
            except OSError:
                return
            match_idxs = [i for i, ln in enumerate(flines) if regex.search(ln)]
            if not match_idxs:
                return
            # Group nearby hits to avoid duplicated context blocks
            groups: list = []
            for idx in match_idxs:
                if groups and idx <= groups[-1][-1] + CONTEXT * 2 + 1:
                    groups[-1].append(idx)
                else:
                    groups.append([idx])
            for grp in groups:
                if len(results) >= MAX_MATCHES:
                    break
                start = max(0, grp[0] - CONTEXT)
                end   = min(len(flines), grp[-1] + CONTEXT + 1)
                block = [f"{relpath}:"]
                for i in range(start, end):
                    marker = ">>> " if i in grp else "    "
                    block.append(f"{marker}{i+1:>4}: {flines[i].rstrip()}")
                results.append("\n".join(block))

        if os.path.isfile(p):
            _search_file(p, os.path.basename(p))
        elif os.path.isdir(p):
            SKIP = {".git", "__pycache__", "node_modules", ".gradle",
                    "build", "dist", ".idea", "venv", ".venv"}
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP]
                for fname in files:
                    if len(results) >= MAX_MATCHES:
                        break
                    fp  = os.path.join(root, fname)
                    rel = os.path.relpath(fp, cwd)
                    _search_file(fp, rel)
        else:
            return f"❌ GREP: path not found: {path}"

        if not results:
            return f"GREP: no matches for '{pattern}' in {path}"

        return (
            f"🔎 GREP '{pattern}' in {path} — {len(results)} match(es):\n\n"
            + "\n\n".join(results)
        )
    except Exception as e:
        return f"❌ GREP error: {e}"


def tool_read_symbols(path: str, cwd: str = ".") -> str:
    """
    READ_SYMBOLS — show the structure of a file without loading its content.

    Returns every function/class name with its line number.  Use this first
    on large files to orient yourself, then use READ_FILE("path:SymbolName")
    to read only the symbol you actually need.
    """
    try:
        # Handle empty path - list directory contents
        if not path or path.strip() == "":
            return "📁 READ_SYMBOLS requires a file path. Use RUN_COMMAND('ls') to see directory contents."
        
        p = os.path.join(cwd, path) if not os.path.isabs(path) else path
        
        # Security: ensure path is within cwd
        cwd_abs = os.path.abspath(cwd)
        cwd_prefix = cwd_abs if cwd_abs.endswith(os.sep) else cwd_abs + os.sep
        if not os.path.abspath(p).startswith(cwd_prefix) and os.path.abspath(p) != cwd_abs:
            return f"❌ Access denied: {path} is outside the workspace."
        
        if not os.path.exists(p):
            return f"❌ File not found: {path}"
        if os.path.isdir(p):
            return f"❌ {path} is a directory. Use RUN_COMMAND('ls {path}') to list it."
        
        try:
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(p, "r", encoding="latin-1") as f:
                content = f.read()
        except Exception as e:
            return f"❌ Error reading symbols from {path}: {e}"
        nlines = content.count("\n") + 1
        fname  = os.path.basename(p)
        syms   = _extract_symbols(content, max_symbols=60)
        if not syms:
            return f"📄 {fname} ({nlines} lines) — no symbols detected."
        lines = [f"📄 {fname} ({nlines} lines) — {len(syms)} symbol(s):"]
        for lineno, kind, name in syms:
            lines.append(f"  L{lineno:>4}  {kind:<6} {name}")
        lines.append("")
        lines.append(f'READ_FILE("{path}:<SYMBOL>") — read one symbol')
        lines.append(f'READ_FILE("{path}:N-M")      — read lines N through M')
        lines.append(f'READ_FILE("{path}:N")        — read line N')
        return "\n".join(lines)
    except Exception as e:
        return f"❌ READ_SYMBOLS error: {e}"


def tool_edit_file(path: str, old_text: str, new_text: str, cwd: str = ".") -> str:
    """
    EDIT_FILE — surgically replace a block of text in a file with multi-tiered resilient matching.
    Always provide enough context in 'old_text' to make the match unique.
    """
    try:
        p = os.path.join(cwd, path) if not os.path.isabs(path) else path
        if not os.path.exists(p):
            return f"❌ File not found: {path}"
        
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Handle unescaped literal \\n and \\t from raw JSON outputs
        if "\\n" in old_text and "\n" not in old_text:
            old_text = old_text.replace("\\n", "\n").replace("\\t", "\t")
        if "\\n" in new_text and "\n" not in new_text:
            new_text = new_text.replace("\\n", "\n").replace("\\t", "\t")

        # Tier 1: Exact string match
        if old_text in content:
            count = content.count(old_text)
            if count > 1:
                return f"❌ Edit failed: 'old_text' matches {count} locations. Provide more context to make it unique."
            new_content = content.replace(old_text, new_text)
            with open(p, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"✅ Surgically edited {path} (replaced {len(old_text)} chars with {len(new_text)} chars)."

        content_lines = content.splitlines(keepends=True)

        # Tier 2: Fuzzy whitespace-agnostic line matching
        def normalize_line(line):
            return line.strip()

        old_norm = [normalize_line(line) for line in old_text.splitlines() if normalize_line(line)]
        if not old_norm:
            return "❌ Edit failed: 'old_text' is empty or contains only whitespace."

        best_start = -1
        best_end = -1
        matches_found = 0

        for i in range(len(content_lines)):
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
                    break

            if match_count == len(old_norm):
                matches_found += 1
                best_start = i
                best_end = j

        if matches_found > 1:
            return f"❌ Edit failed: 'old_text' fuzzy-matches {matches_found} locations. Provide more context."

        if best_start != -1:
            new_content = "".join(content_lines[:best_start]) + new_text
            if new_text and not new_text.endswith("\n") and best_end < len(content_lines):
                new_content += "\n"
            new_content += "".join(content_lines[best_end:])
            with open(p, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"✅ Surgically edited {path} (fuzzy replaced {len(old_norm)} lines ignoring whitespace)."

        # Tier 3: Difflib similarity ratio matching (>= 60% similarity)
        best_ratio = 0.0
        best_diff_start = -1
        best_diff_end = -1
        window_size = len(old_norm)

        for w_size in range(max(1, window_size - 3), window_size + 4):
            for i in range(len(content_lines) - w_size + 1):
                block = "".join(content_lines[i:i + w_size])
                ratio = difflib.SequenceMatcher(None, block, old_text).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_diff_start = i
                    best_diff_end = i + w_size

        if best_ratio >= 0.60 and best_diff_start != -1:
            new_content = "".join(content_lines[:best_diff_start]) + new_text
            if new_text and not new_text.endswith("\n") and best_diff_end < len(content_lines):
                new_content += "\n"
            new_content += "".join(content_lines[best_diff_end:])
            with open(p, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"✅ Surgically edited {path} (similarity replaced block with {int(best_ratio*100)}% match at lines {best_diff_start+1}-{best_diff_end})."

        # All tiers failed — provide closest match as diagnostic
        closest_block = ""
        closest_ratio = 0.0
        closest_line = 0
        for i in range(max(1, len(content_lines) - 20)):
            block = "".join(content_lines[i:min(i+8, len(content_lines))])
            ratio = difflib.SequenceMatcher(None, block, old_text).ratio()
            if ratio > closest_ratio:
                closest_ratio = ratio
                closest_block = block
                closest_line = i + 1

        hint = ""
        if closest_ratio > 0.3:
            snippet = closest_block.strip()[:200]
            hint = (
                f"\nClosest match found ({int(closest_ratio*100)}% similar, line {closest_line}):\n"
                f"```\n{snippet}\n```\n"
                f"Use this as your old_text (copy it exactly) and retry."
            )

        return (
            f"❌ Edit failed: Could not find a matching block for 'old_text' in {path}.\n"
            f"HINT: You MUST read the file first with READ_FILE('{path}') to get the exact text, "
            f"then copy the relevant lines exactly as they appear.{hint}"
        )
    except Exception as e:
        return f"❌ Error editing file: {e}"


def tool_patch_file(path: str, diff: str, preview: bool = True, cwd: str = ".") -> str:
    """
    PATCH_FILE — apply a unified diff to a file.
    If preview=True, returns the result of the diff without writing.
    """
    try:
        p = os.path.join(cwd, path) if not os.path.isabs(path) else path
        if not os.path.exists(p):
            return f"❌ File not found: {path}"
        
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        
        if preview:
            # Return the diff that WOULD be applied
            # (In this case, the input diff is already what would be applied)
            return f"🔍 PREVIEW: Patch for {path}\n```diff\n{diff}\n```"

        # APPLY: Use the 'patch' CLI tool
        patch_cmd = f"patch {p}"
        proc = subprocess.Popen(patch_cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate(input=diff)
        
        if proc.returncode == 0:
            return f"✅ Patched {path} successfully."
        else:
            return f"❌ Patch failed:\n{stderr or stdout}"

    except Exception as e:
        return f"❌ Error patching file: {e}"


def tool_write_file(path: str, content: str, preview: bool = False, cwd: str = ".") -> str:
    try:
        p = os.path.join(cwd, path) if not os.path.isabs(path) else path
        
        if preview:
            # Generate a diff if the file exists
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    old_content = f.read()
                diff = difflib.unified_diff(
                    old_content.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}"
                )
                diff_text = "".join(diff)
                if not diff_text:
                    return f"ℹ️ No changes detected for {path}"
                return f"🔍 PREVIEW: Write to {path}\n```diff\n{diff_text}\n```"
            else:
                return f"🔍 PREVIEW: Create new file {path}\n```\n{content[:1000]}\n```"

        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Written {len(content):,} chars to {p}"
    except Exception as e:
        return f"❌ Error writing file: {e}"


def tool_generate_diff(old: str, new: str, path: str = "file") -> str:
    """Helper to build unified diffs."""
    diff = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}"
    )
    return "".join(diff)


def tool_format_code(snippet: str, language: str = "python") -> str:
    """Beautify code snippets."""
    if language.lower() in ("python", "py"):
        try:
            import black
            return black.format_str(snippet, mode=black.Mode())
        except ImportError:
            return f"ℹ️ 'black' not installed. Returning raw snippet:\n{snippet}"
    # Add other formatters here
    return snippet


def tool_run_code(snippet: str, language: str = "python") -> str:
    """Run a small, sandboxed snippet."""
    if language.lower() in ("python", "py"):
        try:
            # Extremely minimal 'sandbox' - just for demo
            # In production, use a dedicated executor
            local_vars = {}
            exec(snippet, {"__builtins__": __builtins__}, local_vars)
            return f"✅ Snippet executed. Locals: {local_vars}"
        except Exception as e:
            return f"❌ Execution error: {e}"
    return f"❌ Running {language} snippets not yet supported."


def tool_run_command(cmd: str, cwd: str = ".") -> str:
    _LONG_CMDS = ("pip install", "pip3 install", "npm install", "yarn", "cargo build",
                  "gradle", "./gradlew", "mvn ", "make ", "cmake")
    timeout = 180 if any(cmd.strip().startswith(c) for c in _LONG_CMDS) else 60
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=timeout,
        )
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if out and err:
            output = f"{out}\n--- stderr ---\n{err}"
        else:
            output = out or err or "(no output)"
        if "undefined" in output:
            output = "\n".join(
                l for l in output.splitlines() if l.strip() and l.strip() != "undefined"
            )
        if r.returncode == 127 and any(c in cmd for c in ("lscpu", "free ", "lsblk")):
            try:
                fb = subprocess.run(
                    ["sysctl", "-n", "hw.model", "hw.ncpu", "hw.memsize"],
                    capture_output=True, text=True, timeout=5,
                )
                if fb.returncode == 0:
                    return f"ℹ️ Linux-only command. macOS equivalent:\n```\n{fb.stdout.strip()}\n```"
            except Exception:
                pass
        status = "✅" if r.returncode == 0 else f"⚠️ Exit {r.returncode}"
        return f"{status}\n```\n{output[:3000]}\n```"
    except subprocess.TimeoutExpired:
        return f"⏰ Command timed out ({timeout}s). For long installs use a background process."
    except Exception as e:
        return f"❌ Error: {e}"


def _ddg_search(q: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    resp = httpx.post(
        "https://html.duckduckgo.com/html/", data={"q": q, "kl": "us-en"},
        headers=headers, timeout=15, follow_redirects=True,
    )
    resp.raise_for_status()
    def strip_tags(s): return re.sub(r"<[^>]+>", "", s).strip()
    raw      = resp.text
    titles   = [strip_tags(t) for t in re.findall(r'class="result__a"[^>]*>(.*?)</a>', raw, re.DOTALL)]
    urls_raw = [strip_tags(u).strip() for u in re.findall(r'class="result__url"[^>]*>(.*?)</div>', raw, re.DOTALL)]
    snippets = [strip_tags(s) for s in re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', raw, re.DOTALL)]
    if not titles:
        return "No results found."
    out = "🔍 Search Results (DuckDuckGo):\n\n"
    for i, title in enumerate(titles[:5]):
        url  = urls_raw[i] if i < len(urls_raw) else ""
        snip = snippets[i] if i < len(snippets) else ""
        if url and not url.startswith("http"):
            url = "https://" + url
        out += f"**{title}**\n  {url}\n  {snip}\n\n"
    return out.strip()


def tool_web_search(query: str) -> str:
    try:
        if brave_key := os.getenv("BRAVE_API_KEY"):
            r = httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"Accept": "application/json", "X-Subscription-Token": brave_key},
                params={"q": query, "count": 5}, timeout=15,
            )
            r.raise_for_status()
            results = r.json().get("web", {}).get("results", [])
            if results:
                out = "🔍 Search Results (Brave):\n\n"
                for res in results:
                    out += f"**{res.get('title','?')}**\n  {res.get('url','')}\n  {res.get('description','')}\n\n"
                return out.strip()
        if serpapi_key := os.getenv("SERPAPI_KEY"):
            r = httpx.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": serpapi_key, "num": 5}, timeout=15,
            )
            r.raise_for_status()
            results = r.json().get("organic_results", [])
            if results:
                out = "🔍 Search Results (SerpAPI):\n\n"
                for res in results:
                    out += f"**{res.get('title','?')}**\n  {res.get('link','')}\n  {res.get('snippet','')}\n\n"
                return out.strip()
        return _ddg_search(query)
    except Exception as e:
        try:
            return _ddg_search(query)
        except Exception:
            return f"❌ Search error: {e}"


def tool_web_fetch(url: str) -> str:
    try:
        if not url.startswith("http"):
            url = "https://" + url
        try:
            r = httpx.get(
                f"https://r.jina.ai/{url}", headers={"Accept": "text/plain"},
                timeout=20, follow_redirects=True,
            )
            if r.status_code == 200 and r.text.strip():
                return f"🌐 {url}:\n{r.text.strip()[:4000]}"
        except Exception:
            pass
        r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20, follow_redirects=True)
        r.raise_for_status()
        clean = re.sub(r"\s{2,}", " ", re.sub(r"<[^>]+>", " ", r.text)).strip()
        return f"🌐 {url}:\n{clean[:3000]}"
    except Exception as e:
        return f"❌ Fetch error: {e}"


def tool_doc_search(query: str) -> str:
    import urllib.parse
    search_url, label = _detect_doc_source(query)
    if "duckduckgo" not in label:
        domain = re.search(r'https?://([^/]+)', search_url)
        ddg_query = f"site:{domain.group(1)} {query}" if domain else query
    else:
        ddg_query = query + " documentation syntax"
    try:
        raw_results = _ddg_search(ddg_query)
    except Exception as e:
        raw_results = f"Search unavailable: {e}"
    first_url = None
    for line in raw_results.splitlines():
        line = line.strip()
        if line.startswith("https://") or line.startswith("http://"):
            first_url = line
            break
    fetch_snippet = ""
    if first_url:
        try:
            r = httpx.get(
                f"https://r.jina.ai/{first_url}",
                headers={"Accept": "text/plain"}, timeout=15, follow_redirects=True,
            )
            if r.status_code == 200:
                fetch_snippet = f"\n📄 Doc excerpt ({first_url}):\n{r.text.strip()[:1200]}"
        except Exception:
            pass
    return f"📚 DOC_SEARCH — source: {label}\n{'─' * 40}\n" + raw_results + fetch_snippet


def tool_web_verify(snippet: str, language: str = "python") -> str:
    identifiers = _extract_identifiers(snippet, language)
    if not identifiers:
        return "⚠️ WEB_VERIFY: no identifiers found in snippet."
    results = [
        f"✔ WEB_VERIFY — language: {language}",
        f"  Snippet: {snippet[:120]}",
        f"  Checking: {', '.join(identifiers[:6])}",
        "─" * 40,
    ]
    for ident in identifiers[:4]:
        query      = f"{ident} {language} syntax documentation"
        search_url, label = _detect_doc_source(query)
        domain_m   = re.search(r'https?://([^/]+)', search_url)
        ddg_q      = (f"site:{domain_m.group(1)} {ident}"
                      if "duckduckgo" not in label and domain_m
                      else f"{ident} {language} documentation")
        status = "UNKNOWN"
        doc_url = ""
        try:
            raw = _ddg_search(ddg_q)
            if ident.lower() in raw.lower():
                status = "VERIFIED ✓"
                for line in raw.splitlines():
                    line = line.strip()
                    if line.startswith("http"):
                        doc_url = line
                        break
            else:
                status = "NOT FOUND IN DOCS ✗"
        except Exception as exc:
            status = f"SEARCH ERROR ({exc})"
        results.append(f"  {ident:<40} {status}")
        if doc_url:
            results.append(f"  → {doc_url}")
    results += ["─" * 40,
                "VERIFIED = identifier appeared in docs search results.",
                "Always read the full doc page before relying on this."]
    return "\n".join(results)


def _extract_identifiers(snippet: str, language: str) -> list:
    if language in ("python", "py"):
        calls      = re.findall(r'([\w]+(?:\.[\w]+)+)\s*\(', snippet)
        standalone = re.findall(r'\b([A-Z][\w]+|[a-z][\w_]{3,})\s*\(', snippet)
        identifiers = list(dict.fromkeys(calls + standalone))
    elif language in ("javascript", "typescript", "js", "ts"):
        identifiers = list(dict.fromkeys(re.findall(r'([\w]+(?:\.[\w]+)+)\s*\(', snippet)))
    elif language in ("rust", "rs"):
        identifiers = list(dict.fromkeys(re.findall(r'([\w:]+(?:::[\w]+)+)\s*[!\(]', snippet)))
    elif language in ("go",):
        identifiers = list(dict.fromkeys(re.findall(r'([\w]+\.[\w]+)\s*\(', snippet)))
    else:
        identifiers = list(dict.fromkeys(re.findall(r'([\w]+(?:[.:][\w]+)+)\s*[\(!\[]?', snippet)))
    return [i for i in identifiers if len(i) > 3 and not i.startswith("_")][:8]


def tool_save_memory(fact: str, category: str = "fact", cwd: str = ".",
                     lm_url: Optional[str] = None, model: Optional[str] = None) -> str:
    if not lm_url:
        lm_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
    from pathlib import Path
    from ..memory.persistence import ProjectMemory
    if not fact or not fact.strip():
        return "❌ No fact provided."
    fact = fact.strip()
    if len(fact) > 300:
        return "❌ Fact too long — keep under 300 chars."
    embedding: list = []
    embed_note = ""
    try:
        from ..api.lmstudio import LMStudioClient
        from ..memory.embeddings import build_embedder
        client = LMStudioClient(lm_url, model)
        embedding = build_embedder("hybrid", "auto", client).embed_sync(fact)
    except Exception:
        embed_note = " (no embedding — stored as plain text)"
    try:
        pm  = ProjectMemory(Path(cwd))
        cat = category.lower()
        mem = pm.load()
        if "arch" in cat or "decision" in cat:
            if fact not in mem.get("arch_decisions", []):
                mem.setdefault("arch_decisions", []).append(fact)
            pm.save(mem)
        elif "fail" in cat or "tried" in cat:
            if fact not in mem.get("tried_and_failed", []):
                mem.setdefault("tried_and_failed", []).append(fact)
            pm.save(mem)
        elif "tech" in cat or "stack" in cat:
            pm.update_tech_stack([fact])
        else:
            pm.update(fact, embedding if embedding else None)
        return f"✅ Saved to project memory ({cat}){embed_note}: '{fact[:100]}'"
    except Exception as e:
        return f"❌ Failed to write memory file: {e}"


def tool_verify(path: str, expected_snippet: Optional[str] = None, cwd: str = ".") -> str:
    try:
        p = os.path.join(cwd, path) if not os.path.isabs(path) else path
        if not os.path.exists(p):
            return f"❌ Verification FAILED: File does not exist at {path}"
        if expected_snippet:
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
            if expected_snippet in content:
                return f"✅ Verification SUCCESS: Found expected content in {path}"
            else:
                return f"⚠️ Verification WARNING: File exists but expected snippet was NOT found in {path}"
        return f"✅ Verification SUCCESS: File exists at {path}"
    except Exception as e:
        return f"❌ Verification ERROR: {e}"


# ── Registry ──────────────────────────────────────────────────────────────────

@dataclass
class CoreTool:
    name:        str
    icon:        str
    description: str
    risk_level:  str
    fn:          Callable

    @property
    def is_dangerous(self) -> bool:
        return self.risk_level != AUTO


class CoreToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, CoreTool] = {}

    def register(self, tool: CoreTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[CoreTool]:
        return self._tools.get(name)

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def all(self) -> List[CoreTool]:
        return list(self._tools.values())

    def icons(self) -> Dict[str, str]:
        return {t.name: t.icon for t in self._tools.values()}

    def dangerous_tools(self) -> List[str]:
        return [t.name for t in self._tools.values() if t.risk_level != AUTO]

    def risk_level_for(self, name: str, args=None) -> str:
        tool = self._tools.get(name)
        if not tool:
            return CONFIRM
        if name == "RUN_COMMAND" and args:
            if isinstance(args, dict):
                cmd = args.get("cmd", args.get("arg", ""))
            else:
                cmd = args[0] if args else ""
            return classify_command(cmd)
        return tool.risk_level

    def execute(self, name: str, args: List[str], cwd: str = ".") -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"❌ Unknown tool: {name}"
        try:
            return tool.fn(args, cwd)
        except Exception as e:
            return f"❌ {name} error: {e}"


def get_core_registry() -> CoreToolRegistry:
    registry = CoreToolRegistry()

    registry.register(CoreTool(
        name="READ_FILE", icon="📖",
        description=(
            "Read a file. Args: path (required). "
            "Formats: {\"path\": \"file.py\"} for first N lines, "
            "{\"path\": \"file.py:10-50\"} for a line range, "
            "{\"path\": \"file.py:ClassName\"} to jump to a function/class. "
            "Always shows a symbol map so you know what line each function is on."
        ),
        risk_level=AUTO,
        fn=lambda args, cwd: tool_read_file(args[0] if args else "", cwd),
    ))
    registry.register(CoreTool(
        name="GREP", icon="🔎",
        description=(
            "Search for a pattern in a file or directory. Returns only matching "
            "lines with 2 lines of context. Use BEFORE READ_FILE to find the exact "
            "lines you need without loading the whole file. "
            "Args: pattern (required), path (optional, default \".\")."
        ),
        risk_level=AUTO,
        fn=lambda args, cwd: tool_grep(
            args[0] if args else "",
            args[1] if len(args) > 1 else ".",
            cwd,
        ),
    ))
    registry.register(CoreTool(
        name="READ_SYMBOLS", icon="📐",
        description=(
            "Show the structure of a file (all functions/classes with line numbers) "
            "without loading file content. Use on large files to orient yourself before "
            "deciding which symbol to READ_FILE. Very cheap — never fills context."
        ),
        risk_level=AUTO,
        fn=lambda args, cwd: tool_read_symbols(args[0] if args else "", cwd),
    ))
    registry.register(CoreTool(
        name="WRITE_FILE", icon="💾",
        description=(
            "Create or overwrite a file. "
            "Args: path (required, the file path), content (required, the FULL file text). "
            "Always provide the complete file content — do not use code fences."
        ),
        risk_level=CONFIRM,
        fn=lambda args, cwd: tool_write_file(
            args[0] if args else "",
            args[1] if len(args) > 1 else "",
            args[2] if len(args) > 2 else False,
            cwd,
        ),
    ))
    registry.register(CoreTool(
        name="PATCH_FILE", icon="🩹",
        description="Apply a unified diff to a file. Use preview=True to see the diff first.",
        risk_level=CONFIRM,
        fn=lambda args, cwd: tool_patch_file(
            args[0] if args else "",
            args[1] if len(args) > 1 else "",
            args[2] if len(args) > 2 else True,
            cwd,
        ),
    ))
    registry.register(CoreTool(
        name="RUN_CODE", icon="📄",
        description="Run a short, sandboxed code snippet.",
        risk_level=CONFIRM,
        fn=lambda args, cwd: tool_run_code(
            args[0] if args else "",
            args[1] if len(args) > 1 else "python",
        ),
    ))
    registry.register(CoreTool(
        name="FORMAT_CODE", icon="🧹",
        description="Beautify a code snippet.",
        risk_level=AUTO,
        fn=lambda args, cwd: tool_format_code(
            args[0] if args else "",
            args[1] if len(args) > 1 else "python",
        ),
    ))
    registry.register(CoreTool(
        name="GENERATE_DIFF", icon="🔀",
        description="Helper to build unified diffs from old/new strings.",
        risk_level=AUTO,
        fn=lambda args, cwd: tool_generate_diff(
            args[0] if args else "",
            args[1] if len(args) > 1 else "",
            args[2] if len(args) > 2 else "file",
        ),
    ))
    registry.register(CoreTool(
        name="EDIT_FILE", icon="✂️",
        description=(
            "Surgically replace a block of text in a file. "
            "Args: path (required), old_text (required, exact text to find), "
            "new_text (required, replacement text). "
            "Provide enough old_text context to make the match unique. "
            "Faster and safer than WRITE_FILE for small changes."
        ),
        risk_level=CONFIRM,
        fn=lambda args, cwd: tool_edit_file(
            args[0] if args else "",
            args[1] if len(args) > 1 else "",
            args[2] if len(args) > 2 else "",
            cwd=cwd,
        ),
    ))
    registry.register(CoreTool(
        name="RUN_COMMAND", icon="⚡",
        description="Execute a shell command. Risk level computed dynamically.",
        risk_level=CONFIRM,
        fn=lambda args, cwd: tool_run_command(args[0] if args else "", cwd=cwd),
    ))
    registry.register(CoreTool(
        name="WEB_SEARCH", icon="🔍",
        description="General web search.",
        risk_level=AUTO,
        fn=lambda args, cwd: tool_web_search(args[0] if args else ""),
    ))
    registry.register(CoreTool(
        name="WEB_FETCH", icon="🌐",
        description="Fetch and return the readable content of a URL.",
        risk_level=AUTO,
        fn=lambda args, cwd: tool_web_fetch(args[0] if args else ""),
    ))
    registry.register(CoreTool(
        name="DOC_SEARCH", icon="📚",
        description=(
            "Search official documentation for a language or framework. "
            "Automatically routes to docs.python.org, fastapi, MDN, doc.rust-lang.org, etc."
        ),
        risk_level=AUTO,
        fn=lambda args, cwd: tool_doc_search(args[0] if args else ""),
    ))
    registry.register(CoreTool(
        name="WEB_VERIFY", icon="✔",
        description=(
            "Verify a code snippet's API calls against official documentation. "
            "Reports VERIFIED / NOT FOUND per identifier."
        ),
        risk_level=AUTO,
        fn=lambda args, cwd: tool_web_verify(
            args[0] if args else "",
            args[1] if len(args) > 1 else "python",
        ),
    ))
    registry.register(CoreTool(
        name="SAVE_MEMORY", icon="🧠",
        description=(
            "Persist an important fact to project memory. "
            "Categories: 'fact' (default), 'arch' (architectural decision), 'failed' (tried & failed)."
        ),
        risk_level=AUTO,
        fn=lambda args, cwd: tool_save_memory(
            args[0] if args else "",
            args[1] if len(args) > 1 else "fact",
            cwd=cwd,
        ),
    ))
    registry.register(CoreTool(
        name="VERIFY", icon="🛡️",
        description="Verify that a file exists and optionally contains specific text. Use after writes.",
        risk_level=AUTO,
        fn=lambda args, cwd: tool_verify(
            args[0] if args else "",
            args[1] if len(args) > 1 else None,
            cwd=cwd,
        ),
    ))
    registry.register(CoreTool(
        name="ASK_USER", icon="❓",
        description=(
            "Pause and ask the user a question. "
            "Args: question (required), choices (optional comma-separated list), "
            "type ('text'|'choice'|'confirm', default 'text'). "
            "Example: ASK_USER(question='Which database?', choices='PostgreSQL,SQLite,MongoDB')."
        ),
        risk_level=AUTO,
        fn=lambda args, cwd: "[ASK_USER] waiting for user input",
    ))

    return registry
