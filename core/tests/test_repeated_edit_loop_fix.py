"""
End-to-end verification tests for preventing repeated edit loops,
out-of-bounds EDIT_FILE stepping, and TrajectoryLock blind spots.
"""

import os
import pytest
from core.tools.implementations import tool_edit_file_impl, tool_write_file_impl
from core.tools.dedup import TrajectoryLock, compute_payload_hash
from core.tools.task_helpers import auto_mark_task_completed_by_file, parse_all_tasks_from_markdown


def test_out_of_bounds_edit_rejected_without_silent_append(tmp_path):
    """
    Verifies that calling EDIT_FILE with start_line beyond file length
    does NOT silently append to EOF and returns a clear error directive.
    """
    html_file = tmp_path / "index.html"
    initial_content = "<!DOCTYPE html>\n<html>\n<head><title>Snake</title></head>\n<body>\n</body>\n</html>\n"
    html_file.write_text(initial_content, encoding="utf-8")

    # Attempt out-of-bounds edit (lines 106-115 on a 6-line file)
    res = tool_edit_file_impl(
        {
            "path": "index.html",
            "task_id": "1.12",
            "description": "Add initial snake setup",
            "start_line": 106,
            "end_line": 115,
            "new_text": "const snake = [{ x: 200, y: 300 }, direction: 'right' };",
        },
        str(tmp_path),
    )

    # Must be rejected
    assert "Edit failed: start_line 106 is out of bounds" in res
    assert "READ_FILE" in res

    # File content must remain unchanged (no duplicate lines appended)
    assert html_file.read_text(encoding="utf-8") == initial_content


def test_trajectory_lock_catches_changing_task_ids_and_repeated_new_text():
    """
    Verifies that TrajectoryLock catches duplicate edits even when task_id increments (1.12 -> 1.13).
    """
    lock = TrajectoryLock(window_size=5, max_duplicates=2)

    # Turn 1.12
    call1 = {
        "path": "index.html",
        "task_id": "1.12",
        "description": "Add initial snake setup in JavaScript file with starting position and direction",
        "start_line": 10,
        "end_line": 20,
        "new_text": "const snake = [{ x: 200, y: 300 }, direction: 'right' };",
    }
    is_dup1, _, _ = lock.is_duplicate("EDIT_FILE", call1)
    assert is_dup1 is False
    lock.register("EDIT_FILE", call1)

    # Turn 1.13: same new_text and same target path, but different task_id and line numbers
    call2 = {
        "path": "index.html",
        "task_id": "1.13",
        "description": "Add initial snake setup in JavaScript file with starting position and direction",
        "start_line": 21,
        "end_line": 30,
        "new_text": "const snake = [{ x: 200, y: 300 }, direction: 'right' };",
    }
    is_dup2, count2, hint2 = lock.is_duplicate("EDIT_FILE", call2)
    assert is_dup2 is True
    assert "DUPLICATE EDIT_FILE PAYLOAD BLOCKED" in hint2
    assert "READ_FILE" in hint2


def test_auto_mark_task_completed_single_task_progression(tmp_path):
    """
    Verifies that creating/editing index.html advances ONLY the first matching task,
    and does NOT prematurely mark subsequent pending tasks as completed.
    """
    plan_content = """# Implementation Plan

## Proposed Changes
- [ ] 1.1 Create index.html skeleton with canvas container and viewport meta
- [ ] 1.2 Setup clean dark styling in index.html and centered container
- [ ] 2.1 Initialize snake array, direction handling, and keydown listeners in index.html
"""
    plan_file = tmp_path / "implementation_plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    # Create index.html
    html_file = tmp_path / "index.html"
    html_file.write_text("<!DOCTYPE html>\n<html><body><canvas id='game'></canvas></body></html>\n", encoding="utf-8")

    # First edit: only task 1.1 should be completed
    marked = auto_mark_task_completed_by_file(str(tmp_path), "index.html", verified=True)
    assert marked is True

    tasks = parse_all_tasks_from_markdown(str(plan_file))
    t1 = next(t for t in tasks if "1.1" in str(t["description"]))
    t2 = next(t for t in tasks if "1.2" in str(t["description"]))
    t3 = next(t for t in tasks if "2.1" in str(t["description"]))
    assert t1["status"] == "completed"
    assert t2["status"] == "pending"  # Must NOT be marked completed prematurely!
    assert t3["status"] == "pending"


