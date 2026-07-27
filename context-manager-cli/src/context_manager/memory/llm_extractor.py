"""
LLM-powered SessionState extractor.

Replaces the regex-based _merge_summary_into_state() with a single focused
LLM call that returns structured JSON.  The model reads a compressed view of
the conversation and fills every SessionState field in one shot — giving much
higher recall for naturally-phrased arch decisions, tried-and-failed attempts,
and blockers that regex patterns routinely miss.

Design principles
─────────────────
• Single call, low max_tokens (256).  We ask for JSON only, no prose.
• Temperature=0 — we want deterministic extraction, not creativity.
• Strict JSON schema defined in the prompt — no ambiguity for the model.
• Hard timeout (30 s) — extraction must never stall the compression path.
• Falls back silently to the caller's existing regex results on ANY error.
• Never overwrites a field that already has richer data from regex pass;
  it merges instead (LLM findings are appended, not replaced).

Usage
─────
    extractor = LLMStateExtractor(lm_client)
    await extractor.extract_and_merge(messages, session_state)
"""

import json
import logging
import re
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..api.lmstudio import LMStudioClient
    from .models import Message, SessionState

logger = logging.getLogger(__name__)

# ── Prompt ────────────────────────────────────────────────────────────────────
#
# The prompt is intentionally terse.  Local models have limited context and we
# want the entire instruction to fit in < 300 tokens, leaving room for the
# conversation excerpt and the JSON output.

_EXTRACTION_PROMPT = """\
Extract structured facts from this dev session. Reply ONLY with a single valid
JSON object — no prose, no markdown fences, no extra keys.

JSON schema (all fields optional, use [] for empty lists, "" for empty strings):
{
  "intent":             "<one-sentence project goal>",
  "active_file":        "<file currently being edited>",
  "current_blocker":    "<what the developer is stuck on>",
  "arch_decisions":     ["<architectural/design choice verbatim>", ...],
  "tried_and_failed":   ["<approach that was tried and did NOT work>", ...],
  "errors_seen":        ["<exact error message or exception>", ...],
  "failing_tests":      ["<test name or ID still failing>", ...],
  "dependencies_added": ["<package name>", ...],
  "tech_stack":         ["<language or framework detected>", ...],
  "next_steps":         ["<what was about to be done>"]
}

Rules:
- arch_decisions: include any "decided to use X", "going with Y", "instead of Z" statements.
- tried_and_failed: include anything tried that didn't work. This is the most important field.
- errors_seen: copy the exception class + message verbatim (e.g. "ImportError: No module named 'x'").
- Keep each list item under 200 characters.
- Omit a field entirely rather than guessing.

SESSION:
{conversation}

JSON:"""

# How much of each message to include in the extraction view.
# Arch decisions and tried-and-failed clues appear early, so we bias toward
# the start of each message rather than a naive middle truncation.
_MSG_MAX_CHARS = 600

# Hard cap on the total conversation excerpt fed to the extractor.
# At 4 chars/token this is ~750 tokens — comfortable for a 2048-token window.
_EXCERPT_MAX_CHARS = 3000

# Token budget for the model's JSON reply.
_MAX_REPLY_TOKENS = 300

# Extraction call timeout (seconds).  Separate from the chat timeout so a
# slow extraction never blocks the user's next response.
_EXTRACTION_TIMEOUT_S = 30.0


# ── Conversation formatter ─────────────────────────────────────────────────────

def _build_excerpt(messages: "list[Message]") -> str:
    """Build a compact conversation view for the extraction prompt."""
    from .models import MessageRole

    lines: list[str] = []
    total = 0

    for msg in messages:
        role = msg.role if isinstance(msg.role, MessageRole) else MessageRole(msg.role)

        # Skip system summaries — they're already-compressed output and would
        # confuse the extractor with stale or circular information.
        if role == MessageRole.SYSTEM:
            continue

        label = {
            MessageRole.USER:        "USER",
            MessageRole.ASSISTANT:   "ASSISTANT",
            MessageRole.TOOL_RESULT: f"TOOL({msg.metadata.get('tool_name', '?')})",
        }.get(role, role.value.upper())

        content = msg.content[:_MSG_MAX_CHARS].replace("\n", " ").strip()
        line    = f"[{label}] {content}"
        total  += len(line)

        if total > _EXCERPT_MAX_CHARS:
            # Still add a truncation notice so the model knows there's more.
            lines.append("[... earlier messages omitted ...]")
            break

        lines.append(line)

    return "\n".join(lines)


# ── JSON parser ───────────────────────────────────────────────────────────────

