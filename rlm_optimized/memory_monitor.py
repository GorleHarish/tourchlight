"""
Memory pressure monitor for macOS Apple Silicon.

Provides real-time memory pressure detection and swap monitoring
to prevent thrashing during LLM inference on 8GB devices.
"""

import subprocess
import re
import platform


def get_memory_pressure() -> dict:
    """Get current macOS memory pressure level and stats.

    Returns:
        dict with keys:
            level: "normal" | "warn" | "critical" | "unknown"
            swap_used_mb: float — current swap usage in MB
            swapins: int — total swap-in page count since boot
            ram_gb: int — total physical RAM in GB
    """
    result = {
        "level": "unknown",
        "swap_used_mb": 0.0,
        "swapins": 0,
        "ram_gb": 0,
    }

    if platform.system() != "Darwin":
        return result

    # Total RAM
    try:
        out = subprocess.check_output(
            ["sysctl", "-n", "hw.memsize"], text=True, timeout=3
        ).strip()
        result["ram_gb"] = int(out) // (1024 ** 3)
    except Exception:
        pass

    # Memory pressure level
    try:
        out = subprocess.check_output(
            ["memory_pressure"], text=True, timeout=5, stderr=subprocess.DEVNULL
        )
        if "NORMAL" in out.upper():
            result["level"] = "normal"
        elif "WARN" in out.upper():
            result["level"] = "warn"
        elif "CRITICAL" in out.upper():
            result["level"] = "critical"
    except FileNotFoundError:
        # memory_pressure command not available — fallback to vm_stat
        result["level"] = "unknown"
    except Exception:
        pass

    # vm_stat for swap-in counts
    try:
        vm = subprocess.check_output(
            ["vm_stat"], text=True, timeout=3
        )
        swapins = re.search(r"Swapins:\s+(\d+)", vm)
        if swapins:
            result["swapins"] = int(swapins.group(1))
    except Exception:
        pass

    # sysctl for swap usage
    try:
        swap = subprocess.check_output(
            ["sysctl", "-n", "vm.swapusage"], text=True, timeout=3
        ).strip()
        used_match = re.search(r"used\s*=\s*([\d.]+)M", swap)
        if used_match:
            result["swap_used_mb"] = float(used_match.group(1))
    except Exception:
        pass

    return result


def is_memory_safe(swap_threshold_mb: float = 1024.0) -> bool:
    """Quick check: is it safe to run inference without swap thrashing?

    Args:
        swap_threshold_mb: Maximum acceptable swap usage in MB.
                           Default is 1024MB since 8GB Macs typically
                           have some background swap usage even at idle.

    Returns:
        True if memory pressure is normal and swap is below threshold.
    """
    info = get_memory_pressure()
    if info["level"] == "critical":
        return False
    return info["swap_used_mb"] < swap_threshold_mb


def format_memory_status() -> str:
    """Return a human-readable one-line memory status string."""
    info = get_memory_pressure()
    level = info["level"].upper()

    level_icons = {
        "normal": "🟢",
        "warn": "🟡",
        "critical": "🔴",
        "unknown": "⚪",
    }
    icon = level_icons.get(info["level"], "⚪")

    swap_str = f"{info['swap_used_mb']:.0f}MB" if info["swap_used_mb"] > 0 else "0"

    return f"{icon} Memory: {level} | Swap: {swap_str} | RAM: {info['ram_gb']}GB"


if __name__ == "__main__":
    print(format_memory_status())
    info = get_memory_pressure()
    print(f"\nDetails: {info}")
    print(f"Safe for inference: {is_memory_safe()}")
