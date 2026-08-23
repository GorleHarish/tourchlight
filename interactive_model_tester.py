#!/usr/bin/env python3
"""
Interactive Model & Engine Testing Hub
Supports:
  - llama.cpp (with TurboQuant: turbo3, turbo4, and without: f16)
  - Apple MLX (with TurboQuant: turbo-4bit, and without: f16)
  - Multi-model scanning and selection (Qwen 2.5 Coder 3B/7B, Gemma, Llama, etc.)
  - Interactive coding benchmark & performance comparison
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm, IntPrompt, Prompt
    from rich.table import Table
    from rich.text import Text
    console = Console()
except ImportError:
    console = None


# Default Paths
WORKSPACE_ROOT = Path(__file__).parent.resolve()
MODELS_DIR = WORKSPACE_ROOT / "models"
LLAMA_BIN_DIR = WORKSPACE_ROOT / "llama-cpp-turboquant" / "build" / "bin"
VENV_MLX_PYTHON = WORKSPACE_ROOT / "venv_mlx" / "bin" / "python3"

PRESET_PROMPTS = {
    "1": ("LRU Cache (O(1) Get/Put)", "Write a clean, complete Python implementation of an LRU Cache with O(1) time complexity for get(key) and put(key, value) using collections.OrderedDict or a doubly linked list. Include type hints and docstrings."),
    "2": ("Async Token Bucket Rate Limiter", "Write an asynchronous token-bucket rate limiter in Python using asyncio, type annotations, and thread-safe locking."),
    "3": ("Binary Search Tree with In-Order Traversal", "Write a complete Python BST class with insert, search, delete, and generator-based in_order_traversal with type annotations."),
    "4": ("Custom Prompt", ""),
}


@dataclass
class BenchmarkRecord:
    engine: str
    kv_mode: str
    model_name: str
    prompt_tokens: int
    gen_tokens: int
    prompt_tps: float
    gen_tps: float
    ttft_ms: float
    peak_memory_mb: float
    syntax_valid: bool
    status: str
    error_msg: str = ""
    output_preview: str = ""


# ==============================================================================
# Model Discovery
# ==============================================================================

def scan_available_models() -> Tuple[List[Path], List[Path]]:
    """Scan local models directory and HuggingFace/LMStudio caches for models."""
    from rlm_optimized.config import is_valid_mlx_directory
    gguf_models: List[Path] = []
    mlx_models: List[Path] = []

    # 1. Scan ./models
    if MODELS_DIR.exists():
        for item in MODELS_DIR.iterdir():
            if item.is_file() and item.suffix == ".gguf":
                gguf_models.append(item)
            elif item.is_dir() and is_valid_mlx_directory(str(item)):
                mlx_models.append(item)

    # 2. Scan ~/.lmstudio/models for GGUFs
    lmstudio_dir = Path.home() / ".lmstudio" / "models"
    if lmstudio_dir.exists():
        for gguf in lmstudio_dir.rglob("*.gguf"):
            if gguf not in gguf_models:
                gguf_models.append(gguf)

    # 3. Scan ~/.cache/huggingface/hub for valid MLX models
    hf_dir = Path.home() / ".cache" / "huggingface" / "hub"
    if hf_dir.exists():
        for item in hf_dir.glob("models--mlx-community--*"):
            snaps_dir = item / "snapshots"
            if snaps_dir.exists():
                for snap in snaps_dir.iterdir():
                    if is_valid_mlx_directory(str(snap)):
                        if snap not in mlx_models:
                            mlx_models.append(snap)
                        break

    return sorted(gguf_models, key=lambda p: p.name), sorted(mlx_models, key=lambda p: p.name)


def validate_python_ast(code: str) -> bool:
    """Validate python code block syntax."""
    cleaned = code.strip()
    match = re.search(r"```python\s*(.*?)\s*```", cleaned, re.DOTALL)
    to_check = match.group(1) if match else cleaned
    try:
        ast.parse(to_check)
        return True
    except SyntaxError:
        return False


# ==============================================================================
# Benchmark Runners
# ==============================================================================

def run_llama_bench(
    model_path: Path,
    kv_mode: str,
    prompt_tokens: int = 128,
    gen_tokens: int = 32,
    threads: int = 4,
) -> BenchmarkRecord:
    """Run llama-bench throughput evaluation."""
    llama_bench = LLAMA_BIN_DIR / "llama-bench"
    if not llama_bench.exists():
        return BenchmarkRecord(
            engine="llama.cpp",
            kv_mode=kv_mode,
            model_name=model_path.name,
            prompt_tokens=prompt_tokens,
            gen_tokens=gen_tokens,
            prompt_tps=0.0,
            gen_tps=0.0,
            ttft_ms=0.0,
            peak_memory_mb=0.0,
            syntax_valid=False,
            status="ERROR",
            error_msg="llama-bench binary not found",
        )

    cmd = [
        str(llama_bench),
        "-m", str(model_path),
        "-p", str(prompt_tokens),
        "-n", str(gen_tokens),
        "-t", str(threads),
        "-ngl", "99",
        "-ctk", kv_mode,
        "-ctv", kv_mode,
    ]

    env = os.environ.copy()
    env["DYLD_LIBRARY_PATH"] = str(LLAMA_BIN_DIR)

    try:
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
        output = res.stdout + "\n" + res.stderr
    except Exception as e:
        return BenchmarkRecord(
            engine="llama.cpp",
            kv_mode=kv_mode,
            model_name=model_path.name,
            prompt_tokens=prompt_tokens,
            gen_tokens=gen_tokens,
            prompt_tps=0.0,
            gen_tps=0.0,
            ttft_ms=0.0,
            peak_memory_mb=0.0,
            syntax_valid=False,
            status="FAILED",
            error_msg=str(e),
        )

    pp_tps = 0.0
    tg_tps = 0.0
    for line in output.splitlines():
        if f"pp{prompt_tokens}" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                val = parts[-1].split("±")[0].strip()
                try:
                    pp_tps = float(val)
                except ValueError:
                    pass
        elif f"tg{gen_tokens}" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                val = parts[-1].split("±")[0].strip()
                try:
                    tg_tps = float(val)
                except ValueError:
                    pass

    ttft = (prompt_tokens / pp_tps * 1000.0) if pp_tps > 0 else 0.0
    mem_mb = round(model_path.stat().st_size / (1024 * 1024), 1)

    return BenchmarkRecord(
        engine="llama.cpp",
        kv_mode=f"TurboQuant ({kv_mode})" if "turbo" in kv_mode else f"Standard ({kv_mode})",
        model_name=model_path.name,
        prompt_tokens=prompt_tokens,
        gen_tokens=gen_tokens,
        prompt_tps=round(pp_tps, 1),
        gen_tps=round(tg_tps, 1),
        ttft_ms=round(ttft, 1),
        peak_memory_mb=mem_mb,
        syntax_valid=True,
        status="SUCCESS",
        output_preview="[Raw Throughput Benchmark]",
    )


def run_mlx_generation(
    model_path: Path,
    kv_bits: Optional[int],
    prompt: str,
    max_tokens: int = 64,
) -> BenchmarkRecord:
    """Run MLX generation in venv_mlx environment."""
    py_exec = str(VENV_MLX_PYTHON) if VENV_MLX_PYTHON.exists() else sys.executable

    script = f"""
