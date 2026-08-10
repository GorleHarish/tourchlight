"""
Regression guard for the TurboQuant GBNF grammar-parser incompatibility.

The TurboQuant llama.cpp fork's GBNF parser rejects two constructs that the
previous server accepted:

  1. rules whose continuation line STARTS with ``|``
     -> "parse: error parsing grammar: expecting name at | ..."
  2. the ``\\-`` / ``\\+`` escapes inside character classes
     -> "parse: error parsing grammar: unknown escape at \\- ..."

When the grammar fails to parse, llama-server logs "failed to parse grammar"
and proceeds UNCONSTRAINED. That silently broke tool-call decision making in
the solve loop and produced mid-stream client timeouts ("loop terminated by
error: timed out"). These tests keep ``grammar.gbnf`` compatible with the
TurboQuant parser so that failure mode cannot return unnoticed.

The server-backed test is optional: it skips when no local llama-server is
reachable (e.g., CI), so the structural checks are the primary gate.
"""

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from core.tools.schemas import TOOL_SCHEMAS

RLM_DIR = Path(__file__).parent
GRAMMAR_FILE = RLM_DIR / "grammar.gbnf"
LOG_FILE = RLM_DIR.parent / ".torchlight" / "llama_server.log"
BASE_URL = "http://127.0.0.1:8080"

# Rules that must stay flattened to a single line (were previously split with
# leading-'|' continuation lines the TurboQuant parser rejects).
SINGLE_LINE_RULES = {
    "action",
    "tool-kv-name-first",
    "tool-kv-args-first",
    "tool-name-val",
    "tool-name-str",
    "write-file-unit",
    "code-unit",
    "query-unit",
    "error-unit",
    "answer-unit",
    "json-val",
    "string-char",
    "number-val",
}


def _grammar_text() -> str:
    return GRAMMAR_FILE.read_text(encoding="utf-8")


def _code_lines(text: str) -> list[str]:
    """Non-comment, non-blank lines (rules only)."""
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        out.append(line)
    return out


def _scan_tokens(body: str) -> list[str]:
    """Yield bare-word rule references, skipping string literals, char
    classes, inline '#' comments, and structural punctuation."""
    tokens: list[str] = []
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if c == '"':
            i += 1
            while i < n:
                if body[i] == "\\":
                    i += 2
                    continue
                if body[i] == '"':
                    i += 1
                    break
                i += 1
        elif c == "[":
            while i < n and body[i] != "]":
                i += 1
            i += 1
        elif c == "#":
            break  # trailing inline comment
        elif c.isalnum() or c in "_-":
            j = i
            while j < n and (body[j].isalnum() or body[j] in "_-"):
                j += 1
            tokens.append(body[i:j])
            i = j
        else:
            i += 1
    return tokens


def _strip_inline_comment(body: str) -> str:
    """Return ``body`` up to (but not including) a top-level '#' comment,
    ignoring '#' inside string literals and char classes."""
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if c == '"':
            i += 1
            while i < n:
                if body[i] == "\\":
                    i += 2
                    continue
                if body[i] == '"':
                    i += 1
                    break
                i += 1
        elif c == "[":
            while i < n and body[i] != "]":
                i += 1
            i += 1
        elif c == "#":
            return body[:i]
        else:
            i += 1
    return body


def _parse_rules(text: str) -> dict[str, str]:
    """Map rule name -> raw (comment-stripped) rule body."""
    rules: dict[str, str] = {}
    for line in _code_lines(text):
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)\s*::=\s*(.*)$", line.strip())
        assert m is not None, f"line is not a rule definition: {line!r}"
        name, body = m.group(1), m.group(2)
        rules[name] = _strip_inline_comment(body)
    return rules


def test_grammar_file_present():
    assert GRAMMAR_FILE.exists(), f"missing grammar file: {GRAMMAR_FILE}"


def test_no_leading_bar_continuations():
    """TurboQuant parser rejects rule continuations that START with '|'."""
    for lineno, line in enumerate(_code_lines(_grammar_text()), start=1):
        assert not line.strip().startswith("|"), (
            f"line {lineno} starts a rule body with '|' — TurboQuant's parser "
            f"rejects this ('expecting name at | ...'). Flatten the rule onto "
            f"a single line: {line.strip()!r}"
        )


def test_no_rejected_char_class_escapes():
    """TurboQuant parser rejects '\\-' / '\\+' escapes in char classes."""
    text = _grammar_text()
    for lineno, line in enumerate(text.splitlines(), start=1):
        if "\\-" in line or "\\+" in line:
            pytest.fail(
                f"line {lineno} uses a rejected \\- / \\+ escape: {line.strip()!r}. "
                f"Use an alternation such as ( '+' | '-' ) instead of [\\+\\-]."
            )


def test_every_rule_defines_an_alternative():
    rules = _parse_rules(_grammar_text())
    assert rules, "no rules parsed from grammar file"
    for name, body in rules.items():
        assert body.strip(), f"rule {name!r} has an empty alternative set"
    assert "root" in rules  # sanity: the root rule exists


