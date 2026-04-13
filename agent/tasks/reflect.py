"""Weekly reflect task — two-phase: locked decay/transitions, then narrative."""
from __future__ import annotations

from datetime import date, datetime

import sqlite_utils

from agent.ledger import write_updates
from agent.surface.thread import write_message
from core.identity.updater import apply_decay, transition_states


def run_reflect(db: sqlite_utils.Database, store, llm=None, as_of: date | None = None) -> int:
    as_of = as_of or date.today()
    # PHASE 1: locked
    with store.lock():
        model = store.load()
        model, u1 = apply_decay(model, as_of)
        model, u2 = transition_states(model, as_of)
        write_updates(db, u1 + u2)
        store.save(model)

    # PHASE 2: unlocked — narrative + cleanup
    n_active = sum(1 for i in model.interests if i.state == "active")
    parts = [
        "→ Keel (weekly reflect)",
        "",
        f"Interests active: {n_active}",
        f"Total interactions: {model.total_interactions}",
    ]
    write_message(db, "agent", "\n".join(parts), task="reflect")

    # Ghost dismissal cleanup
    try:
        db.execute("DELETE FROM ghost_dismissals WHERE expires_at < ?", [datetime.now().isoformat()])
    except Exception:
        pass
    return n_active
