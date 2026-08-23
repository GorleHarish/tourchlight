"""
Tests for TUI ImageViewer, BinaryFileViewer, and ImageAttachmentCard.

Verifies:
1. Image files (.png, .jpg, .svg, etc.) render structured metadata and ANSI preview instead of gibberish.
2. Binary files (.bin, null-byte payloads) render BinaryFileViewer with system open and copy actions.
3. ImageAttachmentCard interactive header buttons (system open, editor tab, copy path) work as expected.
4. open_file_tab in TorchlightApp mounts ImageViewer without text decode errors.
"""

import os
import tempfile
from unittest.mock import MagicMock

import pytest
from PIL import Image


@pytest.fixture
def sample_image_file():
    """Create a temporary PNG image file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    # Create simple 64x64 RGBA image
    img = Image.new("RGBA", (64, 64), color=(255, 0, 0, 255))
    img.save(path, format="PNG")
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def sample_svg_file():
    """Create a temporary SVG file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w") as f:
        f.write('<svg width="100" height="100"><circle cx="50" cy="50" r="40" fill="green" /></svg>')
        path = f.name
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def sample_binary_file():
    """Create a temporary non-image binary file containing null bytes."""
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False, mode="wb") as f:
        f.write(b"\x00\x01\x02\x03\x04\xff\xfe\x00BinaryBlobData")
        path = f.name
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.mark.anyio
async def test_image_viewer_composes(sample_image_file):
    try:
        from textual.app import App
        from rlm_optimized.tui_widgets.image_viewer import ImageViewer
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class IVApp(App):
        def compose(self):
            yield ImageViewer(image_path=sample_image_file)

    app = IVApp()
    async with app.run_test() as pilot:
        iv = app.query_one(ImageViewer)
        assert iv is not None
        assert iv._image_path == sample_image_file
        # Check that header and preview are mounted
        assert len(app.query(".image-viewer-title")) == 1
        assert len(app.query(".image-viewer-actions")) == 1
        await pilot.pause()


@pytest.mark.anyio
async def test_svg_viewer_and_toggle(sample_svg_file):
    try:
        from textual.app import App
        from textual.widgets import Button
        from rlm_optimized.tui_widgets.image_viewer import ImageViewer
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class SVGApp(App):
        def compose(self):
            yield ImageViewer(image_path=sample_svg_file)

    app = SVGApp()
    async with app.run_test() as pilot:
        iv = app.query_one(ImageViewer)
        assert iv is not None
        # Click toggle XML
        btn = app.query_one("#iv-btn-toggle-svg", Button)
        assert btn is not None
        btn.press()
        await pilot.pause()
        assert iv._show_svg is True


@pytest.mark.anyio
async def test_binary_file_viewer_composes(sample_binary_file):
    try:
        from textual.app import App
        from rlm_optimized.tui_widgets.image_viewer import BinaryFileViewer
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    class BinApp(App):
        def compose(self):
            yield BinaryFileViewer(file_path=sample_binary_file)

    app = BinApp()
    async with app.run_test() as pilot:
        bv = app.query_one(BinaryFileViewer)
        assert bv is not None
        assert len(app.query(".binary-viewer-title")) == 1
        await pilot.pause()


@pytest.mark.anyio
async def test_app_open_file_tab_with_image(sample_image_file):
    try:
        from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
        from rlm_optimized.tui_app import TorchlightApp
        from rlm_optimized.tui_widgets.image_viewer import ImageViewer
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    engine = MagicMock(spec=RLMEngineOptimized)
    engine.project_root = os.path.dirname(sample_image_file)
    engine._total_llm_calls = 0
    engine.max_depth = 10

    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    async with app.run_test():
        app.open_file_tab(sample_image_file)
        # Verify active tab is registered
        assert sample_image_file in app._open_tabs
        assert app._active_tab_path == sample_image_file
        # Verify ImageViewer is mounted instead of plain text / Static gibberish
        content_area = app.query_one("#editor-content-area")
        ivs = content_area.query(ImageViewer)
        assert len(ivs) == 1
        assert ivs[0]._image_path == sample_image_file


