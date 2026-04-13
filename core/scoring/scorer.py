"""Pure scoring function. No IO. No global state."""
from __future__ import annotations

import math

import numpy as np

from core.models import (
    ACTIVE_THRESHOLD,
    CHALLENGE_SIMILARITY_MIN,
    Embedder,
    FILTER_THRESHOLD,
    IdentityModel,
    INTRODUCE_THRESHOLD,
    Interest,
    MatchReason,
    RawItem,
    ScoredArticle,
    SourceStats,
)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _anti_match(item: RawItem, anti: list[str]) -> bool:
    hay = ((item.title or "") + " " + (item.content or "")).lower()
    return any(k.lower() in hay for k in anti if k)


def _bucket_for(score: float) -> str:
    if score >= FILTER_THRESHOLD:
        return "filter"
    if score >= INTRODUCE_THRESHOLD:
        return "introduce"
    return "none"


def score(
    items: list[RawItem],
    identity: IdentityModel,
    embedder: Embedder,
    source_stats: dict[str, SourceStats] | None = None,
) -> list[ScoredArticle]:
    active_interests: list[Interest] = [
        i for i in identity.interests if i.state == "active"
    ]
    kept: list[RawItem] = [
        it for it in items if not _anti_match(it, identity.anti_interests)
    ]
    if not kept:
        return []
    if not active_interests:
        return [
            ScoredArticle(raw=it, interest_score=0.0, bucket="none", match_reason=[])
            for it in kept
        ]

    topic_texts = [i.topic for i in active_interests]
    item_texts = [(it.title or "") + " " + ((it.content or "")[:500]) for it in kept]
    topic_vecs = embedder.embed(topic_texts)
    item_vecs = embedder.embed(item_texts)

    results: list[ScoredArticle] = []
    for it, iv in zip(kept, item_vecs):
        sims: list[tuple[Interest, float]] = []
        for interest, tv in zip(active_interests, topic_vecs):
            sim = _cosine(iv, tv)
            # active-thread weighting: high-weight interests count 2x
            weighted = sim * (2.0 if interest.weight >= ACTIVE_THRESHOLD else 1.0)
            sims.append((interest, weighted))
        sims.sort(key=lambda t: t[1], reverse=True)
        raw_score = sims[0][1] if sims else 0.0
        # clamp to 0..1
        interest_score = max(0.0, min(1.0, raw_score))

        # per-source normalisation
        if source_stats and it.source in source_stats:
            st = source_stats[it.source]
            if st.sample_count >= 20 and st.score_stddev >= 0.01:
                z = (interest_score - st.score_mean) / st.score_stddev
                interest_score = max(0.0, min(1.0, 0.5 + 0.15 * z))

        top3 = [
            MatchReason(topic_id=i.id, topic=i.topic, similarity=round(s, 4))
            for i, s in sims[:3]
        ]
        results.append(
            ScoredArticle(
                raw=it,
                interest_score=round(interest_score, 4),
                bucket=_bucket_for(interest_score),
                match_reason=top3,
            )
        )
    return results
