"""Hacker News Algolia API adapter."""
from __future__ import annotations

from datetime import datetime

from core.models import FetchContext, RawItem


class HNSource:
    name = "hn"

    def __init__(self, name: str = "hn", min_points: int = 100):
        self.name = name
        self.min_points = min_points

    def fetch(self, context: FetchContext) -> list[RawItem]:
        import requests
        sess = context.session or requests
        r = sess.get(
            "https://hn.algolia.com/api/v1/search",
            params={"tags": "front_page", "numericFilters": f"points>{self.min_points}"},
            timeout=30,
        )
        r.raise_for_status()
        now = datetime.now()
        out: list[RawItem] = []
        for hit in r.json().get("hits", []):
            out.append(
                RawItem(
                    id=f"hn:{hit['objectID']}",
                    source=self.name,
                    source_type="hn",
                    title=hit.get("title") or hit.get("story_title") or "",
                    url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}",
                    content=hit.get("story_text") or "",
                    published_at=datetime.fromtimestamp(hit.get("created_at_i", 0)) if hit.get("created_at_i") else None,
                    fetched_at=now,
                    external_score=int(hit.get("points", 0) or 0),
                )
            )
        return out
