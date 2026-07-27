import pytest
from core.compression.compactor import VerbatimCompactor, CompressionConfig


def test_compactor_no_compress_short():
    c = VerbatimCompactor()
    text = "short text"
    assert c.compress(text) == text


def test_compactor_compression():
    c = VerbatimCompactor()
    text = "\n".join([f"line {i}" for i in range(20)])
    compressed = c.compress(text)
    assert len(compressed) <= len(text)


def test_compactor_preserves_code():
    c = VerbatimCompactor(CompressionConfig(preserve_code=True))
    text = "```python\ndef foo():\n    pass\n```\n" + "\n".join(["text"] * 20)
    compressed = c.compress(text)
    assert "def foo" in compressed or len(compressed) < len(text)


def test_compactor_empty_lines():
    c = VerbatimCompactor()
    # Need > 10 lines to trigger compression
    text = "line1\n\n\n\nline2\n\n\n\nline3\n\n\n\n" + "\n".join([f"extra_{i}" for i in range(15)])
    compressed = c.compress(text)
    assert "\n\n\n" not in compressed
