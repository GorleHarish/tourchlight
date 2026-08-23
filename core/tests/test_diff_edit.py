"""
Tests for Aider-style Search/Replace block editing (Approach B)
and dynamic JIT context pinning scaling (Approach C).
"""

import os
import tempfile

from core.memory.manager import MemoryConfig, TieredMemory
from core.tools.implementations import (
    _clean_copied_file_text,
    _parse_diff_block,
    tool_edit_file_impl,
    tool_write_file_impl,
)


def test_parse_diff_block_valid():
    text = """<<<<<<< SEARCH
def foo():
    return 1
=======
def foo():
    return 2
>>>>>>> REPLACE"""
    old_text, new_text = _parse_diff_block(text)
    assert old_text == "def foo():\n    return 1"
    assert new_text == "def foo():\n    return 2"


def test_parse_diff_block_invalid():
    old_text, new_text = _parse_diff_block("invalid diff string")
    assert old_text is None
    assert new_text is None


def test_parse_diff_block_llm_variations():
    # Model using >>>>>>> as divider instead of ======= and omitting REPLACE
    text = """<<<<<<< SEARCH
def check_solution(self):
    print("Checking solution...")
>>>>>>>
def check_solution(self):
    print("Fixed solution...")
>>>>>>>"""
    old_text, new_text = _parse_diff_block(text)
    assert old_text == 'def check_solution(self):\n    print("Checking solution...")'
    assert new_text == 'def check_solution(self):\n    print("Fixed solution...")'


def test_edit_file_malformed_diff_diagnostic():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "main.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def foo(): return 1\n")

        # Completely broken diff marker that cannot be split into 2 parts
        broken_diff = "<<<<<<< SEARCH only one block here"
        res = tool_edit_file_impl({"path": "main.py", "diff": broken_diff}, project_root=tmpdir)
        assert "Malformed diff block syntax" in res
        assert "Ensure your diff block follows this exact format" in res


def test_edit_file_with_diff_block():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a - b\n")

        diff_block = """<<<<<<< SEARCH
def add(a, b):
    return a - b
=======
def add(a, b):
    return a + b
>>>>>>> REPLACE"""

        res = tool_edit_file_impl({"path": "test.py", "diff": diff_block}, project_root=tmpdir)
        assert "Surgically edited" in res or "fuzzy" in res

        with open(test_file, "r", encoding="utf-8") as f:
            updated_content = f.read()

        assert "return a + b" in updated_content


def test_edit_file_diff_block_in_old_text():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("x = 10\ny = 20\n")

        diff_block = """<<<<<<< SEARCH
x = 10
=======
x = 100
>>>>>>> REPLACE"""

        res = tool_edit_file_impl({"path": "test.py", "old_text": diff_block}, project_root=tmpdir)
        assert "Surgically edited" in res or "fuzzy" in res

        with open(test_file, "r", encoding="utf-8") as f:
            updated_content = f.read()

        assert "x = 100" in updated_content


def test_memory_config_auto_tune_pinned_budget():
    config_4k = MemoryConfig.auto_tune(max_tokens=4000)
    assert config_4k.pinned_token_budget == 300

    config_8k = MemoryConfig.auto_tune(max_tokens=8000)
    assert config_8k.pinned_token_budget == 600

    config_12k = MemoryConfig.auto_tune(max_tokens=12000)
    assert config_12k.pinned_token_budget == 1000


def test_pin_file_truncation_to_budget():
    config = MemoryConfig(max_tokens=4000, pinned_token_budget=100)
    mem = TieredMemory(config)

    # Large content
    large_content = "\n".join([f"line_{i} = {i}" for i in range(100)])
    mem.pin_file("large.py", large_content)

    pinned = mem.get_pinned_files()
    assert len(pinned) == 1
    path, pinned_content = pinned[0]
    assert path == "large.py"
    assert "truncated" in pinned_content


