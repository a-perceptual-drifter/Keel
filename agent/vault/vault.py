"""AES-256-GCM credentials vault via Fernet + PBKDF2HMAC."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path


class Vault:
    def __init__(self, path: str | Path, password: str):
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        salt_path = self.path.with_suffix(".salt")
        if salt_path.exists():
            salt = salt_path.read_bytes()
        else:
            salt = os.urandom(16)
            salt_path.write_bytes(salt)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self._fernet = Fernet(key)

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self._fernet.decrypt(self.path.read_bytes()).decode())
        except Exception:
            return {}

    def _save(self, data: dict) -> None:
        enc = self._fernet.encrypt(json.dumps(data).encode())
        self.path.write_bytes(enc)

    def add(self, service: str, key: str, value: str) -> None:
        data = self._load()
        data.setdefault(service, {})[key] = value
        self._save(data)

    def get(self, service: str) -> dict[str, str]:
        return dict(self._load().get(service, {}))

    def list(self) -> dict[str, list[str]]:
        return {s: list(keys) for s, keys in self._load().items()}

    def remove(self, service: str) -> None:
        data = self._load()
        data.pop(service, None)
        self._save(data)