def test_every_referenced_rule_is_defined():
    text = _grammar_text()
    rules = _parse_rules(text)
    defined = set(rules)
    for name, body in rules.items():
        for ref in _scan_tokens(body):
            assert ref in defined, f"rule {name!r} references undefined rule {ref!r}"


def test_required_rules_stay_on_a_single_line():
    """Alternative sets that were flattened must stay flattened — this catches
    an accidental re-introduction of the broken continuation style."""
    text = _grammar_text()
    rules = _parse_rules(text)
    seen = set(rules)
    for name in SINGLE_LINE_RULES:
        assert name in seen, f"expected single-line rule {name!r} not found"
        assert rules[name].strip(), f"rule {name!r} has empty body"


def _grammar_tool_names() -> set[str]:
    """Tool names the grammar whitelists (from tool-name-val, the <tool_call>
    JSON variant — tool-name-str must stay in lockstep with it)."""
    rules = _parse_rules(_grammar_text())
    body = rules.get("tool-name-val", "")
    return set(re.findall(r'\\"([A-Z_]+)\\"', body))


def test_grammar_whitelist_matches_registry():
    """Every registered tool must be token-allowed by the grammar, and no tool
    may be grammar-allowed without a registry entry. A drift here advertises a
    tool the model cannot express (silent token-block), or worse, accepts one
    the registry does not implement."""
    grammar_tools = _grammar_tool_names()
    registered = set(TOOL_SCHEMAS.keys())
    assert grammar_tools == registered, (
        "grammar tool-name-val whitelist drifted from TOOL_SCHEMAS registry:\n"
        f"  in grammar but NOT registered: {sorted(grammar_tools - registered)}\n"
        f"  registered but NOT in grammar: {sorted(registered - grammar_tools)}"
    )


def test_no_reasoning_rule():
    """v2.2 removed the reasoning rule: it masked EOS (which contains '<'),
    forcing prose rambles that burned the token budget and never hit
    finish_reason: stop. Re-introducing it silently regresses the solve loop."""
    rules = _parse_rules(_grammar_text())
    assert "reasoning" not in rules, (
        "'reasoning' rule was removed in v2.2 — it masks EOS and produces "
        "unterminated prose. Put plans in implementation_plan.md instead."
    )


def test_root_is_single_action():
    """root must be exactly one action. 'step+' forced a second action after
    every valid tool call, so generation continued past the call and rambled."""
    rules = _parse_rules(_grammar_text())
    root = rules.get("root", "")
    assert re.fullmatch(r"\s*action\s+ws\s*", root), (
        f"root must be 'action ws' (single action per response). Found: {root!r}"
    )


def _server_reachable() -> bool:
    if not LOG_FILE.exists():
        return False
    try:
        req = urllib.request.Request(f"{BASE_URL}/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001
        return False


def test_grammar_parses_on_live_server():
    """Post the grammar to the running server and confirm it does NOT log
    'failed to parse grammar' (which silently disables constraint)."""
    if not _server_reachable():
        pytest.skip("no local llama-server on :8080 — structural checks only")

    grammar = _grammar_text()
    log_before = LOG_FILE.stat().st_size

    payload = {
        "model": None,  # filled from /v1/models below
        "messages": [
            {
                "role": "user",
                "content": "Answer with a short word inside a FINAL_ANSWER tag.",
            }
        ],
        "max_tokens": 24,
        "temperature": 0.0,
        "grammar": grammar,
        "stream": False,
    }

    req = urllib.request.Request(f"{BASE_URL}/v1/models", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        body = {}
    models = body.get("data") or body.get("models") or []
    if not models:
        pytest.skip("server reports no models — cannot run inference test")
    payload["model"] = (
        models[0].get("id") or models[0].get("model") or models[0].get("name")
    )

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            response_body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        pytest.fail(
            f"server rejected grammar request: HTTP {e.code} {e.read().decode()[:300]}"
        )

    added = LOG_FILE.read_bytes()[log_before:]
    assert b"failed to parse grammar" not in added, (
        "grammar.gbnf failed to parse on the running llama-server — "
        "generation is running UNCONSTRAINED (broken tool-call loop). "
        "See grammar file comments about TurboQuant parser compatibility."
    )

    try:
        choice = response_body["choices"][0]
        content = choice["message"]["content"]
        finish_reason = choice.get("finish_reason")
    except (KeyError, IndexError, TypeError):
        pytest.fail(f"unexpected API response shape: {str(response_body)[:300]}")
    assert finish_reason == "stop", (
        f"expected finish_reason 'stop' but got {finish_reason!r}; content="
        f"{content!r}. A non-'stop' reason means the grammar let generation "
        "run to a limit instead of terminating cleanly."
    )
    assert re.search(
        r"</(tool_call|TOOL|WRITE_FILE|CODE|FINAL_ANSWER|SUB_QUERY|ERROR)>", content
    ), (
        "constrained response did not contain a well-formed action tag; "
        f"content={content!r}. This is the prose-ramble regression — see "
        "grammar v2.2 comments about the removed 'reasoning' rule."
    )
