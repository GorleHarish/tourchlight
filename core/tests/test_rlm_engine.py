import pytest
from unittest.mock import MagicMock
from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
from rlm_optimized.cloud_client import CloudClient
from rlm_optimized.llamacpp_client import LlamaCppClient


def test_rlm_engine_optimized_debate_verifier_initialization():
    mock_client = MagicMock()

    # 1. Default initialization (debate_verifier disabled by default for fast performance)
    engine = RLMEngineOptimized(client=mock_client)
    assert hasattr(engine, "debate_verifier")
    assert engine.debate_verifier is None

    # 2. Enabled debate
    engine_enabled = RLMEngineOptimized(client=mock_client, enable_debate=True)
    assert hasattr(engine_enabled, "debate_verifier")
    assert engine_enabled.debate_verifier is not None

    # 3. Custom debate verifier injection
    custom_verifier = MagicMock()
    engine_custom = RLMEngineOptimized(
        client=mock_client, debate_verifier=custom_verifier
    )
    assert engine_custom.debate_verifier == custom_verifier


def test_client_chat_protocol_methods():
    for client_cls in [CloudClient, LlamaCppClient]:
        assert hasattr(client_cls, "chat"), (
            f"{client_cls.__name__} must implement chat()"
        )
        assert hasattr(client_cls, "chat_stream"), (
            f"{client_cls.__name__} must implement chat_stream()"
        )


def test_rlm_engine_debate_verifier_error_resilience(tmp_path):
    import asyncio

    async def _test():
        mock_client = MagicMock()
        mock_client.stream_chat_with_history.return_value = [
            "<FINAL_ANSWER>42</FINAL_ANSWER>"
        ]
        mock_client.chat_with_history.return_value = "Summary text"

        failing_verifier = MagicMock()
        failing_verifier.should_debate.return_value = True
        failing_verifier.verify_and_refine.side_effect = RuntimeError(
            "Debate service timeout"
        )

        engine = RLMEngineOptimized(
            client=mock_client,
            debate_verifier=failing_verifier,
            project_root=str(tmp_path),
        )
        result = await engine.solve_async("What is 2+2?")

        assert result.answer == "42"
        assert len(result.steps) == 1

    asyncio.run(_test())


def test_rlm_engine_solve_method():
    from rlm_optimized.rlm_engine import RLMEngine

    mock_client = MagicMock()
    mock_client.chat_with_history.return_value = "<FINAL_ANSWER>Done</FINAL_ANSWER>"
    engine = RLMEngine(client=mock_client)
    assert hasattr(engine, "solve"), "RLMEngine must implement solve()"
    res = engine.solve("Test task")
    assert res.answer == "Done"


def test_rlm_engine_optimized_code_execution(tmp_path):
    import asyncio

    async def _test():
        mock_client = MagicMock()
        mock_client.stream_chat_with_history.side_effect = [
            ["<CODE>x = 10 + 32; print(x)</CODE>"],
            ["<FINAL_ANSWER>42</FINAL_ANSWER>"],
        ]
        mock_client.chat_with_history.return_value = "Summary"
        engine = RLMEngineOptimized(
            client=mock_client, enable_debate=False, project_root=str(tmp_path)
        )
        res = await engine.solve_async("Calculate 10+32")
        assert "42" in res.answer or len(res.steps) >= 2

    asyncio.run(_test())


def test_rlm_engine_optimized_none_tool_name():
    import asyncio

    async def _test():
        mock_client = MagicMock()
        # Return tool call with None tool_name from _parse_response
        mock_client.stream_chat_with_history.side_effect = [
            ["<FINAL_ANSWER>Safe</FINAL_ANSWER>"]
        ]
        mock_client.chat_with_history.return_value = "Summary"
        engine = RLMEngineOptimized(client=mock_client, enable_debate=False)
        action, thinking, content, extra_queries, tool_name, tool_args = (
            engine._parse_response("<INVALID>tag</INVALID>")
        )
        assert tool_name is None
        assert action == "final_answer"
        assert content == "<INVALID>tag</INVALID>"

    asyncio.run(_test())


