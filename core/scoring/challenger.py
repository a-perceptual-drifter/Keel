"""Challenge classification. Pure function — LLM injected."""
from __future__ import annotations

from core.models import (
    CHALLENGE_SIMILARITY_MIN,
    FILTER_THRESHOLD,
    IdentityModel,
    LLMClient,
    ScoredArticle,
)

VALID = {"challenge", "confirm", "tangential", "neither"}

SYSTEM = (
    "You classify whether a piece of writing challenges or confirms a given topic. "
    "Answer with exactly one word: challenge / confirm / tangential / neither. "
    "IMPORTANT: If the content is not explicitly supportive of the topic's typical "
    "stance, or introduces conflicting data, evidence, or framing, classify it as "
    "'challenge'. Use 'tangential' for content related to the topic but not taking "
    "a position. Default to 'neither' only for purely factual or neutral reporting."
)


def _normalize(raw: str) -> str:
    if not raw:
        return "neither"
    word = raw.strip().lower().split()[0] if raw.strip().split() else ""
    word = word.strip(".,!?:;'\"")
    return word if word in VALID else "neither"


def classify_batch(
    candidates: list[ScoredArticle],
    identity: IdentityModel,
    llm: LLMClient,
) -> list[ScoredArticle]:
    interest_by_id = {i.id: i for i in identity.interests}
    results: list[ScoredArticle] = []
    for item in candidates:
        if not item.match_reason or item.interest_score < CHALLENGE_SIMILARITY_MIN:
            results.append(item)
            continue
        top = item.match_reason[0]
        interest = interest_by_id.get(top.topic_id)
        if not interest or interest.challenge_mode == "off":
            results.append(item)
            continue
        prompt = (
            f"Topic: {top.topic}\n"
            f"Title: {item.raw.title}\n"
            f"Summary: {(item.raw.content or '')[:400]}"
        )
        stance = _normalize(llm.complete(SYSTEM, prompt, max_tokens=10))
        new_item = item.with_stance(stance)
        if stance == "challenge":
            new_item.bucket = "challenge"
        elif new_item.bucket == "filter" and stance == "challenge":
            new_item.bucket = "challenge"
        results.append(new_item)
    return results