def test_accidental_code_overwrite_guard_in_write_file(tmp_path):
    """
    Verifies that calling WRITE_FILE with a tiny snippet on an established file
    is blocked to prevent accidental deletion of previous progress.
    """
    html_file = tmp_path / "index.html"
    established_code = "\n".join([
        "<!DOCTYPE html>",
        "<html>",
        "<head><title>Snake Game</title></head>",
        "<body>",
        "  <canvas id='game' width='400' height='400'></canvas>",
        "  <script>",
        "    const canvas = document.getElementById('game');",
        "    const ctx = canvas.getContext('2d');",
        "    let snake = [{x: 10, y: 10}];",
        "    let score = 0;",
        "  </script>",
        "</body>",
        "</html>",
    ])
    html_file.write_text(established_code, encoding="utf-8")

    # Attempt to overwrite with a tiny 2-line snippet without force=True
    res = tool_write_file_impl(
        {
            "path": "index.html",
            "content": "<button id='restart'>Restart</button>\n",
        },
        str(tmp_path),
    )

    # Must be blocked by the accidental overwrite guard
    assert "ACCIDENTAL CODE OVERWRITE BLOCKED" in res
    assert "EDIT_FILE" in res

    # File content must remain intact
    assert html_file.read_text(encoding="utf-8") == established_code


def test_edge_case_start_line_with_l_prefix_and_missing_end_line(tmp_path):
    """
    Verifies that 'L106' and start_line without end_line are safely parsed and bounds-checked.
    """
    html_file = tmp_path / "index.html"
    initial_content = "line 1\nline 2\nline 3\n"
    html_file.write_text(initial_content, encoding="utf-8")

    # Pass start_line as "L106" without end_line on a 3-line file
    res = tool_edit_file_impl(
        {
            "path": "index.html",
            "start_line": "L106",
            "new_text": "const snake = 1;",
        },
        str(tmp_path),
    )
    assert "Edit failed: start_line 106 is out of bounds" in res
    assert "READ_FILE" in res


def test_edge_case_single_line_unanchored_edit_rejected(tmp_path):
    """
    Verifies that a valid in-bounds single line edit (e.g. line 2) without old_text is rejected.
    """
    html_file = tmp_path / "index.html"
    initial_content = "line 1\nline 2\nline 3\n"
    html_file.write_text(initial_content, encoding="utf-8")

    res = tool_edit_file_impl(
        {
            "path": "index.html",
            "start_line": 2,
            "end_line": 2,
            "new_text": "replacement line 2",
        },
        str(tmp_path),
    )
    assert "Single-line edit on 'index.html:2' requires 'old_text'" in res


def test_edge_case_trajectory_lock_l_prefix_stepping():
    """
    Verifies TrajectoryLock catches sequential range stepping when line numbers use 'L' prefixes.
    """
    lock = TrajectoryLock(window_size=5, max_duplicates=2)

    call1 = {"path": "game.js", "start_line": "L1", "end_line": "L10", "new_text": "// chunk 1"}
    assert lock.is_duplicate("EDIT_FILE", call1)[0] is False
    lock.register("EDIT_FILE", call1)

    call2 = {"path": "game.js", "start_line": "L11", "end_line": "L20", "new_text": "// chunk 2"}
    assert lock.is_duplicate("EDIT_FILE", call2)[0] is False
    lock.register("EDIT_FILE", call2)

    call3 = {"path": "game.js", "start_line": "L21", "end_line": "L30", "new_text": "// chunk 3"}
    is_dup, _, hint = lock.is_duplicate("EDIT_FILE", call3)
    assert is_dup is True
    assert "SEQUENTIAL RANGE STEPPING DETECTED" in hint


def test_edge_case_path_alias_propagation_in_duplicate_hint():
    """
    Verifies that target file path aliases (target, file, filename, file_path)
    are correctly extracted and propagated into the single-path template.
    """
    lock = TrajectoryLock(window_size=5, max_duplicates=2)

    # Call with 'file' alias
    call1 = {"file": "styles.css", "old_text": "color: red;", "new_text": "color: blue;"}
    lock.register("EDIT_FILE", call1)

    # Repeat call
    is_dup, _, hint = lock.is_duplicate("EDIT_FILE", call1)
    assert is_dup is True
    assert "styles.css" in hint
    assert '<tool_call>{"name": "READ_FILE", "arguments": {"path": "styles.css"}}</tool_call>' in hint


