"""Fetch task — pulls from configured sources, deduplicates, writes rows."""
from __future__ import annotations

from datetime import datetime

import sqlite_utils

from core.models import FetchContext


def fetch_all(db: sqlite_utils.Database, sources: list, context: FetchContext | None = None) -> int:
    if context is None:
        context = FetchContext()
    existing = {row["url"] for row in db["articles"].rows_where("url IS NOT NULL")}
    added = 0
    for source in sources:
        try:
            items = source.fetch(context) or []
        except Exception:
            continue
        for it in items:
            if not it.url or it.url in existing:
                continue
            existing.add(it.url)
            db["articles"].insert(
                {
                    "source": it.source,
                    "source_type": it.source_type,
                    "url": it.url,
                    "title": it.title,
                    "content": it.content,
                    "published_at": it.published_at.isoformat() if it.published_at else None,
                    "fetched_at": it.fetched_at.isoformat(),
                    "fetch_state": "ready_to_score",
                    "external_score": it.external_score,
                    "external_score_prev": it.external_score_prev,
                }
            )
            added += 1
    return added
