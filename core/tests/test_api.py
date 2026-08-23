import pytest
from core.api.base import InferenceParams, PRESETS, detect_model_traits


def test_inference_params_defaults():
    p = InferenceParams()
    assert p.temperature == 0.7
    assert p.top_k == 50
    assert p.top_p == 0.95


def test_inference_params_for_coding():
    p = InferenceParams.for_coding()
    assert p.temperature == 0.1
    assert p.top_k == 20


def test_inference_params_for_planning():
    p = InferenceParams.for_planning()
    assert p.temperature == 0.45
    assert p.top_k == 40


def test_inference_params_for_troubleshoot():
    p = InferenceParams.for_troubleshoot()
    assert p.temperature == 0.3
    assert p.top_k == 35


def test_inference_params_for_chat():
    p = InferenceParams.for_chat()
    assert p.temperature == 0.7
    assert p.top_k == 50


def test_inference_params_describe():
    p = InferenceParams.for_coding()
    desc = p.describe()
    assert "temp=0.1" in desc
    assert "top_k=20" in desc


def test_inference_params_to_payload():
    p = InferenceParams.for_coding()
    payload = p.to_payload()
    assert payload["temperature"] == 0.1
    assert payload["top_k"] == 20


def test_inference_params_to_payload_defaults():
    p = InferenceParams()
    payload = p.to_payload()
    # Default values should be excluded
    assert "temperature" not in payload


def test_presets_exist():
    assert "code" in PRESETS
    assert "plan" in PRESETS
    assert "troubleshoot" in PRESETS
    assert "chat" in PRESETS


def test_llamacpp_client_context_size_error(monkeypatch):
    import io
    import urllib.error
    from rlm_optimized.llamacpp_client import LlamaCppClient

    client = LlamaCppClient(base_url="http://localhost:8080/v1")

    err_json = '{"error":{"code":400,"message":"request (8211 tokens) exceeds the available context size (8192 tokens), try increasing it","type":"exceed_context_size_error","n_prompt_tokens":8211,"n_ctx":8192}}'
    fp = io.BytesIO(err_json.encode("utf-8"))
    http_err = urllib.error.HTTPError("http://localhost:8080/v1/chat/completions", 400, "Bad Request", {}, fp)

    def mock_urlopen(*args, **kwargs):
        raise http_err

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    with pytest.raises(ConnectionError) as exc_info:
        client.query(prompt="Hello")

    assert "llama-server context limit exceeded" in str(exc_info.value)
    assert "8211 tokens" in str(exc_info.value)