@pytest.mark.anyio
async def test_app_open_file_tab_with_binary(sample_binary_file):
    try:
        from rlm_optimized.rlm_engine_optimized import RLMEngineOptimized
        from rlm_optimized.tui_app import TorchlightApp
        from rlm_optimized.tui_widgets.image_viewer import BinaryFileViewer
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    engine = MagicMock(spec=RLMEngineOptimized)
    engine.project_root = os.path.dirname(sample_binary_file)
    engine._total_llm_calls = 0
    engine.max_depth = 10

    app = TorchlightApp(engine=engine, model_name="test", provider_name="llama-cpp")
    async with app.run_test():
        app.open_file_tab(sample_binary_file)
        assert sample_binary_file in app._open_tabs
        # Verify BinaryFileViewer is mounted
        content_area = app.query_one("#editor-content-area")
        bvs = content_area.query(BinaryFileViewer)
        assert len(bvs) == 1


@pytest.mark.anyio
async def test_image_attachment_card_actions(sample_image_file, monkeypatch):
    try:
        from textual.app import App
        from rlm_optimized.tui_widgets.transcript import ImageAttachmentCard
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    copied = []

    def mock_copy(text: str) -> bool:
        copied.append(text)
        return True

    monkeypatch.setattr("rlm_optimized.tui_app.copy_to_clipboard", mock_copy)

    opened = []

    def mock_open_system(file_p: str):
        opened.append(file_p)
        return True

    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: MagicMock())

    class CardApp(App):
        def compose(self):
            yield ImageAttachmentCard(image_path=sample_image_file)

    app = CardApp()
    async with app.run_test() as pilot:
        card = app.query_one(ImageAttachmentCard)
        assert card is not None

        # Test copy action
        card.action_copy_path()
        assert sample_image_file in copied

        # Test system open action
        card.action_open_system()

        await pilot.pause()


def test_save_clipboard_image_pil_object(monkeypatch, tmp_path):
    """Test save_clipboard_image when PIL ImageGrab returns a PIL Image."""
    from PIL import Image as PILImage
    from core.utils.image_utils import save_clipboard_image

    mock_img = PILImage.new("RGBA", (32, 32), color=(0, 255, 0, 255))
    monkeypatch.setattr("PIL.ImageGrab.grabclipboard", lambda: mock_img)

    saved_path = save_clipboard_image(str(tmp_path))
    assert saved_path is not None
    assert os.path.exists(saved_path)
    assert saved_path.endswith(".png")
    assert ".torchlight/attachments" in saved_path


def test_save_clipboard_image_file_list(monkeypatch, sample_image_file, tmp_path):
    """Test save_clipboard_image when PIL ImageGrab returns list of copied file paths."""
    from core.utils.image_utils import save_clipboard_image

    monkeypatch.setattr("PIL.ImageGrab.grabclipboard", lambda: [sample_image_file])
    result = save_clipboard_image(str(tmp_path))
    assert result == sample_image_file


def test_save_clipboard_image_none(monkeypatch, tmp_path):
    """Test save_clipboard_image when clipboard is empty / contains no image."""
    from core.utils.image_utils import save_clipboard_image

    monkeypatch.setattr("PIL.ImageGrab.grabclipboard", lambda: None)
    result = save_clipboard_image(str(tmp_path))
    assert result is None


@pytest.mark.anyio
async def test_prompt_text_area_paste_image(sample_image_file, tmp_path, monkeypatch):
    """Test PromptTextArea pasting image path or clipboard image emits ContextFileAttached."""
    try:
        from textual.app import App
        from textual.events import Paste
        from rlm_optimized.tui_widgets.command_palette import PromptTextArea
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Textual not installed in test environment: {e}")

    attached_files = []

    class PasteTestApp(App):
        project_root = str(tmp_path)

        def compose(self):
            yield PromptTextArea(id="test-input")

        def on_prompt_text_area_context_file_attached(
            self, event: PromptTextArea.ContextFileAttached
        ):
            attached_files.append(event.filepath)

    app = PasteTestApp()
    async with app.run_test() as pilot:
        inp = app.query_one("#test-input", PromptTextArea)
        assert inp is not None

        # 1. Paste image path as text
        paste_event = Paste(sample_image_file)
        inp.on_paste(paste_event)
        await pilot.pause()
        assert sample_image_file in attached_files

        # 2. Paste via ctrl+v with clipboard image
        from PIL import Image as PILImage
        mock_img = PILImage.new("RGBA", (16, 16), color=(255, 0, 0, 255))
        monkeypatch.setattr("PIL.ImageGrab.grabclipboard", lambda: mock_img)

        await pilot.press("ctrl+v")
        await pilot.pause()
        assert len(attached_files) >= 2

