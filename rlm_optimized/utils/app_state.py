"""TUI state persistence across runs."""

from __future__ import annotations

import json
import os

STATE_FILE = os.path.expanduser("~/.torchlight_state.json")


def load_last_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_last_state(data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        state = load_last_state()
        state.update(data)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass
