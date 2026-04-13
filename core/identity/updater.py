"""Pure updater functions. Take IdentityModel, return (new_model, updates).

No IO. `as_of` is always passed in — never call datetime.now().
"""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime
from typing import Any

from core.identity.model import interest_to_dict
from core.models import (
    EPSILON_FLOOR,
    EXPLORATION_INTERACTIONS,
    HALF_LIFE_DAYS,
    IdentityModel,
    Interest,
    ModelUpdate,
    REINFORCEMENT,
    WEIGHT_FLOOR,
)


def _now_ts(as_of: date) -> datetime:
    return datetime.combine(as_of, datetime.min.time())


def _interest_snapshot(i: Interest) -> str:
    return json.dumps(interest_to_dict(i), sort_keys=True)


def apply_decay(
    model: IdentityModel, as_of: date
) -> tuple[IdentityModel, list[ModelUpdate]]:
    updates: list[ModelUpdate] = []
    new_interests: list[Interest] = []
    for i in model.interests:
        hl = HALF_LIFE_DAYS.get(i.decay_rate)
        if hl is None or i.state in ("archived", "discontinued"):
            new_interests.append(i)
            continue
        days = max(0, (as_of - i.last_reinforced).days)
        if days == 0:
            new_interests.append(i)
            continue
        new_w = max(WEIGHT_FLOOR, i.weight * (0.5 ** (days / hl)))
        if abs(new_w - i.weight) < 1e-9:
            new_interests.append(i)
            continue
        before = _interest_snapshot(i)
        # Track inactive_since on floor hit
        inactive_since = i.inactive_since
        if new_w <= EPSILON_FLOOR and inactive_since is None:
            inactive_since = as_of
        elif new_w > EPSILON_FLOOR:
            inactive_since = None
        new_i = replace(i, weight=new_w, inactive_since=inactive_since)
        new_interests.append(new_i)
        updates.append(
            ModelUpdate(
                timestamp=_now_ts(as_of),
                interest_id=i.id,
                update_type="decay",
                field="_interest",
                value_before=before,
                value_after=_interest_snapshot(new_i),
                triggered_by="decay",
            )
        )
    new_model = replace(
        model, interests=new_interests, updated_at=as_of
    )
    return new_model, updates


def transition_states(
    model: IdentityModel, as_of: date
) -> tuple[IdentityModel, list[ModelUpdate]]:
    updates: list[ModelUpdate] = []
    new_interests: list[Interest] = []
    for i in model.interests:
        if i.state in ("discontinued", "archived"):
            new_interests.append(i)
            continue
        # Grace period: < 14 days since first_seen
        age_days = (as_of - i.first_seen).days
        new_state = i.state
        if i.weight <= EPSILON_FLOOR:
            if i.lifetime_engagements >= 5:
                new_state = "dormant"
            elif age_days >= 14 and i.inactive_since and (as_of - i.inactive_since).days >= 21:
                new_state = "inactive"
        elif i.state in ("dormant", "inactive") and i.weight > EPSILON_FLOOR:
            new_state = "active"
        if new_state != i.state:
            before = _interest_snapshot(i)
            new_i = replace(i, state=new_state)
            new_interests.append(new_i)
            updates.append(
                ModelUpdate(
                    timestamp=_now_ts(as_of),
                    interest_id=i.id,
                    update_type="decay",
                    field="_interest",
                    value_before=before,
                    value_after=_interest_snapshot(new_i),
                    triggered_by="state_transition",
                )
            )
        else:
            new_interests.append(i)
    return replace(model, interests=new_interests, updated_at=as_of), updates


