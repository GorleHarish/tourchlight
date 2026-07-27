import re
from typing import Optional
from ..memory.models import Message, MessageRole


# ── Formatting helpers ────────────────────────────────────────────────────────

def _role_label(msg: Message) -> str:
    if isinstance(msg.role, MessageRole):
        return msg.role.value.upper()
    return str(msg.role).upper()


def _role_is(msg: Message, role: MessageRole) -> bool:
    if isinstance(msg.role, MessageRole):
        return msg.role == role
    return msg.role == role.value


def _format_messages_for_summary(messages: list[Message], max_chars: int = 2000) -> str:
    lines = []
    for msg in messages:
        lines.append(f"--- {_role_label(msg)} ---")
        lines.append(msg.content[:max_chars])
        lines.append("")
    return "\n".join(lines)


# ── Extraction helpers ────────────────────────────────────────────────────────

_FILE_PATH_RE = re.compile(
    r'(?:^|[\s"\'`(])([\/~\.]?[\w\-\.]+(?:\/[\w\-\.]+)+\.\w{1,10})',
    re.MULTILINE,
)
_EMOJI_PATH_RE   = re.compile(r'📄\s*([\w/\.\-]+)')
_WRITTEN_PATH_RE = re.compile(r'(?:Written|written|Saved|saved|Created|created).*?(?:to|at)\s+([\w/\.\-]+)', re.IGNORECASE)
_TEST_FAIL_RE    = re.compile(
    r'(?:FAILED|ERROR)\s+([\w/\.::\-]+(?:::\w+)*)|'
    r'✗\s+(.+)|'
    r'× (.+)',
    re.MULTILINE,
)
_ERROR_RE        = re.compile(
    r'(?:TypeError|ValueError|AttributeError|ImportError|ModuleNotFoundError|'
    r'KeyError|IndexError|RuntimeError|SyntaxError|NameError|OSError|IOError)'
    r'[:\s]+([^\n]{10,100})',
)
_ARCH_KEYWORDS   = [
    "decided to use", "going with", "chose ", "will use", "architecture",
    "instead of", "rather than", "switched to", "migrated to", "refactor",
    "design pattern", "approach:", "strategy:", "we'll use", "let's use",
    "better to use", "recommend using",
]
_TRIED_FAIL_RE   = re.compile(
    r"(?:tried|attempted|doesn['\u2019]t work|didn['\u2019]t work|failed to|"
    r"not working|gave up on|abandoned|reverted|that approach)[^\n.]{0,120}",
    re.IGNORECASE,
)
_DEP_RE = re.compile(
    r'(?:pip install|pip3 install|npm install|yarn add|cargo add|go get)\s+([\w@/\-\.]+)',
    re.IGNORECASE,
)


def _extract_file_paths(text: str) -> list[str]:
    raw      = _FILE_PATH_RE.findall(text)
    emoji    = _EMOJI_PATH_RE.findall(text)
    written  = _WRITTEN_PATH_RE.findall(text)
    all_paths = list(dict.fromkeys(raw + emoji + written))
    return [p.strip() for p in all_paths
            if '.' in p.split('/')[-1] and len(p) > 3 and not p.startswith('http')]


def _extract_failing_tests(text: str) -> list[str]:
    results = []
    for groups in _TEST_FAIL_RE.findall(text):
        for g in groups:
            g = g.strip()
            if g and len(g) > 3:
                results.append(g)
    return list(dict.fromkeys(results))[:5]


def _extract_errors(text: str) -> list[str]:
    return list(dict.fromkeys(m.group(0)[:100] for m in _ERROR_RE.finditer(text)))[:3]


def _extract_code_signatures(code_block: str) -> list[str]:
    """Extract function/class/method signatures from a code block.

    This is used to keep the structural skeleton of large code blocks
    instead of discarding everything with a naive first/last-5-lines cut.
    """
    sigs = []
    for line in code_block.split("\n"):
        stripped = line.strip()
        if re.match(
            r'^(?:def |async def |class |function |const |let |var |fn |pub fn |'
            r'export (?:default )?(?:function|class|const)|interface |type |impl )',
            stripped,
        ):
            sigs.append(line.rstrip())
    return sigs


# ── LLM summarization prompts ─────────────────────────────────────────────────

DEV_SESSION_PROMPT = """\
You are a dev-session context compressor. Your job is to produce a compact,
information-dense summary that lets a local LLM resume a software-building
session without losing critical context.

Extract and preserve EXACTLY the following — nothing more, nothing less:

1. GOAL          — one sentence: what is being built / fixed
2. ACTIVE FILE   — the file most recently being worked on
3. TECH STACK    — languages, frameworks, tools detected
4. ARCH DECISIONS — architectural/design choices made (keep verbatim, these matter most)
5. FAILING TESTS  — exact test names / IDs still failing
6. ERRORS SEEN   — exact error messages that appeared (model needs these to not re-hit same wall)
7. TRIED & FAILED — approaches already tried that didn't work (CRITICAL: model must not re-suggest these)
8. FILES MODIFIED — list of files created or changed
9. DEPS ADDED    — packages installed this session
10. NEXT STEP    — what was about to be done when this was summarized

Format as compact labeled bullet points. Be terse. Every token counts.
Omit sections that have no content.

SESSION TO COMPRESS:
{conversation}

SUMMARY:"""

