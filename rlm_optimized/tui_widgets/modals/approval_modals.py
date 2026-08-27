"""Approval and User Question Modal Screens for Torchlight TUI.

Provides:
  - ApprovalModal: Confirmation dialog for high-risk / review tool calls and file edits.
  - AskUserModal: Multi-question & single-question interactive review dialog.
"""

from __future__ import annotations

import json
from typing import Optional, Union

from rich.markup import escape
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, RadioButton, RadioSet, Static

from rlm_optimized.tui_widgets.diff_view import diff_markup


class ApprovalModal(ModalScreen[Union[bool, str]]):
    """Production-grade modal dialog for tool & file modification approval."""

    BINDINGS = [
        ("y", "allow", "Allow"),
        ("Y", "allow", "Allow"),
        ("enter", "allow", "Allow"),
        ("a", "always_allow", "Always Allow"),
        ("A", "always_allow", "Always Allow"),
        ("n", "deny", "Deny"),
        ("N", "deny", "Deny"),
        ("escape", "deny", "Deny"),
    ]

    DEFAULT_CSS = """
    ApprovalModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #approval-dialog {
        width: 90%;
        max-width: 84;
        max-height: 85%;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    #approval-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    #approval-tool {
        margin-bottom: 1;
        color: $foreground;
    }
    #approval-args {
        color: $success;
        max-height: 6;
        overflow-y: auto;
        border: solid $panel;
        background: $background;
        padding: 1;
    }
    #approval-diff-label {
        margin-top: 1;
        margin-bottom: 1;
        color: $warning;
        text-style: bold;
    }
    #approval-diff {
        color: $foreground;
        max-height: 16;
        overflow-y: auto;
        border: solid $panel;
        background: $background;
        padding: 1;
    }
    #approval-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    #approval-buttons Button {
        margin: 0 1;
        min-width: 18;
    }
    #approval-hint {
        text-align: center;
        color: $foreground-muted;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        tool_name: str,
        risk: str,
        tool_args: dict,
        *,
        diff_entries: list | None = None,
        diff_path: str = "",
    ):
        super().__init__()
        self.tool_name = tool_name
        self.risk = risk
        self.tool_args = tool_args
        self.diff_entries = diff_entries or []
        self.diff_path = diff_path

    def compose(self) -> ComposeResult:
        risk_label = (
            f"RISK LEVEL: {self.risk.upper()}" if self.risk else "RISK LEVEL: CONFIRM"
        )

        with Vertical(id="approval-dialog"):
            yield Static(
                f"[{risk_label}]\nModification requires manual operational validation.",
                id="approval-title",
            )
            yield Static(
                f"Action Payload: [bold bright_yellow]{escape(self.tool_name)}[/]",
                id="approval-tool",
            )

            display_args = dict(self.tool_args) if self.tool_args else {}
            if self.tool_name == "WRITE_FILE" and "content" in display_args:
                display_args["content"] = (
                    f"... [{len(str(display_args['content']))} chars of code hidden]"
                )
            elif self.tool_name == "EDIT_FILE":
                if "old_text" in display_args:
                    display_args["old_text"] = (
                        f"... [{len(str(display_args['old_text']))} chars hidden]"
                    )
                if "new_text" in display_args:
                    display_args["new_text"] = (
                        f"... [{len(str(display_args['new_text']))} chars hidden]"
                    )

            args_str = json.dumps(display_args, indent=2)
            if len(args_str) > 4000:
                args_str = args_str[:4000] + "\n... [Arguments Truncated]"
            yield Static(escape(args_str), id="approval-args")
            if self.diff_entries:
                yield Static(
                    f"DIFF PREVIEW -- {escape(self.diff_path or 'file')}",
                    id="approval-diff-label",
                )
                yield Static(
                    diff_markup(self.diff_entries, max_lines=120),
                    id="approval-diff",
                )
            with Horizontal(id="approval-buttons"):
                yield Button("APPROVE (Enter / Y)", variant="success", id="allow-btn")
                yield Button("REJECT (Esc / N)", variant="error", id="deny-btn")
                yield Button("ALWAYS ALLOW (A)", variant="warning", id="always-btn")

            yield Static(
                "[dim]Press Enter / Y to approve, N or Esc to reject, A for session auto-approve[/dim]",
                id="approval-hint",
            )

    def on_mount(self) -> None:
        try:
            self.set_focus(self.query_one("#allow-btn"))
        except Exception:
            pass

    def action_allow(self) -> None:
        self.dismiss(True)

    def action_deny(self) -> None:
        self.dismiss(False)

    def action_always_allow(self) -> None:
        self.dismiss("always")

    @on(Button.Pressed, "#allow-btn")
    def on_allow(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#deny-btn")
    def on_deny(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#always-btn")
    def on_always(self) -> None:
        self.dismiss("always")


class AskUserModal(ModalScreen[str]):
    """Interactive modal dialog for structured user review options and custom input."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+enter", "submit", "Submit"),
    ]

    DEFAULT_CSS = """
    AskUserModal {
        align: center middle;
        background: #0d1117;
    }
    #ask-dialog {
        width: 90%;
        max-width: 86;
        max-height: 85%;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }
    #ask-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    .ask-question-header {
        color: $foreground;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }
    #ask-options-container {
        max-height: 18;
        overflow-y: auto;
        border: solid $panel;
        background: $background;
        padding: 1;
        margin-bottom: 1;
    }
    .ask-q-group {
        margin-bottom: 1;
    }
    #ask-custom-label {
        color: $text-muted;
        margin-top: 1;
        margin-bottom: 0;
    }
    #ask-custom-input {
        margin-bottom: 1;
    }
    #ask-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    #ask-buttons Button {
        border: none;
        padding: 0 1;
        height: 3;
        margin: 0 1;
        min-width: 18;
    }
    """

    def __init__(
        self,
        question: str = "",
        options: Optional[list[str]] = None,
        is_multi_select: bool = False,
        allow_custom_input: bool = True,
        questions: Optional[list[dict]] = None,
    ) -> None:
        super().__init__()
        if questions and isinstance(questions, list):
            self.questions = questions
        elif question or options:
            self.questions = [
                {
                    "question": question or "Agent requested input:",
                    "options": options or [],
                    "is_multi_select": is_multi_select,
                    "allow_custom_input": allow_custom_input,
                }
            ]
        else:
            self.questions = []
        self.allow_custom_input = allow_custom_input

    def compose(self) -> ComposeResult:
        with Vertical(id="ask-dialog"):
            yield Label("❓ Agent Question / Plan Review", id="ask-title")

            if self.questions:
                with VerticalScroll(id="ask-options-container"):
                    for q_idx, q_data in enumerate(self.questions):
                        q_text = q_data.get("question", f"Question {q_idx + 1}")
                        yield Label(f"❓ {q_text}", classes="ask-question-header")
                        q_opts = q_data.get("options", [])
                        is_multi = bool(q_data.get("is_multi_select", False))
                        if q_opts:
                            if not is_multi:
                                with RadioSet(id=f"ask-radioset-{q_idx}", classes="ask-q-group"):
                                    for opt_idx, opt in enumerate(q_opts):
                                        yield RadioButton(opt, value=(opt_idx == 0), id=f"ask-radio-{q_idx}-{opt_idx}")
                            else:
                                with Vertical(id=f"ask-checkgroup-{q_idx}", classes="ask-q-group"):
                                    for opt_idx, opt in enumerate(q_opts):
                                        yield Checkbox(opt, value=(opt_idx == 0), id=f"ask-check-{q_idx}-{opt_idx}")

            if self.allow_custom_input:
                yield Label("Custom input / additional feedback (optional):", id="ask-custom-label")
                yield Input(placeholder="Type your response here...", id="ask-custom-input")

            with Horizontal(id="ask-buttons"):
                yield Button("Submit [Enter]", variant="primary", id="ask-submit-btn")
                yield Button("Dismiss [Esc]", variant="default", id="ask-cancel-btn")

    def action_cancel(self) -> None:
        self.dismiss("User dismissed prompt without input.")

    def action_submit(self) -> None:
        self._perform_submit()

    @on(Button.Pressed, "#ask-cancel-btn")
    def on_cancel_btn(self) -> None:
        self.dismiss("User dismissed prompt without input.")

    @on(Button.Pressed, "#ask-submit-btn")
    def on_submit_btn(self) -> None:
        self._perform_submit()

    @on(Input.Submitted, "#ask-custom-input")
    def on_input_submitted(self) -> None:
        self._perform_submit()

    def _perform_submit(self) -> None:
        results = []
        is_single = len(self.questions) == 1
        for q_idx, q_data in enumerate(self.questions):
            q_text = q_data.get("question", f"Question {q_idx + 1}")
            q_opts = q_data.get("options", [])
            is_multi = bool(q_data.get("is_multi_select", False))
            selected: list[str] = []
            if q_opts:
                if not is_multi:
                    try:
                        radio_set = self.query_one(f"#ask-radioset-{q_idx}", RadioSet)
                        if radio_set.pressed_button:
                            selected.append(str(radio_set.pressed_button.label))
                    except Exception:
                        pass
                else:
                    for opt_idx, opt in enumerate(q_opts):
                        try:
                            cb = self.query_one(f"#ask-check-{q_idx}-{opt_idx}", Checkbox)
                            if cb.value:
                                selected.append(opt)
                        except Exception:
                            pass
            if selected:
                sel_str = selected[0] if not is_multi else ", ".join(selected)
                if is_single:
                    results.append(f"Selected: {sel_str}")
                else:
                    results.append(f"{q_text}: Selected: {sel_str}")

        custom_text = ""
        if self.allow_custom_input:
            try:
                inp = self.query_one("#ask-custom-input", Input)
                custom_text = inp.value.strip()
            except Exception:
                pass

        if custom_text:
            results.append(f"Custom Input: {custom_text}")

        final_ans = "\n".join(results) if results else "User confirmed."
        self.dismiss(final_ans)
