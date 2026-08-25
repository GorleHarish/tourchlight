"""
Unified tool implementations for Torchlight.

All tool functions follow the signature: fn(args: dict, project_root: str) -> str
This module combines the best implementations from both context-manager-cli and rlm_optimized.
"""

import os
import re
import json
import subprocess
import ast
import difflib
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from html.parser import HTMLParser

import httpx


# ── Constants ──────────────────────────────────────────────────────────────

_MAX_TOOL_OUTPUT = 4000
_REJECT_ON_STUB_DEFAULT = True
_SAFE_COMMANDS_SET = {
    "ls",
    "la",
    "ll",
    "cat",
    "head",
    "tail",
    "echo",
    "pwd",
    "which",
    "find",
    "grep",
    "rg",
    "awk",
    "sed",
    "wc",
    "diff",
    "file",
    "python -m pytest",
    "pytest",
    "python -m mypy",
    "mypy",
    "python -m flake8",
    "flake8",
    "ruff check",
    "git status",
    "git log",
    "git diff",
    "git show",
    "git branch",
    "git stash list",
    "git remote",
    "git fetch",
    "npm test",
    "npm run test",
    "npx jest",
    "cargo test",
    "cargo check",
    "cargo clippy",
    "sysctl",
    "vm_stat",
    "top -l",
    "df",
    "diskutil list",
    "pip list",
    "pip show",
    "pip freeze",
    "node --version",
    "python --version",
    "python3 --version",
    "tree",
}

_LONG_CMDS = (
    "pip install",
    "pip3 install",
    "npm install",
    "yarn",
    "cargo build",
    "gradle",
    "./gradlew",
    "mvn ",
    "make ",
    "cmake",
)

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
    try:
        from ..tools.registry import get_tool_registry

        # Default budget
        return 100, 4_000
    except ImportError:
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


# ── Documentation source registry ─────────────────────────────────────────

_DOC_SOURCES: list = [
    (
        r"\bpython\b|\bpytest\b|\basyncio\b|\btyping\b|\bpathlib\b|\bdataclass\b",
        "https://docs.python.org/3/search.html?q=%s",
        "docs.python.org",
    ),
    (
        r"\bfastapi\b",
        "https://fastapi.tiangolo.com/search/?q=%s",
        "fastapi.tiangolo.com",
    ),
    (
        r"\bpydantic\b",
        "https://docs.pydantic.dev/latest/search/?q=%s",
        "docs.pydantic.dev",
    ),
    (
        r"\bsqlalchemy\b",
        "https://docs.sqlalchemy.org/en/20/search.html?q=%s",
        "docs.sqlalchemy.org",
    ),
    (r"\bhttpx\b", "https://www.python-httpx.org/search/?q=%s", "python-httpx.org"),
    (
        r"\brich\b",
        "https://rich.readthedocs.io/en/stable/search.html?q=%s",
        "rich.readthedocs.io",
    ),
    (
        r"\bnode(js)?\b|\bnpm\b|\bjavascript\b|\btypescript\b|\bexpress\b",
        "https://nodejs.org/en/search/?query=%s",
        "nodejs.org",
    ),
    (
        r"\bmdn\b|\bjavascript\b|\bcss\b|\bhtml\b|\bfetch\b|\bpromise\b",
        "https://developer.mozilla.org/en-US/search?q=%s",
        "developer.mozilla.org",
    ),
    (
        r"\brust\b|\bcargo\b|\bcrates?\b|\btokio\b|\bserde\b",
        "https://doc.rust-lang.org/std/?search=%s",
        "doc.rust-lang.org",
    ),
    (r"\bgolang\b|\bgo\b", "https://pkg.go.dev/search?q=%s", "pkg.go.dev"),
    (
        r"\bdocker\b|\bdocker-compose\b",
        "https://docs.docker.com/search/?q=%s",
        "docs.docker.com",
    ),
    (
        r"\bgithub\s+actions?\b|\bworkflow\b",
        "https://docs.github.com/en/search?query=%s",
        "docs.github.com",
    ),
]


def _detect_doc_source(query: str) -> tuple:
    import urllib.parse

    lower = query.lower()
    encoded = urllib.parse.quote_plus(query)
    for pattern, url_tpl, label in _DOC_SOURCES:
        if re.search(pattern, lower):
            return url_tpl % encoded, label
    return (
        f"https://html.duckduckgo.com/html/?q={encoded}+documentation+syntax",
        "duckduckgo (docs)",
    )


def _ddg_search(q: str) -> str:
    """DuckDuckGo HTML search fallback."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    resp = httpx.post(
        "https://html.duckduckgo.com/html/",
        data={"q": q, "kl": "us-en"},
        headers=headers,
        timeout=15,
        follow_redirects=True,
    )
    resp.raise_for_status()

    def strip_tags(s):
        return re.sub(r"<[^>]+>", "", s).strip()

    raw = resp.text
    titles = [
        strip_tags(t)
        for t in re.findall(r'class="result__a"[^>]*>(.*?)</a>', raw, re.DOTALL)
    ]
    urls_raw = [
        strip_tags(u).strip()
        for u in re.findall(r'class="result__url"[^>]*>(.*?)</div>', raw, re.DOTALL)
    ]
    snippets = [
        strip_tags(s)
        for s in re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', raw, re.DOTALL)
    ]

    if not titles:
        return "No results found."

    out = "Search Results (DuckDuckGo):\n\n"
    for i, title in enumerate(titles[:5]):
        url = urls_raw[i] if i < len(urls_raw) else ""
        snip = snippets[i] if i < len(snippets) else ""
        if url and not url.startswith("http"):
            url = "https://" + url
        out += f"**{title}**\n  {url}\n  {snip}\n\n"
    return out.strip()


class StructurePreservingHTMLParser(HTMLParser):
    """
    HTML Parser that preserves structure (<pre>, <code>, <table>, headings)
    while stripping navigation/script noise for clean markdown output.
    Uses depth tracking to handle nested tags cleanly without duplicate backticks.
    """

    def __init__(self):
        super().__init__()
        self.output = []
        self.code_depth = 0
        self.skip_depth = 0
        self.in_heading = False
        self.skip_tags = {
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "noscript",
            "svg",
        }

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in self.skip_tags:
            self.skip_depth += 1
        elif tag_lower in ("pre", "code"):
            self.code_depth += 1
            if self.code_depth == 1:
                self.output.append("\n```\n")
        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.in_heading = True
            level = int(tag_lower[1])
            self.output.append("\n" + "#" * level + " ")
        elif tag_lower == "li":
            self.output.append("\n- ")
        elif tag_lower in ("p", "br", "div", "tr"):
            self.output.append("\n")

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in self.skip_tags:
            if self.skip_depth > 0:
                self.skip_depth -= 1
        elif tag_lower in ("pre", "code"):
            if self.code_depth > 0:
                self.code_depth -= 1
                if self.code_depth == 0:
                    self.output.append("\n```\n")
        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.in_heading = False
            self.output.append("\n")

    def handle_data(self, data):
        if self.skip_depth > 0:
            return
        if self.code_depth > 0:
            self.output.append(data)
        else:
            text = data.strip()
            if text:
                self.output.append(text + " ")

    def get_markdown(self) -> str:
        raw = "".join(self.output)
        return re.sub(r"\n{3,}", "\n\n", raw).strip()


def _get_browser_headers() -> dict:
    """Returns realistic browser headers for stealth HTTP fetching."""
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }


def _fetch_remote_playwright(url: str, timeout_ms: int = 10000) -> Optional[str]:
    """Fallback fetch via Playwright headless browser for Cloudflare / JS SPAs / 403 blocks."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0.0.0 Safari/537.36"
                    )
                )
                page.goto(url, wait_until="load", timeout=timeout_ms)
                page.wait_for_timeout(1000)
                body_text = page.evaluate("""() => {
                    return document.body ? document.body.innerText : '';
                }""")
                if body_text and body_text.strip():
                    return body_text.strip()[:4000]
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
    except Exception as e:
        import logging

        logging.getLogger(__name__).debug(
            f"Playwright remote fetch failed for {url}: {e}"
        )
    return None


def _augment_query_with_project_deps(query: str, project_root: str) -> str:
    """Inspects project dependencies (pyproject.toml, package.json, Cargo.toml) to lock doc query versions."""
    query_str = str(query or "").strip()
    if not query_str or not project_root or not os.path.exists(project_root):
        return query_str

    query_lower = query_str.lower()
    root_path = Path(project_root)

    # Check pyproject.toml
    pyproject = root_path / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8", errors="ignore")
            # Match Poetry style `pkg = "^2.7.0"` or PEP 621 style `"pkg>=2.7.0"`
            matches = re.findall(r'([\w\-]+)\s*=\s*["\'][\^~>=]*(\d+\.\d+)', content)
            matches += re.findall(r'["\']([\w\-]+)\s*[~^>=]+\s*(\d+\.\d+)', content)
            for pkg, ver in matches:
                if pkg.lower() in query_lower:
                    major = ver.split(".")[0]
                    if f"v{major}" not in query_lower and major not in query_lower:
                        return f"{query_str} v{major}"
        except Exception:
            pass

    # Check package.json
    pkg_json = root_path / "package.json"
    if pkg_json.exists():
        try:
            content = pkg_json.read_text(encoding="utf-8", errors="ignore")
            for pkg, ver in re.findall(
                r'"([\w\-@/]+)"\s*:\s*"[\^~>=]*(\d+\.\d+)', content
            ):
                pkg_name = pkg.split("/")[-1]
                if pkg_name.lower() in query_lower:
                    major = ver.split(".")[0]
                    if f"v{major}" not in query_lower and major not in query_lower:
                        return f"{query_str} v{major}"
        except Exception:
            pass

    return query_str


