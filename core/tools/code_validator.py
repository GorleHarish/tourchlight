"""Code syntax verification, zero-overhead formatting, stub detection, and auto-repair."""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Union

_REJECT_ON_STUB_DEFAULT = True

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
