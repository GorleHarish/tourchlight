"""Unit and integration tests for multimodal vision capabilities (Gemma 3, Qwen VL, Llama Vision, etc.)."""

import base64
import os
import tempfile
import pytest
from pathlib import Path

from core.api.base import detect_model_traits
from core.memory.models import Message
from core.memory.manager import TieredMemory, MemoryConfig
from core.memory.token_counter import TokenCounter
from core.tools.schemas import TOOL_SCHEMAS, get_schemas_for_phase
from core.tools.classification import AUTO, classify_tool
from core.tools.implementations import tool_view_image_impl, tool_read_file_impl
from core.tools.registry import get_tool_registry
from core.utils.image_utils import (
    is_image_file,
    get_image_mime_type,
    get_image_metadata,
    encode_image_to_base64,
    format_openai_vision_content,
    format_ollama_vision_payload,
    extract_image_paths_from_text,
)


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """Create a minimal 1x1 valid PNG image."""
    # Minimal 1x1 transparent PNG bytes
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    )
    img_file = tmp_path / "test_image.png"
    img_file.write_bytes(png_bytes)
    return img_file


def test_is_image_file():
    assert is_image_file("diagram.png") is True
    assert is_image_file("photo.JPG") is True
    assert is_image_file("anim.webp") is True
    assert is_image_file("vector.svg") is True
    assert is_image_file("icon.ico") is True
    assert is_image_file("main.py") is False
    assert is_image_file("README.md") is False


def test_get_image_mime_type():
    assert get_image_mime_type("img.png") == "image/png"
    assert get_image_mime_type("img.jpeg") == "image/jpeg"
    assert get_image_mime_type("img.jpg") == "image/jpeg"
    assert get_image_mime_type("img.webp") == "image/webp"
    assert get_image_mime_type("img.svg") == "image/svg+xml"


def test_get_image_metadata(sample_image: Path):
    meta = get_image_metadata(sample_image)
    assert meta["format"] in ("PNG", "IMAGE")
    assert meta["width"] >= 1
    assert meta["height"] >= 1
    assert meta["mime_type"] == "image/png"
    assert meta["size_bytes"] > 0


def test_encode_image_to_base64(sample_image: Path):
    b64_str, mime = encode_image_to_base64(sample_image)
    assert b64_str is not None
    assert len(b64_str) > 0
    assert mime == "image/png"
    # Should decode back to valid bytes
    decoded = base64.b64decode(b64_str)
    assert len(decoded) > 0


def test_format_openai_vision_content(sample_image: Path):
    parts = format_openai_vision_content(
        "Explain this screenshot", [str(sample_image)]
    )
    assert isinstance(parts, list)
    assert len(parts) == 2
    assert parts[0] == {"type": "text", "text": "Explain this screenshot"}
    assert parts[1]["type"] == "image_url"
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_format_ollama_vision_payload(sample_image: Path):
    text, b64_images = format_ollama_vision_payload(
        "Explain this diagram", [str(sample_image)]
    )
    assert text == "Explain this diagram"
    assert len(b64_images) == 1
    assert isinstance(b64_images[0], str)


def test_extract_image_paths_from_text(tmp_path: Path):
    img1 = tmp_path / "mockup.png"
    img1.touch()
    img2 = tmp_path / "chart.jpg"
    img2.touch()

    text = f"Please review {img1} and compare with {img2} for styling."
    found = extract_image_paths_from_text(text)
    assert str(img1) in found
    assert str(img2) in found


def test_detect_model_traits_vision():
    # Gemma 3 models
    assert detect_model_traits("gemma-3-12b-it")["is_vision"] is True
    assert detect_model_traits("gemma-3-4b-it")["is_vision"] is True
    assert detect_model_traits("gemma3-27b")["is_vision"] is True

    # Qwen VL
    assert detect_model_traits("qwen2.5-vl-7b-instruct")["is_vision"] is True
    assert detect_model_traits("qwen-vl-max")["is_vision"] is True

    # Llama 3.2 Vision
    assert detect_model_traits("llama-3.2-11b-vision-instruct")["is_vision"] is True

    # Cloud vision models
    assert detect_model_traits("gpt-4o")["is_vision"] is True
    assert detect_model_traits("claude-3-5-sonnet-20241022")["is_vision"] is True
    assert detect_model_traits("gemini-2.0-flash")["is_vision"] is True

    # Pure text models
    assert detect_model_traits("qwen2.5-coder-7b-instruct")["is_vision"] is False
    assert detect_model_traits("llama-3.1-8b-instruct")["is_vision"] is False


