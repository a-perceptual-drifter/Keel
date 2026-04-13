"""Build FetchContext with optional credentials from vault."""
from __future__ import annotations

from core.models import FetchContext


def build_session(vault=None, service: str | None = None) -> FetchContext:
    import requests
    sess = requests.Session()
    sess.headers.update({"User-Agent": "keel/0.1"})
    creds = None
    if vault is not None and service:
        try:
            creds = vault.get(service) or None
        except Exception:
            creds = None
    return FetchContext(session=sess, credentials=creds)
