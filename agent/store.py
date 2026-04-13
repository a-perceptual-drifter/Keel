"""JsonStore — file-backed IdentityModelStore with atomic writes + filelock."""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from filelock import FileLock

from core.identity.model import from_dict, to_dict
from core.models import IdentityModel, MetaPreferences, PresentationPrefs


class JsonStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(str(self.path) + ".lock")

    def load(self, user_id: str = "") -> IdentityModel:
        if not self.path.exists():
            today = date.today()
            return IdentityModel(
                version="1.0",
                created_at=today,
                updated_at=today,
                interests=[],
                dismissals=[],
                anti_interests=[],
                presentation=PresentationPrefs(),
                meta=MetaPreferences(),
            )
        with self.path.open("r") as f:
            return from_dict(json.load(f))

    def save(self, model: IdentityModel, user_id: str = "") -> None:
        tmp = self.path.with_suffix(".tmp.json")
        tmp.write_text(json.dumps(to_dict(model), indent=2, default=str))
        os.replace(tmp, self.path)

    @contextmanager
    def lock(self, user_id: str = ""):
        with self._lock:
            yield