def test_message_to_dict_openai_and_ollama(sample_image: Path):
    # Text only
    msg_text = Message(role="user", content="Hello Torchlight")
    assert msg_text.to_dict(format="openai") == {"role": "user", "content": "Hello Torchlight"}
    assert msg_text.to_dict(format="ollama") == {"role": "user", "content": "Hello Torchlight"}

    # Multimodal with image
    msg_img = Message(role="user", content="Inspect this UI", images=[str(sample_image)])
    
    dict_openai = msg_img.to_dict(format="openai")
    assert dict_openai["role"] == "user"
    assert isinstance(dict_openai["content"], list)
    assert dict_openai["content"][0]["type"] == "text"
    assert dict_openai["content"][1]["type"] == "image_url"

    dict_ollama = msg_img.to_dict(format="ollama")
    assert dict_ollama["role"] == "user"
    assert dict_ollama["content"] == "Inspect this UI"
    assert "images" in dict_ollama
    assert len(dict_ollama["images"]) == 1


def test_token_counter_with_images():
    tc = TokenCounter()
    img_tokens = tc.count_image()
    assert img_tokens == 640

    msg = Message(role="user", content="Describe", images=["dummy.png"])
    tokens = tc.count_message(msg)
    assert tokens >= 641  # text tokens + 640 image tokens


def test_tiered_memory_add_user_message_with_images(sample_image: Path):
    config = MemoryConfig(max_tokens=12288)
    mem = TieredMemory(config=config)
    mem.add_system_message("System prompt")
    mem.add_user_message("Check this UI design", images=[str(sample_image)])

    ctx_openai = mem.get_context_for_llm(format="openai")
    assert len(ctx_openai) >= 2
    user_msg = ctx_openai[1]
    assert user_msg["role"] == "user"
    assert isinstance(user_msg["content"], list)

    ctx_ollama = mem.get_context_for_llm(format="ollama")
    user_msg_ollama = ctx_ollama[1]
    assert user_msg_ollama["role"] == "user"
    assert user_msg_ollama["content"] == "Check this UI design"
    assert "images" in user_msg_ollama


def test_view_image_tool_impl(sample_image: Path, tmp_path: Path):
    res = tool_view_image_impl({"path": sample_image.name}, project_root=str(tmp_path))
    assert "[IMG] [VIEW_IMAGE]" in res
    assert sample_image.name in res
    assert "attached to context" in res.lower()


def test_read_file_image_redirection(sample_image: Path, tmp_path: Path):
    res = tool_read_file_impl({"path": sample_image.name}, project_root=str(tmp_path))
    assert "VIEW_IMAGE" in res
    assert "binary image file" in res


def test_tool_registry_and_schemas_view_image():
    assert "VIEW_IMAGE" in TOOL_SCHEMAS
    assert classify_tool("VIEW_IMAGE") == AUTO

    reg = get_tool_registry()
    view_img_def = reg.get("VIEW_IMAGE")
    assert view_img_def is not None
    assert view_img_def.risk_level == AUTO

    schemas = get_schemas_for_phase("code")
    assert "VIEW_IMAGE" in schemas


def test_generate_ansi_image_preview(sample_image: Path):
    from core.utils.image_utils import generate_ansi_image_preview

    preview = generate_ansi_image_preview(sample_image, max_width=10, max_height=5)
    assert preview is not None
    assert len(preview.plain) > 0


def test_search_ast_and_symbols_image_and_at_handling(sample_image: Path, tmp_path: Path):
    from core.tools.implementations import tool_search_ast_impl, tool_read_symbols_impl, tool_read_file_impl

    # Create dummy js file
    js_file = tmp_path / "game.js"
    js_file.write_text("function updateScore() { return 100; }\nfunction resetGame() { return 0; }")

    # SEARCH_AST with image file
    ast_img_res = tool_search_ast_impl({"query": sample_image.name}, project_root=str(tmp_path))
    assert "image file" in ast_img_res.lower()

    # SEARCH_AST with @image file
    ast_at_img_res = tool_search_ast_impl({"query": f"@{sample_image.name}"}, project_root=str(tmp_path))
    assert "image file" in ast_at_img_res.lower()

    # SEARCH_AST with @code file
    ast_js_res = tool_search_ast_impl({"query": "@game.js"}, project_root=str(tmp_path))
    assert "updateScore" in ast_js_res or "game.js" in ast_js_res

    # READ_SYMBOLS with image
    sym_img_res = tool_read_symbols_impl({"path": sample_image.name}, project_root=str(tmp_path))
    assert "image file" in sym_img_res.lower()

    # READ_SYMBOLS with @code file
    sym_js_res = tool_read_symbols_impl({"path": "@game.js"}, project_root=str(tmp_path))
    assert "updateScore" in sym_js_res

    # READ_FILE with @code file
    read_js_res = tool_read_file_impl({"path": "@game.js"}, project_root=str(tmp_path))
    assert "updateScore" in read_js_res


