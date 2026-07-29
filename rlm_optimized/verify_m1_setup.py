#!/usr/bin/env python3
"""
Torchlight M1 8GB Pre-Flight Check

Validates the entire setup for running Gemma 4 E2B with TurboQuant
4-bit KV cache on Mac M1 with 8GB RAM.

Usage:
    python3 -m rlm_optimized.verify_m1_setup
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rlm_optimized.config import (
    CHIP_NAME, TOTAL_RAM_GB, IS_8GB_DEVICE, IS_MACOS,
    CTX_SIZE, NUM_PREDICT, THREADS, METAL_GPU_LAYERS, MODEL_NAME,
)
from rlm_optimized.memory_monitor import (
    get_memory_pressure, is_memory_safe, format_memory_status,
)

# ── Color helpers ──────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
NC = "\033[0m"

def ok(msg: str) -> None:
    print(f"  {GREEN}✅ PASS{NC}  {msg}")

def fail(msg: str) -> None:
    print(f"  {RED}❌ FAIL{NC}  {msg}")

def warn(msg: str) -> None:
    print(f"  {YELLOW}⚠  WARN{NC}  {msg}")

def info(msg: str) -> None:
    print(f"  {CYAN}ℹ  INFO{NC}  {msg}")


def check_hardware() -> bool:
    """Check 1: Detect hardware."""
    print(f"\n{BOLD}[1/6] Hardware Detection{NC}")
    passed = True

    if IS_MACOS:
        ok(f"macOS detected")
    else:
        warn("Not macOS — Metal GPU acceleration unavailable")
        passed = False

    if CHIP_NAME != "unknown":
        ok(f"Chip: {CHIP_NAME}")
    else:
        fail("Could not detect chip name")
        passed = False

    if TOTAL_RAM_GB > 0:
        ok(f"RAM: {TOTAL_RAM_GB}GB")
    else:
        fail("Could not detect RAM size")
        passed = False

    if IS_8GB_DEVICE:
        info(f"8GB device mode ACTIVE → CTX={CTX_SIZE}, Predict={NUM_PREDICT}, Threads={THREADS}")
    else:
        info(f"Standard mode → CTX={CTX_SIZE}, Predict={NUM_PREDICT}, Threads={THREADS}")

    return passed


def check_model() -> bool:
    """Check 2: Verify model file exists and size is correct."""
    print(f"\n{BOLD}[2/6] Model File{NC}")
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Determine expected model file based on MODEL_NAME
    is_e4b = any(k in MODEL_NAME.lower() for k in ("e4b", "4e4b", "4e4"))
    target_filename = "gemma-4-E4B-it-Q4_K_M.gguf" if is_e4b else "gemma-4-E2B-it-Q4_K_M.gguf"
    model_path = os.path.join(project_root, "models", target_filename)

    # Check fallback models if target missing
    if not os.path.exists(model_path):
        for alt_file in ("gemma-4-E4B-it-Q4_K_M.gguf", "gemma-4-E2B-it-Q4_K_M.gguf", "qwen2.5-coder-7b-instruct-q4_k_m.gguf"):
            alt_path = os.path.join(project_root, "models", alt_file)
            if os.path.exists(alt_path) and os.path.getsize(alt_path) > 1_000_000_000:
                model_path = alt_path
                break

    if not os.path.exists(model_path):
        fail(f"Model not found: {model_path}")
        info("Run: python3 -m rlm_optimized.download_gemma4e4b  OR  python3 -m rlm_optimized.download_gemma")
        return False

    size_gb = os.path.getsize(model_path) / (1024 ** 3)
    if size_gb < 1.0:
        fail(f"Model file too small ({size_gb:.2f}GB) — likely corrupt")
        return False

    ok(f"Model found: {model_path} ({size_gb:.1f}GB)")
    return True


def check_llama_server_binary() -> bool:
    """Check 3: Verify llama-server is available."""
    print(f"\n{BOLD}[3/6] llama-server Binary{NC}")
    import shutil

    # Check PATH
    binary = shutil.which("llama-server")
    if binary:
        ok(f"llama-server found in PATH: {binary}")
        return True

    # Check common build directories
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    candidates = [
        os.path.join(project_root, "llama-cpp-turboquant", "build", "bin", "llama-server"),
        os.path.join(project_root, "llama.cpp", "build", "bin", "llama-server"),
    ]
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            ok(f"llama-server found at: {path}")
            return True

    fail("llama-server not found in PATH or common build directories")
    info("Install: brew install llama.cpp  OR  build from source with Metal")
    return False


def check_memory() -> bool:
    """Check 4: Check memory pressure."""
    print(f"\n{BOLD}[4/6] Memory Pressure{NC}")
    status = format_memory_status()
    pressure = get_memory_pressure()
    safe = is_memory_safe()

    print(f"  {status}")

    if safe:
        ok("Memory is safe for inference")
    else:
        warn(f"High memory pressure — swap: {pressure['swap_used_mb']:.0f}MB")
        info("Close heavy apps (browser, IDE) to free memory before running inference")

    return safe


def check_server_health(port: int = 8080) -> bool:
    """Check 5: Test if llama-server is running."""
    print(f"\n{BOLD}[5/6] llama-server Health (port {port}){NC}")
    url = f"http://localhost:{port}/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                ok(f"Server is running on port {port}")
                return True
            else:
                warn(f"Server returned status {resp.status}")
                return False
    except urllib.error.URLError:
        warn(f"Server not running on port {port}")
        info("Start it: ./rlm_optimized/start_optimized_local.sh")
        return False
    except Exception as e:
        warn(f"Could not reach server: {e}")
        return False


def check_inference(port: int = 8080) -> bool:
    """Check 6: Run a quick inference test."""
    print(f"\n{BOLD}[6/6] Quick Inference Test{NC}")
    url = f"http://localhost:{port}/v1/chat/completions"
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a coding assistant."},
            {"role": "user", "content": "Say 'hello world' in Python. Be very brief."},
        ],
        "temperature": 0.3,
        "max_tokens": 64,
    }

    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    try:
        start = time.time()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            elapsed = time.time() - start
            body = json.loads(resp.read().decode("utf-8"))

            content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = body.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)

            if content:
                ok(f"Inference successful ({elapsed:.1f}s)")
                info(f"Response: {content[:100].strip()}")
                if completion_tokens > 0 and elapsed > 0:
                    tps = completion_tokens / elapsed
                    info(f"Speed: {tps:.1f} tokens/s ({completion_tokens} tokens in {elapsed:.1f}s)")
                return True
            else:
                fail("Empty response from model")
                return False

    except urllib.error.URLError:
        warn("Server not running — skipping inference test")
        return False
    except Exception as e:
        fail(f"Inference test failed: {e}")
        return False


def main():
    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}  Torchlight Pre-Flight Check{NC}")
    print(f"{BOLD}  Gemma 4 E2B + TurboQuant q4_0 on {CHIP_NAME} ({TOTAL_RAM_GB}GB){NC}")
    print(f"{BOLD}{'='*60}{NC}")

    results = {}
    results["hardware"] = check_hardware()
    results["model"] = check_model()
    results["binary"] = check_llama_server_binary()
    results["memory"] = check_memory()
    results["server"] = check_server_health()

    if results["server"]:
        results["inference"] = check_inference()
    else:
        print(f"\n{BOLD}[6/6] Quick Inference Test{NC}")
        warn("Skipped — server not running")
        results["inference"] = False

    # Summary
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    critical = all(results[k] for k in ["hardware", "model"])

    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}  Results: {passed}/{total} checks passed{NC}")

    if critical and results.get("binary"):
        print(f"\n  {GREEN}🚀 Ready to launch!{NC}")
        print(f"  Terminal 1: ./rlm_optimized/start_optimized_local.sh")
        print(f"  Terminal 2: ./tui.sh turbo \"gemma 4 E2B\"")
    elif critical:
        print(f"\n  {YELLOW}⚠  Almost ready — install llama-server first{NC}")
    else:
        print(f"\n  {RED}❌ Critical checks failed — fix issues above{NC}")

    print()
    return 0 if critical else 1


if __name__ == "__main__":
    sys.exit(main())