def _parse_json_response(raw: str) -> Optional[dict]:
    """
    Robustly extract a JSON object from the model's response.

    Local models sometimes wrap output in ```json fences or add a brief
    preamble. This strips the noise before parsing.
    """
    # 1. Strip markdown fences
    raw = re.sub(r"```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
    raw = raw.replace("```", "").strip()

    # 2. Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 3. Find the first { ... } block
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


# ── State merger ──────────────────────────────────────────────────────────────

def _merge_into_state(data: dict, state: "SessionState") -> None:
    """
    Merge the extracted JSON fields into the existing SessionState.

    Strategy: LLM findings are *additive*.  We never discard what the
    per-message regex pass already captured — we only add new items that
    the regex missed.  Scalar fields (intent, active_file, current_blocker)
    are set only when currently empty, so the session's live values win.
    """

    def _add_unique(target: list, items) -> None:
        """Append items from LLM output that aren't already in the list."""
        if not isinstance(items, list):
            return
        for item in items:
            if isinstance(item, str):
                item = item.strip()[:200]
                if item and item not in target:
                    target.append(item)

    # Scalar fields — set only when empty (live regex state wins)
    if not state.intent and isinstance(data.get("intent"), str):
        state.intent = data["intent"].strip()[:200]

    if not state.active_file and isinstance(data.get("active_file"), str):
        state.active_file = data["active_file"].strip()[:200]

    if not state.current_blocker and isinstance(data.get("current_blocker"), str):
        state.current_blocker = data["current_blocker"].strip()[:200]

    # List fields — additive merge
    _add_unique(state.arch_decisions,     data.get("arch_decisions",     []))
    _add_unique(state.tried_and_failed,   data.get("tried_and_failed",   []))
    _add_unique(state.errors_seen,        data.get("errors_seen",        []))
    _add_unique(state.failing_tests,      data.get("failing_tests",      []))
    _add_unique(state.dependencies_added, data.get("dependencies_added", []))
    _add_unique(state.tech_stack,         data.get("tech_stack",         []))
    _add_unique(state.next_steps,         data.get("next_steps",         []))

    # Cap list sizes to prevent unbounded growth across many compressions
    state.arch_decisions     = state.arch_decisions[-20:]
    state.tried_and_failed   = state.tried_and_failed[-20:]
    state.errors_seen        = state.errors_seen[-10:]
    state.failing_tests      = state.failing_tests[-10:]
    state.dependencies_added = state.dependencies_added[-20:]
    state.next_steps         = state.next_steps[-5:]


# ── Public extractor class ────────────────────────────────────────────────────

class LLMStateExtractor:
    """
    Uses the local LLM to extract structured SessionState fields from a
    conversation batch at compression time.

    Parameters
    ----------
    client : LMStudioClient
        The already-initialised async client used for the main chat loop.
        Extraction reuses the same connection pool.
    enabled : bool
        Kill-switch.  Set to False to fall back to regex-only extraction
        (e.g. for very small context models where every token counts).
    """

    def __init__(self, client: "LMStudioClient", enabled: bool = True):
        self.client  = client
        self.enabled = enabled
        self._stats  = {"calls": 0, "hits": 0, "misses": 0, "errors": 0}

    # ── Main entry point ──────────────────────────────────────────────────────

    async def extract_and_merge(
        self,
        messages:  "list[Message]",
        state:     "SessionState",
    ) -> bool:
        """
        Run LLM extraction and merge findings into *state* in-place.

        Returns True when the extraction succeeded and produced at least one
        new fact, False otherwise.  Never raises — all errors are caught and
        logged so compression always continues.
        """
        if not self.enabled or not messages:
            return False

        self._stats["calls"] += 1

        try:
            excerpt = _build_excerpt(messages)
            if not excerpt.strip():
                return False

            prompt = _EXTRACTION_PROMPT.format(conversation=excerpt)

            # Use a short-lived client call with tight timeout so extraction
            # never stalls the main loop.
            import httpx
            from ..api.lmstudio import LMStudioClient, NON_STREAM_TIMEOUT

            extraction_timeout = httpx.Timeout(
                connect = 10.0,
                read    = _EXTRACTION_TIMEOUT_S,
                write   = 10.0,
                pool    = 5.0,
            )
            extraction_client = LMStudioClient(
                base_url = self.client.base_url,
                model    = self.client.model,
                timeout  = extraction_timeout,
            )

            async with extraction_client:
                raw = await extraction_client.chat(
                    messages    = [{"role": "user", "content": prompt}],
                    temperature = 0.0,      # deterministic extraction
                    max_tokens  = _MAX_REPLY_TOKENS,
                )

            data = _parse_json_response(raw)
            if data is None:
                logger.debug("LLMStateExtractor: JSON parse failed — raw=%s", raw[:200])
                self._stats["misses"] += 1
                return False

            _merge_into_state(data, state)
            self._stats["hits"] += 1
            return True

        except Exception as exc:
            # Extraction is best-effort — never crash compression
            logger.debug("LLMStateExtractor: extraction failed — %s", exc)
            self._stats["errors"] += 1
            return False

    # ── Diagnostics ───────────────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        """Return a copy of the call/hit/miss/error counters."""
        return dict(self._stats)

    def reset_stats(self) -> None:
        self._stats = {"calls": 0, "hits": 0, "misses": 0, "errors": 0}

    def __repr__(self) -> str:  # pragma: no cover
        s = self._stats
        return (
            f"LLMStateExtractor(enabled={self.enabled}, "
            f"calls={s['calls']}, hits={s['hits']}, "
            f"misses={s['misses']}, errors={s['errors']})"
        )
