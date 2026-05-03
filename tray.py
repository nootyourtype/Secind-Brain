"""
tray.py - System Tray Icon (Phase 2D)
Runs a pystray icon in the Windows taskbar with a right-click context menu.
Gives the user control over the Second Brain without needing the terminal.
"""
import sys, io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
import threading
import subprocess
from PIL import Image, ImageDraw, ImageFont

from ingest import NOTES_DIR


# ── Icon Generation ────────────────────────────────────────────────────────────

def _make_icon_image(size: int = 64) -> Image.Image:
    """
    Programmatically generate a clean tray icon:
    dark background + cyan 'SB' (Second Brain) text.
    No external image file needed.
    """
    img  = Image.new("RGBA", (size, size), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle
    pad = 2
    draw.ellipse([pad, pad, size-pad, size-pad], fill=(13, 17, 23))

    # Glowing border ring
    draw.ellipse([pad, pad, size-pad, size-pad], outline=(99, 202, 255), width=2)

    # "SB" text centered
    try:
        font = ImageFont.truetype("arial.ttf", size=size // 3)
    except Exception:
        font = ImageFont.load_default()

    text = "SB"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw   = bbox[2] - bbox[0]
    th   = bbox[3] - bbox[1]
    tx   = (size - tw) // 2
    ty   = (size - th) // 2

    draw.text((tx, ty), text, fill=(99, 202, 255), font=font)
    return img


# ── Shared State passed in from main ──────────────────────────────────────────

class TrayState:
    chunk_count:    int = 0
    last_reindex:   str = "never"
    last_query:     str = "none"
    ollama_model:   str = "unavailable"
    exit_callback          = None
    reindex_callback       = None


_state = TrayState()


# ── Menu Logic ─────────────────────────────────────────────────────────────────

def _open_notes_folder(icon, item):
    subprocess.Popen(f'explorer "{NOTES_DIR}"')


def _trigger_reindex(icon, item):
    if _state.reindex_callback:
        t = threading.Thread(target=_state.reindex_callback, daemon=True)
        t.start()


def _on_exit(icon, item):
    icon.stop()
    if _state.exit_callback:
        _state.exit_callback()


def _status_title(icon=None, item=None):
    return f"Chunks: {_state.chunk_count} | Model: {_state.ollama_model}"


def _last_query_title(icon=None, item=None):
    q = _state.last_query
    return f"Last: {q[:40]}..." if len(q) > 40 else f"Last: {q}"


def _build_menu():
    import pystray
    return pystray.Menu(
        pystray.MenuItem("Second Brain", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_status_title,    None, enabled=False),
        pystray.MenuItem(_last_query_title, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open Notes Folder",  _open_notes_folder),
        pystray.MenuItem("Force Re-index Now", _trigger_reindex),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", _on_exit),
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def start_tray(
    exit_callback=None,
    reindex_callback=None,
    chunk_count: int = 0,
    ollama_model: str = "unavailable",
) -> threading.Thread:
    """
    Start the system tray icon in a daemon thread.
    Returns the thread (already started).
    """
    import pystray

    _state.exit_callback     = exit_callback
    _state.reindex_callback  = reindex_callback
    _state.chunk_count       = chunk_count
    _state.ollama_model      = ollama_model

    icon_img = _make_icon_image(64)

    icon = pystray.Icon(
        name  = "SecondBrain",
        icon  = icon_img,
        title = "Second Brain — Active",
        menu  = _build_menu(),
    )

    def _run():
        icon.run()

    t = threading.Thread(target=_run, daemon=True, name="TrayThread")
    t.start()
    return t


def update_state(**kwargs):
    """Update shared tray state from main thread (chunk_count, last_query, etc.)"""
    for k, v in kwargs.items():
        if hasattr(_state, k):
            setattr(_state, k, v)