def test_rlm_engine_parse_think_tags_and_mid_sentence_prevention():
    mock_client = MagicMock()
    engine = RLMEngineOptimized(client=mock_client, enable_debate=False)

    # 1. Explicit <think> tag + <FINAL_ANSWER>
    resp1 = "<think>Analyzing context...</think>\n<FINAL_ANSWER>The answer is 42.</FINAL_ANSWER>"
    action, thinking, content, _, _, _ = engine._parse_response(resp1)
    assert action == "final_answer"
    assert thinking == "Analyzing context..."
    assert content == "The answer is 42."

    # 2. Mid-sentence tag insertion bug (model says 'I will use <FINAL_ANSWER> to address...')
    resp2 = "I will use <FINAL_ANSWER> to address the query directly and truthfully.</FINAL_ANSWER>"
    action, thinking, content, _, _, _ = engine._parse_response(resp2)
    assert action == "final_answer"
    assert "to address the query directly" in content

    # 2b. Thinking process with mid-sentence tag
    resp2b = "Thinking Process:\n1. Goal: Answer query\n5. Execution: I will use <FINAL_ANSWER> to address the query directly and truthfully.</FINAL_ANSWER>"
    action_b, thinking_b, content_b, _, _, _ = engine._parse_response(resp2b)
    assert action_b == "thinking"
    assert "Goal: Answer query" in thinking_b

    # 3. Plain conversational text with no tool tags
    resp3 = "I cannot browse the internet. My capabilities are limited to executing code and file tools."
    action, thinking, content, _, _, _ = engine._parse_response(resp3)
    assert action == "final_answer"
    assert content == resp3

    # 4. Template placeholder <FINAL_ANSWER>your answer</FINAL_ANSWER>
    resp4 = "<FINAL_ANSWER>your answer</FINAL_ANSWER>"
    action, thinking, content, _, _, _ = engine._parse_response(resp4)
    assert action == "final_answer"
    assert content == "your answer"

    # 5. Server stop-token truncated <FINAL_ANSWER> tag (no closing </FINAL_ANSWER>)
    resp5 = "Thinking about the query...\n<FINAL_ANSWER>The answer is 42."
    action, thinking, content, _, _, _ = engine._parse_response(resp5)
    assert action == "final_answer"
    assert thinking == "Thinking about the query..."
    assert content == "The answer is 42."

    # 6. Unwrapped reasoning prefix ('thought The user wants me to...')
    resp6 = "thought The user wants me to look for bugs in a 'snake game'. I need to first understand the project structure.\n\n1 List directory contents: Use LIST_DIR...\nI will start by listing directory contents."
    action, thinking, content, _, _, _ = engine._parse_response(resp6)
    assert action == "thinking"
    assert "The user wants me to look for bugs" in thinking
    assert content == ""

    # 7. CoT planning step without tool tags
    resp7 = "1 List directory contents: Use LIST_DIR to see what files are available.\nI will start by listing the directory contents."
    action, thinking, content, _, _, _ = engine._parse_response(resp7)
    assert action == "thinking"
    assert "List directory contents" in thinking
    assert content == ""


def test_rlm_engine_code_tag_and_backticks():
    mock_client = MagicMock()
    engine = RLMEngineOptimized(client=mock_client, enable_debate=False)

    # 1. Inline `<code>` tag or backticks in prose should NOT trigger Python code execution
    resp1 = "Plan: Generate complete HTML solution.\nWrap everything in a single `<code>` tag."
    action1, thinking1, content1, _, _, _ = engine._parse_response(resp1)
    assert action1 != "code"

    # 2. Markdown triple backticks inside <CODE> should be stripped cleanly
    resp2 = "<CODE>\n```python\nx = 42\nprint(x)\n```\n</CODE>"
    action2, thinking2, content2, _, _, _ = engine._parse_response(resp2)
    assert action2 == "code"
    assert content2 == "x = 42\nprint(x)"

    # 3. REPL Sandbox should strip markdown backticks before exec
    from rlm_optimized.repl_sandbox import REPLSandbox

    sandbox = REPLSandbox()
    res = sandbox.execute("```python\na = 10\nb = 20\nprint(a + b)\n```")
    assert res["success"] is True
    # 4. English prose inside <CODE> tags should NOT be parsed as action="code"
    resp3 = "<CODE>\n` tags if I were executing, but here I'm generating the final result as an HTML file.\n</CODE>"
    action3, thinking3, content3, _, _, _ = engine._parse_response(resp3)
    assert action3 == "thinking"

    # 5. REPL Sandbox should reject natural language prose gracefully
    res_prose = sandbox.execute(
        "tags if I were executing, but here I'm generating the final result as an HTML file."
    )
    assert res_prose["success"] is False
    assert "Content appears to be natural language/prose" in res_prose["error"]