def test_verification_gate_dynamic_template_and_anti_defeatist_sanitization(tmp_path):
    """
    Verifies that when a target file already exists on disk, the verification gate
    injects EDIT_FILE rather than WRITE_FILE, and that defeatist/revert echoing
    text is cleanly sanitized from assistant history.
    """
    import asyncio
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized

    plan_file = tmp_path / "implementation_plan.md"
    plan_file.write_text("# Plan\n- [ ] 1.2 Setup dark styling in index.html\n", encoding="utf-8")

    # index.html already exists on disk
    html_file = tmp_path / "index.html"
    html_file.write_text("<!DOCTYPE html><html><body><canvas id='game'></canvas></body></html>\n", encoding="utf-8")

    recorded_history = []

    class MockDefeatistClient:
        def __init__(self):
            self.call_count = 0

        def chat_with_history(self, messages, *args, **kwargs):
            self.call_count += 1
            recorded_history.append(list(messages))
            if self.call_count == 1:
                return "Given the rejection and unresolvable state, I will revert to a known-good state by reverting the edits made in `index.html` and marking this task as failed. Let's revert `index.html` and mark it as failed: ```json"
            else:
                return '<tool_call>{"name": "EDIT_FILE", "arguments": {"path": "index.html", "old_text": "<body>", "new_text": "<body class=\'dark\'>"}}</tool_call>'

        async def stream_chat_async(self, messages, *args, **kwargs):
            self.call_count += 1
            recorded_history.append(list(messages))
            if self.call_count == 1:
                # Simulates the defeatist response from the user report:
                yield "Given the rejection and unresolvable state, I will revert to a known-good state by reverting the edits made in `index.html` and marking this task as failed. Let's revert `index.html` and mark it as failed: ```json"
            else:
                yield '<tool_call>{"name": "EDIT_FILE", "arguments": {"path": "index.html", "old_text": "<body>", "new_text": "<body class=\'dark\'>"}}</tool_call>'

    engine = RLMEngineOptimized(project_root=str(tmp_path), client=MockDefeatistClient())
    engine.execution_mode = "unified"

    res = asyncio.run(engine.solve_async("implement task 1.2"))
    assert len(res.steps) >= 2

    # Step 0 is rejected_final_answer
    assert res.steps[0].action == "rejected_final_answer"

    # Verify that since index.html existed on disk, the gate template recommended EDIT_FILE
    assert "EDIT_FILE" in res.steps[0].result
    assert "WRITE_FILE" not in res.steps[0].result

    # Verify that the defeatist response was sanitized in history
    turn_2_messages = recorded_history[1]
    assistant_msg = next((m for m in turn_2_messages if m["role"] == "assistant"), None)
    assert assistant_msg is not None
    assert "Given the rejection and unresolvable state" not in assistant_msg["content"]
    assert "without <tool_call>]" in assistant_msg["content"]


def test_file_looks_complete_with_placeholder_and_todo_in_real_code(tmp_path):
    """
    Verifies that real code files containing HTML placeholders or TODO comments
    are correctly recognized as complete and not false-positive stubs.
    """
    from core.tools.task_helpers import _file_looks_complete

    # Real HTML with <input placeholder="...">
    html_p = tmp_path / "index.html"
    html_p.write_text(
        "<!DOCTYPE html>\n<html>\n<body>\n  <input type='text' placeholder='Enter task name'>\n  <button>Submit</button>\n</body>\n</html>\n",
        encoding="utf-8",
    )
    assert _file_looks_complete(str(html_p)) is True

    # Real JS with a TODO comment in full implementation
    js_p = tmp_path / "game.js"
    js_p.write_text(
        "// Game implementation\n// TODO: add high score storage\nfunction start() {\n  console.log('game running');\n}\nstart();\n",
        encoding="utf-8",
    )
    assert _file_looks_complete(str(js_p)) is True

    # 1-line stub file must still be rejected
    stub_p = tmp_path / "stub.py"
    stub_p.write_text("# TODO: implement\npass\n", encoding="utf-8")
    assert _file_looks_complete(str(stub_p)) is False


