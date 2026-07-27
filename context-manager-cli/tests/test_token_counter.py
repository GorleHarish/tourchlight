from context_manager.memory.token_counter import TokenCounter, get_token_counter


def test_count_basic():
    c = TokenCounter()
    n = c.count("hello world")
    assert n > 0
    assert isinstance(n, int)


def test_count_empty():
    c = TokenCounter()
    assert c.count("") == 0


def test_estimate_fallback():
    """_estimate works regardless of tiktoken availability."""
    c = TokenCounter()
    n = c._estimate("the quick brown fox jumps over the lazy dog")
    assert n > 0
    assert isinstance(n, int)


def test_count_cjk():
    """CJK characters should produce a higher token count than plain ASCII."""
    c = TokenCounter()
    ascii_count = c.count("hello")
    cjk_count = c.count("你好世界")
    assert cjk_count >= ascii_count


def test_truncate_short_text():
    c = TokenCounter()
    text = "short"
    result = c.truncate(text, max_tokens=1000)
    assert result == text


def test_truncate_long_text():
    c = TokenCounter()
    text = "word " * 500
    result = c.truncate(text, max_tokens=5)
    assert c.count(result) <= 5
    assert len(result) < len(text)


def test_truncate_exact_boundary():
    c = TokenCounter()
    text = "hello world"
    budget = c.count(text)
    result = c.truncate(text, max_tokens=budget)
    assert result == text


def test_get_token_counter_caching():
    a = get_token_counter("cl100k_base")
    b = get_token_counter("cl100k_base")
    assert a is b


def test_get_token_counter_different_models():
    a = get_token_counter("cl100k_base")
    b = get_token_counter("p50k_base")
    assert a is not b
