"""
Optional LLM narration layer.

The data-science core (``ml/``) never needs a language model. The LLM is used
only to turn already-computed numbers into readable prose. This helper makes
that dependency *optional*: if no GEMINI_API_KEY is configured, narration calls
return ``None`` and the app falls back to deterministic, template-based text.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")


@lru_cache(maxsize=1)
def _client():
    """Create the Gemini client once, or return None if unavailable."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    try:
        from google import genai

        return genai.Client(api_key=key)
    except Exception:
        return None


def available() -> bool:
    """True if an LLM is configured and importable."""
    return _client() is not None


def narrate(prompt: str) -> str | None:
    """
    Send ``prompt`` to the LLM and return the text, or None on any failure
    (no key, quota exhausted, network error). Callers must handle None.
    """
    client = _client()
    if client is None:
        return None
    try:
        resp = client.models.generate_content(model=MODEL, contents=prompt)
        return resp.text.strip()
    except Exception:
        return None