def test_edit_file_line_bounded():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "sample.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("val = 1\nval = 1\nval = 1\n")

        res = tool_edit_file_impl({"path": "sample.py", "old_text": "val = 1", "new_text": "val = 99", "start_line": 2, "end_line": 2}, project_root=tmpdir)
        assert "Surgically edited" in res

        with open(test_file, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        assert lines[0] == "val = 1"
        assert lines[1] == "val = 99"
        assert lines[2] == "val = 1"


def test_edit_file_line_bounded_without_old_text():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "sample.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("val = 1\nval = 2\nval = 3\nval = 4\n")

        res = tool_edit_file_impl({"path": "sample.py", "new_text": "val = 999\nval = 888", "start_line": 2, "end_line": 3}, project_root=tmpdir)
        assert "Surgically edited" in res

        with open(test_file, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        assert lines[0] == "val = 1"
        assert lines[1] == "val = 999"
        assert lines[2] == "val = 888"
        assert lines[3] == "val = 4"


def test_edit_file_single_line_without_old_text_rejected():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "sample.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("val = 1\nval = 2\nval = 3\n")

        res = tool_edit_file_impl({"path": "sample.py", "new_text": "val = 999", "start_line": 2, "end_line": 2}, project_root=tmpdir)
        assert "Single-line edit on 'sample.py:2' requires 'old_text'" in res



def test_edit_file_symbol_anchored():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "code.py")
        code = "def alpha():\n    return 'old'\n\ndef beta():\n    return 42\n"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(code)

        new_fn = "def alpha():\n    return 'new'"
        res = tool_edit_file_impl({"path": "code.py", "symbol": "alpha", "new_text": new_fn}, project_root=tmpdir)
        assert "Surgically replaced symbol 'alpha'" in res

        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()

        assert "new" in updated
        assert "def beta():" in updated


def test_edit_file_multi_chunk():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "multi.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("a = 1\nb = 2\nc = 3\n")

        chunks = [
            {"old_text": "a = 1", "new_text": "a = 10"},
            {"old_text": "c = 3", "new_text": "c = 30"}
        ]
        res = tool_edit_file_impl({"path": "multi.py", "chunks": chunks}, project_root=tmpdir)
        assert "Chunk 1:" in res and "Chunk 2:" in res

        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()

        assert "a = 10" in updated
        assert "b = 2" in updated
        assert "c = 30" in updated


def test_edit_file_diagnostic_nudge():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "diag.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def calculate_total_amount(items):\n    return sum(items)\n")

        res = tool_edit_file_impl({"path": "diag.py", "old_text": "def totally_different_function_name(x, y, z):\n    return x + y + z"}, project_root=tmpdir)
        assert "Edit failed:" in res
        assert "HINT" in res or "READ_FILE" in res


def test_parse_diff_block_missing_divider():
    text = """<<<<<<< SEARCH
def foo():
    return 1
>>>>>>> REPLACE
def foo():
    return 2
>>>>>>>"""
    old_text, new_text = _parse_diff_block(text)
    assert old_text == "def foo():\n    return 1"
    assert new_text == "def foo():\n    return 2"


def test_edit_file_auto_fallback_to_write():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Case A: EDIT_FILE called with content argument on new file
        res = tool_edit_file_impl({"path": "new_file.py", "content": "print('hello')"}, project_root=tmpdir)
        assert "Wrote" in res or "Created" in res or "written" in res.lower() or "Surgically" in res
        with open(os.path.join(tmpdir, "new_file.py"), "r", encoding="utf-8") as f:
            assert "hello" in f.read()

        # Case B: EDIT_FILE called with new_text on new file without old_text
        res2 = tool_edit_file_impl({"path": "new_file_2.py", "new_text": "x = 42"}, project_root=tmpdir)
        assert "Wrote" in res2 or "Created" in res2 or "written" in res2.lower() or "Surgically" in res2
        with open(os.path.join(tmpdir, "new_file_2.py"), "r", encoding="utf-8") as f:
            assert "x = 42" in f.read()



def test_edit_file_line_range_old_text_not_found_does_not_overwrite():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "main.py")
        original = "a = 1\nb = 2\nc = 3\n"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(original)

        res = tool_edit_file_impl(
            {"path": "main.py", "start_line": 1, "end_line": 2,
             "old_text": "zzz", "new_text": "X"},
            project_root=tmpdir,
        )
        assert "not found within line range" in res
        assert "READ_FILE" in res
        with open(test_file, "r", encoding="utf-8") as f:
            assert f.read() == original