def _extract_identifiers(snippet: str, language: str) -> list:
    if language in ("python", "py"):
        calls = re.findall(r"([\w]+(?:\.[\w]+)+)\s*\(", snippet)
        standalone = re.findall(r"\b([A-Z][\w]+|[a-z][\w_]{3,})\s*\(", snippet)
        identifiers = list(dict.fromkeys(calls + standalone))
    elif language in ("javascript", "typescript", "js", "ts"):
        identifiers = list(
            dict.fromkeys(re.findall(r"([\w]+(?:\.[\w]+)+)\s*\(", snippet))
        )
    elif language in ("rust", "rs"):
        identifiers = list(
            dict.fromkeys(re.findall(r"([\w:]+(?:::[\w]+)+)\s*[!\(]", snippet))
        )
    elif language in ("go",):
        identifiers = list(dict.fromkeys(re.findall(r"([\w]+\.[\w]+)\s*\(", snippet)))
    else:
        identifiers = list(
            dict.fromkeys(re.findall(r"([\w]+(?:[.:][\w]+)+)\s*[\(!\[]?", snippet))
        )
    return [i for i in identifiers if len(i) > 3 and not i.startswith("_")][:8]


# ══════════════════════════════════════════════════════════════════════════
# Tool implementations
# ══════════════════════════════════════════════════════════════════════════


def tool_read_file_impl(args: dict, project_root: str) -> str:
    """READ_FILE — read a file with optional line-range or symbol syntax."""
    try:
        path = (args.get("path") or "").strip().lstrip("@")
        if not path:
            return "READ_FILE requires a file path. Use RUN_COMMAND('ls') to see directory contents."

        # Helper to parse integer safely from string / int / 'L10'
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
        return f"Error reading file: {e}"


_TAB_PRESERVE_EXTS = {
    ".go",
    ".tsv",
    ".tab",
    ".mk",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".asm",
    ".s",
    ".zig",
    ".lua",
    ".just",
}
_TAB_PRESERVE_BASENAMES = {"makefile", "gnumakefile", "justfile", "kbuild"}


def _normalize_whitespace(content: str, filename: str = "") -> str:
    """Normalize mixed tabs to spaces (except Makefiles/TSV/Go/C/ASM/etc.), remove trailing line spaces, and ensure trailing newline."""
    if not content:
        return ""
    ext = os.path.splitext(filename)[1].lower() if filename else ""
    basename = os.path.basename(filename).lower() if filename else ""
    preserve_tabs = ext in _TAB_PRESERVE_EXTS or basename in _TAB_PRESERVE_BASENAMES

    lines = content.splitlines()
    if preserve_tabs:
        normalized = [line.rstrip() for line in lines]
    else:
        normalized = [line.replace("\t", "    ").rstrip() for line in lines]
    return "\n".join(normalized) + "\n"


def _detect_stubs(content: str, filename: str = "") -> Optional[str]:
    """Scan content for suspicious lazy LLM stub/placeholder patterns."""
    if not content:
        return None

    # Skip stub check on test files to prevent false positives on test fixtures
    basename = os.path.basename(filename).lower() if filename else ""
    if any(kw in basename for kw in ("test_", "_test", ".test.", ".spec.")):
        return None

    stub_patterns = [
        (r"#\s*TODO:?\s*(?:implement|add logic|fill in)", "Python TODO stub"),
        (
            r"#\s*\.\.\.\s*(?:rest|existing|code|remaining)",
            "Python code truncation stub",
        ),
        (
            r"//\s*\.\.\.\s*(?:rest|existing|code|implementation|remaining)",
            "JS/C code truncation stub",
        ),
        (
            r"/\*\s*\.\.\.\s*(?:rest|existing|code|remaining)\s*\*/",
            "C-style block stub",
        ),
        (r"pass\s*#\s*(?:stub|implement|todo|fill)", "Python pass stub"),
        (r'throw new Error\(["\']Not implemented["\']\)', "Unimplemented error stub"),
    ]

    found = []
    for pattern, name in stub_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            found.append(name)

    if found:
        return f"\n⚠️ Stub Warning: Code contains placeholder stubs ({', '.join(found)}). Ensure full implementation is provided."
    return None


def _format_code_on_save(content: str, filename: str, project_root: str) -> str:
    """Format code deterministically post-save using local tools (ruff, black, prettier, gofmt, rustfmt)."""
    if not content:
        return content

    ext = os.path.splitext(filename)[1].lower()

    # 1. Python formatters: ruff format or black
    if ext == ".py":
        try:
            res = subprocess.run(
                ["ruff", "format", "-"],
                input=content,
                text=True,
                capture_output=True,
                timeout=2,
                cwd=project_root,
            )
            if res.returncode == 0 and res.stdout:
                return res.stdout
        except Exception:
            pass
        try:
            res = subprocess.run(
                ["black", "-q", "-"],
                input=content,
                text=True,
                capture_output=True,
                timeout=2,
                cwd=project_root,
            )
            if res.returncode == 0 and res.stdout:
                return res.stdout
        except Exception:
            pass

    # 2. Web/JS/TS/JSON formatters: local or global prettier (no npx network prompts)
    elif ext in (".js", ".ts", ".jsx", ".tsx", ".json", ".css", ".html"):
        import shutil

        prettier_bin = None
        local_prettier = os.path.join(project_root, "node_modules", ".bin", "prettier")
        if os.path.exists(local_prettier):
            prettier_bin = [local_prettier]
        elif shutil.which("prettier"):
            prettier_bin = ["prettier"]

        if prettier_bin:
            try:
                res = subprocess.run(
                    prettier_bin + ["--stdin-filepath", filename],
                    input=content,
                    text=True,
                    capture_output=True,
                    timeout=2,
                    cwd=project_root,
                )
                if res.returncode == 0 and res.stdout:
                    return res.stdout
            except Exception:
                pass

    # 3. Go: gofmt
    elif ext == ".go":
        try:
            res = subprocess.run(
                ["gofmt"],
                input=content,
                text=True,
                capture_output=True,
                timeout=2,
                cwd=project_root,
            )
            if res.returncode == 0 and res.stdout:
                return res.stdout
        except Exception:
            pass

    # 4. Rust: rustfmt
    elif ext == ".rs":
        try:
            res = subprocess.run(
                ["rustfmt", "--emit", "stdout"],
                input=content,
                text=True,
                capture_output=True,
                timeout=2,
                cwd=project_root,
            )
            if res.returncode == 0 and res.stdout:
                return res.stdout
        except Exception:
            pass

    return _normalize_whitespace(content, filename)


def _check_syntax(content: str, filename: str) -> Optional[str]:
    """Perform fast inline syntax validation for edited/written files across Python, JSON, JS/TS."""
    if not content:
        return None

    ext = os.path.splitext(filename)[1].lower()

    # 1. Python AST parsing
    if ext == ".py":
        import ast

        try:
            ast.parse(content, filename=filename)
        except SyntaxError as se:
            line_no = getattr(se, "lineno", "?")
            msg = getattr(se, "msg", str(se))
            return f"\n⚠️ Syntax Warning (line {line_no}): {msg}"
        except Exception as e:
            return f"\n⚠️ Syntax Warning: {e}"

    # 2. JSON parsing
    elif ext in (".json", ".jsonc"):
        import json

        if not content.strip():
            return "\n⚠️ JSON Syntax Warning: Empty file content"
        try:
            data = json.loads(content)
            if isinstance(data, dict) and not data:
                return "\n⚠️ JSON Syntax Warning: Empty JSON object"
        except json.JSONDecodeError as je:
            return (
                f"\n⚠️ JSON Syntax Warning (line {je.lineno}, col {je.colno}): {je.msg}"
            )
        except Exception as e:
            return f"\n⚠️ JSON Syntax Warning: {e}"

    # 3. Basic bracket balance check for JS/TS/C-like languages (filtering strings and comments)
    elif ext in (".js", ".ts", ".jsx", ".tsx", ".c", ".cpp", ".java"):
        # Strip comments and string literals to prevent false positives on bracket matching
        cleaned = re.sub(r"//.*", "", content)
        cleaned = re.sub(r"/\*[\s\S]*?\*/", "", cleaned)
        cleaned = re.sub(r'([\'"`])(?:\\.|[^\\])*?\1', "", cleaned)

        stack = []
        matching = {")": "(", "}": "{", "]": "["}
        for line_idx, line in enumerate(cleaned.splitlines(), start=1):
            for char in line:
                if char in matching.values():
                    stack.append((char, line_idx))
                elif char in matching:
                    if not stack or stack[-1][0] != matching[char]:
                        return f"\n⚠️ Syntax Warning (line {line_idx}): Unmatched closing bracket '{char}'"
                    stack.pop()
        if stack:
            unclosed_char, unclosed_line = stack[-1]
            return f"\n⚠️ Syntax Warning (line {unclosed_line}): Unclosed bracket '{unclosed_char}'"

    return None