def test_auto_mark_task_completed_fallback_to_active_or_pending(tmp_path):
    """
    Verifies that editing a file advances the active or first pending task even when
    the task description uses action wording without explicit file names.
    """
    plan_content = """# Implementation Plan

## Proposed Changes
- [ ] 1.1 Set up game loop, physics engine, and scoring
- [ ] 1.2 Add responsive mobile controls
"""
    plan_file = tmp_path / "implementation_plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    code_file = tmp_path / "game.js"
    code_file.write_text(
        "const state = { score: 0 };\nfunction tick() {\n  state.score += 1;\n}\nsetInterval(tick, 1000);\n",
        encoding="utf-8",
    )

    # auto_mark with verified=True should advance the first pending task 1.1
    marked = auto_mark_task_completed_by_file(str(tmp_path), "game.js", verified=True)
    assert marked is True

    tasks = parse_all_tasks_from_markdown(str(plan_file))
    t1 = next(t for t in tasks if "1.1" in str(t["description"]))
    t2 = next(t for t in tasks if "1.2" in str(t["description"]))
    assert t1["status"] == "completed"
    assert t2["status"] == "pending"


def test_extract_task_file_and_scope():
    """
    Verifies that _extract_task_file_and_scope correctly extracts filepaths, line ranges,
    AST symbol anchors, and [NEW] flags.
    """
    from core.tools.task_helpers import _extract_task_file_and_scope

    # Existing file with line range
    info1 = _extract_task_file_and_scope("- [ ] 1.1 [src/auth/jwt.py:L15-L40] Implement JWT token validation")
    assert info1["target_files"] == ["src/auth/jwt.py"]
    assert info1["line_range"] == (15, 40)
    assert info1["symbol"] is None
    assert info1["is_new"] is False

    # Existing file with symbol anchor
    info2 = _extract_task_file_and_scope("- [ ] 1.2 [src/models/user.py#User] Add is_verified column")
    assert info2["target_files"] == ["src/models/user.py"]
    assert info2["symbol"] == "User"
    assert info2["line_range"] is None
    assert info2["is_new"] is False

    # Brand new file
    info3 = _extract_task_file_and_scope("- [ ] 1.3 [src/utils/crypto.py] [NEW] Scaffold hashing helper")
    assert info3["target_files"] == ["src/utils/crypto.py"]
    assert info3["is_new"] is True
    assert info3["line_range"] is None


def test_sync_workspace_tasks_preserves_file_and_scope(tmp_path):
    """
    Verifies that sync_workspace_tasks populates target_files, line_range, symbol,
    and is_new directly into .torchlight/goal_spec.json.
    """
    import json
    from core.tools.task_helpers import sync_workspace_tasks

    plan_content = """# Feature Plan

## Proposed Changes
### Phase 1
- [ ] 1.1 [src/auth.py:L10-L25] Add token refresh logic
- [ ] 1.2 [src/crypto.py] [NEW] Scaffold crypto helpers
"""
    plan_file = tmp_path / "implementation_plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    sync_workspace_tasks(str(tmp_path))

    goal_path = tmp_path / ".torchlight" / "goal_spec.json"
    assert goal_path.exists()
    data = json.loads(goal_path.read_text(encoding="utf-8"))
    tasks = data.get("tasks", [])
    assert len(tasks) == 2

    t1 = tasks[0]
    assert t1["target_files"] == ["src/auth.py"]
    assert t1["line_range"] == [10, 25] or t1["line_range"] == (10, 25)
    assert t1["is_new"] is False

    t2 = tasks[1]
    assert t2["target_files"] == ["src/crypto.py"]
    assert t2["is_new"] is True


def test_auto_mark_with_scoped_task_references(tmp_path):
    """
    Verifies that auto_mark_task_completed_by_file matches relative paths like src/auth.py
    when task descriptions use bracketed notation [src/auth.py:L10-L25].
    """
    from core.tools.task_helpers import sync_workspace_tasks

    plan_content = """# Auth Plan

## Proposed Changes
- [ ] 1.1 [src/auth.py:L10-L25] Add token refresh logic
"""
    plan_file = tmp_path / "implementation_plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    auth_file = src_dir / "auth.py"
    auth_file.write_text("def refresh():\n    return 'new_token'\n\nprint(refresh())\n", encoding="utf-8")

    sync_workspace_tasks(str(tmp_path))

    # Editing src/auth.py should match and complete task 1.1
    marked = auto_mark_task_completed_by_file(str(tmp_path), "src/auth.py", verified=True)
    assert marked is True

    tasks = parse_all_tasks_from_markdown(str(plan_file))
    assert tasks[0]["status"] == "completed"


