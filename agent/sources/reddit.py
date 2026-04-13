"""Reddit public-JSON adapter."""
from __future__ import annotations

import time
from datetime import datetime

from core.models import FetchContext, RawItem


class RedditSource:
    def __init__(self, name: str, subreddit: str, user_agent: str = "keel/0.1"):
        self.name = name
        self.subreddit = subreddit
        self.user_agent = user_agent

    def fetch(self, context: FetchContext) -> list[RawItem]:
        import requests
        sess = context.session or requests.Session()
        r = sess.get(
            f"https://www.reddit.com/r/{self.subreddit}/top.json?t=day&limit=25",
            headers={"User-Agent": self.user_agent},
            timeout=30,
        )
        time.sleep(1.0)
        r.raise_for_status()
        now = datetime.now()
        out: list[RawItem] = []
        for child in r.json().get("data", {}).get("children", []):
            d = child.get("data", {})
            out.append(
                RawItem(
                    id=f"reddit:{d.get('id')}",
                    source=self.name,
                    source_type="reddit",
                    title=d.get("title", ""),
                    url=d.get("url", ""),
                    content=d.get("selftext") or "",
                    published_at=datetime.fromtimestamp(d.get("created_utc", 0)) if d.get("created_utc") else None,
                    fetched_at=now,
                    external_score=int(d.get("ups", 0) or 0),
                )
            )
        return out
