"""LLM-driven topic extraction and embedding-based interest matching."""
from __future__ import annotations

import numpy as np

from core.models import IdentityModel, Interest

TOPIC_DEDUP_THRESHOLD = 0.80


def extract_topic(llm, title: str, body: str) -> str:
    """Ask the LLM for a 2-4 word topic phrase summarizing an article.

    Returns a short lowercase phrase. On failure returns an empty string.
    """
    system = (
        "You label articles with a short topic phrase for a personal interest tracker. "
        "Return exactly one topic phrase of 2-4 words. No preamble, no quotes, no punctuation, "
        "no explanation. Lowercase. If the article is unclassifiable, return 'uncategorized'."
    )
    snippet = (body or "")[:1500]
    prompt = f"Title: {title}\n\n{snippet}\n\nTopic phrase:"
    try:
        out = llm.complete(system, prompt, max_tokens=12).strip()
    except Exception:
        return ""
    out = out.strip("'\"`.,;: \n\t").lower()
    out = out.splitlines()[0] if out else ""
    return out[:60]


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def find_matching_interest(
    topic: str,
    model: IdentityModel,
    embedder,
    threshold: float = TOPIC_DEDUP_THRESHOLD,
) -> Interest | None:
    """Return the existing interest whose topic embedding is most similar to `topic`,
    if above the dedup threshold. Otherwise None."""
    if not topic or topic == "uncategorized":
        return None
    if not model.interests:
        return None
    topic_strings = [topic] + [i.topic for i in model.interests]
    try:
        vecs = embedder.embed(topic_strings)
    except Exception:
        return None
    if not vecs or len(vecs) != len(topic_strings):
        return None
    query = vecs[0]
    best: tuple[float, Interest | None] = (0.0, None)
    for iv, interest in zip(vecs[1:], model.interests):
        sim = _cosine(query, iv)
        if sim > best[0]:
            best = (sim, interest)
    if best[0] >= threshold:
        return best[1]
    return None
