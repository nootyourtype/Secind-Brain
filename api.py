from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import synthesizer
import scraper

app = FastAPI(title="Second Brain API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_injected_model = None
_injected_collection = None

# ── Models ─────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

class SearchResult(BaseModel):
    source: str
    score: float
    excerpt: str

class SearchResponse(BaseModel):
    results: List[SearchResult]

class ChatRequest(BaseModel):
    query: str
    top_k: int = 3

class ChatResponse(BaseModel):
    insight: str
    sources: List[SearchResult]

class UrlIngestRequest(BaseModel):
    url: str

# ── File Upload ────────────────────────────────────────────────────────────────

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a document file to the notes directory for auto-ingestion."""
    import os, re
    from ingest import NOTES_DIR, SUPPORTED_EXTENSIONS

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    safe_name = re.sub(r'[\\/:*?"<>|]', '_', file.filename)
    dest_path = os.path.join(NOTES_DIR, safe_name)

    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    return {
        "status": "success",
        "file": safe_name,
        "size": len(content),
    }


# ── Dashboard Stats ────────────────────────────────────────────────────────────

@app.get("/stats")
def get_stats():
    """Aggregate statistics for the dashboard."""
    import os
    from ingest import NOTES_DIR, SUPPORTED_EXTENSIONS
    import agent

    file_count = 0
    total_size = 0
    if os.path.exists(NOTES_DIR):
        for fname in os.listdir(NOTES_DIR):
            fpath = os.path.join(NOTES_DIR, fname)
            if os.path.isfile(fpath) and os.path.splitext(fname)[1].lower() in SUPPORTED_EXTENSIONS:
                file_count += 1
                total_size += os.path.getsize(fpath)

    enrichments = agent.get_all_enrichments()
    all_tags = agent.get_all_tags()
    collection = _injected_collection
    chunk_count = collection.count() if collection else 0

    return {
        "file_count": file_count,
        "chunk_count": chunk_count,
        "total_size_bytes": total_size,
        "enriched_count": len(enrichments),
        "unique_tags": len(all_tags),
    }


# ── Reindex & Config ──────────────────────────────────────────────────────────

@app.post("/reindex")
def trigger_reindex():
    """Force a full re-index of the notes directory."""
    global _injected_collection
    from ingest import build_index, DB_PATH, COLLECTION_NAME
    import chromadb

    build_index(silent=True)
    client = chromadb.PersistentClient(path=DB_PATH)
    _injected_collection = client.get_collection(COLLECTION_NAME)
    count = _injected_collection.count()
    return {"status": "success", "chunks": count}


@app.get("/config")
def get_config():
    """Return current brain configuration for the settings page."""
    import os
    from ingest import NOTES_DIR, SUPPORTED_EXTENSIONS, MODEL_NAME, DB_PATH

    ollama_info = synthesizer.check_ollama_status()
    return {
        "notes_dir": NOTES_DIR,
        "db_path": DB_PATH,
        "embedding_model": MODEL_NAME,
        "supported_extensions": list(SUPPORTED_EXTENSIONS),
        "ollama": ollama_info,
    }


# ── Search & Chat ──────────────────────────────────────────────────────────────

@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    model      = _injected_model
    collection = _injected_collection
    if not model or not collection:
        raise HTTPException(status_code=503, detail="Brain not ready")

    query_vec = model.encode([req.query]).tolist()
    results   = collection.query(
        query_embeddings=query_vec,
        n_results=req.top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs  = results["documents"][0] if results["documents"] else []
    metas = results["metadatas"][0]  if results["metadatas"]  else []
    dists = results["distances"][0]  if results["distances"]  else []

    out = []
    for d, m, di in zip(docs, metas, dists):
        out.append(SearchResult(
            source=m.get("source", "Unknown"),
            score=round(1 - di, 3),
            excerpt=d,
        ))
    return SearchResponse(results=out)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    search_res = search(SearchRequest(query=req.query, top_k=req.top_k))

    if not search_res.results:
        return ChatResponse(insight="I don't have any notes related to that.", sources=[])

    docs    = [r.excerpt for r in search_res.results]
    sources = [r.source  for r in search_res.results]

    insight = synthesizer.synthesize(req.query, docs, sources)
    return ChatResponse(
        insight=insight or "Ollama unavailable — showing raw sources.",
        sources=search_res.results,
    )


# ── Status ─────────────────────────────────────────────────────────────────────

@app.get("/status")
def status():
    collection  = _injected_collection
    chunk_count = collection.count() if collection else 0
    ollama_ok   = synthesizer.check_ollama_status()
    return {
        "status":          "online",
        "chunks":          chunk_count,
        "ollama_available": ollama_ok["available"],
        "ollama_model":    ollama_ok["model"],
    }


@app.get("/ollama/status")
def ollama_detailed_status():
    """Detailed Ollama status with all available models."""
    info = synthesizer.check_ollama_status()
    return info


@app.post("/ollama/test")
def ollama_test():
    """Send a quick test prompt to verify Ollama is working end-to-end."""
    try:
        import ollama
        model = synthesizer._get_available_model()
        if not model:
            return {"success": False, "error": "No model available. Run: ollama pull phi3:mini"}

        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: Second Brain AI is online."}],
            options={"num_predict": 20, "temperature": 0.0},
        )
        return {
            "success": True,
            "model": model,
            "response": response.message.content.strip(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── URL Ingestion ──────────────────────────────────────────────────────────────

@app.post("/ingest_url")
def ingest_url(req: UrlIngestRequest):
    try:
        fname = scraper.fetch_and_save_url(req.url)
        return {"status": "success", "file": fname}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Agentic Memory: Notes Library ─────────────────────────────────────────────

@app.get("/notes")
def get_notes():
    """All enriched notes — tags, summaries, chunk counts."""
    try:
        import agent
        enrichments = agent.get_all_enrichments()
        result = {}
        for fname, data in enrichments.items():
            ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else "txt"
            result[fname] = {**data, "file_type": ext}
        return {"notes": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tags")
def get_tags():
    """Sorted, deduplicated list of every tag across all notes."""
    try:
        import agent
        return {"tags": agent.get_all_tags()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notes/{filename}")
def get_note_enrichment(filename: str):
    """Tags + summary for one specific file."""
    try:
        import agent
        data = agent.get_file_enrichment(filename)
        if not data:
            raise HTTPException(status_code=404, detail="Not found or not yet enriched")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notes/{filename}/enrich")
def enrich_note(filename: str):
    """Manually re-trigger enrichment (re-tags + re-summarises) for a file."""
    try:
        import agent, os
        from ingest import NOTES_DIR, parse_file
        fpath = os.path.join(NOTES_DIR, filename)
        if not os.path.exists(fpath):
            raise HTTPException(status_code=404, detail="File not found in notes directory")
        chunks = parse_file(fpath)
        agent.enrich_file_async(filename, chunks)
        return {"status": "enrichment_queued", "file": filename}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notes/{filename}/content")
def get_note_content(filename: str):
    """Read raw file content for the note viewer panel."""
    import os
    from ingest import NOTES_DIR

    fpath = os.path.join(NOTES_DIR, filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(filename)[1].lower()

    if ext in ('.md', '.txt'):
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    elif ext == '.pdf':
        try:
            from pypdf import PdfReader
            reader = PdfReader(fpath)
            content = '\n\n'.join(page.extract_text() or '' for page in reader.pages)
        except Exception:
            content = '[PDF content could not be extracted]'
    elif ext == '.docx':
        try:
            from docx import Document
            doc = Document(fpath)
            content = '\n\n'.join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception:
            content = '[DOCX content could not be extracted]'
    else:
        content = '[Unsupported file type]'

    return {
        "filename": filename,
        "content": content,
        "size": os.path.getsize(fpath),
        "extension": ext,
    }
