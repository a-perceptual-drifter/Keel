"""pytest fixtures for core + agent tests."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.models import (  # noqa: E402
    IdentityModel,
    Interest,
    MetaPreferences,
    PresentationPrefs,
)


@pytest.fixture
def today():
    return date(2026, 4, 10)


@pytest.fixture
def sample_model(today):
    return IdentityModel(
        version="1.0",
        created_at=date(2026, 1, 1),
        updated_at=today,
        interests=[
            Interest(
                id="int_001",
                topic="local-first software",
                weight=0.60,
                provenance="given",
                decay_rate="medium",
                challenge_mode="adjacent",
                state="active",
                first_seen=date(2026, 1, 1),
                last_reinforced=today,
                lifetime_engagements=4,
            ),
            Interest(
                id="int_002",
                topic="climate adaptation",
                weight=0.45,
                provenance="interpreted",
                decay_rate="slow",
                challenge_mode="off",
                state="active",
                first_seen=date(2026, 2, 1),
                last_reinforced=date(2026, 3, 15),
                lifetime_engagements=2,
            ),
        ],
        dismissals=[],
        anti_interests=["crypto"],
        presentation=PresentationPrefs(),
        meta=MetaPreferences(),
    )