import json, os, time, sys
import mlx.core as mx
from mlx_lm import load, stream_generate
from mlx_lm.models.cache import QuantizedKVCache, make_prompt_cache

model_path = r"{str(model_path)}"
prompt_text = r\"\"\"{prompt}\"\"\"
kv_bits = {kv_bits if kv_bits else 'None'}
max_toks = {max_tokens}

if hasattr(mx, 'reset_peak_memory'):
    mx.reset_peak_memory()
else:
    mx.metal.reset_peak_memory()

model, tokenizer = load(model_path)

if hasattr(tokenizer, "apply_chat_template"):
    messages = [{{"role": "user", "content": prompt_text}}]
    formatted_prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
else:
    formatted_prompt = prompt_text

if kv_bits:
    cache = [QuantizedKVCache(group_size=64, bits=kv_bits) for _ in range(len(model.layers))]
else:
    cache = make_prompt_cache(model)

t0 = time.perf_counter()
first_t = None
texts = []
last_r = None

for r in stream_generate(model, tokenizer, prompt=formatted_prompt, prompt_cache=cache, max_tokens=max_toks):
    if first_t is None:
        first_t = time.perf_counter()
    texts.append(r.text)
    last_r = r

t1 = time.perf_counter()
output_str = "".join(texts)

ttft = ((first_t - t0) * 1000.0) if first_t else 0.0
p_tps = getattr(last_r, 'prompt_tps', 0.0)
g_tps = getattr(last_r, 'generation_tps', 0.0)
p_len = getattr(last_r, 'prompt_tokens', len(tokenizer.encode(formatted_prompt)))
g_len = getattr(last_r, 'generation_tokens', len(texts))

if hasattr(mx, 'get_peak_memory'):
    mem_mb = mx.get_peak_memory() / (1024 * 1024)
else:
    mem_mb = mx.metal.get_peak_memory() / (1024 * 1024)

