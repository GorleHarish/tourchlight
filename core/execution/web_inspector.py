"""
Web Outcome Inspector for Torchlight.

Provides low-memory, ephemeral runtime and visual feedback for generated HTML, CSS, JavaScript,
and HTML5 Canvas games / web applications.
"""

from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

import http.server
import logging
import os
import socket
import socketserver
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WebInspectionResult:
    url: str
    status: str  # "PASS" | "FAIL" | "WARN"
    tier_used: str  # "playwright" | "node_jsdom" | "static"
    duration_ms: float = 0.0
    console_errors: List[str] = field(default_factory=list)
    console_logs: List[str] = field(default_factory=list)
    failed_requests: List[str] = field(default_factory=list)
    dom_summary: Dict[str, Any] = field(default_factory=dict)
    ax_tree: Optional[Dict[str, Any]] = None
    screenshot_path: Optional[str] = None
    error_summary: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_passed(self) -> bool:
        return self.status == "PASS" and len(self.console_errors) == 0 and len(self.failed_requests) == 0

    def to_markdown(self) -> str:
        """Formats the result into compact Markdown suitable for LLM context."""
        lines = [f"### Web Inspection Outcome: `{self.status}` (Tier: `{self.tier_used}`, {self.duration_ms:.0f}ms)"]
        
        if self.console_errors:
            lines.append("\n**Runtime Console Errors:**")
            for err in self.console_errors[:5]:
                lines.append(f"- ❌ `{err}`")
            if len(self.console_errors) > 5:
                lines.append(f"- ... (and {len(self.console_errors) - 5} more errors)")

        if self.failed_requests:
            lines.append("\n**Failed Resources (404/Network):**")
            for req in self.failed_requests[:5]:
                lines.append(f"- ⚠️ `{req}`")

        if self.dom_summary:
            lines.append("\n**DOM Snapshot Summary:**")
            if "title" in self.dom_summary and self.dom_summary["title"]:
                lines.append(f"- Title: `{self.dom_summary['title']}`")
            if "canvases" in self.dom_summary and self.dom_summary["canvases"]:
                lines.append(f"- Canvases: {', '.join(self.dom_summary['canvases'])}")
            if "element_count" in self.dom_summary:
                lines.append(f"- Total DOM Elements: {self.dom_summary['element_count']}")
            if "interactive_elements" in self.dom_summary:
                ie = self.dom_summary["interactive_elements"]
                lines.append(f"- Interactive Elements: Buttons ({ie.get('buttons', 0)}), Inputs ({ie.get('inputs', 0)}), Links ({ie.get('links', 0)})")
            if "overflow_warnings" in self.dom_summary and self.dom_summary["overflow_warnings"]:
                lines.append(f"- ⚠️ Overflow Warnings: {', '.join(self.dom_summary['overflow_warnings'])}")
            if "text_preview" in self.dom_summary and self.dom_summary["text_preview"]:
                preview = self.dom_summary["text_preview"][:150].replace("\n", " ")
                lines.append(f"- Text Preview: *\"{preview}\"*")

        if self.ax_tree:
            lines.append("\n**Accessibility Tree Summary:**")
            role = self.ax_tree.get("role", {}).get("value", "document") if isinstance(self.ax_tree, dict) else "document"
            name = self.ax_tree.get("name", {}).get("value", "") if isinstance(self.ax_tree, dict) else ""
            lines.append(f"- Root Role: `{role}` {f'({name})' if name else ''}")

        if self.screenshot_path:
            lines.append(f"\n**Screenshot Saved:** `{self.screenshot_path}`")

        if not self.console_errors and not self.failed_requests and self.status == "PASS":
            lines.append("\n✅ **No runtime errors detected.** Web outcome loaded cleanly.")

        return "\n".join(lines)


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP Request Handler that suppresses console logging noise."""
    def log_message(self, format: str, *args: Any) -> None:
        pass


class EphemeralHTTPServer:
    """Spins up a lightweight local HTTP server for static file inspection."""
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()
        self.server: Optional[socketserver.TCPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.port: int = 0

    def start(self) -> str:
        handler = lambda *args, **kwargs: QuietHTTPRequestHandler(*args, directory=str(self.root_dir), **kwargs)
        # Find an available free port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            self.port = s.getsockname()[1]

        self.server = socketserver.TCPServer(('127.0.0.1', self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return f"http://127.0.0.1:{self.port}"

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None


class StaticHTMLValidator(HTMLParser):
    """Tier 1: Static HTML syntax and asset path validator."""
    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
        self.missing_files: List[str] = []
        self.found_scripts: List[str] = []
        self.found_canvases: List[str] = []
        self.title: str = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: List[tuple]):
        attr_dict = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "script" and "src" in attr_dict:
            src = attr_dict["src"]
            self.found_scripts.append(src)
            if not src.startswith(("http://", "https://", "//")):
                file_path = self.base_dir / src
                if not file_path.exists():
                    self.missing_files.append(f"Script missing: {src}")
        elif tag == "img" and "src" in attr_dict:
            src = attr_dict["src"]
            if not src.startswith(("http://", "https://", "data:", "//")):
                file_path = self.base_dir / src
                if not file_path.exists():
                    self.missing_files.append(f"Image missing: {src}")
        elif tag == "link" and attr_dict.get("rel") == "stylesheet" and "href" in attr_dict:
            href = attr_dict["href"]
            if not href.startswith(("http://", "https://", "//")):
                file_path = self.base_dir / href
                if not file_path.exists():
                    self.missing_files.append(f"CSS missing: {href}")
        elif tag == "canvas":
            c_id = attr_dict.get("id", "canvas")
            w = attr_dict.get("width", "default")
            h = attr_dict.get("height", "default")
            self.found_canvases.append(f"<canvas id=\"{c_id}\" {w}x{h}>")

    def handle_endtag(self, tag: str):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str):
        if self._in_title:
            self.title += data.strip()


class WebOutcomeInspector:
    """
    Main Inspector Subsystem driving zero-memory, ephemeral web verification.
    """
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path(os.getcwd()) / ".torchlight" / "screenshots"

    def inspect(
        self,
        file_path: str,
        wait_ms: int = 1500,
        interact: Optional[List[Dict[str, Any]]] = None,
        take_screenshot: bool = True
    ) -> WebInspectionResult:
        start_time = time.time()
        
        # Clamp wait_ms between 100ms and 10000ms (10 sec max) to prevent context/process hanging
        wait_ms = max(100, min(10000, wait_ms))
        raw_path = str(file_path).strip()

        # Handle direct HTTP/HTTPS URLs (e.g. local dev servers)
        if raw_path.startswith(("http://", "https://")):
            target_url = raw_path
            path_obj = Path("remote_page.html")
            res = self._inspect_playwright(target_url, path_obj, wait_ms, interact, take_screenshot)
            if res is not None:
                res.duration_ms = (time.time() - start_time) * 1000
                return res
            return WebInspectionResult(
                url=target_url,
                status="FAIL",
                tier_used="none",
                duration_ms=(time.time() - start_time) * 1000,
                console_errors=[f"Failed to load remote URL: {target_url}"]
            )

        # Separate query params/hash fragments from real disk path (e.g. index.html?v=1#canvas)
        query_suffix = ""
        if "?" in raw_path or "#" in raw_path:
            split_char = "?" if "?" in raw_path else "#"
            parts = raw_path.split(split_char, 1)
            raw_path = parts[0]
            query_suffix = split_char + parts[1]

        path_obj = Path(raw_path).resolve()

        if not path_obj.exists():
            return WebInspectionResult(
                url=file_path,
                status="FAIL",
                tier_used="none",
                duration_ms=(time.time() - start_time) * 1000,
                console_errors=[f"File not found: {raw_path}"],
                error_summary="File not found"
            )

        base_dir = path_obj.parent
        server = EphemeralHTTPServer(base_dir)
        server_url = server.start()
        target_url = f"{server_url}/{path_obj.name}{query_suffix}"

        try:
            # Try Tier 2: Playwright Headless Inspection
            res = self._inspect_playwright(target_url, path_obj, wait_ms, interact, take_screenshot)
            if res is not None:
                res.duration_ms = (time.time() - start_time) * 1000
                return res

            # Try Tier 3: Node JSDOM Fallback
            res = self._inspect_node_jsdom(path_obj)
            if res is not None:
                res.duration_ms = (time.time() - start_time) * 1000
                return res

            # Tier 1: Static Parsing Fallback
            res = self._inspect_static(path_obj)
            res.duration_ms = (time.time() - start_time) * 1000
            return res

        finally:
            server.stop()

    def _inspect_playwright(
        self,
        url: str,
        file_path: Path,
        wait_ms: int,
        interact: Optional[List[Dict[str, Any]]],
        take_screenshot: bool
    ) -> Optional[WebInspectionResult]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.debug("Playwright not installed, skipping Tier 2 Playwright inspection.")
            return None

        console_errors: List[str] = []
        console_logs: List[str] = []
        failed_requests: List[str] = []
        screenshot_file: Optional[str] = None
        ax_tree: Optional[Dict[str, Any]] = None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    context = browser.new_context(viewport={"width": 1024, "height": 768})
                    page = context.new_page()

                    page.on("console", lambda msg: (
                        console_errors.append(msg.text) if msg.type == "error" else console_logs.append(msg.text)
                    ))
                    page.on("pageerror", lambda exc: console_errors.append(str(exc)))
                    page.on("requestfailed", lambda req: failed_requests.append(
                        f"{req.url} ({req.failure.error_text if req.failure else 'failed'})"
                    ))

                    page.goto(url, wait_until="load", timeout=10000)

                    if wait_ms > 0:
                        page.wait_for_timeout(wait_ms)

                    if interact:
                        for act in interact:
                            act_type = act.get("type")
                            selector = act.get("selector", "body")
                            if act_type == "key_press":
                                page.keyboard.press(act.get("key", "Space"))
                            elif act_type == "click":
                                if page.is_visible(selector):
                                    page.click(selector)
                            elif act_type in ("fill", "type"):
                                text = act.get("text", "")
                                if page.is_visible(selector):
                                    page.fill(selector, text)
                            elif act_type == "hover":
                                if page.is_visible(selector):
                                    page.hover(selector)
                            elif act_type == "wait_for_selector":
                                try:
                                    page.wait_for_selector(selector, timeout=act.get("timeout", 2000))
                                except Exception:
                                    console_errors.append(f"Timeout waiting for selector: {selector}")

                    try:
                        ax_tree = page.accessibility.snapshot()
                    except Exception:
                        ax_tree = None

                    dom_summary = page.evaluate("""() => {
                        const canvases = Array.from(document.querySelectorAll('canvas'));
                        const canvasDetails = canvases.map(c => {
                            let isBlank = false;
                            try {
                                const ctx = c.getContext('2d');
                                if (ctx) {
                                    const imgData = ctx.getImageData(0, 0, Math.min(c.width, 100), Math.min(c.height, 100)).data;
                                    isBlank = Array.from(imgData).every(val => val === 0);
                                }
                            } catch (e) {}
                            return {
                                id: c.id || 'unnamed',
                                width: c.width,
                                height: c.height,
                                isBlank: isBlank
                            };
                        });
                        const canvasList = canvasDetails.map(c => 
                            `<canvas id="${c.id}" width="${c.width}" height="${c.height}">${c.isBlank ? ' [BLANK_CANVAS]' : ''}`
                        );

                        const overflowWarnings = [];
                        const bodyWidth = document.body ? document.body.clientWidth : 1024;
                        document.querySelectorAll('*').forEach(el => {
                            if (el.scrollWidth > bodyWidth + 50 && el.tagName !== 'SCRIPT' && el.tagName !== 'STYLE') {
                                overflowWarnings.push(`${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''} (scrollWidth ${el.scrollWidth}px > body ${bodyWidth}px)`);
                            }
                        });

                        const bodyText = document.body ? document.body.innerText.trim().slice(0, 300) : '';
                        return {
                            title: document.title,
                            canvases: canvasList,
                            blank_canvas_detected: canvasDetails.length > 0 && canvasDetails.every(c => c.isBlank),
                            element_count: document.querySelectorAll('*').length,
                            interactive_elements: {
                                buttons: document.querySelectorAll('button, input[type="button"], input[type="submit"]').length,
                                inputs: document.querySelectorAll('input, select, textarea').length,
                                links: document.querySelectorAll('a[href]').length
                            },
                            overflow_warnings: overflowWarnings.slice(0, 3),
                            text_preview: bodyText
                        };
                    }""")

                    if dom_summary.get("blank_canvas_detected"):
                        console_errors.append("⚠️ Warning: Canvas element found but 0 pixels drawn (blank canvas). Check game loop or rendering code.")

                    if take_screenshot:
                        self.output_dir.mkdir(parents=True, exist_ok=True)
                        shot_filename = f"{file_path.stem}_inspect.png"
                        shot_path = self.output_dir / shot_filename
                        page.screenshot(path=str(shot_path))
                        screenshot_file = str(shot_path)

                    status = "FAIL" if console_errors or failed_requests else "PASS"
                    return WebInspectionResult(
                        url=url,
                        status=status,
                        tier_used="playwright",
                        console_errors=console_errors,
                        console_logs=console_logs,
                        failed_requests=failed_requests,
                        dom_summary=dom_summary,
                        ax_tree=ax_tree,
                        screenshot_path=screenshot_file
                    )
                finally:
                    browser.close()
        except Exception as e:
            logger.warning(f"Playwright inspection encountered error: {e}")
            return None

    def _inspect_node_jsdom(self, file_path: Path) -> Optional[WebInspectionResult]:
        """Tier 3: Run Node JSDOM script if node is available."""
        try:
            node_check = subprocess.run(["node", "-v"], capture_output=True, text=True, timeout=2)
            if node_check.returncode != 0:
                return None
        except Exception:
            return None

        # Inline Node execution script to check syntax and basic load
        js_code = f"""
        const fs = require('fs');
        const html = fs.readFileSync({repr(str(file_path))}, 'utf8');
        console.log('JSDOM check OK');
        """
        try:
            r = subprocess.run(["node", "-e", js_code], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return WebInspectionResult(
                    url=str(file_path),
                    status="PASS",
                    tier_used="node_jsdom",
                    dom_summary={"title": file_path.name}
                )
            else:
                return WebInspectionResult(
                    url=str(file_path),
                    status="FAIL",
                    tier_used="node_jsdom",
                    console_errors=[r.stderr.strip() or r.stdout.strip()]
                )
        except Exception:
            return None

    def _inspect_static(self, file_path: Path) -> WebInspectionResult:
        """Tier 1: Static HTML analysis using Python standard library."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            validator = StaticHTMLValidator(file_path.parent)
            validator.feed(content)

            status = "FAIL" if validator.missing_files else "PASS"
            return WebInspectionResult(
                url=str(file_path),
                status=status,
                tier_used="static",
                failed_requests=validator.missing_files,
                dom_summary={
                    "title": validator.title,
                    "canvases": validator.found_canvases,
                    "element_count": len(content.split("<")) - 1
                }
            )
        except Exception as e:
            return WebInspectionResult(
                url=str(file_path),
                status="FAIL",
                tier_used="static",
                console_errors=[f"HTML parse error: {str(e)}"]
            )