def test_edit_file_line_range_old_text_found_replaces_within_range():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "main.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("a = 1\nb = 2\nc = 3\n")

        res = tool_edit_file_impl(
            {"path": "main.py", "start_line": 1, "end_line": 2,
             "old_text": "a = 1", "new_text": "a = 10"},
            project_root=tmpdir,
        )
        assert "within line range 1-2" in res
        with open(test_file, "r", encoding="utf-8") as f:
            assert f.read() == "a = 10\nb = 2\nc = 3\n"


def test_edit_file_line_range_no_old_text_full_range_replace():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "main.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("a = 1\nb = 2\nc = 3\n")

        res = tool_edit_file_impl(
            {"path": "main.py", "start_line": 2, "end_line": 3, "new_text": "b = 20\nc = 30\n"},
            project_root=tmpdir,
        )
        assert "within line range 2-3" in res
        with open(test_file, "r", encoding="utf-8") as f:
            assert f.read() == "a = 1\nb = 20\nc = 30\n"


def test_write_file_content_hash_dedup():
    from core.tools.implementations import tool_write_file_impl
    with tempfile.TemporaryDirectory() as tmpdir:
        res1 = tool_write_file_impl({"path": "doc.txt", "content": "Hello World\n"}, project_root=tmpdir)
        assert "Written" in res1

        res2 = tool_write_file_impl({"path": "doc.txt", "content": "Hello World\n"}, project_root=tmpdir)
        assert "No change: file content of doc.txt is already identical" in res2


def test_edit_file_rejects_shorter_content_fallback_without_force():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "index.html")
        original = "\n".join([f"line {i}" for i in range(1, 133)])  # 132 lines
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(original)

        shorter_content = "\n".join([f"line {i}" for i in range(1, 102)])  # 101 lines

        # Attempt to pass content to EDIT_FILE without old_text / line range
        res = tool_edit_file_impl(
            {"path": "index.html", "content": shorter_content},
            project_root=tmpdir,
        )
        assert "⛔ Edit rejected" in res
        assert "smaller than existing file" in res
        # Verify file content is completely intact and not overwritten
        with open(test_file, "r", encoding="utf-8") as f:
            assert f.read() == original


def test_edit_file_allows_shorter_content_with_force():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "index.html")
        original = "\n".join([f"line {i}" for i in range(1, 50)])
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(original)

        shorter_content = "line 1\nline 2\n"
        res = tool_edit_file_impl(
            {"path": "index.html", "content": shorter_content, "force": True},
            project_root=tmpdir,
        )
        assert "Written" in res or "Surgically" in res or "Wrote" in res
        with open(test_file, "r", encoding="utf-8") as f:
            assert f.read().strip() == shorter_content.strip()


def test_edit_file_auto_strips_read_file_line_numbers():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "style.css")
        original = "body {\n  display: flex;\n  background: #000;\n}\n"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(original)

        # Model copied lines from READ_FILE output containing ' 1 | ' and ' 2 | '
        copied_old_text = "  1 | body {\n  2 |   display: flex;\n  3 |   background: #000;"
        new_text = "body {\n  display: grid;\n  background: #fff;"

        res = tool_edit_file_impl(
            {"path": "style.css", "old_text": copied_old_text, "new_text": new_text},
            project_root=tmpdir,
        )
        assert "Surgically edited style.css" in res
        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()
            assert "display: grid;" in updated
            assert "background: #fff;" in updated


def test_edit_file_normalizes_unicode_curly_quotes():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "script.js")
        original = 'const title = "Snake Game";\nconst mode = \'arcade\';\n'
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(original)

        # Model used typographic smart quotes
        smart_old_text = 'const title = “Snake Game”;\nconst mode = ‘arcade’; '
        new_text = 'const title = "Super Snake";\nconst mode = \'hardcore\';'

        res = tool_edit_file_impl(
            {"path": "script.js", "old_text": smart_old_text, "new_text": new_text},
            project_root=tmpdir,
        )
        assert "Surgically edited script.js" in res
        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()
            assert 'const title = "Super Snake";' in updated
            assert "const mode = 'hardcore';" in updated


def test_edit_file_line_drift_auto_recovery():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "index.html")
        content = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
  <header><h1>Welcome</h1></header>
  <div class="banner">Original Banner</div>
  <main>Content here</main>
  <footer>Footer note</footer>
