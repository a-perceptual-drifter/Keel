from datetime import datetime

from core.models import RawItem
from core.scoring.scorer import score
from tests.mocks.embedder import MockEmbedder


def _raw(title: str, source="rss", content=""):
    return RawItem(
        id=title, source=source, source_type="rss",
        title=title, url=f"https://example/{title}",
        content=content, published_at=None, fetched_at=datetime(2026, 4, 10),
    )


def test_anti_interest_drops(sample_model):
    items = [_raw("crypto is cool"), _raw("local-first software is great")]
    results = score(items, sample_model, MockEmbedder())
    assert len(results) == 1
    assert "local-first" in results[0].raw.title


def test_buckets_assigned(sample_model):
    items = [_raw("local-first software deep dive", content="local-first software architecture")]
    results = score(items, sample_model, MockEmbedder())
    assert results[0].bucket in {"filter", "introduce", "none"}
    assert 0.0 <= results[0].interest_score <= 1.0


def test_match_reason_has_top_topics(sample_model):
    items = [_raw("climate adaptation planning")]
    results = score(items, sample_model, MockEmbedder())
    assert len(results[0].match_reason) >= 1
