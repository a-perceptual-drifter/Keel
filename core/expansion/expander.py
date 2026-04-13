"""Pure expansion helpers: edge candidates + world signal scoring."""
from __future__ import annotations

from core.models import IdentityModel, ScoredArticle

EDGE_LOW = 0.40
EDGE_HIGH = 0.54


def find_edge_candidates(
    scored: list[ScoredArticle], identity: IdentityModel
) -> list[ScoredArticle]:
    """Items in the 0.40–0.54 similarity band are edge candidates."""
    out = []
    for s in scored:
        if EDGE_LOW <= s.interest_score < EDGE_HIGH:
            out.append(s)
    return out


def score_world_signal(
    scored: list[ScoredArticle], identity: IdentityModel
) -> list[ScoredArticle]:
    """World signal: low-similarity items boosted by external engagement."""
    out = []
    for s in scored:
        if s.interest_score >= EDGE_LOW:
            continue
        ext = s.raw.external_score or 0
        if ext >= 100:
            out.append(s)
    out.sort(key=lambda x: x.raw.external_score or 0, reverse=True)
    return out