def test_parse_response_intercepts_here_is_filename(tmp_path):
    """
    Verifies that _parse_response intercepts code blocks preceded by 'Here is game.js:'
    as WRITE_FILE tool calls on Turn 1.
    """
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized

    engine = RLMEngineOptimized(project_root=str(tmp_path))
    engine.execution_mode = "code"

    llm_resp = "Here is game.js:\n```javascript\nlet snake = [{x: 10, y: 10}];\n```"
    action, thinking, content, _, tool_name, tool_args = engine._parse_response(llm_resp)

    assert action == "tool"
    assert tool_name == "WRITE_FILE"
    assert tool_args["path"] == "game.js"
    assert "let snake" in tool_args["content"]


def test_parse_response_intercepts_unannotated_codeblock_for_active_task(tmp_path):
    """
    Verifies that when a task like '2.1 [game.js]' is pending, an unannotated code block
    is automatically mapped to WRITE_FILE('game.js', content) on Turn 1.
    """
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
    from core.tools.task_helpers import sync_workspace_tasks

    plan_content = """# Plan
## Proposed Changes
- [ ] 2.1 [game.js] Initialize snake array
"""
    (tmp_path / "implementation_plan.md").write_text(plan_content, encoding="utf-8")
    sync_workspace_tasks(str(tmp_path))

    engine = RLMEngineOptimized(project_root=str(tmp_path))
    engine.execution_mode = "code"

    llm_resp = "```javascript\n// Game implementation\nconst canvas = document.getElementById('canvas');\n```"
    action, thinking, content, _, tool_name, tool_args = engine._parse_response(llm_resp)
    assert action == "tool"
    assert tool_name == "WRITE_FILE"
    assert tool_args["path"] == "game.js"
    assert "const canvas" in tool_args["content"]


def test_strip_leading_filename_header():
    """
    Verifies that _strip_leading_filename_header removes bare filenames, markdown headers,
    and comments from the start of file content.
    """
    from core.tools.implementations import _strip_leading_filename_header

    # Bare filename on line 1
    c1 = "game.js\nconst canvas = document.getElementById('canvas');\n"
    assert _strip_leading_filename_header(c1, "game.js") == "const canvas = document.getElementById('canvas');\n"

    # Markdown header
    c2 = "### game.js\nconst canvas = document.getElementById('canvas');\n"
    assert _strip_leading_filename_header(c2, "game.js") == "const canvas = document.getElementById('canvas');\n"

    # Comment header with path
    c3 = "// file: src/game.js\nconst canvas = document.getElementById('canvas');\n"
    assert _strip_leading_filename_header(c3, "src/game.js") == "const canvas = document.getElementById('canvas');\n"

    # Leftover codeblock fence
    c4 = "```javascript\nconst canvas = document.getElementById('canvas');\n"
    assert _strip_leading_filename_header(c4, "game.js") == "const canvas = document.getElementById('canvas');\n"

    # Edge Case: Shebang lines must NEVER be stripped
    c5 = "#!/usr/bin/env node\nconst x = 1;\n"
    assert _strip_leading_filename_header(c5, "cli.js") == c5

    # Edge Case: Markdown title headers (e.g. # README.md) must NOT be stripped in markdown files
    c6 = "# README.md\nProject overview text\n"
    assert _strip_leading_filename_header(c6, "README.md") == c6

    # Edge Case: Explicit file comment label in markdown SHOULD be stripped
    c7 = "### File: README.md\n# Project Overview\n"
    assert _strip_leading_filename_header(c7, "README.md") == "# Project Overview\n"


