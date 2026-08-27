"""Hardware detection, Apple Silicon RAM inspection, and GPU core tuning."""

from __future__ import annotations

import platform
import socket
import subprocess as _sp


def _detect_apple_silicon_ram() -> int:
    """Detect total RAM in GB on macOS."""
    try:
        out = _sp.check_output(
            ["sysctl", "-n", "hw.memsize"], text=True, timeout=3
        ).strip()
        return int(out) // (1024**3)
    except Exception:
        return 0


def _detect_chip() -> str:
    """Detect Apple Silicon chip name (e.g., 'Apple M1')."""
    try:
        out = _sp.check_output(
            ["sysctl", "-n", "machdep.cpu.brand_string"], text=True, timeout=3
        ).strip()
        return out
    except Exception:
        return "unknown"


IS_MACOS = platform.system() == "Darwin"
TOTAL_RAM_GB = _detect_apple_silicon_ram() if IS_MACOS else 0
CHIP_NAME = _detect_chip() if IS_MACOS else "unknown"
IS_8GB_DEVICE = 0 < TOTAL_RAM_GB <= 8

# M1 Thread Tuning: Use perf cores only to avoid thread migration overhead
METAL_GPU_LAYERS = 99
THREADS = 4 if IS_8GB_DEVICE else 8


def is_port_in_use(port: int = 8080) -> bool:
    """Check if server port is actively listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) == 0
