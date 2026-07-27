import pytest
from core.api.base import InferenceParams, PRESETS


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