def test_tool_write_file_strips_leading_filename_and_passes_js_compile(tmp_path):
    """
    Verifies that writing a JS file with a bare filename on line 1 cleanly strips the filename
    and passes the JS syntax/compile gate without error.
    """
    from core.tools.implementations import tool_write_file_impl

    raw_js = "game.js\nconst x = 10;\nfunction getX() { return x; }\n"
    res = tool_write_file_impl({"path": "game.js", "content": raw_js}, str(tmp_path))

    assert "Written" in res or "created" in res.lower()
    written_text = (tmp_path / "game.js").read_text(encoding="utf-8")
    assert not written_text.startswith("game.js")
    assert written_text.startswith("const x = 10;")


def test_edit_file_partial_lines_without_old_text_rejects_with_read_file_directive(tmp_path):
    """
    Verifies that calling EDIT_FILE with partial content without old_text on an existing file
    returns a deterministic READ_FILE directive rather than demanding old_text without content.
    """
    from core.tools.implementations import tool_edit_file_impl

    js_file = tmp_path / "game.js"
    # Create 36-line file
    full_content = "\n".join([f"// line {i}\nconst var{i} = {i};" for i in range(18)])
    js_file.write_text(full_content, encoding="utf-8")

    partial_new_text = "function spawnFood() {\n  return {x: 10, y: 10};\n}\n"
    res = tool_edit_file_impl(
        {
            "path": "game.js",
            "new_text": partial_new_text,
        },
        str(tmp_path),
    )

    assert "⛔ Edit rejected" in res
    assert "READ_FILE" in res
    assert '<tool_call>{"name": "READ_FILE", "arguments": {"path": "game.js"}}</tool_call>' in res


def test_rlm_engine_preflight_and_duplicate_handling_for_unknown_content(tmp_path):
    """
    Verifies that RLMEngineOptimized preflight check injects a READ_FILE directive when
    partial content is passed without old_text on an existing file, and that repeating
    the invalid call triggers TrajectoryLock with direct file preview.
    """
    import asyncio
    from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized

    js_file = tmp_path / "game.js"
    initial_content = "\n".join([f"const line{i} = {i};" for i in range(36)])
    js_file.write_text(initial_content, encoding="utf-8")

    plan_file = tmp_path / "implementation_plan.md"
    plan_file.write_text("# Plan\n- [ ] 2.2 Implement food spawning logic\n", encoding="utf-8")

    class MockLoopingSLMClient:
        def __init__(self):
            self.turn = 0

        def _get_turn_resp(self):
            self.turn += 1
            if self.turn == 1:
                # Turn 1: SLM emits partial EDIT_FILE without old_text
                return '<tool_call>{"name": "EDIT_FILE", "arguments": {"path": "game.js", "new_text": "function spawnFood() { return 1; }"}}</tool_call>'
            elif self.turn == 2:
                # Turn 2: SLM repeats the exact same invalid call
                return '<tool_call>{"name": "EDIT_FILE", "arguments": {"path": "game.js", "new_text": "function spawnFood() { return 1; }"}}</tool_call>'
            elif self.turn == 3:
                # Turn 3: SLM reads the file after seeing the duplicate hint
                return '<tool_call>{"name": "READ_FILE", "arguments": {"path": "game.js"}}</tool_call>'
            else:
                # Turn 4: SLM performs surgical edit with exact old_text
                return '<tool_call>{"name": "EDIT_FILE", "arguments": {"path": "game.js", "old_text": "const line0 = 0;", "new_text": "function spawnFood() { return 1; }"}}</tool_call>'

        def chat_with_history(self, messages, *args, **kwargs):
            return self._get_turn_resp()

        async def stream_chat_async(self, messages, *args, **kwargs):
            yield self._get_turn_resp()

    engine = RLMEngineOptimized(project_root=str(tmp_path), client=MockLoopingSLMClient())
    engine.execution_mode = "code"

    res = asyncio.run(engine.solve_async("implement food spawning"))

    assert len(res.steps) >= 3
    # Step 0: Rejected by preflight check with READ_FILE directive
    assert res.steps[0].tool_name == "EDIT_FILE"
    assert "READ_FILE" in res.steps[0].result
    assert '<tool_call>{"name": "READ_FILE", "arguments": {"path": "game.js"}}</tool_call>' in res.steps[0].result

    # Step 1: Duplicate invalid call caught by TrajectoryLock
    assert "duplicate" in res.steps[1].result.lower()
    assert "CURRENT FILE CONTENT" in res.steps[1].result
    assert "game.js" in res.steps[1].result






