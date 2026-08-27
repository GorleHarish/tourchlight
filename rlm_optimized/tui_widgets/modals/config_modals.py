"""Engine and Session Mode Configuration Modals for Torchlight TUI.

Provides:
  - SessionModePickerModal: Mode switching dialog (Code, Plan, Chat, Goal, Unified).
  - EngineConfigModal: Inference backend (llama.cpp, MLX, LM Studio, Ollama) and TurboQuant KV mode selector.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from rich.markup import escape
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Select, Static


class SessionModePickerModal(ModalScreen[Optional[str]]):
    """Modal dialog for selecting session execution mode (Chat vs Goal)."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    SessionModePickerModal {
        align: center middle;
    }
    #mode-dialog {
        width: 90%;
        max-width: 74;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }
    #mode-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #mode-tooltip {
        background: $boost;
        color: $text-muted;
        padding: 1;
        margin: 1 0;
        border: solid $accent;
    }
    .mode-btn {
        margin: 1 0;
        width: 1fr;
    }
    """

    def __init__(self, current_mode: str = "chat"):
        super().__init__()
        self.current_mode = current_mode

    def compose(self) -> ComposeResult:
        with Vertical(id="mode-dialog"):
            yield Static("Select Torchlight Execution Mode", id="mode-title")
            yield Static(
                "Choose the operation mode for your session:\n\n"
                "• Code Mode: Direct surgical coding & task execution. Implements pending tasks from implementation_plan.md in source files.\n"
                "• Plan Mode: Brainstorm architecture, steps, & process. Writes/updates implementation_plan.md.\n"
                "• Chat Mode: Fast, lightweight Q&A. No disk task tracking files created.\n"
                "• Goal Mode: Continuous autonomous harness with disk-backed task graph (.torchlight/tasks.md).\n"
                "• Unified Mode: Dynamic phase auto-detection with full developer toolset.",
                id="mode-desc",
            )
            yield Static(
                "Tooltip: Plan Mode helps you brainstorm and maintain implementation_plan.md before coding. "
                "Code Mode executes pending tasks directly in source code files.",
                id="mode-tooltip",
            )
            with Horizontal():
                yield Button(
                    "Code Mode",
                    id="select-code-btn",
                    variant="primary",
                    classes="mode-btn",
                )
                yield Button(
                    "Plan Mode",
                    id="select-plan-btn",
                    variant="primary",
                    classes="mode-btn",
                )
                yield Button(
                    "Chat Mode",
                    id="select-chat-btn",
                    variant="default",
                    classes="mode-btn",
                )
                yield Button(
                    "Goal Mode",
                    id="select-goal-btn",
                    variant="success",
                    classes="mode-btn",
                )
                yield Button(
                    "Unified Mode",
                    id="select-unified-btn",
                    variant="warning",
                    classes="mode-btn",
                )
            yield Button("Cancel", id="cancel-mode-btn", variant="default")

    @on(Button.Pressed, "#select-code-btn")
    def select_code(self) -> None:
        self.dismiss("code")

    @on(Button.Pressed, "#select-chat-btn")
    def select_chat(self) -> None:
        self.dismiss("chat")

    @on(Button.Pressed, "#select-plan-btn")
    def select_plan(self) -> None:
        self.dismiss("plan")

    @on(Button.Pressed, "#select-goal-btn")
    def select_goal(self) -> None:
        self.dismiss("goal")

    @on(Button.Pressed, "#select-unified-btn")
    def select_unified(self) -> None:
        self.dismiss("unified")

    @on(Button.Pressed, "#cancel-mode-btn")
    def cancel_btn(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class EngineConfigModal(ModalScreen[Optional[dict]]):
    """Modal dialog for selecting Inference Engine and TurboQuant KV Cache mode."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    EngineConfigModal {
        align: center middle;
        background: #0d1117;
    }
    #engine-dialog {
        width: 90%;
        max-width: 76;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: solid $accent;
        padding: 1 2;
    }
    #engine-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #engine-desc {
        margin-bottom: 1;
    }
    #engine-info-box {
        background: $boost;
        color: $text-muted;
        padding: 1;
        margin: 1 0;
        border: solid $panel;
    }
    .engine-field-label {
        color: $text;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }
    #engine-backend-select, #engine-kv-select, #engine-model-select {
        width: 1fr;
        height: 1;
        margin-bottom: 1;
        border: none;
    }
    .engine-btn-row {
        height: 3;
        margin-top: 1;
        align: right middle;
    }
    .engine-modal-btn {
        border: none;
        padding: 0 2;
        height: 3;
        margin-left: 1;
    }
    """

    def __init__(
        self,
        current_engine: str = "llama.cpp",
        current_kv_mode: str = "turbo3",
        current_model: str = "",
    ):
        super().__init__()
        self.current_engine = current_engine or "llama.cpp"
        self.current_kv_mode = current_kv_mode or "turbo3"
        self.current_model = current_model or ""

    def _get_model_options_for_engine(self, engine: str) -> list[tuple[str, str]]:
        """Get model choices tailored to the selected inference backend."""
        options: list[tuple[str, str]] = []
        # Resolve repository root from rlm_optimized/tui_widgets/modals/ (4 levels up)
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        models_candidates = [
            repo_root / "models",
            Path.cwd() / "models",
            Path(__file__).resolve().parent.parent.parent / "models",
        ]
        models_dir = next((d for d in models_candidates if d.exists()), repo_root / "models")
        engine_str = (engine or "llama.cpp").lower()

        if "mlx" in engine_str:
            from rlm_optimized.config import is_valid_mlx_directory
            # 1. ./models directory MLX model folders ONLY
            if models_dir.exists():
                for item in sorted(models_dir.iterdir()):
                    if is_valid_mlx_directory(str(item)):
                        options.append((item.name, str(item.resolve())))

            # 2. ~/.cache/huggingface/hub snapshots (verified complete only)
            hf_dir = Path.home() / ".cache" / "huggingface" / "hub"
            if hf_dir.exists():
                for item in sorted(hf_dir.glob("models--*mlx*")):
                    snaps_dir = item / "snapshots"
                    if snaps_dir.exists():
                        for snap in snaps_dir.iterdir():
                            if is_valid_mlx_directory(str(snap)):
                                clean_name = item.name.replace("models--mlx-community--", "").replace("models--", "")
                                if not any(clean_name in opt[0] or opt[1] == str(snap.resolve()) for opt in options):
                                    options.append((f"{clean_name} (HuggingFace)", str(snap.resolve())))
                                break

            # 3. Ensure popular MLX Coder, Gemma, and Reasoning models are available
            if not any("DeepSeek-R1" in opt[0] for opt in options):
                options.append(("DeepSeek-R1-Distill-Qwen-7B-4bit (MLX)", "mlx-community/DeepSeek-R1-Distill-Qwen-7B-4bit"))
            if not any("Qwen2.5-Coder-3B" in opt[0] for opt in options):
                options.append(("Qwen2.5-Coder-3B-Instruct-4bit (MLX)", "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"))
            if not any("Qwen2.5-Coder-7B" in opt[0] for opt in options):
                options.append(("Qwen2.5-Coder-7B-Instruct-4bit (MLX)", "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"))
            if not any("gemma-4-e4b" in opt[1].lower() for opt in options):
                options.append(("Gemma 4 E4B (MLX)", "mlx-community/gemma-4-E4B-it-4bit"))
            if not any("gemma-4-e2b" in opt[1].lower() for opt in options):
                options.append(("Gemma 4 E2B (MLX)", "mlx-community/gemma-4-E2B-it-4bit"))
            if not any("gemma-2-2b" in opt[1].lower() for opt in options):
                options.append(("Gemma 2 2B (MLX)", "mlx-community/gemma-2-2b-it-4bit"))

        elif "lmstudio" in engine_str:
            try:
                from rlm_optimized.config import fetch_provider_models, LMSTUDIO_BASE_URL
                lm_models = fetch_provider_models(LMSTUDIO_BASE_URL)
                for m_id in lm_models:
                    options.append((f"{m_id} (LM Studio)", m_id))
            except Exception:
                pass
            lmstudio_dir = Path.home() / ".lmstudio" / "models"
            if lmstudio_dir.exists():
                for gguf in sorted(lmstudio_dir.rglob("*.gguf")):
                    sz_mb = gguf.stat().st_size / (1024 * 1024)
                    options.append((f"{gguf.name} ({sz_mb:.0f}MB LMStudio)", str(gguf.resolve())))

        elif "ollama" in engine_str:
            try:
                from rlm_optimized.config import fetch_provider_models
                ol_models = fetch_provider_models("http://localhost:11434/v1")
                for m_id in ol_models:
                    options.append((f"{m_id} (Ollama)", m_id))
            except Exception:
                pass

        else:
            # 1. ./models directory GGUF models
            if models_dir.exists():
                for item in sorted(models_dir.iterdir()):
                    if item.is_file() and item.suffix == ".gguf":
                        sz_mb = item.stat().st_size / (1024 * 1024)
                        options.append((f"{item.name} ({sz_mb:.0f}MB)", str(item.resolve())))

            # 2. ~/.lmstudio/models GGUF models
            lmstudio_dir = Path.home() / ".lmstudio" / "models"
            if lmstudio_dir.exists():
                for gguf in sorted(lmstudio_dir.rglob("*.gguf")):
                    sz_mb = gguf.stat().st_size / (1024 * 1024)
                    if not any(opt[1] == str(gguf.resolve()) for opt in options):
                        options.append((f"{gguf.name} ({sz_mb:.0f}MB LMStudio)", str(gguf.resolve())))

        if not options:
            if "mlx" in engine_str:
                options = [
                    ("Gemma 4 E2B (MLX)", "mlx-community/gemma-4-E2B-it-4bit"),
                    ("Gemma 4 E4B (MLX)", "mlx-community/gemma-4-E4B-it-4bit"),
                    ("Qwen 2.5 Coder 3B (MLX)", "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"),
                ]
            else:
                options = [
                    ("Gemma 4 E2B (Auto-Download)", "gemma-4-E2B-it-Q4_K_M.gguf"),
                    ("Gemma 4 E4B (Auto-Download)", "gemma-4-E4B-it-Q4_K_M.gguf"),
                    ("Qwen 2.5 Coder 3B (Auto-Download)", "qwen2.5-coder-3b-instruct-q4_k_m.gguf"),
                ]
        return options

    def compose(self) -> ComposeResult:
        engine_options = [
            ("llama.cpp (Metal Shading Language + TurboQuant)", "llama.cpp"),
            ("Apple MLX (Native Metal Array Engine)", "mlx"),
            ("LM Studio (Local REST API Server)", "lmstudio"),
            ("Ollama (Local REST API Server)", "ollama"),
        ]

        kv_options = [
            ("turbo3 (3-bit TurboQuant — ~75% KV Memory Reduction)", "turbo3"),
            ("turbo4 (4-bit TurboQuant — Balanced Speed & Precision)", "turbo4"),
            ("f16 (Standard Baseline — Without TurboQuant)", "f16"),
        ]

        model_options = self._get_model_options_for_engine(self.current_engine)
        initial_model_val = self.current_model
        if not any(o[1] == initial_model_val for o in model_options):
            initial_model_val = model_options[0][1]

        with Vertical(id="engine-dialog"):
            yield Static("⚡ Inference Engine & TurboQuant Setup", id="engine-title")
            yield Static(
                "Configure your target execution backend and KV cache quantization scheme.\n"
                "• [bold]llama.cpp[/bold]: Ultra-low memory overhead (~150MB base) with hand-crafted Metal LUT shaders.\n"
                "• [bold]Apple MLX[/bold]: Python-native array execution with high generation throughput on M-series chips.\n"
                "• [bold]TurboQuant[/bold]: Compresses KV cache down to 3-bit / 4-bit, enabling 16k–32k context on 8GB/16GB Macs.",
                id="engine-desc",
            )
            yield Static(
                "💡 Tip: Select 'turbo3' or 'turbo4' for long multi-file coding sessions without swapping, "
                "or 'f16' for standard unquantized floating point operations.",
                id="engine-info-box",
            )

            yield Static("Select Inference Backend Engine:", classes="engine-field-label")
            yield Select(
                engine_options,
                value=self.current_engine if any(o[1] == self.current_engine for o in engine_options) else "llama.cpp",
                id="engine-backend-select",
                allow_blank=False,
            )

            yield Static("Select Model for Coding Agent:", classes="engine-field-label")
            yield Select(
                model_options,
                value=initial_model_val,
                id="engine-model-select",
                allow_blank=False,
            )

            yield Static("Select TurboQuant KV Cache Compression Mode:", classes="engine-field-label")
            yield Select(
                kv_options,
                value=self.current_kv_mode if any(o[1] == self.current_kv_mode for o in kv_options) else "turbo3",
                id="engine-kv-select",
                allow_blank=False,
            )

            with Horizontal(classes="engine-btn-row"):
                yield Button("Cancel", id="cancel-engine-btn", classes="engine-modal-btn")
                yield Button(
                    "Apply Engine Settings",
                    id="apply-engine-btn",
                    variant="primary",
                    classes="engine-modal-btn",
                )

    @on(Select.Changed, "#engine-backend-select")
    def on_engine_changed(self, event: Select.Changed) -> None:
        try:
            model_dropdown = self.query_one("#engine-model-select", Select)
            opts = self._get_model_options_for_engine(str(event.value))
            model_dropdown.set_options(opts)
            if opts:
                model_dropdown.value = opts[0][1]
        except Exception:
            pass

    @on(Button.Pressed, "#apply-engine-btn")
    def on_apply(self) -> None:
        try:
            eng = self.query_one("#engine-backend-select", Select).value
            model = self.query_one("#engine-model-select", Select).value
            kv = self.query_one("#engine-kv-select", Select).value
            self.dismiss({"engine": eng, "model": model, "kv_mode": kv})
        except Exception:
            self.dismiss(None)

    @on(Button.Pressed, "#cancel-engine-btn")
    def on_cancel(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