def test_message_to_dict_text_only_fallback(sample_image: Path):
    """Verify Message.to_dict generates rich text description when vision_supported is False."""
    msg = Message(
        role="user",
        content="What is this screenshot?",
        images=[str(sample_image)],
    )

    # When vision is supported -> OpenAI image_url dicts
    dict_vision = msg.to_dict(format="openai", vision_supported=True)
    assert isinstance(dict_vision["content"], list)
    assert any(part.get("type") == "image_url" for part in dict_vision["content"])

    # When vision is NOT supported -> pure text with attached image notice
    dict_text = msg.to_dict(format="openai", vision_supported=False)
    assert isinstance(dict_text["content"], str)
    assert "What is this screenshot?" in dict_text["content"]
    assert "[Image Attached & Processed:" in dict_text["content"]
    assert sample_image.name in dict_text["content"]
    assert 'call VIEW_IMAGE with arguments: {"path":' in dict_text["content"]


def test_format_image_text_summary(sample_image: Path):
    """Verify format_image_text_summary extracts metadata and embeds exact calling contract."""
    from core.utils.image_utils import format_image_text_summary

    summary = format_image_text_summary(sample_image)
    assert "[Image Attached & Processed:" in summary
    assert sample_image.name in summary
    assert "Format: PNG" in summary
    assert 'call VIEW_IMAGE with arguments: {"path":' in summary


def test_validate_tool_call_view_image_auto_healing():
    """Verify validate_tool_call auto-heals missing/misplaced path arguments for VIEW_IMAGE."""
    from core.tools.schemas import validate_tool_call

    # 1. Direct string argument
    valid, msg, args = validate_tool_call("VIEW_IMAGE", "screenshot.png")
    assert valid is True
    assert args["path"] == "screenshot.png"

    # 2. Key alias: 'image'
    valid, msg, args = validate_tool_call("VIEW_IMAGE", {"image": "assets/mockup.png"})
    assert valid is True
    assert args["path"] == "assets/mockup.png"

    # 3. Path misplaced inside 'prompt'
    valid, msg, args = validate_tool_call(
        "VIEW_IMAGE", {"prompt": "inspect UI at mockup.png"}
    )
    assert valid is True
    assert args["path"] == "inspect UI at mockup.png"

    # 4. Standard path parameter
    valid, msg, args = validate_tool_call(
        "VIEW_IMAGE", {"path": "diagram.svg", "prompt": "Check node labels"}
    )
    assert valid is True
    assert args["path"] == "diagram.svg"
    assert args["prompt"] == "Check node labels"


def test_llamacpp_client_multimodal_image_stripping():
    """Verify _strip_multimodal_images flattens image_url blocks into text."""
    from rlm_optimized.llamacpp_client import _strip_multimodal_images

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this game."},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
            ],
        },
        {"role": "user", "content": "hi"},
    ]

    stripped = _strip_multimodal_images(messages)
    assert len(stripped) == 2
    assert isinstance(stripped[0]["content"], str)
    assert "Describe this game." in stripped[0]["content"]
    assert "[Attached Image:" in stripped[0]["content"]
    assert stripped[1]["content"] == "hi"


def test_tiered_memory_active_images_tracking(sample_image: Path, tmp_path: Path):
    """Verify TieredMemory records relative active image paths and surfaces them in L0 scratchpad."""
    memory = TieredMemory(
        config=MemoryConfig(max_tokens=4000),
    )

    memory.add_user_message(
        "Look at this screenshot",
        images=[str(sample_image)],
        project_root=str(tmp_path),
    )

    # Relative path stored in session state
    assert sample_image.name in memory.state.active_images

    # Surfaces in L0 Working Memory Scratchpad
    scratchpad = memory.format_l0_scratchpad(project_root=str(tmp_path))
    assert "- Active Images:" in scratchpad
    assert sample_image.name in scratchpad
    assert "PNG" in scratchpad

