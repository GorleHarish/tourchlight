"""Engine lifecycle, model selection options, backend process control, and mode switching mixin."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.markup import escape
from textual import events, on, work
from textual.widgets import Button, Select, Static

from core.memory.models import ExecutionMode
from rlm_optimized.config import (
    CHIP_NAME,
    CTX_SIZE,
    IS_8GB_DEVICE,
    LMSTUDIO_API_KEY,
    LMSTUDIO_BASE_URL,
    MAX_RECURSION_DEPTH,
    MODEL_NAME,
    PROVIDER,
    TOTAL_RAM_GB,
    fetch_provider_models,
    is_port_in_use,
    list_available_models,
    normalize_model_name,
)
from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
from rlm_optimized.services import (
    EngineProcessManager,
    SlashCommandDispatcher,
    provider_runtime_info as _provider_runtime_info,
)
from rlm_optimized.tui_widgets.diff_view import build_diff_preview
from rlm_optimized.tui_widgets.modals import (
    ApprovalModal,
    AskUserModal,
    EngineConfigModal,
    FolderPickerModal,
    SessionModePickerModal,
)
from rlm_optimized.utils import STATE_FILE, load_last_state, save_last_state


class EngineLifecycleMixin:
    """Mixin providing engine process management, model switching, and mode selection."""

    def set_mode(self, mode_str: str) -> None:
        m_str = mode_str.lower().strip()
        if m_str in ("code", "chat", "goal", "plan", "unified"):
            self.engine.execution_mode = m_str
            save_last_state({"last_execution_mode": m_str})



            if m_str == "code":
                self.notify(
                    "Switched to Code Mode (Surgical coding & task execution)",
                    severity="success",
                    timeout=3,
                )
            elif m_str == "goal":
                try:
                    from core.execution.autonomous_harness import AutonomousHarness

                    harness = AutonomousHarness(
                        project_root=self.engine.project_root, memory=mem
                    )
                    success = harness.ensure_goal_spec_initialized()
                    if not success:
                        self.notify(
                            "Failed to initialize Goal Mode task graph",
                            severity="error",
                            timeout=5,
                        )
                        return
                except Exception as e:
                    self.notify(
                        f"Failed to initialize Goal Mode: {e}",
                        severity="error",
                        timeout=5,
                    )
                    return
                self.notify(
                    "Switched to Goal Mode (Task Graph in .torchlight/tasks.md)",
                    severity="success",
                    timeout=3,
                )
            elif m_str == "plan":
                self.notify(
                    "Switched to Plan Mode (Brainstorm & maintain implementation_plan.md)",
                    severity="success",
                    timeout=3,
                )
            elif m_str == "unified":
                self.notify(
                    "Switched to Unified Mode (Dynamic Phase & Toolset)",
                    severity="success",
                    timeout=3,
                )
            else:
                self.notify(
                    "Switched to Chat Mode (Lightweight Q&A)",
                    severity="information",
                    timeout=3,
                )
            if hasattr(self, "_user_input") and self._user_input and hasattr(self._user_input, "set_mode_placeholder"):
                self._user_input.set_mode_placeholder(m_str)
            try:
                from textual.widgets import Select
                dropdown = self.query_one("#mode-select-dropdown", Select)
                if dropdown.value != m_str:
                    dropdown.value = m_str
            except Exception:
                pass
            self.update_sidebar_meta()
            self.update_status_bar()
        else:
            self.notify(
                f"Unknown mode: {mode_str}. Options: code, plan, chat, goal, unified.",
                severity="error",
                timeout=3,
            )

    def action_select_mode(self) -> None:
        def _on_mode_selected(selected_mode: Optional[str]):
            if selected_mode:
                self.set_mode(selected_mode)

        m_str = self._get_current_mode_val()
        self.push_screen(SessionModePickerModal(m_str), _on_mode_selected)

    def _get_active_mode_label(self) -> str:
        current_m = getattr(self.engine, "execution_mode", None) if hasattr(self, "engine") else None
        if not current_m:
            mem = getattr(self.engine, "memory", None) if hasattr(self, "engine") else None
            current_m = getattr(getattr(mem, "state", None), "execution_mode", "unified")
        m_str = (
            current_m.value if hasattr(current_m, "value") else str(current_m or "unified")
        )
        if "code" in m_str.lower():
            return "CODE"
        elif "goal" in m_str.lower():
            return "GOAL"
        elif "plan" in m_str.lower():
            return "PLAN"
        elif "unified" in m_str.lower():
            return "UNIFIED"
        return "CHAT"

    def _get_current_mode_val(self) -> str:
        current_m = getattr(self.engine, "execution_mode", None) if hasattr(self, "engine") else None
        if not current_m:
            mem = getattr(self.engine, "memory", None) if hasattr(self, "engine") else None
            current_m = getattr(getattr(mem, "state", None), "execution_mode", "unified")
        m_str = (
            current_m.value if hasattr(current_m, "value") else str(current_m or "unified")
        )
        m_lower = m_str.lower()
        if "code" in m_lower:
            return "code"
        elif "goal" in m_lower:
            return "goal"
        elif "plan" in m_lower:
            return "plan"
        elif "unified" in m_lower:
            return "unified"
        return "chat"

    def _get_mode_select_options(self) -> list[tuple[str, str]]:
        return [
            ("Mode: Code", "code"),
            ("Mode: Plan", "plan"),
            ("Mode: Chat", "chat"),
            ("Mode: Goal", "goal"),
            ("Mode: Unified", "unified"),
        ]


    @on(Select.Changed, "#mode-select-dropdown")
    def _on_mode_select_changed(self, event: Select.Changed) -> None:
        if event.value:
            self.set_mode(str(event.value))

    def _get_models_for_engine(self, engine: str = "") -> list[tuple[str, str]]:
        """Get model choices strictly tailored ONLY to the selected inference backend."""
        from pathlib import Path
        options: list[tuple[str, str]] = []
        repo_root = Path(__file__).resolve().parent.parent.parent
        workspace = Path(self.engine.project_root if hasattr(self, "engine") and self.engine else os.getcwd()).resolve()
        models_candidates = [
            workspace / "models",
            repo_root / "models",
            Path.cwd() / "models",
        ]
        models_dir = next((d for d in models_candidates if d.exists()), workspace / "models")
        engine_str = (engine or getattr(self, "provider_name", "llama.cpp") or "llama.cpp").lower()

        if "mlx" in engine_str:
            from rlm_optimized.config import is_valid_mlx_directory
            # 1. ./models directory MLX model folders ONLY
            if models_dir.exists():
                for item in sorted(models_dir.iterdir()):
                    if is_valid_mlx_directory(str(item)):
                        options.append((item.name, str(item.resolve())))

            # 2. ~/.cache/huggingface/hub snapshots for MLX models ONLY (verified complete)
            hf_dir = Path.home() / ".cache" / "huggingface" / "hub"
            if hf_dir.exists():
                for item in sorted(hf_dir.glob("models--*mlx*")):
                    snaps_dir = item / "snapshots"
                    if snaps_dir.exists():
                        for snap in snaps_dir.iterdir():
                            if is_valid_mlx_directory(str(snap)):
                                clean_name = item.name.replace("models--mlx-community--", "").replace("models--", "")
                                if not any(opt[0] == clean_name or opt[1] == str(snap.resolve()) for opt in options):
                                    options.append((clean_name, str(snap.resolve())))
                                break
            # 3. Ensure popular MLX Coder, Gemma, and Reasoning models are available
            if not any("DeepSeek-R1" in opt[0] for opt in options):
                options.append(("DeepSeek-R1-Distill-Qwen-7B-4bit", "mlx-community/DeepSeek-R1-Distill-Qwen-7B-4bit"))
            if not any("Qwen2.5-Coder-3B" in opt[0] for opt in options):
                options.append(("Qwen2.5-Coder-3B-Instruct-4bit", "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"))
            if not any("Qwen2.5-Coder-7B" in opt[0] for opt in options):
                options.append(("Qwen2.5-Coder-7B-Instruct-4bit", "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"))
            if not any("gemma-4-e4b" in opt[1].lower() for opt in options):
                options.append(("Gemma 4 E4B (MLX)", "mlx-community/gemma-4-E4B-it-4bit"))
            if not any("gemma-4-e2b" in opt[1].lower() for opt in options):
                options.append(("Gemma 4 E2B (MLX)", "mlx-community/gemma-4-E2B-it-4bit"))
            if not any("gemma-2-2b" in opt[1].lower() for opt in options):
                options.append(("Gemma 2 2B (MLX)", "mlx-community/gemma-2-2b-it-4bit"))

            if not options:
                options = [("Qwen2.5-Coder-3B-Instruct-4bit", "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit")]

        elif "lmstudio" in engine_str:
            # ONLY LM Studio models
            try:
                from rlm_optimized.config import fetch_provider_models, LMSTUDIO_BASE_URL
                lm_models = fetch_provider_models(LMSTUDIO_BASE_URL)
                for m_id in lm_models:
                    options.append((f"{m_id} (LM Studio)", m_id))
            except Exception:
                pass
            if not options:
                lmstudio_dir = Path.home() / ".lmstudio" / "models"
                if lmstudio_dir.exists():
                    for gguf in sorted(lmstudio_dir.rglob("*.gguf")):
                        sz_mb = gguf.stat().st_size / (1024 * 1024)
                        options.append((f"{gguf.name} ({sz_mb:.0f}MB)", str(gguf.resolve())))
            if not options:
                options = [("No LM Studio models found (check port 1234)", "lmstudio-default")]

        elif "ollama" in engine_str:
            # ONLY Ollama models
            try:
                from rlm_optimized.config import fetch_provider_models
                ol_models = fetch_provider_models("http://localhost:11434/v1")
                for m_id in ol_models:
                    options.append((f"{m_id} (Ollama)", m_id))
            except Exception:
                pass
            if not options:
                options = [("No Ollama models found (check port 11434)", "ollama-default")]

        else:
            # llama.cpp / TurboQuant — ONLY .gguf model files
            if models_dir.exists():
                for item in sorted(models_dir.iterdir()):
                    if item.is_file() and item.suffix == ".gguf":
                        sz_mb = item.stat().st_size / (1024 * 1024)
                        options.append((f"{item.name} ({sz_mb:.0f}MB)", str(item.resolve())))

            lmstudio_dir = Path.home() / ".lmstudio" / "models"
            if lmstudio_dir.exists():
                for gguf in sorted(lmstudio_dir.rglob("*.gguf")):
                    sz_mb = gguf.stat().st_size / (1024 * 1024)
                    if not any(opt[1] == str(gguf.resolve()) for opt in options):
                        options.append((f"{gguf.name} ({sz_mb:.0f}MB)", str(gguf.resolve())))

            if not options:
                options = [("qwen2.5-coder-3b-instruct-q4_k_m.gguf", "models/qwen2.5-coder-3b-instruct-q4_k_m.gguf")]

        curr_m = getattr(self, "model_name", "")
        if curr_m and curr_m != "default":
            matching_idx = next(
                (i for i, opt in enumerate(options) if opt[1] == curr_m or curr_m in opt[1] or opt[1] in curr_m),
                None,
            )
            if matching_idx is not None:
                matched_item = options.pop(matching_idx)
                val = curr_m if curr_m == matched_item[1] or curr_m in matched_item[1] else matched_item[1]
                options.insert(0, (matched_item[0], val))
            elif (("mlx" in engine_str and ("mlx" in curr_m.lower() or "safetensors" in curr_m.lower())) or 
                  ("llama" in engine_str and ("gguf" in curr_m.lower() or "qwen" in curr_m.lower() or "gemma" in curr_m.lower()))):
                options.insert(0, (curr_m, curr_m))

        return options

    def _populate_supported_models_near_chat(self, engine: str) -> None:
        """Populate the model dropdown near chat toolbar based strictly on selected backend engine."""
        try:
            dropdown = self.query_one("#model-select-dropdown", Select)
            options = self._get_models_for_engine(engine)
            dropdown.set_options(options)
            if options:
                curr = self.model_name
                matching = next(
                    (opt[1] for opt in options if opt[1] == curr or (curr and curr in opt[1]) or (curr and opt[1] in curr)),
                    None,
                )
                if matching is not None:
                    dropdown.value = matching
                    self.model_name = matching
                else:
                    dropdown.value = options[0][1]
                    self.model_name = options[0][1]
            self.update_sidebar_meta()
            self.update_status_bar()
        except Exception:
            pass

    @on(Select.Changed, "#sidebar-engine-select")
    def _on_sidebar_engine_changed(self, event: Select.Changed) -> None:
        if event.value:
            new_engine = str(event.value)
            self.provider_name = new_engine
            self.engine_provider = new_engine
            os.environ["PROVIDER"] = new_engine
            self._populate_supported_models_near_chat(new_engine)
            self.notify(
                f"Switched engine to: {new_engine.upper()}",
                severity="information",
                timeout=2,
            )
            self.update_sidebar_meta()

    @on(Button.Pressed, "#sidebar-apply-engine-btn")
    def _on_sidebar_apply_engine_pressed(self) -> None:
        try:
            eng = str(self.query_one("#sidebar-engine-select", Select).value)
            kv = str(self.query_one("#sidebar-kv-select", Select).value)
            try:
                ctx = int(self.query_one("#sidebar-ctx-select", Select).value)
                temp = float(self.query_one("#sidebar-temp-select", Select).value)
                rep_pen = float(self.query_one("#sidebar-rep-select", Select).value)
                threads = int(self.query_one("#sidebar-threads-select", Select).value)
            except Exception:
                ctx = 12288
                temp = 0.1
                rep_pen = 1.08
                threads = 4

            self.provider_name = eng
            self.engine_provider = eng
            self.kv_cache_mode = kv
            self.context_window_size = ctx

            os.environ["PROVIDER"] = eng
            if eng in ("llama.cpp", "llama-cpp", "turbo", "turboquant"):
                os.environ["KV_CACHE_COMPRESSION"] = kv
                save_last_state({"last_kv_cache_mode": kv})
            os.environ["RLM_CTX_SIZE"] = str(ctx)
            os.environ["THREADS"] = str(threads)
            os.environ["TEMPERATURE"] = str(temp)
            os.environ["REPEAT_PENALTY"] = str(rep_pen)
            os.environ["REPETITION_PENALTY"] = str(rep_pen)

            if hasattr(self, "engine") and self.engine and hasattr(self.engine, "client") and self.engine.client:
                if hasattr(self.engine.client, "temperature"):
                    self.engine.client.temperature = temp
                if hasattr(self.engine.client, "repeat_penalty"):
                    self.engine.client.repeat_penalty = rep_pen
                if hasattr(self.engine.client, "repetition_penalty"):
                    self.engine.client.repetition_penalty = rep_pen

            self._populate_supported_models_near_chat(eng)

            # Re-instantiate engine client matching the newly applied engine & model
            self._load_selected_model(self.model_name, auto_start=False)

            status_msg = self.query_one("#sidebar-engine-status-msg", Static)
            status_msg.update(f"[green]✓ Applied {eng.upper()} ({kv}) @ {ctx} ctx | rep={rep_pen}[/green]")

            self.notify(
                f"Applied: {eng.upper()} ({kv}, {ctx} ctx, rep={rep_pen}, {threads} thr)",
                severity="information",
                timeout=3,
            )
            self.update_sidebar_meta()
            self.update_status_bar()
            if not self.externally_managed:
                self._start_engine(force_restart=True)
        except Exception as e:
            self.notify(f"Error applying engine settings: {e}", severity="error", timeout=4)

    def _get_model_select_options(self) -> list[tuple[str, str]]:
        """Return all available models across MLX, TurboQuant GGUF, LM Studio, and Ollama."""
        from rlm_optimized.config import list_available_models, format_model_display_name
        options: list[tuple[str, str]] = []
        seen_ids: set[str] = set()
        try:
            available = list_available_models()
            for m in available:
                m_id = m.get("id", "")
                if not m_id or m_id in seen_ids:
                    continue
                seen_ids.add(m_id)
                label = m.get("name") or format_model_display_name(m_id, provider=m.get("provider", ""))
                options.append((label, m_id))
        except Exception:
            pass

        if not options:
            return self._get_models_for_engine(getattr(self, "provider_name", "llama.cpp"))

        curr = getattr(self, "model_name", "")
        if curr and curr != "default":
            matching_idx = next(
                (i for i, opt in enumerate(options) if opt[1] == curr or curr in opt[1] or opt[1] in curr),
                None,
            )
            if matching_idx is not None:
                matched_item = options.pop(matching_idx)
                options.insert(0, matched_item)

        return options

    def _is_model_connected(self) -> bool:
        try:
            from rlm_optimized.llamacpp_client import is_port_in_use

            return is_port_in_use(self.engine_port) or getattr(
                self, "_last_server_online", False
            )
        except Exception:
            return False

    @on(Select.Changed, "#model-select-dropdown")
    def _on_model_select_changed(self, event: Select.Changed) -> None:
        if event.value:
            new_model = str(event.value)
            if new_model != self.model_name:
                self._load_selected_model(new_model, auto_start=True)

    def _get_draft_model_select_options(self) -> list[tuple[str, str]]:
        options = []
        try:
            from rlm_optimized.config import list_available_draft_models

            drafts = list_available_draft_models(target_model=self.model_name)
            for d in drafts:
                label = str(d.get("name", d.get("id", "")))
                options.append((label, d["id"]))
        except Exception:
            options = [("None (Disabled)", "none"), ("Auto-Match Draft", "auto")]
        return options or [("None (Disabled)", "none")]

    @on(Button.Pressed, "#model-toggle-btn")
    def _on_model_toggle_pressed(self, event: Button.Pressed) -> None:
        btn_label = str(event.button.label).strip().upper()
        if btn_label == "UNLOAD" or self._is_model_connected():
            try:
                subprocess.run(
                    ["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL
                )
                subprocess.run(
                    ["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL
                )
            except Exception:
                pass
            self._last_server_online = False
            self._server_starting = False
            self._update_connection_state(False)
            self.notify(
                "Model unloaded & engine stopped",
                severity="information",
                timeout=2,
            )
            self._set_input_enabled(True)
        else:
            selected_model = self.model_name
            try:
                dropdown = self.query_one("#model-select-dropdown", Select)
                if dropdown.value:
                    selected_model = str(dropdown.value)
            except Exception:
                pass
            self._load_selected_model(selected_model, auto_start=True)

    def _load_selected_model(
        self, model_id: str, auto_start: bool = True
    ) -> None:
        """Unified model loader: configures provider, client, port runtime, and starts backend engine if auto_start=True."""
        if not model_id:
            return

        # Base provider detection from current active engine / state
        current_eng = getattr(self, "engine_provider", getattr(self, "provider_name", "turbo"))
        if current_eng in ("llama.cpp", "llama-cpp"):
            current_eng = "turbo"
        provider = current_eng or "turbo"
        name = model_id

        try:
            from rlm_optimized.config import (
                list_available_models,
                fetch_provider_models,
                format_model_display_name,
                LMSTUDIO_BASE_URL,
            )

            models = list_available_models()

            # Only query the provider that the detected engine actually uses,
            # instead of hitting all three servers (up to 6s timeout if all down).
            if provider == "lmstudio":
                lm_models = fetch_provider_models(LMSTUDIO_BASE_URL)
                for m_id in lm_models:
                    if not any(m["id"] == m_id for m in models):
                        models.append({"id": m_id, "name": f"{m_id} (LM Studio)", "provider": "lmstudio"})
            elif provider == "ollama":
                ollama_models = fetch_provider_models("http://localhost:11434/v1")
                for m_id in ollama_models:
                    if not any(m["id"] == m_id for m in models):
                        models.append({"id": m_id, "name": f"{m_id} (Ollama)", "provider": "ollama"})
            elif provider in ("llama-cpp", "turbo", "turboquant"):
                # Not "mlx": mlx_lm's /v1/models lists every MLX-ish repo in the
                # HF cache, not the loaded model, so it injects unrelated models.
                local_8080 = fetch_provider_models("http://localhost:8080/v1")
                for m_id in local_8080:
                    if not any(m["id"] == m_id for m in models):
                        p = "mlx" if ("mlx" in m_id.lower() or "deepseek" in m_id.lower() or "safetensors" in m_id.lower()) else "turbo"
                        models.append({"id": m_id, "name": f"{m_id} (Local Server)", "provider": p})

            for m in models:
                if m["id"] == model_id or m.get("id", "").lower() == model_id.lower():
                    provider = m.get("provider", provider)
                    name = m.get("name", model_id)
                    break
        except Exception:
            pass

        # Enhanced provider detection
        m_lower = model_id.lower()
        if (os.path.isdir(model_id) and os.path.exists(os.path.join(model_id, "config.json"))) or "safetensors" in m_lower or "snapshots" in m_lower:
            provider = "mlx"
        elif "mlx" in m_lower or model_id.startswith("mlx-community/"):
            provider = "mlx"
        elif ("deepseek" in m_lower or "r1" in m_lower) and not model_id.endswith(".gguf"):
            provider = "mlx"
        elif model_id.endswith(".gguf"):
            if provider == "lmstudio" or "lmstudio" in m_lower:
                provider = "lmstudio"
            else:
                provider = "turbo"
        elif "gemini" in m_lower:
            provider = "gemini"
        elif "ollama" in m_lower or ":" in model_id:
            provider = "ollama"
        elif "groq" in m_lower:
            provider = "groq"
        elif "together" in m_lower:
            provider = "together"
        elif "openrouter" in m_lower:
            provider = "openrouter"
        elif "openai" in m_lower or "gpt" in m_lower:
            provider = "openai"
        elif current_eng == "mlx" and not model_id.endswith(".gguf"):
            provider = "mlx"

        # Kill old server processes only when actively starting a model
        if auto_start:
            try:
                subprocess.run(
                    ["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL
                )
                subprocess.run(
                    ["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL
                )
                time.sleep(0.3)
            except Exception:
                pass

        save_last_state(
            {
                "last_model": model_id,
                "last_provider": provider,
                "last_provider_name": name,
            }
        )

        self.model_name = model_id
        self.provider_name = provider
        self.engine_provider = provider

        # 2. Re-instantiate engine client
        if provider in ("llama-cpp", "turbo", "turboquant"):
            from rlm_optimized.llamacpp_client import LlamaCppClient

            self.engine.client = LlamaCppClient(
                base_url="http://localhost:8080/v1", model=model_id
            )
        elif provider == "mlx":
            from rlm_optimized.cloud_client import CloudClient

            self.engine.client = CloudClient(
                provider="mlx",
                model=model_id,
                base_url="http://localhost:8080/v1",
                api_key="not-needed",
            )
        elif provider == "ollama":
            from rlm_optimized.ollama_client import OllamaClient

            self.engine.client = OllamaClient(model=model_id)
        elif provider == "lmstudio":
            from rlm_optimized.cloud_client import CloudClient
            from rlm_optimized.config import LMSTUDIO_BASE_URL, LMSTUDIO_API_KEY

            self.engine.client = CloudClient(
                provider=None,
                model=model_id,
                base_url=LMSTUDIO_BASE_URL,
                api_key=LMSTUDIO_API_KEY,
            )
        else:
            from rlm_optimized.cloud_client import CloudClient

            self.engine.client = CloudClient(provider=provider, model=model_id)

        # 3. Update engine port & runtime info
        self.engine_port, self.externally_managed = _provider_runtime_info(
            provider
        )

        # 4. Launch engine server if auto_start requested
        if auto_start:
            if self.engine_port <= 0:
                self._update_connection_state(True)
                self.notify(
                    f"Connected to {escape(name)}.",
                    severity="information",
                    timeout=3,
                )
            elif not self.externally_managed:
                self._start_engine(force_restart=True)
            else:
                if is_port_in_use(self.engine_port):
                    self._update_connection_state(True)
                    self.notify(
                        f"Connected to {escape(name)}.",
                        severity="information",
                        timeout=3,
                    )
                else:
                    self._update_connection_state(False)
                    self.notify(
                        f"Switched to {escape(name)}. Start service on port {self.engine_port}.",
                        severity="warning",
                        timeout=5,
                    )
        self.update_status_bar()
        self.update_sidebar_meta()

    def action_select_model(self) -> None:
        """Focus and open the model select dropdown (model badge click / toolbar)."""
        try:
            dropdown = self.query_one("#model-select-dropdown", Select)
            self.set_focus(dropdown)
            # Dynamically refresh model list so any new live models are immediately selectable
            current_val = dropdown.value
            options = self._get_model_select_options()
            dropdown.set_options(options)
            if current_val:
                dropdown.value = current_val
            dropdown.action_show_overlay()
        except Exception:
            pass


    def action_engine_config(self) -> None:
        """Open the Inference Engine & TurboQuant configuration modal."""
        def _on_engine_applied(result: Optional[dict]):
            if result:
                selected_engine = result.get("engine", "llama.cpp")
                selected_kv = result.get("kv_mode", "turbo3")
                selected_model = result.get("model", "")

                self.provider_name = selected_engine
                self.engine_provider = selected_engine
                self.kv_cache_mode = selected_kv
                if selected_model:
                    self.model_name = selected_model

                os.environ["KV_CACHE_COMPRESSION"] = selected_kv
                save_last_state({"last_kv_cache_mode": selected_kv})
                os.environ["PROVIDER"] = selected_engine

                self.notify(
                    f"⚡ Engine: {selected_engine.upper()} | Model: {os.path.basename(self.model_name)} | KV: {selected_kv}",
                    severity="information",
                    timeout=3,
                )
                self.update_sidebar_meta()
                self.update_status_bar()
                if not self.externally_managed:
                    self._start_engine(force_restart=True)

        self.push_screen(
            EngineConfigModal(
                current_engine=getattr(self, "provider_name", "llama.cpp"),
                current_kv_mode=getattr(self, "kv_cache_mode", "turbo3"),
                current_model=self.model_name,
            ),
            _on_engine_applied,
        )

    def action_open_folder(self) -> None:
        # Same thing as /cd with no argument. This used to be a separate copy that
        # forgot to os.chdir() and to persist last_workdir, so a workspace picked
        # with ctrl+o was silently lost on the next launch.
        self.action_open_folder_picker()

    @work(exclusive=True, group="ast_indexer", thread=True)
    def _start_ast_indexing(self) -> None:
        """Build the AST knowledge graph silently in background thread."""
        target = self.engine.project_root
        try:
            from rlm_optimized.ast_indexer import index_directory

            index_directory(target)
            self.call_from_thread(
                self.notify,
                f"✓ AST graph indexed for {os.path.basename(target)}",
                severity="information",
                timeout=2,
            )
        except Exception:
            pass

    @work
    async def _poll_server_launch(self) -> None:
        port = self.engine_port
        for _ in range(30):
            await asyncio.sleep(0.5)
            if is_port_in_use(port):
                self._server_starting = False
                self._last_server_online = True
                self._update_connection_state(True)
                self.update_status_bar()
                self.update_sidebar_meta()
                self.notify(
                    f"Engine server active on port {port}",
                    severity="information",
                    timeout=2,
                )
                return

        self._server_starting = False
        self._last_server_online = False
        self._update_connection_state(False)
        self.update_status_bar()
        self.update_sidebar_meta()
        self.notify(
            f"Engine server failed to bind to port {port} within 15 seconds",
            severity="error",
            timeout=5,
        )

    @on(Button.Pressed, "#toggle-engine-btn")
    def on_toggle_engine_btn(self) -> None:
        # toggle-engine-btn was removed from the input bar in v2 UX overhaul.
        # If somehow triggered (e.g. from a slash command), redirect to model picker.
        self.action_select_model()

    @on(Button.Pressed, "#start-engine-btn")
    def on_start_engine_btn(self) -> None:
        self._start_engine(force_restart=False)

    def _start_engine(self, force_restart: bool = False) -> None:
        container = self.query_one("#chat-container")

        if self.engine_port <= 0:
            self.notify(
                f"{escape(self.provider_name)} is a cloud provider, nothing to start locally",
                severity="information",
                timeout=2,
            )
            self.update_status_bar()
            self.update_sidebar_meta()
            return

        if not force_restart and is_port_in_use(self.engine_port):
            self._server_starting = False
            self._last_server_online = True
            self._update_connection_state(True)
            self.notify(
                f"Connected to {escape(self.provider_name)} on port {self.engine_port}",
                severity="information",
                timeout=2,
            )
            self.update_status_bar()
            self.update_sidebar_meta()
            return

        if self.externally_managed:
            self.notify(
                f"{escape(self.provider_name)} offline on port {self.engine_port}. Start it yourself, then retry.",
                severity="warning",
                timeout=5,
            )
            self.update_status_bar()
            self.update_sidebar_meta()
            return

        self._server_starting = True
        self.notify(
            f"Launching local engine on port {self.engine_port}...",
            severity="information",
            timeout=3,
        )
        if hasattr(self, "_conn_banner_widget") and self._conn_banner_widget:
            self._conn_banner_widget.update(
                f"  [bold yellow]Starting local engine server ({escape(self.model_name)})...[/]\n"
            )
        self.update_status_bar()
        self.update_sidebar_meta()

        pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        provider_str = getattr(self, "engine_provider", getattr(self, "provider_name", "")).lower()
        model_str = getattr(self, "model_name", "").lower()
        is_mlx = (
            "mlx" in provider_str
            or "mlx" in model_str
            or (isinstance(self.model_name, str) and os.path.isdir(self.model_name) and os.path.exists(os.path.join(self.model_name, "config.json")))
            or (isinstance(self.model_name, str) and ("deepseek" in model_str or "r1" in model_str) and not self.model_name.endswith(".gguf"))
        )
        script_name = (
            "start_mlx_server.sh"
            if is_mlx
            else "start_optimized_local.sh"
        )
        engine_root = getattr(self.engine, "project_root", "") if hasattr(self, "engine") else ""
        candidates = [
            os.path.join(pkg_dir, script_name),
            os.path.join(engine_root, "rlm_optimized", script_name) if engine_root else "",
            os.path.join(getattr(self, "project_root", ""), "rlm_optimized", script_name),
            os.path.join(os.getcwd(), "rlm_optimized", script_name),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name),
        ]
        target_script = None
        for cand in candidates:
            if cand and os.path.exists(cand):
                target_script = os.path.abspath(cand)
                break

        if not target_script:
            target_script = os.path.join(pkg_dir, script_name)

        if os.path.exists(target_script):
            try:
                # Terminate any previously running server processes to ensure the new model loads
                try:
                    subprocess.run(
                        ["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL
                    )
                    subprocess.run(
                        ["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL
                    )
                    time.sleep(0.5)
                except Exception:
                    pass

                log_dir = os.path.join(self.engine.project_root, ".torchlight")
                os.makedirs(log_dir, exist_ok=True)
                server_log_path = os.path.join(log_dir, "llama_server.log")
                server_log_file = open(server_log_path, "a", encoding="utf-8")

                env = os.environ.copy()
                env["PORT"] = str(self.engine_port)
                env["KV_CACHE_COMPRESSION"] = getattr(self, "kv_cache_mode", "turbo3")
                draft_arg = getattr(self, "draft_model_name", "none") or "none"
                if draft_arg != "none":
                    env["DRAFT_MODEL"] = draft_arg
                    env["DRAFT_MAX"] = str(getattr(self, "draft_max_tokens", 8))

                subprocess.Popen(
                    [target_script, self.model_name, draft_arg],
                    cwd=os.path.dirname(target_script),
                    stdout=server_log_file,
                    stderr=server_log_file,
                    start_new_session=True,
                    env=env,
                )
                self._poll_server_launch()
            except Exception as e:
                self._server_starting = False
                self.notify(
                    f"Failed to launch server: {escape(str(e))}",
                    severity="error",
                    timeout=5,
                )
                self.update_status_bar()
                self.update_sidebar_meta()
        else:
            self._server_starting = False
            self.notify(
                f"Server launch script not found: {target_script}",
                severity="error",
                timeout=5,
            )
            self.update_status_bar()
            self.update_sidebar_meta()

    @on(Button.Pressed, "#stop-engine-btn")
    def on_stop_engine_btn(self) -> None:
        if self.externally_managed:
            self.notify(
                f"{self.provider_name} is managed externally, stop it from its own app",
                severity="information",
                timeout=3,
            )
            return
        try:
            subprocess.run(["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL)
            self.notify("Engine server stopped", severity="warning", timeout=2)
        except Exception as e:
            self.notify(
                f"Failed to stop server: {escape(str(e))}", severity="error", timeout=5
            )

    @on(Button.Pressed, "#restart-engine-btn")
    def on_restart_engine_btn(self) -> None:
        if self.externally_managed:
            self.notify(
                f"Re-checking connection to {self.provider_name}...",
                severity="information",
                timeout=2,
            )
            self.update_status_bar()
            self.update_sidebar_meta()
            return

        self.notify(
            "Restarting with defaults (gemma 4 E2B + TurboQuant)...",
            severity="information",
            timeout=3,
        )

        # 1. Reset defaults to gemma 4 E2B and TurboQuant
        self.model_name = "gemma-4-E2B-it"
        self.provider_name = "llama.cpp + TurboQuant (3-bit/4-bit KV)"
        self.engine_port, self.externally_managed = _provider_runtime_info("turbo")
        from rlm_optimized.llamacpp_client import LlamaCppClient

        self.engine.client = LlamaCppClient(
            base_url="http://localhost:8080/v1", model=self.model_name
        )

        # 2. Terminate existing engine processes
        try:
            subprocess.run(["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL)
        except Exception:
            pass

        # 3. Re-launch local server
        self._start_engine(force_restart=True)
        self.update_status_bar()
        self.update_sidebar_meta()

    @on(Button.Pressed, "#kill-session-btn")
    def on_kill_session_btn(self) -> None:
        container = self.query_one("#chat-container")
        try:
            subprocess.run(["pkill", "-f", "llama-server"], stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-f", "mlx_lm.server"], stderr=subprocess.DEVNULL)
        except Exception:
            pass
        self.engine.sandbox.reset()
        self._is_running = False
        self._set_input_enabled(True)
        self._agent_state = "IDLE"
        self.update_status_bar()
        self.update_sidebar_meta()
        self.notify("Session killed, REPL memory reset", severity="warning", timeout=3)

    # NOTE: The model badge button click is handled by on_model_badge_clicked
    # above (bound to #input-model-badge) which focuses the toolbar model dropdown.

    # ── Approval Modal ──────────────────────────────────────────────────

    async def _handle_approval(self, tool_name: str, risk: str, args: dict) -> bool:
        if getattr(self, "_auto_approve_session", False):
            return True
        diff_entries = None
        diff_path = ""
        self._capture_prewrite_snapshot(tool_name, args)
        try:
            snapshot = None
            path = str(args.get("path") or args.get("file_path") or "")
            if path and os.path.isabs(path):
                snapshot = self._prewrite_snapshots.get(path)
            preview = build_diff_preview(
                tool_name, args, self.engine.project_root, old_text=snapshot
            )
            if preview is not None:
                _old, _new, diff_path, diff_entries = preview
        except Exception:
            pass
        res = await self.push_screen_wait(
            ApprovalModal(
                tool_name,
                risk,
                args,
                diff_entries=diff_entries,
                diff_path=diff_path,
            )
        )
        if res == "always":
            self._auto_approve_session = True
            self.notify(
                "Session auto-approval enabled for all tools",
                severity="information",
                timeout=3,
            )
            return True
        return bool(res)

    async def _handle_ask_user(self, args: dict) -> str:
        questions_list = args.get("questions")
        if isinstance(questions_list, list) and questions_list:
            res = await self.push_screen_wait(
                AskUserModal(
                    questions=questions_list,
                    allow_custom_input=bool(args.get("allow_custom_input", True)),
                )
            )
        else:
            question = args.get("question", "")
            options = args.get("options", [])
            is_multi = bool(args.get("is_multi_select", False))
            allow_custom = bool(args.get("allow_custom_input", True))
            res = await self.push_screen_wait(
                AskUserModal(
                    question=question,
                    options=options,
                    is_multi_select=is_multi,
                    allow_custom_input=allow_custom,
                )
            )
        return str(res or "No input provided.")

    def _capture_prewrite_snapshot(self, tool_name: str, args: dict) -> None:
        """Snapshot file contents *before* a diffable write executes.

        ``_handle_step`` runs after the write has landed, so reading the file
        there would show an empty diff. Capture the prior content here (the
        engine always routes CONFIRM/REVIEW file writes through approval).
        """
        if not isinstance(args, dict):
            return
        path = str(args.get("path") or args.get("file_path") or "")
        if (
            not path
            or not os.path.isabs(path)
            or tool_name not in ("WRITE_FILE", "EDIT_FILE", "CODE_FILE_WRITE")
        ):
            return
        if path in self._prewrite_snapshots:
            return
        old = ""
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    old = f.read()
        except OSError:
            old = ""
        self._prewrite_snapshots[path] = old

    # ── Actions ─────────────────────────────────────────────────────────
