"""
Unit tests for Torchlight Zero-Context Code Quality Harness.
"""

import json
import os
import tempfile
import pytest

from core.tools.implementations import (
    _normalize_whitespace,
    _detect_stubs,
    _check_syntax,
    _check_compile,
    _format_code_on_save,
    _validate_and_repair,
    _detect_truncation_stubs,
    tool_write_file_impl,
    tool_edit_file_impl,
    tool_verify_impl,
)


def test_normalize_whitespace():
    raw_code = "def foo():\n\ta = 1   \n\treturn a"
    normalized = _normalize_whitespace(raw_code)
    assert "\t" not in normalized
    assert "a = 1" in normalized
    assert normalized.endswith("\n")


def test_detect_stubs():
    code_with_python_stub = "def foo():\n    # TODO: implement later\n    pass"
    warning = _detect_stubs(code_with_python_stub)
    assert warning is not None
    assert "Stub Warning" in warning
    assert "Python TODO stub" in warning

    code_with_js_stub = "function foo() {\n  // ... rest of implementation ...\n}"
    warning_js = _detect_stubs(code_with_js_stub)
    assert warning_js is not None
    assert "JS/C code truncation stub" in warning_js

    clean_code = "def add(a, b):\n    return a + b\n"
    assert _detect_stubs(clean_code) is None


def test_check_syntax_python():
    valid_py = "def foo():\n    return 42\n"
    assert _check_syntax(valid_py, "test.py") is None

    invalid_py = "def foo():\n    return 42 ("
    warning = _check_syntax(invalid_py, "test.py")
    assert warning is not None
    assert "Syntax Warning" in warning


def test_check_syntax_json():
    valid_json = '{"name": "torchlight", "status": "ok"}'
    assert _check_syntax(valid_json, "config.json") is None

    invalid_json = '{"name": "torchlight", "status": }'
    warning = _check_syntax(invalid_json, "config.json")
    assert warning is not None
    assert "JSON Syntax Warning" in warning


def test_check_syntax_js_bracket_balance():
    valid_js = "function test() { console.log([1, 2, 3]); }"
    assert _check_syntax(valid_js, "app.js") is None

    unmatched_js = "function test() { console.log([1, 2, 3]; }"
    warning = _check_syntax(unmatched_js, "app.js")
    assert warning is not None
    assert "Unmatched closing bracket" in warning or "Unclosed bracket" in warning


def test_format_code_on_save_fallback():
    raw_code = "def foo():\n\ta = 1   "
    formatted = _format_code_on_save(raw_code, "script.py", os.getcwd())
    assert "\t" not in formatted
    assert formatted.endswith("\n")


def test_tool_write_file_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "stubbed.py")
        content = "def calculate():\n    # TODO: implement logic\n    pass\n"
        res = tool_write_file_impl({"path": file_path, "content": content}, tmpdir)
        assert "Written 3 lines" in res
        assert "Stub Warning" in res
        assert os.path.exists(file_path)


def test_makefile_tab_preservation():
    makefile_content = "all:\n\techo 'building'\n"
    res = _normalize_whitespace(makefile_content, "Makefile")
    assert "\techo" in res

    res_go = _normalize_whitespace("package main\n\tfunc main() {}\n", "main.go")
    assert "\tfunc" in res_go


def test_check_syntax_js_string_literal_brackets():
    js_code = 'const s = "closing brace } inside string";'
    assert _check_syntax(js_code, "script.js") is None


def test_tool_edit_file_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "main.py")
        initial_content = "def main():\n    print('hello')\n"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(initial_content)

        edit_args = {
            "path": file_path,
            "old_text": "print('hello')",
            "new_text": "# TODO: implement\n    print('world')",
        }
        res = tool_edit_file_impl(edit_args, tmpdir)
        assert "Surgically edited" in res
        assert "Stub Warning" in res
        with open(file_path, "r", encoding="utf-8") as f:
            edited_content = f.read()
        assert "world" in edited_content


def test_validate_and_repair_rejects_broken_python():
    status, payload = _validate_and_repair(
        "def broken_func(\n", "broken.py", os.getcwd()
    )
    assert status == "error"
    assert "Syntax error" in payload
    assert "NOT written" in payload


