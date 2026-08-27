"""Engine process lifecycle and background server manager for Torchlight."""

from __future__ import annotations

import os
import subprocess
import time
from typing import Optional

from rlm_optimized.config import is_port_in_use


def provider_runtime_info(provider_key: str) -> tuple[int, bool]:
    """Return (port, externally_managed) for a given provider key.

    externally_managed=True means Torchlight does not own the server process
    (the user starts LM Studio / `ollama serve` themselves), so the sidebar
    Start/Restart buttons should just re-check connectivity instead of trying
    to launch a bundled script.
    """
    if provider_key in ("llama-cpp", "turbo", "turboquant", "mlx"):
        return 8080, False
    if provider_key == "lmstudio":
        return 1234, True
    if provider_key == "ollama":
        return 11434, True
    return 0, True  # cloud providers — no local port to track


class EngineProcessManager:
    """Manages local inference server subprocesses (llama-server, MLX, etc.)."""

    def __init__(self, project_root: str):
        self.project_root = project_root

    @staticmethod
    def kill_running_servers() -> None:
        """Terminate any lingering local llama-server or mlx_lm.server processes."""
        try:
            subprocess.run(["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL)
            time.sleep(0.5)
        except Exception:
            pass

    def launch_local_server(
        self,
        model_name: str,
        provider_name: str,
        engine_port: int,
        kv_cache_mode: str = "turbo3",
        draft_model_name: str = "none",
        draft_max_tokens: int = 8,
    ) -> tuple[bool, str]:
        """Launch local server script in background and return (success, message_or_error)."""
        if engine_port <= 0:
            return True, "Cloud provider — no local server required"

        self.kill_running_servers()

        pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        provider_str = provider_name.lower()
        model_str = model_name.lower()

        is_mlx = (
            "mlx" in provider_str
            or "mlx" in model_str
            or (isinstance(model_name, str) and os.path.isdir(model_name) and os.path.exists(os.path.join(model_name, "config.json")))
            or (isinstance(model_name, str) and ("deepseek" in model_str or "r1" in model_str) and not model_name.endswith(".gguf"))
        )
        script_name = "start_mlx_server.sh" if is_mlx else "start_optimized_local.sh"

        candidates = [
            os.path.join(pkg_dir, script_name),
            os.path.join(self.project_root, "rlm_optimized", script_name),
            os.path.join(os.getcwd(), "rlm_optimized", script_name),
        ]
        target_script = None
        for cand in candidates:
            if cand and os.path.exists(cand):
                target_script = os.path.abspath(cand)
                break

        if not target_script or not os.path.exists(target_script):
            return False, f"Server launch script not found: {target_script or os.path.join(pkg_dir, script_name)}"

        try:
            log_dir = os.path.join(self.project_root, ".torchlight")
            os.makedirs(log_dir, exist_ok=True)
            server_log_path = os.path.join(log_dir, "llama_server.log")
            server_log_file = open(server_log_path, "a", encoding="utf-8")

            env = os.environ.copy()
            env["PORT"] = str(engine_port)
            env["KV_CACHE_COMPRESSION"] = kv_cache_mode or "turbo3"
            draft_arg = draft_model_name or "none"
            if draft_arg != "none":
                env["DRAFT_MODEL"] = draft_arg
                env["DRAFT_MAX"] = str(draft_max_tokens)

            subprocess.Popen(
                [target_script, model_name, draft_arg],
                cwd=os.path.dirname(target_script),
                stdout=server_log_file,
                stderr=server_log_file,
                start_new_session=True,
                env=env,
            )
            return True, f"Launched {script_name} for {model_name} on port {engine_port}"
        except Exception as e:
            return False, str(e)
