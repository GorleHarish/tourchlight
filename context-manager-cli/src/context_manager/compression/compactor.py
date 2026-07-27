import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class CompressionConfig:
    preserve_code: bool = True
    preserve_errors: bool = True
    preserve_paths: bool = True
    aggressive_mode: bool = False
    min_length_to_compress: int = 100


class VerbatimCompactor:
    """Compress text while preserving the content that matters most for dev sessions.

    Key principle: a dev LLM needs structure more than prose.  When compressing
    code, keep imports + signatures + the last few lines (where the current work
    is), not a random first/last slice.  When compressing errors, keep the most
    recent ones, not the first ones.
    """

    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()

    def compress(self, text: str) -> str:
        if len(text) < self.config.min_length_to_compress:
            return text
        if len(text.split("\n")) <= 10:
            return text

        if self.config.preserve_code:
            text = self._compress_code(text)
        if self.config.preserve_errors:
            text = self._compress_errors(text)
        if self.config.preserve_paths:
            text = self._compress_paths(text)

        text = self._remove_empty_lines(text)
        text = self._normalize_whitespace(text)
        return text

    def compress_with_budget(self, text: str, max_tokens: int, tokenizer) -> str:
        """Compress text to fit a specific token budget while preserving Head/Tail.

        Standard truncation loses the bottom of a page. This keeps the start and
        the end, which is usually where summary and 'recent context' live.
        """
        initial_tokens = tokenizer.count(text)
        if initial_tokens <= max_tokens:
            return text

        # If it's a code block, use the code compressor first
        if "```" in text:
            text = self.compress(text)
            if tokenizer.count(text) <= max_tokens:
                return text

        # Split into Head and Tail (roughly 60% head, 40% tail)
        head_budget = int(max_tokens * 0.6)
        tail_budget = max_tokens - head_budget - 5  # minus a few for the marker

        head = tokenizer.truncate(text, head_budget)
        # To get the tail, we reverse, truncate, and reverse back (crude but effective for tokenizers)
        # Better: use a proper tail-truncate if the tokenizer supports it
        # Since tiktoken doesn't easily do tail-truncate, we'll estimate by character count
        # or just use the truncate function on the reversed string if possible.
        # However, for now, we'll use a simpler character-based slice for the tail fallback
        words = text.split()
        tail_text = " ".join(words[-int(tail_budget * 1.5):]) # Roughly 1.5 chars per token estimate
        tail = tokenizer.truncate(tail_text, tail_budget)

        return f"{head}\n\n[... {initial_tokens - max_tokens} tokens compressed ...]\n\n{tail}"

    # ── Code block compression ────────────────────────────────────────────────

    def _compress_code(self, text: str) -> str:
        code_pattern = r"```[\s\S]*?```"
        code_blocks  = list(re.finditer(code_pattern, text))

        if not code_blocks:
            return self._compress_prose(text)

        result   = []
        last_end = 0

        for match in code_blocks:
            before = text[last_end: match.start()]
            result.append(self._compress_prose(before))
            result.append(self._compress_code_block(match.group(0)))
            last_end = match.end()

        result.append(self._compress_prose(text[last_end:]))
        return "\n".join(result)

    def _compress_code_block(self, block: str) -> str:
        """Compress a fenced code block intelligently.

        Strategy (dev-aware):
        - Always keep the opening fence + language tag
        - Always keep import/require statements (give the model dependency context)
        - Always keep function/class/method signatures (structural skeleton)
        - Always keep the last N lines (where active work is happening)
        - Compress the middle body with a token-count marker
        """
        lines = block.split("\n")
        if len(lines) <= 25:
            return block

        fence_open  = lines[0]   # e.g. "```python"
        fence_close = lines[-1]  # "```"
        body_lines  = lines[1:-1]

        imports:    list[tuple[int, str]] = []
        signatures: list[tuple[int, str]] = []
        body_other: list[tuple[int, str]] = []

        for i, line in enumerate(body_lines):
            stripped = line.strip()
            if re.match(r'^(?:import |from .+ import |require\(|#include)', stripped):
                imports.append((i, line))
            elif re.match(
                r'^(?:def |async def |class |function |const \w+ ?= ?(?:async )?(?:function|\()|'
                r'let \w+ ?= ?(?:async )?(?:function|\()|'
                r'var \w+ ?= ?(?:async )?(?:function|\()|'
                r'fn |pub fn |pub async fn |impl |interface |type \w+ ?=|'
                r'export (?:default )?(?:function|class|const|async))',
                stripped,
            ):
                signatures.append((i, line))
            else:
                body_other.append((i, line))

        # Keep last 8 lines of body unconditionally (active work zone)
        tail_count    = min(8, len(body_lines))
        tail_lines    = body_lines[-tail_count:]
        tail_start_i  = len(body_lines) - tail_count

        # Signatures that are NOT in the tail
        sigs_to_keep  = [(i, l) for i, l in signatures if i < tail_start_i]
        # Imports that are NOT in the tail
        imps_to_keep  = [(i, l) for i, l in imports if i < tail_start_i]

        compressed_body: list[str] = []

        if imps_to_keep:
            compressed_body.extend(l for _, l in imps_to_keep[:10])
            if len(imps_to_keep) > 10:
                compressed_body.append(f"    # ... {len(imps_to_keep) - 10} more imports ...")

        if sigs_to_keep:
            compressed_body.append("")
            # Count how many body lines we're compressing
            shown_i  = {i for i, _ in imps_to_keep} | {i for i, _ in sigs_to_keep}
            omitted  = sum(1 for i, _ in body_other if i < tail_start_i and i not in shown_i)
            for idx, (i, sig) in enumerate(sigs_to_keep):
                compressed_body.append(sig)
                # Add a compact body placeholder after each signature
                compressed_body.append("    ...")
                if idx < len(sigs_to_keep) - 1:
                    compressed_body.append("")
            if omitted:
                compressed_body.append(f"    # [{omitted} lines of body compressed]")

        if tail_lines:
            compressed_body.append("")
            compressed_body.append("    # ... (recent work below) ...")
            compressed_body.extend(tail_lines)

        return "\n".join([fence_open] + compressed_body + [fence_close])

    # ── Prose compression ─────────────────────────────────────────────────────

    def _compress_prose(self, text: str) -> str:
        lines = text.split("\n")
        if len(lines) <= 8:
            return text

        significant: list[str] = []
        empty_count = 0

        for line in lines:
            if not line.strip():
                empty_count += 1
                continue
            if empty_count > 2:
                significant.append("...")
            significant.append(line)
            empty_count = 0

        return "\n".join(significant)

    # ── Error compression ─────────────────────────────────────────────────────

    def _compress_errors(self, text: str) -> str:
        """Keep the MOST RECENT errors, not the first ones.

        For dev sessions, the latest error is what matters — earlier ones were
        presumably fixed or are irrelevant to the current problem.
        """
        error_patterns = [
            r"Traceback \(most recent call last\):[\s\S]+?(?=\n\n|\Z)",
            r"Error:\s+.+",
            r"Exception:\s+.+",
            r"FAILED[\s\S]+?(?=\n\n|\Z)",
            r"warning:[\s\S]+?(?=\n\n|\Z)",
        ]

        for pattern in error_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if len(matches) > 3:
                # Keep the LAST 2 (most recent), not the first 2
                kept    = matches[-2:]
                removed = len(matches) - 2

                # Rebuild text: pre-first-kept + omission notice + kept errors + tail
                tail   = text[matches[-1].end():]
                result = text[: matches[0].start()]
                result += f"\n[... {removed} earlier similar errors omitted ...]\n\n"
                for m in kept:
                    result += m.group(0) + "\n"
                result += tail
                text = result
                break

        return text

    # ── Path compression ──────────────────────────────────────────────────────

    def _compress_paths(self, text: str) -> str:
        # Match absolute paths (/foo/bar), home-relative (~/.config),
        # explicit relative (./src/file.py), and bare relative (src/foo/bar.py).
        path_pattern = r'(?:~|\.{1,2})?/[\w./-]+|(?<![\w/])(?:\w[\w.-]*/){2,}[\w.-]+'
        paths        = re.findall(path_pattern, text)
        unique_paths = list(dict.fromkeys(paths))

        if len(unique_paths) > 5:
            short_paths = {
                p: self._shorten_path(p)
                for p in unique_paths[:10]
                if len(p) > 35
            }
            for full, short in short_paths.items():
                text = text.replace(full, short)

        return text

    def _shorten_path(self, path: str) -> str:
        # Preserve leading sigil so absolute/home paths stay recognisable.
        if path.startswith("/"):
            prefix = "/"
            inner  = path.lstrip("/")
        elif path.startswith("~/"):
            prefix = "~/"
            inner  = path[2:]
        elif path.startswith("./"):
            prefix = "./"
            inner  = path[2:]
        else:
            prefix = ""
            inner  = path

        parts = inner.split("/")
        if len(parts) <= 3:
            return path
        # Keep the first component + last 2 — enough to identify the file.
        return f"{prefix}{parts[0]}/.../{parts[-2]}/{parts[-1]}"

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _remove_empty_lines(self, text: str) -> str:
        lines  = text.split("\n")
        result = []
        for line in lines:
            if line.strip() or (result and result[-1].strip()):
                result.append(line)
        return "\n".join(result)

    def _normalize_whitespace(self, text: str) -> str:
        text = re.sub(r"[ \t]+",  " ",    text)
        text = re.sub(r"\n{3,}",  "\n\n", text)
        return text.strip()


# ── Standalone utility functions ──────────────────────────────────────────────

def extract_code_blocks(text: str) -> list[str]:
    return re.findall(r"```(?:\w+)?\n([\s\S]*?)```", text)


def extract_error_messages(text: str) -> list[str]:
    errors = []
    for pattern in [
        r"(TypeError|ValueError|AttributeError|ImportError|ModuleNotFoundError|"
        r"RuntimeError|SyntaxError|NameError)[:\s]+([^\n]{10,150})",
        r"Traceback[\s\S]{0,500}",
    ]:
        errors.extend(re.findall(pattern, text, re.IGNORECASE))
    return errors


def detect_content_type(text: str) -> str:
    if "```" in text and any(
        kw in text.lower()
        for kw in ["def ", "class ", "import ", "function", "const ", "let "]
    ):
        return "code"
    if any(kw in text.lower() for kw in ["error", "exception", "failed", "traceback"]):
        return "error"
    if re.search(r"/[\w/.-]+\.\w+", text):
        return "file_path"
    if re.search(r"^\s*(git|npm|pip|cargo|make|./)", text, re.MULTILINE):
        return "command"
    if text.startswith("#") or "decision" in text.lower()[:50]:
        return "decision"
    return "general"
