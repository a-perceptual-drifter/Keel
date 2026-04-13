"""Pure serialization for IdentityModel. No IO."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from core.models import (
    Dismissal,
    IdentityModel,
    Interest,
    MetaPreferences,
    PresentationPrefs,
)


def _iso(v: date | datetime | None) -> str | None:
    return v.isoformat() if v is not None else None


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def _dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


def interest_to_dict(i: Interest) -> dict[str, Any]:
    return {
        "id": i.id,
        "topic": i.topic,
        "weight": i.weight,
        "provenance": i.provenance,
        "decay_rate": i.decay_rate,
        "challenge_mode": i.challenge_mode,
        "state": i.state,
        "first_seen": _iso(i.first_seen),
        "last_reinforced": _iso(i.last_reinforced),
        "lifetime_engagements": i.lifetime_engagements,
        "inactive_since": _iso(i.inactive_since),
        "project_archived_at": _iso(i.project_archived_at),
        "depth_score": i.depth_score,
    }


def interest_from_dict(d: dict) -> Interest:
    return Interest(
        id=d["id"],
        topic=d["topic"],
        weight=float(d["weight"]),
        provenance=d["provenance"],
        decay_rate=d["decay_rate"],
        challenge_mode=d["challenge_mode"],
        state=d["state"],
        first_seen=_d(d["first_seen"]),
        last_reinforced=_d(d["last_reinforced"]),
        lifetime_engagements=int(d.get("lifetime_engagements", 0)),
        inactive_since=_d(d.get("inactive_since")),
        project_archived_at=_d(d.get("project_archived_at")),
        depth_score=float(d.get("depth_score", 0.0)),
    )


def to_dict(model: IdentityModel) -> dict[str, Any]:
    return {
        "version": model.version,
        "created_at": _iso(model.created_at),
        "updated_at": _iso(model.updated_at),
        "interests": [interest_to_dict(i) for i in model.interests],
        "dismissals": [
            {
                "type": d.type,
                "target": d.target,
                "dismissed_at": _iso(d.dismissed_at),
                "permanent": d.permanent,
                "review_after": _iso(d.review_after),
                "resumed_at": _iso(d.resumed_at),
            }
            for d in model.dismissals
        ],
        "anti_interests": list(model.anti_interests),
        "presentation": {
            "default_resolution": model.presentation.default_resolution,
            "per_topic": dict(model.presentation.per_topic),
            "max_items_per_surface": model.presentation.max_items_per_surface,
        },
        "meta": {
            "exploration_bias": model.meta.exploration_bias,
            "depth_bias": model.meta.depth_bias,
            "stance_bias": model.meta.stance_bias,
            "inferred": model.meta.inferred,
            "last_updated": _iso(model.meta.last_updated),
        },
        "mood": model.mood,
        "mood_set_at": _iso(model.mood_set_at),
        "mood_inferred": model.mood_inferred,
        "exploration_end_at": _iso(model.exploration_end_at),
        "total_interactions": model.total_interactions,
    }


def from_dict(d: dict) -> IdentityModel:
    pres = d.get("presentation") or {}
    meta = d.get("meta") or {}
    return IdentityModel(
        version=d.get("version", "1.0"),
        created_at=_d(d.get("created_at")) or date.today(),
        updated_at=_d(d.get("updated_at")) or date.today(),
        interests=[interest_from_dict(x) for x in d.get("interests", [])],
        dismissals=[
            Dismissal(
                type=x["type"],
                target=x["target"],
                dismissed_at=_d(x["dismissed_at"]),
                permanent=bool(x.get("permanent", False)),
                review_after=_d(x.get("review_after")),
                resumed_at=_d(x.get("resumed_at")),
            )
            for x in d.get("dismissals", [])
        ],
        anti_interests=list(d.get("anti_interests", [])),
        presentation=PresentationPrefs(
            default_resolution=pres.get("default_resolution", "summary"),
            per_topic=dict(pres.get("per_topic", {})),
            max_items_per_surface=int(pres.get("max_items_per_surface", 8)),
        ),
        meta=MetaPreferences(
            exploration_bias=float(meta.get("exploration_bias", 0.5)),
            depth_bias=float(meta.get("depth_bias", 0.5)),
            stance_bias=float(meta.get("stance_bias", 0.5)),
            inferred=bool(meta.get("inferred", False)),
            last_updated=_d(meta.get("last_updated")),
        ),
        mood=d.get("mood", "open"),
        mood_set_at=_dt(d.get("mood_set_at")),
        mood_inferred=bool(d.get("mood_inferred", False)),
        exploration_end_at=_d(d.get("exploration_end_at")),
        total_interactions=int(d.get("total_interactions", 0)),
    )
