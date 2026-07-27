#!/usr/bin/env python3
import os
import sys
import urllib.request

MODEL_URL = "https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-Q4_K_M.gguf"
DEST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
DEST_FILE = os.path.join(DEST_DIR, "gemma-4-E2B-it-Q4_K_M.gguf")

def download_gemma(url=MODEL_URL, dest=DEST_FILE) -> str:
    os.makedirs(DEST_DIR, exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000_000:
        print(f"✅ Gemma 4 E2B GGUF Model found at: {dest}")
        return dest

    tmp_dest = dest + ".part"
    print(f"📥 Gemma 4 E2B GGUF model downloading from Hugging Face...")
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
    download_gemma()
