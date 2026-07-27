"""
VerbatimCompactor — compress text while preserving code structure.
"""

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
    """Compress text while preserving the content that matters most for dev sessions."""

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
        initial_tokens = tokenizer.count(text)
        if initial_tokens <= max_tokens:
            return text
        if "```" in text:
            text = self.compress(text)
            if tokenizer.count(text) <= max_tokens:
                return text
        head_budget = int(max_tokens * 0.6)
        tail_budget = max_tokens - head_budget - 5
        head = tokenizer.truncate(text, head_budget)
        words = text.split()
        tail_text = " ".join(words[-int(tail_budget * 1.5):])
        tail = tokenizer.truncate(tail_text, tail_budget)
        return f"{head}\n\n[... {initial_tokens - max_tokens} tokens compressed ...]\n\n{tail}"

    def _compress_code(self, text: str) -> str:
        code_pattern = r"```[\s\S]*?```"
        code_blocks = list(re.finditer(code_pattern, text))
        if not code_blocks:
            return self._compress_prose(text)
        result = []
        last_end = 0
        for match in code_blocks:
            before = text[last_end:match.start()]
            result.append(self._compress_prose(before))
            result.append(self._compress_code_block(match.group(0)))
            last_end = match.end()
        result.append(self._compress_prose(text[last_end:]))
        return "\n".join(result)

    def _compress_code_block(self, block: str) -> str:
        lines = block.split("\n")
        if len(lines) <= 10:
            return block
        header = lines[0]
        footer = lines[-1] if lines[-1].strip() == "```" else ""
        body = lines[1:-1] if footer else lines[1:]
        if self.config.aggressive_mode:
            sigs = [l for l in body if re.match(r'^\s*(?:def |async def |class |function |const |fn |pub fn )', l)]
            if sigs:
                return f"{header}\n" + "\n".join(sigs) + f"\n{footer}"
        kept = body[:5] + ["..."] + body[-3:] if len(body) > 10 else body
        return f"{header}\n" + "\n".join(kept) + (f"\n{footer}" if footer else "")

    def _compress_prose(self, text: str) -> str:
        if not text.strip():
            return text
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) <= 3:
            return text
        if self.config.aggressive_mode:
            return " ".join(sentences[:2]) + " ..."
        return " ".join(sentences[:3]) + " ..."

    def _compress_errors(self, text: str) -> str:
        error_pattern = r'(?:Traceback|Error|Exception|FAILED).*?(?:\n\s+.*?)*'
        errors = list(re.finditer(error_pattern, text, re.MULTILINE | re.DOTALL))
        if len(errors) <= 2:
            return text
        result = text
        for err in errors[:-2]:
            replacement = err.group(0).split("\n")[0] + " [compressed]"
            result = result.replace(err.group(0), replacement, 1)
        return result

    def _compress_paths(self, text: str) -> str:
        path_pattern = r'📄\s*([\w/\.\-]+)'
        paths = list(re.finditer(path_pattern, text))
        if len(paths) <= 3:
            return text
        return text

    def _remove_empty_lines(self, text: str) -> str:
        return re.sub(r'\n{3,}', '\n\n', text)

    def _normalize_whitespace(self, text: str) -> str:
        lines = text.split("\n")
        return "\n".join(l.rstrip() for l in lines)
