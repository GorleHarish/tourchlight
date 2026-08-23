"""
Image processing and multimodal serialization utilities for Torchlight.

Provides zero-dependency baseline image utilities with automatic Pillow downscaling
and token-optimized serialization for vision models (Gemma 3, Qwen VL, Llama Vision,
GPT-4o, Gemini, etc.).
"""

import base64
import datetime
import io
import mimetypes
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from PIL import Image

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
    ".svg",
    ".ico",
    ".tif",
    ".tiff",
    ".avif",
    ".heic",
    ".heif",
}


def is_image_file(path_or_name: Union[str, Path]) -> bool:
    """Check if the given path or filename has an image extension."""
    if not path_or_name:
        return False
    path_str = str(path_or_name).strip()
    # Strip URL fragments or query params if any
    if "?" in path_str:
        path_str = path_str.split("?")[0]
    if "#" in path_str:
        path_str = path_str.split("#")[0]
    ext = os.path.splitext(path_str)[1].lower()
    return ext in IMAGE_EXTENSIONS


def get_image_mime_type(
    path_or_bytes: Union[str, Path, bytes], default: str = "image/png"
) -> str:
    """Detect image MIME type from path, file header bytes, or magic bytes."""
    if isinstance(path_or_bytes, bytes):
        header = path_or_bytes[:16]
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if header.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            return "image/gif"
        if header.startswith(b"RIFF") and b"WEBP" in header:
            return "image/webp"
        if header.startswith(b"BM"):
            return "image/bmp"
        if b"<svg" in header.lower() or b"<?xml" in header.lower():
            return "image/svg+xml"
        return default

    path_str = str(path_or_bytes)
    # Check if data URI
    if path_str.startswith("data:image/"):
        match = re.match(r"^data:(image/[a-zA-Z0-9\-\+\.]+);", path_str)
        if match:
            return match.group(1)

    mime, _ = mimetypes.guess_type(path_str)
    if mime and mime.startswith("image/"):
        return mime

    ext = os.path.splitext(path_str)[1].lower()
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }
    return mapping.get(ext, default)


