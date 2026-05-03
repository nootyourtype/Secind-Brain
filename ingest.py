"""
ingest.py - The Brain (Phase 2A: Rich Ingestion)
Supports: .md  .txt  .pdf  .docx
Chunks by paragraphs/headings (not fixed character windows)
for much higher-quality semantic retrieval.
"""
import sys, io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
import re
import hashlib
import chromadb
from sentence_transformers import SentenceTransformer
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich import box

console = Console()

NOTES_DIR       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes")
DB_PATH         = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brain_db")
COLLECTION_NAME = "second_brain"
MODEL_NAME      = "all-MiniLM-L6-v2"

# Supported file types
SUPPORTED_EXTENSIONS = (".md", ".txt", ".pdf", ".docx")

# Chunking config
MIN_CHUNK_CHARS = 60    # discard tiny fragments
MAX_CHUNK_CHARS = 600   # hard cap to keep context windows tight


# ── Parsers ────────────────────────────────────────────────────────────────────

def parse_markdown(text: str) -> list[str]:
    """Split markdown by headings and double-newlines into semantic paragraphs."""
    # Split on lines starting with # (headings) or double blank lines
    blocks = re.split(r"\n#{1,6}\s+|\n\n+", text)
    cleaned = []
    for b in blocks:
        b = re.sub(r"[`*_\[\]()<>#]", " ", b)   # strip markdown syntax
        b = re.sub(r"\s+", " ", b).strip()
        if len(b) >= MIN_CHUNK_CHARS:
            cleaned.append(b[:MAX_CHUNK_CHARS])
    return cleaned


def parse_text(text: str) -> list[str]:
    """Split plain text by paragraphs (double newlines)."""
    blocks = re.split(r"\n\n+", text)
    cleaned = []
    for b in blocks:
        b = re.sub(r"\s+", " ", b).strip()
        if len(b) >= MIN_CHUNK_CHARS:
            cleaned.append(b[:MAX_CHUNK_CHARS])
    return cleaned


def parse_pdf(path: str) -> list[str]:
    """Extract text page-by-page from a PDF, then split by paragraphs."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        chunks = []
        for page in reader.pages:
            raw = page.extract_text() or ""
            chunks.extend(parse_text(raw))
        return chunks
    except Exception as e:
        console.print(f"[red]  PDF parse error ({os.path.basename(path)}): {e}[/red]")
        return []


def parse_docx(path: str) -> list[str]:
    """Extract text from a DOCX file, grouping by heading boundaries."""
    try:
        from docx import Document
        doc = Document(path)
        chunks   = []
        buffer   = []

        def flush():
            combined = " ".join(buffer).strip()
            if len(combined) >= MIN_CHUNK_CHARS:
                chunks.append(combined[:MAX_CHUNK_CHARS])
            buffer.clear()

        for para in doc.paragraphs:
            text  = para.text.strip()
            style = para.style.name.lower() if para.style else ""
            if not text:
                continue
            # Each heading starts a new chunk
            if "heading" in style:
                flush()
                buffer.append(text)
            else:
                buffer.append(text)
                # Flush when buffer is large enough to stand alone
                if len(" ".join(buffer)) >= MAX_CHUNK_CHARS // 2:
                    flush()

        flush()   # final flush
        return chunks
    except Exception as e:
        console.print(f"[red]  DOCX parse error ({os.path.basename(path)}): {e}[/red]")
        return []


def parse_file(path: str) -> list[str]:
    """Route a file to the correct parser based on extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return parse_pdf(path)
    elif ext == ".docx":
        return parse_docx(path)
    elif ext == ".md":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return parse_markdown(f.read())
    elif ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return parse_text(f.read())
    return []


def file_id(path: str) -> str:
    """Stable short ID for a file path (used as chunk prefix)."""
    return hashlib.md5(path.encode()).hexdigest()[:8]


# ── Ingestion Pipeline ─────────────────────────────────────────────────────────

def scan_files(directory: str) -> list[str]:
    """Return all supported files under a directory recursively."""
    found = []
    for root, _, files in os.walk(directory):
        for fname in files:
            if fname.lower().endswith(SUPPORTED_EXTENSIONS):
                found.append(os.path.join(root, fname))
    return sorted(found)


def build_index(silent: bool = False):
    """
    Full re-index pipeline.
    silent=True suppresses decorative headers (useful when called from watcher).
    """
    if not silent:
        console.rule("[bold cyan]== Second Brain - Knowledge Ingestion ==[/bold cyan]")

    # ── Load model ─────────────────────────────────────────────────────────
    if not silent:
        console.print("[yellow]Loading embedding model (local, no cloud)...[/yellow]")
    model = SentenceTransformer(MODEL_NAME)
    if not silent:
        console.print("[green]Embedding model ready[/green]")

    # ── Init ChromaDB ──────────────────────────────────────────────────────
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    # ── Scan files ─────────────────────────────────────────────────────────
    files = scan_files(NOTES_DIR)
    if not files:
        console.print(f"[red]No files found in {NOTES_DIR}[/red]")
        return

    # ── Parse + collect chunks ─────────────────────────────────────────────
    stats = []
    all_chunks, all_ids, all_metas = [], [], []
    file_chunks: dict[str, list[str]] = {}   # fname -> chunks (for enrichment)

    for fpath in files:
        fname    = os.path.basename(fpath)
        ext      = os.path.splitext(fname)[1].lower().lstrip(".")
        chunks   = parse_file(fpath)
        fid      = file_id(fpath)

        file_chunks[fname] = chunks  # store for agentic enrichment

        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_ids.append(f"{fid}::c{i}")
            all_metas.append({
                "source": fname,
                "path":   fpath,
                "type":   ext,
            })

        stats.append((fname, ext.upper(), len(chunks)))

    # ── Print ingestion table ──────────────────────────────────────────────
    if not silent:
        tbl = Table(title="Files Indexed", box=box.ROUNDED, header_style="bold cyan")
        tbl.add_column("File",   style="white")
        tbl.add_column("Type",   style="dim cyan", width=6)
        tbl.add_column("Chunks", justify="right",  style="green", width=8)
        for fname, ftype, count in stats:
            tbl.add_row(fname, ftype, str(count))
        console.print(tbl)
        console.print()

    # ── Embed ──────────────────────────────────────────────────────────────
    total = len(all_chunks)
    console.print(f"[cyan]Embedding {total} chunks...[/cyan]")
    embeddings = model.encode(all_chunks, show_progress_bar=not silent).tolist()

    # ── Store in batches ───────────────────────────────────────────────────
    batch = 100
    for i in range(0, total, batch):
        collection.add(
            documents  = all_chunks[i:i+batch],
            embeddings = embeddings[i:i+batch],
            ids        = all_ids[i:i+batch],
            metadatas  = all_metas[i:i+batch],
        )

    console.print(f"[bold green]Index built: {total} chunks from {len(files)} file(s)[/bold green]")
    console.print(f"[dim]DB path: {DB_PATH}[/dim]\n")

    # ── Agentic enrichment (async, non-blocking) ───────────────────────────
    try:
        import agent
        for fname, fchunks in file_chunks.items():
            agent.enrich_file_async(fname, fchunks)
        if not silent:
            console.print("[dim]Agentic enrichment queued — tags & summaries generating in background...[/dim]\n")
    except Exception as e:
        if not silent:
            console.print(f"[dim yellow]Agent enrichment skipped: {e}[/dim yellow]\n")

    return collection


if __name__ == "__main__":
    build_index()
