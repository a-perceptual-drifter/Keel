"""Surface task — select items, render, write message, mark articles."""
from __future__ import annotations

import json
from datetime import datetime

import sqlite_utils

from agent.surface.renderer import assemble_surface_message
from agent.surface.thread import write_message
from core.expansion.mood import apply_mood_thresholds
from core.models import IdentityModel, MatchReason, RawItem, ScoredArticle


def _row_to_scored(r: dict) -> ScoredArticle:
    mr = []
    try:
        for m in json.loads(r.get("match_reason") or "[]"):
            mr.append(MatchReason(topic_id=m["topic_id"], topic=m["topic"], similarity=m["similarity"]))
    except Exception:
        pass
    raw = RawItem(
        id=str(r["id"]),
        source=r["source"],
        source_type=r["source_type"],
        title=r.get("title") or "",
        url=r["url"],
        content=r.get("content") or "",
        published_at=None,
        fetched_at=datetime.fromisoformat(r["fetched_at"]) if r.get("fetched_at") else datetime.now(),
        external_score=int(r.get("external_score") or 0),
    )
    return ScoredArticle(
        raw=raw,
        interest_score=float(r.get("interest_score") or 0),
        bucket=r.get("bucket") or "none",
        match_reason=mr,
    )


def run_surface(db: sqlite_utils.Database, store, llm=None, runtime=None) -> int:
    model: IdentityModel = store.load()
    filter_t, intro_t = apply_mood_thresholds(model.mood)
    rows = list(
        db.query(
            "SELECT * FROM articles WHERE fetch_state='scored' "
            "ORDER BY interest_score DESC LIMIT 50"
        )
    )
    scored = [_row_to_scored(r) for r in rows]
    max_items = model.presentation.max_items_per_surface
    # priority chain: challenge > filter > introduce
    priority = {"challenge": 0, "filter": 1, "introduce": 2, "none": 3}
    scored.sort(key=lambda s: (priority.get(s.bucket, 9), -s.interest_score))
    selected = [s for s in scored if s.bucket in ("filter", "introduce", "challenge")][:max_items]
    if not selected:
        return 0
    msg = assemble_surface_message(selected, mood=model.mood, llm=llm)
    msg_id = write_message(db, "agent", msg, task="surface", mood_at_surface=model.mood)
    for s in selected:
        db["articles"].update(
            int(s.raw.id),
            {
                "fetch_state": "surfaced",
                "surfaced_at": datetime.now().isoformat(),
                "surfaced_msg_id": msg_id,
                "resolution": model.presentation.default_resolution,
            },
        )
    if runtime is not None:
        runtime.emit(
            "new_message",
            {
                "message_id": msg_id,
                "task": "surface",
                "content": msg,
                "count": len(selected),
            },
        )
    return len(selected)
