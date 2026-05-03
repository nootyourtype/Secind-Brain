"""
popup.py - Desktop Popup Window (Phase 2C - Persistent Daemon)
We run this once as a background process so the WebView engine
is "warm", bringing popup load times down from ~2 seconds to ~10ms.

It reads JSON payloads from stdin and shows/updates the window instantly.
"""
import sys, io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
import json
import threading
import subprocess

POPUP_W    = 400
POPUP_H    = 360
MARGIN     = 20
DURATION   = 12
HTML_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "popup_template.html")

# ── Controller (Runs in main.py) ───────────────────────────────────────────────

_popup_proc = None

def _get_or_create_proc():
    global _popup_proc
    if _popup_proc is None or _popup_proc.poll() is not None:
        _popup_proc = subprocess.Popen(
            [sys.executable, __file__, "--daemon"],
            stdin=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
    return _popup_proc

def show(query: str, insight: str | None, sources: list[dict], duration: int = DURATION):
    """
    Called by main.py. Instantly writes to the warm daemon process via stdin.
    """
    payload = {
        "query":    query[:120],
        "insight":  insight,
        "sources":  sources[:3],
        "duration": duration,
    }
    
    proc = _get_or_create_proc()
    try:
        proc.stdin.write((json.dumps(payload) + "\n").encode('utf-8'))
        proc.stdin.flush()
    except Exception:
        pass  # if pipe broke, it'll restart on the next copy


# ── Daemon (Runs in the background subprocess) ─────────────────────────────────

def _daemon_main():
    import webview
    
    class PopupAPI:
        def __init__(self):
            self._window = None

        def set_window(self, win):
            self._window = win

        def get_data(self) -> str:
            return "{}"

        def close_window(self):
            """Called by JS dismiss() to hide the window, not destroy it."""
            if self._window:
                self._window.hide()

    _cached_screen_size = [None]

    def _get_screen_size():
        if _cached_screen_size[0] is not None:
            return _cached_screen_size[0]
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            w = root.winfo_screenwidth()
            h = root.winfo_screenheight()
            root.destroy()
            _cached_screen_size[0] = (w, h)
            return w, h
        except:
            return 1920, 1080

    def _stdin_reader(window):
        """Listens for JSON payloads from the parent process over stdin."""
        while True:
            try:
                line = sys.stdin.buffer.readline()
                if not line:
                    window.destroy()
                    break
                    
                payload = json.loads(line.decode('utf-8').strip())
                
                # Reposition and inject data
                sw, sh = _get_screen_size()
                window.move(sw - POPUP_W - MARGIN, sh - POPUP_H - MARGIN - 48)
                
                js = f"""
                    document.getElementById('card').classList.remove('hiding');
                    populate({json.dumps(payload)});
                """
                window.evaluate_js(js)
                window.show()
                
            except Exception as e:
                pass

    def _on_loaded(window):
        t = threading.Thread(target=_stdin_reader, args=(window,), daemon=True)
        t.start()

    api = PopupAPI()
    sw, sh = _get_screen_size()
    
    win = webview.create_window(
        title          = "Second Brain",
        url            = f"file:///{HTML_PATH.replace(chr(92), '/')}",
        js_api         = api,
        width          = POPUP_W,
        height         = POPUP_H,
        x              = sw - POPUP_W - MARGIN,
        y              = sh - POPUP_H - MARGIN - 48,
        resizable      = False,
        frameless      = True,
        on_top         = True,
        transparent    = True,
        hidden         = True,   # <-- Important: start hidden!
        background_color = "#0d1117",
    )
    api.set_window(win)
    win.events.loaded += lambda: _on_loaded(win)
    
    webview.start(debug=False)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        _daemon_main()
