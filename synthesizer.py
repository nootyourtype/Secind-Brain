"""
synthesizer.py - The AI Layer (Phase 2B)
Uses a local Ollama LLM (zero cloud, zero API key) to synthesize
matched knowledge chunks into a concise, human-readable insight.

Falls back gracefully if Ollama is not installed or no model is running.
"""
import sys, io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from typing import Optional

# Preferred local models in order (smallest/fastest first)
PREFERRED_MODELS = ["phi3:mini", "llama3.2:1b", "llama3.2:3b", "llama3:8b", "mistral"]
OLLAMA_TIMEOUT   = 15   # seconds — don't block clipboard monitoring for too long


def _get_available_model() -> Optional[str]:
    """Return the first available Ollama model from our preference list."""
    try:
        import ollama
        models = ollama.list()
        available = {m.model.split(":")[0] for m in models.models}
        for preferred in PREFERRED_MODELS:
            name = preferred.split(":")[0]
            if name in available:
                return preferred
        # If none of our preferred models, just use whatever is there
        if models.models:
            return models.models[0].model
    except Exception:
        pass
    return None


def synthesize(query: str, chunks: list[str], sources: list[str]) -> Optional[str]:
    """
    Given a user query and a list of matched knowledge chunks,
    call a local Ollama LLM to synthesize a 2-3 sentence insight.

    Returns:
        str  - the synthesized insight
        None - if Ollama is unavailable (caller should fall back to raw chunks)
    """
    model = _get_available_model()
    if not model:
        return None

    # Build context block from chunks
    context = "\n\n".join(
        f"[Source: {src}]\n{chunk}"
        for chunk, src in zip(chunks, sources)
    )

    prompt = f"""You are a personal knowledge assistant. The user just copied this text:

QUERY: "{query}"

Below are the most relevant excerpts from their personal notes:

{context}

Your task: Write a 2-3 sentence synthesis that directly answers or contextualizes 
the query using ONLY the information in the notes above. 
Be specific, use exact terms from the notes. Do not add information not in the notes.
Do not say "Based on your notes" or "According to" -- just state the insight directly.
Keep it under 80 words."""

    try:
        import ollama
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 150, "temperature": 0.2},
        )
        return response.message.content.strip()
    except Exception as e:
        return None


def check_ollama_status() -> dict:
    """
    Returns a dict with Ollama availability info.
    Used by main.py to show status on startup.
    """
    try:
        import ollama
        models = ollama.list()
        model  = _get_available_model()
        return {
            "available": True,
            "model":     model or "none",
            "all_models": [m.model for m in models.models],
        }
    except Exception as e:
        return {
            "available": False,
            "model":     None,
            "error":     str(e),
        }
