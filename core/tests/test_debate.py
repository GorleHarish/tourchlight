import json
import pytest
from unittest.mock import AsyncMock

from core.api.base import InferenceParams, PRESETS
from core.debate.verifier import DebateVerifier, CritiqueResult


class MockLLMClient:
    """Mock LLMClient for debate testing."""
    def __init__(self, responses=None):
        self.responses = responses or []
        self.chat_calls = []

    async def chat(self, messages, params=None):
        self.chat_calls.append({"messages": messages, "params": params})
        if self.responses:
            return self.responses.pop(0)
        return '{"has_flaws": false, "flaws": [], "recommendations": []}'


def test_critic_and_refine_presets():
    critic_p = InferenceParams.for_critic()
    assert critic_p.temperature == 0.2
    assert critic_p.top_k == 25

    refine_p = InferenceParams.for_refine()
    assert refine_p.temperature == 0.1
    assert refine_p.repeat_penalty == 1.10

    assert "critic" in PRESETS
    assert "refine" in PRESETS


def test_should_debate():
    client = MockLLMClient()
    verifier = DebateVerifier(client, enabled=True)

    # AUTO tier tools should bypass debate
    assert verifier.should_debate(tool_name="READ_FILE", phase="code") is False
    assert verifier.should_debate(tool_name="GREP", phase="code") is False

    # CONFIRM / REVIEW tier tools should trigger debate
    assert verifier.should_debate(tool_name="WRITE_FILE", phase="code") is True
    assert verifier.should_debate(tool_name="EDIT_FILE", phase="code") is True
    assert verifier.should_debate(tool_name="RUN_COMMAND", phase="code") is True

    # Planning phase should trigger debate regardless of tool
    assert verifier.should_debate(tool_name=None, phase="plan") is True

    # Disabled verifier should always return False
    disabled_verifier = DebateVerifier(client, enabled=False)
    assert disabled_verifier.should_debate(tool_name="WRITE_FILE", phase="code") is False


import asyncio

def test_critique_parsing_valid_json():
    async def _test():
        critic_response = json.dumps({
            "has_flaws": True,
            "flaws": ["Missing import 'os'"],
            "recommendations": ["Add import os at top of file"]
        })
        client = MockLLMClient(responses=[critic_response])
        verifier = DebateVerifier(client)

        res = await verifier.critique("import sys\nos.getcwd()", "Write script to get cwd")

        assert res.has_flaws is True
        assert "Missing import 'os'" in res.flaws
        assert "Add import os at top of file" in res.recommendations

    asyncio.run(_test())


def test_critique_parsing_markdown_codeblock():
    async def _test():
        critic_response = """```json
{
  "has_flaws": true,
  "flaws": ["Division by zero possibility"],
  "recommendations": ["Check if denominator == 0"]
}
```"""
        client = MockLLMClient(responses=[critic_response])
        verifier = DebateVerifier(client)

        res = await verifier.critique("def div(a, b): return a / b", "Division function")

        assert res.has_flaws is True
        assert "Division by zero possibility" in res.flaws

    asyncio.run(_test())


def test_verify_and_refine_flow_with_flaws():
    async def _test():
        critic_response = json.dumps({
            "has_flaws": True,
            "flaws": ["Unused variable x"],
            "recommendations": ["Remove x or return it"]
        })
        refine_response = "def calc(): return 42"

        client = MockLLMClient(responses=[critic_response, refine_response])
        verifier = DebateVerifier(client)

        output, res = await verifier.verify_and_refine(
            proposal="def calc(): x = 10; return 42",
            task_context="Calculate value",
            tool_name="WRITE_FILE",
            phase="code"
        )

        assert output == "def calc(): return 42"
        assert res.has_flaws is True
        assert len(client.chat_calls) == 2

    asyncio.run(_test())


def test_verify_and_refine_bypasses_auto_tools():
    async def _test():
        client = MockLLMClient()
        verifier = DebateVerifier(client)

        output, res = await verifier.verify_and_refine(
            proposal='{"name": "READ_FILE", "arguments": {"path": "main.py"}}',
            task_context="Inspect main.py",
            tool_name="READ_FILE",
            phase="code"
        )

        assert output == '{"name": "READ_FILE", "arguments": {"path": "main.py"}}'
        assert res.has_flaws is False
        assert len(client.chat_calls) == 0

    asyncio.run(_test())

