"""Unit tests verifying that all @on message handlers and BINDINGS from mixin
classes are correctly registered and responsive on TorchlightApp."""

import pytest
from unittest.mock import MagicMock
from textual.widgets import Button, Select
from textual import on
from rlm_optimized.tui_app import TorchlightApp, _register_mixin_handlers_and_bindings


def test_mixin_decorated_handlers_registered():
    """Verify that TorchlightApp has collected all @on handlers across all mixins."""
    assert len(TorchlightApp._decorated_handlers) > 0

    # Ensure key message types are present
    msg_types = [t.__name__ for t in TorchlightApp._decorated_handlers.keys()]
    assert "Pressed" in msg_types
    assert "Changed" in msg_types

    # Ensure critical button and select handlers are registered
    pressed_handlers = [
        h[0].__name__
        for h in TorchlightApp._decorated_handlers.get(Button.Pressed, [])
    ]
    assert "on_send_button" in pressed_handlers
    assert "on_wipe_context_btn_clicked" in pressed_handlers
    assert "on_compact_btn_clicked" in pressed_handlers
    assert "on_mode_toggle_pressed" in pressed_handlers
    assert "_on_attach_context_btn_pressed" in pressed_handlers

    changed_handlers = [
        h[0].__name__
        for h in TorchlightApp._decorated_handlers.get(Select.Changed, [])
    ]
    assert "_on_mode_select_changed" in changed_handlers
    assert "_on_model_select_changed" in changed_handlers


def test_mixin_bindings_registered():
    """Verify that TorchlightApp has merged all BINDINGS across all mixins."""
    binding_actions = {b.action for b in TorchlightApp.BINDINGS}
    assert "toggle_editor_split" in binding_actions
    assert "engine_config" in binding_actions
    assert "select_mode" in binding_actions
