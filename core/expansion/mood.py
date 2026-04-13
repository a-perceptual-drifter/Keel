"""Pure mood helpers. Thresholds and inference."""
from __future__ import annotations

from core.models import FILTER_THRESHOLD, INTRODUCE_THRESHOLD, IdentityModel

MOODS = {"open", "depth", "wander", "friction", "signal", "ambient"}


def apply_mood_thresholds(
    mood: str, base_filter: float = FILTER_THRESHOLD, base_introduce: float = INTRODUCE_THRESHOLD
) -> tuple[float, float]:
    """Return (filter_threshold, introduce_threshold) adjusted for mood."""
    if mood == "depth":
        return base_filter + 0.03, base_introduce + 0.05
    if mood == "wander":
        return base_filter - 0.05, base_introduce - 0.08
    if mood == "friction":
        return base_filter, base_introduce
    if mood == "signal":
        return base_filter + 0.05, base_introduce + 0.05
    if mood == "ambient":
        return base_filter + 0.02, base_introduce + 0.02
    return base_filter, base_introduce


def infer_mood(signals: dict) -> str:
    """Infer a mood from behavioral signals. Defaults to 'open'."""
    if signals.get("go_further_rate", 0) > 0.5:
        return "depth"
    if signals.get("dismiss_rate", 0) > 0.5:
        return "wander"
    if signals.get("engagement_rate", 0) < 0.1:
        return "ambient"
    return "open"