def _detect_truncation_stubs(content: str, filename: str = "") -> Optional[str]:
    """Detect truncation-style stubs (code cut off / intentionally unimplemented).

    These indicate the model failed to produce a complete implementation and
    are treated as hard errors by the write gate (unlike benign TODO comments).
    """
    if not content:
        return None
    basename = os.path.basename(filename).lower() if filename else ""
    if any(kw in basename for kw in ("test_", "_test", ".test.", ".spec.")):
        return None
    truncation_patterns = [
        (
            r"#\s*\.\.\.\s*(?:rest|existing|code|remaining)",
            "Python code truncation stub",
        ),
        (
            r"//\s*\.\.\.\s*(?:rest|existing|code|implementation|remaining)",
            "JS/C code truncation stub",
        ),
        (
            r"/\*\s*\.\.\.\s*(?:rest|existing|code|remaining)\s*\*/",
            "C-style block stub",
        ),
        (r'throw new Error\(["\']Not implemented["\']\)', "Unimplemented error stub"),
        (
            r"\.\.\.\s*(?:rest|remaining|code|implementation|continues|more)",
            "Plain-text truncation marker",
        ),
        (
            r"\b(?:code|implementation|rest|content)\s+omitted\b",
            "Explicit truncation statement",
        ),
        (
            r"<!--\s*(?:truncated|cut[ -]?off|incomplete|rest\s+omitted)\s*-->",
            "HTML truncation comment",
        ),
    ]
    found = []
    for pattern, name in truncation_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            found.append(name)
    if found:
        return (
            f"\n🚫 Incomplete Code Detected: content contains placeholder truncation stubs "
            f"({', '.join(found)}). Provide the full implementation."
        )
    return None


