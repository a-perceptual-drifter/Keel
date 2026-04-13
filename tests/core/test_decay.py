from datetime import date, timedelta

from core.identity.updater import (
    apply_decay,
    apply_interaction,
    transition_states,
)
from core.models import EPSILON_FLOOR


def test_apply_decay_reduces_weight(sample_model):
    future = sample_model.updated_at + timedelta(days=30)
    new_model, updates = apply_decay(sample_model, future)
    weights_before = {i.id: i.weight for i in sample_model.interests}
    for i in new_model.interests:
        if i.decay_rate != "permanent":
            assert i.weight <= weights_before[i.id]
    assert any(u.update_type == "decay" for u in updates)


def test_floor_holds(sample_model):
    far = sample_model.updated_at + timedelta(days=1000)
    new_model, _ = apply_decay(sample_model, far)
    assert all(i.weight >= 0.10 - 1e-9 for i in new_model.interests)


def test_apply_interaction_engage(sample_model, today):
    new_model, updates = apply_interaction(sample_model, "int_001", "engage", today)
    before = next(i for i in sample_model.interests if i.id == "int_001")
    after = next(i for i in new_model.interests if i.id == "int_001")
    assert round(after.weight - before.weight, 4) == 0.03
    assert new_model.total_interactions == sample_model.total_interactions + 1


def test_interpreted_promotes_to_selected(sample_model, today):
    m = sample_model
    # two more engagements → 3rd triggers promotion
    m, _ = apply_interaction(m, "int_002", "engage", today)
    m, _ = apply_interaction(m, "int_002", "engage", today)
    m, _ = apply_interaction(m, "int_002", "engage", today)
    i2 = next(i for i in m.interests if i.id == "int_002")
    assert i2.provenance == "selected"


def test_state_transitions_dormant(sample_model, today):
    # Force weight to floor, keep lifetime_engagements ≥ 5
    from dataclasses import replace
    from core.models import IdentityModel
    i = sample_model.interests[0]
    i = replace(i, weight=0.10, lifetime_engagements=6)
    m = replace(sample_model, interests=[i] + sample_model.interests[1:])
    new_model, _ = transition_states(m, today)
    assert new_model.interests[0].state == "dormant"
