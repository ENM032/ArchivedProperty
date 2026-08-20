"""
Cross-platform clipboard reader with zero hard external dependencies.
Supports Windows (ctypes Win32 API), Tkinter, macOS (pbpaste), and Linux (xclip/wl-paste).
"""

import logging
import subprocess
import sys

logger = logging.getLogger(__name__)


def get_clipboard_text() -> str | None:
    """Read text content from the system clipboard."""
    # 1. Windows Native Win32 API (Fast, no dependencies)
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            if user32.OpenClipboard(0):
                try:
                    if user32.IsClipboardFormatAvailable(13):  # CF_UNICODETEXT
                        handle = user32.GetClipboardData(13)
                        data = kernel32.GlobalLock(handle)
                        try:
                            text = ctypes.c_wchar_p(data).value
                            if text:
                                return text.strip()
                        finally:
                            kernel32.GlobalUnlock(handle)
                finally:
                    user32.CloseClipboard()
        except Exception as exc:
            logger.debug("Win32 clipboard read failed: %s", exc)

    # 2. Tkinter standard library fallback (Cross-platform)
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
        if text and isinstance(text, str):
            return text.strip()
    except Exception as exc:
        logger.debug("Tkinter clipboard read failed: %s", exc)

    # 3. macOS / Linux Subprocess fallbacks
    if sys.platform == "darwin":
        try:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        for cmd in (["xclip", "-selection", "clipboard", "-o"], ["wl-paste"]):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except Exception:
                continue

    return None