GENERAL_SUMMARIZE_PROMPT = """\
You are a context compression assistant. Summarize the conversation below,
preserving intent, key decisions, files changed, current status, and pending tasks.
Be concise. Format as structured notes.

CONVERSATION:
{conversation}

SUMMARY:"""


# ── Summarizers ───────────────────────────────────────────────────────────────

class ConversationSummarizer:
    """Summarizer with LLM-powered and rule-based fallback paths.

    When an llm_client is provided, uses the model itself to compress — this
    gives the best results for dev sessions because the model understands code.
    Falls back to DevSessionSummarizer.rule_based() when no client is set.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def summarize(self, messages: list[Message], focus: str = "general") -> str:
        if not messages:
            return "Empty conversation."

        if not self.llm_client:
            return self.simple_summarize(messages)

        prompt_template = DEV_SESSION_PROMPT if focus in ("code", "dev") else GENERAL_SUMMARIZE_PROMPT
        conversation    = _format_messages_for_summary(messages)
        full_prompt     = prompt_template.format(conversation=conversation)

        try:
            return await self.llm_client.chat([{"role": "user", "content": full_prompt}])
        except Exception:
            return self.simple_summarize(messages)

    def simple_summarize(self, messages: list[Message]) -> str:
        return DevSessionSummarizer.rule_based(messages)


class DevSessionSummarizer:
    """High-fidelity rule-based summarizer tuned for software build sessions.

    This is what runs when no LLM client is available (i.e. during compression
    triggered before the first response, or on very small context windows).
    It extracts the signals that matter most for fighting context rot:
    - What files are in play
    - What's failing and why
    - What was already tried (prevent re-suggestions)
    - What architectural choices were made
    - What the next step is
    """

    @staticmethod
    def rule_based(messages: list[Message]) -> str:
        if not messages:
            return "Empty conversation."

        user_msgs      = [m for m in messages if _role_is(m, MessageRole.USER)]
        assistant_msgs = [m for m in messages if _role_is(m, MessageRole.ASSISTANT)]
        tool_msgs      = [m for m in messages if _role_is(m, MessageRole.TOOL_RESULT)]

        parts: list[str] = []

        # ── Goal ─────────────────────────────────────────────────────────────
        if user_msgs:
            goal = user_msgs[0].content[:150].replace("\n", " ").strip()
            parts.append(f"GOAL: {goal}")

        # ── File activity ─────────────────────────────────────────────────────
        files_read:    set[str] = set()
        files_written: set[str] = set()
        commands_run:  list[str] = []
        failing_tests: list[str] = []
        errors_seen:   list[str] = []
        deps_added:    list[str] = []

        for m in tool_msgs:
            tn = m.metadata.get("tool_name", "")
            c  = m.content

            if tn in ("read_file", "READ_FILE"):
                for p in _extract_file_paths(c):
                    files_read.add(p)

            elif tn in ("write_file", "WRITE_FILE"):
                for p in _extract_file_paths(c):
                    files_written.add(p)

            elif tn in ("bash", "RUN_COMMAND"):
                # Grab the command itself from the tool call content
                cmd_m = re.search(r'⚡\s*RUN_COMMAND\((.+?)\)', c)
                if cmd_m:
                    commands_run.append(cmd_m.group(1)[:80])
                else:
                    # Fall back: first non-empty line of output
                    first_line = next((l.strip() for l in c.split('\n') if l.strip()), "")
                    if first_line:
                        commands_run.append(first_line[:80])

                for t in _extract_failing_tests(c):
                    if t not in failing_tests:
                        failing_tests.append(t)
                for e in _extract_errors(c):
                    if e not in errors_seen:
                        errors_seen.append(e)
                for dep in _DEP_RE.findall(c):
                    if dep not in deps_added:
                        deps_added.append(dep)

            # Catch file paths from all tool results
            for p in _extract_file_paths(c):
                files_read.add(p)

        active_file = ""
        if files_written:
            active_file = list(files_written)[-1]
        elif files_read:
            active_file = list(files_read)[-1]

        if active_file:
            parts.append(f"ACTIVE FILE: {active_file}")

        if files_written:
            parts.append(f"FILES MODIFIED: {', '.join(list(files_written)[:8])}")
        if files_read - files_written:
            parts.append(f"FILES READ: {', '.join(list(files_read - files_written)[:5])}")

        # ── Tech stack ────────────────────────────────────────────────────────
        all_text  = " ".join(m.content for m in messages)
        from ..memory.manager import _extract_tech_stack
        tech = _extract_tech_stack(all_text)
        if tech:
            parts.append(f"TECH STACK: {', '.join(tech)}")

        # ── Architectural decisions ───────────────────────────────────────────
        arch: list[str] = []
        for m in assistant_msgs:
            lower = m.content.lower()
            if any(kw in lower for kw in _ARCH_KEYWORDS):
                for sentence in re.split(r'[.!?\n]', m.content):
                    if any(kw in sentence.lower() for kw in _ARCH_KEYWORDS):
                        entry = sentence.strip()[:200]
                        if entry and entry not in arch:
                            arch.append(entry)
                            break
        if arch:
            parts.append("ARCH DECISIONS:")
            for a in arch[-4:]:
                parts.append(f"  - {a}")

        # ── Failing tests ─────────────────────────────────────────────────────
        if failing_tests:
            parts.append(f"FAILING TESTS: {', '.join(failing_tests[:4])}")

        # ── Errors seen ───────────────────────────────────────────────────────
        if errors_seen:
            parts.append("ERRORS SEEN:")
            for e in errors_seen[:3]:
                parts.append(f"  - {e}")

        # ── Tried and failed ──────────────────────────────────────────────────
        tried: list[str] = []
        for m in user_msgs + assistant_msgs:
            for match in _TRIED_FAIL_RE.finditer(m.content):
                entry = match.group(0).strip()
                if entry and entry not in tried:
                    tried.append(entry)
        if tried:
            parts.append("TRIED & FAILED (do not re-suggest):")
            for t in tried[-4:]:
                parts.append(f"  - {t}")

        # ── Deps added ────────────────────────────────────────────────────────
        if deps_added:
            parts.append(f"DEPS ADDED: {', '.join(deps_added[:5])}")

        # ── Commands run ──────────────────────────────────────────────────────
        if commands_run:
            parts.append(f"COMMANDS RUN: {'; '.join(commands_run[:4])}")

        # ── Code output ───────────────────────────────────────────────────────
        # Extract function/class signatures from the last significant code block
        last_code_sigs: list[str] = []
        for m in reversed(assistant_msgs):
            code_blocks = re.findall(r'```[\w]*\n([\s\S]*?)```', m.content)
            for block in reversed(code_blocks):
                sigs = _extract_code_signatures(block)
                if sigs:
                    last_code_sigs = sigs[:8]
                    break
            if last_code_sigs:
                break
        if last_code_sigs:
            parts.append("LAST CODE STRUCTURE:")
            parts.extend(f"  {s}" for s in last_code_sigs)

        # ── Exchange count ────────────────────────────────────────────────────
        parts.append(
            f"EXCHANGES: {len(user_msgs)} user / {len(assistant_msgs)} assistant / {len(tool_msgs)} tool"
        )

        # ── Last question & answer ────────────────────────────────────────────
        if len(user_msgs) > 1:
            last_q = user_msgs[-1].content[:120].replace("\n", " ").strip()
            parts.append(f"LAST QUESTION: {last_q}")

        if assistant_msgs:
            last_a = assistant_msgs[-1].content[:200].replace("\n", " ").strip()
            parts.append(f"LAST ANSWER: {last_a}")

        return "\n".join(parts)


class IncrementalSummarizer:
    """Extends an existing summary with new messages without re-summarizing everything."""

    def __init__(self, base_summary: str = ""):
        self.base_summary = base_summary

    async def extend(self, new_messages: list[Message], llm_client=None) -> str:
        if not new_messages:
            return self.base_summary

        if not llm_client:
            return self._simple_extend(new_messages)

        prompt = (
            "Extend this dev-session summary with the new messages. "
            "Update only what changed. Be terse — every token counts.\n\n"
            f"CURRENT SUMMARY:\n{self.base_summary}\n\n"
            f"NEW MESSAGES:\n{_format_messages_for_summary(new_messages, max_chars=1500)}\n\n"
            "EXTENDED SUMMARY:"
        )
        try:
            return await llm_client.chat([{"role": "user", "content": prompt}])
        except Exception:
            return self._simple_extend(new_messages)

    def _simple_extend(self, messages: list[Message]) -> str:
        additions: list[str] = []
        for msg in messages[-5:]:
            role    = msg.role.value if isinstance(msg.role, MessageRole) else str(msg.role)
            content = msg.content[:120].replace("\n", " ")

            if role == MessageRole.USER.value:
                additions.append(f"User: {content}")
            elif role == MessageRole.TOOL_RESULT.value:
                tool = msg.metadata.get("tool_name", "tool")
                # Include first error if present
                err = next(iter(_extract_errors(msg.content)), None)
                additions.append(f"{tool}: {'❌ ' + err if err else '✓ done'}")
            elif role == MessageRole.ASSISTANT.value:
                sigs = _extract_code_signatures(msg.content)
                if sigs:
                    additions.append(f"Code: {sigs[0]}")
                elif "```" in msg.content:
                    additions.append("Code block generated")
                else:
                    additions.append(f"Response: {content[:80]}")

        new_part = "; ".join(additions) if additions else "continued"
        return f"{self.base_summary}\n• Recent: {new_part}"