def test_rlm_engine_parse_system_thought_and_plan_prefix():
    mock_client = MagicMock()
    engine = RLMEngineOptimized(client=mock_client, enable_debate=False)

    # 1. System Thought prefix with Plan: header and INSPECT_WEB reference
    resp = (
        "SYSTEM Thought: The user wants me to build a complete single-file HTML5 Canvas Breakout game in breakout.html, "
        "then perform a web inspection using Playwright simulation to test for runtime bugs and fix them iteratively.\n\n"
        "Plan:\n1 Write the full HTML/CSS/JS game logic into breakout.html.\n"
        "2 Simulate running the required inspection step via INSPECT_WEB.\n"
        "I will start by creating breakout.html."
    )
    action, thinking, content, _, _, _ = engine._parse_response(resp)
    assert action == "thinking"
    assert "build a complete single-file HTML5 Canvas Breakout game" in thinking
    assert "Plan:" in thinking

    # 2. Q&A explanation mentioning READ_FILE (should NOT be classified as thinking)
    resp_qa = "Here are the steps to use READ_FILE:\n1. Specify the path.\n2. Execute READ_FILE to inspect content."
    action_qa, thinking_qa, content_qa, _, _, _ = engine._parse_response(resp_qa)
    assert action_qa == "final_answer"
    assert "Here are the steps to use READ_FILE" in content_qa

    # 3. Conversational plan (e.g. learning plan) should NOT be trapped in thinking mode
    resp_plan = "Plan for learning Python:\n1. Learn variables\n2. Learn functions"
    action_plan, _, content_plan, _, _, _ = engine._parse_response(resp_plan)
    assert action_plan == "final_answer"
    assert "Plan for learning Python" in content_plan


def test_clean_and_parse_json_tolerant_multiline_content():
    from rlm_optimized.rlm_engine_optimized import _clean_and_parse_json

    # Raw (unescaped) newlines + embedded braces in content must not truncate
    raw = '{"path": "x.py", "content": "def f():\n    return {"k": 1}\n"}'
    parsed = _clean_and_parse_json(raw)
    assert parsed["path"] == "x.py"
    assert parsed["content"] == 'def f():\n    return {"k": 1}\n'


def test_clean_and_parse_json_trailing_unterminated_string():
    from rlm_optimized.rlm_engine_optimized import _clean_and_parse_json

    parsed = _clean_and_parse_json('{"path": "x.py", "content": "def f():')
    assert parsed["path"] == "x.py"


def test_repair_stop_tokens_write_file():
    mock_client = MagicMock()
    engine = RLMEngineOptimized(client=mock_client, enable_debate=False)

    repaired = engine._repair_stop_tokens('<WRITE_FILE path="x.py">\ndef f():')
    assert repaired.endswith("</WRITE_FILE>")

    # A fully closed WRITE_FILE must be left untouched
    closed = engine._repair_stop_tokens(
        '<WRITE_FILE path="x.py">\ndef f():</WRITE_FILE>'
    )
    assert closed.endswith("</WRITE_FILE>")
    assert closed.count("</WRITE_FILE>") == 1


def test_action_tag_unclosed_with_trailing_prose():
    mock_client = MagicMock()
    engine = RLMEngineOptimized(client=mock_client, enable_debate=False)

    # Unclosed <action> + trailing prose previously produced NO MATCH (tool call lost)
    resp = (
        '<action>WRITE_FILE {"path": "x.py", "content": "def f():\\n    return 1"}\n'
        "I will now continue with the next step."
    )
    action, _, _, _, tool_name, tool_args = engine._parse_response(resp)
    assert action == "tool"
    assert tool_name == "WRITE_FILE"
    assert tool_args["path"] == "x.py"
    assert tool_args["content"] == "def f():\n    return 1"


def test_action_tag_braces_inside_string_values():
    mock_client = MagicMock()
    engine = RLMEngineOptimized(client=mock_client, enable_debate=False)

    resp = '<action>EDIT_FILE {"path": "x.py", "old_text": "a {b}", "new_text": "c"}</action>'
    action, _, _, _, tool_name, tool_args = engine._parse_response(resp)
    assert action == "tool"
    assert tool_name == "EDIT_FILE"
    assert tool_args["old_text"] == "a {b}"
    assert tool_args["new_text"] == "c"


def test_action_tag_no_json_args():
    mock_client = MagicMock()
    engine = RLMEngineOptimized(client=mock_client, enable_debate=False)

    action, _, _, _, tool_name, tool_args = engine._parse_response(
        "<action>LIST_DIR</action>"
    )
    assert action == "tool"
    assert tool_name == "LIST_DIR"
    assert tool_args == {}


