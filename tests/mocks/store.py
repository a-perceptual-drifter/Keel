"""In-memory IdentityModelStore for tests."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from core.models import (
    IdentityModel,
    MetaPreferences,
    PresentationPrefs,
)


class InMemoryStore:
    def __init__(self, model: IdentityModel | None = None):
        today = date.today()
        self._model = model or IdentityModel(
            version="1.0",
            created_at=today,
            updated_at=today,
            interests=[],
            dismissals=[],
            anti_interests=[],
            presentation=PresentationPrefs(),
            meta=MetaPreferences(),
        )

    def load(self, user_id: str = "") -> IdentityModel:
        return self._model

    def save(self, model: IdentityModel, user_id: str = "") -> None:
        self._model = model

    @contextmanager
    def lock(self, user_id: str = ""):
        yield
