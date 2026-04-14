"""Prefetch task — populate article body for scored items so summarize is instant."""
from __future__ import annotations

import logging

import sqlite_utils

from agent.body_fetch import MIN_BODY_CHARS, fetch_article_body

log = logging.getLogger(__name__)


def prefetch_bodies(db: sqlite_utils.Database, limit: int = 50) -> int:
    """For scored articles missing a usable body, fetch + extract once and tag body_status.
    Returns the number of articles processed (ok + link_only)."""
    rows = list(
        db.query(
            "SELECT id, url, content FROM articles "
            "WHERE fetch_state = 'scored' AND body_status IS NULL "
            "ORDER BY interest_score DESC LIMIT ?",
            [limit],
        )
    )
    processed = 0
    for r in rows:
        existing = (r.get("content") or "").strip()
        if len(existing) >= MIN_BODY_CHARS:
            db["articles"].update(int(r["id"]), {"body_status": "body_ok"})
            processed += 1
            continue
        body = ""
        try:
            body = fetch_article_body(r["url"])
        except Exception:
            log.exception("prefetch failed for %s", r["url"])
        if body and len(body) >= MIN_BODY_CHARS:
            db["articles"].update(
                int(r["id"]),
                {"content": body, "body_status": "body_ok"},
            )
        else:
            db["articles"].update(int(r["id"]), {"body_status": "link_only"})
        processed += 1
    return processed
