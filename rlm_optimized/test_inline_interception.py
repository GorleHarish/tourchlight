"""
Unit tests for inline code interception safety checks, tight regex matching, and existing file protection.
"""

import os
import tempfile
import pytest
from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized, _looks_like_full_file, _looks_like_prose_or_outline


class MockEngine(RLMEngineOptimized):
    def __init__(self, project_root="."):
        self.project_root = project_root
        self._current_phase = "code"


def test_tight_pre_text_regex_prevents_false_positives():
    engine = MockEngine()
    
    # 1. Conversational English containing loose words like 'for' or 'in' should NOT trigger interception
    response_false_positive = """
    In summary.md, we see the following results from the test run:

    ```text
    1. Test pass
    2. Test pass
    ```
    """
    res = engine._parse_response(response_false_positive)
    # Should NOT produce a WRITE_FILE tool execution on summary.md
    assert res[0] != "tool" or (res[4] != "WRITE_FILE")


def test_explicit_pre_text_path_declaration_triggers():
    engine = MockEngine()
    
    response_explicit = """
    Writing file `src/config.py`:

    ```python
    DATABASE_URL = "sqlite:///db.sqlite3"
    SECRET_KEY = "super-secret"
    DEBUG = True
    PORT = 8080
    HOST = "0.0.0.0"
    ```
    """
    res = engine._parse_response(response_explicit)
    assert res[0] == "tool"
    assert res[4] == "WRITE_FILE"
    assert res[5]["path"] == "src/config.py"


def test_in_block_comment_header_triggers():
    engine = MockEngine()

    response = """
    Here is the requested module:

    ```python
    # file: src/math_utils.py
    def add(a, b):
        return a + b
    ```
    """
    res = engine._parse_response(response)
    assert res[0] == "tool"
    assert res[4] == "WRITE_FILE"
    assert res[5]["path"] == "src/math_utils.py"
    assert "# file: src/math_utils.py" not in res[5]["content"]


def test_unified_mode_triggers_in_block_annotation_even_if_phase_chat():
    engine = MockEngine()
    engine.execution_mode = "unified"
    engine._current_phase = "chat"

    response = """
    Here is the file you requested:

    ```python
    # file: src/server.py
    def run_server():
        pass
    ```
    """
    res = engine._parse_response(response)
    assert res[0] == "tool"
    assert res[4] == "WRITE_FILE"
    assert res[5]["path"] == "src/server.py"


def test_existing_file_partial_snippet_protection():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an existing file with 30 lines of code
        file_path = os.path.join(tmpdir, "existing_file.py")
        with open(file_path, "w") as f:
            f.write("# Existing large module\n" + "x = 1\n" * 30)

        engine = MockEngine(project_root=tmpdir)

        # Small 2-line partial snippet for existing file
        response_snippet = f"""
        Here is a small snippet for file: {file_path}

        ```python
        def foo():
            pass
        ```
        """
        res = engine._parse_response(response_snippet)
        # Should skip overwriting existing file with small snippet
        assert res[0] != "tool"


def test_detect_phase_prioritizes_write_and_file_extensions():
    engine = MockEngine()
    phase = engine._detect_phase('write a message.txt file with message "hi write file working successfully"')
    assert phase == "code"


def test_looks_like_full_file_helper():
    assert _looks_like_full_file("import os\nimport sys\ndef main(): pass", "app.py") is True
    assert _looks_like_full_file("print('hi')", "app.py") is False
