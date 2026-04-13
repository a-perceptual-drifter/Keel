"""Arbitrary URL adapter via trafilatura."""
from __future__ import annotations

from datetime import datetime

from core.models import FetchContext, RawItem


class URLSource:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url

    def fetch(self, context: FetchContext) -> list[RawItem]:
        import trafilatura
        downloaded = trafilatura.fetch_url(self.url)
        if not downloaded:
            return []
        text = trafilatura.extract(downloaded) or ""
        return [
            RawItem(
                id=self.url,
                source=self.name,
                source_type="url",
                title=self.name,
                url=self.url,
                content=text,
                published_at=None,
                fetched_at=datetime.now(),
            )
        ]
