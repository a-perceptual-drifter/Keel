from datetime import datetime

from core.models import MatchReason, RawItem, ScoredArticle
from core.scoring.challenger import classify_batch
from tests.mocks.llm import MockLLM


def _scored(title, topic_id="int_001", topic="local-first software", score=0.75):
    return ScoredArticle(
        raw=RawItem(
            id=title, source="rss", source_type="rss", title=title,
            url="https://x", content="body", published_at=None,
            fetched_at=datetime(2026, 4, 10),
        ),
        interest_score=score,
        bucket="filter",
        match_reason=[MatchReason(topic_id=topic_id, topic=topic, similarity=score)],
    )


def test_challenge_classification(sample_model):
    item = _scored("critique of local-first")
    llm = MockLLM(responses={"local-first": "challenge"})
    out = classify_batch([item], sample_model, llm)
    assert out[0].stance == "challenge"
    assert out[0].bucket == "challenge"


def test_normalization_fallback(sample_model):
    item = _scored("something")
    llm = MockLLM(default="Maybe yes???")
    out = classify_batch([item], sample_model, llm)
    assert out[0].stance == "neither"
