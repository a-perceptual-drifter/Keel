"""Silence task — apply -0.02 weight to surfaced items with no interaction."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import sqlite_utils

from agent.ledger import write_updates
from core.identity.updater import apply_interaction


def apply_silence(
    db: sqlite_utils.Database, store, as_of: date | None = None
) -> int:
    as_of = as_of or date.today()
    cutoff = datetime.combine(as_of, datetime.min.time()) - timedelta(hours=48)
    rows = list(
        db.query(
            "SELECT a.id AS article_id, a.match_reason, a.surfaced_msg_id "
            "FROM articles a WHERE a.fetch_state = 'surfaced' AND a.surfaced_at <= ?",
            [cutoff.isoformat()],
        )
    )
    count = 0
    with store.lock():
        model = store.load()
        for r in rows:
            # Cap at 3 silences per (article, message)
            n = list(
                db.query(
                    "SELECT COUNT(*) AS c FROM interactions "
                    "WHERE article_id = ? AND message_id = ? AND type = 'silence'",
                    [r["article_id"], r["surfaced_msg_id"]],
                )
            )[0]["c"]
            if n >= 3:
                continue
            topic_id = None
            try:
                mr = json.loads(r["match_reason"] or "[]")
                if mr:
                    topic_id = mr[0]["topic_id"]
            except Exception:
                pass
            model, updates = apply_interaction(
                model, topic_id, "silence", as_of, article_id=r["article_id"]
            )
            write_updates(db, updates)
            db["interactions"].insert(
                {
                    "article_id": r["article_id"],
                    "message_id": r["surfaced_msg_id"],
                    "type": "silence",
                    "detail": None,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            count += 1
        store.save(model)
    return count
