"""
main.py - Second Brain Orchestrator (Full Product Build)
Ties together:
  - Clipboard monitoring
  - ChromaDB vector search
  - Local LLM synthesis (Ollama)
  - Desktop popup notification
  - File watcher (auto-reindex)
  - System tray icon

Run:  python main.py
"""
import sys, io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import time
import os
import threading
import pyperclip
import chromadb
from sentence_transformers import SentenceTransformer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich import box
from rich.table import Table
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ingest import build_index, DB_PATH, COLLECTION_NAME, NOTES_DIR, MODEL_NAME
from synthesizer import synthesize, check_ollama_status
import popup
import tray
import uvicorn
import api

# ── Config ──────────────────────────────────────────────────────────────────────
POLL_INTERVAL    = 1.0     # seconds between clipboard checks
TOP_K            = 3       # number of results to retrieve
MIN_SCORE        = 0.28    # relevance threshold
MIN_QUERY_LEN    = 10      # skip very short clipboard content
REINDEX_DEBOUNCE = 3.0     # seconds to wait after file change before reindexing
POPUP_DURATION   = 14      # seconds before popup auto-dismisses
# ───────────────────────────────────────────────────────────────────────────────

console = Console()

# ── Shared mutable state (accessed by watcher thread) ──────────────────────────
_collection_ref  = [None]
_model_ref       = [None]
_reindex_timer   = None
_reindex_lock    = threading.Lock()
_should_exit     = threading.Event()


# ── File Watcher ───────────────────────────────────────────────────────────────

class NotesWatcher(FileSystemEventHandler):
    def _schedule(self):
        global _reindex_timer
        with _reindex_lock:
            if _reindex_timer:
                _reindex_timer.cancel()
            _reindex_timer = threading.Timer(REINDEX_DEBOUNCE, self._reindex)
            _reindex_timer.start()

    def _reindex(self):
        console.print()
        console.print(Rule("[bold magenta]Note changed — rebuilding index...[/bold magenta]", style="magenta"))
        try:
            build_index(silent=True)
            client = chromadb.PersistentClient(path=DB_PATH)
            _collection_ref[0] = client.get_collection(COLLECTION_NAME)
            count = _collection_ref[0].count()
            # Keep API server in sync with the new collection
            api._injected_collection = _collection_ref[0]
            tray.update_state(chunk_count=count, last_reindex=time.strftime("%H:%M:%S"))
            console.print(f"[bold green]Index refreshed — {count} chunks ready[/bold green]\n")
        except Exception as e:
            console.print(f"[red]Reindex error: {e}[/red]")

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith((".md", ".txt", ".pdf", ".docx")):
            self._schedule()

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith((".md", ".txt", ".pdf", ".docx")):
            self._schedule()

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.endswith((".md", ".txt", ".pdf", ".docx")):
            self._schedule()


# ── Display (terminal fallback) ────────────────────────────────────────────────

def print_result_terminal(query: str, insight: str | None, results: dict):
    console.print(Rule("[bold yellow]>> Clipboard captured[/bold yellow]", style="yellow"))
    console.print(f'[dim italic]  "{query[:90]}{"..." if len(query) > 90 else ""}"[/dim italic]\n')

    if insight:
        console.print(Panel(
            f"[white]{insight}[/white]",
            title="[bold cyan]AI Insight[/bold cyan]",
            border_style="cyan",
            padding=(0, 2),
        ))
        console.print()

    if not results["documents"][0]:
        console.print("[dim]  No relevant memories found.[/dim]\n")
        return

    for rank, (doc, meta, dist) in enumerate(
        zip(results["documents"][0], results["metadatas"][0], results["distances"][0]), 1
    ):
        score = 1 - dist
        if score < MIN_SCORE:
            continue
        filled     = int(score * 12)
        score_bar  = "[" + "#" * filled + "-" * (12 - filled) + "]"
        score_col  = "green" if score > 0.7 else "yellow" if score > 0.5 else "dim white"
        t = Table(box=box.SIMPLE, show_header=False, padding=(0,1))
        t.add_column("k", style="dim cyan", width=10)
        t.add_column("v", style="white")
        t.add_row("Source",  f"[bold]{meta['source']}[/bold]")
        t.add_row("Score",   f"[{score_col}]{score_bar} {score:.0%}[/{score_col}]")
        t.add_row("Excerpt", f"{doc[:300]}{'...' if len(doc)>300 else ''}")
        console.print(Panel(t, border_style="cyan", padding=(0,1)))
    console.print()


