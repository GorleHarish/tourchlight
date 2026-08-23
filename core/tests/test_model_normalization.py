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
    assert normalize_model_name("4e2b") == "gemma-4-E2B-it"
    assert normalize_model_name("e2b") == "gemma-4-E2B-it"
    assert normalize_model_name("gemma 4 e2b", provider="mlx") == "mlx-community/gemma-4-E2B-it-4bit"
    assert normalize_model_name("gemma-4-E2B-it", provider="mlx") == "mlx-community/gemma-4-E2B-it-4bit"
    assert normalize_model_name("e2b", provider="mlx") == "mlx-community/gemma-4-E2B-it-4bit"


def test_normalize_gemma_2_and_3_variants():
    assert normalize_model_name("gemma-2-2b-it") == "gemma-2-2b-it"
    assert normalize_model_name("gemma-2-9b-it") == "gemma-2-9b-it"
    assert normalize_model_name("gemma-2-27b-it") == "gemma-2-27b-it"
    assert normalize_model_name("gemma 3 4b") == "gemma-3-4b-it"
    assert normalize_model_name("gemma-3-1b-it") == "gemma-3-1b-it"
    assert normalize_model_name("gemma-3-12b-it") == "gemma-3-12b-it"

    # MLX backend
    assert normalize_model_name("gemma-2-2b-it", provider="mlx") == "mlx-community/gemma-2-2b-it-4bit"
    assert normalize_model_name("gemma-2-9b-it", provider="mlx") == "mlx-community/gemma-2-9b-it-4bit"
    assert normalize_model_name("gemma 3 4b", provider="mlx") == "mlx-community/gemma-3-4b-it-4bit"
    assert normalize_model_name("gemma-3-1b-it", provider="mlx") == "mlx-community/gemma-3-1b-it-4bit"


def test_format_model_display_names():
    from rlm_optimized.config import format_model_display_name

    assert format_model_display_name("gemma-4-E2B-it-Q4_K_M.gguf") == "Gemma 4 E2B"
    assert format_model_display_name("gemma-4-E4B-it-Q4_K_M.gguf") == "Gemma 4 E4B"
    assert format_model_display_name("mlx-community/gemma-4-E2B-it-4bit") == "Gemma 4 E2B (MLX)"
    assert format_model_display_name("mlx-community/gemma-4-E4B-it-4bit") == "Gemma 4 E4B (MLX)"
    assert format_model_display_name("gemma-2-2b-it") == "Gemma 2 2B"
    assert format_model_display_name("gemma-3-4b-it") == "Gemma 3 4B"


def test_list_available_models_includes_gemma():
    models = list_available_models()
    model_ids = [m["id"] for m in models]
    assert "gemma-4-E4B-it" in model_ids
    assert "gemma-4-E2B-it" in model_ids
    assert "mlx-community/gemma-4-E4B-it-4bit" in model_ids
    assert "mlx-community/gemma-4-E2B-it-4bit" in model_ids
    assert any("DeepSeek" in m["id"] for m in models)


def test_list_available_draft_models():
    from rlm_optimized.config import list_available_draft_models

    gemma_drafts = list_available_draft_models("gemma-4-E4B-it")
    assert any(d["id"] == "auto" for d in gemma_drafts)
    # Target gemma compatibility
    for d in gemma_drafts:
        if "gemma" in d["id"].lower():
            assert d["is_compatible"] is True


def test_is_valid_mlx_directory(tmp_path):
    import json
    from rlm_optimized.config import is_valid_mlx_directory

    # 1. Non-existent path
    assert is_valid_mlx_directory(str(tmp_path / "nonexistent")) is False

    # 2. Directory missing config.json
    empty_dir = tmp_path / "empty_model"
    empty_dir.mkdir()
    assert is_valid_mlx_directory(str(empty_dir)) is False

    # 3. Directory with config.json and model.safetensors -> True
    single_shard = tmp_path / "single_shard_model"
    single_shard.mkdir()
    (single_shard / "config.json").write_text("{}")
    (single_shard / "model.safetensors").write_bytes(b"dummy_weights")
    assert is_valid_mlx_directory(str(single_shard)) is True

    # 4. Multi-shard model missing some shards -> False
    broken_multi = tmp_path / "broken_multi_model"
    broken_multi.mkdir()
    (broken_multi / "config.json").write_text("{}")
    index_data = {
        "metadata": {"total_size": 1000},
        "weight_map": {
            "layer1": "model-00001-of-00002.safetensors",
            "layer2": "model-00002-of-00002.safetensors",
        },
    }
    (broken_multi / "model.safetensors.index.json").write_text(json.dumps(index_data))
    # Only create shard 1
    (broken_multi / "model-00001-of-00002.safetensors").write_bytes(b"shard1")
    assert is_valid_mlx_directory(str(broken_multi)) is False

    # 5. Multi-shard model with ALL shards present -> True
    (broken_multi / "model-00002-of-00002.safetensors").write_bytes(b"shard2")
    assert is_valid_mlx_directory(str(broken_multi)) is True


