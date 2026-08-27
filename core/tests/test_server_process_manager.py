"""Tests for EngineProcessManager and server script resolution."""

import os
from unittest.mock import MagicMock, patch

from rlm_optimized.services.process_manager import EngineProcessManager, provider_runtime_info


def test_provider_runtime_info():
    """Verify ports and external management flags for providers."""
    port, ext = provider_runtime_info("llama-cpp")
    assert port == 8080
    assert ext is False

    port, ext = provider_runtime_info("mlx")
    assert port == 8080
    assert ext is False

    port, ext = provider_runtime_info("lmstudio")
    assert port == 1234
    assert ext is True

    port, ext = provider_runtime_info("ollama")
    assert port == 11434
    assert ext is True

    port, ext = provider_runtime_info("gemini")
    assert port == 0
    assert ext is True


def test_launch_local_server_script_found():
    """Verify that launch_local_server correctly locates start scripts in the repo."""
    manager = EngineProcessManager(project_root=os.getcwd())

    with patch("subprocess.Popen") as mock_popen, patch("subprocess.run"):
        mock_popen.return_value = MagicMock()

        # Test llama.cpp starter script resolution
        success, msg = manager.launch_local_server(
            model_name="gemma-4-E2B-it-Q4_K_M.gguf",
            provider_name="llama.cpp",
            engine_port=8080,
        )
        assert success is True
        assert "Launched start_optimized_local.sh" in msg
        assert mock_popen.called
        call_args = mock_popen.call_args[0][0]
        assert call_args[0].endswith("start_optimized_local.sh")
        assert os.path.exists(call_args[0])

        # Test MLX starter script resolution
        mock_popen.reset_mock()
        success, msg = manager.launch_local_server(
            model_name="Qwen2.5-Coder-3B-Instruct-4bit",
            provider_name="mlx",
            engine_port=8080,
        )
        assert success is True
        assert "Launched start_mlx_server.sh" in msg
        assert mock_popen.called
        call_args = mock_popen.call_args[0][0]
        assert call_args[0].endswith("start_mlx_server.sh")
        assert os.path.exists(call_args[0])


def test_launch_local_server_from_external_project_root():
    """Verify script resolution even when project_root is an arbitrary directory."""
    manager = EngineProcessManager(project_root="/tmp/some_external_project")

    with patch("subprocess.Popen") as mock_popen, patch("subprocess.run"):
        mock_popen.return_value = MagicMock()

        success, msg = manager.launch_local_server(
            model_name="gemma-4-E2B-it-Q4_K_M.gguf",
            provider_name="llama-cpp",
            engine_port=8080,
        )
        assert success is True
        assert "Launched start_optimized_local.sh" in msg
        call_args = mock_popen.call_args[0][0]
        assert os.path.exists(call_args[0])