def test_validate_and_repair_accepts_valid_python():
    status, payload = _validate_and_repair(
        "def ok():\n    return 1\n", "ok.py", os.getcwd()
    )
    assert status == "ok"
    assert "return 1" in payload


def test_compile_gate_rejects_return_outside_function():
    # ast.parse passes this; compile() must catch it (RC-1 strict gate)
    assert _check_syntax("return 1\n", "x.py") is None
    compile_note = _check_compile("return 1\n", "x.py", os.getcwd())
    assert compile_note is not None
    assert "return" in compile_note

    status, payload = _validate_and_repair("return 1\n", "x.py", os.getcwd())
    assert status == "error"
    assert "Syntax error" in payload


def test_validate_and_repair_non_code_files_pass():
    status, payload = _validate_and_repair(
        "# just a readme\n", "README.md", os.getcwd()
    )
    assert status == "ok"
    status_json, _ = _validate_and_repair('{"ok": true}', "cfg.json", os.getcwd())
    assert status_json == "ok"


def test_reject_truncation_stub_by_default():
    content = "def run():\n    # ... rest of implementation ...\n    pass\n"
    assert _detect_truncation_stubs(content, "run.py") is not None

    status, payload = _validate_and_repair(content, "run.py", os.getcwd())
    assert status == "error"
    assert "truncation stubs" in payload


def test_reject_on_stub_false_allows_truncation():
    content = "def run():\n    # ... rest of implementation ...\n    pass\n"
    status, payload = _validate_and_repair(
        content, "run.py", os.getcwd(), reject_on_stub=False
    )
    assert status == "ok"


def test_force_bypasses_validation_gates():
    content = "def broken_func(\n# ... rest ...\n"
    status, payload = _validate_and_repair(
        content, "scaffold.py", os.getcwd(), force=True
    )
    assert status == "ok"


def test_write_file_blocks_broken_syntax_and_truncation():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "broken.py")
        res = tool_write_file_impl(
            {"path": file_path, "content": "def broken_func(\n"}, tmpdir
        )
        assert "Syntax error" in res
        assert not os.path.exists(file_path)

        trunc_path = os.path.join(tmpdir, "stub.py")
        res_trunc = tool_write_file_impl(
            {
                "path": trunc_path,
                "content": "def run():\n    # ... rest of implementation ...\n    pass\n",
            },
            tmpdir,
        )
        assert "truncation stubs" in res_trunc
        assert not os.path.exists(trunc_path)


def test_edit_file_blocks_broken_syntax():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "main.py")
        initial = "def main():\n    print('hello')\n"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(initial)

        res = tool_edit_file_impl(
            {
                "path": file_path,
                "old_text": "print('hello')",
                "new_text": "print('world'(\n",
            },
            tmpdir,
        )
        assert "Syntax error" in res
        with open(file_path, "r", encoding="utf-8") as f:
            assert f.read() == initial


def test_verify_compile_param():
    with tempfile.TemporaryDirectory() as tmpdir:
        good_path = os.path.join(tmpdir, "good.py")
        with open(good_path, "w", encoding="utf-8") as f:
            f.write("def ok():\n    return 1\n")
        res_good = tool_verify_impl({"path": good_path, "compile": True}, tmpdir)
        assert "Verification SUCCESS" in res_good
        assert "compile check passed" in res_good

        bad_path = os.path.join(tmpdir, "bad.py")
        with open(bad_path, "w", encoding="utf-8") as f:
            f.write("def bad(\n")
        res_bad = tool_verify_impl({"path": bad_path, "compile": True}, tmpdir)
        assert "Verification FAILED" in res_bad


def test_truncation_stubs_detected_in_non_code_files():
    # Plain-text truncation markers must be rejected even for .txt/.md targets.
    assert _detect_truncation_stubs("Some notes ... rest of the content", "notes.txt")
    status, payload = _validate_and_repair(
        "The config is ... more code omitted\n", "notes.txt", os.getcwd()
    )
    assert status == "error"
    assert "truncation stubs" in payload

    # Explicit "code omitted" statement is a hard error.
    assert _detect_truncation_stubs("def run():\n    # code omitted\n", "run.py")

    # Benign prose is still allowed for non-code files.
    status_ok, _ = _validate_and_repair(
        "# just a readme\n\nThis describes the project.\n", "README.md", os.getcwd()
    )
    assert status_ok == "ok"
