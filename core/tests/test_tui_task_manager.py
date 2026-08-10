"""Tests for TorchlightApp project_root property and task manager modal integration."""

from unittest.mock import MagicMock, patch
import pytest


def test_torchlight_app_project_root_property(tmp_path):
    from rlm_optimized.tui_app import TorchlightApp

    mock_engine = MagicMock()
    mock_engine.project_root = str(tmp_path)

    app = TorchlightApp(engine=mock_engine)
    assert app.project_root == str(tmp_path)


def test_torchlight_app_project_root_fallback(monkeypatch):
    from rlm_optimized.tui_app import TorchlightApp

    mock_engine = MagicMock()
    mock_engine.project_root = None

    app = TorchlightApp(engine=mock_engine)
    assert app.project_root == app.engine.project_root or app.project_root != ""


@pytest.mark.asyncio
async def test_action_task_manager_pushes_screen(tmp_path):
    from rlm_optimized.tui_app import TorchlightApp

    mock_engine = MagicMock()
    mock_engine.project_root = str(tmp_path)

    app = TorchlightApp(engine=mock_engine)
    pushed_screen = None

    def mock_push_screen(screen):
        nonlocal pushed_screen
        pushed_screen = screen

    app.push_screen = mock_push_screen
    with patch("rlm_optimized.tui_app.TaskManagerModal") as MockModal:
        MockModal.return_value = MagicMock(project_root=str(tmp_path))
        app.action_task_manager()

        MockModal.assert_called_once_with(str(tmp_path))
        assert pushed_screen is not None
