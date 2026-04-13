"""End-to-end pipeline smoke: fetch→score→surface→silence→reflect."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
import sqlite_utils

from agent.init import apply_migrations, seed_identity
from agent.store import JsonStore
from agent.tasks.fetch import fetch_all
from agent.tasks.reflect import run_reflect
from agent.tasks.score import score_pending
from agent.tasks.silence import apply_silence
from agent.tasks.surface import run_surface
from core.models import FetchContext, RawItem
from tests.mocks.embedder import MockEmbedder
from tests.mocks.llm import MockLLM


class FakeSource:
    name = "fake"
    source_type = "rss"

    def __init__(self, items: list[RawItem]):
        self._items = items

    def fetch(self, ctx: FetchContext) -> list[RawItem]:
        return list(self._items)


def _raw(title: str, content: str = "body") -> RawItem:
    return RawItem(
        id=title, source="fake", source_type="rss",
        title=title, url=f"https://example.test/{title.replace(' ', '-')}",
        content=content, published_at=None, fetched_at=datetime.now(),
    )


def test_full_pipeline(tmp_path):
    db_path = tmp_path / "keel.db"
    # apply migrations
    import shutil
    src = Path(__file__).resolve().parents[2] / "migrations"
    migrations_dst = tmp_path / "migrations"
    shutil.copytree(src, migrations_dst)

    # Patch apply_migrations to use tmp migrations dir via monkey
    db = sqlite_utils.Database(str(db_path))
    db.executescript(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version TEXT PRIMARY KEY, applied_at DATETIME NOT NULL);"
    )
    for sql_file in sorted(migrations_dst.glob("*.sql")):
        db.executescript(sql_file.read_text())

    store = JsonStore(tmp_path / "identity.json")
    seed_identity(store, ["local-first software", "climate adaptation"])

    # Fetch
    source = FakeSource([
        _raw("local-first software guide", "building offline-first apps"),
        _raw("climate adaptation strategies", "planning for a warming world"),
        _raw("unrelated sports headline", "team wins big game"),
    ])
    added = fetch_all(db, [source])
    assert added == 3

    # Score
    n = score_pending(db, store.load(), MockEmbedder())
    assert n == 3
    states = {r["fetch_state"] for r in db["articles"].rows}
    assert "scored" in states

    # Force high scores so surface picks them (MockEmbedder similarity is ~0)
    db.execute(
        "UPDATE articles SET bucket='filter', interest_score=0.80 WHERE fetch_state='scored'"
    )
    db.conn.commit()
    run_surface(db, store, llm=MockLLM())
    # at least the messages table has an entry
    assert db["messages"].count >= 1

    # Mark surfaced_at to 49h ago so silence will pick them up
    past = (datetime.now() - timedelta(hours=49)).isoformat()
    db.execute("UPDATE articles SET surfaced_at=? WHERE fetch_state='surfaced'", [past])
    db.conn.commit()
    apply_silence(db, store)

    # Reflect
    run_reflect(db, store, llm=MockLLM())
    assert db["messages"].count >= 2