def test_llamacpp_client_503_loading_model_auto_wait(monkeypatch):
    import io
    import urllib.error
    from rlm_optimized.llamacpp_client import LlamaCppClient

    client = LlamaCppClient(base_url="http://localhost:8080/v1")

    err_503_json = '{"error":{"message":"Loading model","type":"unavailable_error","code":503}}'
    success_json = '{"choices":[{"message":{"content":"Model ready response"}}]}'

    call_count = 0

    def mock_urlopen(req, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        url = req.full_url if hasattr(req, "full_url") else str(req)
        # First call is POST /chat/completions -> returns 503 Loading model
        if call_count == 1:
            fp = io.BytesIO(err_503_json.encode("utf-8"))
            raise urllib.error.HTTPError(url, 503, "Service Unavailable", {}, fp)
        # Subsequent health/readiness check -> returns 200 OK
        if "health" in url or "models" in url:
            resp_data = b'{"status": "ok"}'
            mock_resp = io.BytesIO(resp_data)
            mock_resp.status = 200
            return mock_resp
        # Next query attempt -> returns success
        mock_resp = io.BytesIO(success_json.encode("utf-8"))
        mock_resp.status = 200
        return mock_resp

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
    monkeypatch.setattr("time.sleep", lambda s: None)

    res = client.query(prompt="Hello")
    assert res == "Model ready response"
    assert call_count >= 2


def test_llamacpp_client_503_streaming_auto_wait(monkeypatch):
    import io
    import urllib.error
    from rlm_optimized.llamacpp_client import LlamaCppClient

    client = LlamaCppClient(base_url="http://localhost:8080/v1")

    err_503_json = '{"error":{"message":"Loading model","type":"unavailable_error","code":503}}'
    stream_chunk = b'data: {"choices":[{"delta":{"content":"Chunk response"}}]}\n\ndata: [DONE]\n\n'

    call_count = 0

    def mock_urlopen(req, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        url = req.full_url if hasattr(req, "full_url") else str(req)
        # First call is POST /chat/completions -> returns 503 Loading model
        if call_count == 1:
            fp = io.BytesIO(err_503_json.encode("utf-8"))
            raise urllib.error.HTTPError(url, 503, "Service Unavailable", {}, fp)
        # Subsequent health/readiness check -> returns 200 OK
        if "health" in url or "models" in url:
            resp_data = b'{"status": "ok"}'
            mock_resp = io.BytesIO(resp_data)
            mock_resp.status = 200
            return mock_resp
        # Next stream attempt -> returns stream_chunk
        mock_resp = io.BytesIO(stream_chunk)
        mock_resp.status = 200
        return mock_resp

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
    monkeypatch.setattr("time.sleep", lambda s: None)

    tokens = list(client.stream_chat_with_history(messages=[{"role": "user", "content": "Hi"}]))
    assert tokens == ["Chunk response"]
    assert call_count >= 2




def test_detect_model_traits():
    t_2b = detect_model_traits("gemma-2b-it")
    assert t_2b["is_small_model"] is True
    assert t_2b["is_reasoning"] is False
    assert t_2b["param_size_b"] == 2.0

    t_7b = detect_model_traits("qwen2.5-coder-7b-instruct")
    assert t_7b["is_small_model"] is False
    assert t_7b["is_reasoning"] is False
    assert t_7b["param_size_b"] == 7.0

    t_r1 = detect_model_traits("deepseek-r1-distill-qwen-7b")
    assert t_r1["is_reasoning"] is True
    assert t_r1["param_size_b"] == 7.0

    # Edge cases: GGUF files, Ollama docker tags, and relative file paths
    t_gguf = detect_model_traits("qwen2.5-coder-7b.gguf")
    assert t_gguf["param_size_b"] == 7.0

    t_ollama = detect_model_traits("ollama/qwen2.5-coder:7b")
    assert t_ollama["param_size_b"] == 7.0

    t_path = detect_model_traits("models/gemma-2b.bin")
    assert t_path["param_size_b"] == 2.0


def test_for_model_and_phase():
    # 2B model gets repeat_penalty >= 1.05
    p_2b = InferenceParams.for_model_and_phase("gemma-2b", "code")
    assert p_2b.repeat_penalty >= 1.05
    assert p_2b.repetition_penalty == p_2b.repeat_penalty

    # 7B model gets repeat_penalty == 1.08 (hardcoded for all now)
    p_7b = InferenceParams.for_model_and_phase("qwen2.5-coder-7b", "code")
    assert p_7b.repeat_penalty >= 1.08
    assert p_7b.repetition_penalty >= 1.08

    # Reasoning model gets repeat_penalty == 1.08 (hardcoded for all now)
    p_r1 = InferenceParams.for_model_and_phase("deepseek-r1-distill-qwen-7b", "plan")
    assert p_r1.repeat_penalty >= 1.08
    assert p_r1.presence_penalty == 0.15


def test_inference_params_repetition_penalty_aliases():
    # Initializing with repetition_penalty syncs to repeat_penalty
    p1 = InferenceParams(repetition_penalty=1.12)
    assert p1.repetition_penalty == 1.12
    assert p1.repeat_penalty == 1.12
    assert "rep=1.12" in p1.describe()

    # Initializing with repeat_penalty syncs to repetition_penalty
    p2 = InferenceParams(repeat_penalty=1.08)
    assert p2.repeat_penalty == 1.08
    assert p2.repetition_penalty == 1.08

    # Payload includes both keys and lookback window when non-1.0
    payload = p1.to_payload()
    assert payload["repeat_penalty"] == 1.12
    assert payload["repetition_penalty"] == 1.12
    assert payload["repetition_context_size"] == 256
    assert payload["repeat_last_n"] == 256


def test_config_repetition_penalty_defaults():
    from rlm_optimized.config import REPEAT_PENALTY, REPETITION_PENALTY

    assert REPEAT_PENALTY > 0
    assert REPETITION_PENALTY == REPEAT_PENALTY


def test_llamacpp_client_stream_repetition_breaker(monkeypatch):
    import io
    import json
    from rlm_optimized.llamacpp_client import LlamaCppClient

    client = LlamaCppClient(base_url="http://localhost:8080/v1")

    # Generate repeating cycle with escaped \n (simulating JSON payload stream)
    cycle = [
        "\\n- How to optimize code documentation accessibility?",
        "\\n- How to optimize code documentation security?",
        "\\n- How to optimize code documentation reliability?",
        "\\n- How to optimize code documentation scalability?",
        "\\n- How to optimize code documentation testability?",
    ]
    # Repeat cycle 6 times (30 lines total)
    repeated_tokens = cycle * 6

    lines = []
    for tok in repeated_tokens:
        payload = json.dumps({"choices": [{"delta": {"content": tok}}]})
        lines.append(f"data: {payload}\n\n".encode("utf-8"))
    lines.append(b"data: [DONE]\n\n")

    stream_bytes = b"".join(lines)

    def mock_urlopen(req, *args, **kwargs):
        mock_resp = io.BytesIO(stream_bytes)
        mock_resp.status = 200
        return mock_resp

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    received = list(client.stream_chat_with_history(messages=[{"role": "user", "content": "Hi"}]))
    # Stream breaker must abort before reaching the full 30 tokens
    assert len(received) < len(repeated_tokens)
    assert len(received) <= 15


def test_small_model_calibration_qwen_3b():
    # 3B small models must receive repeat_penalty >= 1.12, presence_penalty == 0.20, and frequency_penalty == 0.15
    p_3b = InferenceParams.for_model_and_phase("mlx-community/Qwen2.5-Coder-3B-Instruct-4bit", "code")
    assert p_3b.repeat_penalty >= 1.12
    assert p_3b.repetition_penalty >= 1.12
    assert p_3b.presence_penalty == 0.20
    assert p_3b.frequency_penalty == 0.15


def test_cloud_client_stream_repetition_breaker(monkeypatch):
    from types import SimpleNamespace
    from rlm_optimized.cloud_client import CloudClient

    client = CloudClient(provider="mlx", model="mlx-community/Qwen2.5-Coder-3B-Instruct-4bit", base_url="http://localhost:8080/v1")
    assert client.presence_penalty == 0.20
    assert client.frequency_penalty == 0.15
    assert client.repeat_penalty >= 1.12

    # Simulate MLX streaming a repeating 4-line CSS cycle
    cycle = [
        "border-top: 5px solid #000000;\n",
        "border-bottom: 5px solid #000000;\n",
        "border-left: 5px solid #000000;\n",
        "border-right: 5px solid #000000;\n",
    ]
    repeated_tokens = cycle * 6

    def mock_create(**kwargs):
        assert kwargs.get("presence_penalty") == 0.20
        assert kwargs.get("frequency_penalty") == 0.15
        assert kwargs.get("extra_body", {}).get("repetition_penalty") >= 1.12

        def _gen():
            for tok in repeated_tokens:
                yield SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content=tok, reasoning=""))]
                )
        return _gen()

    monkeypatch.setattr(client._client.chat.completions, "create", mock_create)

    tokens = list(client.stream_query(prompt="Edit css"))
    # Stream loop breaker must abort before emitting the full 24 tokens
    assert len(tokens) < len(repeated_tokens)
    assert len(tokens) <= 12





