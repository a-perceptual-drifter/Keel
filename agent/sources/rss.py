"""RSS / Atom adapter via feedparser."""
from __future__ import annotations

from datetime import datetime
from time import mktime

from core.models import FetchContext, RawItem


class RSSSource:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url

    def fetch(self, context: FetchContext) -> list[RawItem]:
        import feedparser
        feed = feedparser.parse(self.url)
        now = datetime.now()
        out: list[RawItem] = []
        for e in feed.entries:
            published = None
            if getattr(e, "published_parsed", None):
                published = datetime.fromtimestamp(mktime(e.published_parsed))
            content = getattr(e, "summary", None) or ""
            if hasattr(e, "content") and e.content:
                content = e.content[0].get("value", content)
            out.append(
                RawItem(
                    id=e.get("id") or e.get("link") or e.get("title", ""),
                    source=self.name,
                    source_type="rss",
                    title=e.get("title", ""),
                    url=e.get("link", ""),
                    content=content,
                    published_at=published,
                    fetched_at=now,
                )
            )
        return out
