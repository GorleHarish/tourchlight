#!/usr/bin/env python3
"""
Qwen 2.5 Coder 7B Instruct (MLX 4-bit) Model Downloader for Torchlight.

Downloads the MLX-quantized Qwen 2.5 Coder 7B Instruct weights for local
inference via mlx_lm.server on Apple Silicon (Metal GPU).

Unlike the GGUF downloaders in this directory, an MLX model is a multi-file
Hugging Face repo (config + safetensors + tokenizer), so it is fetched with
snapshot_download rather than a single urlretrieve.

The destination matches the path start_mlx_server.sh already probes
(`$PROJECT_ROOT/models/<repo basename>`), so the server resolves it with no
extra configuration.
"""

import os
import sys

REPO_ID = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
DEST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
DEST_PATH = os.path.join(DEST_DIR, REPO_ID.split("/")[-1])

# Files mlx_lm.server needs before it will load a directory.
_REQUIRED = ("config.json", "tokenizer_config.json")
_MIN_WEIGHT_BYTES = 3_500_000_000  # 4-bit 7B is ~4.28 GB


def _weights_bytes(path: str) -> int:
    if not os.path.isdir(path):
        return 0
    return sum(
        os.path.getsize(os.path.join(path, f))
        for f in os.listdir(path)
        if f.endswith(".safetensors")
    )


def is_complete(path: str = DEST_PATH) -> bool:
    """True when the directory holds a loadable MLX model."""
    return all(
        os.path.exists(os.path.join(path, f)) for f in _REQUIRED
    ) and _weights_bytes(path) >= _MIN_WEIGHT_BYTES


def download_qwen7b_mlx(repo_id: str = REPO_ID, dest: str = DEST_PATH) -> str:
    if is_complete(dest):
        print(f"✅ Qwen 2.5 Coder 7B MLX model found at: {dest}")
        return dest

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print(
            "❌ huggingface_hub is required for MLX downloads.\n"
            "   Install with: pip install huggingface_hub"
        )
        sys.exit(1)

    os.makedirs(DEST_DIR, exist_ok=True)
    print(f"📥 Downloading {repo_id} (~4.3 GB) ...")
    print(f"   Destination: {dest}\n")

    try:
        path = snapshot_download(repo_id=repo_id, local_dir=dest, max_workers=4)
    except Exception as e:
        # Leave whatever was fetched in place; snapshot_download resumes.
        print(f"\n❌ Download failed: {e}")
        print("   Re-run this script to resume from where it stopped.")
        sys.exit(1)

    if not is_complete(path):
        print(f"\n❌ Download finished but {path} is incomplete. Re-run to resume.")
        sys.exit(1)

    print(f"\n✅ Download complete: {path}")
    print(f"   Serve it with: ./rlm_optimized/start_mlx_server.sh {DEST_PATH}")
    return path


if __name__ == "__main__":
    download_qwen7b_mlx()
