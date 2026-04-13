"""Conversational thread: message read/write + event emission."""
from __future__ import annotations

import queue
from datetime import datetime

import sqlite_utils

from core.models import KeelEvent


def write_message(
    db: sqlite_utils.Database,
    role: str,
    content: str,
    task: str | None = None,
    parent_id: int | None = None,
    mood_at_surface: str | None = None,
) -> int:
    pk = db["messages"].insert(
        {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "parent_id": parent_id,
            "mood_at_surface": mood_at_surface,
        }
    ).last_pk
    return int(pk)


def read_history(db: sqlite_utils.Database, limit: int = 50) -> list[dict]:
    return list(
        db.query("SELECT * FROM messages ORDER BY id DESC LIMIT ?", [limit])
    )[::-1]


def emit_event(q: queue.Queue, event: KeelEvent) -> None:
    try:
        q.put_nowait(event)
    except queue.Full:
        pass
