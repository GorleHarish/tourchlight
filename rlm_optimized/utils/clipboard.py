"""Cross-platform clipboard utilities for Torchlight."""

from __future__ import annotations

import subprocess
import sys


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard across macOS, Linux, and Windows."""
    if not text:
        return False
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception:
        pass

    if sys.platform == "darwin":
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
            return True
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        for cmd in [["xclip", "-selection", "clipboard"], ["wl-copy"], ["xsel", "-b"]]:
            try:
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                p.communicate(text.encode("utf-8"))
                return True
            except Exception:
                pass
    elif sys.platform == "win32":
        try:
            p = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-16le"))
            return True
        except Exception:
            pass
    return False
