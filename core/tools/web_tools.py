"""Web browsing, search, documentation retrieval, and web outcome inspection tools."""

from __future__ import annotations

import os
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

import httpx

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


def tool_inspect_web_impl(args: dict, project_root: str) -> str:
    """Inspect runtime outcome of HTML/JS/CSS web pages or Canvas games."""
    path = str(args.get("path", "")).strip()
    wait_ms = int(args.get("wait_ms", 1500))
    interact = args.get("interact")

    if not path:
        return "INSPECT_WEB requires 'path' parameter."

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
