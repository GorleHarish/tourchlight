"""Shared utilities for rlm_optimized package."""

from rlm_optimized.utils.app_state import STATE_FILE, load_last_state, save_last_state
from rlm_optimized.utils.clipboard import copy_to_clipboard

__all__ = [
    "STATE_FILE",
    "copy_to_clipboard",
    "load_last_state",
    "save_last_state",
]
