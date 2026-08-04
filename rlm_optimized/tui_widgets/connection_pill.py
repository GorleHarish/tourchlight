"""ConnectionPill — compact header widget showing live model/server status.

Replaces the red error banner and the misplaced "Load Model" button.

Design rules:
  - CONNECTED: green ● ModelName (Local)
  - DISCONNECTED: muted gray ○ Offline — ^M Connect
  - Clicking the pill opens the model picker modal (action_select_model).
  - NEVER uses $error color for disconnected — that is expected first-run state.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Button, Static
from textual.containers import Horizontal


class ConnectionPill(Horizontal):
    """Compact connection status pill for the top HUD header.

    Usage in compose()::

        yield ConnectionPill(id="connection-pill")

    Update via::

        pill.set_connected(True, model_name="Qwen-7B")
        pill.set_connected(False)
    """

    DEFAULT_CSS = """
    ConnectionPill {
        width: auto;
        height: 1;
        align: left middle;
        background: transparent;
    }

    ConnectionPill #cp-pill-btn {
        width: auto;
        height: 1;
        padding: 0 1;
        border: none;
        background: transparent;
        text-style: bold;
    }

    ConnectionPill #cp-pill-btn.cp-online {
        color: $success;
    }

    ConnectionPill #cp-pill-btn.cp-offline {
        color: $foreground-muted;
    }

    ConnectionPill #cp-pill-btn:hover {
        background: $surface;
        color: $accent;
    }

    ConnectionPill #cp-pill-btn:focus {
        background: $panel;
    }
    """

    def __init__(self, connected: bool = False, model_name: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._connected = connected
        self._model_name = model_name

    def compose(self) -> ComposeResult:
        label = self._build_label()
        classes = "cp-online" if self._connected else "cp-offline"
        yield Button(label, id="cp-pill-btn", classes=classes)

    def _build_label(self) -> str:
        if self._connected and self._model_name:
            return f"● {self._model_name} (Local)"
        elif self._connected:
            return "● Connected"
        else:
            return "○ Offline  ^M"

    # ── Public API ────────────────────────────────────────────────────────

    def set_connected(self, connected: bool, model_name: str = "") -> None:
        """Update the pill's connected state and model name."""
        self._connected = connected
        self._model_name = model_name
        try:
            btn = self.query_one("#cp-pill-btn", Button)
            btn.label = self._build_label()
            btn.remove_class("cp-online", "cp-offline")
            btn.add_class("cp-online" if connected else "cp-offline")
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cp-pill-btn":
            event.stop()
            try:
                self.app.action_select_model()
            except Exception:
                pass
