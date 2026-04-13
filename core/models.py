"""Data shapes and protocols for keel-core.

Pure dataclasses and Protocols only. No IO, no storage, no concrete
implementations. Application layer (`agent/`) injects all concrete deps.
"""
from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol

import numpy as np

# ---------- Identity model ----------


@dataclass
class Interest:
    id: str
    topic: str
    weight: float
    provenance: str              # interpreted | given | selected | chosen | nuanced | project
    decay_rate: str              # permanent | slow | medium | fast
    challenge_mode: str          # off | adjacent | friction
    state: str                   # active | dormant | inactive | discontinued | archived
    first_seen: date
    last_reinforced: date
    lifetime_engagements: int = 0
    inactive_since: date | None = None
    project_archived_at: date | None = None
    depth_score: float = 0.0


@dataclass
class Dismissal:
    type: str                    # article | thread | source
    target: str
    dismissed_at: date
    permanent: bool = False
    review_after: date | None = None
    resumed_at: date | None = None


@dataclass
class PresentationPrefs:
    default_resolution: str = "summary"       # micro | summary | synthesis | connection
    per_topic: dict[str, str] = field(default_factory=dict)
    max_items_per_surface: int = 8


@dataclass
class MetaPreferences:
    exploration_bias: float = 0.5
    depth_bias: float = 0.5
    stance_bias: float = 0.5
    inferred: bool = False
    last_updated: date | None = None


@dataclass
class IdentityModel:
    version: str
    created_at: date
    updated_at: date
    interests: list[Interest]
    dismissals: list[Dismissal]
    anti_interests: list[str]
    presentation: PresentationPrefs
    meta: MetaPreferences = field(default_factory=MetaPreferences)
    mood: str = "open"
    mood_set_at: datetime | None = None
    mood_inferred: bool = False
    exploration_end_at: date | None = None
    total_interactions: int = 0


# ---------- Articles / scoring ----------


@dataclass
class RawItem:
    id: str
    source: str
    source_type: str             # rss | hn | reddit | url
    title: str
    url: str
    content: str | None
    published_at: datetime | None
    fetched_at: datetime
    external_score: int = 0
    external_score_prev: int = 0


@dataclass
class MatchReason:
    topic_id: str
    topic: str
    similarity: float


@dataclass
class ScoredArticle:
    raw: RawItem
    interest_score: float
    bucket: str                  # filter | introduce | challenge | none
    match_reason: list[MatchReason]
    stance: str | None = None    # challenge | confirm | tangential | neither | None
    summary: str | None = None
    resolution: str | None = None

    def with_stance(self, stance: str) -> "ScoredArticle":
        from dataclasses import replace
        return replace(self, stance=stance)


@dataclass
class SourceStats:
    source: str
    score_mean: float
    score_stddev: float
    sample_count: int
    updated_at: datetime


# ---------- Audit + events ----------


@dataclass
class ModelUpdate:
    timestamp: datetime
    interest_id: str | None
    update_type: str             # reinforcement | decay | dismissal | nuance | ...
    field: str
    value_before: str | None
    value_after: str | None
    triggered_by: str | None = None
    article_id: int | None = None


@dataclass
class KeelEvent:
    type: str                    # new_message | task_start | task_complete | error
    payload: dict
    timestamp: datetime


# ---------- Transport ----------


@dataclass
class FetchContext:
    session: Any | None = None   # requests.Session in practice
    credentials: dict[str, str] | None = None


# ---------- Hardware ----------


@dataclass
class HardwareProfile:
    cpu_cores: int
    cpu_brand: str
    ram_gb: float
    gpu_vendor: str | None
    gpu_name: str | None
    gpu_vram_gb: float | None
    unified_memory: bool
    unified_memory_gb: float | None
    has_npu: bool
    cuda_available: bool
    rocm_available: bool
    mps_available: bool
    ollama_installed: bool
    ollama_version: str | None


# ---------- Protocols ----------


class LLMClient(Protocol):
    def complete(self, system: str, prompt: str, max_tokens: int = 80) -> str: ...


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[np.ndarray]: ...


class IdentityModelStore(Protocol):
    def load(self, user_id: str = "") -> IdentityModel: ...
    def save(self, model: IdentityModel, user_id: str = "") -> None: ...
    def lock(self, user_id: str = "") -> AbstractContextManager: ...


class FeedSource(Protocol):
    name: str
    def fetch(self, context: FetchContext) -> list[RawItem]: ...


class TaskStatus(Protocol):
    def write(self, task: str, status: dict) -> None: ...
    def read(self, task: str) -> dict | None: ...


# ---------- Constants ----------

ACTIVE_THRESHOLD = 0.70
EPSILON_FLOOR = 0.105
WEIGHT_FLOOR = 0.10
EXPLORATION_INTERACTIONS = 50
EXPLORATION_DAYS = 7
FILTER_THRESHOLD = 0.72
INTRODUCE_THRESHOLD = 0.55
CHALLENGE_SIMILARITY_MIN = 0.60
CONSOLIDATION_SIMILARITY = 0.82
MAX_ACTIVE_INTERESTS = 50
SATURATION_THRESHOLD = 0.85

HALF_LIFE_DAYS = {"permanent": None, "slow": 90, "medium": 30, "fast": 7}

REINFORCEMENT = {
    "engage": 0.03,
    "acknowledged": 0.0,
    "go_further": 0.10,
    "worth_it": 0.15,
    "correct": 0.05,
    "nuanced": 0.05,
    "silence": -0.02,
    "dismiss_article": -0.02,
    "dismiss_thread": -0.30,
    "regret": -0.15,
}
