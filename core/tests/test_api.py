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
    assert p.temperature == 0.4
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

    # 7B model gets repeat_penalty == 1.03 for code
    p_7b = InferenceParams.for_model_and_phase("qwen2.5-coder-7b", "code")
    assert p_7b.repeat_penalty == 1.03

    # Reasoning model gets repeat_penalty == 1.00 and presence_penalty == 0.0
    p_r1 = InferenceParams.for_model_and_phase("deepseek-r1-distill-qwen-7b", "plan")
    assert p_r1.repeat_penalty == 1.00
    assert p_r1.presence_penalty == 0.0
    assert p_r1.temperature == 0.60