def test_rlm_engine_optimized_duplicate_code_execution(tmp_path):
    import asyncio

    async def _test():
        mock_client = MagicMock()
        mock_client.temperature = 0.1
        mock_client.stream_chat_with_history.side_effect = [
            ["<CODE>raise ValueError('fail')</CODE>"],
            ["<CODE>raise ValueError('fail')</CODE>"],
            ["<FINAL_ANSWER>42</FINAL_ANSWER>"],
        ]
        mock_client.chat_with_history.return_value = "Summary"
        engine = RLMEngineOptimized(
            client=mock_client, enable_debate=False, project_root=str(tmp_path)
        )
        res = await engine.solve_async("Do math")

        dup_steps = [
            s for s in res.steps if "Duplicate code execution block" in s.result
        ]
        assert len(dup_steps) >= 1
        assert mock_client.temperature == 0.1

    asyncio.run(_test())


def test_inline_interception_skips_plan_prose_blocks():
    mock_client = MagicMock()
    engine = RLMEngineOptimized(client=mock_client, enable_debate=False)

    # A bare ``` block containing a numbered plan outline must NOT become a file.
    resp_plan_block = (
        "Here is my approach:\n"
        "```\n"
        "# 1. Set up the project structure\n"
        "# 2. Implement the core module\n"
        "# 3. Wire up the CLI entrypoint\n"
        "```"
    )
    action, _, _, _, tool_name, _ = engine._parse_response(resp_plan_block)
    assert action != "tool"
    assert tool_name != "WRITE_FILE"

    # A prose sentence dump (no file header) must NOT be intercepted either.
    resp_prose = (
        "```\n"
        "First, we need to understand the existing codebase structure.\n"
        "Then, we can identify the relevant modules and their responsibilities.\n"
        "Finally, we will implement the fix in the appropriate location.\n"
        "```"
    )
    action2, _, _, _, tool_name2, _ = engine._parse_response(resp_prose)
    assert action2 != "tool"
    assert tool_name2 != "WRITE_FILE"


def test_inline_interception_requires_explicit_file_or_header():
    mock_client = MagicMock()
    engine = RLMEngineOptimized(client=mock_client, enable_debate=False)

    # Bare code without an explicit file header or pre-text path is NOT auto-written to inline_code_output.txt
    resp_code = "```python\ndef add(a, b):\n    return a + b\n```"
    action, _, _, _, tool_name, tool_args = engine._parse_response(resp_code)
    assert action != "tool"
    assert tool_name is None

    # An explicit `# file:` header correctly triggers WRITE_FILE
    resp_header = "```\n# file: notes.txt\nThis is a short note without code.\n```"
    action2, _, _, _, tool_name2, tool_args2 = engine._parse_response(resp_header)
    assert action2 == "tool"
    assert tool_name2 == "WRITE_FILE"
    assert tool_args2["path"] == "notes.txt"


def test_inline_interception_skips_plan_phase():
    mock_client = MagicMock()
    engine = RLMEngineOptimized(client=mock_client, enable_debate=False)
    engine._current_phase = "plan"

    # Even a real-looking code block is not auto-written during plan phase.
    resp = "```python\ndef add(a, b):\n    return a + b\n```"
    action, _, _, _, tool_name, _ = engine._parse_response(resp)
    assert action != "tool"
    assert tool_name != "WRITE_FILE"


def test_write_file_trailing_prose_trimmed_for_code_targets():
    mock_client = MagicMock()
    engine = RLMEngineOptimized(client=mock_client, enable_debate=False)

    # Unclosed <WRITE_FILE> for a code target swallows trailing prose; trimmed.
    resp = (
        '<WRITE_FILE path="main.py">\n'
        "def main():\n"
        '    print("hello")\n'
        "This function serves as the primary entrypoint of the application.\n"
    )
    action, _, _, _, tool_name, tool_args = engine._parse_response(resp)
    assert action == "tool"
    assert tool_name == "WRITE_FILE"
    assert 'print("hello")' in tool_args["content"]
    assert "primary entrypoint" not in tool_args["content"]

    # A prose target (.md) must NOT be trimmed.
    resp_md = (
        '<WRITE_FILE path="README.md">\n'
        "# My Project\n\n"
        "This project provides a terminal-based agent with intelligent context management.\n"
    )
    action2, _, _, _, _, tool_args2 = engine._parse_response(resp_md)
    assert action2 == "tool"
    assert "intelligent context management" in tool_args2["content"]
