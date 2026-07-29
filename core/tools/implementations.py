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
from pathlib import Path
from typing import Optional, Tuple
from html.parser import HTMLParser

import httpx


# ── Constants ──────────────────────────────────────────────────────────────

_MAX_TOOL_OUTPUT = 4000
_SAFE_COMMANDS_SET = {
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
    "node --version", "python --version", "python3 --version",
    "tree",
}

_LONG_CMDS = ("pip install", "pip3 install", "npm install", "yarn", "cargo build",
              "gradle", "./gradlew", "mvn ", "make ", "cmake")


# ── Symbol extraction patterns ────────────────────────────────────────────

_SYM_PATTERNS = [
    (re.compile(r'^(?:async )?def\s+(\w+)\s*\(', re.MULTILINE), "fn"),
    (re.compile(r'^class\s+(\w+)[:(]', re.MULTILINE), "class"),
    (re.compile(r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)', re.MULTILINE), "fn"),
    (re.compile(r'^(?:export\s+)?class\s+(\w+)', re.MULTILINE), "class"),
    (re.compile(r'^\s*(?:pub\s+)?fn\s+(\w+)', re.MULTILINE), "fn"),
    (re.compile(r'^\s*(?:fun)\s+(\w+)\s*\(', re.MULTILINE), "fn"),
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


def _truncate(text: str, limit: int = _MAX_TOOL_OUTPUT) -> str:
    if len(text) > limit:
        return text[:limit] + f"\n... [Truncated at {limit} chars]"
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
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    resp = httpx.post(
        "https://html.duckduckgo.com/html/", data={"q": q, "kl": "us-en"},
        headers=headers, timeout=15, follow_redirects=True,
    )
    resp.raise_for_status()

    def strip_tags(s):
        return re.sub(r"<[^>]+>", "", s).strip()

    raw = resp.text
    titles = [strip_tags(t) for t in re.findall(r'class="result__a"[^>]*>(.*?)</a>', raw, re.DOTALL)]
    urls_raw = [strip_tags(u).strip() for u in re.findall(r'class="result__url"[^>]*>(.*?)</div>', raw, re.DOTALL)]
    snippets = [strip_tags(s) for s in re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', raw, re.DOTALL)]

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
    """
    def __init__(self):
        super().__init__()
        self.output = []
        self.in_code = False
        self.in_heading = False
        self.in_skip = False
        self.skip_tags = {"script", "style", "nav", "footer", "header", "noscript", "svg"}

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in self.skip_tags:
            self.in_skip = True
        elif tag_lower in ("pre", "code"):
            self.in_code = True
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
            self.in_skip = False
        elif tag_lower in ("pre", "code"):
            self.in_code = False
            self.output.append("\n```\n")
        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.in_heading = False
            self.output.append("\n")

    def handle_data(self, data):
        if self.in_skip:
            return
        if self.in_code:
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
                browser.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).debug(f"Playwright remote fetch failed for {url}: {e}")
    return None


def _augment_query_with_project_deps(query: str, project_root: str) -> str:
    """Inspects project dependencies (pyproject.toml, package.json, Cargo.toml) to lock doc query versions."""
    if not project_root or not os.path.exists(project_root):
        return query

    query_lower = query.lower()
    root_path = Path(project_root)

    # Check pyproject.toml
    pyproject = root_path / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8", errors="ignore")
            for pkg, ver in re.findall(r'([\w\-]+)\s*=\s*["\'][\^~>=]*(\d+\.\d+)', content):
                if pkg.lower() in query_lower:
                    major = ver.split('.')[0]
                    if f"v{major}" not in query_lower and major not in query_lower:
                        return f"{query} v{major}"
        except Exception:
            pass

    # Check package.json
    pkg_json = root_path / "package.json"
    if pkg_json.exists():
        try:
            content = pkg_json.read_text(encoding="utf-8", errors="ignore")
            for pkg, ver in re.findall(r'"([\w\-@/]+)"\s*:\s*"[\^~>=]*(\d+\.\d+)', content):
                pkg_name = pkg.split('/')[-1]
                if pkg_name.lower() in query_lower:
                    major = ver.split('.')[0]
                    if f"v{major}" not in query_lower and major not in query_lower:
                        return f"{query} v{major}"
        except Exception:
            pass

    return query


def _extract_identifiers(snippet: str, language: str) -> list:
    if language in ("python", "py"):
        calls = re.findall(r'([\w]+(?:\.[\w]+)+)\s*\(', snippet)
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


# ══════════════════════════════════════════════════════════════════════════
# Tool implementations
# ══════════════════════════════════════════════════════════════════════════

def tool_read_file_impl(args: dict, project_root: str) -> str:
    """READ_FILE — read a file with optional line-range or symbol syntax."""
    try:
        path = (args.get("path") or "").strip()
        if not path:
            return "READ_FILE requires a file path. Use RUN_COMMAND('ls') to see directory contents."

        # Parse optional :N-M or :SymbolName suffix
        range_start = None
        range_end = None
        symbol_name = None

        m_range = re.match(r'^(.+?)\s*:\s*(\d+)-(\d+)\s*$', path)
        m_line = re.match(r'^(.+?)\s*:\s*(\d+)\s*$', path)
        m_sym = re.match(r'^(.+?)\s*:\s*([A-Za-z_]\w*)\s*$', path)

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
            return f"File not found: {path}. Use RUN_COMMAND('ls') to verify."

        if os.path.isdir(p):
            return f"{path} is a directory. Use RUN_COMMAND('ls {path}') to list it."

        # Image file rejection
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg", ".tiff"}
        ext = os.path.splitext(p)[1].lower()
        if ext in image_extensions:
            return f"Cannot read image file: {os.path.basename(p)}."

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
                trunc_note = f"\n... (capped at {MAX_LINES} lines — use a tighter range)"
            else:
                trunc_note = ""
            display = "\n".join(sl)[:MAX_CHARS]
            return (
                f"{fname} lines {r0+1}–{r0+len(sl)} (of {nlines} total)\n"
                f"```{ext}\n{display}{trunc_note}\n```"
            )

        # Default: symbol map + top-N lines
        sym_hdr = _symbol_map(content, fname)
        display = "\n".join(lines[:MAX_LINES])[:MAX_CHARS]
        truncated = nlines > MAX_LINES or len(content) > MAX_CHARS
        suffix = (
            f"\n... ({nlines - MAX_LINES} more lines)"
            f' — use READ_FILE("{path}:N-M") for a range,'
            f' or READ_FILE("{path}:<SYMBOL>") to jump to a function.'
        ) if truncated else ""

        return (
            f"{sym_hdr}"
            f"{fname} ({nlines} lines)\n"
            f"```{ext}\n{display}{suffix}\n```"
        )

    except Exception as e:
        return f"Error reading file: {e}"


def _normalize_whitespace(content: str, filename: str = "") -> str:
    """Normalize mixed tabs to spaces (except Makefiles/TSV/Go), remove trailing line spaces, and ensure trailing newline."""
    if not content:
        return ""
    ext = os.path.splitext(filename)[1].lower() if filename else ""
    basename = os.path.basename(filename).lower() if filename else ""
    preserve_tabs = ext in (".go", ".tsv", ".tab", ".mk") or basename in ("makefile", "gnumakefile")

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
        (r'#\s*TODO:?\s*(?:implement|add logic|fill in)', "Python TODO stub"),
        (r'#\s*\.\.\.\s*(?:rest|existing|code|remaining)', "Python code truncation stub"),
        (r'//\s*\.\.\.\s*(?:rest|existing|code|implementation|remaining)', "JS/C code truncation stub"),
        (r'/\*\s*\.\.\.\s*(?:rest|existing|code|remaining)\s*\*/', "C-style block stub"),
        (r'pass\s*#\s*(?:stub|implement|todo|fill)', "Python pass stub"),
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
                input=content, text=True, capture_output=True, timeout=2, cwd=project_root
            )
            if res.returncode == 0 and res.stdout:
                return res.stdout
        except Exception:
            pass
        try:
            res = subprocess.run(
                ["black", "-q", "-"],
                input=content, text=True, capture_output=True, timeout=2, cwd=project_root
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
                    input=content, text=True, capture_output=True, timeout=2, cwd=project_root
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
                input=content, text=True, capture_output=True, timeout=2, cwd=project_root
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
                input=content, text=True, capture_output=True, timeout=2, cwd=project_root
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
        try:
            json.loads(content)
        except json.JSONDecodeError as je:
            return f"\n⚠️ JSON Syntax Warning (line {je.lineno}, col {je.colno}): {je.msg}"
        except Exception as e:
            return f"\n⚠️ JSON Syntax Warning: {e}"

    # 3. Basic bracket balance check for JS/TS/C-like languages (filtering strings and comments)
    elif ext in (".js", ".ts", ".jsx", ".tsx", ".c", ".cpp", ".java"):
        # Strip comments and string literals to prevent false positives on bracket matching
        cleaned = re.sub(r'//.*', '', content)
        cleaned = re.sub(r'/\*[\s\S]*?\*/', '', cleaned)
        cleaned = re.sub(r'([\'"`])(?:\\.|[^\\])*?\1', '', cleaned)

        stack = []
        matching = {')': '(', '}': '{', ']': '['}
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



def tool_write_file_impl(args: dict, project_root: str) -> str:
    """WRITE_FILE — create or overwrite a file."""
    if not isinstance(args, dict):
        args = {"raw": str(args)}

    path_raw = (
        args.get("path") or args.get("file") or args.get("filepath")
        or args.get("filename") or args.get("dest") or args.get("target") or args.get("p")
    )

    content = args.get("content")
    if content is None:
        content = args.get("code") or args.get("text") or args.get("data") or ""

    # Fallback: extract from raw string
    if not path_raw and "raw" in args:
        raw_text = str(args["raw"])
        p_match = re.search(r'["\']?(?:path|file|filename|filepath)["\']?\s*:\s*["\']([^"\']+)["\']', raw_text)
        if p_match:
            path_raw = p_match.group(1)
        c_match = re.search(r'["\']?(?:content|code|text)["\']?\s*:\s*["\']([\s\S]*)["\']\s*\}?$', raw_text)
        if c_match:
            content = c_match.group(1)

    if not path_raw or not str(path_raw).strip():
        return "Error: Missing required 'path' parameter for WRITE_FILE."

    path_str = str(path_raw).strip()
    p = os.path.join(project_root, path_str) if not os.path.isabs(path_str) else path_str

    if os.path.isdir(p):
        return f"Error: Specified path '{path_str}' is a directory, not a file."

    try:
        parent_dir = os.path.dirname(p)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        formatted_content = _format_code_on_save(content, p, project_root)
        if formatted_content != content:
            content = formatted_content
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        syntax_note = _check_syntax(content, p) or ""
        stub_note = _detect_stubs(content) or ""
        return f"Written {line_count} lines to {p}{syntax_note}{stub_note}"
    except Exception as e:
        return f"Error writing {p}: {e}"



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
    search_match = re.search(r'<<<<<<<(?:[ \t]*SEARCH)?\r?\n', text)
    if search_match:
        after_search = text[search_match.end():]
        # Option A: Standard divider =======
        div_match = re.search(r'\r?\n=======\r?\n', after_search)
        if div_match:
            search_part = after_search[:div_match.start()]
            after_div = after_search[div_match.end():]
            end_match = re.search(r'\r?\n>>>>>>>(?:[ \t]*REPLACE)?(?:$|\r?\n)', after_div)
            if end_match:
                replace_part = after_div[:end_match.start()]
                return _clean_segment(search_part), _clean_segment(replace_part)
            else:
                end_match2 = re.search(r'>>>>>>>(?:[ \t]*REPLACE)?', after_div)
                if end_match2:
                    replace_part = after_div[:end_match2.start()]
                    return _clean_segment(search_part), _clean_segment(replace_part)

        # Option B: Model used >>>>>>> as divider between SEARCH block and REPLACE block
        div_alt = re.search(r'\r?\n>>>>>>>(?:[ \t]*SEARCH)?\r?\n', after_search)
        if div_alt:
            search_part = after_search[:div_alt.start()]
            after_div = after_search[div_alt.end():]
            end_match = re.search(r'\r?\n>>>>>>>(?:[ \t]*REPLACE)?', after_div)
            if end_match:
                replace_part = after_div[:end_match.start()]
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

    return None, None


def _get_symbol_bounds_ast(content: str, symbol_name: str) -> Optional[Tuple[int, int]]:
    """Helper to locate exact start and end line bounds for an AST symbol in Python source code."""
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = node.name
                if name == symbol_name or symbol_name.endswith(f".{name}") or f".{name}" in symbol_name:
                    start = getattr(node, "lineno", None)
                    end = getattr(node, "end_lineno", None)
                    if start and end:
                        return start, end
    except Exception:
        pass
    return None


def tool_edit_file_impl(args: dict, project_root: str) -> str:
    """EDIT_FILE — surgically replace a block of text in a file with multi-tiered resilient matching."""
    try:
        # Multi-chunk batch edit processing
        chunks = args.get("chunks") or args.get("replacements") or args.get("edits")
        if chunks and isinstance(chunks, list) and len(chunks) > 0:
            results = []
            for idx, chunk in enumerate(chunks):
                if isinstance(chunk, dict):
                    chunk_args = dict(args)
                    chunk_args.pop("chunks", None)
                    chunk_args.pop("replacements", None)
                    chunk_args.pop("edits", None)
                    chunk_args.update(chunk)
                    res = tool_edit_file_impl(chunk_args, project_root)
                    results.append(f"Chunk {idx+1}: {res}")
            return "\n".join(results)

        path = args.get("path", "")
        old_text = args.get("old_text", "")
        new_text = args.get("new_text", "")
        diff_text = args.get("diff") or args.get("block") or args.get("diff_block") or ""
        start_line = args.get("start_line") or args.get("start")
        end_line = args.get("end_line") or args.get("end")
        symbol_name = args.get("symbol") or args.get("symbol_name") or args.get("function")

        # Parse line range suffix from path (e.g. "path/to/file.py:20-45")
        if ":" in path and not os.path.exists(os.path.join(project_root, path) if not os.path.isabs(path) else path):
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

        # Check for Aider-style Search/Replace blocks in diff, old_text, or raw inputs
        diff_attempted = False
        for candidate in [diff_text, old_text, args.get("content", ""), args.get("raw", "")]:
            if candidate and any(m in str(candidate) for m in ["<<<<<<<", "SEARCH", "=======", ">>>>>>>"]):
                diff_attempted = True
                s_parsed, r_parsed = _parse_diff_block(str(candidate))
                if s_parsed is not None and r_parsed is not None:
                    old_text = s_parsed
                    new_text = r_parsed
                    diff_attempted = False
                    break

        if not path:
            return "EDIT_FILE requires a file path."

        p = os.path.join(project_root, path) if not os.path.isabs(path) else path
        if not os.path.exists(p):
            return f"File not found: {path}"

        with open(p, "r", encoding="utf-8") as f:
            content = f.read()

        # AST Symbol-anchored replacement mode
        if symbol_name:
            bounds = _get_symbol_bounds_ast(content, str(symbol_name))
            if bounds:
                s_l, e_l = bounds
                lines = content.splitlines(keepends=True)
                new_content = "".join(lines[:s_l-1]) + new_text
                if new_text and not new_text.endswith("\n") and e_l < len(lines):
                    new_content += "\n"
                new_content += "".join(lines[e_l:])
                formatted_content = _format_code_on_save(new_content, p, project_root)
                if formatted_content != new_content:
                    new_content = formatted_content
                with open(p, "w", encoding="utf-8") as f:
                    f.write(new_content)
                syntax_note = _check_syntax(new_content, p) or ""
                stub_note = _detect_stubs(new_content) or ""
                return f"Surgically replaced symbol '{symbol_name}' in {path} (lines {s_l}-{e_l}).{syntax_note}{stub_note}"

        # Line-bounded search window handling
        if start_line is not None and end_line is not None:
            try:
                s_l = max(1, int(start_line))
                e_l = int(end_line)
                lines = content.splitlines(keepends=True)
                s_idx = s_l - 1
                e_idx = min(len(lines), e_l)
                target_slice = "".join(lines[s_idx:e_idx])
                if old_text and old_text in target_slice:
                    new_slice = target_slice.replace(old_text, new_text, 1)
                    new_content = "".join(lines[:s_idx]) + new_slice + "".join(lines[e_idx:])
                else:
                    new_content = "".join(lines[:s_idx]) + new_text
                    if new_text and not new_text.endswith("\n") and e_idx < len(lines):
                        new_content += "\n"
                    new_content += "".join(lines[e_idx:])
                formatted_content = _format_code_on_save(new_content, p, project_root)
                if formatted_content != new_content:
                    new_content = formatted_content
                with open(p, "w", encoding="utf-8") as f:
                    f.write(new_content)
                syntax_note = _check_syntax(new_content, p) or ""
                stub_note = _detect_stubs(new_content) or ""
                return f"Surgically edited {path} within line range {s_l}-{e_l}.{syntax_note}{stub_note}"
            except ValueError:
                pass

        if not old_text or diff_attempted:
            if diff_attempted:
                return (
                    "Edit failed: Malformed diff block syntax in 'diff'. Could not locate valid SEARCH block, '=======' divider, and '>>>>>>> REPLACE' footer.\n"
                    "Ensure your diff block follows this exact format:\n"
                    "<<<<<<< SEARCH\n"
                    "<exact text to replace>\n"
                    "=======\n"
                    "<new replacement text>\n"
                    ">>>>>>> REPLACE\n\n"
                    "Or use exact JSON arguments: {\"path\": \"file.py\", \"old_text\": \"...\", \"new_text\": \"...\"}"
                )
            return "EDIT_FILE requires old_text (or a <<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE block) to find, or line range (start_line/end_line). To overwrite full file, use WRITE_FILE."
        if new_text == old_text:
            return "No change: old_text and new_text are identical."

        # Handle unescaped literal \\n and \\t from raw JSON outputs
        if "\\n" in old_text and "\n" not in old_text:
            old_text = old_text.replace("\\n", "\n").replace("\\t", "\t")
        if "\\n" in new_text and "\n" not in new_text:
            new_text = new_text.replace("\\n", "\n").replace("\\t", "\t")

        # Tier 1: Exact string match
        if old_text in content:
            count = content.count(old_text)
            if count > 1:
                return f"Edit failed: 'old_text' matches {count} locations. Provide line numbers (start_line/end_line) or more context to make it unique."

            new_content = content.replace(old_text, new_text)
            formatted_content = _format_code_on_save(new_content, p, project_root)
            if formatted_content != new_content:
                new_content = formatted_content
            with open(p, "w", encoding="utf-8") as f:
                f.write(new_content)

            syntax_note = _check_syntax(new_content, p) or ""
            stub_note = _detect_stubs(new_content) or ""
            return f"Surgically edited {path} (replaced {len(old_text)} chars with {len(new_text)} chars).{syntax_note}{stub_note}"


        # Helper: Normalize lines for line-based matching
        def normalize_line(l):
            return l.strip()

        content_lines = content.splitlines(keepends=True)

        # Tier 2: Fuzzy whitespace-agnostic line matching
        old_norm = [normalize_line(l) for l in old_text.splitlines() if normalize_line(l)]
        if not old_norm:
            return "Edit failed: 'old_text' is empty or contains only whitespace."

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
            return f"Edit failed: 'old_text' fuzzy-matches {matches_found} locations. Provide line numbers (start_line/end_line) or more context."

        if best_start != -1:
            new_content = "".join(content_lines[:best_start]) + new_text
            if new_text and not new_text.endswith("\n") and best_end < len(content_lines):
                new_content += "\n"
            new_content += "".join(content_lines[best_end:])

            formatted_content = _format_code_on_save(new_content, p, project_root)
            if formatted_content != new_content:
                new_content = formatted_content
            with open(p, "w", encoding="utf-8") as f:
                f.write(new_content)
            syntax_note = _check_syntax(new_content, p) or ""
            stub_note = _detect_stubs(new_content) or ""
            return f"Surgically edited {path} (fuzzy replaced {len(old_norm)} lines ignoring whitespace).{syntax_note}{stub_note}"

        # Tier 3: Ellipsis / Wildcard matching (e.g. header \n ... \n footer)
        old_raw_lines = [l.strip() for l in old_text.splitlines()]
        wildcard_indices = [idx for idx, l in enumerate(old_raw_lines) if l in ("...", "…", "# ...", "// ...", "/* ... */")]
        if len(wildcard_indices) == 1:
            w_idx = wildcard_indices[0]
            head_norm = [normalize_line(l) for l in old_text.splitlines()[:w_idx] if normalize_line(l)]
            tail_norm = [normalize_line(l) for l in old_text.splitlines()[w_idx+1:] if normalize_line(l)]

            if head_norm and tail_norm:
                # Find head match
                head_match_idx = -1
                for i in range(len(content_lines)):
                    if content_lines[i].strip() == head_norm[0]:
                        if all(i+k < len(content_lines) and content_lines[i+k].strip() == head_norm[k] for k in range(len(head_norm))):
                            head_match_idx = i
                            break

                # Find tail match after head
                if head_match_idx != -1:
                    tail_match_idx = -1
                    for i in range(head_match_idx + len(head_norm), len(content_lines)):
                        if content_lines[i].strip() == tail_norm[0]:
                            if all(i+k < len(content_lines) and content_lines[i+k].strip() == tail_norm[k] for k in range(len(tail_norm))):
                                tail_match_idx = i + len(tail_norm)
                                break

                    if tail_match_idx != -1:
                        new_content = "".join(content_lines[:head_match_idx]) + new_text
                        if new_text and not new_text.endswith("\n") and tail_match_idx < len(content_lines):
                            new_content += "\n"
                        new_content += "".join(content_lines[tail_match_idx:])

                        with open(p, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        return f"Surgically edited {path} (wildcard replaced block from line {head_match_idx+1} to {tail_match_idx})."

        # Tier 4: Anchor Matching (First line & Last line match uniquely)
        if len(old_norm) >= 3:
            first_l = old_norm[0]
            last_l = old_norm[-1]

            first_matches = [i for i, l in enumerate(content_lines) if l.strip() == first_l]
            last_matches = [i for i, l in enumerate(content_lines) if l.strip() == last_l]

            if len(first_matches) == 1 and len(last_matches) == 1:
                f_idx = first_matches[0]
                l_idx = last_matches[0]
                if f_idx < l_idx:
                    new_content = "".join(content_lines[:f_idx]) + new_text
                    if new_text and not new_text.endswith("\n") and (l_idx + 1) < len(content_lines):
                        new_content += "\n"
                    new_content += "".join(content_lines[l_idx + 1:])

                    with open(p, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    return f"Surgically edited {path} (anchor replaced block between lines {f_idx+1} and {l_idx+1})."

        # Tier 5: Difflib similarity ratio matching (>= 60% similarity for small models)
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
            return f"Surgically edited {path} (similarity replaced block with {int(best_ratio*100)}% match at lines {best_diff_start+1}-{best_diff_end})."

        # Tier 6: Character-level subsequence matching for typo-ridden input
        best_subseq_len = 0
        best_subseq_start = -1
        old_stripped = old_text.strip()
        if len(old_stripped) >= 20:
            for i in range(len(content) - len(old_stripped) // 3):
                end = min(i + len(old_stripped) + len(old_stripped) // 3, len(content))
                candidate = content[i:end]
                sm = difflib.SequenceMatcher(None, old_stripped, candidate)
                for bloc in sm.get_matching_blocks():
                    if bloc.size > best_subseq_len:
                        best_subseq_len = bloc.size
                        best_subseq_start = i + bloc.a

        if best_subseq_len >= len(old_stripped) * 0.65 and best_subseq_start != -1:
            match_start = content.rfind("\n", 0, best_subseq_start) + 1
            remaining = content[best_subseq_start:]
            match_end = remaining.find("\n")
            if match_end == -1:
                match_end = len(remaining)
            match_end += best_subseq_start

            line_start = content.rfind("\n", 0, match_start)
            line_start = 0 if line_start == -1 else line_start + 1
            line_end = content.find("\n", match_end)
            if line_end == -1:
                line_end = len(content)
            else:
                line_end += 1

            new_content = content[:line_start] + new_text
            if new_text and not new_text.endswith("\n") and line_end < len(content):
                new_content += "\n"
            new_content += content[line_end:]

            with open(p, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"Surgically edited {path} (character-level matched {best_subseq_len}/{len(old_stripped)} chars at line ~{content[:match_start].count(chr(10))+1})."

        # All tiers failed — provide closest match as diagnostic
        closest_block = ""
        closest_ratio = 0.0
        closest_line = 1
        for i in range(max(1, len(content_lines) - 10)):
            block = "".join(content_lines[i:min(i+10, len(content_lines))])
            ratio = difflib.SequenceMatcher(None, block, old_text).ratio()
            if ratio > closest_ratio:
                closest_ratio = ratio
                closest_block = block
                closest_line = i + 1

        hint = ""
        if closest_ratio > 0.25:
            snippet = closest_block.strip()[:250]
            hint = (
                f"\n⚠️ Closest match found ({int(closest_ratio*100)}% similar, around line {closest_line}):\n"
                f"```\n{snippet}\n```\n"
                f"ACTION REQUIRED: Call READ_FILE(path='{path}:{closest_line}-{closest_line+15}') to copy the exact lines before retrying your edit."
            )

        return (
            f"Edit failed: Could not find a matching block for 'old_text' in {path}.\n"
            f"HINT: Always call READ_FILE first to view current line numbers and exact indentation.{hint}"
        )
    except Exception as e:
        return f"Error editing file: {e}"


def tool_read_symbols_impl(args: dict, project_root: str) -> str:
    """READ_SYMBOLS — show file structure without loading content."""
    try:
        path = args.get("path", "")
        if not path or path.strip() == "":
            return "READ_SYMBOLS requires a file path. Use RUN_COMMAND('ls') to see directory contents."

        p = os.path.join(project_root, path) if not os.path.isabs(path) else path

        # Security
        cwd_abs = os.path.abspath(project_root)
        cwd_prefix = cwd_abs if cwd_abs.endswith(os.sep) else cwd_abs + os.sep
        if not os.path.abspath(p).startswith(cwd_prefix) and os.path.abspath(p) != cwd_abs:
            return f"Access denied: {path} is outside the workspace."

        if not os.path.exists(p):
            return f"File not found: {path}"
        if os.path.isdir(p):
            return f"{path} is a directory. Use RUN_COMMAND('ls {path}') to list it."

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
                        size_str = f"{size/1024:.1f}KB"
                    else:
                        size_str = f"{size/(1024*1024):.1f}MB"
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
        path = args.get("path", ".")
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
        "--context", str(CONTEXT),
        "--max-count", str(MAX_MATCHES),
        "--color", "never",
        "--hidden",
        "--glob", "!.git",
        "--glob", "!__pycache__",
        "--glob", "!node_modules",
        "--glob", "!venv",
        "--glob", "!.venv",
        "--glob", "!*.pyc",
        "--glob", "!*.pyo",
        "--glob", "!*.so",
        "--glob", "!*.o",
        "--glob", "!*.class",
        "--glob", "!build",
        "--glob", "!dist",
        "--glob", "!.gradle",
        "--glob", "!.idea",
    ]

    if os.path.isfile(path):
        parts.extend(["--no-ignore", "--", pattern, path])
    elif os.path.isdir(path):
        parts.extend(["--", pattern, path])
    else:
        return f"GREP: path not found: {path}"

    try:
        r = subprocess.run(
            parts, capture_output=True, text=True,
            cwd=project_root, timeout=30,
        )
        output = (r.stdout or "").strip()
        if not output:
            # rg returns exit code 1 when no matches
            return f"GREP: no matches for '{pattern}' in {os.path.relpath(path, project_root)}"

        # Count matches (lines without context markers)
        match_count = sum(1 for line in output.splitlines()
                         if line and ":" in line and not line.startswith("--"))

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
                block.append(f"{marker}{i+1:>4}: {flines[i].rstrip()}")
            results.append("\n".join(block))

    if os.path.isfile(path):
        rel = os.path.relpath(path, project_root) if os.path.isabs(path) else path
        _search_file(path, rel)
    elif os.path.isdir(path):
        SKIP = {".git", "__pycache__", "node_modules", ".gradle",
                "build", "dist", ".idea", "venv", ".venv"}
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
    timeout = 180 if any(cmd.strip().startswith(c) for c in _LONG_CMDS) else 60

    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=project_root, timeout=timeout,
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
                headers={"Accept": "application/json", "X-Subscription-Token": brave_key},
                params={"q": query, "count": 5}, timeout=15,
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
    url = args.get("url", "")
    if not url:
        return "Fetch error: No URL provided."
    if not url.startswith("http"):
        url = "https://" + url

    # Tier 1: Reader API (Jina AI)
    try:
        r = httpx.get(
            f"https://r.jina.ai/{url}", headers={"Accept": "text/plain"},
            timeout=20, follow_redirects=True,
        )
        if r.status_code == 200 and r.text.strip():
            return f"{url}:\n{r.text.strip()[:4000]}"
    except Exception:
        pass

    # Tier 1 Fallback: Stealth HTTP request with realistic browser headers
    try:
        headers = _get_browser_headers()
        r = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
        if r.status_code == 200 and r.text.strip():
            parser = StructurePreservingHTMLParser()
            parser.feed(r.text)
            parsed_text = parser.get_markdown()
            if parsed_text and len(parsed_text) > 50:
                return f"{url}:\n{parsed_text[:4000]}"
    except Exception:
        pass

    # Tier 2: Remote Playwright Headless Browser fallback (for 403, 429, JS SPAs)
    pw_content = _fetch_remote_playwright(url)
    if pw_content:
        return f"{url} (via Playwright):\n{pw_content}"

    return f"Fetch error: Unable to retrieve content from {url} (blocked or unreachable)."


def tool_doc_search_impl(args: dict, project_root: str) -> str:
    """DOC_SEARCH — search official documentation."""
    import urllib.parse
    raw_query = args.get("query", "")
    query = _augment_query_with_project_deps(raw_query, project_root)
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
        domain_m = re.search(r'https?://([^/]+)', search_url)
        ddg_q = (f"site:{domain_m.group(1)} {ident}"
                 if "duckduckgo" not in label and domain_m
                 else f"{ident} {language} documentation")
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
    results += ["─" * 40,
                "VERIFIED = identifier appeared in docs search results.",
                "Always read the full doc page before relying on this."]
    return "\n".join(results)


def tool_save_memory_impl(args: dict, project_root: str) -> str:
    """SAVE_MEMORY — save a fact to project memory."""
    fact = args.get("fact", "")
    category = args.get("category", "fact")

    if not fact or not fact.strip():
        return "No fact provided."
    fact = fact.strip()
    if len(fact) > 300:
        return "Fact too long — keep under 300 chars."

    try:
        from ..memory.persistence import ProjectMemory
        pm = ProjectMemory(Path(project_root))
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
            pm.update(fact)
        return f"Saved to project memory ({cat}): '{fact[:100]}'"
    except Exception as e:
        return f"Failed to write memory file: {e}"


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
    """VERIFY — verify a file exists and optionally contains expected content."""
    try:
        path = args.get("path", "")
        expected_snippet = args.get("expected_snippet")
        p = os.path.join(project_root, path) if not os.path.isabs(path) else path
        if not os.path.exists(p):
            return f"Verification FAILED: File does not exist at {path}"
        if expected_snippet:
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
            if expected_snippet in content:
                return f"Verification SUCCESS: Found expected content in {path}"
            else:
                return f"Verification WARNING: File exists but expected snippet was NOT found in {path}"
        return f"Verification SUCCESS: File exists at {path}"
    except Exception as e:
        return f"Verification ERROR: {e}"


def tool_ask_user_impl(args: dict, project_root: str) -> str:
    """ASK_USER — ask the user a question."""
    question = args.get("question", "")
    return f"[AWAITING USER INPUT] {question}"


# ── GIT tool ────────────────────────────────────────────────────────────────

_GIT_SAFE_SUBCOMMANDS = {
    "status", "log", "diff", "show", "branch", "stash", "remote",
    "ls-files", "rev-parse", "describe", "blame", "shortlog",
}
_GIT_WRITE_SUBCOMMANDS = {"add", "restore", "stash", "checkout", "switch"}
_GIT_DESTRUCTIVE_SUBCOMMANDS = {"push", "reset", "rebase", "merge", "clean", "drop"}


def _git_run(cmd: str, project_root: str, timeout: int = 30) -> tuple[bool, str]:
    """Run a git command and return (success, output)."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=project_root, timeout=timeout,
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
            return "Not a git repository. Use RUN_COMMAND('git init') to initialize one."

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
    query = str(args.get("query", "")).strip()
    action = str(args.get("action", "search")).strip().lower()
    top_k = int(args.get("top_k", 5))

    from core.flashlight.graph_engine import get_project_graph
    graph = get_project_graph(project_root)

    if action in ("update", "reindex", "build"):
        gdict = graph.build()
        return f"✅ AST Graph re-indexed successfully: {gdict['node_count']} nodes, {gdict['edge_count']} edges saved to `.torchlight/graph.json`."
    elif action in ("search", "query", "semantic"):
        if not query:
            return graph.get_structure()
        res = graph.query(query, top_k=top_k)
        if "No AST graph nodes found" in res:
            try:
                from rlm_optimized.repl_sandbox import semantic_search
                return semantic_search(query, top_k=top_k, project_root=project_root)
            except ImportError:
                pass
        return res
    elif action in ("path", "find_path"):
        target = str(args.get("target", args.get("to", ""))).strip()
        if not target and "," in query:
            parts = query.split(",", 1)
            query, target = parts[0].strip(), parts[1].strip()
        return graph.find_path(query, target)
    elif action == "subgraph":
        return graph.get_subgraph(query)
    elif action in ("structure", "project"):
        return graph.get_structure()
    elif action in ("summary", "info"):
        return f"Project AST Graph: {graph.graph_file}\nNodes: {len(graph.nodes)} | Edges: {len(graph.edges)}"
    else:
        return graph.query(query, top_k=top_k)


def tool_inspect_web_impl(args: dict, project_root: str) -> str:
    """Inspect runtime outcome of HTML/JS/CSS web pages or Canvas games."""
    path = str(args.get("path", "")).strip()
    wait_ms = int(args.get("wait_ms", 1500))

    if not path:
        return "INSPECT_WEB requires 'path' parameter."

    from pathlib import Path
    full_path = Path(project_root) / path if not Path(path).is_absolute() else Path(path)

    try:
        from core.execution.web_inspector import WebOutcomeInspector
        inspector = WebOutcomeInspector(output_dir=Path(project_root) / ".torchlight" / "screenshots")
        res = inspector.inspect(file_path=str(full_path), wait_ms=wait_ms)
        return res.to_markdown()
    except Exception as e:
        return f"Error during web outcome inspection: {e}"


