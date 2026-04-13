"""Render scored items for surfacing. LLM-backed summaries optional."""
from __future__ import annotations

from core.models import ScoredArticle


def render_item(item: ScoredArticle, resolution: str = "summary", llm=None) -> str:
    title = item.raw.title
    url = item.raw.url
    if resolution == "micro":
        return f"• {title}\n  {url}"
    snippet = (item.raw.content or "")[:240].replace("\n", " ").strip()
    return f"• {title}\n  {url}\n  {snippet}"


def assemble_surface_message(
    items: list[ScoredArticle], mood: str = "open", llm=None
) -> str:
    if not items:
        return "→ Keel\n\nNothing new worth surfacing today."
    lines = [f"→ Keel ({mood})", ""]
    for it in items:
        lines.append(render_item(it))
        lines.append("")
    return "\n".join(lines).rstrip()
