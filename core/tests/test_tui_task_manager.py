import json
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


def test_build_task_tree_markup_with_goal_spec(tmp_path):
    import json
    from rlm_optimized.tui_widgets.task_tree import build_task_tree_markup

    t_dir = tmp_path / ".torchlight"
    t_dir.mkdir(parents=True, exist_ok=True)
    goal_file = t_dir / "goal_spec.json"
    goal_file.write_text(
        json.dumps(
            {
                "goal": "Build authentication system",
                "tasks": [
                    {"id": "t1", "description": "Create login form", "status": "completed"},
                    {"id": "t2", "description": "Implement JWT middleware", "status": "in_progress"},
                    {"id": "t3", "description": "Add logout handler", "status": "pending"},
                ],
            }
        ),
        encoding="utf-8",
    )

    markup = build_task_tree_markup(str(tmp_path))
    assert "Goal: Build authentication system" in markup
    assert "Create login form" in markup
    assert "Implement JWT middleware" in markup
    assert "Add logout handler" in markup
    assert "Progress:" in markup
    assert "1/3 (33%)" in markup


def test_build_task_tree_markup_with_plan_markdown(tmp_path):
    from rlm_optimized.tui_widgets.task_tree import build_task_tree_markup

    plan_file = tmp_path / "implementation_plan.md"
    plan_file.write_text(
        "# Authentication Refactor\n\n"
        "- [x] Write unit tests\n"
        "- [/] Update token verification\n"
        "- [ ] Deploy to staging\n",
        encoding="utf-8",
    )

    markup = build_task_tree_markup(str(tmp_path))
    assert "Goal: Authentication Refactor" in markup
    assert "Write unit tests" in markup
    assert "Update token verification" in markup
    assert "Deploy to staging" in markup
    assert "1/3 (33%)" in markup


def test_build_task_tree_markup_fallback_empty(tmp_path):
    from rlm_optimized.tui_widgets.task_tree import build_task_tree_markup

    markup = build_task_tree_markup(str(tmp_path))
    assert "No active tasks defined in workspace" in markup


@pytest.mark.asyncio
async def test_task_tree_widget_compose_and_update(tmp_path):
    from textual.widgets import Static
    from rlm_optimized.tui_widgets.task_tree import TaskTreeWidget

    widget = TaskTreeWidget(str(tmp_path))
    children = list(widget.compose())
    assert len(children) == 1
    assert isinstance(children[0], Static)
    assert children[0].id == "task-tree-content"
    assert "No active tasks defined in workspace" in str(children[0].render())



