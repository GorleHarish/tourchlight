"""CenterEmptyState — the welcome / idle screen shown in the editor pane.

Replaces the void black center when no file is open.  State-aware:

  • DISCONNECTED  → friendly onboarding with [Connect Model] CTA
  • CONNECTED_IDLE → quick-action suggestion chips
  • CONNECTED_WORKING → invisible (calling code hides it / shows spinner)

Design rules (matching the spec):
  - Never uses $error color for first-run / offline states.
  - All interaction goes through the parent App's actions.
  - Pure composition widget — no async work done here.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Static, Button, Label


# ── ASCII logo ────────────────────────────────────────────────────────────

_LOGO = """\
  ⚡  T O R C H L I G H T
     C O D E X  I D E
"""

_SUBTITLE = "Local AI Coding Agent"

# ── States ────────────────────────────────────────────────────────────────

STATE_DISCONNECTED = "disconnected"
STATE_IDLE = "idle"
STATE_WORKING = "working"


class CenterEmptyState(Container):
    """Full-pane empty state widget for the editor / center area.

    Mount this inside ``#editor-content-area`` when no file is open.
    Call :meth:`set_connection_state` to switch between states.
    """

    DEFAULT_CSS = """
    CenterEmptyState {
        width: 1fr;
        height: 1fr;
        align: center middle;
        background: $background;
        padding: 2 4;
    }

    CenterEmptyState #ces-inner {
        width: auto;
        height: auto;
        align: center middle;
        min-width: 48;
    }

    CenterEmptyState #ces-logo {
        text-align: center;
        color: $primary;
        text-style: bold;
        margin-bottom: 0;
    }

    CenterEmptyState #ces-subtitle {
        text-align: center;
        color: $foreground-muted;
        text-style: italic;
        margin-bottom: 2;
    }

    CenterEmptyState #ces-msg {
        text-align: center;
        color: $foreground-muted;
        margin-bottom: 1;
    }

    CenterEmptyState #ces-btn-row {
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    CenterEmptyState .ces-chip {
        margin: 0 1;
        min-width: 18;
    }

    CenterEmptyState #ces-connect-btn {
        margin: 0 1;
        min-width: 22;
    }

    CenterEmptyState #ces-divider {
        color: $panel;
        text-align: center;
        margin: 1 0;
    }

    CenterEmptyState #ces-hint {
        text-align: center;
        color: $foreground-muted;
        text-style: dim;
        margin-top: 2;
    }
    """

    def __init__(self, state: str = STATE_DISCONNECTED, **kwargs) -> None:
        super().__init__(**kwargs)
        self._state = state

    def compose(self) -> ComposeResult:
        with Vertical(id="ces-inner"):
            yield Static(_LOGO, id="ces-logo")
            yield Static(_SUBTITLE, id="ces-subtitle")
            yield Static("", id="ces-divider")
            # Placeholder — populated by set_connection_state()
            yield Static("", id="ces-msg")
            with Horizontal(id="ces-btn-row"):
                pass
            yield Static("", id="ces-hint")

    def on_mount(self) -> None:
        self.set_connection_state(self._state)

    # ── Public API ────────────────────────────────────────────────────────

    def set_connection_state(self, state: str, model_name: str = "") -> None:
        """Switch displayed content based on connection state."""
        self._state = state
        try:
            msg = self.query_one("#ces-msg", Static)
            btn_row = self.query_one("#ces-btn-row", Horizontal)
            hint = self.query_one("#ces-hint", Static)
            divider = self.query_one("#ces-divider", Static)

            # Clear buttons
            for child in list(btn_row.children):
                child.remove()

            divider.update("─" * 36)

            if state == STATE_DISCONNECTED:
                msg.update(
                    "[dim]No model connected.[/dim]\n"
                    "Press [bold $primary]Ctrl+M[/bold $primary] to connect to LM Studio."
                )
                btn_row.mount(
                    Button(
                        "  Connect Model  ",
                        id="ces-connect-btn",
                        variant="primary",
                        classes="ces-connect-btn",
                    )
                )
                hint.update(
                    "[dim]Tip: Start LM Studio, load a model, then press Ctrl+M[/dim]"
                )

            elif state == STATE_IDLE:
                name_display = f"[bold $success]● {model_name}[/]  " if model_name else ""
                msg.update(
                    f"{name_display}[dim]What would you like to build today?[/dim]"
                )
                for label, btn_id, variant in [
                    ("  New File  ", "ces-new-file-btn", "default"),
                    ("  Open Folder  ", "ces-open-folder-btn", "default"),
                    ("  Create React Component  ", "ces-chip-react-btn", "default"),
                    ("  Refactor File  ", "ces-chip-refactor-btn", "default"),
                ]:
                    btn_row.mount(
                        Button(
                            label,
                            id=btn_id,
                            variant=variant,
                            classes="ces-chip",
                        )
                    )
                hint.update(
                    "[dim]Type a message in the input below, or pick a quick action ↑[/dim]"
                )

            elif state == STATE_WORKING:
                msg.update("[dim]Agent is working…[/dim]")
                hint.update("")

        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Route chip buttons to app-level actions."""
        btn_id = event.button.id or ""
        app = self.app

        if btn_id == "ces-connect-btn":
            event.stop()
            try:
                app.action_select_model()
            except Exception:
                pass

        elif btn_id == "ces-open-folder-btn":
            event.stop()
            try:
                app.action_open_folder()
            except Exception:
                pass

        elif btn_id == "ces-new-file-btn":
            event.stop()
            # Notify app — new-file action
            try:
                app.notify("Use Ctrl+O to open a folder, then right-click a file.", timeout=3)
            except Exception:
                pass

        elif btn_id in ("ces-chip-react-btn", "ces-chip-refactor-btn", "ces-chip-explain-btn"):
            event.stop()
            snippets = {
                "ces-chip-react-btn": "Create a new React functional component with TypeScript props and Tailwind styling",
                "ces-chip-refactor-btn": "Refactor the currently open file to improve readability and performance",
                "ces-chip-explain-btn": "Explain the current codebase architecture",
            }
            msg = snippets.get(btn_id, "")
            if msg:
                try:
                    inp = app.query_one("#user-input")
                    inp.load_text(msg)
                    inp.focus()
                except Exception:
                    pass
