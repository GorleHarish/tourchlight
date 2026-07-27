#!/usr/bin/env python3
"""
Qwen 2.5 Coder Model Downloader for Torchlight.

Downloads the Qwen 2.5 Coder Instruct GGUF model from Hugging Face for
local inference via llama.cpp / TurboQuant on Apple Silicon & local setups.
"""

import os
import sys
import urllib.request

MODEL_URL = "https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
DEST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
DEST_FILE = os.path.join(DEST_DIR, "qwen2.5-coder-7b-instruct-q4_k_m.gguf")

def download_qwen(url=MODEL_URL, dest=DEST_FILE) -> str:
    os.makedirs(DEST_DIR, exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000_000:
        print(f"✅ Qwen 2.5 Coder GGUF Model found at: {dest}")
        return dest

    tmp_dest = dest + ".part"
    print(f"📥 Qwen 2.5 Coder GGUF model downloading from Hugging Face...")
    print(f"   URL: {url}")
    print(f"   Destination: {dest}\n")

    try:
        def _progress(count, block_size, total_size):
            if total_size > 0:
                percent = min(100, int(count * block_size * 100 / total_size))
                mb = (count * block_size) / (1024 * 1024)
                sys.stdout.write(f"\r  Downloading: {percent}% ({mb:.1f} MB)")
                sys.stdout.flush()

        urllib.request.urlretrieve(url, tmp_dest, _progress)
        os.rename(tmp_dest, dest)
        print(f"\n\n✅ Download completed successfully! Model saved to:\n   {dest}\n")
        return dest
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        if os.path.exists(tmp_dest):
            os.remove(tmp_dest)
        sys.exit(1)

if __name__ == "__main__":
    download_qwen()