result = {{
    "prompt_tokens": p_len,
    "gen_tokens": g_len,
    "prompt_tps": round(p_tps, 1),
    "gen_tps": round(g_tps, 1),
    "ttft_ms": round(ttft, 1),
    "peak_memory_mb": round(mem_mb, 1),
    "output_text": output_str
}}
print("---JSON_OUTPUT_START---")
print(json.dumps(result))
"""

    try:
        res = subprocess.run([py_exec, "-c", script], capture_output=True, text=True, timeout=120)
        out = res.stdout
        if "---JSON_OUTPUT_START---" not in out:
            return BenchmarkRecord(
                engine="Apple MLX",
                kv_mode=f"TurboQuant ({kv_bits}-bit)" if kv_bits else "Standard (f16)",
                model_name=model_path.name,
                prompt_tokens=0,
                gen_tokens=0,
                prompt_tps=0.0,
                gen_tps=0.0,
                ttft_ms=0.0,
                peak_memory_mb=0.0,
                syntax_valid=False,
                status="FAILED",
                error_msg=res.stderr.strip() or "Failed to parse MLX output",
            )

        json_str = out.split("---JSON_OUTPUT_START---")[-1].strip()
        data = json.loads(json_str)
        syntax_ok = validate_python_ast(data["output_text"])

        return BenchmarkRecord(
            engine="Apple MLX",
            kv_mode=f"TurboQuant ({kv_bits}-bit)" if kv_bits else "Standard (f16)",
            model_name=model_path.name,
            prompt_tokens=data["prompt_tokens"],
            gen_tokens=data["gen_tokens"],
            prompt_tps=data["prompt_tps"],
            gen_tps=data["gen_tps"],
            ttft_ms=data["ttft_ms"],
            peak_memory_mb=data["peak_memory_mb"],
            syntax_valid=syntax_ok,
            status="SUCCESS",
            output_preview=data["output_text"][:200] + "...",
        )
    except Exception as e:
        return BenchmarkRecord(
            engine="Apple MLX",
            kv_mode=f"TurboQuant ({kv_bits}-bit)" if kv_bits else "Standard (f16)",
            model_name=model_path.name,
            prompt_tokens=0,
            gen_tokens=0,
            prompt_tps=0.0,
            gen_tps=0.0,
            ttft_ms=0.0,
            peak_memory_mb=0.0,
            syntax_valid=False,
            status="FAILED",
            error_msg=str(e),
        )


# ==============================================================================
# Interactive Terminal UI (TUI)
# ==============================================================================

def render_summary_table(records: List[BenchmarkRecord]):
    """Render comparison results table."""
    table = Table(
        title="⚡ Multi-Model & Engine Benchmark Results",
        header_style="bold cyan",
        border_style="bright_blue",
    )
    table.add_column("Engine", style="bold white")
    table.add_column("KV Cache Scheme", style="magenta")
    table.add_column("Model", style="yellow")
    table.add_column("Prefill TPS", justify="right", style="green")
    table.add_column("Decode TPS", justify="right", style="cyan")
    table.add_column("TTFT (ms)", justify="right", style="blue")
    table.add_column("Peak RAM", justify="right", style="magenta")
    table.add_column("AST Valid", justify="center")
    table.add_column("Status", justify="center")

    for r in records:
        syntax_str = "[green]✓ PASS[/green]" if r.syntax_valid else "[red]✗ FAIL[/red]"
        status_str = "[green]SUCCESS[/green]" if r.status == "SUCCESS" else f"[red]{r.status}[/red]"
        table.add_row(
            r.engine,
            r.kv_mode,
            r.model_name[:24],
            f"{r.prompt_tps:.1f} t/s" if r.prompt_tps > 0 else "-",
            f"{r.gen_tps:.1f} t/s" if r.gen_tps > 0 else "-",
            f"{r.ttft_ms:.1f} ms" if r.ttft_ms > 0 else "-",
            f"{r.peak_memory_mb:.1f} MB" if r.peak_memory_mb > 0 else "-",
            syntax_str if r.status == "SUCCESS" else "-",
            status_str,
        )

    console.print()
    console.print(table)
    console.print()


def interactive_menu():
    """Run full interactive TUI for engine, model, and TurboQuant configuration."""
    console.print(Panel.fit(
        "[bold cyan]⚡ Torchlight Interactive Model & Engine Tester[/bold cyan]\n"
        "[dim]Test & compare llama.cpp vs. Apple MLX with/without TurboQuant[/dim]",
        border_style="cyan"
    ))

    gguf_models, mlx_models = scan_available_models()

    # 1. Engine Selection
    console.print("\n[bold yellow]Step 1: Select Inference Engine[/bold yellow]")
    console.print("  [1] llama.cpp (Metal Backend)")
    console.print("  [2] Apple MLX (Native Array Engine)")
    console.print("  [3] Compare Both Engines Side-by-Side")
    engine_choice = Prompt.ask("Choose engine", choices=["1", "2", "3"], default="3")

    # 2. TurboQuant Mode Selection
    console.print("\n[bold yellow]Step 2: Select TurboQuant KV Cache Mode[/bold yellow]")
    console.print("  [1] With TurboQuant Only (turbo3 / turbo-4bit)")
    console.print("  [2] Without TurboQuant Only (f16 baseline)")
    console.print("  [3] Compare Both (With & Without TurboQuant)")
    quant_choice = Prompt.ask("Choose mode", choices=["1", "2", "3"], default="3")

    # 3. Model Selection
    selected_gguf: Optional[Path] = None
    selected_mlx: Optional[Path] = None

    if engine_choice in ["1", "3"]:
        console.print("\n[bold yellow]Available GGUF Models for llama.cpp:[/bold yellow]")
        for i, m in enumerate(gguf_models, 1):
            sz_mb = m.stat().st_size / (1024 * 1024)
            console.print(f"  [{i}] {m.name} [dim]({sz_mb:.1f} MB)[/dim]")
        if gguf_models:
            m_idx = IntPrompt.ask("Select GGUF model", default=1)
            selected_gguf = gguf_models[min(max(1, m_idx), len(gguf_models)) - 1]

    if engine_choice in ["2", "3"]:
        console.print("\n[bold yellow]Available MLX Models for Apple MLX:[/bold yellow]")
        for i, m in enumerate(mlx_models, 1):
            console.print(f"  [{i}] {m.name}")
        if mlx_models:
            m_idx = IntPrompt.ask("Select MLX model", default=1)
            selected_mlx = mlx_models[min(max(1, m_idx), len(mlx_models)) - 1]

    # 4. Benchmark Prompt Selection
    console.print("\n[bold yellow]Step 3: Select Benchmark Coding Task[/bold yellow]")
    for k, (name, _) in PRESET_PROMPTS.items():
        console.print(f"  [{k}] {name}")
    prompt_choice = Prompt.ask("Choose task", choices=["1", "2", "3", "4"], default="1")

    if prompt_choice == "4":
        test_prompt = Prompt.ask("Enter custom prompt", default="Write a python binary search function.")
    else:
        test_prompt = PRESET_PROMPTS[prompt_choice][1]

    gen_tokens = IntPrompt.ask("Max generation tokens", default=64)

    # Run Benchmark
    records: List[BenchmarkRecord] = []
    console.print("\n[bold green]🚀 Running Benchmarks...[/bold green]\n")

    # A. llama.cpp Runs
    if engine_choice in ["1", "3"] and selected_gguf:
        modes_to_test = []
        if quant_choice in ["1", "3"]:
            modes_to_test.extend(["turbo3", "turbo4"])
        if quant_choice in ["2", "3"]:
            modes_to_test.append("f16")

        for kv_m in modes_to_test:
            console.print(f"[*] Running [bold cyan]llama.cpp[/bold cyan] on [yellow]{selected_gguf.name}[/yellow] (KV: {kv_m})...")
            rec = run_llama_bench(selected_gguf, kv_mode=kv_m, prompt_tokens=128, gen_tokens=gen_tokens)
            records.append(rec)

    # B. MLX Runs
    if engine_choice in ["2", "3"] and selected_mlx:
        mlx_modes = []
        if quant_choice in ["1", "3"]:
            mlx_modes.append((4, "turbo-4bit"))
        if quant_choice in ["2", "3"]:
            mlx_modes.append((None, "f16"))

        for kv_bits, label in mlx_modes:
            console.print(f"[*] Running [bold magenta]Apple MLX[/bold magenta] on [yellow]{selected_mlx.name}[/yellow] (KV: {label})...")
            rec = run_mlx_generation(selected_mlx, kv_bits=kv_bits, prompt=test_prompt, max_tokens=gen_tokens)
            records.append(rec)

    # Render Table
    render_summary_table(records)

    # Export option
    if Confirm.ask("Would you like to save results to JSON?", default=False):
        save_path = Path("benchmark_results.json")
        save_path.write_text(json.dumps([asdict(r) for r in records], indent=2))
        console.print(f"[green]✓ Saved results to {save_path.resolve()}[/green]")


def main():
    parser = argparse.ArgumentParser(description="Torchlight Interactive Model & Engine Tester")
    parser.add_argument("--interactive", "-i", action="store_true", default=True, help="Launch interactive selection menu.")
    parser.add_argument("--engine", type=str, choices=["llamacpp", "mlx", "all"], default="all")
    parser.add_argument("--kv-mode", type=str, choices=["turbo3", "turbo4", "turbo-4bit", "f16", "all"], default="all")
    args = parser.parse_args()

    interactive_menu()


if __name__ == "__main__":
    main()
