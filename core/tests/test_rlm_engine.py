import pytest
from unittest.mock import MagicMock
from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
from rlm_optimized.cloud_client import CloudClient
from rlm_optimized.llamacpp_client import LlamaCppClient

def test_rlm_engine_optimized_debate_verifier_initialization():
    mock_client = MagicMock()
    
    # 1. Default initialization (should have debate_verifier)
    engine = RLMEngineOptimized(client=mock_client)
    assert hasattr(engine, "debate_verifier")
    assert engine.debate_verifier is not None

    # 2. Disabled debate
    engine_disabled = RLMEngineOptimized(client=mock_client, enable_debate=False)
    assert hasattr(engine_disabled, "debate_verifier")
    assert engine_disabled.debate_verifier is None

    # 3. Custom debate verifier injection
    custom_verifier = MagicMock()
    engine_custom = RLMEngineOptimized(client=mock_client, debate_verifier=custom_verifier)
    assert engine_custom.debate_verifier == custom_verifier

def test_client_chat_protocol_methods():
    for client_cls in [CloudClient, LlamaCppClient]:
        assert hasattr(client_cls, "chat"), f"{client_cls.__name__} must implement chat()"
        assert hasattr(client_cls, "chat_stream"), f"{client_cls.__name__} must implement chat_stream()"

def test_rlm_engine_debate_verifier_error_resilience():
    import asyncio

    async def _test():
        mock_client = MagicMock()
        mock_client.stream_chat_with_history.return_value = ["<FINAL_ANSWER>42</FINAL_ANSWER>"]
        mock_client.chat_with_history.return_value = "Summary text"
        
        failing_verifier = MagicMock()
        failing_verifier.should_debate.return_value = True
        failing_verifier.verify_and_refine.side_effect = RuntimeError("Debate service timeout")

        engine = RLMEngineOptimized(client=mock_client, debate_verifier=failing_verifier)
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


def test_rlm_engine_optimized_code_execution():
    import asyncio
    async def _test():
        mock_client = MagicMock()
        mock_client.stream_chat_with_history.side_effect = [
            ["<CODE>x = 10 + 32; print(x)</CODE>"],
            ["<FINAL_ANSWER>42</FINAL_ANSWER>"]
        ]
        mock_client.chat_with_history.return_value = "Summary"
        engine = RLMEngineOptimized(client=mock_client, enable_debate=False)
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
        action, thinking, content, extra_queries, tool_name, tool_args = engine._parse_response("Invalid tag content")
        assert tool_name is None
    asyncio.run(_test())

