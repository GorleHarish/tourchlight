"""
Unit tests for transient LLM timeout/connection retry behavior in the solve loop.

Guards against the "loop terminated by error: timed out" failure mode where a
transient local-server stall kills the entire task instead of retrying.
"""

import asyncio

import pytest

from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized


def _bare_engine():
    """Construct an engine without the heavy __init__ (client/sandbox setup)."""
    engine = object.__new__(RLMEngineOptimized)
    engine._notify_status_calls = []
    engine._total_llm_calls = 0
    return engine


# ── _is_transient_llm_error classification ────────────────────────────────


def test_classifies_timeout_messages_as_transient():
    engine = _bare_engine()
    for msg in (
        "Local engine server connection error on http://localhost:1234: <urlopen error timed out>",
        "⏰ Request timed out: Read timed out",
        "connection refused by peer",
        "connection reset by remote",
        "read timeout — model took too long",
        "connect timeout — LM Studio not responding",
        "broken pipe while streaming",
    ):
        assert engine._is_transient_llm_error(msg.lower()), msg


def test_classifies_fatal_errors_as_non_transient():
    engine = _bare_engine()
    for msg in (
        "SyntaxError: invalid syntax",
        "AttributeError: 'NoneType' object has no attribute 'foo'",
        "context overflow detected",
        "division by zero",
        "",
    ):
        assert not engine._is_transient_llm_error(msg.lower()), msg


# ── _stream_llm_with_retry ────────────────────────────────────────────────


class _FailingStreamEngine(RLMEngineOptimized):
    """Engine whose _stream_llm fails transiently N times then succeeds."""

    def __init__(self, fail_count: int, error: Exception):
        self.fail_count = fail_count
        self.error = error
        self.calls = 0
        self._notify_status_calls = []
        self._total_llm_calls = 0

    def _notify_status(self, state, details=None):
        self._notify_status_calls.append((state, details))

    async def _stream_llm(self, messages):
        self.calls += 1
        if self.calls <= self.fail_count:
            raise self.error
        return "<FINAL_ANSWER>done</FINAL_ANSWER>"


def test_retries_and_succeeds_after_transient_stalls():
    engine = _FailingStreamEngine(2, TimeoutError("urlopen error timed out"))
    result = asyncio.run(
        RLMEngineOptimized._stream_llm_with_retry.__get__(engine, RLMEngineOptimized)(
            [{"role": "user", "content": "hi"}], retries=2, backoff=0.0
        )
    )
    assert result == "<FINAL_ANSWER>done</FINAL_ANSWER>"
    assert engine.calls == 3  # 2 failures + 1 success
    assert len(engine._notify_status_calls) == 2


def test_reraises_after_retries_exhausted():
    engine = _FailingStreamEngine(3, TimeoutError("urlopen error timed out"))
    with pytest.raises(TimeoutError, match="timed out"):
        asyncio.run(
            RLMEngineOptimized._stream_llm_with_retry.__get__(
                engine, RLMEngineOptimized
            )([{"role": "user", "content": "hi"}], retries=1, backoff=0.0)
        )
    assert engine.calls == 2  # initial + 1 retry (retries=1)


def test_reraises_non_transient_immediately_without_retry():
    engine = _FailingStreamEngine(
        99, ValueError("AttributeError: 'NoneType' object has no attribute 'foo'")
    )
    with pytest.raises(ValueError):
        asyncio.run(
            RLMEngineOptimized._stream_llm_with_retry.__get__(
                engine, RLMEngineOptimized
            )([{"role": "user", "content": "hi"}], retries=5, backoff=0.0)
        )
    assert engine.calls == 1  # no retry for fatal errors
    assert engine._notify_status_calls == []


def test_backoff_grows_exponentially(monkeypatch):
    sleeps = []
    original_sleep = asyncio.sleep

    async def _record_sleep(seconds):
        sleeps.append(seconds)
        await original_sleep(0)

    monkeypatch.setattr(asyncio, "sleep", _record_sleep)

    engine = _FailingStreamEngine(2, TimeoutError("urlopen error timed out"))
    asyncio.run(
        RLMEngineOptimized._stream_llm_with_retry.__get__(engine, RLMEngineOptimized)(
            [{"role": "user", "content": "hi"}], retries=2, backoff=1.0
        )
    )
    assert sleeps == [1.0, 2.0]
