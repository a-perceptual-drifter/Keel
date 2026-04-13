"""Render scored items for surfacing. LLM-backed summaries optional."""
from __future__ import annotations

from core.models import ScoredArticle


def _llm_summary(item: ScoredArticle, llm) -> str:
    body = (item.raw.content or "")[:1200].replace("\n", " ").strip()
    topic = item.match_reason[0].topic if item.match_reason else ""
    system = (
        "You write a single-sentence intro (≤ 22 words) that names why a reader "
        "interested in the given topic might care about the linked piece. "
        "If only the title is available, infer from it. Never ask for more context, "
        "never reference missing content, never use meta-commentary. "
        "Return only the sentence itself, no preamble."
    )
    prompt = f"Topic: {topic}\nTitle: {item.raw.title}"
    if body:
        prompt += f"\nExcerpt: {body}"
    try:
        out = llm.complete(system, prompt, max_tokens=60).strip()
        return out.split("\n")[0].strip(" -•")
    except Exception:
        return ""


def render_item(item: ScoredArticle, resolution: str = "summary", llm=None) -> str:
    title = item.raw.title
    url = item.raw.url
    if resolution == "micro":
        return f"• {title}\n  {url}"
    intro = ""
    if llm is not None:
        intro = _llm_summary(item, llm)
    if not intro:
        intro = (item.raw.content or "")[:240].replace("\n", " ").strip()
    tag = ""
    if item.stance == "challenge":
        tag = "  [challenge]"
    return f"• {title}{tag}\n  {url}\n  {intro}"


def assemble_surface_message(
    items: list[ScoredArticle], mood: str = "open", llm=None
) -> str:
    if not items:
        return "→ Keel\n\nNothing new worth surfacing today."
    lines = [f"→ Keel ({mood})", ""]
    for it in items:
        lines.append(render_item(it, llm=llm))
        lines.append("")
    return "\n".join(lines).rstrip()