</body>
</html>
"""
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Model thought the banner was at lines 15-20 (stale line offsets from previous turn)
        res = tool_edit_file_impl(
            {
                "path": "index.html",
                "start_line": 15,
                "end_line": 20,
                "old_text": '<div class="banner">Original Banner</div>',
                "new_text": '<div class="banner">Updated Hero Banner</div>',
            },
            project_root=tmpdir,
        )
        assert "Surgically edited index.html" in res
        assert "relocated from lines 15-20" in res or "line drift" in res

        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()
            assert '<div class="banner">Updated Hero Banner</div>' in updated


def test_sync_ast_graph_skips_markup(monkeypatch):
    import core.flashlight.graph_engine as ge
    from core.tools.implementations import _sync_ast_graph

    called = []
    monkeypatch.setattr(ge, "update_project_graph_file", lambda root, fp: called.append(fp))

    # Should skip html, css, json, md
    _sync_ast_graph("/tmp", "/tmp/index.html")
    _sync_ast_graph("/tmp", "/tmp/style.css")
    _sync_ast_graph("/tmp", "/tmp/data.json")
    _sync_ast_graph("/tmp", "/tmp/README.md")
    assert len(called) == 0

    # Should process python / ts
    _sync_ast_graph("/tmp", "/tmp/main.py")
    assert "/tmp/main.py" in called


def test_edit_file_line_drift_multi_occurrence_proximity():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "main.py")
        content = """# Header
def item_one():
    return True

# Middle section
def item_two():
    return True

# Footer section
def item_three():
    return True
