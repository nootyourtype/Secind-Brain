"""
agent.py - Agentic Memory (Phase 4.3)
Background worker that auto-tags and auto-summarizes documents as they are ingested.
Uses Ollama for all AI processing — 100% local, zero cloud.

Falls back gracefully if Ollama is unavailable — enrichments are simply skipped.
"""
import sys, io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import os
import threading
import time
from typing import Optional

# Preferred local models (same list as synthesizer.py)
PREFERRED_MODELS = ["phi3:mini", "llama3.2:1b", "llama3.2:3b", "llama3:8b", "mistral"]

ENRICHMENTS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "brain_db", "enrichments.json"
)

_lock = threading.Lock()


# ── Persistence ────────────────────────────────────────────────────────────────

def _load_enrichments() -> dict:
    if os.path.exists(ENRICHMENTS_PATH):
        try:
            with open(ENRICHMENTS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_enrichments(data: dict):
    os.makedirs(os.path.dirname(ENRICHMENTS_PATH), exist_ok=True)
    with open(ENRICHMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Ollama Helper ──────────────────────────────────────────────────────────────

def _get_model() -> Optional[str]:
    try:
        import ollama
        models = ollama.list()
        available = {m.model.split(":")[0] for m in models.models}
        for preferred in PREFERRED_MODELS:
            name = preferred.split(":")[0]
            if name in available:
                return preferred
        if models.models:
            return models.models[0].model
    except Exception:
        pass
    return None


# ── AI workers ────────────────────────────────────────────────────────────────

def generate_tags(text: str, filename: str) -> list[str]:
    """Ask Ollama to generate 3-6 semantic tags for the document."""
    model = _get_model()
    if not model:
        return []
    try:
        import ollama
        prompt = (
            f"Analyze this document and generate 3 to 6 concise semantic tags.\n"
            f"Rules:\n"
            f"- Tags must be lowercase, 1-3 words each\n"
            f"- Focus on main topics, concepts, or domain areas\n"
            f"- Return ONLY a JSON array of strings, nothing else\n"
            f"- Example: [\"machine learning\", \"python\", \"neural networks\"]\n\n"
            f"Filename: {filename}\n\n"
            f"Excerpt:\n{text[:1200]}\n\n"
            f"JSON array of tags:"
        )
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 120, "temperature": 0.1},
        )
        raw = response.message.content.strip()
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        if start != -1 and end > start:
            tags = json.loads(raw[start:end])
            return [str(t).lower().strip() for t in tags if t][:6]
    except Exception:
        pass
    return []


def generate_summary(text: str, filename: str) -> Optional[str]:
    """Ask Ollama to generate a 2-3 sentence executive summary."""
    model = _get_model()
    if not model:
        return None
    try:
        import ollama
        prompt = (
            f"Write a 2-3 sentence executive summary of the document below.\n"
            f"Be specific and factual. Mention the main topics and key takeaways.\n"
            f"Do NOT start with 'This document' or 'The document'.\n"
            f"Keep under 60 words.\n\n"
            f"Filename: {filename}\n\n"
            f"Content:\n{text[:2000]}\n\n"
            f"Summary:"
        )
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 140, "temperature": 0.2},
        )
        return response.message.content.strip()
    except Exception:
        return None


# ── Enrichment Pipeline ────────────────────────────────────────────────────────

def enrich_file(filename: str, chunks: list[str]) -> Optional[dict]:
    """
    Run auto-tagging + auto-summarization for one file.
    Persists result to enrichments.json. Thread-safe.
    Returns the enrichment dict, or None if Ollama is unavailable.
    """
    if not chunks or not _get_model():
        return None

    combined = "\n\n".join(chunks[:5])   # first ~5 chunks for analysis

    tags    = generate_tags(combined, filename)
    summary = generate_summary(combined, filename)

    enrichment = {
        "tags":        tags,
        "summary":     summary or "",
        "enriched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "chunk_count": len(chunks),
    }

    with _lock:
        data = _load_enrichments()
        data[filename] = enrichment
        _save_enrichments(data)

    return enrichment


def enrich_file_async(filename: str, chunks: list[str]) -> threading.Thread:
    """Kick off enrichment in a background daemon thread (non-blocking)."""
    t = threading.Thread(
        target=enrich_file,
        args=(filename, chunks),
        daemon=True,
        name=f"Enrich-{filename[:20]}",
    )
    t.start()
    return t


# ── Public accessors ───────────────────────────────────────────────────────────

def get_all_enrichments() -> dict:
    with _lock:
        return _load_enrichments()


def get_file_enrichment(filename: str) -> Optional[dict]:
    with _lock:
        return _load_enrichments().get(filename)


def get_all_tags() -> list[str]:
    """Return a sorted, deduplicated list of every tag across all files."""
    data = get_all_enrichments()
    tags = set()
    for enrichment in data.values():
        tags.update(enrichment.get("tags", []))
    return sorted(tags)


# ── CLI (for manual enrichment runs) ─────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from ingest import NOTES_DIR, scan_files, parse_file
    print("Running agentic enrichment on all notes in:", NOTES_DIR)
    files = scan_files(NOTES_DIR)
    for fpath in files:
        fname  = os.path.basename(fpath)
        chunks = parse_file(fpath)
        print(f"  Enriching {fname} ({len(chunks)} chunks)...")
        result = enrich_file(fname, chunks)
        if result:
            print(f"    Tags: {result['tags']}")
            print(f"    Summary: {result['summary'][:80]}...")
        else:
            print(f"    Skipped (Ollama unavailable)")
    print("Done.")
