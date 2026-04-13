"""Startup: migrations, reconciliation, onboarding seed."""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path

import sqlite_utils

from agent.store import JsonStore
from core.identity.model import interest_from_dict
from core.models import (
    IdentityModel,
    Interest,
    MetaPreferences,
    PresentationPrefs,
)

log = logging.getLogger(__name__)


def apply_migrations(db_path: str) -> None:
    db = sqlite_utils.Database(db_path)
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    db.executescript(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version TEXT PRIMARY KEY, applied_at DATETIME NOT NULL);"
    )
    applied = {r["version"] for r in db["schema_migrations"].rows}
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        version = sql_file.stem
        if version in applied:
            continue
        sql = sql_file.read_text()
        try:
            db.executescript(sql)
            db["schema_migrations"].insert({"version": version, "applied_at": datetime.now().isoformat()})
            log.info("applied migration %s", version)
        except Exception as e:
            log.error("migration %s failed: %s", version, e)
            raise


def reconcile_identity(db: sqlite_utils.Database, store: JsonStore) -> None:
    """Re-apply orphaned model_updates (field='_interest') to identity.json."""
    model = store.load()
    # scan last 24h of _interest rows and re-apply if current model doesn't match
    try:
        rows = list(
            db.query(
                "SELECT * FROM model_updates WHERE field = '_interest' "
                "ORDER BY timestamp DESC LIMIT 50"
            )
        )
    except Exception:
        return
    current = {i.id: i for i in model.interests}
    dirty = False
    for r in rows:
        iid = r.get("interest_id")
        va = r.get("value_after")
        if not iid or not va:
            continue
        try:
            new_i = interest_from_dict(json.loads(va))
        except Exception:
            continue
        if iid in current and current[iid] != new_i:
            current[iid] = new_i
            dirty = True
            break  # only re-apply the newest mismatch
    if dirty:
        from dataclasses import replace
        model = replace(model, interests=list(current.values()))
        store.save(model)
        log.info("reconciled identity from orphaned updates")


def seed_identity(store: JsonStore, topics: list[str], as_of: date | None = None) -> IdentityModel:
    """Seed a brand-new identity model from onboarding topics."""
    as_of = as_of or date.today()
    interests = []
    for i, t in enumerate(topics):
        interests.append(
            Interest(
                id=f"int_seed_{i:03d}",
                topic=t,
                weight=0.50,
                provenance="given",
                decay_rate="medium",
                challenge_mode="adjacent",
                state="active",
                first_seen=as_of,
                last_reinforced=as_of,
            )
        )
    model = IdentityModel(
        version="1.0",
        created_at=as_of,
        updated_at=as_of,
        interests=interests,
        dismissals=[],
        anti_interests=[],
        presentation=PresentationPrefs(),
        meta=MetaPreferences(),
    )
    store.save(model)
    return model
