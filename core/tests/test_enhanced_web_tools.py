"""
Tests for enhanced web tools and anti-blocking capabilities in core/tools/implementations.py.
"""

import os
import tempfile
import pytest
from core.tools.implementations import (
    StructurePreservingHTMLParser,
    _get_browser_headers,
    _augment_query_with_project_deps,
    tool_web_fetch_impl,
)


def test_structure_preserving_html_parser():
    html_input = """
    <html>
        <head><title>Test Doc</title></head>
        <body>
            <nav><header><a href="/home">Home</a></header></nav>
            <h1>Getting Started with PyTorch</h1>
            <p>PyTorch is a machine learning framework.</p>
            <pre><code>import torch
x = torch.tensor([1.0, 2.0])</code></pre>
            <footer>Copyright 2026</footer>
        </body>
    </html>
    """
    parser = StructurePreservingHTMLParser()
    parser.feed(html_input)
    md = parser.get_markdown()

    assert "# Getting Started with PyTorch" in md
    assert "PyTorch is a machine learning framework." in md
    assert "import torch" in md
    # Ensure nested <pre><code> does not create double backtick blocks
    assert "```\n\n```" not in md
    assert "Home" not in md  # nav/header stripped
    assert "Copyright 2026" not in md  # footer stripped


def test_get_browser_headers():
    headers = _get_browser_headers()
    assert "User-Agent" in headers
    assert "Chrome/" in headers["User-Agent"]
    assert "Sec-Ch-Ua" in headers
    assert headers["Sec-Fetch-Dest"] == "document"


def test_augment_query_with_project_deps_pyproject():
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = os.path.join(tmpdir, "pyproject.toml")
        with open(pyproject_path, "w", encoding="utf-8") as f:
            f.write('[tool.poetry.dependencies]\npydantic = "^2.7.0"\n')

        query = "pydantic BaseModel validator"
        augmented = _augment_query_with_project_deps(query, tmpdir)
        assert "v2" in augmented


def test_augment_query_pep621_pyproject():
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = os.path.join(tmpdir, "pyproject.toml")
        with open(pyproject_path, "w", encoding="utf-8") as f:
            f.write('dependencies = ["pydantic>=2.8.0"]\n')

        query = "pydantic BaseModel validator"
        augmented = _augment_query_with_project_deps(query, tmpdir)
        assert "v2" in augmented


def test_augment_query_with_project_deps_package_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_path = os.path.join(tmpdir, "package.json")
        with open(pkg_path, "w", encoding="utf-8") as f:
            f.write('{\n  "dependencies": {\n    "react": "^19.0.0"\n  }\n}\n')

        query = "react useActionState hook"
        augmented = _augment_query_with_project_deps(query, tmpdir)
        assert "v19" in augmented


def test_tool_web_fetch_no_url_or_none():
    assert "Fetch error" in tool_web_fetch_impl({}, "/tmp")
    assert "Fetch error" in tool_web_fetch_impl({"url": None}, "/tmp")
    assert "Fetch error" in tool_web_fetch_impl({"url": ""}, "/tmp")


def test_none_query_augment_handling():
    assert _augment_query_with_project_deps(None, "/tmp") == ""
