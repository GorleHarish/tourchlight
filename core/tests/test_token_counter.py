import pytest
from core.memory.token_counter import TokenCounter, get_token_counter


def test_token_counter_basic():
    tc = TokenCounter()
    count = tc.count("Hello world")
    assert count > 0
    assert count < 10


def test_token_counter_empty():
    tc = TokenCounter()
    assert tc.count("") == 0
    assert tc.count(None) == 0
    assert tc.truncate(None, 10) == ""


def test_token_counter_truncate_short():
    tc = TokenCounter()
    text = "Hello world"
    assert tc.truncate(text, 100) == text


def test_token_counter_truncate_long():
    tc = TokenCounter()
    text = " ".join(["word"] * 1000)
    truncated = tc.truncate(text, 10)
    assert tc.count(truncated) <= 10


def test_get_token_counter_caching():
    tc1 = get_token_counter()
    tc2 = get_token_counter()
    assert tc1 is tc2


def test_get_token_counter_different_models():
    tc1 = get_token_counter("cl100k_base")
    tc2 = get_token_counter("p50k_base")
    assert tc1 is not tc2