# ── Main ───────────────────────────────────────────────────────────────────────

def run():
    console.rule("[bold cyan]== Second Brain Startup ==[/bold cyan]")

    # 1. Build index if missing
    if not os.path.exists(DB_PATH):
        console.print("[yellow]Building knowledge index from scratch...[/yellow]\n")
        build_index()

    # 2. Load embedding model
    console.print("[yellow]Loading embedding model...[/yellow]")
    model = SentenceTransformer(MODEL_NAME)
    _model_ref[0] = model
    console.print("[green]Embedding model ready[/green]")

    # 3. Connect to ChromaDB
    client     = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(COLLECTION_NAME)
    _collection_ref[0] = collection
    chunk_count = collection.count()
    console.print(f"[green]Brain connected — {chunk_count} chunks loaded[/green]")

    # 4. Check Ollama
    ollama_info = check_ollama_status()
    if ollama_info["available"] and ollama_info["model"]:
        console.print(f"[green]Ollama ready — using model: {ollama_info['model']}[/green]")
        ollama_model = ollama_info["model"]
    else:
        console.print("[yellow]Ollama not running — showing raw excerpts (install Ollama for AI synthesis)[/yellow]")
        ollama_model = "unavailable"

    # 5. Start system tray
    def _on_exit():
        _should_exit.set()

    def _on_reindex():
        console.print("\n[yellow]Manual reindex triggered from tray...[/yellow]")
        NotesWatcher()._reindex()

    tray.start_tray(
        exit_callback     = _on_exit,
        reindex_callback  = _on_reindex,
        chunk_count       = chunk_count,
        ollama_model      = ollama_model,
    )
    console.print("[green]System tray icon started[/green]")

    # 6. Pre-warm popup daemon
    popup._get_or_create_proc()
    console.print("[green]Popup engine pre-warmed[/green]")

    # 7. Start file watcher
    observer = Observer()
    observer.schedule(NotesWatcher(), path=NOTES_DIR, recursive=True)
    observer.start()
    console.print(f"[green]File watcher active: {NOTES_DIR}[/green]")

    # 8. Start Background API Server
    def _run_api():
        api._injected_model = model
        api._injected_collection = _collection_ref[0]
        uvicorn.run(api.app, host="127.0.0.1", port=8000, log_level="error")
    
    api_thread = threading.Thread(target=_run_api, daemon=True, name="APIThread")
    api_thread.start()
    console.print("[green]API Server started on http://127.0.0.1:8000[/green]")

    console.print()
    console.print(Panel.fit(
        "[bold cyan]Second Brain is running[/bold cyan]\n\n"
        "[dim]Copy any text   -> popup appears with your relevant notes\n"
        "Edit a note file -> brain auto-reindexes instantly\n"
        "Right-click tray -> see status / open notes / exit[/dim]",
        border_style="cyan", padding=(1, 4)
    ))
    console.print()

    last_clip = ""

    try:
        while not _should_exit.is_set():
            time.sleep(POLL_INTERVAL)

            try:
                clip = pyperclip.paste().strip()
            except Exception:
                continue

            if clip == last_clip or len(clip) < MIN_QUERY_LEN:
                continue
            last_clip = clip
            tray.update_state(last_query=clip)

            current_col = _collection_ref[0]
            if current_col is None:
                continue

            # Vector search
            query_vec = model.encode([clip]).tolist()
            results = current_col.query(
                query_embeddings = query_vec,
                n_results        = TOP_K,
                include          = ["documents", "metadatas", "distances"],
            )

            # Filter results by score threshold
            docs, metas, dists = [], [], []
            if results["documents"][0]:
                for d, m, di in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
                    if (1 - di) >= MIN_SCORE:
                        docs.append(d);  metas.append(m);  dists.append(di)

            if not docs:
                continue   # nothing relevant — stay silent

            # LLM synthesis
            insight = None
            if ollama_model != "unavailable":
                insight = synthesize(
                    query  = clip,
                    chunks = docs,
                    sources = [m["source"] for m in metas],
                )

            # Build source list for popup
            sources = [
                {"source": m["source"], "score": round(1 - di, 3)}
                for m, di in zip(metas, dists)
            ]

            # Show popup (non-blocking)
            popup.show(
                query    = clip,
                insight  = insight,
                sources  = sources,
                duration = POPUP_DURATION,
            )

            # Also print to terminal
            print_result_terminal(clip, insight, results)

    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
        console.print("\n[bold red]Second Brain stopped.[/bold red]\n")


if __name__ == "__main__":
    run()
