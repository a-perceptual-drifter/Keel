"""Score task — runs core.scorer.score() over ready_to_score articles."""
from __future__ import annotations

import json
from datetime import datetime

import sqlite_utils

from core.models import Embedder, IdentityModel, RawItem
from core.scoring.scorer import score as core_score


def _row_to_raw(r: dict) -> RawItem:
    return RawItem(
        id=str(r["id"]),
        source=r["source"],
        source_type=r["source_type"],
        title=r.get("title") or "",
        url=r["url"],
        content=r.get("content") or "",
        published_at=datetime.fromisoformat(r["published_at"]) if r.get("published_at") else None,
        fetched_at=datetime.fromisoformat(r["fetched_at"]),
        external_score=int(r.get("external_score") or 0),
        external_score_prev=int(r.get("external_score_prev") or 0),
    )


def score_pending(db: sqlite_utils.Database, identity: IdentityModel, embedder: Embedder) -> int:
    rows = list(db["articles"].rows_where("fetch_state = ?", ["ready_to_score"]))
    if not rows:
        return 0
    raws = [_row_to_raw(r) for r in rows]
    scored = core_score(raws, identity, embedder)
    id_by_raw_id = {s.raw.id: s for s in scored}
    for r in rows:
        s = id_by_raw_id.get(str(r["id"]))
        if not s:
            continue
        db["articles"].update(
            r["id"],
            {
                "fetch_state": "scored",
                "interest_score": s.interest_score,
                "bucket": s.bucket,
                "match_reason": json.dumps(
                    [
                        {"topic_id": m.topic_id, "topic": m.topic, "similarity": m.similarity}
                        for m in s.match_reason
                    ]
                ),
            },
        )
    return len(rows)