def apply_interaction(
    model: IdentityModel,
    interest_id: str | None,
    interaction_type: str,
    as_of: date,
    article_id: int | None = None,
) -> tuple[IdentityModel, list[ModelUpdate]]:
    """Apply a graded reinforcement interaction to an interest."""
    updates: list[ModelUpdate] = []
    delta = REINFORCEMENT.get(interaction_type, 0.0)
    reset_clock = interaction_type in {
        "engage", "acknowledged", "go_further", "worth_it", "correct", "nuanced", "challenge_set"
    }
    new_interests: list[Interest] = []
    for i in model.interests:
        if i.id != interest_id or interest_id is None:
            new_interests.append(i)
            continue
        before = _interest_snapshot(i)
        new_w = max(WEIGHT_FLOOR, min(1.0, i.weight + delta))
        last_rf = as_of if reset_clock else i.last_reinforced
        lifetime = i.lifetime_engagements + (1 if delta > 0 else 0)
        state = i.state
        if state in ("dormant", "inactive") and delta > 0:
            state = "active"
            new_w = max(new_w, 0.40)
            last_rf = as_of
        depth = i.depth_score
        if interaction_type == "go_further":
            depth = min(1.0, depth + 0.04)
        elif interaction_type == "worth_it":
            depth = min(1.0, depth + 0.05)
        elif interaction_type == "nuanced":
            depth = min(1.0, depth + 0.03)
        # Promote interpreted→selected after 3 lifetime engagements
        provenance = i.provenance
        if provenance == "interpreted" and lifetime >= 3:
            provenance = "selected"
            updates.append(
                ModelUpdate(
                    timestamp=_now_ts(as_of),
                    interest_id=i.id,
                    update_type="provenance_promotion",
                    field="provenance",
                    value_before="interpreted",
                    value_after="selected",
                    triggered_by=interaction_type,
                    article_id=article_id,
                )
            )
        new_i = replace(
            i,
            weight=new_w,
            last_reinforced=last_rf,
            lifetime_engagements=lifetime,
            state=state,
            depth_score=depth,
            provenance=provenance,
            inactive_since=None if new_w > EPSILON_FLOOR else i.inactive_since,
        )
        new_interests.append(new_i)
        updates.append(
            ModelUpdate(
                timestamp=_now_ts(as_of),
                interest_id=i.id,
                update_type="reinforcement",
                field="_interest",
                value_before=before,
                value_after=_interest_snapshot(new_i),
                triggered_by=interaction_type,
                article_id=article_id,
            )
        )

    total = model.total_interactions + 1
    expl_end = model.exploration_end_at
    if expl_end is None and total >= EXPLORATION_INTERACTIONS:
        expl_end = as_of
    new_model = replace(
        model,
        interests=new_interests,
        updated_at=as_of,
        total_interactions=total,
        exploration_end_at=expl_end,
    )
    return new_model, updates


def nuance_interest(
    model: IdentityModel,
    interest_id: str,
    instruction: str,
    llm: Any,
    as_of: date,
) -> tuple[IdentityModel, list[ModelUpdate]]:
    updates: list[ModelUpdate] = []
    new_interests: list[Interest] = []
    for i in model.interests:
        if i.id != interest_id:
            new_interests.append(i)
            continue
        system = "You rewrite topic strings concisely."
        prompt = (
            f"Rewrite this topic string to incorporate this refinement. "
            f"Keep it concise (under 8 words). Original: '{i.topic}'. "
            f"Refinement: '{instruction}'. Return only the rewritten topic string."
        )
        new_topic = llm.complete(system, prompt, max_tokens=30).strip().strip("'\"")
        before_topic = i.topic
        new_w = i.weight
        state = i.state
        last_rf = i.last_reinforced
        inactive_since = i.inactive_since
        if state in ("inactive", "dormant") or i.weight <= EPSILON_FLOOR:
            new_w = max(i.weight, 0.40)
            state = "active"
            last_rf = as_of
            inactive_since = None
        new_i = replace(
            i,
            topic=new_topic or i.topic,
            provenance="nuanced",
            weight=new_w,
            state=state,
            last_reinforced=last_rf,
            inactive_since=inactive_since,
        )
        new_interests.append(new_i)
        updates.append(
            ModelUpdate(
                timestamp=_now_ts(as_of),
                interest_id=i.id,
                update_type="nuance",
                field="topic",
                value_before=before_topic,
                value_after=new_i.topic,
                triggered_by="nuance",
            )
        )
    return replace(model, interests=new_interests, updated_at=as_of), updates