"""
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(content)

        # "return True" appears at lines 3, 7, and 11.
        # Target was around lines 6-8 (item_two), but shifted slightly.
        res = tool_edit_file_impl(
            {
                "path": "main.py",
                "start_line": 6,
                "end_line": 9,
                "old_text": "    return True",
                "new_text": "    return False",
            },
            project_root=tmpdir,
        )
        assert "Surgically edited main.py" in res

        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()

        # item_one should still return True
        assert "def item_one():\n    return True" in updated
        # item_two should be changed to False
        assert "def item_two():\n    return False" in updated
        # item_three should still return True
def test_edit_file_empty_file_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an empty file (0 bytes / touched skeleton)
        empty_file = os.path.join(tmpdir, "index.html")
        with open(empty_file, "w", encoding="utf-8") as f:
            f.write("")

        # Model calls EDIT_FILE on the empty file
        res = tool_edit_file_impl(
            {
                "path": "index.html",
                "old_text": "",
                "new_text": "<!DOCTYPE html>\n<html><body><canvas id='game'></canvas></body></html>",
            },
            project_root=tmpdir,
        )
        assert "Written" in res or "Surgically" in res or "index.html" in res

        with open(empty_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "<canvas id='game'>" in content


def test_edit_file_new_text_without_old_text_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Existing file with 25 lines of skeleton
        test_file = os.path.join(tmpdir, "index.html")
        skeleton = "<!DOCTYPE html>\n<html>\n<head><title>Test</title></head>\n<body>\n</body>\n</html>\n"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(skeleton)

        # Model emits EDIT_FILE with new_text (full new content) but omits old_text
        full_new_code = "<!DOCTYPE html>\n<html>\n<head>\n  <meta charset='utf-8'>\n  <title>Snake</title>\n</head>\n<body>\n  <canvas id='game'></canvas>\n  <script src='game.js'></script>\n</body>\n</html>\n"
        res = tool_edit_file_impl(
            {
                "path": "index.html",
                "new_text": full_new_code,
            },
            project_root=tmpdir,
        )
        assert "Written" in res or "Surgically" in res or "index.html" in res

        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()
        assert "<canvas id='game'>" in updated
        assert "Snake" in updated


def test_edit_file_full_copied_read_file_decorations_in_old_and_new_text():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "game.js")
        original_code = (
            "const canvas = document.getElementById('canvas');\n"
            "const ctx = canvas.getContext('2d');\n"
            "let snake = [{x: 10, y: 10}];\n"
            "const direction = {dx: 0, dy: 0};\n"
            "function update() {\n"
            "  // Update snake position based on direction\n"
            "}\n"
            "function draw() {\n"
            "  ctx.clearRect(0, 0, canvas.width, canvas.height);\n"
            "}\n"
            "function handleKeyDown(event) {\n"
            "  // handler\n"
            "}\n"
            "function spawnFood() {\n"
            "  // food\n"
            "}\n"
            "window.addEventListener('keydown', handleKeyDown);\n"
        )
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(original_code)

        # Exact copied READ_FILE / pinned context framing as produced in SLM Qwen2.5-Coder-3B turn
        copied_old_text = (
            "--- game.js---\n"
            "Symbols:\n"
            "  L 5 fn update\n"
            "  L 8 fn draw\n"
            "  L 11 fn handleKeyDown\n"
            "  L 14 fn spawnFood\n"
            "game.js (17 lines)\n"
            "```js\n"
            " 1 | const canvas = document.getElementById('canvas');\n"
            " 2 | const ctx = canvas.getContext('2d');\n"
            " 3 | let snake = [{x: 10, y: 10}];\n"
            " 4 | const direction = {dx: 0, dy: 0};\n"
            " 5 | function update() {\n"
            " 6 |   // Update snake position based on direction\n"
            " 7 | }\n"
            " 8 | function draw() {\n"
            " 9 |   ctx.clearRect(0, 0, canvas.width, canvas.height);\n"
            " 10 | }\n"
            " 11 | function handleKeyDown(event) {\n"
            " 12 |   // handler\n"
            " 13 | }\n"
            " 14 | function spawnFood() {\n"
            " 15 |   // food\n"
            " 16 | }\n"
            " 17 | window.addEventListener('keydown', handleKeyDown);\n"
            "```\n"
            "game.js (17 lines)\n"
            "--- end game.js ---"
        )

        copied_new_text = (
            "--- game.js---\n"
            "Symbols:\n"
            "  L 5 fn update\n"
            "  L 8 fn draw\n"
            "game.js (17 lines)\n"
            "```js\n"
            " 1 | const canvas = document.getElementById('canvas');\n"
            " 2 | const ctx = canvas.getContext('2d');\n"
            " 3 | let snake = [{x: 10, y: 10}];\n"
            " 4 | const direction = {dx: 0, dy: 0};\n"
            " 5 | function update() {\n"
            " 6 |   snake[0].x += direction.dx;\n"
            " 7 |   snake[0].y += direction.dy;\n"
            " 8 | }\n"
            " 9 | function draw() {\n"
            " 10 |   ctx.clearRect(0, 0, canvas.width, canvas.height);\n"
            " 11 | }\n"
            " 12 | function handleKeyDown(event) {\n"
            " 13 |   // handler\n"
            " 14 | }\n"
            " 15 | function spawnFood() {\n"
            " 16 |   // food\n"
            " 17 | }\n"
            " 18 | window.addEventListener('keydown', handleKeyDown);\n"
            "```\n"
            "--- end game.js ---"
        )

        res = tool_edit_file_impl(
            {"path": "game.js", "old_text": copied_old_text, "new_text": copied_new_text},
            project_root=tmpdir,
        )
        assert "Surgically edited game.js" in res or "Written" in res
        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()

        assert "snake[0].x += direction.dx;" in updated
        assert "snake[0].y += direction.dy;" in updated
        # Verify NO line number prefixes or symbols headers were leaked into the file
        assert "1 |" not in updated
        assert "Symbols:" not in updated
        assert "--- game.js" not in updated
        assert "```js" not in updated


def test_edit_file_copied_line_numbers_in_new_text_stripped():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "main.py")
        original = "def compute():\n    x = 1\n    return x\n"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(original)

        # Model passed line numbers in new_text
        old_text = "    x = 1\n    return x"
        new_text = " 2 |     x = 42\n 3 |     return x * 2"

        res = tool_edit_file_impl(
            {"path": "main.py", "old_text": old_text, "new_text": new_text},
            project_root=tmpdir,
        )
        assert "Surgically edited main.py" in res
        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()

        assert "x = 42" in updated
        assert "return x * 2" in updated
        assert "2 |" not in updated
        assert "3 |" not in updated


def test_write_file_strips_copied_read_file_decorations():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "app.js")
        payload = (
            "--- app.js ---\n"
            "Symbols:\n"
            "  L 1 fn start\n"
            "app.js (3 lines)\n"
            "```js\n"
            " 1 | function start() {\n"
            " 2 |   console.log('started');\n"
            " 3 | }\n"
            "```\n"
            "--- end app.js ---"
        )
        res = tool_write_file_impl(
            {"path": "app.js", "content": payload},
            project_root=tmpdir,
        )
        assert "Written" in res
        with open(test_file, "r", encoding="utf-8") as f:
            saved = f.read()

        assert "function start() {" in saved
        assert "console.log('started');" in saved
        assert "1 |" not in saved
        assert "Symbols:" not in saved
        assert "--- app.js" not in saved


def test_edit_file_empty_old_text_with_symbol_replacement():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "game.js")
        original = (
            "const canvas = document.getElementById('canvas');\n"
            "function update() {}\n"
            "function spawnFood() {\n"
            "  // stub\n"
            "}\n"
            "window.addEventListener('keydown', () => {});\n"
        )
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(original)

        # Model emits EDIT_FILE with empty / newline old_text to replace spawnFood
        new_text = "function spawnFood() {\n  food = {x: 5, y: 5};\n}"
        res = tool_edit_file_impl(
            {"path": "game.js", "old_text": "\n", "new_text": new_text},
            project_root=tmpdir,
        )
        assert "Surgically replaced fn 'spawnFood'" in res or "Surgically" in res
        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()
        assert "food = {x: 5, y: 5};" in updated
        assert "// stub" not in updated


def test_edit_file_empty_old_text_inserts_before_listeners():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "game.js")
        original = (
            "const canvas = document.getElementById('canvas');\n"
            "function draw() {}\n"
            "window.addEventListener('keydown', () => {});\n"
        )
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(original)

        new_text = "function checkCollisions() {\n  return false;\n}"
        res = tool_edit_file_impl(
            {"path": "game.js", "old_text": "", "new_text": new_text},
            project_root=tmpdir,
        )
        assert "Surgically" in res
        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()
        assert "function checkCollisions() {" in updated
        # Ensure it was placed before the listener
        assert updated.index("function checkCollisions()") < updated.index("window.addEventListener")


def test_edit_file_disambiguates_multi_match_via_start_line():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "utils.js")
        original = (
            "function a() {\n  return 1;\n}\n"
            "function b() {\n  return 1;\n}\n"
            "function c() {\n  return 1;\n}\n"
        )
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(original)

        # '  return 1;' appears 3 times. Target the one in function b (lines 4-6)
        res = tool_edit_file_impl(
            {"path": "utils.js", "old_text": "  return 1;", "new_text": "  return 42;", "start_line": 5},
            project_root=tmpdir,
        )
        assert "Surgically edited utils.js" in res
        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()
        lines = updated.splitlines()
        assert lines[1] == "  return 1;"
        assert lines[4] == "  return 42;"
        assert lines[7] == "  return 1;"


def test_edit_file_short_old_text_fallback_to_symbol():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "game.js")
        original = (
            "function update() {\n  x += 1;\n}\n"
            "function draw() {\n  ctx.clear();\n}\n"
            "function reset() {\n  x = 0;\n}\n"
        )
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(original)

        # Model passed '}' which matches 3 times, but new_text implements draw
        new_draw = "function draw() {\n  ctx.clearRect(0, 0, 100, 100);\n  render();\n}"
        res = tool_edit_file_impl(
            {"path": "game.js", "old_text": "}", "new_text": new_draw},
            project_root=tmpdir,
        )
        assert "Surgically replaced fn 'draw'" in res or "Surgically" in res
        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()
        assert "render();" in updated
        assert "function update() {" in updated
        assert "function reset() {" in updated


def test_edit_file_high_coverage_auto_promotion_when_old_text_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "game.js")
        original = (
            "const canvas = document.getElementById('canvas');\n"
            "let x = 0;\n"
            "function update() { x += 1; }\n"
        )
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(original)

        # Model emits full file update but provides a hallucinatory old_text
        full_file = (
            "const canvas = document.getElementById('canvas');\n"
            "const ctx = canvas.getContext('2d');\n"
            "let x = 0;\n"
            "let y = 0;\n"
            "function update() { x += 1; y += 1; }\n"
            "function draw() { ctx.clearRect(0, 0, 100, 100); }\n"
        )
        res = tool_edit_file_impl(
            {"path": "game.js", "old_text": "completely_nonexistent_hallucination()", "new_text": full_file},
            project_root=tmpdir,
        )
        assert "Surgically" in res or "Written" in res
        with open(test_file, "r", encoding="utf-8") as f:
            updated = f.read()
        assert "let y = 0;" in updated
        assert "function draw() {" in updated






