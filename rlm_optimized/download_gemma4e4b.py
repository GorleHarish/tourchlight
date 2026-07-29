#!/usr/bin/env python3
"""
Gemma 4 E4B (4E4B) Model Downloader for Torchlight.

Downloads the Gemma 4 E4B Instruct GGUF model from Hugging Face for
local inference via llama.cpp / TurboQuant on Apple Silicon & local setups.
"""

import os
import sys
import ssl
import subprocess
import urllib.request

# Bypass SSL certificate verification issues on macOS python installations
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

MODEL_URL = "https://huggingface.co/unsloth/gemma-4-E4B-it-GGUF/resolve/main/gemma-4-E4B-it-Q4_K_M.gguf"
DEST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
DEST_FILE = os.path.join(DEST_DIR, "gemma-4-E4B-it-Q4_K_M.gguf")


def download_gemma4e4b(url: str = MODEL_URL, dest: str = DEST_FILE) -> str:
    os.makedirs(DEST_DIR, exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000_000:
        print(f"✅ Gemma 4 E4B GGUF Model found at: {dest}")
        return dest

    tmp_dest = dest + ".part"
    print("📥 Gemma 4 E4B GGUF model downloading from Hugging Face...")
    print(f"   URL: {url}")
    print(f"   Destination: {dest}\n")

    # Try curl first (resilient against macOS urllib SSL certificate errors)
    try:
        res = subprocess.run(["curl", "-L", "-C", "-", "-#", "-o", tmp_dest, url], check=False)
        if res.returncode == 0 and os.path.exists(tmp_dest) and os.path.getsize(tmp_dest) > 1_000_000_000:
            os.rename(tmp_dest, dest)
            print(f"\n✅ Download completed successfully! Model saved to:\n   {dest}\n")
            return dest
    except Exception as e:
        print(f"ℹ️ curl attempt deferred: {e}")

    # Fallback to urllib
    try:
        def _progress(count, block_size, total_size):
            if total_size > 0:
                percent = min(100, int(count * block_size * 100 / total_size))
                mb = (count * block_size) / (1024 * 1024)
                sys.stdout.write(f"\r  Downloading: {percent}% ({mb:.1f} MB)")
                sys.stdout.flush()

        ctx = ssl._create_unverified_context() if hasattr(ssl, "_create_unverified_context") else None
        req = urllib.request.urlopen(url, context=ctx) if ctx else urllib.request.urlopen(url)
        with open(tmp_dest, "wb") as out_file:
            total_size = int(req.headers.get("Content-Length", 0))
            count = 0
            block_size = 8192
            while True:
                chunk = req.read(block_size)
                if not chunk:
                    break
                out_file.write(chunk)
                count += 1
                _progress(count, block_size, total_size)

        os.rename(tmp_dest, dest)
        print(f"\n\n✅ Download completed successfully! Model saved to:\n   {dest}\n")
        return dest
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        if os.path.exists(tmp_dest):
            os.remove(tmp_dest)
        sys.exit(1)


if __name__ == "__main__":
    download_gemma4e4b()