def get_image_metadata(
    path_or_bytes: Union[str, Path, bytes], project_root: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract image metadata (width, height, format, size in bytes, mime_type).
    Uses Pillow if available, otherwise estimates from file stats.
    """
    raw_bytes: bytes
    file_path: Optional[str] = None

    if isinstance(path_or_bytes, bytes):
        raw_bytes = path_or_bytes
    else:
        p = str(path_or_bytes)
        if p.startswith("data:image/"):
            # Extract base64 part
            if ";base64," in p:
                b64_str = p.split(";base64,")[1]
                raw_bytes = base64.b64decode(b64_str)
            else:
                raw_bytes = p.encode("utf-8")
        else:
            if project_root and not os.path.isabs(p):
                p = os.path.join(project_root, p)
            file_path = p
            if not os.path.exists(p):
                return {
                    "exists": False,
                    "error": f"Image file not found: {path_or_bytes}",
                }
            with open(p, "rb") as f:
                raw_bytes = f.read()

    size_bytes = len(raw_bytes)
    mime = get_image_mime_type(file_path or raw_bytes)

    width = 0
    height = 0
    fmt = mime.replace("image/", "").upper()

    if _HAS_PIL:
        try:
            with Image.open(io.BytesIO(raw_bytes)) as img:
                width, height = img.size
                fmt = (img.format or fmt).upper()
        except Exception:
            pass

    return {
        "exists": True,
        "path": file_path or "",
        "width": width,
        "height": height,
        "format": fmt,
        "mime_type": mime,
        "size_bytes": size_bytes,
        "size_kb": round(size_bytes / 1024.0, 1),
    }


def format_image_text_summary(
    path_or_bytes: Union[str, Path, bytes], project_root: Optional[str] = None
) -> str:
    """
    Format a rich textual summary of an attached image with exact tool calling schema contract.
    Used for text-only LLMs to inject processed image context directly into prompt.
    """
    meta = get_image_metadata(path_or_bytes, project_root=project_root)
    name = (
        Path(str(path_or_bytes)).name
        if not isinstance(path_or_bytes, bytes)
        else "image"
    )
    if not meta.get("exists", True):
        return (
            f"[Attached Image: {name} (Error: {meta.get('error', 'File not found')})]"
        )

    w = meta.get("width", 0)
    h = meta.get("height", 0)
    dim_str = f", Dimensions: {w}x{h}" if w > 0 and h > 0 else ""
    fmt = meta.get("format", "IMAGE")
    size_kb = meta.get("size_kb", 0)

    return (
        f"[Image Attached & Processed: {name} (Format: {fmt}{dim_str}, Size: {size_kb} KB | "
        f'To inspect details with a specific prompt, call VIEW_IMAGE with arguments: {{"path": "{name}"}})]'
    )


def encode_image_to_base64(
    path_or_bytes: Union[str, Path, bytes],
    max_dim: int = 1024,
    quality: int = 85,
    project_root: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Read, normalize/downscale if necessary, and encode image to (base64_str, mime_type).

    Downscaling:
    If Pillow is available and image max dimension exceeds max_dim,
    resizes the image proportionally to avoid context token overflow
    and excessive VRAM usage on local inference engines.
    """
    raw_bytes: bytes
    path_str = str(path_or_bytes) if not isinstance(path_or_bytes, bytes) else ""

    # Check if already a base64 data URL
    if path_str.startswith("data:image/"):
        if ";base64," in path_str:
            parts = path_str.split(";base64,")
            mime = parts[0].replace("data:", "")
            return parts[1], mime

    if isinstance(path_or_bytes, bytes):
        raw_bytes = path_or_bytes
    else:
        p = path_str
        if project_root and not os.path.isabs(p):
            p = os.path.join(project_root, p)
        if not os.path.exists(p):
            raise FileNotFoundError(f"Image not found at path: {p}")
        with open(p, "rb") as f:
            raw_bytes = f.read()

    mime = get_image_mime_type(path_str or raw_bytes)

    # Downscale large images if PIL is available
    if _HAS_PIL and mime not in ("image/svg+xml", "image/gif"):
        try:
            with Image.open(io.BytesIO(raw_bytes)) as img:
                # Handle EXIF orientation if needed
                w, h = img.size
                if max(w, h) > max_dim:
                    scale = max_dim / float(max(w, h))
                    new_w = max(1, int(w * scale))
                    new_h = max(1, int(h * scale))
                    resample = (
                        getattr(Image, "Resampling", Image).LANCZOS
                        if hasattr(Image, "Resampling")
                        else Image.LANCZOS
                    )
                    resized = img.resize((new_w, new_h), resample=resample)

                    buf = io.BytesIO()
                    if mime in ("image/jpeg", "image/jpg"):
                        if resized.mode != "RGB":
                            resized = resized.convert("RGB")
                        resized.save(buf, format="JPEG", quality=quality, optimize=True)
                    elif mime == "image/webp":
                        resized.save(buf, format="WEBP", quality=quality)
                    else:
                        # Default to PNG
                        resized.save(buf, format="PNG", optimize=True)
                    raw_bytes = buf.getvalue()
        except Exception:
            # Fall back to un-resized bytes if PIL resize encounters an issue
            pass

    b64 = base64.b64encode(raw_bytes).decode("ascii")
    return b64, mime


def build_image_data_url(
    path_or_bytes: Union[str, Path, bytes],
    max_dim: int = 1024,
    project_root: Optional[str] = None,
) -> str:
    """
    Construct a base64 Data URL (data:image/<mime>;base64,<data>)
    or return as-is if already an http(s) URL or data URL.
    """
    if isinstance(path_or_bytes, str):
        if path_or_bytes.startswith(("http://", "https://", "data:image/")):
            return path_or_bytes

    b64, mime = encode_image_to_base64(
        path_or_bytes, max_dim=max_dim, project_root=project_root
    )
    return f"data:{mime};base64,{b64}"


def format_openai_vision_content(
    text: str,
    images: List[Union[str, Path, bytes]],
    max_dim: int = 1024,
    project_root: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Build standard OpenAI / LM Studio / CloudClient multimodal content parts:
    [{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}]
    """
    parts: List[Dict[str, Any]] = []
    if text:
        parts.append({"type": "text", "text": text})

    for img in images:
        if not img:
            continue
        try:
            data_url = build_image_data_url(
                img, max_dim=max_dim, project_root=project_root
            )
            parts.append({"type": "image_url", "image_url": {"url": data_url}})
        except Exception as e:
            # If image encoding fails, append text notice so turn doesn't crash
            parts.append(
                {"type": "text", "text": f"[Attached Image: {img} (Error: {e})]"}
            )

    return parts


def format_ollama_vision_payload(
    text: str,
    images: List[Union[str, Path, bytes]],
    max_dim: int = 1024,
    project_root: Optional[str] = None,
) -> Tuple[str, List[str]]:
    """
    Build Ollama multimodal payload: (text_content, [raw_base64_string, ...]).
    """
    b64_list: List[str] = []
    for img in images:
        if not img:
            continue
        try:
            b64, _ = encode_image_to_base64(
                img, max_dim=max_dim, project_root=project_root
            )
            b64_list.append(b64)
        except Exception:
            continue
    return text, b64_list


def extract_image_paths_from_text(text: str) -> List[str]:
    """
    Scan user prompt for image file paths or markdown image tags:
    - Markdown: ![alt](path/to/image.png)
    - Slash command: /image path/to/image.png
    - Direct paths: src/assets/mockup.png, /tmp/screenshot.webp
    """
    if not text:
        return []

    found: List[str] = []

    # 1. Markdown image syntax: ![...](path)
    md_matches = re.findall(r"!\[.*?\]\((.+?)\)", text)
    for m in md_matches:
        clean = m.strip().strip("'\"")
        if is_image_file(clean):
            found.append(clean)

    # 2. Slash command /image <path>
    slash_matches = re.findall(r"^/image\s+([^\s]+)", text, re.MULTILINE)
    for m in slash_matches:
        clean = m.strip().strip("'\"")
        if clean and clean not in found:
            found.append(clean)

    # 3. Explicit path patterns ending in image extensions
    path_regex = r"(?:^|\s|['\"])([\w\-\./\\]+\.(?:png|jpg|jpeg|webp|gif|bmp|svg))(?:['\"]|\s|$)"
    for m in re.findall(path_regex, text, re.IGNORECASE):
        clean = m.strip().strip("'\"")
        if clean and clean not in found:
            found.append(clean)

    return found


def generate_ansi_image_preview(
    path_or_bytes: Union[str, Path, bytes],
    max_width: int = 44,
    max_height: int = 16,
    project_root: Optional[str] = None,
) -> Optional[object]:
    """
    Generate a Rich Text object containing a 24-bit ANSI half-block color preview of the image.
    Uses '▀' (upper half block) where foreground = top pixel, background = bottom pixel.
    """
    if not _HAS_PIL:
        return None
    try:
        from rich.text import Text
        from rich.style import Style

        p = str(path_or_bytes) if not isinstance(path_or_bytes, bytes) else ""
        if isinstance(path_or_bytes, bytes):
            with Image.open(io.BytesIO(path_or_bytes)) as raw_img:
                img = raw_img.copy()
        else:
            full_p = (
                os.path.join(project_root, p)
                if project_root and not os.path.isabs(p)
                else p
            )
            if not os.path.exists(full_p):
                return None
            with Image.open(full_p) as raw_img:
                img = raw_img.copy()

        # Handle alpha channel by compositing over dark terminal background
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (22, 27, 34))
            bg.paste(rgba, mask=rgba.split()[3])
            img = bg
        else:
            img = img.convert("RGB")

        w, h = img.size
        if w == 0 or h == 0:
            return None

        # Calculate target dimensions (height in pixels = 2 * character lines)
        target_w = max(1, min(max_width, w))
        target_h = max(2, int((h / max(1, w)) * target_w))
        if target_h > max_height * 2:
            target_h = max_height * 2
            target_w = max(1, int((w / max(1, h)) * target_h))

        if target_h % 2 != 0:
            target_h += 1

        resample = (
            getattr(Image, "Resampling", Image).BILINEAR
            if hasattr(Image, "Resampling")
            else Image.BILINEAR
        )
        img = img.resize((target_w, target_h), resample)
        pixels = img.load()

        text = Text()
        for y in range(0, target_h, 2):
            for x in range(target_w):
                r1, g1, b1 = pixels[x, y]
                r2, g2, b2 = pixels[x, y + 1] if y + 1 < target_h else (0, 0, 0)
                style = Style(
                    color=f"rgb({r1},{g1},{b1})", bgcolor=f"rgb({r2},{g2},{b2})"
                )
                text.append("▀", style=style)
            if y + 2 < target_h:
                text.append("\n")
        return text
    except Exception:
        return None


def save_clipboard_image(project_root: str = ".") -> Optional[str]:
    """
    Check system clipboard for image data or copied image file paths.
    If found, saves bitmap image to <project_root>/.torchlight/attachments/pasted_image_<timestamp>.png
    or returns existing copied image file path.
    Returns path to the image, or None.
    """
    # 1. Check Pillow ImageGrab
    if _HAS_PIL:
        try:
            from PIL import ImageGrab

            clip = ImageGrab.grabclipboard()
            if clip is not None:
                # Case A: PIL Image object (screenshot or copied image bitmap)
                if hasattr(clip, "save"):
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    target_dir = os.path.join(project_root, ".torchlight", "attachments")
                    os.makedirs(target_dir, exist_ok=True)
                    out_path = os.path.join(target_dir, f"pasted_image_{ts}.png")
                    clip.save(out_path, format="PNG")
                    return out_path

                # Case B: List of files copied from Finder/Explorer
                if isinstance(clip, (list, tuple)):
                    for item in clip:
                        item_str = str(item)
                        if is_image_file(item_str) and os.path.exists(item_str):
                            return item_str
        except Exception:
            pass

    # 2. Native macOS fallback via pngpaste
    if sys.platform == "darwin":
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            target_dir = os.path.join(project_root, ".torchlight", "attachments")
            out_path = os.path.join(target_dir, f"pasted_image_{ts}.png")
            os.makedirs(target_dir, exist_ok=True)
            p = subprocess.run(["pngpaste", out_path], capture_output=True, timeout=1)
            if p.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                return out_path
            elif os.path.exists(out_path) and os.path.getsize(out_path) == 0:
                os.remove(out_path)
        except Exception:
            pass

    # 3. Linux fallback via xclip / wl-paste
    if sys.platform.startswith("linux"):
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            target_dir = os.path.join(project_root, ".torchlight", "attachments")
            out_path = os.path.join(target_dir, f"pasted_image_{ts}.png")
            os.makedirs(target_dir, exist_ok=True)
            for cmd in [
                ["wl-paste", "-t", "image/png"],
                ["xclip", "-selection", "clipboard", "-target", "image/png", "-out"],
            ]:
                try:
                    with open(out_path, "wb") as f:
                        p = subprocess.run(
                            cmd, stdout=f, stderr=subprocess.DEVNULL, timeout=1
                        )
                    if (
                        p.returncode == 0
                        and os.path.exists(out_path)
                        and os.path.getsize(out_path) > 0
                    ):
                        return out_path
                    elif os.path.exists(out_path):
                        os.remove(out_path)
                except Exception:
                    pass
        except Exception:
            pass

    return None