def _auto_repair(content: str, filename: str, project_root: str) -> Optional[str]:
    """Apply safe auto-fixes (ruff check --fix, E/F rules) to in-memory content.

    Returns repaired content or None when no repair tool is available.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext != ".py":
        return None
    try:
        res = subprocess.run(
            [
                "ruff",
                "check",
                "--fix",
                "--select",
                "E,F",
                "--stdin-filename",
                filename,
                "-",
            ],
            input=content,
            text=True,
            capture_output=True,
            timeout=5,
            cwd=project_root,
        )
        if res.returncode in (0, 1) and res.stdout:
            return res.stdout
    except Exception:
        pass
    return None


def _check_compile(content: str, filename: str, project_root: str) -> Optional[str]:
    """Stricter compile gate: compile() for Python, node --check for plain JS.

    Catches errors ast.parse misses (e.g. 'return' outside a function).
    Returns an error message or None when the content compiles / can't be checked.
    """
    if not content:
        return None
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".py":
        try:
            compile(content, filename, "exec")
        except SyntaxError as se:
            line_no = getattr(se, "lineno", "?")
            msg = getattr(se, "msg", str(se))
            return f"compile error (line {line_no}): {msg}"
        except (ValueError, TypeError, RecursionError) as e:
            return f"compile error: {e}"

    elif ext in (".js", ".mjs", ".cjs"):
        import shutil
        import tempfile

        node_bin = shutil.which("node")
        if not node_bin:
            return None
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", suffix=ext, delete=False, encoding="utf-8"
            ) as tf:
                tf.write(content)
                tmp_path = tf.name
            res = subprocess.run(
                [node_bin, "--check", tmp_path],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=project_root,
            )
            if res.returncode != 0:
                stderr = (res.stderr or "").strip()
                return f"node syntax error: {stderr[:400]}"
        except Exception:
            return None
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

def _clean_copied_file_text(text: str, filename: str = "") -> str:
    """Strip display decorations (line number prefixes, symbol maps, markdown codeblock fences,
    file header/footer annotations, pinned file framing, and stray copy/token artifacts) if model
    copied verbatim from READ_FILE or memory scratchpad into old_text, new_text, or content.
    """
    if not text or not isinstance(text, str):
        return text

    # Handle unescaped literal \\n and \\t from raw JSON serialization
    if "\\n" in text and "\n" not in text:
        text = text.replace("\\n", "\n").replace("\\t", "\t")

    lines = text.splitlines()
    if not lines:
        return text

    cleaned_lines = []
    in_symbol_map = False

    for line in lines:
        trimmed = line.strip()

        # 1. Pinned file framing headers/footers e.g. "--- game.js ---", "--- index.html---", "=== style.css ==="
        if (
            re.match(r"^---\s*[\w\.\-/: ]+\s*---$", trimmed)
            or re.match(r"^---\s*end\s+[\w\.\-/: ]+\s*---$", trimmed, re.IGNORECASE)
            or re.match(r"^===\s*[\w\.\-/: ]+\s*===$", trimmed)
            or trimmed.startswith("[Pinned file")
            or trimmed.endswith("old_text:]")
        ):
            continue

        # 2. Symbol map header e.g. "Symbols:" or "Symbols in file:"
        if trimmed.lower() in ("symbols:", "symbols in file:"):
            in_symbol_map = True
            continue

        # 3. Inside symbol map: skip symbol entries e.g. "L   6  fn     update"
        if in_symbol_map:
            if re.match(
                r"^L\s*\d+\s+(?:fn|class|struct|interface|type|const|var|let|def|func|val|pub|async)\s+\w+",
                trimmed,
                re.IGNORECASE,
            ):
                continue
            elif not trimmed:
                continue
            else:
                # Reached non-symbol line, exit symbol map
                in_symbol_map = False

        # 4. File line count headers e.g. "game.js (42 lines)", "index.html (26 lines)", "lines 1–42 (of 42 total)"
        if re.search(
            r"^(?:[\w\.\-/]+\s+)?(?:\(\d+\s*lines\)|lines\s*\d+[–\-]\d+\s*\(of\s*\d+\s*total\))$",
            trimmed,
            re.IGNORECASE,
        ):
            continue

        # 5. Markdown code fences e.g. "```js", "```html", "```python", "```"
        if re.match(r"^```[a-zA-Z0-9_\-]*$", trimmed) or trimmed == "```":
            continue

        # 6. READ_FILE truncation suffixes e.g. "... (capped at 100 lines...)"
        if re.search(
            r"^\.\.\.\s*\((?:capped at \d+ lines|\d+ more lines).*\)$",
            trimmed,
            re.IGNORECASE,
        ):
            continue

        # 7. Line number prefixes with optional stray copy/token artifacts e.g.
        # " 1 | const canvas...", " 5 | al <meta...", "  42 | ctx...", "L10 | def foo()", " 1: import os", " 1. const x"
        line_num_match = re.match(
            r"^\s*(?:L\s*)?\d+\s*[|:]\s?(?:(?:al|el|le|la|il|l|a)\s+)?(.*)$", line
        )
        if not line_num_match:
            line_num_match = re.match(
                r"^\s*(?:L\s*)?\d+\.\s?(?:(?:al|el|le|la|il|l|a)\s+)?(.*)$", line
            )
        if not line_num_match:
            line_num_match = re.match(
                r"^\s*\|\s?(?:(?:al|el|le|la|il|l|a)\s+)?(.*)$", line
            )

        if line_num_match:
            processed_line = line_num_match.group(1)
        else:
            processed_line = line

        # 8. Clean stray token noise before HTML tags, CSS rules, or keywords if present
        token_noise_match = re.match(
            r"^(\s*)(?:al|el|le|la|il)\s+(<[a-zA-Z/!]|body\b|html\b|head\b|meta\b|title\b|style\b|script\b|canvas\b|div\b|span\b|header\b|footer\b|main\b|section\b|const\b|let\b|var\b|function\b|def\b|import\b|from\b|class\b|pub\b|fn\b|return\b|if\b|else\b|for\b|while\b)(.*)$",
            processed_line,
        )
        if token_noise_match:
            processed_line = f"{token_noise_match.group(1)}{token_noise_match.group(2)}{token_noise_match.group(3)}"

        cleaned_lines.append(processed_line)

    res = "\n".join(cleaned_lines)
    if text.endswith("\n") and not res.endswith("\n"):
        res += "\n"
    return res


def _strip_leading_filename_header(content: str, filename: str) -> str:
    """Strip redundant leading filename headers or markdown labels from file content."""
    if not content or not filename:
        return content
    base = os.path.basename(filename).strip()
    if not base:
        return content

    lines = content.splitlines(keepends=True)
    if not lines:
        return content

    first_line = lines[0].strip()

    # Edge Case 1: Shebang lines (e.g. #!/usr/bin/env node) must NEVER be stripped
    if first_line.startswith("#!"):
        return content

    # Edge Case 2: In markdown files, legitimate '# README.md' title headers must NOT be stripped
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".md", ".markdown", ".rst") and first_line.startswith("#"):
        if not re.search(r"^(?:#{1,6}|<!--)\s*(?:file|filename|filepath|path)\s*[:=]", first_line, re.IGNORECASE):
            return content

    base_lower = base.lower()

    # 1. Check if first line is bare filename or relative path (e.g. "game.js", "src/game.js", "`game.js`", "### game.js")
    cleaned_first = first_line.strip("`'\"#/*- ").strip()
    if (
        cleaned_first.lower() == base_lower
        or cleaned_first.lower().endswith("/" + base_lower)
        or cleaned_first.lower().endswith("\\" + base_lower)
    ):
        return "".join(lines[1:]).lstrip("\r\n")

    # 2. Check if first line is markdown header or file label (e.g. "### File: game.js", "// file: game.js")
    m = re.search(
        r"^(?:#{1,6}|//|/\*|<!--|#)\s*(?:file|filename|filepath|path)\s*[:=]?\s*`?([^\n\r`]+)`?",
        first_line,
        re.IGNORECASE,
    )
    if m and os.path.basename(m.group(1).strip()).lower() == base_lower:
        return "".join(lines[1:]).lstrip("\r\n")

    # 3. Check for leftover leading codeblock fence (e.g. ```javascript\n...)
    if first_line.startswith("```"):
        return "".join(lines[1:]).lstrip("\r\n")

    return content


def _validate_and_repair(
    content: str,
    filename: str,
    project_root: str,
    *,
    force: bool = False,
    reject_on_stub: bool = True,
) -> Tuple[str, str]:
    """Validate code before it is written; auto-repair when possible.

    Returns a (status, payload) tuple:
      - ("ok", content)    → content is validated (and possibly repaired/formatted)
      - ("error", message) → message is a user-facing error; the file must NOT be written

    `force=True` bypasses the syntax/compile/stub gates (scaffolding escape hatch)
    while still running formatting.
    """
    if not content or not content.strip():
        return "ok", content

    # 0. Clean accidental leading filename header, symbol maps, line numbers, or markdown codeblock fences
    content = _clean_copied_file_text(content, filename)
    content = _strip_leading_filename_header(content, filename)
    if content.endswith("```"):
        content = re.sub(r"[\r\n]+```\s*$", "", content)

    # 1. Auto-repair (safe ruff fixes), then deterministic formatting
    repaired = _auto_repair(content, filename, project_root)
    if repaired is not None and repaired != content:
        content = repaired
    formatted = _format_code_on_save(content, filename, project_root)
    if formatted != content:
        content = formatted

    if not force:
        # 2. Fast syntax validation
        syntax_note = _check_syntax(content, filename)
        if syntax_note:
            detail = syntax_note.replace("\n⚠️ Syntax Warning", "").strip()
            err_json = json.dumps({"error": "syntax_error", "file": os.path.basename(filename), "detail": detail, "force_hint": "pass force=true to write anyway"}, separators=(',', ':'))
            return ("error", f"Error: Syntax gate rejected write -> {err_json}")

        # 3. Compile gate (catches what ast.parse misses, e.g. 'return' outside function)
        compile_note = _check_compile(content, filename, project_root)
        if compile_note:
            err_json = json.dumps({"error": "compile_error", "file": os.path.basename(filename), "detail": compile_note, "force_hint": "pass force=true to write anyway"}, separators=(',', ':'))
            return ("error", f"Error: Compile gate rejected write -> {err_json}")

        # 4. Truncation stub gate
        if reject_on_stub:
            trunc_note = _detect_truncation_stubs(content, filename)
            if trunc_note:
                err_json = json.dumps({"error": "stub_error", "file": os.path.basename(filename), "detail": trunc_note.strip()}, separators=(',', ':'))
                return ("error", f"Error: Stub gate rejected write -> {err_json}")

        # 5. Anti-Symptom Patching Gate
        symptom_note = _detect_symptom_patching(content, filename)
        if symptom_note:
            err_json = json.dumps({"error": "symptom_patching_error", "file": os.path.basename(filename), "detail": symptom_note.strip()}, separators=(',', ':'))
            return ("error", f"Error: Anti-Symptom-Patching gate rejected write -> {err_json}")

    return "ok", content


def _detect_symptom_patching(content: str, filename: str) -> Optional[str]:
    """Detect exception-swallowing and test assertion commenting out anti-patterns."""
    if not content:
        return None

    # Check exception swallowing patterns
    swallow_patterns = [
        (
            r"except\s*:\s*pass\b",
            "Blank 'except: pass' block swallowing all exceptions",
        ),
        (
            r"except\s+Exception\s*:\s*pass\b",
            "Generic 'except Exception: pass' block swallowing exceptions",
        ),
        (
            r'except\s+Exception\s*:\s*return\s+(?:None|0|""|\{\}|\[\])\b',
            "Generic 'except Exception: return <dummy>' swallowing exceptions",
        ),
    ]

    for pat, desc in swallow_patterns:
        if re.search(pat, content):
            return desc

    # Check test assertion comment-out patterns in test files
    if _is_test_file(filename):
        lines = content.splitlines()
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") and (
                "assert " in stripped or "self.assert" in stripped
            ):
                return f"Commented-out test assertion on line {idx}: '{stripped[:60]}'"

    return None


def _is_test_file(filepath: str) -> bool:
    """Check if filepath matches known test file patterns."""
    return any(
        pat in filepath.lower()
        for pat in ["test_", "_test.py", "tests/", "spec/", ".test.", ".spec."]
    )


def _sync_ast_graph(project_root: str, file_path: str) -> None:
    """Incrementally update AST graph when a file is created or edited."""
    try:
        # Skip static markup, styling, docs, and assets where AST symbol trees are inapplicable
        lower_path = file_path.lower()
        if lower_path.endswith((
            ".html", ".htm", ".css", ".scss", ".sass", ".less",
            ".svg", ".json", ".md", ".txt", ".yaml", ".yml",
            ".csv", ".tsv", ".xml", ".ini", ".conf", ".toml",
        )):
            return

        from core.flashlight.graph_engine import update_project_graph_file

        update_project_graph_file(project_root, file_path)
    except Exception:
        pass


def tool_write_file_impl(args: dict, project_root: str) -> str:
    """WRITE_FILE — create or overwrite a file."""
    if not isinstance(args, dict):
        args = {"raw": str(args)}

    path_raw = (
        args.get("path")
        or args.get("file")
        or args.get("filepath")
        or args.get("filename")
        or args.get("dest")
        or args.get("target")
        or args.get("p")
    )

    content = args.get("content")
    if content is None:
        content = args.get("code") or args.get("text") or args.get("data") or ""

    # Fallback: extract from raw string
    if not path_raw and "raw" in args:
        raw_text = str(args["raw"])
        p_match = re.search(
            r'["\']?(?:path|file|filename|filepath)["\']?\s*:\s*["\']([^"\']+)["\']',
            raw_text,
        )
        if p_match:
            path_raw = p_match.group(1)
        c_match = re.search(
            r'["\']?(?:content|code|text)["\']?\s*:\s*["\']([\s\S]*)["\']\s*\}?$',
            raw_text,
        )
        if c_match:
            content = c_match.group(1)

    if not path_raw or not str(path_raw).strip():
        return "Error: Missing required 'path' parameter for WRITE_FILE."

    if content is not None:
        content = _clean_copied_file_text(str(content), str(path_raw))

    path_str = str(path_raw).strip()
    protect_tests = (
        args.get("protect_tests", False)
        or os.environ.get("TORCHLIGHT_PROTECT_TESTS") == "1"
    )
    if protect_tests and _is_test_file(path_str):
        return "Error: Test files are protected during automated recovery. Fix the source code instead."

    p = (
        os.path.join(project_root, path_str)
        if not os.path.isabs(path_str)
        else path_str
    )

    if os.path.isdir(p):
        return f"Error: Specified path '{path_str}' is a directory, not a file."

    try:
        parent_dir = os.path.dirname(p)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        force = bool(args.get("force", False))
        reject_on_stub = bool(args.get("reject_on_stub", _REJECT_ON_STUB_DEFAULT))
        status, payload = _validate_and_repair(
            content, p, project_root, force=force, reject_on_stub=reject_on_stub
        )
        if status != "ok":
            return payload
        content = payload

        existing_content = ""
        if os.path.exists(p) and os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as existing_f:
                    existing_content = existing_f.read()
                if (
                    hashlib.sha256(existing_content.encode("utf-8")).hexdigest()
                    == hashlib.sha256(content.encode("utf-8")).hexdigest()
                ):
                    return (
                        f"No change: file content of {path_str} is already identical. "
                        f"Hint: Use READ_FILE to verify current contents, or WRITE_FILE if you need to overwrite."
                    )

                # Accidental Code Deletion Guard:
                # If target file already has substantial code (>= 8 lines) and the new write
                # provides significantly fewer lines (< 60% of existing lines), reject unless force=True.
                existing_lines = [l for l in existing_content.splitlines() if l.strip()]
                new_lines = [l for l in content.splitlines() if l.strip()]
                if len(existing_lines) >= 8 and len(new_lines) < int(len(existing_lines) * 0.6) and not force:
                    return (
                        f"⛔ [ACCIDENTAL CODE OVERWRITE BLOCKED]: Target file '{path_str}' already has {len(existing_lines)} lines of code, "
                        f"but WRITE_FILE was called with only {len(new_lines)} line(s) without 'force: true'.\n"
                        f"This would overwrite and destroy previous progress/functions.\n"
                        f"Next required action: Use EDIT_FILE to surgically insert or modify code:\n"
                        f'<tool_call>{{"name": "EDIT_FILE", "arguments": {{"path": "{path_str}", "old_text": "...", "new_text": "..."}}}}</tool_call>\n'
                        f"Or if you genuinely intend to replace the entire file, pass 'force': true."
                    )
            except Exception:
                pass

        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        _sync_ast_graph(project_root, p)
        line_count = content.count("\n") + (
            1 if content and not content.endswith("\n") else 0
        )
        from core.memory.manager import calculate_in_memory_diff

        added, deleted = calculate_in_memory_diff(existing_content, content)
        stub_note = _detect_stubs(content) or ""
        return f"Written {line_count} lines to {p} (+{added}, -{deleted}){stub_note}"
    except Exception as e:
        return f"Error writing {p}: {e}"


# A Search/Replace block is only recognized when a 7-character conflict marker
# opens a line. Substring checks for "SEARCH" or "=======" match ordinary source.
_CONFLICT_MARKER_RE = re.compile(r"^[ \t]*(?:<{7}|>{7})", re.MULTILINE)

# Both tool_edit_file_impl and tool_write_file_impl append a "(+added, -deleted)"
# diffstat, and only after the file has actually been written to disk. Testing
# for it is a structural success signal; matching English prefixes like "Error"
# or "Edit failed" against the message is not, and missed whole failure classes.
_DIFFSTAT_RE = re.compile(r"\(\+\d+, -\d+\)")


def _edit_succeeded(result: str) -> bool:
    """True only when an edit/write result reports a committed change."""
    return bool(result) and _DIFFSTAT_RE.search(result) is not None


def _parse_diff_block(text: str) -> tuple[Optional[str], Optional[str]]:
    """Parse Aider-style <<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE block into (old_text, new_text).
    Supports flexible variations produced by LLMs (e.g., missing 'REPLACE' label, '>>>>>>>' used as divider).
    """
    if not text:
        return None, None

    def _clean_segment(s: str) -> str:
        if s.startswith("\r\n"):
            s = s[2:]
        elif s.startswith("\n"):
            s = s[1:]
        if s.endswith("\r\n"):
            s = s[:-2]
        elif s.endswith("\n"):
            s = s[:-1]
        return s

    # 1. Flexible regex-based parsing for Search/Replace blocks
    search_match = re.search(r"<<<<<<<(?:[ \t]*SEARCH)?\r?\n", text)
    if search_match:
        after_search = text[search_match.end() :]
        # Option A: Standard divider =======
        div_match = re.search(r"\r?\n=======\r?\n", after_search)
        if div_match:
            search_part = after_search[: div_match.start()]
            after_div = after_search[div_match.end() :]
            end_match = re.search(
                r"\r?\n>>>>>>>(?:[ \t]*REPLACE)?(?:$|\r?\n)", after_div
            )
            if end_match:
                replace_part = after_div[: end_match.start()]
                return _clean_segment(search_part), _clean_segment(replace_part)
            else:
                end_match2 = re.search(r">>>>>>>(?:[ \t]*REPLACE)?", after_div)
                if end_match2:
                    replace_part = after_div[: end_match2.start()]
                    return _clean_segment(search_part), _clean_segment(replace_part)

        # Option B: Model used >>>>>>> as divider between SEARCH block and REPLACE block
        div_alt = re.search(r"\r?\n>>>>>>>(?:[ \t]*SEARCH)?\r?\n", after_search)
        if div_alt:
            search_part = after_search[: div_alt.start()]
            after_div = after_search[div_alt.end() :]
            end_match = re.search(r"\r?\n>>>>>>>(?:[ \t]*REPLACE)?", after_div)
            if end_match:
                replace_part = after_div[: end_match.start()]
                return _clean_segment(search_part), _clean_segment(replace_part)

        # Option C: Model omitted ======= divider, putting >>>>>>> REPLACE directly between search and replace
        rep_tag = re.search(r"\r?\n>>>>>>>(?:[ \t]*REPLACE)?\r?\n", after_search)
        if rep_tag:
            search_part = after_search[: rep_tag.start()]
            after_rep = after_search[rep_tag.end() :]
            end_tag = re.search(r"\r?\n>>>>>>>(?:[ \t]*REPLACE)?", after_rep)
            replace_part = after_rep[: end_tag.start()] if end_tag else after_rep
            if search_part and replace_part:
                return _clean_segment(search_part), _clean_segment(replace_part)

    # 2. String splitting fallback (legacy logic)
    search_marker = "<<<<<<< SEARCH"
    divide_marker = "======="
    replace_marker = ">>>>>>> REPLACE"

    if search_marker in text and divide_marker in text:
        try:
            after_search = text.split(search_marker, 1)[1]
            if replace_marker in after_search:
                between, _ = after_search.split(replace_marker, 1)
            elif ">>>>>>>" in after_search:
                between, _ = after_search.split(">>>>>>>", 1)
            else:
                between = after_search
            search_part, replace_part = between.split(divide_marker, 1)
            return _clean_segment(search_part), _clean_segment(replace_part)
        except Exception:
            pass

    # No recognizable block structure. Return (None, None) rather than guessing:
    # splitting arbitrary text on blank lines or at its midpoint fabricates an
    # (old_text, new_text) pair the model never asked for, which silently
    # deletes the "old" half and duplicates the "new" half.
    return None, None


def _get_symbol_bounds_ast(content: str, symbol_name: str) -> Optional[Tuple[int, int]]:
    """Helper to locate exact start and end line bounds for an AST symbol in Python source code."""
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = node.name
                if (
                    name == symbol_name
                    or symbol_name.endswith(f".{name}")
                    or f".{name}" in symbol_name
                ):
                    start = getattr(node, "lineno", None)
                    end = getattr(node, "end_lineno", None)
                    if start and end:
                        return start, end
    except Exception:
        pass
    return None


def _get_symbol_bounds_general(content: str, symbol_name: str, ext: str = "") -> Optional[Tuple[int, int]]:
    """Helper to locate exact start and end line bounds (1-based) for a symbol across Python, JS, TS, Go, Rust, etc."""
    if not content or not symbol_name:
        return None

    # 1. Python AST parsing
    ext_norm = ext.lower().lstrip(".")
    if ext_norm in ("py", ""):
        bounds = _get_symbol_bounds_ast(content, symbol_name)
        if bounds:
            return bounds

    lines = content.splitlines()
    total = len(lines)

    # 2. Brace-based languages (JS, TS, C, C++, Java, Rust, Go, CSS)
    sym_clean = re.escape(symbol_name)
    patterns = [
        re.compile(rf"^\s*(?:export\s+)?(?:async\s+)?function\s+{sym_clean}\b"),
        re.compile(rf"^\s*(?:export\s+)?(?:const|let|var)\s+{sym_clean}\s*="),
        re.compile(rf"^\s*(?:export\s+)?class\s+{sym_clean}\b"),
        re.compile(rf"^\s*(?:pub\s+)?fn\s+{sym_clean}\b"),
        re.compile(rf"^\s*(?:def|func|fun)\s+{sym_clean}\b"),
        re.compile(rf"^\s*{sym_clean}\s*\([^)]*\)\s*\{{"),
        re.compile(rf"\b{sym_clean}\b"),
    ]

    start_line = None
    for i, line in enumerate(lines):
        for pat in patterns:
            if pat.search(line):
                start_line = i + 1
                break
        if start_line is not None:
            break

    if start_line is None:
        return None

    # Track brace balance from start_line
    brace_depth = 0
    found_first_brace = False
    for i in range(start_line - 1, total):
        line = lines[i]
        clean_l = re.sub(r"//.*$", "", line)
        for char in clean_l:
            if char == "{":
                brace_depth += 1
                found_first_brace = True
            elif char == "}":
                brace_depth -= 1
                if found_first_brace and brace_depth <= 0:
                    return start_line, i + 1

    if start_line is not None:
        return start_line, start_line

    return None


def _commit_edit_file(
    p: str,
    new_content: str,
    original_content: str,
    project_root: str,
    force: bool,
    reject_on_stub: bool,
) -> tuple[bool, str, int, int]:
    if (
        hashlib.sha256(original_content.encode("utf-8")).hexdigest()
        == hashlib.sha256(new_content.encode("utf-8")).hexdigest()
    ):
        return False, "No change: file content is already identical.", 0, 0
    status, payload = _validate_and_repair(
        new_content, p, project_root, force=force, reject_on_stub=reject_on_stub
    )
    if status != "ok":
        return False, payload, 0, 0
    new_content = payload
    with open(p, "w", encoding="utf-8") as f:
        f.write(new_content)
    _sync_ast_graph(project_root, p)
    from core.memory.manager import calculate_in_memory_diff

    added, deleted = calculate_in_memory_diff(original_content, new_content)
    return True, new_content, added, deleted


def _commit_edit_and_format_result(
    p: str,
    new_content: str,
    original_content: str,
    project_root: str,
    force: bool,
    reject_on_stub: bool,
    prefix_msg: str,
) -> str:
    from core.memory.manager import calculate_in_memory_diff
    from core.tools.task_helpers import get_active_task_description

    if (
        hashlib.sha256(original_content.encode("utf-8")).hexdigest()
        == hashlib.sha256(new_content.encode("utf-8")).hexdigest()
    ):
        return "No change: file content is already identical."

    status, payload = _validate_and_repair(
        new_content, p, project_root, force=force, reject_on_stub=reject_on_stub
    )
    if status != "ok":
        return payload
    new_content = payload

    with open(p, "w", encoding="utf-8") as f:
        f.write(new_content)
    _sync_ast_graph(project_root, p)

    added, deleted = calculate_in_memory_diff(original_content, new_content)
    stub_note = _detect_stubs(new_content) or ""
    active_task = get_active_task_description(project_root)
    task_suffix = f" • 🎯 Task: {active_task}" if active_task else ""

    return f"{prefix_msg} (+{added}, -{deleted}){task_suffix}.{stub_note}"


def _reindent_block(old_text: str, new_text: str, content: str, start_idx: int) -> str:
    line_start = content.rfind("\n", 0, start_idx)
    line_start = 0 if line_start == -1 else line_start + 1
    leading_space_match = re.match(r"^[ \t]*", content[line_start:start_idx])
    if not leading_space_match:
        return new_text
    leading_space = leading_space_match.group(0)
    if new_text.startswith(leading_space):
        return new_text
    lines = new_text.split("\n")
    reindented = []
    for i, line in enumerate(lines):
        if i == 0:
            reindented.append(line)
        else:
            reindented.append(leading_space + line if line.strip() else line)
    return "\n".join(reindented)

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
    """GREP — search for a pattern in files using ripgrep (rg) with Python fallback.

    Uses rg when available for 10-50x speed on large codebases,
    .gitignore awareness, binary detection, and Unicode support.
    Falls back to pure Python when rg is not installed.
    """
    import shutil

    try:
        pattern = args.get("pattern", "")
        path = str(args.get("path", ".")).strip().lstrip("@")
        p = os.path.join(project_root, path) if not os.path.isabs(path) else path
        if not pattern:
            return "GREP requires a pattern. Usage: GREP(pattern='def ', path='src')"

        # Try ripgrep first
        rg_path = shutil.which("rg")
        if rg_path:
            return _grep_rg(pattern, p, project_root, rg_path)

        # Fallback to Python
        return _grep_python(pattern, p, project_root)
    except Exception as e:
        return f"GREP error: {e}"


def _grep_rg(pattern: str, path: str, project_root: str, rg_path: str) -> str:
    """Search using ripgrep for maximum speed and accuracy."""
    import shlex

    MAX_MATCHES = 30
    CONTEXT = 2

    # Build rg command
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
            # rg returns exit code 1 when no matches
            return f"GREP: no matches for '{pattern}' in {os.path.relpath(path, project_root)}"

        # Count matches (lines without context markers)
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
        # If rg fails for any reason, fall back to Python
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


def tool_run_command_impl(args: dict, project_root: str) -> str:
    """RUN_COMMAND — execute a shell command."""
    cmd = args.get("cmd", "")
    cmd_clean = cmd.strip()

    # Intercept accidental internal AST tool or Python function calls routed to RUN_COMMAND
    if "get_project_structure" in cmd_clean:
        return tool_search_ast_impl({"action": "structure"}, project_root)

    if cmd_clean.startswith("semantic_search"):
        import re

        match = re.search(
            r'semantic_search\((?:query_string=)?["\'](.*?)["\']', cmd_clean
        )
        q = (
            match.group(1)
            if match
            else cmd_clean.replace("semantic_search", "").strip("() '\"")
        )
        return tool_search_ast_impl({"action": "search", "query": q}, project_root)

    if cmd_clean.startswith("SEARCH_AST"):
        import re

        match = re.search(r"SEARCH_AST\((.*?)\)", cmd_clean, re.IGNORECASE)
        payload = match.group(1) if match else ""
        if "structure" in payload.lower():
            return tool_search_ast_impl({"action": "structure"}, project_root)
        return tool_search_ast_impl(
            {"action": "search", "query": payload}, project_root
        )

    timeout = 180 if any(cmd_clean.startswith(c) for c in _LONG_CMDS) else 30

    try:
        r = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=timeout,
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
        status = "OK" if r.returncode == 0 else f"Exit {r.returncode}"
        return f"{status}\n```\n{output[:3000]}\n```"
    except subprocess.TimeoutExpired:
        return f"Command timed out ({timeout}s). For long installs use a background process."
    except Exception as e:
        return f"Error: {e}"


def tool_web_search_impl(args: dict, project_root: str) -> str:
    """WEB_SEARCH — general web search."""
    query = args.get("query", "")
    try:
        if brave_key := os.getenv("BRAVE_API_KEY"):
            r = httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": brave_key,
                },
                params={"q": query, "count": 5},
                timeout=15,
            )
            r.raise_for_status()
            results = r.json().get("web", {}).get("results", [])
            if results:
                out = "Search Results (Brave):\n\n"
                for res in results:
                    out += f"**{res.get('title', '?')}**\n  {res.get('url', '')}\n  {res.get('description', '')}\n\n"
                return out.strip()
        return _ddg_search(query)
    except Exception as e:
        try:
            return _ddg_search(query)
        except Exception:
            return f"Search error: {e}"


def tool_web_fetch_impl(args: dict, project_root: str) -> str:
    """WEB_FETCH — fetch and return readable content of a URL."""
    url = str(args.get("url") or "").strip()
    if not url:
        return "Fetch error: No URL provided."
    if not url.startswith("http"):
        url = "https://" + url

    def sanitize_web_text(text: str) -> str:
        # Sanitize <tool_call> tags to prevent indirect prompt injection from web pages
        clean = text.replace("<tool_call>", "&lt;tool_call&gt;").replace(
            "</tool_call>", "&lt;/tool_call&gt;"
        )
        return clean[:4000]

    # Tier 1: Reader API (Jina AI)
    try:
        r = httpx.get(
            f"https://r.jina.ai/{url}",
            headers={"Accept": "text/plain"},
            timeout=10,
            follow_redirects=True,
        )
        if r.status_code == 200 and r.text.strip():
            return f"{url}:\n{sanitize_web_text(r.text.strip())}"
    except Exception:
        pass

    # Tier 1 Fallback: Stealth HTTP request with realistic browser headers
    try:
        headers = _get_browser_headers()
        r = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
        if r.status_code == 200 and r.text.strip():
            parser = StructurePreservingHTMLParser()
            parser.feed(r.text)
            parsed_text = parser.get_markdown()
            if parsed_text and len(parsed_text) > 50:
                return f"{url}:\n{sanitize_web_text(parsed_text)}"
    except Exception:
        pass

    # Tier 2: Remote Playwright Headless Browser fallback (for 403, 429, JS SPAs)
    pw_content = _fetch_remote_playwright(url, timeout_ms=8000)
    if pw_content:
        return f"{url} (via Playwright):\n{sanitize_web_text(pw_content)}"

    return (
        f"Fetch error: Unable to retrieve content from {url} (blocked or unreachable)."
    )


def tool_doc_search_impl(args: dict, project_root: str) -> str:
    """DOC_SEARCH — search official documentation."""
    import urllib.parse

    raw_query = args.get("query", "")
    query = _augment_query_with_project_deps(raw_query, project_root)
    search_url, label = _detect_doc_source(query)
    if "duckduckgo" not in label:
        domain = re.search(r"https?://([^/]+)", search_url)
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
                headers={"Accept": "text/plain"},
                timeout=15,
                follow_redirects=True,
            )
            if r.status_code == 200:
                fetch_snippet = f"\nDoc excerpt ({first_url}):\n{r.text.strip()[:1200]}"
        except Exception:
            pass
    return f"DOC_SEARCH — source: {label}\n{'─' * 40}\n" + raw_results + fetch_snippet


def tool_web_verify_impl(args: dict, project_root: str) -> str:
    """WEB_VERIFY — verify code snippet API calls against documentation."""
    snippet = args.get("snippet", "")
    language = args.get("language", "python")
    identifiers = _extract_identifiers(snippet, language)
    if not identifiers:
        return "WEB_VERIFY: no identifiers found in snippet."
    results = [
        f"WEB_VERIFY — language: {language}",
        f"  Snippet: {snippet[:120]}",
        f"  Checking: {', '.join(identifiers[:6])}",
        "─" * 40,
    ]
    for ident in identifiers[:4]:
        query = f"{ident} {language} syntax documentation"
        search_url, label = _detect_doc_source(query)
        domain_m = re.search(r"https?://([^/]+)", search_url)
        ddg_q = (
            f"site:{domain_m.group(1)} {ident}"
            if "duckduckgo" not in label and domain_m
            else f"{ident} {language} documentation"
        )
        status = "UNKNOWN"
        doc_url = ""
        try:
            raw = _ddg_search(ddg_q)
            if ident.lower() in raw.lower():
                status = "VERIFIED"
                for line in raw.splitlines():
                    line = line.strip()
                    if line.startswith("http"):
                        doc_url = line
                        break
            else:
                status = "NOT FOUND IN DOCS"
        except Exception as exc:
            status = f"SEARCH ERROR ({exc})"
        results.append(f"  {ident:<40} {status}")
        if doc_url:
            results.append(f"  -> {doc_url}")
    results += [
        "─" * 40,
        "VERIFIED = identifier appeared in docs search results.",
        "Always read the full doc page before relying on this.",
    ]
    return "\n".join(results)


def tool_save_memory_impl(args: dict, project_root: str) -> str:
    """SAVE_MEMORY — save a fact, decision, or failed strategy to project memory."""
    fact = str(args.get("entry") or args.get("fact", ""))
    category = args.get("category", "decision")
    channel_id = args.get("channel_id", "default")

    if not fact or not fact.strip():
        return "No memory entry provided."
    fact = fact.strip()
    if len(fact) > 300:
        return "Memory entry too long — keep under 300 chars."

    try:
        from ..memory.persistence import ProjectMemory
        from ..memory.models import MemoryObject
        from ..memory.embeddings import tokenize_text
        from datetime import datetime

        pm = ProjectMemory(Path(project_root))
        cat = category.lower()
        mem = pm.load()
        if "arch" in cat or "decision" in cat:
            if fact not in mem.get("arch_decisions", []):
                mem.setdefault("arch_decisions", []).append(fact)
            if fact not in mem.get("decisions", []):
                mem.setdefault("decisions", []).append(fact)
            pm.save(mem)
        elif "fail" in cat or "tried" in cat:
            if fact not in mem.get("tried_and_failed", []):
                mem.setdefault("tried_and_failed", []).append(fact)
            pm.save(mem)
        elif "tech" in cat or "stack" in cat:
            pm.update_tech_stack([fact])
        else:
            pm.update(fact)

        mo = MemoryObject(
            kind=category,
            summary=fact,
            source="SAVE_MEMORY",
            channel_id=channel_id,
            vector_tokens=tokenize_text(fact),
            timestamp=datetime.now(),
        )
        pm.add_memory_object(mo)

        # Also sync active memory manager if initialized
        if _global_memory_mgr is not None:
            _global_memory_mgr.record_memory(
                fact, category=category, channel_id=channel_id
            )

        return f"Saved to project memory ({cat}, channel={channel_id}): '{fact[:100]}'"
    except Exception as e:
        return f"Failed to write memory file: {e}"


def tool_update_task_graph_impl(args: dict, project_root: str) -> str:
    """UPDATE_TASK_GRAPH — dynamically mutate sub-tasks in .torchlight/goal_spec.json."""
    action = (args.get("action") or "").lower().strip()
    task_id = args.get("task_id") or args.get("id", "")
    description = args.get("description") or args.get("desc", "")
    depends_on = args.get("depends_on") or args.get("deps", [])
    target_files = args.get("target_files") or args.get("files", [])

    if not action:
        return "UPDATE_TASK_GRAPH requires 'action' argument (add_subtask, skip_task, update_status)."

    g_path = Path(project_root) / ".torchlight" / "goal_spec.json"
    if not g_path.exists():
        return f"No active goal specification found at {g_path}. Initialize goal first."

    try:
        with open(g_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tasks = data.get("tasks", [])
        phase = args.get("phase")
        task_num = args.get("task_number") or args.get("number")
        if action in ("add_subtask", "add_task"):
            existing_ids = [str(t.get("id") or "") for t in tasks]
            if not task_id:
                from core.tools.task_helpers import _stable_task_id

                task_id = _stable_task_id(existing_ids)
            new_task = {
                "id": task_id,
                "description": description or f"Sub-task {task_id}",
                "task_number": task_num,
                "phase": phase,
                "target_files": target_files
                if isinstance(target_files, list)
                else [target_files],
                "depends_on": depends_on
                if isinstance(depends_on, list)
                else [depends_on],
                "outputs_summary": None,
                "status": "pending",
                "attempts": 0,
                "max_attempts": 3,
                "failure_reasons": [],
                "completed_at": None,
            }
            tasks.append(new_task)
            data["tasks"] = tasks
            with open(g_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            # Mirror into implementation_plan.md + tasks.md so the added subtask
            # survives any subsequent sync (canonical store merge never drops it).
            from core.tools.task_helpers import (
                insert_task_into_plan,
                sync_workspace_tasks,
            )

            insert_task_into_plan(
                project_root, new_task["description"], status="pending"
            )
            sync_workspace_tasks(project_root)
            return f"Successfully added sub-task '{task_id}' to goal spec."

        elif action in ("skip_task", "skip"):
            if not task_id:
                return "UPDATE_TASK_GRAPH action 'skip_task' requires 'task_id'."
            found = False
            task_desc = ""
            from core.tools.task_helpers import _is_task_match
            for t in tasks:
                t_num = str(t.get("task_number") or "")
                if t.get("id") == task_id or t.get("description") == task_id or (t_num and t_num == str(task_id)) or _is_task_match(str(task_id), str(t.get("description") or "")):
                    t["status"] = "skipped"
                    task_desc = t.get("description") or t.get("id")
                    found = True
                    break
            if not found:
                return f"Task '{task_id}' not found in goal spec."
            with open(g_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            from core.tools.task_helpers import mark_task_status

            mark_task_status(project_root, task_desc or task_id, status="skipped")
            return f"Task '{task_id}' marked as SKIPPED."

        elif action in ("update_status", "status"):
            status_val = args.get("status", "pending")
            found = False
            task_desc = ""
            from core.tools.task_helpers import _is_task_match
            for t in tasks:
                t_num = str(t.get("task_number") or "")
                if t.get("id") == task_id or t.get("description") == task_id or (t_num and t_num == str(task_id)) or _is_task_match(str(task_id), str(t.get("description") or "")):
                    t["status"] = status_val
                    task_desc = t.get("description") or t.get("id")
                    found = True
                    break
            if not found:
                return f"Task '{task_id}' not found in goal spec."
            with open(g_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            from core.tools.task_helpers import mark_task_status

            mark_task_status(project_root, task_desc or task_id, status=status_val)
            return f"Task '{task_id}' status updated to '{status_val}'."

        else:
            return f"Unsupported UPDATE_TASK_GRAPH action: {action}. Supported: add_subtask, skip_task, update_status."

    except Exception as e:
        return f"Failed to update task graph: {e}"


def tool_format_code_impl(args: dict, project_root: str) -> str:
    """FORMAT_CODE — beautify a code snippet."""
    snippet = args.get("snippet", "")
    language = args.get("language", "python")
    if language.lower() in ("python", "py"):
        try:
            import black

            return black.format_str(snippet, mode=black.Mode())
        except ImportError:
            return f"'black' not installed. Returning raw snippet:\n{snippet}"
    return snippet


def tool_verify_impl(args: dict, project_root: str) -> str:
    """VERIFY — verify a file exists and optionally contains expected content or compiles.

    `compile: true` runs the same syntax + compile gates used by WRITE_FILE/EDIT_FILE,
    letting the agent self-check before reporting completion.
    """
    try:
        path = args.get("path", "")
        expected_snippet = args.get("expected_snippet")
        do_compile = bool(args.get("compile", False))
        p = os.path.join(project_root, path) if not os.path.isabs(path) else path
        if not os.path.exists(p):
            return f"Verification FAILED: File does not exist at {path}"
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        notes = []
        if expected_snippet:
            if expected_snippet in content:
                notes.append("expected content found")
            else:
                return f"Verification WARNING: File exists but expected snippet was NOT found in {path}"
        if do_compile:
            syntax_note = _check_syntax(content, p)
            if syntax_note:
                detail = syntax_note.replace("\n⚠️ Syntax Warning", "").strip()
                return f"Verification FAILED: Syntax error in {path}: {detail}"
            compile_note = _check_compile(content, p, project_root)
            if compile_note:
                return f"Verification FAILED: Syntax error in {path}: {compile_note}"
            notes.append("compile check passed")
        suffix = (f" ({'; '.join(notes)})") if notes else ""
        return f"Verification SUCCESS: File exists at {path}{suffix}"
    except Exception as e:
        return f"Verification ERROR: {e}"


def tool_ask_user_impl(args: dict, project_root: str) -> str:
    """ASK_USER — ask the user a question with structured options and custom input."""
    questions_list = args.get("questions")
    if isinstance(questions_list, list) and questions_list:
        lines = ["[AWAITING USER INPUT] Multiple questions for review:"]
        for q_idx, q in enumerate(questions_list, 1):
            q_text = q.get("question", f"Question {q_idx}")
            q_opts = q.get("options", [])
            is_m = bool(q.get("is_multi_select", False))
            opt_type = "Checkbox (Multi-Select)" if is_m else "Radio (Single Choice)"
            lines.append(f"\n{q_idx}. {q_text} [{opt_type}]")
            for idx, opt in enumerate(q_opts, 1):
                marker = "[ ]" if is_m else "( )"
                lines.append(f"  {marker} {idx}. {opt}")
        if args.get("allow_custom_input", True):
            lines.append("\n  [ ] Custom text input / feedback (reply with your answers)")
        return "\n".join(lines)

    question = args.get("question", "")
    options = args.get("options", [])
    is_multi = bool(args.get("is_multi_select", False))
    allow_custom = bool(args.get("allow_custom_input", True))

    lines = [f"[AWAITING USER INPUT] {question}"]
    if options and isinstance(options, list):
        opt_type = "Checkbox (Multi-Select)" if is_multi else "Radio (Single Choice)"
        lines.append(f"Input Type: {opt_type}")
        for idx, opt in enumerate(options, 1):
            marker = "[ ]" if is_multi else "( )"
            lines.append(f"  {marker} {idx}. {opt}")
        if allow_custom:
            marker = "[ ]" if is_multi else "( )"
            lines.append(f"  {marker} {len(options) + 1}. Custom text input (reply with your own answer)")
    return "\n".join(lines)


def tool_set_phase_impl(args: dict, project_root: str) -> str:
    """SET_PHASE — switch active agent phase."""
    phase = str(args.get("phase", "code")).lower().strip()
    reason = args.get("reason", "")
    reason_str = f" Reason: {reason}" if reason else ""
    return f"Agent phase switched to '{phase}' successfully.{reason_str}"


# ── GIT tool ────────────────────────────────────────────────────────────────

_GIT_SAFE_SUBCOMMANDS = {
    "status",
    "log",
    "diff",
    "show",
    "branch",
    "stash",
    "remote",
    "ls-files",
    "rev-parse",
    "describe",
    "blame",
    "shortlog",
}
_GIT_WRITE_SUBCOMMANDS = {"add", "restore", "stash", "checkout", "switch"}
_GIT_DESTRUCTIVE_SUBCOMMANDS = {"push", "reset", "rebase", "merge", "clean", "drop"}


def _git_run(cmd: str, project_root: str, timeout: int = 30) -> tuple[bool, str]:
    """Run a git command and return (success, output)."""
    try:
        r = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=timeout,
        )
        output = (r.stdout or "").strip()
        if r.stderr:
            err = r.stderr.strip()
            if err and not output:
                output = err
        return r.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, f"Git command timed out ({timeout}s)"
    except Exception as e:
        return False, f"Git error: {e}"


def tool_git_impl(args: dict, project_root: str) -> str:
    """GIT — execute git operations with safety classification.

    Supported subcommands:
      status  — working tree status
      diff    — show changes (optional: path, staged)
      log     — commit history (optional: count, path)
      show    — show a commit (optional: ref)
      branch  — list branches (optional: pattern)
      blame   — line-by-line blame (optional: path)
      commit  — stage and commit (optional: message, files)
      add     — stage files (optional: files, all)
      restore — restore files (optional: files, staged)
      stash   — stash changes (optional: action: push/pop/drop/list)
      remote  — list remotes
      shortlog — summary of contributors
    """
    subcommand = (args.get("subcommand") or args.get("cmd") or "status").strip().lower()
    message = args.get("message") or args.get("msg") or ""
    files = args.get("files") or args.get("path") or ""
    flag = args.get("flag") or ""
    staged = args.get("staged", False)
    count = args.get("count") or args.get("n") or ""

    # Check if git repo exists (auto-heal/provision if missing)
    ok, _ = _git_run("git rev-parse --is-inside-work-tree", project_root)
    if not ok:
        try:
            from ..memory.persistence import ensure_git_repository

            ensure_git_repository(project_root)
            ok, _ = _git_run("git rev-parse --is-inside-work-tree", project_root)
        except Exception:
            pass
        if not ok:
            return (
                "Not a git repository. Use RUN_COMMAND('git init') to initialize one."
            )

    # Safety check
    if subcommand in _GIT_DESTRUCTIVE_SUBCOMMANDS:
        return (
            f"DESTRUCTIVE: git {subcommand} requires explicit user approval.\n"
            f"Ask the user to confirm this operation."
        )

    # Build command
    if subcommand == "status":
        cmd = "git status --short"
    elif subcommand == "diff":
        parts = ["git diff"]
        if staged:
            parts.append("--staged")
        if files:
            parts.append(f"-- {files}")
        if flag:
            parts.append(flag)
        cmd = " ".join(parts)
    elif subcommand == "log":
        n = count or "10"
        parts = [f"git log --oneline -{n}"]
        if files:
            parts.append(f"-- {files}")
        if flag:
            parts.append(flag)
        cmd = " ".join(parts)
    elif subcommand == "show":
        ref = flag or "HEAD"
        cmd = f"git show --stat {ref}"
    elif subcommand == "branch":
        pattern = flag or ""
        cmd = f"git branch -a {pattern}".strip()
    elif subcommand == "blame":
        if not files:
            return "GIT blame requires a file path. Usage: GIT(subcommand='blame', files='path/to/file.py')"
        cmd = f"git blame {files}"
    elif subcommand == "commit":
        if not message:
            return "GIT commit requires a message. Usage: GIT(subcommand='commit', message='fix: ...', files='file.py')"
        parts = []
        if files:
            parts.append(f"git add {files}")
            parts.append("&&")
        parts.append(f'git commit -m "{message}"')
        cmd = " ".join(parts)
    elif subcommand == "add":
        target = files or flag or "."
        cmd = f"git add {target}"
    elif subcommand == "restore":
        target = files or flag or "."
        parts = ["git restore"]
        if staged:
            parts.append("--staged")
        parts.append(target)
        cmd = " ".join(parts)
    elif subcommand == "stash":
        action = flag or "push"
        if action == "list":
            cmd = "git stash list"
        elif action == "pop":
            cmd = "git stash pop"
        elif action == "drop":
            cmd = "git stash drop"
        else:
            cmd = "git stash push -m 'torchlight stash'"
    elif subcommand == "remote":
        cmd = "git remote -v"
    elif subcommand == "shortlog":
        cmd = "git shortlog -sn --all"
    else:
        return f"Unknown git subcommand: '{subcommand}'. Supported: {', '.join(sorted(_GIT_SAFE_SUBCOMMANDS | _GIT_WRITE_SUBCOMMANDS))}"

    ok, output = _git_run(cmd, project_root)
    if not output:
        output = "(no output)"

    # Truncate very long output
    if len(output) > 4000:
        lines = output.splitlines()
        output = "\n".join(lines[:80]) + f"\n... [{len(lines)} total lines, truncated]"

    status_icon = "✅" if ok else "⚠️"
    return f"{status_icon} git {subcommand}:\n{output}"


def tool_search_ast_impl(args: dict, project_root: str) -> str:
    """Query AST Knowledge Graph (search, path, subgraph, structure, update, summary)."""
    query = str(args.get("query", "")).strip().lstrip("@")
    action = str(args.get("action", "search")).strip().lower()
    top_k = int(args.get("top_k", 5))

    from core.flashlight.graph_engine import get_project_graph
    from core.utils.image_utils import is_image_file

    if query and is_image_file(query):
        return f"ℹ️ '{os.path.basename(query)}' is an image file and does not contain AST code symbols. Visual context is attached for vision models, or use VIEW_IMAGE to inspect."

    graph = get_project_graph(project_root)

    if action in ("update", "reindex", "build"):
        gdict = graph.build()
        return f"✅ AST Graph re-indexed successfully: {gdict['node_count']} nodes, {gdict['edge_count']} edges saved to `.torchlight/graph.json`."
    elif action in (
        "search",
        "query",
        "semantic",
        "signature",
        "signatures",
        "symbol",
        "symbols",
        "definition",
        "definitions",
    ):
        if not query:
            return graph.get_structure()
        res = graph.query(query, top_k=top_k)
        if "No AST graph nodes found" in res:
            # Refresh graph to capture any new or edited files on disk
            graph.build()
            rebuilt_res = graph.query(query, top_k=top_k)
            if "No AST graph nodes found" not in rebuilt_res:
                return rebuilt_res
            if query.lower() in ("main", "app", "index", "root"):
                return graph.get_structure()
            # Auto-fallback to READ_SYMBOLS to surface signatures without forcing full READ_FILE
            possible_file = os.path.join(project_root, query) if not os.path.isabs(query) else query
            if os.path.exists(possible_file) or "." in query or "/" in query or "\\" in query:
                sym_res = tool_read_symbols_impl({"path": query}, project_root)
                if not sym_res.startswith("Error") and "File not found" not in sym_res and "requires a file path" not in sym_res:
                    return f"AST Node search fallback (READ_SYMBOLS for {query}):\n{sym_res}"
            return rebuilt_res
        return res
    elif action in ("path", "find_path"):
        target = str(args.get("target", args.get("to", ""))).strip().lstrip("@")
        if not target and "," in query:
            parts = query.split(",", 1)
            query, target = parts[0].strip().lstrip("@"), parts[1].strip().lstrip("@")
        res = graph.find_path(query, target)
        if "Path search failed" in res:
            graph.build()
            return graph.find_path(query, target)
        return res
    elif action in ("subgraph", "sub_graph", "deps", "depend", "dependencies", "graph"):
        res = graph.get_subgraph(query)
        if "not found in AST index" in res:
            graph.build()
            return graph.get_subgraph(query)
        return res
    elif action in ("structure", "project", "get_project_structure", "get_structure"):
        return graph.get_structure()
    elif action in ("summary", "info"):
        return f"Project AST Graph: {graph.graph_file}\nNodes: {len(graph.nodes)} | Edges: {len(graph.edges)}"
    else:
        res = graph.query(query, top_k=top_k)
        if "No AST graph nodes found" in res:
            graph.build()
            rebuilt_res = graph.query(query, top_k=top_k)
            if "No AST graph nodes found" not in rebuilt_res:
                return rebuilt_res
            possible_file = os.path.join(project_root, query) if not os.path.isabs(query) else query
            if os.path.exists(possible_file) or "." in query or "/" in query:
                sym_res = tool_read_symbols_impl({"path": query}, project_root)
                if not sym_res.startswith("Error") and "File not found" not in sym_res and "requires a file path" not in sym_res:
                    return f"AST Node search fallback (READ_SYMBOLS for {query}):\n{sym_res}"
            return rebuilt_res
        return res


def tool_inspect_web_impl(args: dict, project_root: str) -> str:
    """Inspect runtime outcome of HTML/JS/CSS web pages or Canvas games."""
    path = str(args.get("path", "")).strip()
    wait_ms = int(args.get("wait_ms", 1500))
    interact = args.get("interact")

    if not path:
        return "INSPECT_WEB requires 'path' parameter."

    from pathlib import Path

    full_path = (
        Path(project_root) / path if not Path(path).is_absolute() else Path(path)
    )

    try:
        from core.execution.web_inspector import WebOutcomeInspector

        inspector = WebOutcomeInspector(
            output_dir=Path(project_root) / ".torchlight" / "screenshots"
        )
        res = inspector.inspect(
            file_path=str(full_path)
            if not path.startswith(("http://", "https://"))
            else path,
            wait_ms=wait_ms,
            interact=interact,
        )
        return res.to_markdown()
    except Exception as e:
        return f"Error during web outcome inspection: {e}"


def tool_play_and_verify_game_impl(args: dict, project_root: str) -> str:
    """Plays an HTML game autonomously, analyzing frame buffers and runtime events."""
    path = str(args.get("path", "")).strip()
    duration_ms = int(args.get("duration_ms", args.get("wait_ms", 3000)))
    return play_and_verify_game(
        path=path, duration_ms=duration_ms, project_root=project_root
    )


def tool_self_improve_game_impl(args: dict, project_root: str) -> str:
    """Executes closed-loop autonomous repair and verification on an HTML game."""
    path = str(args.get("path", "")).strip()
    max_iterations = int(args.get("max_iterations", 3))
    duration_ms = int(args.get("duration_ms", 2500))
    return self_improve_game(
        path=path,
        max_iterations=max_iterations,
        duration_ms=duration_ms,
        project_root=project_root,
    )


def play_and_verify_game(
    path: str = "",
    duration_ms: int = 3000,
    project_root: str = ".",
    **kwargs: Any,
) -> str:
    """Plays an HTML game autonomously, analyzing frame buffers and runtime events."""
    if not path:
        return "PLAY_AND_VERIFY_GAME requires 'path' parameter."

    from pathlib import Path

    full_path = (
        Path(project_root) / path if not Path(path).is_absolute() else Path(path)
    )

    try:
        from core.execution.game_inspector import HtmlGamePlayer

        player = HtmlGamePlayer(
            output_dir=Path(project_root) / ".torchlight" / "screenshots"
        )
        res = player.play_and_verify(
            file_path=str(full_path)
            if not path.startswith(("http://", "https://"))
            else path,
            duration_ms=duration_ms,
        )
        return res.to_markdown()
    except Exception as e:
        return f"Error playing and verifying HTML game: {e}"


def self_improve_game(
    path: str = "",
    max_iterations: int = 3,
    duration_ms: int = 2500,
    project_root: str = ".",
    **kwargs: Any,
) -> str:
    """Executes closed-loop autonomous repair and verification on an HTML game."""
    if not path:
        return "SELF_IMPROVE_GAME requires 'path' parameter."

    from pathlib import Path

    full_path = (
        Path(project_root) / path if not Path(path).is_absolute() else Path(path)
    )

    try:
        from core.execution.game_self_improver import GameSelfImprover

        improver = GameSelfImprover(project_root=Path(project_root))
        report = improver.run_self_improvement_cycle(
            file_path=str(full_path),
            max_iterations=max_iterations,
            duration_ms=duration_ms,
        )
        return report.to_markdown()
    except Exception as e:
        return f"Error executing HTML game self-improvement cycle: {e}"


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

    # Security check
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

    # Record in active memory if available
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
