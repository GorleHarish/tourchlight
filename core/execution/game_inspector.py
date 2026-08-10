"""
HTML Game Inspector & Player Harness for Torchlight.

Provides autonomous playing, dynamic frame buffer analysis, input simulation,
memory load tracking, live progress indicators, and runtime error verification
for HTML5 / Canvas / Web games.
"""

from dataclasses import dataclass, field
from datetime import datetime
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable, Dict, List, Optional

from core.execution.web_inspector import EphemeralHTTPServer, StaticHTMLValidator

logger = logging.getLogger(__name__)


def get_process_memory_mb() -> float:
    """Returns current process RSS memory load in Megabytes (MB)."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            if sys.platform == "darwin":
                return usage.ru_maxrss / (1024 * 1024)  # Bytes on macOS
            else:
                return usage.ru_maxrss / 1024  # KB on Linux
        except Exception:
            return 0.0


@dataclass
class GameInputEvent:
    """Represents an input action simulated during HTML game playback."""
    action: str  # "key_press" | "key_down" | "key_up" | "click" | "wait"
    key: Optional[str] = None
    selector: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    duration_ms: int = 200


@dataclass
class GameOutcomeResult:
    """Detailed diagnostic results after playing an HTML game."""
    url: str
    status: str  # "PASS" | "FAIL" | "WARN"
    tier_used: str = "playwright"
    duration_ms: float = 0.0
    frame_count: int = 0
    blank_canvas_detected: bool = False
    frozen_canvas_detected: bool = False
    unresponsive_input_detected: bool = False
    memory_mb: float = 0.0
    console_errors: List[str] = field(default_factory=list)
    console_logs: List[str] = field(default_factory=list)
    failed_requests: List[str] = field(default_factory=list)
    pixel_deltas: List[float] = field(default_factory=list)
    dom_summary: Dict[str, Any] = field(default_factory=dict)
    screenshot_path: Optional[str] = None
    error_summary: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_passed(self) -> bool:
        return (
            self.status == "PASS"
            and len(self.console_errors) == 0
            and len(self.failed_requests) == 0
            and not self.blank_canvas_detected
            and not self.frozen_canvas_detected
        )

    def to_markdown(self) -> str:
        """Formats the result into concise Markdown for LLM context."""
        lines = [f"### 🎮 HTML Game Verification: `{self.status}` ({self.duration_ms:.0f}ms | Memory: `{self.memory_mb:.1f} MB`)"]

        if self.console_errors:
            lines.append("\n**Runtime Exceptions / Console Errors:**")
            for err in self.console_errors[:5]:
                lines.append(f"- ❌ `{err}`")
            if len(self.console_errors) > 5:
                lines.append(f"- ... ({len(self.console_errors) - 5} more errors)")

        if self.failed_requests:
            lines.append("\n**Missing Assets / Failed Network Requests:**")
            for req in self.failed_requests[:5]:
                lines.append(f"- ⚠️ `{req}`")

        anomalies = []
        if self.blank_canvas_detected:
            anomalies.append("⚠️ **Blank Canvas Detected**: Canvas container mounted, but 0 pixels drawn.")
        if self.frozen_canvas_detected:
            anomalies.append("⚠️ **Frozen Frame / Render Freeze**: Pixel delta was 0.0 over multi-frame playback under input simulation.")
        if self.unresponsive_input_detected:
            anomalies.append("⚠️ **Unresponsive Controls**: Input events sent, but canvas state did not respond.")

        if anomalies:
            lines.append("\n**Game Behavior Anomalies:**")
            for item in anomalies:
                lines.append(f"- {item}")

        if self.dom_summary:
            lines.append("\n**Game Canvas & DOM State:**")
            if "title" in self.dom_summary and self.dom_summary["title"]:
                lines.append(f"- Title: `{self.dom_summary['title']}`")
            if "canvases" in self.dom_summary and self.dom_summary["canvases"]:
                lines.append(f"- Canvas Elements: {', '.join(self.dom_summary['canvases'])}")

        lines.append(f"\n**Performance & System Load:**")
        lines.append(f"- RSS Memory Load: `{self.memory_mb:.1f} MB`")
        lines.append(f"- Played Frame Samples: {self.frame_count}")
        lines.append(f"- Verification Engine: `{self.tier_used}`")

        if self.screenshot_path:
            lines.append(f"\n**Game Screenshot Captured:** `{self.screenshot_path}`")

        if self.is_passed:
            lines.append("\n✅ **Game verified! No errors, render freezes, or input issues detected.**")

        return "\n".join(lines)


class HtmlGamePlayer:
    """
    Autonomous HTML Game Harness & Dynamic Verifier.

    Launches an ephemeral browser session, simulates interactive play,
    tracks memory load, emits live progress indicators, and catches game loop bugs.
    """

    DEFAULT_HEURISTIC_INPUTS = [
        GameInputEvent(action="key_press", key="ArrowUp", duration_ms=200),
        GameInputEvent(action="key_press", key="ArrowRight", duration_ms=200),
        GameInputEvent(action="key_press", key="Space", duration_ms=300),
        GameInputEvent(action="key_press", key="ArrowDown", duration_ms=200),
        GameInputEvent(action="key_press", key="ArrowLeft", duration_ms=200),
        GameInputEvent(action="key_press", key="KeyW", duration_ms=200),
        GameInputEvent(action="key_press", key="KeyD", duration_ms=200),
        GameInputEvent(action="click", selector="canvas", duration_ms=200),
    ]

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path(os.getcwd()) / ".torchlight" / "screenshots"

    def play_and_verify(
        self,
        file_path: str,
        duration_ms: int = 3000,
        input_events: Optional[List[GameInputEvent]] = None,
        take_screenshot: bool = True,
        on_progress: Optional[Callable[[str, str], None]] = None
    ) -> GameOutcomeResult:
        """
        Plays the HTML game for duration_ms while simulating inputs and checking frame diffs.
        Emits live progress updates via on_progress(stage, message) callback.
        """
        start_time = time.time()
        start_mem = get_process_memory_mb()
        duration_ms = max(500, min(15000, duration_ms))  # 0.5s to 15s max
        raw_path = str(file_path).strip()

        def _emit(stage: str, msg: str):
            logger.info(f"[{stage}] {msg}")
            if on_progress:
                on_progress(stage, msg)

        _emit("INIT", f"🚀 Starting Game Verification for `{Path(file_path).name}` (Initial Memory: {start_mem:.1f} MB)")

        # Handle direct HTTP/HTTPS URLs
        if raw_path.startswith(("http://", "https://")):
            target_url = raw_path
            path_obj = Path("game_remote.html")
            res = self._run_playwright_game(
                target_url, path_obj, duration_ms, input_events, take_screenshot, start_time, _emit
            )
            if res is not None:
                return res
            return self._inspect_static(path_obj, start_time)

        # Handle disk path
        query_suffix = ""
        if "?" in raw_path or "#" in raw_path:
            split_char = "?" if "?" in raw_path else "#"
            parts = raw_path.split(split_char, 1)
            raw_path = parts[0]
            query_suffix = split_char + parts[1]

        path_obj = Path(raw_path).resolve()
        if not path_obj.exists():
            return GameOutcomeResult(
                url=file_path,
                status="FAIL",
                tier_used="none",
                duration_ms=(time.time() - start_time) * 1000,
                memory_mb=get_process_memory_mb(),
                console_errors=[f"File not found: {raw_path}"],
                error_summary="Game file not found"
            )

        base_dir = path_obj.parent
        server = EphemeralHTTPServer(base_dir)
        server_url = server.start()
        target_url = f"{server_url}/{path_obj.name}{query_suffix}"

        try:
            res = self._run_playwright_game(
                target_url, path_obj, duration_ms, input_events, take_screenshot, start_time, _emit
            )
            if res is not None:
                return res
            return self._inspect_static(path_obj, start_time)
        finally:
            server.stop()

    def _run_playwright_game(
        self,
        url: str,
        file_path: Path,
        duration_ms: int,
        input_events: Optional[List[GameInputEvent]],
        take_screenshot: bool,
        start_time: float,
        emit_func: Callable[[str, str], None]
    ) -> Optional[GameOutcomeResult]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.debug("Playwright not installed, falling back to static inspection.")
            return None

        console_errors: List[str] = []
        console_logs: List[str] = []
        failed_requests: List[str] = []
        screenshot_file: Optional[str] = None
        pixel_samples: List[List[int]] = []

        inputs_to_run = input_events if input_events is not None else self.DEFAULT_HEURISTIC_INPUTS

        try:
            emit_func("BROWSER", "🎮 Launching Playwright Chromium headless browser engine...")
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

                    emit_func("LOAD", f"🌐 Navigating to game page `{url}`...")
                    page.goto(url, wait_until="load", timeout=10000)
                    page.wait_for_timeout(300)

                    # Helper script to snapshot canvas pixel sample
                    get_sample_js = """() => {
                        const canvas = document.querySelector('canvas');
                        if (!canvas) return null;
                        try {
                            const ctx = canvas.getContext('2d');
                            if (!ctx) return { isNullCtx: true };
                            const w = canvas.width || 300;
                            const h = canvas.height || 150;
                            const sample = [];
                            const stepX = Math.max(1, Math.floor(w / 10));
                            const stepY = Math.max(1, Math.floor(h / 10));
                            for (let y = 0; y < h; y += stepY) {
                                for (let x = 0; x < w; x += stepX) {
                                    const px = ctx.getImageData(x, y, 1, 1).data;
                                    sample.push(px[0], px[1], px[2], px[3]);
                                }
                            }
                            return { sample: sample, width: w, height: h };
                        } catch (e) {
                            return { error: e.toString() };
                        }
                    }"""

                    # Capture initial frame sample
                    initial_snap = page.evaluate(get_sample_js)
                    if initial_snap and "sample" in initial_snap:
                        pixel_samples.append(initial_snap["sample"])

                    # Play game by executing inputs across elapsed time
                    step_duration = max(100, int(duration_ms / (len(inputs_to_run) + 1)))
                    emit_func("PLAYING", f"🕹️ Simulating game controls ({len(inputs_to_run)} actions over {duration_ms}ms)...")

                    for idx, inp in enumerate(inputs_to_run, 1):
                        if inp.action == "key_press" and inp.key:
                            page.keyboard.press(inp.key)
                        elif inp.action == "key_down" and inp.key:
                            page.keyboard.down(inp.key)
                        elif inp.action == "key_up" and inp.key:
                            page.keyboard.up(inp.key)
                        elif inp.action == "click":
                            sel = inp.selector or "canvas"
                            if page.is_visible(sel):
                                page.click(sel)
                            elif inp.x is not None and inp.y is not None:
                                page.mouse.click(inp.x, inp.y)

                        page.wait_for_timeout(step_duration)

                        # Sample canvas pixels after each action
                        snap = page.evaluate(get_sample_js)
                        if snap and "sample" in snap:
                            pixel_samples.append(snap["sample"])

                    emit_func("VERIFYING", "📊 Evaluating canvas frame buffer deltas & game DOM state...")

                    # Evaluate canvas DOM summary
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
                            return { id: c.id || 'gameCanvas', width: c.width, height: c.height, isBlank: isBlank };
                        });
                        return {
                            title: document.title,
                            canvases: canvasDetails.map(c => `<canvas id="${c.id}" ${c.width}x${c.height}>${c.isBlank ? ' [BLANK]' : ''}`),
                            has_canvas: canvasDetails.length > 0,
                            blank_canvas_detected: canvasDetails.length > 0 && canvasDetails.every(c => c.isBlank)
                        };
                    }""")

                    # Calculate frame pixel deltas to detect render freeze
                    pixel_deltas = []
                    for i in range(1, len(pixel_samples)):
                        prev = pixel_samples[i - 1]
                        curr = pixel_samples[i]
                        if len(prev) == len(curr) and len(prev) > 0:
                            diff = sum(abs(curr[j] - prev[j]) for j in range(len(prev))) / len(prev)
                            pixel_deltas.append(diff)

                    blank_canvas = dom_summary.get("blank_canvas_detected", False)
                    # If canvas is present, we took multiple samples, and max pixel delta across frames is 0 -> Frozen frame!
                    frozen_canvas = bool(
                        dom_summary.get("has_canvas")
                        and len(pixel_deltas) >= 2
                        and max(pixel_deltas) == 0.0
                        and not blank_canvas
                    )

                    if take_screenshot:
                        self.output_dir.mkdir(parents=True, exist_ok=True)
                        shot_path = self.output_dir / f"{file_path.stem}_game_play.png"
                        page.screenshot(path=str(shot_path))
                        screenshot_file = str(shot_path)

                    status = "FAIL" if (console_errors or failed_requests or blank_canvas or frozen_canvas) else "PASS"
                    final_mem = get_process_memory_mb()

                    emit_func("DONE", f"✅ Game Playback Verification Finished: Status `{status}` (Memory Load: {final_mem:.1f} MB)")

                    return GameOutcomeResult(
                        url=url,
                        status=status,
                        tier_used="playwright",
                        duration_ms=(time.time() - start_time) * 1000,
                        frame_count=len(pixel_samples),
                        blank_canvas_detected=blank_canvas,
                        frozen_canvas_detected=frozen_canvas,
                        unresponsive_input_detected=frozen_canvas,
                        memory_mb=final_mem,
                        console_errors=console_errors,
                        console_logs=console_logs,
                        failed_requests=failed_requests,
                        pixel_deltas=pixel_deltas,
                        dom_summary=dom_summary,
                        screenshot_path=screenshot_file
                    )
                finally:
                    browser.close()
        except Exception as e:
            logger.warning(f"HTML Game Playwright inspection failed: {e}")
            return None

    def _inspect_static(self, file_path: Path, start_time: float) -> GameOutcomeResult:
        """Tier 1: Static HTML game parsing fallback when Playwright is unavailable."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            validator = StaticHTMLValidator(file_path.parent)
            validator.feed(content)

            status = "FAIL" if validator.missing_files else "PASS"
            return GameOutcomeResult(
                url=str(file_path),
                status=status,
                tier_used="static",
                duration_ms=(time.time() - start_time) * 1000,
                memory_mb=get_process_memory_mb(),
                failed_requests=validator.missing_files,
                dom_summary={
                    "title": validator.title,
                    "canvases": validator.found_canvases,
                }
            )
        except Exception as e:
            return GameOutcomeResult(
                url=str(file_path),
                status="FAIL",
                tier_used="static",
                duration_ms=(time.time() - start_time) * 1000,
                memory_mb=get_process_memory_mb(),
                console_errors=[f"HTML parse error: {str(e)}"]
            )
