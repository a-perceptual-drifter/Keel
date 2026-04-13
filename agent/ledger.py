"""Audit ledger — writes model_updates rows to SQLite."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

import sqlite_utils

from core.models import ModelUpdate


def write_updates(db: sqlite_utils.Database, updates: Iterable[ModelUpdate]) -> list[int]:
    rows = []
    for u in updates:
        rows.append(
            {
                "timestamp": (u.timestamp or datetime.now()).isoformat(),
                "interest_id": u.interest_id,
                "update_type": u.update_type,
                "field": u.field,
                "value_before": u.value_before,
                "value_after": u.value_after,
                "triggered_by": u.triggered_by,
                "article_id": u.article_id,
            }
        )
    if not rows:
        return []
    db["model_updates"].insert_all(rows)
    return [r.get("id") for r in rows]


def recent_updates(db: sqlite_utils.Database, limit: int = 20) -> list[dict]:
    return list(
        db.query("SELECT * FROM model_updates ORDER BY timestamp DESC LIMIT ?", [limit])
    )
