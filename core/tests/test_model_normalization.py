import pytest
from rlm_optimized.config import normalize_model_name, list_available_models


def test_normalize_gemma_4_4e4b_variants():
    assert normalize_model_name("gemma 4 4e4b") == "gemma-4-E4B-it"
    assert normalize_model_name("gemma4e4b") == "gemma-4-E4B-it"
    assert normalize_model_name("google/gemma-4-E4B-it") == "gemma-4-E4B-it"
    assert normalize_model_name("gemma-4-E4B-it") == "gemma-4-E4B-it"
    assert normalize_model_name("gemma 4 e4b") == "gemma-4-E4B-it"
    assert normalize_model_name("4e4b") == "gemma-4-E4B-it"


def test_normalize_gemma_4_e2b_variants():
    assert normalize_model_name("gemma 4 e2b") == "gemma-4-E2B-it"
    assert normalize_model_name("gemma-4-E2B-it") == "gemma-4-E2B-it"


def test_normalize_mlx_gemma_4_4e4b():
    assert normalize_model_name("gemma 4 4e4b", provider="mlx") == "mlx-community/gemma-4-E4B-it-4bit"
    assert normalize_model_name("google/gemma-4-E4B-it", provider="mlx") == "mlx-community/gemma-4-E4B-it-4bit"


def test_list_available_models_includes_gemma4e4b():
    models = list_available_models()
    model_ids = [m["id"] for m in models]
    assert "gemma-4-E4B-it" in model_ids
    assert "mlx-community/gemma-4-E4B-it-4bit" in model_ids
