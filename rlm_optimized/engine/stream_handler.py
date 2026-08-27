"""LLM transport streaming, stop-token repairing, and transient network error retry handling."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Optional


class StreamHandlerMixin:
    """Provides LLM token streaming and network resilience for RLMEngine."""

    # Stop tokens used by the LLM — the server strips these from output,
    # so we need to re-append them for the parser to match properly.
    _STOP_TAG_PAIRS = [
        ("<tool_call>", "</tool_call>"),
        ("<WRITE_FILE", "</WRITE_FILE>"),
        ("<TOOL>", "</TOOL>"),
        ("<TOOL ", "</TOOL>"),
        ("<tool>", "</tool>"),
        ("<tool ", "</tool>"),
        ("<CODE>", "</CODE>"),
        ("<FINAL_ANSWER>", "</FINAL_ANSWER>"),
        ("<SUB_QUERY>", "</SUB_QUERY>"),
        ("<ERROR>", "</ERROR>"),
        ("<action>", "</action>"),
    ]

    def _truncate_trailing_after_stop_tag(self, text: str) -> str:
        """Truncate any trailing rambling/hallucinated text after the first closed action tag."""
        for open_tag, close_tag in self._STOP_TAG_PAIRS:
            if open_tag.lower() in text.lower() and close_tag.lower() in text.lower():
                close_pos = text.lower().find(close_tag.lower()) + len(close_tag)
                return text[:close_pos].strip()
        return text

    def _repair_stop_tokens(self, text: str) -> str:
        """Re-append closing tags that were consumed as stop tokens by llama-server,
        and prune any trailing hallucinated text after completed action tags."""
        text = self._truncate_trailing_after_stop_tag(text)
        for open_tag, close_tag in self._STOP_TAG_PAIRS:
            # Check if text has the opening tag but NOT the closing tag
            if (
                open_tag.lower() in text.lower()
                and close_tag.lower() not in text.lower()
            ):
                text = text.rstrip() + close_tag
                break  # Only one action per response
        return text

    async def _stream_llm(self, messages: list[dict]) -> str:
        """Stream LLM response token-by-token cleanly without thread deadlocks."""
        loop = asyncio.get_running_loop()
        use_grammar = getattr(self, "_current_phase", "code") != "chat"
        if hasattr(self.client, "stream_chat_with_history"):
            queue = asyncio.Queue()
            sentinel = object()

            def _worker():
                try:
                    try:
                        stream = self.client.stream_chat_with_history(
                            messages, use_grammar=use_grammar
                        )
                    except TypeError:
                        stream = self.client.stream_chat_with_history(messages)
                    for chunk in stream:
                        loop.call_soon_threadsafe(queue.put_nowait, chunk)
                except Exception as e:
                    loop.call_soon_threadsafe(queue.put_nowait, e)
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, sentinel)

            loop.run_in_executor(None, _worker)

            chunks = []
            while True:
                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=60.0)
                except asyncio.TimeoutError as exc:
                    # LLM server stopped responding mid-stream. Raise a
                    # transient error instead of silently returning a truncated
                    # (possibly mid-tool-call) response so callers retry rather
                    # than feeding garbage into _parse_response.
                    raise asyncio.TimeoutError(
                        "LLM stream stalled: no tokens for 60s (timed out)"
                    ) from exc
                if isinstance(chunk, Exception):
                    raise chunk
                if chunk is sentinel:
                    break
                chunks.append(chunk)
                if self.on_token:
                    try:
                        self.on_token(chunk)
                    except Exception:
                        pass
                else:
                    print(chunk, end="", flush=True)

                # Early-stop stream interceptor: only scan when the latest chunk contains tag closing indicators
                if ">" in chunk or "}" in chunk or "|" in chunk:
                    recent_tail = "".join(chunks[-30:])
                    recent_tail_lower = recent_tail.lower()
                    stop_matched = False
                    for open_tag, close_tag in self._STOP_TAG_PAIRS:
                        if close_tag.lower() in recent_tail_lower:
                            current_accum = "".join(chunks)
                            if open_tag.lower() in current_accum.lower():
                                close_pos = current_accum.lower().find(close_tag.lower()) + len(close_tag)
                                chunks = [current_accum[:close_pos]]
                                stop_matched = True
                                break
                    if stop_matched:
                        break

            if not self.on_token:
                print()
            response = "".join(chunks)
            return self._repair_stop_tokens(response)
        else:
            def _call_chat():
                try:
                    return self.client.chat_with_history(
                        messages, use_grammar=use_grammar
                    )
                except TypeError:
                    return self.client.chat_with_history(messages)

            raw = await loop.run_in_executor(None, _call_chat)
            return self._repair_stop_tokens(raw)

    # Timeout / connection errors are transient — the server may simply be
    # slow or momentarily stalled (common with local models). These must NOT
    # terminate the whole solve loop the way genuine fatal errors do.
    _TRANSIENT_LLM_ERROR_KEYWORDS = (
        "timed out",
        "timeout",
        "connection error",
        "connection refused",
        "connection reset",
        "urlopen",
        "read timeout",
        "connect timeout",
        "pool timeout",
        "server not responding",
        "no response",
        "broken pipe",
        "connection aborted",
        "socket",
    )

    def _is_transient_llm_error(self, err_str: str) -> bool:
        """True when an LLM error string looks like a transient server stall that
        a short retry can recover from (as opposed to a fatal programming error)."""
        if not err_str:
            return False
        return any(k in err_str for k in self._TRANSIENT_LLM_ERROR_KEYWORDS)

    async def _stream_llm_with_retry(
        self,
        messages: list[dict],
        retries: int = 2,
        backoff: float = 2.0,
    ) -> str:
        """Stream an LLM response, retrying up to ``retries`` times on transient
        server stalls (timeout / connection errors). Returns the first successful
        response; re-raises the last error once retries are exhausted."""
        # Hash prompt payload for ring-buffer duplicate generation skip
        try:
            p_bytes = json.dumps(messages, sort_keys=True, default=str).encode("utf-8")
            p_hash = hashlib.md5(p_bytes).hexdigest()
            if getattr(self, "_prompt_hash_ring", None) and self._prompt_hash_ring[-1] == p_hash:
                self._notify_status("SKIP", {"status": "Duplicate prompt hash detected in ring buffer; skipping generation turn."})
                return "<tool_call>{\"name\": \"ASK_USER\", \"arguments\": {\"question\": \"Duplicate prompt state detected. Please specify next directive.\"}}</tool_call>"
            if hasattr(self, "_prompt_hash_ring") and self._prompt_hash_ring is not None:
                self._prompt_hash_ring.append(p_hash)
        except Exception:
            pass

        last_err: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                return await self._stream_llm(messages)
            except Exception as err:  # noqa: BLE001
                if not self._is_transient_llm_error(str(err).lower()):
                    raise
                last_err = err
                self._notify_status(
                    "THINKING",
                    {
                        "status": (
                            f"LLM server stall detected (attempt {attempt + 1}) — "
                            f"retrying in {backoff}s"
                        ),
                        "error": str(err)[:120],
                    },
                )
                await asyncio.sleep(backoff)
                backoff = backoff * 2
        assert last_err is not None
        raise last_err
