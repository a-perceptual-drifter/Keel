> **Historical design document.** This is the v1 spec Keel was built from. It may drift from the code as the implementation evolves — the source of truth is `core/` and `agent/`. Kept here for context on the design intent, reinforcement constants, and the `core/`-is-pure contract.

# Keel — Specification

---

## Instructions for Claude Code

**Read this section first. It defines how you operate, not just what you build.**

This is a fresh codebase. There is nothing to preserve, nothing to break, nothing to migrate. You have full freedom to implement, revise, and re-implement any part of the system until it works correctly.

---

### The Goal

Build a personal feed agent that a real person can run from zero. When they clone the repo and follow the README, they should be able to:

1. Run `keel --setup` and have the system detect their hardware, install everything it needs, and configure itself optimally — without them knowing which LLM to use or what batch size means
2. Run `keel --init` and have a natural conversation that builds their identity model and configures their sources
3. Run `keel --schedule` and start receiving a morning briefing that gets better over time
4. Interact with that briefing — engage, dismiss, refine, forget — and see their model respond
5. Run `keel --monitor` and see their system's health and feed quality at a glance
6. Know that everything is running locally and nothing is leaving their machine

That is the goal. Not "implement the checklist." The checklist exists to help you hit the goal. If you find a better way to hit the goal than what the spec describes, use it. If the spec is wrong about something, fix it. Document the deviation in `DEVIATIONS.md`.

---

### How to Operate

You work in a loop. The loop has four steps:

```
BUILD → TEST → MEASURE → FIX
  ↑                        ↓
  └────────────────────────┘
```

**BUILD** — implement the next logical unit of work. Follow the build order in the Implementation Guide. Build the smallest unit that can be tested independently.

**TEST** — run the relevant tests immediately after building. Do not accumulate untested code. The rule is: nothing moves forward with a failing test. Fix it before moving on.

**MEASURE** — after each major phase (core complete, agent tasks complete, e2e simulation passing), run the measurement commands to verify the system is behaving as intended, not just running without errors:

```bash
keel --dev --measure scoring-distribution
keel --dev --measure interest-health
keel --dev --measure drift
keel --dev --status
```

If the numbers don't look right — wrong bucket ratios, interests not moving, drift not detecting — that is a gap. Find it. Fix it.

**FIX** — when a gap is found, trace it to root cause, fix the implementation, re-run the test that caught it, then re-run all tests for that module. Never patch around a symptom. Fix the cause.

---

### Gap Identification

You will find gaps that aren't in the spec. That is expected. When you find one:

1. Write a test that fails because of the gap — before you fix it
2. Fix the implementation
3. Verify the test passes
4. Document the gap and fix in `DEFECTS.md`

Do not skip step 1. A gap without a test is a gap that will reappear.

**Signs of a gap:**

- A test passes but the system behaves incorrectly in the e2e simulation
- A `--measure` command returns numbers outside the expected ranges
- The 90-day simulation produces a model that hasn't changed meaningfully (interests all still at 0.70 after 90 days = decay not working)
- The surface is empty or always the same sources
- `--monitor` shows errors accumulating
- The LLM call in `--init` produces malformed JSON
- Silence, decay, or reinforcement aren't visibly moving weights

**How to trace a gap:**

```
1. Identify the symptom (what is wrong)
2. Find the last correct state (what should have happened)
3. Trace backward through the data flow:
   - Check the DB directly (sqlite3 store/dev/keel.db)
   - Check model_updates table (did the update get written?)
   - Check identity.json (did the update get applied?)
   - Check the task log (did the task run at all?)
4. Find the earliest point where actual state diverges from expected
5. That is where the bug is
```

---

### The E2E Simulation is the Truth Oracle

The spec describes intended behavior. The e2e simulation in the "E2E Simulation: Build Validation" section operationalises it. When you're unsure whether something is working correctly, run the simulation.

The simulation uses a concrete persona with specific interests, a fixed random seed, MockLLM and MockEmbedder, and fixture sources. Its assertions are precise. If an assertion fails, something is wrong in the implementation — not in the assertion.

**The simulation is the final arbiter.** If all simulation assertions pass and all `--measure` outputs are in range, the system is working. If not, it isn't, regardless of how clean the code looks.

---

### Phase Completion Criteria

You do not move to the next phase until the current phase is complete. A phase is complete when:

**Core complete:**
```bash
pytest tests/core/ -v --timeout=30
# 0 failed, 0 errors
```

**Agent tasks complete:**
```bash
pytest tests/agent/ -v --timeout=60
# 0 failed, 0 errors
keel --dev --task fetch
keel --dev --task score
keel --dev --task surface
# All run without errors, DB has expected rows
```

**E2E simulation passing:**
```bash
pytest tests/e2e/test_simulation.py -v -s --timeout=300
# 0 failed — all 7 phases pass
```

**Full system passing:**
```bash
pytest tests/ -v --timeout=300
keel --dev --fast-forward 90 2>&1 | grep -i "error\|exception\|traceback"
# 0 failed, no errors in 90-day run
keel --dev --status
keel --dev --model --snapshot | python -m json.tool
# Both produce valid, expected output
```

---

### Permissions

You have full permission to:

- Implement any part of the spec in whatever order makes sense after completing core
- Deviate from the spec's implementation details when you find a better approach — document it in `DEVIATIONS.md`
- Add helper functions, utilities, or abstractions the spec doesn't mention, as long as they don't violate the core boundary rule
- Refactor anything in the codebase at any time — it's fresh, there's nothing to protect
- Change the fixture content, test structure, or mock behavior if it makes tests more reliable
- Add config values the spec doesn't mention if a task needs them — document them
- Fail loudly — if something can't be implemented as specced, say so and propose an alternative rather than silently working around it

You do not have permission to:

- Import anything from `agent/` in `core/` — the boundary is absolute
- Write to the identity model from a core function — core returns, agent writes
- Make any network call from a test — all tests use mocks
- Add telemetry, analytics, or remote calls of any kind
- Proceed past a failing test without fixing it

---

### What "Done" Looks Like

The build is done when a person who has never heard of Keel can:

1. Clone the repo
2. Read the README and follow it without needing the spec
3. Run the three commands (`--setup`, `--init`, `--schedule`) and have a working agent
4. After 7 days, see their identity model has moved in response to their engagement
5. After 30 days, see a reflect message that correctly describes what happened
6. Run `--monitor` and understand the health of their system at a glance

Everything in the spec exists to make those six things true. When they're true, the system is done.

---

> Your account is your agent. It watches the world, reads for you, and surfaces what fits you — in your frame, at the right resolution, in the form you receive ideas best. All of it evolves over time.

---

## Thesis

Every AI agent being built today attaches to a company. The company's model, the company's interests, running on the company's servers. You get a surface. What's underneath belongs to them.

The right attachment point is the person.

One agent per account — where account means person, not platform. Your model, running in your space, serving your interests. Every platform you use becomes a source. Your agent scores and ranks what reaches you. The platform's algorithm no longer touches that step.

This is a small architectural change. The model's home moves from institution to person. Everything downstream of that is different.

Keel is the infrastructure for that shift. A core library, a personal agent, and a feed service — built so the personal agent and the service share the same model and the same principles. Platforms that integrate with Keel don't get your data. They get your agent's verdict on theirs.

---

## Architecture Overview

Keel is three things built as one:

**`keel-core`** — a Python library. No orchestration responsibility — no scheduling, no UI, no decisions about when things run. Core depends on external models (LLM, embedder) but never owns the runtime context that provides them. Applications inject those dependencies. Pure computation from the outside in: identity model, scoring, embedding, challenge classification, source adapters, vault. Published as a package. Everything else depends on it.

**`keel-agent`** — a personal application built on core. Runs on your machine, for you. Conversational thread, scheduler, reflect task, CLI. One user, full sovereignty.

**`keel-service`** — a feed service built on core. REST API, multi-user, self-hostable. Platforms and feed generators call it to score content through a user's identity model instead of their own algorithm.

These are not the same application configured differently. They are different applications that share a library. Core never knows which application is using it.

```
keel/
├── core/                   # keel-core — library, no orchestration responsibility
│   ├── identity/
│   │   ├── model.py        # IdentityModel serialization (to_dict, from_dict) — pure
│   │   ├── store.py        # IdentityModelStore protocol — contract only, no implementations
│   │   └── updater.py      # Pure functions: apply_decay, apply_interaction,
│   │                       #   transition_states, nuance_interest
│   ├── sources/
│   │   └── protocol.py     # FeedSource protocol + FetchContext + RawItem — contracts only
│   ├── scoring/
│   │   ├── embedder.py     # Embedder protocol — contract only, no implementations
│   │   ├── scorer.py       # Pure function: score(items, identity, embedder) → ScoredItems
│   │   └── challenger.py   # classify_batch() — takes injected LLMClient, no side effects
│   ├── expansion/
│   │   ├── expander.py     # Pure functions: find_edge_candidates(), score_world_signal()
│   │   └── mood.py         # Pure functions: apply_mood_thresholds(), infer_mood()
│   └── models.py           # All data shapes: RawItem, ScoredArticle, Interest, IdentityModel,
│                           #   FetchContext, KeelEvent, ModelUpdate, etc.
├── agent/                  # keel-agent — orchestration, IO, storage, user interaction
│   ├── setup/              # hardware detection and first-run setup
│   │   ├── detect.py       # HardwareProfile detection (CPU, GPU, NPU, Ollama)
│   │   ├── installer.py    # dependency install, Ollama install, model pull
│   │   └── benchmark.py    # throughput measurement → config optimisation
│   ├── llm.py              # LLMClient implementations: OllamaLLM, AnthropicLLM, OpenAILLM
│   ├── embedders.py        # Embedder implementations: OllamaEmbedder, SentenceTransformerEmbedder
│   ├── store.py            # JsonStore — implements IdentityModelStore protocol (file IO)
│   ├── ledger.py           # Audit log write/read — DB IO, implements ledger contract
│   ├── resources.py        # OllamaResourceManager — priority lock for shared VRAM
│   ├── scheduler.py        # APScheduler setup, misfire config, task registration
│   ├── sources/            # Source adapters — never imported by core
│   │   ├── rss.py          # RSS/Atom adapter
│   │   ├── hn.py           # Hacker News adapter (two-pass)
│   │   ├── reddit.py       # Reddit adapter (two-pass)
│   │   └── url.py          # Arbitrary URL adapter
│   ├── vault/              # Credentials — never imported by core
│   │   ├── vault.py        # Encrypted credential store (AES-256-GCM)
│   │   └── session.py      # build_session() → FetchContext with credentials injected
│   ├── tasks/
│   │   ├── fetch.py        # Fetch + deduplicate + store
│   │   ├── score.py        # Score + challenge-classify new items
│   │   ├── silence.py      # Daily: record silence for un-interacted surfaced items
│   │   ├── surface.py      # Select + render + write to thread
│   │   └── reflect.py      # Weekly: decay, drift signals, summary message
│   ├── surface/
│   │   ├── thread.py       # Read/write conversational thread; KeelEvent bus
│   │   ├── renderer.py     # Render ScoredArticle at chosen resolution via LLM
│   │   └── cli.py          # readline REPL with polling loop for new thread messages
│   └── init.py             # Cold start conversation; identity model seeding
├── service/                # keel-service — feed service application
│   ├── api/
│   │   ├── app.py          # FastAPI app
│   │   ├── routes/
│   │   │   ├── users.py    # User management, API keys
│   │   │   ├── identity.py # Identity model CRUD
│   │   │   ├── score.py    # Scoring API endpoint
│   │   │   ├── feed.py     # Feed API endpoint
│   │   │   ├── interact.py # Interaction recording
│   │   │   └── thread.py   # Conversational thread + WebSocket
│   │   └── auth.py         # API key validation
│   ├── workers/
│   │   ├── fetcher.py      # Global source pool fetch worker
│   │   ├── scorer.py       # Per-user scoring worker (queued)
│   │   └── challenger.py   # Async challenge classification worker pool
│   └── store/
│       └── db.py           # SqliteStore + service-level schema
├── store/                  # Runtime data (agent)
│   ├── keel.db
│   ├── identity.json
│   └── vault.enc
├── config/
│   ├── config.yaml         # main config: LLM, scoring thresholds, scheduler
│   ├── preferences.yaml    # user preferences — generated during onboarding, editable
│   └── sources.yaml        # feed sources — generated during onboarding, editable
└── run.py                  # CLI entry point for agent
```

---

## keel-core

### Identity Model

`IdentityModel` is a pure data class — no storage, no IO.

```python
@dataclass
class Interest:
    id: str
    topic: str
    weight: float                   # 0.0 – 1.0, floored at 0.10
    provenance: str                 # interpreted | given | selected | chosen | nuanced | project
    decay_rate: str                 # permanent | slow | medium | fast
    challenge_mode: str             # off | adjacent | friction
    state: str                      # active | dormant | inactive | discontinued | archived
    first_seen: date
    last_reinforced: date
    lifetime_engagements: int = 0   # total engagement count across all time
    inactive_since: date | None = None
    project_archived_at: date | None = None  # set when project interest is archived

@dataclass
class Dismissal:
    type: str                       # article | thread | source
    target: str                     # topic string or source name
    dismissed_at: date
    permanent: bool
    review_after: date | None = None
    resumed_at: date | None = None  # set when source resumes; bucket cap active for 14 days after

@dataclass
class MetaPreferences:
    """
    Persistent cognitive style preferences. Slower-moving than mood.
    Mood is session-level (hours). MetaPreferences are identity-level (months).
    These shape how the agent weights and explores — not what it shows, but how it thinks.
    """
    exploration_bias: float = 0.5     # 0.0 = optimizer (show me what I know I like)
                                      # 1.0 = explorer (surprise me, push edges)
    depth_bias: float = 0.5           # 0.0 = novelty-seeker (breadth, new topics)
                                      # 1.0 = depth-seeker (go deeper in known threads)
    stance_bias: float = 0.5          # 0.0 = confirmer (prefer content that aligns)
                                      # 1.0 = contrarian (prefer content that challenges)
    inferred: bool = False            # whether current values were inferred or explicitly set
    last_updated: date | None = None

@dataclass
class IdentityModel:
    version: str
    created_at: date
    updated_at: date
    interests: list[Interest]
    dismissals: list[Dismissal]
    anti_interests: list[str]       # keyword blacklist, case-insensitive substring match
    presentation: PresentationPrefs # default_resolution, per_topic, max_items_per_surface
    meta: MetaPreferences = field(default_factory=MetaPreferences)
    mood: str = "open"              # open | depth | wander | friction | signal | ambient
    mood_set_at: datetime | None = None
    mood_inferred: bool = False
    exploration_end_at: date | None = None  # set when exploration period ends; None if still active
    total_interactions: int = 0     # running count; triggers exploration end at 50
```

### IdentityModelStore Protocol

Core defines the interface. Applications provide the implementation.

```python
class IdentityModelStore(Protocol):
    def load(self, user_id: str) -> IdentityModel: ...
    def save(self, user_id: str, model: IdentityModel) -> None: ...
    def lock(self, user_id: str) -> ContextManager: ...
```

Two implementations — both live in the application layer, not in core:

**`JsonStore`** — `agent/store.py`. Reads/writes `identity.json`. File locking via `filelock`. Single user, `user_id` ignored.

**Atomic write pattern** — `identity.json` must never be overwritten in-place. A crash or power loss mid-write produces a corrupted file with no recovery path. The save method writes to `identity.tmp.json` first, then uses `os.replace()` which is atomic at the filesystem level (rename syscall on POSIX):

```python
def save(self, user_id: str, model: IdentityModel) -> None:
    tmp_path = self.path.with_suffix(".tmp.json")
    tmp_path.write_text(json.dumps(model.to_dict(), indent=2))
    os.replace(tmp_path, self.path)  # atomic on POSIX
```

If the process crashes before `os.replace()`, `identity.tmp.json` is left on disk and `identity.json` is intact. Startup reconciliation detects orphaned `model_updates` rows and re-applies them to the intact file. If the process crashes after `os.replace()`, the write completed cleanly. `identity.tmp.json` left on disk at startup is safe to delete — it indicates a previous clean write.

**`SqliteStore`** — `service/store/db.py`. Per-user rows. Row-level locking via SQLite WAL mode. Phase 2.

**Write-ahead contract for agent (JSON + SQLite split-brain prevention)**

`identity.json` and `model_updates` (SQLite) are two separate storage systems. They cannot be wrapped in a single atomic transaction. Over time, power loss or DB lock contention can cause them to drift — `identity.json` updated but audit row not written, or vice versa. The write-ahead contract prevents divergence:

```
1. Write model_updates row to SQLite FIRST (inside a DB transaction)
2. Only if that succeeds: write identity.json
3. If JSON write fails: log the orphaned model_updates row ID
4. On next startup: reconciliation check runs before any tasks
```

**`value_after` stores the full serialized Interest object, not just the changed field.** When a `model_updates` row has `field = "_interest"`, `value_after` contains the complete JSON of the Interest after the update. This makes startup reconciliation an atomic object replacement — load the row, deserialize `value_after`, replace the matching interest in the model by ID. No fragile multi-step math, no type-casting reconstruction. For model-level changes (mood, anti-interests), `field` names the specific field and `value_after` stores the new scalar value.

**Startup reconciliation** — `run.py` checks for orphaned `model_updates` rows on every startup: rows where `triggered_by` is set but `identity.json` weight doesn't reflect the `value_after`. If found, re-apply the update to `identity.json` before starting the scheduler. Log each re-application. This ensures JSON and SQLite converge on every startup even after crashes.

```python
# agent/init.py — startup reconciliation (runs before scheduler)
def reconcile_identity(db: sqlite_utils.Database, store: JsonStore) -> None:
    """Re-apply any model_updates rows not reflected in identity.json."""
    model = store.load()
    orphans = find_orphaned_updates(db, model)
    if orphans:
        logger.warning("Reconciling %d orphaned model updates", len(orphans))
        for update in orphans:
            model = reapply_update(model, update)
        store.save(model)
        logger.info("Reconciliation complete")
```

**Atomic update contract** — every task that modifies the identity model must follow this pattern without exception:

```python
with store.lock(user_id):
    model = store.load(user_id)
    updated_model = apply_something(model, ...)
    store.save(user_id, updated_model)
```

The atomic unit of identity change is: lock → load → modify → save → release. No partial writes. No reading outside the lock and writing back later. Tasks that don't modify the identity model (fetch, score writing to DB) do not need the lock. Tasks that do (silence, interaction handling) always use it.

**Exception — fetch acquires lock briefly for source resumption.** Dismissal records live inside `identity.json`. When the fetch task detects an expired source dismissal (`review_after < today`), it must acquire the identity lock briefly to update `resumed_at` before proceeding with network requests. This is the only case where fetch touches the identity model. The lock is held for the minimum duration: load → set `resumed_at` → save → release. No fetch network activity happens while the lock is held.

```python
# In fetch task — source resumption only
expired_dismissals = [d for d in model.dismissals
                      if d.type == "source" and d.review_after and d.review_after < today]
if expired_dismissals:
    with store.lock(""):
        model = store.load()
        for d in expired_dismissals:
            d.resumed_at = today  # bucket cap active for 14 days
        store.save(model)
# Now proceed with network requests for resumed sources
```

**Exception — reflect Phase 1 acquires lock.** Documented separately above.

**LLM calls must never happen while the identity lock is held.** This is a hard rule. Reflect Phase 2 (LLM calls) runs with lock released. No other task calls the LLM while holding the lock.

### Interest Decay

Applied by calling `apply_decay(model, as_of_date)` — pure function, returns `(new_model, updates)` where `updates` is a `list[ModelUpdate]`. The agent writes `updates` to the audit log via `agent/ledger.py` before saving the new model (write-ahead contract). Same return pattern for all updater functions that modify the model: `apply_decay`, `apply_interaction`, `transition_states`, `nuance_interest` all return `tuple[IdentityModel, list[ModelUpdate]]`.

| Rate | Half-life | Use for |
|------|-----------|---------|
| `permanent` | Never decays | Standing interests you always want |
| `slow` | 90 days | Active threads with long horizons |
| `medium` | 30 days | Current preoccupations |
| `fast` | 7 days | Temporary curiosity spikes |

Formula: `new_weight = max(0.10, weight * (0.5 ^ (days_since_reinforced / half_life)))`

**Floating point floor detection**: `weight == 0.10` is unreliable due to floating point arithmetic. Use `weight <= 0.105` as the floor detection condition throughout — in state transitions, inactive_since tracking, and drift detection. The floor is still enforced at exactly `0.10` via `max(0.10, ...)` in the decay formula; the epsilon band is only for detecting whether a weight has reached the floor, not for setting it.

### Graded Reinforcement

Not all engagement is equal. The current interaction types map to distinct reinforcement weights:

| Interaction | Weight effect | Resets `last_reinforced` |
|-------------|--------------|--------------------------|
| `engage` (read/skim) | `+0.03` | Yes |
| `acknowledged` | none | Yes — resets decay clock only |
| `go_further` | `+0.10` | Yes |
| `worth_it` | `+0.15` | Yes |
| `correct` / `nuanced` | `+0.05`, provenance → `nuanced` | Yes |
| `challenge_set` | none | Yes |
| `mood_set` | none | No |
| `silence` | `-0.02`, capped at 3× per item | No |
| `dismiss` (article) | `-0.02` | No |
| `dismiss` (thread) | `-0.30` | No |
| `regret` | `-0.15`, flags item for scoring calibration | No |
| `discontinuity` | removes from active model | — |

**`acknowledged`** — for contemplative reading. Triggered by: *"noted"*, *"read this"*, *"seen it"*, *"read"*. Resets `last_reinforced` to today without changing weight. The interest does not grow, but the decay clock resets — the system treats it as "user is still engaged with this topic, just quietly." Prevents the negative drift that accumulates on interests the user processes silently over weeks without explicit engagement commands. This is the explicit tool for heavy readers who rarely type responses.

**`worth_it`** — delayed satisfaction signal. Triggered 24h after surfacing by the agent asking: *"Anything from yesterday worth noting?"* If the user explicitly says "that AI safety piece was worth it" or similar, the matched item gets a `worth_it` interaction. This is stronger than `go_further` (which means "show me more") — it means "I'm glad this reached me." The 24h delay is intentional: it captures whether the item had lasting value, not just immediate appeal.

**`regret`** — the inverse. "Shouldn't have shown me that." Applied via: *"that piece was a waste of time"* or *"don't show me things like that."* Stronger than `dismiss` — it signals that not only was this item wrong, the scoring that produced it was miscalibrated. `regret` events are stored in `interactions` with the article ID and feed back into threshold calibration in reflect: if an interest accumulates 3+ regret events in 30 days, the reflect task flags it as a miscalibration candidate and suggests lowering that interest's weight manually.

**`--show-below-threshold` connects to learning.** When the user runs `--show-below-threshold` and explicitly engages with an item shown there, it is recorded as a `worth_it` interaction on that item AND a `threshold_miss` event on the scoring config. If `threshold_miss` events exceed 5 in 14 days, the reflect task suggests lowering `filter_threshold` by 0.02.

**Interest saturation.** Once an interest reaches `weight >= 0.85`, continued engagement has diminishing returns epistemically. The user already demonstrates deep investment. What they need is not more of the same — it's the frontier of that interest. Saturation behavior:

- The surface task reduces the maximum items surfaced for a saturated interest from 3 to 1 per surface cycle
- The freed slots are reallocated to edge items in that interest's semantic neighborhood (`similarity 0.40–0.54`)
- The interest's `challenge_mode` is automatically promoted one level for surface selection: `off → adjacent`, `adjacent → friction`
- The promotion is temporary and surface-only — it does not modify `interest.challenge_mode` in the identity model (no write to identity)
- If the user explicitly set `challenge_mode: off`, saturation does not override it

Saturation threshold is configurable:
```yaml
active_interest_threshold: 0.70
interest_saturation_threshold: 0.85   # above this, surface behavior shifts
```

The saturation principle: **high confidence in what you know should open more space for what you don't, not less.** The system must resist the pull toward serving what it knows works.

**`apply_interaction()` increments `total_interactions` and checks the exploration threshold.** Every call to `apply_interaction()` in `updater.py` increments `model.total_interactions` by 1. After incrementing, if `model.exploration_end_at is None` and `model.total_interactions >= 50`, it sets `model.exploration_end_at = as_of` immediately. This triggers the momentum blending on the very next surface cycle — no dependency on the weekly reflect task. The 7-day time-based check runs in the surface task at surface time and sets `exploration_end_at` if the date threshold is hit before the interaction count.

```python
# In apply_interaction() — runs after all weight updates
model = replace(model, total_interactions=model.total_interactions + 1)
if model.exploration_end_at is None and model.total_interactions >= EXPLORATION_INTERACTIONS:
    model = replace(model, exploration_end_at=as_of)
    logger.info("Exploration period ended by interaction count (%d)", model.total_interactions)
```

**Provenance promotion logic** — `interpreted` interests (inferred by the agent from behavior) are hypothetical until validated. If a user engages with an `interpreted` interest 3 or more times (cumulative `lifetime_engagements >= 3`), its provenance automatically promotes to `selected`. This moves the topic from hypothetical to validated, which has two effects: it protects the interest from the `Active → Inactive` transition for one additional reflect cycle (equivalent to 7 extra days), and it signals to the model that the inferred topic was correct. The promotion is recorded in `model_updates` with `update_type: "provenance_promotion"`, `value_before: "interpreted"`, `value_after: "selected"`.

**`nuance_interest(interest_id, instruction, llm)`** — called when the user refines a topic. Defined in `core/identity/updater.py`:

```python
def nuance_interest(
    model: IdentityModel,
    interest_id: str,
    instruction: str,
    llm,
    as_of: date,
) -> tuple[IdentityModel, list[ModelUpdate]]:
    """
    Rewrite a topic string based on user instruction.
    Preserves interest ID. Triggers re-hash (new topic string changes hash).
    Returns new model and audit entries.

    Example: instruction = "specifically for mobile, not desktop"
    Old topic: "local-first software"
    New topic: "local-first software for mobile"
    """
```

The LLM call prompt: `"Rewrite this topic string to incorporate this refinement. Keep it concise (under 8 words). Original: '{topic}'. Refinement: '{instruction}'. Return only the rewritten topic string."` The rewritten string replaces `interest.topic`. The `id` is preserved. `provenance` is updated to `nuanced`. After the model is saved, only this interest's embedding cache entry is invalidated — not all interests. The per-interest hash for this `interest.id` will differ on next scoring run, triggering re-embedding of just this one topic.

**Nuance reactivates inactive and dormant interests.** A nuance interaction is an explicit user intent — the user is actively engaging with the topic. If the interest is `state == "inactive"` or `state == "dormant"` with `weight <= 0.105`, `nuance_interest()` must:
- Reset `weight = max(current_weight, 0.40)` — brings it back above the introduce threshold
- Set `state = "active"`
- Set `last_reinforced = today`
- Clear `inactive_since`

Without this, a user's explicit refinement of a dormant topic would still be ignored by the scorer — it would remain at 0.10 weight and excluded from scoring. The nuance interaction counts as a strong engagement signal regardless of current state.

**Audit trail for nuance**: the `model_updates` entry for a nuance call must store the human-readable topic strings in `value_before` and `value_after`, not just the interest ID. The explanatory narrative tier (Tier 4 legibility) needs to show the semantic shift — "changed from 'local-first software' to 'local-first software for mobile'" — not just "interest int_dev_002 was updated." IDs are meaningless to the user reading an audit entry.

### Inactive and Dormant Interests

Interests exist in one of four states:

| State | Condition | Scoring | Edge influence |
|-------|-----------|---------|----------------|
| **Active** | weight > 0.10, not inactive | Yes | Yes |
| **Dormant** | weight ≤ 0.10, strong historical reinforcement (≥ 5 lifetime engagements) | No | Yes — still pulls edge expansion toward its semantic neighborhood |
| **Inactive** | weight ≤ 0.10, weak historical reinforcement (< 5 lifetime engagements), 3+ consecutive reflect cycles at floor | No | No |
| **Archived** | Project interest explicitly archived by user | No | Yes — preserved like dormant; shapes edges without surfacing new content |
| **Discontinued** | Explicitly removed via `--forget` or discontinuity interaction | No | No — removed from model entirely |

The dormant state is the key addition. Human attention doesn't decay smoothly — important interests go dormant, not weak. They resurge via indirect association, triggered by something adjacent rather than direct engagement. Dormant interests don't participate in scoring but they do influence which edge topics get probed. An interest that has been deeply reinforced over time should not lose its gravity on the model's perimeter just because it hasn't been recently engaged.

### Identity Consolidation

**The identity model is bounded.** Without a hard cap and a consolidation mechanism, interests accumulate indefinitely as separate semantic vectors. A user who reads about AI for six months ends up with "AI safety," "AI alignment," "AI philosophy," "AI product design," and "AI startups" as five independent vectors — none strong enough to decay, all pulling the surface in slightly different directions. The model becomes vector soup.

**Active interest cap: 50.** If `apply_interaction()` would create a new interest that pushes the active count above 50, the proposed interest is returned as a suggestion rather than written automatically. The agent informs the user:

```
→ Keel

You have 50 active interests — the model's working limit.
I'd like to add "AI product design" but need to make room.

Lowest-weight active interests:
  • "startup recruiting" (0.12) — last engaged 47 days ago
  • "web3 governance" (0.11) — last engaged 62 days ago

Say "drop [topic]" to make space, or "skip" to not add the new one.
```

The user decides. The agent never silently discards an interest the user might want.

**Similarity consolidation in reflect.** The weekly reflect task checks for semantic overlap among active interests. If two active interests have embedding similarity ≥ 0.82, they are flagged as consolidation candidates in the reflect message:

```
→ Keel (weekly reflect)

I noticed two interests that may be covering the same ground:
  • "AI safety" (weight 0.74)
  • "AI alignment doom" (weight 0.61)
  Similarity: 0.87

Consider merging them into a single interest. Say:
  "merge AI safety and AI alignment doom into AI existential risk"
Or keep them separate if the distinction matters to you.
```

The agent never merges without confirmation. Consolidation is a suggestion, not an action. The merge combines weights (capped at 0.90), inherits the higher `lifetime_engagements`, and sets `provenance: nuanced`.

```yaml
identity:
  max_active_interests: 50
  consolidation_similarity_threshold: 0.82  # interests above this flagged for merge
```

The reflect task determines state transitions:
- Active → Dormant: weight hits floor AND lifetime engagements ≥ 5
- Active → Inactive: weight hits floor AND lifetime engagements < 5, sustained for 3 cycles
- Dormant → Active: any engagement or explicit statement resets weight to 0.40, `last_reinforced` to today
- Inactive → Active: explicit user reactivation only

**"At floor"** means `weight == 0.10` after decay has been applied by the reflect task — not approaching floor, exactly at it. **"3 consecutive cycles"** means 3 consecutive Sunday reflect runs where the condition is still met. If a cycle is missed (machine off, misfire beyond grace period), it does not count against the 3. Cycles are tracked via `inactive_since`: set on first floor-hit, cleared on any engagement, transition to inactive when `(today - inactive_since).days >= 21` (3 × 7-day reflect interval).

Add `state: Literal["active", "dormant", "inactive", "discontinued"]` and `lifetime_engagements: int` to the `Interest` dataclass.

**Thread depth tracking.** `lifetime_engagements` counts total touches but doesn't distinguish between a thread being grazed repeatedly at the surface and one being actively deepened. A user who skims 40 AI headlines has high `lifetime_engagements` on their AI interest but hasn't gone deep. A user who read three long pieces, went further on two of them, and got a `worth_it` on one has done something qualitatively different with lower engagement count.

Add `depth_score: float = 0.0` to the `Interest` dataclass. Computed as:

```
depth_score = (go_further_count * 0.4) + (worth_it_count * 0.5) + (nuance_count * 0.3)
             normalised to 0–1 by dividing by a ceiling of 10
```

`depth_score` is updated by `apply_interaction()` whenever a `go_further`, `worth_it`, or `nuanced` interaction is recorded for that interest.

**Depth vs novelty signal in reflect.** The reflect task computes per-interest `depth_score` trend over 4 weeks. Interests with rising `depth_score` are deepening. Interests with high `lifetime_engagements` but flat `depth_score` are being grazed. The reflect narrative receives this:

```json
"thread_depth": [
  {"topic": "AI self-awareness", "depth_score": 0.72, "trend": "rising", "characterisation": "deepening"},
  {"topic": "startup culture", "depth_score": 0.08, "trend": "flat", "characterisation": "grazing"},
]
```

If the system detects that all interests have flat `depth_score` for 3+ weeks (the user is reading broadly but not going deep on anything), the reflect message asks: *"You've been covering a lot of ground lately. Is there a thread you'd like to go deeper on?"*

`depth_score` is readable via `--model` and visible in the `--measure interest-health` report.

**Grace period for new interests**: interests added within the last 14 days are exempt from the `Active → Inactive` state transition, regardless of weight. Fast decay interests (`decay_rate: fast`) can hit the floor quickly — a week-old interest shouldn't be marked inactive just because it faded before accumulating engagement. Add `created_at: date` to the `Interest` dataclass (already present as `first_seen`). The transition check in `transition_states()` should skip interests where `(as_of - interest.first_seen).days < 14`.

### MetaPreferences

The `MetaPreferences` object captures cognitive style at the identity level — slower-moving than mood (hours), slower than interests (weeks), on the timescale of months. Mood is how the user feels today. MetaPreferences are who the user is as a reader.

Without explicit modeling, cognitive style emerges accidentally from threshold values and mood cycling. Two users with identical interests but different cognitive styles should get meaningfully different feeds. MetaPreferences make that explicit.

**Three dimensions:**

| Dimension | Low (0.0) | High (1.0) | Default |
|-----------|-----------|-----------|---------|
| `exploration_bias` | Optimizer — show me what I know I like | Explorer — surprise me, push edges | 0.5 |
| `depth_bias` | Novelty-seeker — breadth, new topics | Depth-seeker — go deeper in known threads | 0.5 |
| `stance_bias` | Confirmer — prefer content that aligns | Contrarian — prefer content that challenges | 0.5 |

**How they affect scoring:**

- `exploration_bias` scales the effective `exploration_budget_pct`. At 0.0: budget is `base * 0.5`. At 1.0: budget is `base * 1.5`. A pure optimizer gets half the edge/foreign items; a pure explorer gets 50% more.
- `depth_bias` scales `go_further` reinforcement weight. At 1.0: `go_further` is worth `+0.15` instead of `+0.10`. At 0.0: `engage` is worth `+0.05` instead of `+0.03` (breadth engagement rewarded more). Deep readers get stronger signal from depth; novelty-seekers get more signal from skimming across many items.
- `stance_bias` scales the default `challenge_mode` on newly created interests. At 1.0: new interests default to `challenge_mode: friction`. At 0.0: new interests default to `challenge_mode: off`. The user's existing interests retain their set `challenge_mode` — this only affects defaults for new interests.

**How they're set explicitly:**

```
> I prefer to go deep on fewer topics
> I'd rather be challenged than confirmed
> show me more surprising things
```

The agent maps these to dimension adjustments and confirms:

```
→ Keel

Updating your cognitive style:
  depth_bias: 0.5 → 0.80  (deeper focus on active threads)
  stance_bias: 0.5 → 0.75  (more challenge-oriented by default)
```

**How they're inferred:**

The reflect task infers `MetaPreferences` from behavioral patterns over 8+ weeks:

- `exploration_bias` inferred from: engagement rate on edge items vs filter items. If edge engagement > 40% of total, exploration_bias nudges toward 1.0.
- `depth_bias` inferred from: ratio of `go_further` to `engage` interactions. High `go_further` rate nudges depth_bias toward 1.0.
- `stance_bias` inferred from: challenge item engagement vs dismissal rate. High challenge engagement nudges stance_bias toward 1.0.

Inference only updates when `inferred: true` (user hasn't set explicitly). If the user has set a dimension, inference never overwrites it. Inferred updates are small (±0.05 per reflect cycle) and only after 8+ weeks of data.

The reflect message surfaces a meta-preference insight when a dimension moves meaningfully:

```
→ Keel (weekly reflect)

Your reading pattern suggests you're more depth-oriented than your current setting.
  depth_bias current: 0.50 → suggested: 0.68

Say "update my depth preference" to apply, or ignore to keep current.
```

**Visible in `--model`:**

```
Cognitive style (meta-preferences):
  exploration_bias: 0.72  [explorer]     (inferred)
  depth_bias:       0.80  [depth-seeker] (set by you)
  stance_bias:      0.50  [balanced]     (inferred)
```

```yaml
meta_preferences:
  inference_enabled: true
  inference_min_weeks: 8        # don't infer until 8 weeks of data
  inference_step: 0.05          # max change per reflect cycle
```

### Project Provenance

A project is a distinct kind of interest: bounded in time, high intensity during active work, should not decay while active, should archive cleanly when done rather than fade into dormancy.

The five standard provenance modes don't handle this well. A project interest set as `permanent` never fades even after completion. Set as `slow` it lingers for months after the project ends. Neither is right.

`provenance: project` adds a sixth mode with its own lifecycle:

| State | Condition | Behavior |
|-------|-----------|---------|
| **Active** | Project is ongoing | `decay_rate` overridden to `permanent` — no decay while active |
| **Archived** | User archives the project | Weight frozen at archive value; excluded from scoring; preserved in model; still influences edge expansion (dormant-like) |
| **Discontinued** | User explicitly forgets it | Removed completely, same as standard discontinuity |

```bash
keel --archive-project --topic "int_001"     # Archive by ID
keel --archive-project --topic "Q3 report"   # Archive by topic match
```

In chat:
```
> archive this project
> done with Q3 report
```

The agent confirms and archives:
```
→ Keel
"Q3 report" archived. Weight frozen at 0.74.
It won't surface new content, but it still shapes your edges.
Say "forget Q3 report" to remove it entirely.
```

**What archiving does**:
- Sets `state = "archived"`, `project_archived_at = today`
- Excludes from scoring (no new items surface for it)
- Preserves in `thread_items` (unlike discontinuity — archived projects still influence edge adjacency)
- No decay applied
- Visible in `--model` under a separate "archived projects" section
- Reactivatable: `"resume Q3 report"` sets state back to `active`, clears `project_archived_at`

**What archiving does not do**: it does not clear `thread_items`. Archived projects are meant to persist as historical context that shapes adjacency — unlike discontinuity, which severs completely.

### Dismissal Logic

Dismissals are evaluated at scoring time, not fetch time (except anti_interests — see below).

- **Article dismissal** — weak negative signal. `weight -= 0.02` on matched interests.
- **Thread dismissal** — `weight -= 0.30`. If the same thread is dismissed twice, `permanent = true`.
- **Source dismissal** — source excluded at fetch time. `review_after` causes silent resumption with no prompt. On resumption, items from the source are **capped at the introduce bucket** for 14 days — they cannot enter the filter bucket regardless of their actual interest score. This is the "reduced weight" semantic: not a score penalty on the article itself, but a temporary ceiling on how prominent the source can become. After 14 days, the cap lifts automatically and items from the source are scored normally. This is tracked via a `resumed_at` timestamp on the dismissal record.

**Anti-interests** — keyword blacklist evaluated at fetch time, before embedding. Any article whose title or content contains a listed keyword is dropped immediately. Case-insensitive substring match. No LLM, no embedding, no storage. Zero cost.

### Interest ID Normalization

The canonical identifier for an interest is `interest.id` — a UUID-derived string (e.g. `int_a3f2c891`). All cross-references must use this ID, not the topic string. Topic strings are user-facing labels that can change via nuance; IDs are stable.

Normalization rules:
- `thread_items.topic_id` → references `interest.id`
- `match_reason.topic_id` → references `interest.id`
- `dismissals` targeting a thread → matched by topic string at write time, stored as `interest.id` in the DB
- Embedding cache keys → `interest.id`, not topic string (so topic label changes don't invalidate unnecessarily)

The `updater.py` is responsible for maintaining this normalization when interests are added, renamed via nuance, or removed. **When a topic string is renamed via nuance, only that interest's per-interest hash entry is invalidated — the composite hash changes, but only one embedding is recomputed at next scoring run.**

### LLMClient Protocol

All LLM calls in core — challenge classification, summarization, nuance rewriting — go through this protocol. Core never knows which LLM is behind it.

```python
class LLMClient(Protocol):
    def complete(
        self,
        system: str,
        prompt: str,
        max_tokens: int = 80,
    ) -> str: ...
```

Implementations are provided by the application layer, not core:

| Implementation | Where | When to use |
|---------------|-------|-------------|
| `OllamaLLM` | `agent/llm.py` | Local Ollama instance. Uses `OllamaResourceManager` for VRAM management. |
| `AnthropicLLM` | `agent/llm.py` | Anthropic API (cloud). No resource manager needed. |
| `OpenAILLM` | `agent/llm.py` | OpenAI-compatible API (cloud or local). |
| `MockLLM` | `tests/mocks/llm.py` | Testing. Deterministic canned responses. |

Swapping the LLM requires only changing which implementation is injected at startup in `run.py`. No core code changes. The `OllamaResourceManager` is wired only to `OllamaLLM` — cloud implementations don't use it.

```python
# run.py — LLM injection at startup
if config.llm.provider == "ollama":
    resource_manager = OllamaResourceManager()
    llm_client = OllamaLLM(resource_manager)
elif config.llm.provider == "anthropic":
    llm_client = AnthropicLLM(api_key=config.llm.api_key)
elif config.llm.provider == "openai":
    llm_client = OpenAILLM(base_url=config.llm.base_url, api_key=config.llm.api_key)
```

Add `provider`, `api_key`, and `base_url` to `config.yaml` under `llm:`. The `OllamaResourceManager` lives in `agent/resources.py`, not `core/`.

### Source Adapters

Each adapter implements `FeedSource`:

```python
@dataclass
class FetchContext:
    """
    Transport-layer context for source adapters.
    Adapters use what they need and ignore the rest.
    HTTP adapters use session. Non-HTTP adapters (email, local file) use credentials directly.
    """
    session: requests.Session | None = None
    credentials: dict[str, str] | None = None  # from vault, keyed by field name

class FeedSource(Protocol):
    def fetch(self, context: FetchContext) -> list[RawItem]: ...
```

`FetchContext` decouples source adapters from HTTP transport. An email adapter (Phase 2 Substack paywalled content), a local file scanner, or any non-HTTP source can implement `FeedSource` without receiving an irrelevant `requests.Session`. HTTP adapters use `context.session`. Non-HTTP adapters use `context.credentials` directly.

**`FetchContext` is defined in core as a data shape — populated exclusively by the agent layer.** Core never reads credentials, never builds sessions, never knows what a source URL is. `agent/vault/session.py` calls `build_session()` which reads from the vault and returns a populated `FetchContext`. Core receives this `FetchContext` as an argument to the `FeedSource.fetch()` call — it never creates one. The boundary is absolute: core defines the shape, agent fills it.

**RSS/Atom** — `feedparser`. Respects `ETag` and `Last-Modified`. Deduplicates by URL + published date.

**Hacker News** — Algolia API. Title + metadata only on first pass. Two-pass quick-fetch for items scoring 0.50–0.72: retrieves first 200 words of linked article and re-scores before bucket assignment. Items scoring ≥ 0.72 on title alone skip quick-fetch.

**Reddit** — Public JSON endpoints. Requires `User-Agent` header. 1-second delay between subreddit requests. Respects `Retry-After`. Same two-pass quick-fetch as HN. For > 10 subreddits: PRAW with OAuth credentials from vault.

**Arbitrary URLs** — `trafilatura` for content extraction. `index` type crawls outbound same-domain links to specified depth. Depth > 1 not recommended.

### Scoring

`score()` is a pure function:

```python
def score(
    items: list[RawItem],
    identity: IdentityModel,
    embedder: Embedder,
    source_stats: dict[str, SourceStats] | None = None,
) -> list[ScoredArticle]: ...
```

`source_stats` is an optional dict of per-source calibration data (mean and stddev of historical scores for that source). When provided, scores are normalised within source before bucket assignment.

Pipeline per item:
1. Check anti_interests — drop immediately if matched
2. Embed: `title + " " + content[:500]`
3. Compute cosine similarity against each interest topic embedding
4. `interest_score = max(weighted_similarity)` where active thread matches weight 2x, standing 1x
5. **Per-source normalisation** (if `source_stats` available): `normalised = (raw_score - source_mean) / source_stddev`, then rescale to 0–1. This prevents sources with dense, clean text (long-form essays) from systematically dominating sources with sparse titles (HN, Reddit) through no fault of content quality.
6. Assign preliminary bucket using normalised score (or raw if no stats available)
7. Record `match_reason`: top 3 matching interests with similarity scores

**Per-source calibration** — `SourceStats` is computed by the score task from the last 90 days of scored articles per source. Stored in `source_stats` table in the DB. Updated incrementally after each score cycle (rolling window). The first 20 scored items per source use raw scores — insufficient data for normalisation.

```sql
CREATE TABLE source_stats (
    source      TEXT PRIMARY KEY,
    score_mean  REAL NOT NULL,
    score_stddev REAL NOT NULL,
    sample_count INTEGER NOT NULL,
    updated_at  DATETIME NOT NULL
);
```

**Normalisation is skipped** for sources with fewer than 20 scored items (cold source), for sources where stddev < 0.01 (effectively constant scores — normalisation would amplify noise), and in dev mode with MockEmbedder (deterministic vectors have no meaningful distribution).

**"Active thread" definition**: in scoring, "active thread" means an interest with `weight >= 0.70` and `state == "active"`. This is distinct from the conversational thread (the message history in the `messages` table). The word "thread" is overloaded — in the identity model it means a topic you're actively pursuing; in the surface layer it means the ongoing conversation. Context disambiguates, but implementation should use the constant `ACTIVE_THRESHOLD = 0.70` rather than the string "thread" to avoid confusion.

**Pipeline ordering caveat**: similarity runs before stance detection. This means satire, opposition reading, and curiosity-without-affinity can score as high interest before the challenge classifier corrects them in the next step. This is a pragmatic tradeoff — stance detection on every item is prohibitively expensive. The pipeline catches misclassification on high-similarity candidates via challenge classification, but low-similarity false positives (items that score high due to surface topic overlap, not genuine interest) are an accepted limitation of the current approach.

**Phase 2 research item**: a lightweight pre-semantic stance heuristic before similarity scoring would reduce false positives at source. Possible approaches: cheap keyword-based stance classifier, or stance-aware embedding fine-tuning. Not in Phase 1 scope.

Embeddings computed in batches of 20. Interest topic embeddings cached and invalidated only when identity model changes.

**Embedding cache invalidation — atomic per-interest**: the global hash is a composite of per-interest hashes. Each interest has its own hash: `SHA-256(interest.id + interest.topic)`. The composite is `SHA-256(sorted(per_interest_hashes))`. Stored in `store/identity_hash.txt` as a JSON dict: `{interest_id: hash, ..., "_composite": composite_hash}`.

On each scoring run: recompute per-interest hashes, compare to stored. Only interests whose hash differs need re-embedding. This means a single nuance call re-embeds one interest, not all fifty. Weight and decay changes do not affect hashes — they don't change the topic string. New interests get embedded on first seen. Discontinued interests have their hash entry removed.

```python
# store/identity_hash.txt format
{
  "int_dev_001": "a3f2c891...",   # SHA-256 of "int_dev_001" + "self-awareness and prediction"
  "int_dev_002": "b7e1d445...",
  "_composite": "ff9a3c12..."      # composite of all per-interest hashes
}
```

This prevents the "computational spike" where a single semantic refinement triggers full re-embedding of all interests during a background fetch cycle.

**Embedder Protocol** — two implementations:

```python
class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[np.ndarray]: ...
```

Implementations live in `agent/embedders.py`, not core:

- `OllamaEmbedder` — `nomic-embed-text` via Ollama HTTP API. Default for agent.
- `SentenceTransformerEmbedder` — `bge-small-en-v1.5`. Loads locally, no Ollama required. Fallback for agent, default for service.

**`OllamaResourceManager`** lives in `agent/resources.py`, not `core/`. Core is technology-agnostic — it receives a configured `Embedder` and `LLMClient` and never manages their concurrency. The resource manager is agent-layer infrastructure wired at startup in `run.py` when `config.llm.provider == "ollama"`. Cloud LLM providers (Anthropic, OpenAI) don't use it.

**Embedding model versioning contract** — if the embedding model changes (e.g. `nomic-embed-text` → `bge-small-en-v1.5`, or any model upgrade), historical embeddings are incomparable to new ones. Cosine similarity between a vector from model A and a vector from model B is mathematically meaningless. The scoring pipeline must detect and handle this.

On each scoring run, the scorer reads the `model` and `dims` columns from the `embeddings` table. If the configured `embed_model` differs from stored embeddings, the system must:

1. Log a warning: `"Embedding model changed: {old} → {new}. Re-embedding required."`
2. Mark all existing embeddings as stale by setting `model = "stale:{old_model}"` in the DB
3. Re-embed all articles in `fetch_state IN ('scored', 'surfaced')` in batches over the next scoring cycles — not all at once (avoids a spike on a large corpus)
4. Reset `identity_hash.txt` composite hash to force re-embedding of all interest topic embeddings

**Mixed-state corpus rule** — during the re-embedding transition window, the corpus contains embeddings from both the old and new model. Cosine similarity between vectors from different models is meaningless. The scorer must skip articles with `model = "stale:*"` embeddings entirely — they are not scored, not surfaced, not penalized. They remain in `pending_content` limbo until re-embedded. This is the correct trade-off: a temporarily smaller surfaceable corpus is far preferable to garbage scores. The batch re-embedding runs each scoring cycle until no stale embeddings remain. Log progress: `"Re-embedding: {n} stale, {m} complete"`.

**Manual re-embedding command**:
```bash
keel --task score --reembed-all   # re-embeds entire corpus with current model
```

**Dimensionality mismatch guard**: the `dims` column catches silent model swaps where the model name is unchanged but the dimensionality differs (e.g. a model update that changes vector size). On startup, the scorer checks `dims` of the first stored embedding against the current model's output dimension. If they differ, treat it as a model change even if the name matches.

```python
class OllamaResourceManager:
    """
    Priority-aware lock for Ollama access.
    FOREGROUND requests (CLI interactions) preempt BACKGROUND batch jobs.
    Background jobs finish their current LLM call, then yield to foreground.
    """
    FOREGROUND = 0   # CLI queries, user-initiated actions
    BACKGROUND = 1   # batch scoring, challenge classification

    def __init__(self):
        self._lock = threading.Lock()
        self._foreground_waiting = threading.Event()

    @contextmanager
    def acquire(self, model: str, priority: int = BACKGROUND) -> Iterator[None]:
        if priority == self.FOREGROUND:
            self._foreground_waiting.set()
            with self._lock:
                self._foreground_waiting.clear()
                yield
        else:
            # Background: wait if foreground is queued, then acquire
            while self._foreground_waiting.is_set():
                time.sleep(0.1)
            with self._lock:
                yield
```

Background batch jobs check `_foreground_waiting` before acquiring and pause when a foreground request is queued. They do not interrupt a call mid-flight — they finish the current LLM call (typically 1–3 seconds), then yield. This ensures CLI interactions feel responsive without introducing true preemption complexity.

**Challenge classification runs one item at a time with foreground yield between each call.** Unlike embeddings which can be chunked mid-batch, LLM generation cannot be interrupted mid-call. A single Llama 3.2 challenge evaluation may hold the resource lock for 2–5 seconds. To prevent CLI stuttering, challenge classification must: acquire the lock for one item, complete the LLM call, release the lock, check `_foreground_waiting`, pause if set, then acquire for the next item. Never batch multiple challenge calls under a single lock acquisition.

```python
def classify_batch(
    candidates: list[ScoredArticle],
    identity: IdentityModel,
    llm: LLMClient,
    resource_manager: OllamaResourceManager,
) -> list[ScoredArticle]:
    results = []
    for item in candidates:
        # Check if foreground is waiting before acquiring for next item
        while resource_manager._foreground_waiting.is_set():
            time.sleep(0.1)
        with resource_manager.acquire(model="llama3.2", priority=BACKGROUND):
            stance = classify_stance(item, identity, llm)
        results.append(item.with_stance(stance))
    return results
```

This means challenge classification is maximally interruptible between items — each item is an independent lock acquisition — while each individual LLM call runs to completion without interruption.

**Strict sequential ordering within a fetch cycle**: all article embeddings must complete before any challenge classification begins. Never interleave embedding calls and LLM calls. The `fetch_and_score()` pipeline is:

```
1. fetch()          — no Ollama
2. embed_batch()    — nomic-embed-text via OllamaResourceManager lock (chunked)
3. score()          — pure computation, no Ollama
4. challenge()      — llama3.2 via OllamaResourceManager lock
5. summarize()      — llama3.2, optional, after challenge
```

**Embedding uses sub-batch chunking, not single large batches.** The `OllamaResourceManager` lock is acquired, a small chunk is embedded, the lock is released, foreground priority is checked, then re-acquired for the next chunk. This gives the foreground (CLI queries) a window to slip in every few seconds without destroying throughput:

```python
EMBED_CHUNK_SIZE = 5  # configurable; default 5, not 20

def embed_batch_chunked(
    texts: list[str],
    embedder: Embedder,
    resource_manager: OllamaResourceManager,
) -> list[np.ndarray]:
    results = []
    for i in range(0, len(texts), EMBED_CHUNK_SIZE):
        chunk = texts[i:i + EMBED_CHUNK_SIZE]
        with resource_manager.acquire(model="nomic-embed-text", priority=BACKGROUND):
            chunk_embeddings = embedder.embed(chunk)
        results.extend(chunk_embeddings)
    return results
```

`EMBED_CHUNK_SIZE` is configurable in `config.yaml` under `llm.embed_chunk_size`. On hardware with fast NPU/iGPU, increase it (10–15) for throughput. On slower hardware or when foreground responsiveness is critical, lower it (3–5). Default: `5`. `SentenceTransformerEmbedder` runs in-process and ignores the resource manager entirely — chunking only applies to `OllamaEmbedder`.

### Challenge Classification

Separate from scoring. Runs asynchronously after scoring completes.

Candidates: items with `interest_score ≥ 0.60` AND matched interest has `challenge_mode ≠ off`.

For each candidate, one LLM call:

```
System: "You classify whether a piece of writing challenges or confirms a given topic.
         Answer with exactly one word: challenge / confirm / tangential / neither.
         IMPORTANT: If the content is not explicitly supportive of the topic's typical
         stance, or introduces conflicting data, evidence, or framing, classify it as
         'challenge'. Use 'tangential' for content related to the topic but not taking
         a position — satire, highly technical content, adjacent domain pieces, or
         content where stance is genuinely ambiguous. Default to 'neither' only for
         purely factual or neutral reporting that takes no position. Do not use 'neither'
         as a safe default when the content has a discernible stance."

User: "Topic: {topic}
       Title: {title}
       Summary: {summary}"
```

**Four-class normalization**: the LLM response must be normalized to exactly one of `challenge`, `confirm`, `tangential`, `neither` (lowercase, stripped). Any other response (capitalized, punctuated, multi-word) is treated as `neither`. Log unexpected responses for debugging.

**`tangential` bucket behavior**: tangential items are treated as `introduce` bucket items — they surface in the feed but do not receive the challenge framing. They are not shown with the "this challenges your view" attribution. This prevents satire or highly technical content from being aggressively presented as epistemic friction when it isn't. Tangential items still count toward the exploration budget.

Results cached by `(article_id, topic_id)` — never re-classified. Items classified as `challenge` on an eligible thread move to the Challenge bucket.

**Cache key tradeoff**: `topic_id` is `interest.id` — a stable UUID. If an interest is discontinued and later reintroduced, it receives a new UUID, making the cache key a miss. The article will be re-classified from scratch. This is acceptable and intentional: a reintroduced interest is a different semantic context, and stale classifications from a previous life of that interest should not carry forward.

**Ternary limitation**: the `challenge / confirm / neither` classification compresses real stance space. Missing categories include ironic alignment, partial agreement, "agrees with premise but rejects conclusion," and emotional challenge without epistemic challenge. For Phase 1 this is acceptable — the ternary model surfaces the most salient cases. A vector stance model (epistemic alignment + emotional valence + novelty pressure) is the Phase 2 path if misclassification proves systematically harmful.

For keel-service: runs via async worker queue. Under load, classification will lag behind scoring. This is the explicit degradation contract: **when challenge workers are backlogged, items that would qualify for the challenge bucket remain in introduce until classified**. The feed is never blocked. Challenge mode degrades gracefully to introduce mode — it does not fail hard. This is intentional. The most philosophically important feature is also the most computationally expensive; it is explicitly best-effort at service scale.

### Bucket Assignment

| Bucket | Criteria |
|--------|----------|
| **Filter** | `interest_score ≥ 0.72` AND classification ≠ `challenge` |
| **Introduce** | `0.55 ≤ interest_score < 0.72` AND classification ≠ `challenge` |
| **Challenge** | `interest_score ≥ 0.60` AND classification = `challenge` AND `challenge_mode ≠ off` |
| **None** | `interest_score < 0.55` |

```yaml
scoring:
  filter_threshold: 0.72
  introduce_threshold: 0.55
  challenge_similarity_min: 0.60
  filter_max_items: 20
  introduce_max_items: 5
  challenge_max_items: 3

diversity:
  max_consecutive_same_thread: 3    # Assembly order: descending score; diversity rules applied after sort
  max_items_per_source: 3
  confirmation_ratio_alert_threshold: 0.90
  confirmation_ratio_alert_weeks: 3
  confirmation_ratio_intervention_threshold: 0.85   # automatic intervention (below alert)
  confirmation_ratio_intervention_weeks: 2           # fires faster than the alert
```

**Confirmation ratio: flag and intervene.** Tracking is not enough. If the confirmation ratio exceeds `0.85` for 2 consecutive weeks (before the 0.90 alert even fires), the surface task automatically adjusts assembly for that week's surfaces:

- The maximum filter-bucket items per surface drops from the normal cap to `floor(max_items_per_surface / 2)`
- The freed slots are filled with edge items, world signal, or challenge items — in that priority order
- The intervention is applied silently: no message to the user, no model update
- It lasts for 2 surface cycles, then normal assembly resumes
- If confirmation ratio is still high after 2 cycles, it triggers again on the next measurement

This is not punishment. It's the system refusing to trap the user in comfort without their awareness. The automatic intervention is deliberately gentle — it halves the confirmation items, not eliminates them. The user still gets what fits them. Just not only what fits them.

### Credentials Vault

Encrypted local store. AES-256-GCM via `cryptography` (Fernet). Key derived from master password using PBKDF2HMAC-SHA256, 480,000 iterations.

Master password entered once per session, or via `KEEL_VAULT_KEY` environment variable for unattended runs. Never stored.

```bash
keel --vault add --service substack --key email --value you@example.com
keel --vault add --service reddit --key client_id --value abc123
keel --vault list         # shows service names and key names only, never values
keel --vault remove --service substack
```

| Service | Keys | What it unlocks |
|---------|------|-----------------|
| `substack` | email, password | Authenticated RSS, paywalled content (Phase 2) |
| `reddit` | client_id, client_secret, username, password | PRAW OAuth, higher rate limits |
| `generic` | url_pattern, cookie or session_token | Arbitrary authenticated sites |

`vault.enc` is excluded from git by default (`.gitignore` entry included).

Vault failure behavior: log error, skip authenticated sources, continue with unauthenticated. Never prompt mid-run.

---

## Expansion, Mood, and Legibility

### The Four Layers of Attention

The identity model has a center, edges, an outside, and an unscored exterior. The system operates across all four depending on what the user wants from it at a given moment.

| Layer | What it is | How it's used |
|-------|------------|---------------|
| **Center** | Known interest graph — topics with weight ≥ 0.55 | Standard scoring. Filter and introduce buckets. |
| **Edges** | Topics sitting just outside the interest perimeter — weight 0.40–0.54, or engaged-with-but-not-reinforced | Probed occasionally. Surfaced with explicit framing: "This is at the edge of your known territory." |
| **Outside** | Ambient world signal — what's accumulating attention in the corpus regardless of your model | Surfaced at most once per surface, separately framed by signal type. |
| **Foreign** | Random injection — unscored, un-embedded, never enters the model | Surfaced occasionally. Explicitly framed: "This does not belong to your model." |

### Foreign Signal

The foreign signal layer is the escape hatch from closed epistemic circuitry. World signal is still curated through the system's lens — it gets fetched, scored by engagement metrics, and eventually could influence the model. Foreign signal cannot. It is drawn from a random injection pool, presented with a single item per surface cycle, and the system learns nothing from it regardless of how the user responds.

**Toxicity gating on foreign signal candidates.** Before adversarial selection, all candidates are filtered through a basic content gate. This is not an interest filter — it's a harm filter. Items are dropped from foreign signal candidacy if they match any of the following (checked against title + first 200 words):

```yaml
foreign_signal_filters:
  block_keywords: []              # user-configurable blocklist for foreign signal only
  min_content_length: 100         # drop near-empty pages
  require_language: []            # optional: restrict to specific languages (e.g. ["en", "fr"])
  # Quality heuristics — applied before adversarial selection
  require_extractable_text: true  # drop items where trafilatura returns < min_content_length
  block_paywall_indicators: true  # drop items with paywall signals in content (subscribe, sign in, etc.)
  block_video_only: true          # drop items with no text content (YouTube, pure video pages)
  min_word_count: 50              # distinct word count floor, not raw character count
```

**Minimum quality rationale**: `min_content_length: 100` catches near-empty pages but passes low-quality content at 101 characters. A 150-word clickbait title passes. Adding `min_word_count: 50` (distinct words), paywall detection, and video-only detection gives the foreign signal pool a meaningful quality floor without becoming a curation layer. The goal is that foreign items are genuinely readable, not that they're algorithmically vetted.

**User tolerance tuning**: add `foreign_signal_quality` to config as a named preset:

```yaml
expansion:
  foreign_signal_quality: "standard"   # standard | strict | minimal
  # standard: all heuristics above enabled
  # strict: adds readability score floor (Flesch-Kincaid > 30), no listicles
  # minimal: length check only — maximum randomness, user accepts noise
```

More importantly, **injection pool sources must be vetted at configuration time** — not at runtime. The admin configuring the injection pool is responsible for ensuring sources don't contain extremist content, malware, or illegal material. The spec intentionally does not auto-curate the injection pool, but it does provide:
- A `rotation: "weekly"` default to prevent any single source from dominating long-term
- The `block_keywords` filter as a runtime safety net
- A `--check-injection-pool` command that fetches one sample item per source and reports domain/language/content length for admin review

**A bad actor seeding the injection pool** (in a service context) is a real threat. The injection pool is admin-defined in `service/config/sources.yaml` — it is not user-configurable. Users cannot add sources to the injection pool. This limits the attack surface to the service administrator, not the user base.

Foreign signal items are:
- Selected by **minimax similarity to surfaced items** — not by distance to the centroid. The centroid of a highly diverse surface (wander/ambient mode) collapses toward the origin in high-dimensional space, making centroid distance meaningless. Instead: for each candidate item in the low-relevance pool, compute its maximum cosine similarity to any item already in the current surface. Select the candidate with the lowest maximum similarity — the item that is furthest from its closest neighbor in the current surface set.

**Minimax quality pre-filter** — items pushed furthest to the semantic margins in high-dimensional space are often semantic noise or malformed content whose vectors are abnormal rather than genuinely distant. Before applying minimax, pre-filter candidates to the top 50 by content length (proxy for coherence). Apply minimax selection only within this pre-filtered set. This prevents systematically selecting the weirdest items in the corpus. Configurable via `expansion.foreign_signal_filters.max_minimax_candidates` (default: 50).

```python
def select_adversarial_foreign(
    candidates: list[ScoredArticle],
    candidate_embeddings: list[np.ndarray],
    surface_embeddings: list[np.ndarray],
    max_candidates: int = 50,
) -> int:
    if not surface_embeddings:
        return 0  # caller sorts by external_score ASC; least-popular is the fallback

    # Pre-filter to top N by content length before applying minimax
    indexed = sorted(
        enumerate(candidates),
        key=lambda x: len(x[1].content or ""),
        reverse=True
    )[:max_candidates]

    min_max_sim = float("inf")
    best_idx = indexed[0][0]
    for orig_idx, _ in indexed:
        max_sim = max(cosine_similarity(candidate_embeddings[orig_idx], s) for s in surface_embeddings)
        if max_sim < min_max_sim:
            min_max_sim = max_sim
            best_idx = orig_idx
    return best_idx
```
- Not embedded against the identity model
- Not stored in `thread_items` or `interactions` (unless explicitly saved by user)
- Framed exactly as: *"This does not belong to your model. No score. No match. Just here."*

```yaml
expansion:
  foreign_signal_enabled: true
  foreign_signal_frequency: "daily"
  foreign_signal_selection: "adversarial"   # adversarial | random
  # adversarial: lowest cosine similarity to current surface centroid (default)
  # random: purely random from low-relevance pool
```

**Why adversarial over random**: purely random selection occasionally draws items that happen to be semantically adjacent to current interests. Adversarial selection maximizes the semantic distance from what was just surfaced — it is the most "other" thing in the corpus. This is the true escape hatch from epistemic closure.

Configuration:

```yaml
expansion:
  edge_enabled: true
  edge_probe_rate: 0.3
  edge_similarity_min: 0.40
  edge_similarity_max: 0.54
  world_signal_enabled: true
  world_signal_frequency: "daily"
  foreign_signal_enabled: true
  foreign_signal_frequency: "daily"   # daily | every_surface | off
```

The user can engage with a foreign item, dismiss it, or ignore it. None of these interactions write to the identity model. The item exists outside it. If the user explicitly says "add this to my model," it enters as `provenance: chosen` — but that is an active decision, not passive absorption.

**Why this matters**: without foreign signal, the system is a closed ecology of meaning. Every input eventually influences the model. Foreign signal is the one guaranteed source of noise that refuses categorization — items that exist for the user to see without the system learning from the seeing.

### Edge Expansion

The system maintains an implicit `edge_topics` set — topics that sit in semantic space adjacent to known interests but below the introduce threshold. These emerge from:

- Introduced items the user engaged with but never explicitly reinforced
- Semantic neighbors of active interests at similarity 0.40–0.54
- Topics that appear in the corpus with rising frequency but don't yet match the model

Edge items surface at most once per surface cycle, with explicit framing. The rate of edge probing is configurable:

```yaml
expansion:
  edge_enabled: true
  edge_probe_rate: 0.3          # Probability of including one edge item per surface
  edge_similarity_min: 0.40
  edge_similarity_max: 0.54
  edge_random_fraction: 0.4     # Fraction of edge selections drawn randomly within band (floor: 0.20)
  world_signal_enabled: true
  world_signal_frequency: "daily"   # daily | every_surface | off
```

**Edge selection has a mandatory random component.** Without it, edge items are selected by highest similarity within the edge band — biased toward what the user is most likely to engage with. That's curated novelty, not exploration: a predictable frontier that stops being a frontier. `edge_random_fraction` (default `0.4`) means 40% of edge selections are drawn randomly within the similarity band regardless of score. The floor is `0.20` — not configurable lower. Some surprise must be genuinely unearned.

**Foreign signal source for the agent**: in the service, foreign signal candidates come from the injection pool. In the agent, they are drawn from the full fetched corpus — any item that passed anti-interest filtering but scored below the introduce threshold (`< 0.55`). Selection uses the minimax formulation: the item with the lowest maximum cosine similarity to any item in the current surface set. Falls back to random if no surface embeddings are available (first cycle). No scoring, no embedding against the identity model. The agent simply draws from the low-relevance pool rather than maintaining a separate injection source.

**Empty pool fallback**: if no items exist below the introduce threshold (new user, very small source set, or unusually high-scoring fetch cycle), foreign signal is skipped for that cycle. No error, no placeholder, no substitute. The slot is simply absent from the surface that day.

World signal scoring ignores the identity model's **interests** entirely — it does not score items by topic relevance. However, it must still respect `source_dismissals` at assembly time. A dismissed source (permanent or within `review_after` window) is excluded from world signal candidates the same as from scored items. The priority chain applies: `source dismissal → hard exclude` comes before world signal selection. World signal bypasses interest scoring only, not source exclusions.

| Signal | What it measures | Framing to user |
|--------|-----------------|-----------------|
| **Recency** | Items published in last 6 hours with any traction | "This just landed" |
| **Momentum** | Items with rapidly accelerating engagement (score velocity, not absolute score) | "This is moving fast" |
| **Diversity** | Items from sources not represented in recent surfaces | "This is outside your usual territory" |

**Signal formulas:**

- **Recency**: `published_at >= now - 6h AND external_score >= 10`. Ranked by `published_at` descending. Top item selected.
- **Momentum**: `score_velocity = external_score_now - external_score_at_last_fetch`. Computed per item across two consecutive fetch cycles. Top item by velocity selected. Requires items to have been fetched at least twice — new items are ineligible.
- **Diversity**: source not present in the last 10 surfaced items (`articles` table, `surfaced_at` descending). Among all qualifying items, top by `external_score` selected.

**`core/expansion/expander.py`** — pure functions. The agent surface task calls these with pre-loaded data; core does the computation:

```python
def find_edge_candidates(
    scored_items: list[ScoredArticle],
    edge_similarity_min: float = 0.40,
    edge_similarity_max: float = 0.54,
    random_fraction: float = 0.40,
    rng: random.Random | None = None,
) -> list[ScoredArticle]:
    """
    From scored items, return candidates in the edge band.
    random_fraction of selections drawn randomly within band (floor: 0.20).
    Pure — caller injects RNG for determinism in dev mode.
    """

def score_world_signal(
    items: list[RawItem],
    now: datetime,
    recent_surface_sources: list[str],
    recency_hours: int = 6,
    recency_min_score: int = 10,
) -> dict[str, RawItem | None]:
    """
    Returns {'recency': item|None, 'momentum': item|None, 'diversity': item|None}.
    Pure — caller passes in pre-fetched data and current time.
    No DB access. Items must already have external_score and external_score_prev set.
    """
```

The agent surface task loads what's needed from the DB, calls these functions, and uses the results in assembly. Core never touches the DB.

Each signal surfaces at most one item per surface cycle. All are explicitly labeled with their signal type — never presented as "relevant to you." The framing matters: these are popularity and recency pressures, not truth pressures. The system says so.

**What world signal is not**: a quality filter. High engagement does not mean high quality. The labeling is the user's protection against treating it as authoritative.

### Moods

A mood is a named configuration overlay applied at surface time. It doesn't write to the identity model. It shifts thresholds, layer weights, and resolution preferences temporarily.

**A note on filter topology**: this system avoids engagement optimization but not filter topology risk entirely. A user who disables challenge mode, prunes discomfort, and collapses diversity through repeated dismissals can still construct an epistemic tunnel — just one driven by personal agency rather than platform incentives. Challenge mode, edge expansion, and drift detection are the structural mitigations. They are available and on by default. They are not enforced. That is intentional: sovereignty includes the right to be wrong about your own attention.

| Mood | What it does |
|------|-------------|
| `depth` | Raises filter threshold to 0.80. Suppresses introduce and edge. Summary and synthesis resolution. For going deep on known threads. |
| `wander` | Lowers introduce threshold to 0.45. Amplifies edge probing to 0.8. More introduce, fewer filter. For exploratory days. |
| `friction` | Sets all eligible threads to `challenge_mode: friction` temporarily. For days you want to be pushed. |
| `signal` | Micro resolution across the board. High filter threshold (0.85). Fast and dense. For low-attention windows. |
| `ambient` | World signal dominant. Edge probing off. One or two items max, both from outside layer. For days you want to know what's moving without being pulled into your own threads. |
| `open` | Default. All layers active at standard thresholds. |

Moods are set explicitly or inferred. Inference runs at surface time based on recent interaction patterns:

| Pattern | Inferred mood |
|---------|--------------|
| Rapid dismissals of filter items in last 2 surfaces | `wander` or `signal` |
| Repeated "go further" on same thread | `depth` |
| Engaging with challenge items, dismissing filter items | `friction` |
| Long silence after multiple surfaces | `ambient` |
| Engaging broadly across many threads | `open` |

When a mood is inferred, the agent surfaces the inference as a soft confirmation before applying it:

```
→ Keel

You've been dismissing most of what I surface lately.
Switching to wander mode — looser edges, more introduction.
Say "stop" or set a different mood if not.
```

The user can set mood explicitly at any time:

```
> mood: depth
> mood: wander
> mood: open
> what's my mood?
```

Mood resets to `open` after 24 hours unless explicitly held.

**Mandatory exploration pulse — overrides all mood suppression.** A user in sustained `depth`, `signal`, or `ambient` mode for 14+ days will have edge probing suppressed throughout. Without correction, this creates epistemic calcification: the system warns (weekly reflect) but never corrects. Warnings are not corrections.

Every N surface cycles, regardless of current mood, the surface task injects one edge item and one world signal item. These bypass mood threshold suppression. They are labeled differently from normal edge items:

```
→ Keel

[Exploration pulse — outside your current depth mode]
...item...
```

The user can dismiss it normally. The pulse does not override the rest of the surface — it adds two items above the mood-gated selection. It cannot be disabled. This is the one place sovereignty yields to epistemic health: a user can choose not to engage, but they cannot choose not to see.

**Exploration pulse scales with model age — not static.** As the model matures and interests solidify, the surface naturally converges. A 6-month-old model with 5 high-weight interests needs more structural disruption than a 2-week-old model, not less. The pulse interval shortens as model age increases:

| Model age | Pulse interval | What this means |
|-----------|---------------|-----------------|
| 0–30 days | Every 7 surfaces | ~2 exploration items/week |
| 31–60 days | Every 6 surfaces | Slightly more frequent |
| 61–90 days | Every 5 surfaces | Model solidifying — increase pressure |
| 90+ days | Every 4 surfaces | Permanent floor for mature models |

The minimum is `every_4_surfaces` — not configurable lower. A mature model gets one exploration item roughly every other day. This is not negotiable: a system that has learned the user well must work harder to keep the door open, not less.

```yaml
exploration:
  pulse_every_n_surfaces: 7       # starting interval; decreases automatically with model age
  pulse_minimum_interval: 4       # floor; never goes below this regardless of age
  pulse_age_step_days: 30         # interval decreases by 1 every this many days
```

**Mood momentum**: moods don't switch cleanly in human cognition — they echo. A `mood_momentum` config value (default `0.3`) blends the previous mood's thresholds into the next surface at reduced weight for one cycle.

**Mood inference vs explicit precedence**: inferred mood never overwrites an explicitly set mood. Inference only applies when the current mood is `open` or when the current mood was itself inferred (`mood_inferred: true`). If the user explicitly sets a mood, `mood_inferred` is set to `false` and inference is suppressed until the mood expires or the user resets to `open`. The reflect task may suggest a mood change but will not apply it if `mood_inferred: false`. This prevents jarring threshold jumps and makes mood transitions feel more continuous. Full partial blending across concurrent mood states is Phase 2 behavior.

Blending formula applied to each threshold at surface time:
```
effective_threshold = new_mood_threshold * (1 - momentum) + prev_mood_threshold * momentum
```
Example: switching from `depth` (filter_threshold=0.80) to `open` (filter_threshold=0.72) with momentum=0.3:
`effective = 0.72 * 0.7 + 0.80 * 0.3 = 0.504 + 0.24 = 0.744`
After one cycle, momentum is no longer applied — full new mood thresholds take effect.

```yaml
mood:
  default_reset_hours: 24
  momentum: 0.3       # 0.0 = hard switch, 1.0 = no change
```

### Legibility

The user is always legible to themselves. Every update the model made, every inference it drew, every action that wrote to it — visible, traceable, correctable at any time. Legibility is structured in four tiers:

**Tier 1 — Raw traces** (`--model --raw`): unprocessed vector deltas, score histories, adjacency maps. The system does not interpret these. No narrative, no summary, no explanation. Just the numbers changing over time. For users who want to inspect the model's behavior without the system's own framing mediating what they see. This is the only legibility layer the system does not "beautify."

**Tier 2 — Operational log** (`--model --log`): full trace of every model update, decay event, interaction, and inference with timestamps. Dense. Not meant for regular reading.

**Tier 3 — Behavioral summary** (`--model`): weekly digest in plain language. What changed, why, and what effect it had. "Your interest in civilizational design strengthened this week — 4 engagements, 1 challenge item. Local-first software is fading — last engagement 18 days ago." This is the default legibility surface.

**Tier 4 — Explanatory narrative** (in-chat, on demand): "why did you surface that?" or "what changed this week?" — the agent synthesizes from the operational log into a direct conversational answer. Grounded in data, expressed in plain language.

**In-thread attribution footer** — every surface message includes a compact summary:

```
[3 items · wander mode · triggered by: civilizational design (0.84), local-first (0.79)]
```

**What legibility is not**: explanation of the system's philosophy. It is a trace of what actually happened to your specific model. The explanatory layers are always system-rendered — the system that shapes identity is also the system that explains it. Raw traces exist precisely because explanation is never fully external to the explainer. The user can look at the numbers directly and draw their own conclusions.

### Drift Detection

The feedback loop — surfaced content shapes interactions, interactions update the model, the model shapes future surfacing — is not neutral. It is a behavior-shaping machine with memory. The reflect task tracks model movement and makes it visible.

Five signals tracked weekly:

| Signal | What it measures | Flag condition |
|--------|-----------------|----------------|
| **Velocity** | Rate of weight change across all **active** interests (excludes archived, dormant, inactive) | High velocity sustained for 3+ weeks |
| **Concentration** | Whether weights are converging on fewer **active** topics (excludes archived, dormant, inactive) | Top 3 active interests holding > 70% of total active weight |
| **Compression** | Whether the semantic spread of surfaced content is narrowing over time — tracks centroid spread of surfaced item embeddings week over week | Spread shrinking for 3+ consecutive weeks |
| **Passivity** | Whether the user is steering the agent or only passively consuming — ratio of user-initiated to agent-initiated interactions | `user_initiated_pct < 0.10` for 3+ consecutive weeks |

**Archived interests are excluded from all drift detection math.** Archived project interests have frozen weights by design — including them in concentration and velocity calculations would permanently skew the signal for active interests. A high-weight archived interest occupying one of the top 3 slots would trigger a false concentration alert indefinitely. All drift signals operate only on `state == "active"` interests. Dormant and inactive interests are also excluded — their weights are at or near floor and would distort the pool denominator.

**Centroid spread formula** — Mean Squared Distance (MSD) from each surfaced item embedding to the collective centroid:

```
centroid = mean(e_1, e_2, ..., e_n)
MSD = (1/n) * sum(||e_i - centroid||^2  for i in 1..n)
```

Lower MSD = tighter semantic neighborhood = more compression. Computed per surface cycle and stored in `surfaced_embeddings.centroid` as the mean vector. Weekly compression signal compares MSD across the last 3 stored centroids.

**Compression alert threshold**: if MSD drops by more than 30% over three consecutive weeks, the epistemic tunnel alert fires in the reflect message. The 30% threshold is configurable:

```yaml
drift:
  compression_alert_msd_drop_pct: 0.30   # 30% MSD reduction triggers alert
```
| **Source diversity** | Range of sources driving interactions | Single source driving > 50% of engagements |
| **Edge engagement** | Whether edge items are being engaged or ignored | Zero edge engagement for 4+ weeks |

**Edge engagement drift flag includes mood context.** If the edge engagement flag fires while the user has been in `depth`, `signal`, or `ambient` mode for the majority of the flag period, the reflect message must note this explicitly — the low edge engagement was caused by the system's own mood, not user avoidance. Without this context, the user sees a flag for a problem they didn't create:

```
→ Keel (weekly reflect)

No edge items engaged in four weeks — but you've been in depth mode
for most of that time, which suppresses edge probing. This may not
reflect a real pattern. Switch to wander or open mode to re-enable
edge exploration before drawing conclusions.
```

If edge engagement is low and mood has been open or wander (exploration was available), the flag fires without the caveat — it's a genuine signal.

Compression is distinct from concentration. You can have 10 active interests that are all semantically adjacent — the model looks diverse by topic count but the actual content being surfaced is drawing from an increasingly tight neighborhood. Compression catches this. It is the identity compression loop made visible: the model smoothing the user until they slide easily inside it.

When a flag condition is met, the reflect message notes it — not as a judgment, but as information:

```
→ Keel (weekly reflect)

Your model is concentrating. Three topics now account for 74% of
your engagement weight, up from 51% four weeks ago. This could be
deepening focus or narrowing range — hard to tell from here.
Edge engagement has been low. Might be worth a wander session.

Separately: the semantic spread of what's been surfacing has been
narrowing for three weeks. The topics look different but the content
is coming from a tighter neighborhood. Flagging it.
```

Drift detection doesn't intervene. It reports. The user decides.

### Intentional Forgetting

Three levels of forgetting, from softest to hardest:

| Type | What it does | How to trigger |
|------|-------------|----------------|
| **Decay** | Weight fades gradually without reinforcement | Automatic |
| **Dismissal** | Weight reduced explicitly; topic can return | "Drop this thread" |
| **Discontinuity** | Topic removed completely from active model; no residual weight; no decay clock | "I'm not that person anymore" or `--forget` |

Discontinuity is irreversible in the active model. The interaction history retains that it happened — the audit log records the discontinuity with timestamp and the topic that was removed. But the model itself carries no trace forward.

**`thread_items` must be cleared on discontinuity.** When a topic is discontinued, all rows in `thread_items` where `topic_id` matches the interest's `id` must be deleted. Without this, articles that were previously mapped to the discontinued topic remain linked to it in the DB. These articles can still surface via similarity scoring on other overlapping interests — they become ghost relevance, carrying the shadow of a topic the user has explicitly rejected. The discontinuity is only complete when the topic is removed from the identity model, the interaction history, AND the `thread_items` mapping table.

```sql
-- Run atomically with identity model update when discontinuity fires
DELETE FROM thread_items WHERE topic_id = ?;  -- interest.id of discontinued topic
```

**Ghost dismissal (optional)** — purging a topic from the model while still fetching from semantically similar sources means that content can resurface as foreign or world signal, creating a zombie topic effect. The `--forget` command accepts an optional `--ghost-dismiss` flag that applies a 14-day temporary negative bias on the semantic vector of the discontinued interest:

```bash
keel --forget --topic "startup culture" --ghost-dismiss
```

The ghost dismissal stores the discontinued interest's last embedding in a `ghost_dismissals` table with an expiry date. During scoring, items with cosine similarity ≥ the ghost dismissal threshold to any active ghost vector receive a score penalty of -0.20, pushing them below the surface threshold. After 14 days, the ghost entry expires automatically. This is opt-in — standard `--forget` without the flag does not apply a ghost dismissal.

**Ghost dismissal threshold default: 0.70, not 0.55.** Short topic strings (e.g. "startup culture") produce imprecise embeddings that may cast a wide semantic net at 0.55. A ghost dismissal at 0.55 against "startup culture" might silently suppress adjacent topics the user still values (business strategy, company culture, founders). The threshold should be high enough to be surgical. Default is `0.70`, configurable:

```yaml
expansion:
  ghost_dismiss_threshold: 0.70    # cosine similarity threshold for ghost penalty (default: 0.70)
  ghost_dismiss_days: 14           # days the penalty lasts
  ghost_dismiss_penalty: -0.20     # score penalty applied to matching items
```

The user can lower the threshold via config if they want a wider suppression radius, but the default prioritizes precision over breadth.

**Ghost-penalized items are hard-excluded from edge expansion.** A score of 0.45 after ghost penalty falls within the edge band (0.40–0.54), which would route the item into exploratory probing — the opposite of discontinuity's intent. Items that receive a ghost penalty must be flagged `ghost_penalized: true` in the `ScoredArticle` and excluded from edge selection at surface time, regardless of their final score. The edge surfacer checks this flag and skips any item where it is set. Ghost-penalized items are bucketed as `none`, not `edge`.

```sql
CREATE TABLE ghost_dismissals (
    id          INTEGER PRIMARY KEY,
    embedding   BLOB NOT NULL,        -- embedding of the discontinued interest topic
    topic       TEXT NOT NULL,        -- stored for audit reference only
    created_at  DATETIME NOT NULL,
    expires_at  DATETIME NOT NULL     -- created_at + 14 days
);
```

```bash
keel --forget --topic "int_001"    # Removes interest by ID
keel --forget --topic "startup culture"  # Removes by topic string match
```

In chat:

```
> forget startup culture
> I'm not that person anymore
```

The agent confirms before executing:

```
→ Keel

This will remove "startup culture" from your model entirely —
no residual weight, no decay. It won't come back unless you
reintroduce it. Confirm?
```

Discontinuity is the answer to: how do you build a memory that learns without becoming law. You give the person the ability to break the continuity on purpose.

**`--forget --scrub` for sensitive discontinuities** — standard `--forget` preserves the topic string in `model_updates` and `interactions` audit entries. If the topic is sensitive or the user wants a genuinely clean break, `--scrub` replaces all topic string references in the audit tables with `[FORGOTTEN]` while preserving the numerical deltas (weight changes, interaction counts). The model's behavioral history remains intact for calibration purposes; the semantic label is erased.

```bash
keel --forget --topic "startup culture" --scrub
```

What `--scrub` touches:
- `model_updates`: `value_before` and `value_after` where they contain the topic string → `[FORGOTTEN]`
- `interactions`: `detail` field where it contains the topic string → `[FORGOTTEN]`
- `thread_items`: deleted (same as standard discontinuity)
- `ghost_dismissals`: if `--ghost-dismiss` was also used, the `topic` field → `[FORGOTTEN]`

What `--scrub` does not touch:
- Numerical weight values in `model_updates` — these are preserved
- Interaction type counts — these are preserved
- Article content — articles remain in the DB; only the topic mapping is severed

`--scrub` is irreversible. The agent confirms before executing with a distinct warning when `--scrub` is included.

---

## keel-agent

### Scheduler

APScheduler in blocking mode. Task registration:

```python
# score is NOT registered as a scheduled job — it runs as fetch's callback
scheduler.add_job(fetch,   'interval', hours=6,    misfire_grace_time=3600, max_instances=1)
scheduler.add_job(surface, 'cron',     hour=7,     misfire_grace_time=1800, max_instances=1)
scheduler.add_job(silence, 'cron',     hour=8,     misfire_grace_time=3600, max_instances=1)
scheduler.add_job(reflect, 'cron',     day_of_week='sun', hour=8, misfire_grace_time=7200, max_instances=1)

# fetch internally calls score on completion:
def fetch_and_score():
    new_items = run_fetch()
    if new_items:
        run_score()         # score runs inline, not as a separate scheduled job
        run_challenge()     # challenge classification runs after score
```

**Job chaining**: `score` is not an independent interval job. It runs as a continuation when `fetch` completes. This ensures score always operates on a fully committed fetch batch. If fetch fails, score does not run. If score fails, the next fetch cycle will trigger score again on completion — unscored articles accumulate and are scored in the next cycle's batch.

For persistent background execution:

```bash
# systemd (recommended) — see docs/systemd.md for unit file
# nohup fallback
nohup keel --schedule > logs/keel.log 2>&1 &
keel --status    # shows last run time and outcome for each task
```

**SIGTERM handling** — the scheduler catches `SIGTERM` and `SIGINT`, waits for the currently running task to finish writing to the DB, then exits cleanly. It does not interrupt mid-batch. A task that is between jobs exits immediately. This prevents partial writes on machine shutdown or `systemctl stop`.

### Tasks

**`fetch`** — polls all enabled sources. Skips sources in `dismissals` with `permanent: true`. Resumes sources past their `review_after` date, setting `resumed_at = today` on the dismissal record. Respects per-source fetch intervals.

**External score update**: for sources that provide engagement scores (HN, Reddit), the fetch task must update `external_score_prev = external_score` before writing the new `external_score`. This preserves the delta needed for momentum calculation. Items fetched for the first time have `external_score_prev = 0`.

**`score`** — embeds new items in batches of 20. Scores against identity model. Runs challenge classification asynchronously as continuation. Records `match_reason` on each article. Writes `last_score_completed_at` via `TaskStatus`.

**`surface`** — before selecting items, checks `last_score_completed_at` via `TaskStatus`. If score completed less than 30 minutes before the 07:00 surface trigger, or if score is currently running (`fetch_state=ready_to_score` items exist in the DB), the surface task defers up to 30 minutes in 5-minute increments, re-checking each time. If score hasn't completed after 30 minutes, surface proceeds with whatever is scored — partial corpus is better than no surface. Deferred start is logged.

**`TaskStatus` protocol** — file-based for the agent, DB-based for the service. Same interface, different backing store:

```python
class TaskStatus(Protocol):
    def write(self, task: str, status: dict) -> None: ...
    def read(self, task: str) -> dict | None: ...

# agent: FileTaskStatus → store/task_status.json
# service: DbTaskStatus → task_status table in SQLite
```

```json
// store/task_status.json (agent)
{
  "last_fetch_completed_at": "2026-04-10T06:04:12",
  "last_score_completed_at": "2026-04-10T06:31:44",
  "last_surface_completed_at": "2026-04-10T07:02:11",
  "last_reflect_completed_at": "2026-04-06T08:00:33",
  "score_in_progress": false
}
```

This file is advisory, not a lock. The scheduler remains in charge of timing; surface simply waits politely when score is still processing.

**`silence`** — runs daily at 08:00. Finds all surfaced items with no interaction in the past 48 hours. Records `silence` interaction for each. Applies weak weight reduction (`-0.02`) to matched interests. Capped at 3 silence interactions per item.

**Silence is keyed to `surfaced_msg_id`, not `article_id`.** If the same article is surfaced twice before 48 hours have elapsed (e.g. high-scoring item resurfaced in a different mood cycle), each surfacing is tracked independently. Silence on the first surfacing does not carry forward to the second. This prevents double-penalizing an item the user simply hasn't seen yet. The 48h timer starts from the `messages.timestamp` of the surface message, not from `articles.surfaced_at`.

**One silence penalty per surfacing event.** An item receives at most one silence interaction per `surfaced_msg_id`, regardless of how many days pass. The daily silence task checks: `no silence interaction exists for this (article_id, message_id) pair` — if one already exists, the item is skipped entirely.

The cap of 3 applies across three distinct surfacing events of the same article across separate surface cycles. Not three days of ignoring the same surface. Each `surfaced_msg_id` gets exactly one silence interaction or zero.

**Silence double-tap guard** (simplified): only record silence if `now() - message.timestamp > 48h` AND `no silence interaction exists for (article_id, message_id)`.

**Absence protection — silence does not accumulate during extended inactivity.** A user who doesn't open their feed for a week accumulates silence on all items surfaced during that week. The cap of 3 per surfacing event limits per-item damage, but a week of absence could still generate 7 silence interactions across 7 daily cycles (one per cycle per item). To prevent availability collapse — where the model learns from absence rather than intent — silence interactions older than 48 hours from the same `surfaced_msg_id` are not applied if the user has zero interactions of any type in the last 5 days. This is the "extended absence" guard: if the user simply wasn't present, silence is not recorded.

```python
# Extended absence guard in silence task
last_any_interaction = db.execute(
    "SELECT MAX(timestamp) FROM interactions"
).fetchone()[0]
user_was_absent = (
    last_any_interaction is None or
    (now - datetime.fromisoformat(last_any_interaction)).days >= 5
)
if user_was_absent:
    # Skip silence recording entirely this cycle
    logger.info("Silence task: user absent 5+ days, skipping silence recording")
    return identity, 0
```

**Silence is mood-aware.** Items should only accumulate silence if they were eligible to be rendered at the mood-adjusted threshold that was active when they were surfaced. If the user was in `depth` mode (filter threshold 0.80) and an item scored 0.74, that item was invisible — it could not have been seen regardless of engagement. Recording silence against it would penalize the user for not reading something they were never shown.

The silence task checks: `article.interest_score >= mood_threshold_at_surface_time`. The mood active at surface time is stored in the surface message's metadata. Items below the threshold at surface time are skipped by the silence task entirely — they are invisible, not silenced. Add `mood_at_surface` to the `messages` table to support this check.

**Silence suspended entirely in depth mode.** When the user is explicitly in `depth` mood (`mood = "depth"` AND `mood_inferred = false`), the silence task does not run. Depth mode is specifically for contemplative, non-conversational engagement with known threads — reading carefully without responding is the intended behavior. Applying silence penalties during a session the user deliberately chose for deep engagement contradicts the purpose of that mood. Silence resumes on the next task run after depth mode expires or the user resets mood.

**Silence transparency**: the weekly reflect message explicitly states what silence did that week. Users should not feel watched by their own non-engagement. The reflect output includes a plain-language statement of silence's effect:

```
Silence this week: 7 items seen without interaction.
Weak signal applied — small weight reductions on matched threads.
This does not mean the system recorded your not-engaging as meaningful.
It means items you didn't act on get slightly less weight next time.
Nothing more was inferred.
```

This framing is non-negotiable. The perception of surveillance matters as much as the implementation.

**`surface`** — selects items to surface. Assembles in descending **effective score** order. Applies diversity floor (max 3 consecutive same-thread, max 3 per source). Chooses resolution per item based on presentation preferences. Renders via LLM. Writes message to thread. Emits event to CLI if active.

**Stale queue penalty** — items blocked by the diversity floor accumulate in `fetch_state='scored'` and choke the top of the queue, preventing newer mid-scoring items from ever surfacing. The surface task applies a time-based effective score for sorting only (not stored):

```python
STALE_PENALTY_PER_DAY = 0.02   # configurable
MAX_STALE_PENALTY = 0.30        # cap; prevents items from going negative

hours_since_fetch = (now - article.fetched_at).total_seconds() / 3600
days_since_fetch = hours_since_fetch / 24
stale_penalty = min(MAX_STALE_PENALTY, days_since_fetch * STALE_PENALTY_PER_DAY)
effective_score = article.interest_score - stale_penalty
```

Items are sorted by `effective_score`, not `interest_score`. The stored `interest_score` is never modified — this is a sort-time adjustment only. A high-scoring item blocked by diversity on Monday has an effective score 0.10 lower by Friday, allowing mid-scoring fresh items to surface ahead of it. After ~6–15 days the stale item's effective score drops below the introduce threshold and it stops competing entirely.

Add `stale_penalty_per_day` and `max_stale_penalty` to `config.yaml` under `surfacing:`.

**Resurfacing eligibility**:
- Items surfaced and ignored (silence recorded) — not eligible for 14 days
- Items explicitly dismissed — never resurfaced
- Items the user engaged with — eligible to resurface after 30 days if still scoring above filter threshold
- Items never surfaced — always eligible

**Priority resolution chain** — when multiple layers conflict (mood suppresses an item, world signal wants to surface it, anti-interest blocks another), the following chain governs:

```
anti_interests     → hard drop, no override possible
discontinuity      → hard exclude, no override possible
source dismissal   → hard exclude until review_after date (applies to world signal too)
source resumption  → introduce bucket cap for 14 days after resumed_at (cannot enter filter)
thread dismissal   → exclude unless mood=wander (partial override)
mood thresholds    → filter/introduce thresholds shift per mood
exploration budget → exploration items capped at global budget (see below)
bucket assignment  → filter > challenge > introduce > edge > world > foreign
diversity floor    → applied after bucket, limits per-thread and per-source count
```

**Global exploration budget.** Edge items, world signal, foreign signal, challenge items, and exploration pulse all draw from a single exploration budget. Without a global cap they can stack — a surface of 5 items could have 3 exploration items, making the feed feel broken. The budget is a fraction of `surface_density`:

```yaml
expansion:
  exploration_budget_pct: 0.30   # max 30% of surface items can be exploration
                                  # e.g. surface_density=5 → max 1-2 exploration items
```

**Budget allocation priority** — exploration mechanisms compete for the budget in this order:
1. Challenge items (highest epistemic value — gets first claim)
2. Edge items (second — adjacent territory)
3. Exploration pulse items (mandatory — always gets its slot even if budget is tight)
4. World signal (daily ambient signal)
5. Foreign signal (adversarial — gets a slot only if budget remains)

The exploration pulse is the one exception: it fires regardless of budget. Its items are added above the budget calculation — they don't consume the budget. This ensures the mandatory exploration minimum is always preserved. Everything else competes.

**At surface_density=5 with exploration_budget_pct=0.30**: maximum 1 exploration item from the competitive pool, plus the exploration pulse item when it fires (every 4–7 surfaces). A normal surface has 3–4 filter/introduce items and 1 exploration item. That is the intended ratio.

**World signal respects source dismissals.** World signal bypasses interest scoring (it does not match items against the identity model's topics) but it is not exempt from source-level exclusions. A dismissed source is excluded from world signal candidates at assembly time, same as scored items.

Earlier in the chain always wins. Mood can override dismissal only at the thread level and only in wander mode — it cannot override source dismissal, anti-interests, or discontinuity under any circumstances. Foreign signal bypasses the chain entirely — it is drawn after all other assembly is complete.

**`reflect`** — weekly. Runs in two phases to minimize identity lock hold time.

**Phase 1 (locked)** — acquires identity lock. Applies decay to all interests. Transitions interest states. Releases lock. Total lock hold time: milliseconds. No LLM calls, no DB reads beyond identity model.

**Phase 2 (unlocked)** — runs with identity lock released. Reads DB for drift signals, confirmation ratios, source health, challenge dismissal rates. Calls LLM for mood inference (if needed). Assembles weekly summary message. Writes message to thread. Writes status to `task_status.json`.

**Why the split matters**: the reflect task's LLM call for mood inference can take 2–10 seconds. If the identity lock is held during this call, any user interaction that tries to update the identity model (typing a response in `--chat`) is blocked for the duration. Splitting into locked (pure computation) and unlocked (IO + LLM) keeps the lock hold time under 100ms in all cases. The drift signals and source health check are read-only — they don't need the lock.

Tracks challenge dismissal rate per thread. Writes weekly summary message to thread.

**Challenge dismissal rate tracking** — the reflect task computes the dismissal rate for challenge-classified items per interest thread. If challenge items from a specific thread are dismissed at > 70% rate over 4+ weeks, the reflect message flags it and suggests lowering `challenge_mode` to `adjacent`. This prevents slow negative reinforcement accumulation against topics the user values but whose challenge items are systematically misclassified. The biased challenge prompt produces genuine false positives over time — this signal catches them before they compound into meaningful weight damage.

**Cognitive passivity detection** — the reflect task tracks whether the user is steering the agent or only passively consuming its output. Two interaction modes exist: *agent-initiated* (the agent surfaces something, the user responds) and *user-initiated* (the user sends a message, asks a question, submits a URL, fires a nuance call, changes mood). A user whose interactions have been exclusively agent-initiated for 3+ weeks is a user who has stopped directing their own curiosity — they are receiving, not seeking.

**Longitudinal mood memory** — mood transitions are already written to `interactions`. The reflect task should analyze mood patterns over time and surface behavioral insights when they emerge:

- Cycle detection: if the user transitions to the same mood 3+ times in 8 weeks, note the approximate cycle length ("you tend toward depth mode roughly every 10 days")
- Domain correlation: if a specific mood consistently co-occurs with engagement on a specific interest thread, note it ("depth mode correlates with your AI self-awareness reading")
- Duration patterns: average time spent in each mood mode, whether certain moods are trending up or down in frequency

This analysis runs in reflect Phase 2 (unlocked, LLM-optional). The data comes from querying `interactions WHERE type = 'mood_set'` over the trailing 8 weeks. No new storage needed — the signal is already in `interactions`. The insight is added to `reflect_data` as a `mood_patterns` field and narrated if meaningful. If no pattern is detectable yet (< 3 mood transitions in the window), the field is omitted from the reflect message entirely.

**Dormant reactivation signal** — dormant interests only wake on explicit engagement. But a topic that went dormant 2 months ago may suddenly become relevant — 3 new items scored above the introduce threshold this week. The reflect task checks: for each dormant interest, count items in the current score cycle with `interest_score >= introduce_threshold` matched against that interest's embedding. If the count is ≥ 3, add a reactivation candidate to the reflect message:

```
→ Keel (weekly reflect)

A dormant interest is resurfacing:
  "web3 governance" (dormant since March 12)
  3 items this week scored above your introduce threshold against it.

Say "reactivate web3 governance" to bring it back, or ignore to leave it dormant.
```

No automatic reactivation. One query per dormant interest in reflect Phase 1 (locked, pure computation). The query runs against already-scored articles — no additional embedding work. Add `dormant_reactivation_candidates` to `reflect_data`.

The reflect task computes `user_initiated_pct` over the past 4 weeks:
```
user_initiated = count of interactions where type NOT IN ('engage', 'silence', 'dismiss')
                 AND source = 'user' AND not triggered by a surface message
total          = all interactions
user_initiated_pct = user_initiated / total
```

If `user_initiated_pct < 0.10` for 3+ consecutive weeks, the reflect message includes a gentle flag — not a warning, not a recommendation to use the agent less, but a question:

```
→ Keel (weekly reflect)

A small observation: for the past few weeks, I've been doing
most of the steering. Nothing wrong with that — but if you
have something specific you're thinking about, you can always
bring it here directly.
```

This is logged as a `passivity_flag` drift signal. It fires at most once every 4 weeks regardless of how long the pattern continues. It never auto-adjusts the model. The user decides whether to respond or ignore it. The agent's job is to notice, not to intervene.

**Source health check** — the reflect task checks each configured source for "source rot": sources that have provided zero items passing the introduce threshold (`interest_score >= 0.55`) in the last 30 days. These sources are fetching content but contributing nothing to the surface. The reflect message flags them as candidates for dismissal.

**Source health window starts from `exploration_end_at`, not install date.** During the exploration period, the introduce threshold is 0.45 — many sources appear healthy at this lower bar. When the threshold transitions to 0.72, sources producing 0.45–0.72 items suddenly appear to produce zero surfaceable content. If the health window started at install, these sources would be incorrectly flagged as rotten on day 30 even though they were contributing during exploration. The 30-day window only begins counting from `exploration_end_at`. If `exploration_end_at` is null (exploration still active), source health check is skipped entirely.

```
→ Keel (weekly reflect)

Source health: 2 sources haven't contributed surfaceable content in 30 days.
  - TechCrunch: 0 items above introduce threshold in 30 days
  - reddit:r/webdev: 0 items above introduce threshold in 30 days
Say "dismiss TechCrunch" or "dismiss reddit:r/webdev" to stop fetching from them.
Or say nothing — they'll continue fetching until you decide.
```

The agent proposes. The user decides. Source health never auto-dismisses.

### Silence vs. Reflect — Separation of Concerns

These are deliberately separate tasks on separate schedules:

- **Silence** (daily) — behavioral signal. Records that an item was seen and not acted on.
- **Reflect** (weekly) — analytical. Applies decay, surfaces patterns, writes summary.

Bundling them into one weekly task would delay silence signals by up to 6 days, making the interest model slow to respond to behavioral drift.

### Conversational Surface

The agent writes into a persistent thread stored in the `messages` table. The CLI polls for new messages.

**CLI spec** — `keel --chat`:

```
readline REPL. Input at bottom. Thread history displayed above.
New messages from agent appear immediately via polling loop (1s interval).
Scrollable history. `q` or Ctrl-C to exit.
No external TUI library required — rich.Console with Live display.
```

**Real-time updates** — an in-process event bus connects the `surface` task and the CLI. When surface writes a new message, it puts an event on the queue. The CLI polling loop picks it up within 1 second and renders it. This works because agent and CLI run in the same process. No sockets, no pub/sub required.

**Event schema** — all events use this structure:

```python
@dataclass
class KeelEvent:
    type: str       # "new_message" | "task_start" | "task_complete" | "error"
    payload: dict   # type-specific fields:
                    #   new_message: {"message_id": int, "role": str, "content": str, "task": str}
                    #   task_start:  {"task": str, "timestamp": str}
                    #   task_complete: {"task": str, "count": int, "timestamp": str}
                    #   error:       {"task": str, "error": str, "timestamp": str}
    timestamp: datetime
```

The CLI polls the queue every 1 second. Events of type `new_message` are rendered immediately. `task_start` / `task_complete` show a brief status line. `error` events are shown in dim red.

**Event queue has a bounded capacity with backpressure.** The queue is capped at 100 events (`queue.Queue(maxsize=100)`). When the queue is full (CLI is stuck or not reading), producers use `put_nowait()` with a try/except — if the queue is full, the event is dropped and logged as a warning. `new_message` events from the surface task are never silently dropped: if the queue is full when surface tries to emit, it clears the oldest `task_start`/`task_complete` events to make room. New message delivery takes priority over status events.

```python
def emit_event(q: queue.Queue, event: KeelEvent) -> None:
    try:
        q.put_nowait(event)
    except queue.Full:
        if event.type == "new_message":
            # Clear oldest non-message events to make room
            _clear_status_events(q)
            q.put_nowait(event)  # try once more
        else:
            logger.warning("Event queue full, dropping %s event", event.type)
```

**Renderer system prompt** — enforced on all LLM render calls:

```
"You are a research assistant summarizing content for the person who owns this agent.
Speak like someone with 30 seconds of their time. No preamble. No 'In this article.'
No 'fascinating' or 'insightful.' State the claim, state why it matters to them, stop."
```

**Challenge and adversarial content framing.** The renderer uses a different system prompt for challenge-bucket items. The architecture assumes challenge is valuable — users often don't. The framing must not feel punitive, accusatory, or like the system is judging the user's views:

```
Challenge item renderer system prompt:
"Summarize this piece in 2 sentences. It takes a different angle on a topic you follow.
No judgment. No 'this challenges your view.' Just: what it argues, and what's new about it."
```

Adversarial framing rules enforced on all challenge renders:
- Never say "this contradicts your belief" or "this challenges your view"
- Never frame the challenge as correcting the user
- Frame as: "a different angle," "another perspective," "something that argues differently"
- The user decides whether it's actually in conflict — the system doesn't tell them

The same applies to drift detection messages in reflect. "Your model is concentrating" — not "you're in an echo chamber." The agent reports what it observes, not what it thinks it means for the user's intellectual character.

**UX tone principle**: Keel observes and surfaces. It does not evaluate, correct, or judge. All system-generated text must pass this check: could this sentence feel like criticism of the user's mind? If yes, rewrite it as observation.

**Resolution in Phase 1** — Micro and Summary only. Synthesis and Connection are Phase 2.

### What You Can Do

| Response | What it does |
|----------|-------------|
| "Go further" / "More on this" | Queries stored items by topic, deepens the surface |
| "Dismiss" / "Not this" | Article dismissed, weak negative signal |
| "Undo" | Reverses the last dismiss — only valid within the same session |
| "Drop this thread" | Thread weight reduced; repeated → permanent |
| "More like this" | Interest weight increased |
| "Not this kind — more like X" | Nuance recorded, interest refined in identity model |
| "Challenge me on this" | Sets `challenge_mode: friction` for thread |
| "Stop challenging me on this" | Sets `challenge_mode: off` for thread |
| "mood: [name]" | Sets mood (depth / wander / friction / signal / ambient / open) |
| "what's my mood?" | Reports current mood and whether inferred or set |
| "forget [topic]" / "I'm not that person anymore" | Discontinuity — topic removed completely, no residual |
| "what changed in my model this week?" | Agent reports recent updates from audit log |
| "why did you surface that?" | Agent explains which interests triggered, at what score |
| "What else on X?" | Queries stored articles by topic |
| Direct question | Context assembled from stored articles; LLM responds grounded in corpus |
| *(48h no response)* | Silence recorded by daily silence task |

**What counts as `engage`**: any explicit action — "go further," "more like this," responding to the item in chat, or asking a question about it. Passive dwell time is not tracked. The CLI has no way to measure it and the system does not try. An interaction must be deliberate to count.

**Known limitation — passive consumption bias**: users who read carefully but respond rarely will accumulate silence on items they may genuinely value. Over 6–8 weeks, this creates measurable negative drift on contemplative interests — interests the user processes quietly rather than interactively. The system will drift toward topics the user engages with conversationally and away from topics they read silently. This is an inherent limitation of a CLI-based agent with no passive signal. Users who notice their feed drifting away from topics they value but rarely respond to should periodically use "more like this" to anchor those interests. This limitation is worth documenting in the README as a known behavioral property of the system.

**Dismiss is undoable within the same session** via "undo." After the session ends, a dismiss stands. This prevents accidental permanent signal from a misfire, without making dismissal feel provisional.

### Conversational QA

LLM has no persistent memory. Context assembly per question:

1. Embed the question
2. Find top-5 articles by cosine similarity from articles fetched in last 90 days
3. Pass `[title + summary[:100]]` for each as context to LLM — title plus first 100 characters of summary only
4. LLM responds grounded in that context only; states when question exceeds what's in the corpus

**Context window discipline**: top-5 with truncated summaries keeps QA context under ~600 tokens, leaving adequate room for the question and answer in small local models (llama3.2:3b, ~4k context). Top-10 with full summaries risks the "lost in the middle" failure where the model loses track of the most relevant material. If the user has a large local model with more context headroom, they can raise the limit via config:

```yaml
qa:
  top_k: 5              # number of context articles (default: 5)
  summary_truncate: 100  # characters per summary (default: 100, 0 = full)
```

Chunk-level RAG (embed article chunks, retrieve specific passages rather than full summaries) is Phase 2.

### Cold Start

`keel --init`:

- If `identity.json` exists: offer to merge or replace. Merge adds new topics without removing existing ones. Replace starts fresh.
- If no `identity.json`: run the onboarding conversation.

The init command produces three output files. Claude Code must not proceed to Day Zero fetch until all three are written:

1. `store/identity.json` — seeded identity model
2. `config/preferences.yaml` — stable user preferences
3. `config/sources.yaml` — configured feed sources

---

### Onboarding Conversation

The onboarding is a structured LLM-mediated interview. The LLM asks open questions, infers what it can, and only asks for explicit confirmation when it cannot infer. It does not present forms or ask for structured input. The conversation ends with a single extraction call that produces all three config files.

**The conversation has five phases:**

**Phase 1 — Current thinking**
```
→ Keel

I don't know you yet. Let's start simply.

What's been occupying your thinking lately?
Anything — work, ideas, questions, obsessions.
```
*Infers*: interests, rough weights, whether they feel time-sensitive or permanent.

**Phase 2 — What to avoid**
```
→ Keel

What do you want less of? Topics, sources, formats —
anything you're tired of seeing.
```
*Infers*: anti-interests (keyword blacklist), source dismissals, thread dismissals.
If the user says nothing or "I don't know", this phase is skipped silently — anti-interests start empty.

**Phase 3 — Reading mode**
```
→ Keel

How do you usually read? Quick scan of headlines,
or do you sit with things and go deep?
```
*Infers*: default resolution (`micro` for scanners, `summary` for deep readers), surface density (5–7 items for scanners, 3–4 for deep readers).

**Phase 4 — Active projects**
```
→ Keel

Are you working on anything specific right now —
a project, a piece of writing, a problem you're trying to solve?
```
*Infers*: project-provenance interests, higher initial weight (0.85), permanent decay rate, `challenge_mode: friction`.
If no project: skipped.

**Phase 5 — Challenge tolerance**
```
→ Keel

One last thing. Do you want me to show you things
that push back on what you think? Or are you here
more to go deep on what you already care about?
```
*Infers*: global `challenge_tolerance` in preferences (`high | medium | low | off`). Maps to per-interest `challenge_mode` defaults in identity model.
If unclear: defaults to `adjacent` (some challenge, not aggressive).

**Source suggestion** — after Phase 5, the LLM proposes sources based on stated interests. It does not wait for the user to supply them:
```
→ Keel

Based on what you've told me, here are some sources to start with.
Tell me which ones to keep, drop, or swap.

  • Hacker News (hn) — tech, startups, software
  • LessWrong RSS — AI, rationality, systems thinking
  • Aeon (rss) — philosophy, science, long reads
  • ArXiv cs.AI (rss) — AI research papers

Keep all? Drop any? Want something different?
```
*Infers*: `config/sources.yaml` entries. User can confirm, drop individual sources, or say "add X instead."

---

### Extraction Prompt

After the conversation ends, a single LLM call converts the full conversation transcript into structured config. This is the contract Claude Code must implement exactly.

**System prompt:**
```
You are extracting structured configuration from an onboarding conversation.
Output ONLY valid JSON matching the schema below. No preamble, no explanation,
no markdown fences. If a field cannot be inferred from the conversation,
use the default value specified in the schema.
```

**User prompt:**
```
Conversation transcript:
{full_conversation_text}

Extract the following JSON structure:

{
  "identity": {
    "interests": [
      {
        "id": "int_{4_char_alphanum}",
        "topic": "concise topic string, max 8 words",
        "weight": 0.70,
        "provenance": "chosen",
        "decay_rate": "slow | medium | permanent | fast",
        "challenge_mode": "off | adjacent | friction",
        "state": "active",
        "first_seen": "{today_iso}",
        "last_reinforced": "{today_iso}",
        "lifetime_engagements": 0
      }
    ],
    "anti_interests": ["keyword1", "keyword2"],
    "dismissals": [],
    "presentation": {
      "default_resolution": "micro | summary | synthesis",
      "max_items_per_surface": 5
    },
    "mood": "open",
    "mood_set_at": null,
    "mood_inferred": false
  },
  "preferences": {
    "challenge_tolerance": "high | medium | low | off",
    "default_resolution": "micro | summary | synthesis",
    "surface_density": 5,
    "reading_mode": "scan | deep",
    "silence_enabled": true,
    "surface_time": "07:00",
    "surface_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
  },
  "sources": [
    {
      "name": "human readable name",
      "type": "rss | hn | reddit | url",
      "url": "feed url or identifier",
      "enabled": true,
      "fetch_interval_hours": 6
    }
  ]
}

Rules:
- Extract 2–6 interests. Prefer specific over vague. "AI safety" not "AI".
- decay_rate: use "permanent" for philosophical or identity-level interests.
  Use "slow" for active intellectual threads. Use "medium" for current events.
  Use "fast" for clearly temporary curiosity spikes.
- challenge_mode: use "friction" for project interests. Use "adjacent" for
  general interests. Use "off" only if the user explicitly said they don't
  want to be challenged.
- For project interests: weight = 0.85, decay_rate = "permanent",
  challenge_mode = "friction".
- anti_interests: only include explicit statements of avoidance.
  Do not infer avoidances from topic preferences.
- surface_density: 3–4 for deep readers, 5–7 for scanners.
- Include only sources the user confirmed or did not object to.
```

**Post-extraction validation** — the init code must validate the LLM output before writing any files:
- All `interest.id` values are unique
- All `weight` values are between 0.10 and 1.0
- All `decay_rate` values are valid enum members
- `sources` list is non-empty (warn if empty, don't fail)
- If validation fails: log the raw LLM output and fall back to asking the user to re-run `--init`

---

### `config/preferences.yaml` Schema

```yaml
# User preferences — stable config set during onboarding, editable manually
# These do not decay and are not updated by the scoring pipeline.

challenge_tolerance: medium       # high | medium | low | off
                                  # Maps to per-interest challenge_mode defaults
                                  # high → friction, medium → adjacent, low → off, off → off

default_resolution: summary       # micro | summary | synthesis
                                  # micro: 1-sentence + link
                                  # summary: 3-5 sentences
                                  # synthesis: full digest paragraph

surface_density: 5                # items per surface message (3–10)
reading_mode: deep                # scan | deep — affects resolution and density defaults

silence_enabled: true             # false suspends silence penalties entirely
                                  # for users who read without responding

surface_time: "07:00"             # daily surface cron time (24h, local timezone)
surface_days:                     # which days to surface
  - mon
  - tue
  - wed
  - thu
  - fri
  - sat
  - sun

timezone: "Asia/Kolkata"          # user's local timezone for surface scheduling
                                  # inferred from system if not set
```

**`preferences.yaml` is the user's override layer.** When the surfacing or silence tasks read configuration, they check `preferences.yaml` first, then fall back to `config/config.yaml` defaults. The user can edit this file directly without re-running `--init`.

---

### Init Completion Message

After all three files are written and Day Zero fetch begins:

```
→ Keel

Setup complete.

Interests: {n} topics seeded
Sources: {n} sources configured
Surface: daily at {surface_time}

Fetching now. First surface coming shortly.
```

---

### Cold Start Continuation

**Day Zero surface** — after seeding the identity model, `--init` immediately triggers a `fetch_and_score()` cycle in the background, then surfaces the results without waiting for the 07:00 scheduler. The user should not have to wait up to 23 hours to see whether their seed topics produced a coherent epistemic space. The Day Zero surface is explicitly labeled:

**Day Zero Ollama fallback.** If Ollama is unavailable during `--init` (not installed, model not pulled, or service not running), the Day Zero surface must not silently fail. The fallback path:

1. Detect Ollama unavailability before fetch (health check: `GET http://localhost:11434/`). If unreachable, do not fetch.
2. Print a clear setup message — not a silent failure:

```
→ Keel

Ollama isn't running. I can't fetch or score yet.

To get started:
  1. Install Ollama: https://ollama.com
  2. Run: ollama pull llama3.2 && ollama pull nomic-embed-text
  3. Run: keel --init again

Or if you're using a different LLM provider, set config.llm.provider
and run --init again.
```

3. If `embed_provider: sentence_transformers` is configured (no Ollama needed for embedding), proceed with fetch and scoring but skip challenge classification and summarization. Surface with unsummarized titles only, labeled: *"[Ollama unavailable — titles only. Summaries appear when LLM is configured.]"*

This ensures first-run experience is never silent failure. The user always knows why and what to do.

```
→ Keel

Day zero — here's what I found on your first fetch.
This is sparse. It gets better as I learn what you engage with.

[surface items]
```

If the fetch returns nothing relevant (all items below introduce threshold), the agent says so plainly and suggests reviewing sources. The scheduler takes over after the Day Zero surface — the 07:00 cron fires normally the next day.



**Exploration period**: the first 7 days (or 50 interactions, whichever comes first) run with loosened thresholds — `introduce_threshold` lowered to `0.45` and `edge_probe_rate` raised to `0.6`. The system needs data before it can score meaningfully. Sparse initial engagement would otherwise produce a surface that feels too narrow too early.

**Exploration confidence signaling.** During exploration, the agent does not yet know the user. Surface messages must say so plainly — not as a disclaimer footer, but as the first line of the surface. The framing changes as confidence builds:

| Interactions | Surface opening |
|---|---|
| 0–10 | *"Day {n} — still guessing. Engage or dismiss to help me calibrate."* |
| 11–25 | *"Starting to get a sense of you. Still early."* |
| 26–49 | *"Getting there. {n} interactions in."* |
| 50+ / day 7 | *(exploration framing removed — normal surface)* |

This prevents the user from treating early surfaces as authoritative. The system is explicitly uncertain. That honesty buys trust that a confidently wrong surface destroys.

**Exploration transition uses momentum blending, not a hard cut.** When the exploration period ends, thresholds do not snap to config values overnight. The same mood momentum formula applies: `effective_threshold = config_threshold * (1 - momentum) + exploration_threshold * momentum`, blended over 3 surface cycles (approximately 3 days). A hard threshold cliff — where items surfacing at 0.50 yesterday disappear today — would feel like the system broke. The agent notes the transition when blending begins, not when it completes:

```
→ Keel

Your exploration period is ending. I'm gradually raising my standards
over the next few days — you may notice the surface tightening slightly.
This is normal. Say "keep it loose" to extend the exploration period.
```

`exploration_end_at` is stored in `identity.json` so source health and drift detection know when to start their windows. Add `exploration_end_at: date | None` to `IdentityModel`.

---

## keel-service

### What the Service Is

The service is an integration layer, not an identity holder. It provides authenticated API access to identity models that users own — it does not own them on their behalf.

The relationship between the three layers maps directly to the core thesis:

- **core** — the engine. Generic computation over any `IdentityModel`. Belongs to no one.
- **agent** — the account. One person, one identity, running on their machine. The agent *is* the person in the system — not a tool they use, but the attachment point itself.
- **service** — the integration surface. Platforms call your service to get your agent's verdict on their content. The service reads identity models that users own and provides API access to their judgment. It is a wrapper around identity, not a container for it.

When the service holds a `SqliteStore` with multiple users' identity models, it is acting as infrastructure on behalf of those users — the same way a server holds your email without owning it. Ownership stays with the person. The service is operational scaffolding.

### Sovereignty

The service is **self-hostable only**. Running it means running it on infrastructure you control — your own server, your own VPS, your own home machine. The design explicitly does not support a hosted public cloud deployment where a third party holds user identity models. The whole point is that the model stays in your infrastructure.

A platform integrating Keel calls *your* service, not ours.

### Source Pool

The service uses multi-pool ingestion by default. A single global pool is an epistemic bottleneck — it reintroduces centralized corpus curation through the back door. Three required source pools run in parallel:

| Pool | What it is | Who controls it |
|------|-----------|----------------|
| **Global pool** | High-quality canonical sources curated by the service admin | Admin-defined in `service/config/sources.yaml` |
| **User pool** | Per-user source additions — feeds, URLs, subreddits the user explicitly adds | User-defined, additive to global |
| **Injection pool** | Random and adversarial sources — low-signal, uncurated, rotating | Admin-defined; provides foreign signal candidates and baseline noise |

The injection pool is not optional. It is the source of foreign signal items and ensures the shared corpus cannot be fully curated into coherence. It should include sources that would not pass editorial quality filters — noise sources, minority viewpoints, non-English feeds, low-traffic blogs. Not to surface them as relevant, but to ensure the corpus retains genuine diversity rather than the appearance of it.

Each pool is fetched independently. Global and user pool items are scored normally. Injection pool items feed the foreign signal layer only — they are never scored against user identity models directly.

```yaml
# service/config/sources.yaml
global_pool:
  - name: "Hacker News"
    type: hn
  - name: "Ribbonfarm"
    url: "https://www.ribbonfarm.com/feed/"

injection_pool:
  enabled: true
  rotation: "weekly"         # rotate injection sources weekly
  sources:
    - url: "https://..."     # low-traffic, uncurated feeds
```

### Multi-User Identity Model

The `SqliteStore` implementation stores identity models relationally:

```sql
CREATE TABLE users (
    id          TEXT PRIMARY KEY,       -- UUID
    api_key     TEXT UNIQUE NOT NULL,   -- hashed
    created_at  DATETIME NOT NULL
);

CREATE TABLE interests (
    id              TEXT PRIMARY KEY,
    user_id         TEXT REFERENCES users(id),
    topic           TEXT NOT NULL,
    weight          REAL NOT NULL,
    provenance      TEXT NOT NULL,
    decay_rate      TEXT NOT NULL,
    challenge_mode  TEXT NOT NULL,
    first_seen      DATE NOT NULL,
    last_reinforced DATE NOT NULL
);

CREATE TABLE dismissals (
    id              INTEGER PRIMARY KEY,
    user_id         TEXT REFERENCES users(id),
    type            TEXT NOT NULL,
    target          TEXT NOT NULL,
    dismissed_at    DATE NOT NULL,
    permanent       BOOLEAN NOT NULL,
    review_after    DATE
);

CREATE TABLE anti_interests (
    user_id     TEXT REFERENCES users(id),
    keyword     TEXT NOT NULL,
    PRIMARY KEY (user_id, keyword)
);
```

Row-level access. SQLite WAL mode for concurrent reads.

### Workers

Three async worker types, all using `asyncio` + `aiohttp`:

**Fetch worker** — fetches global source pool every 6 hours. One worker, shared corpus. Stores raw articles once.

**Score worker** — per-user scoring runs queued. When new articles arrive, a scoring job is enqueued per user. Workers pick up jobs from the queue. Parallelism is configurable (`KEEL_SCORE_WORKERS`, default 4). Each worker loads a user's identity model, scores the new batch, writes results.

**Scoring fanout scaling note**: per-user scoring is O(users × items) — at 10k users each receiving 100 new items per cycle, that's 1M scoring operations per fetch cycle. Batching and worker parallelism handle moderate scale. The Phase 2 scaling path beyond that is an **approximate nearest neighbor (ANN) index** over the shared corpus embedding space (e.g. `faiss` or `hnswlib`), with per-user interest vectors precomputed and stored. Each new article gets one embedding; per-user scoring becomes a vector lookup rather than fresh pairwise computation. This reduces per-cycle cost from O(users × items) to O(items + users) amortized.

**Challenge worker pool** — challenge classification calls are queued separately. `KEEL_CHALLENGE_WORKERS` (default 2) workers process the queue. Cached by `(article_id, user_id, topic_id)`. At service scale with many users, challenge classification is best-effort — it may lag behind scoring by minutes during high load. Items awaiting challenge classification stay in introduce bucket until classified.

### Embedding Concurrency

Ollama is effectively single-threaded per model. For personal agent use this is fine. For service with concurrent scoring workers all calling Ollama simultaneously, requests queue at Ollama and latency compounds.

Options in order of simplicity:
1. **Single embedding worker** — all embedding calls go through one worker that batches requests. Adds latency but avoids thundering herd. Simplest.
2. **Multiple Ollama instances** — run 2–4 Ollama processes on different ports, round-robin. More complex, linear scale.
3. **Replace Ollama embedding with sentence-transformers in-process** — `SentenceTransformerEmbedder` runs directly in each worker process. No Ollama for embedding. Recommended for service deployment.

Default for service: `SentenceTransformerEmbedder`. Ollama used for LLM calls only (summarization, challenge classification).

### API

Authentication: API key in `Authorization: Bearer {key}` header. Keys are generated at user creation and stored hashed.

**API key lifecycle** — keys are not permanent. The service provides full lifecycle management:

```
POST   /users/{id}/keys                 Generate new key (previous key remains valid for 24h)
DELETE /users/{id}/keys/current         Revoke current key immediately
POST   /users/{id}/keys/rotate          Rotate: generate new, revoke old after 24h grace period
GET    /users/{id}/keys/status          Check current key status: active | rotating | revoked
```

Key storage: SHA-256 hashed, never stored in plaintext. On rotation, both old and new keys are active during the 24h grace period to allow in-flight requests to complete. After grace period, old key is permanently revoked.

**Compromised key recovery**: revoke immediately via `DELETE /users/{id}/keys/current`, then generate a new key via `POST /users/{id}/keys`. There is no admin override — the user must authenticate to revoke, which requires the current key. If the current key is compromised and the user cannot authenticate, the only recovery path is direct DB access by the admin (self-hosted). This is documented in `docs/security.md`.

```sql
-- Add to users schema for service
ALTER TABLE users ADD COLUMN key_created_at DATETIME;
ALTER TABLE users ADD COLUMN key_expires_at DATETIME;       -- NULL = no expiry
ALTER TABLE users ADD COLUMN rotating_key_hash TEXT;        -- active during rotation grace period
ALTER TABLE users ADD COLUMN rotating_key_expires_at DATETIME;
```

**Rate limiting**: 100 requests/minute per API key, enforced via token bucket in FastAPI middleware. Scoring API (`POST /users/{id}/score`) has a separate limit of 20 requests/minute — each call can submit up to 100 items, so this is equivalent to 2000 items/minute per user. Exceeding limits returns `429 Too Many Requests` with a `Retry-After` header.

```
POST   /users                           Create user, returns API key (shown once)
GET    /users/{id}/identity             Get full identity model
PUT    /users/{id}/identity             Replace identity model
PATCH  /users/{id}/identity/interests   Add/update interests
DELETE /users/{id}/identity/interests/{interest_id}

POST   /users/{id}/score                Score a batch of items (Scoring API)
GET    /users/{id}/feed                 Get current scored feed (Feed API)
POST   /users/{id}/interact             Record interaction
GET    /users/{id}/thread               Get conversation thread (paginated)
POST   /users/{id}/thread/message       Send message to agent
WS     /users/{id}/thread/live          WebSocket for real-time thread updates
```

### Feed Integration Protocol

Two integration models for platforms and feed generators:

---

**Model A — Scoring API**

Platform maintains its own fetching and content store. Before serving content to a user, it calls Keel to re-rank.

```
POST /users/{id}/score
Authorization: Bearer {api_key}

{
  "items": [
    {
      "id": "platform_item_id",
      "title": "Article title",
      "content": "First 500 chars of content",
      "url": "https://...",
      "source": "source_name",
      "published_at": "2026-04-10T07:00:00Z"
    }
  ]
}

Response:
{
  "scored": [
    {
      "id": "platform_item_id",
      "bucket": "filter",
      "interest_score": 0.84,
      "match_reason": [{"topic": "civilizational design", "similarity": 0.84}],
      "resolution": "summary",
      "surface": true
    }
  ]
}
```

The platform uses the `interest_score` to re-rank its feed. `surface: true` is a hint — items scoring above `filter_threshold` in the user's model. The platform decides its own cutoff and display logic. `filter_max_items` is the agent's own surface budget and does not apply here — the API always returns scores for all submitted items.

---

**Model B — Feed API**

Keel runs the full pipeline. The platform polls or subscribes for a user's scored feed.

```
GET /users/{id}/feed?since=2026-04-10T00:00:00Z
Authorization: Bearer {api_key}

Response:
{
  "items": [
    {
      "bucket": "filter",
      "title": "...",
      "url": "...",
      "source": "...",
      "resolution": "summary",
      "rendered": "The core claim: systems fail when they optimize for legibility over effectiveness.",
      "match_reason": [{"topic": "civilizational design", "similarity": 0.84}],
      "surfaced_at": "2026-04-10T07:04:00Z"
    }
  ],
  "next_since": "2026-04-10T07:04:00Z"
}
```

The platform renders the `rendered` field directly. Keel has already done the reading.

For push delivery, the platform registers a webhook:

```
POST /users/{id}/feed/webhook
{ "url": "https://platform.com/keel-hook", "secret": "..." }
```

Keel POSTs new surface batches to the webhook URL after each surface run.

---

**What a platform needs to implement to integrate:**

1. Store a Keel API key per user (user grants this via OAuth flow or manual key entry)
2. Choose Model A or B
3. Model A: call `/score` before serving feed; re-rank by `interest_score`
4. Model B: poll `/feed` or register webhook; render `rendered` field

No platform-side algorithm change required. The platform keeps its existing fetching and infrastructure. Keel replaces only the ranking/filtering step.

---

## Storage (Agent)

```sql
-- Articles
CREATE TABLE articles (
    id              INTEGER PRIMARY KEY,
    source          TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    url             TEXT UNIQUE NOT NULL,
    title           TEXT,
    content         TEXT,                   -- NULL if fetch_state = pending_content
    summary         TEXT,                   -- LLM one-sentence summary
    published_at    DATETIME,
    fetched_at      DATETIME NOT NULL,
    fetch_state     TEXT NOT NULL DEFAULT 'ready_to_score',
                                            -- pending_content: title only, awaiting two-pass content fetch
                                            -- ready_to_score: content available, not yet embedded/scored
                                            -- scored: bucket and interest_score set
                                            -- surfaced: written to thread
    interest_score  REAL,
    match_reason    TEXT,                   -- JSON: [{topic_id, topic, similarity}]
    external_score  INTEGER DEFAULT 0,      -- HN points, Reddit upvotes, etc.
    external_score_prev INTEGER DEFAULT 0,  -- score at previous fetch cycle (for momentum)
    bucket          TEXT,                   -- filter | introduce | challenge | none
    resolution      TEXT,                   -- micro | summary | synthesis | connection
    surfaced_at     DATETIME,
    surfaced_msg_id INTEGER REFERENCES messages(id)
);

-- Index for score task to find unscored articles efficiently
CREATE INDEX IF NOT EXISTS idx_articles_fetch_state ON articles(fetch_state);

-- Embeddings
-- ON DELETE CASCADE: embeddings pruned automatically when article is pruned
-- Exception: surfaced_embeddings (centroid table) is never pruned — see below
CREATE TABLE embeddings (
    article_id  INTEGER PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
    embedding   BLOB NOT NULL,             -- sqlite-utils BLOB type; numpy array serialized via .tobytes()
    model       TEXT NOT NULL,             -- e.g. "nomic-embed-text" or "bge-small-en-v1.5"
    dims        INTEGER NOT NULL           -- embedding dimensionality; catches silent model swaps
);

-- Conversational thread
CREATE TABLE messages (
    id              INTEGER PRIMARY KEY,
    role            TEXT NOT NULL,              -- agent | user
    content         TEXT NOT NULL,
    timestamp       DATETIME NOT NULL,
    task            TEXT,                       -- surface | reflect | qa | null
    parent_id       INTEGER REFERENCES messages(id),  -- for QA reply threading; NULL for top-level
    mood_at_surface TEXT                        -- mood active when surface task wrote this message; NULL for non-surface messages
);

-- Interactions
CREATE TABLE interactions (
    id          INTEGER PRIMARY KEY,
    article_id  INTEGER REFERENCES articles(id),
    message_id  INTEGER REFERENCES messages(id),
    type        TEXT NOT NULL,              -- engage | dismiss | go_further | correct | silence | challenge_set | mood_set | discontinuity
    detail      TEXT,
    timestamp   DATETIME NOT NULL
);

-- Required index for silence cap check (3× per article+message pair)
-- Without this, silence count queries become full table scans at scale
CREATE INDEX IF NOT EXISTS idx_interactions_silence
    ON interactions(article_id, message_id, type)
    WHERE type = 'silence';

-- Topic-to-article mapping
-- ON DELETE CASCADE: when an article is pruned by retention policy, its thread_items rows
-- are automatically removed. Without this, orphaned rows accumulate and slow JOIN queries.
CREATE TABLE thread_items (
    topic_id    TEXT NOT NULL,              -- matches interest.id in identity.json
    article_id  INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    similarity  REAL NOT NULL,
    week        TEXT NOT NULL,              -- ISO week: 2026-W15
    PRIMARY KEY (topic_id, article_id)
);

-- Identity model audit log (powers legibility tiers 2, 3, 4)
CREATE TABLE model_updates (
    id              INTEGER PRIMARY KEY,
    timestamp       DATETIME NOT NULL,
    interest_id     TEXT,                   -- NULL for model-level changes (mood, anti-interest)
    update_type     TEXT NOT NULL,          -- reinforcement | decay | dismissal | nuance | discontinuity | mood_set | init | provenance_promotion
    field           TEXT NOT NULL,          -- e.g. "weight", "challenge_mode", "state", or "_interest" for full object
    value_before    TEXT,                   -- JSON-encoded: full Interest object if field="_interest", else scalar value
    value_after     TEXT,                   -- JSON-encoded: full Interest object if field="_interest", else scalar value
    triggered_by    TEXT,                   -- interaction type that caused this
    article_id      INTEGER REFERENCES articles(id)  -- NULL for non-article-triggered updates
);

-- Required for Tier 3 behavioral summary queries ("what changed this week")
-- Without this, legibility queries become full table scans at ~25k rows/year
CREATE INDEX IF NOT EXISTS idx_model_updates_timestamp
    ON model_updates(timestamp);

-- Surfaced item embeddings for compression rate tracking
-- NEVER pruned by retention_days — compression history requires the full timeline.
-- Pruning these at 90 days would destroy the compression signal exactly when it becomes meaningful.
-- Only the centroid (mean vector) is stored, not individual item embeddings.
-- Storage cost: ~1.5KB per surface cycle × 365 cycles/year ≈ 550KB/year. Negligible.
CREATE TABLE surfaced_embeddings (
    id          INTEGER PRIMARY KEY,
    message_id  INTEGER REFERENCES messages(id),
    centroid    BLOB NOT NULL,              -- mean embedding of all items in this surface
    week        TEXT NOT NULL              -- ISO week for weekly centroid spread calculation
);

-- Ghost dismissals — temporary negative bias after --forget --ghost-dismiss
CREATE TABLE ghost_dismissals (
    id          INTEGER PRIMARY KEY,
    embedding   BLOB NOT NULL,             -- embedding of the discontinued interest topic
    topic       TEXT NOT NULL,             -- stored for audit; replaced with [FORGOTTEN] if --scrub used
    created_at  DATETIME NOT NULL,
    expires_at  DATETIME NOT NULL          -- created_at + ghost_dismiss_days (default 14 days)
);

-- Index for fast ghost dismissal expiry checks during scoring
CREATE INDEX IF NOT EXISTS idx_ghost_dismissals_expiry
    ON ghost_dismissals(expires_at);

-- Metrics — performance, pipeline, and quality tracking
CREATE TABLE metrics (
    id          INTEGER PRIMARY KEY,
    timestamp   DATETIME NOT NULL,
    category    TEXT NOT NULL,   -- system | pipeline | quality | error
    name        TEXT NOT NULL,
    value       REAL NOT NULL,
    unit        TEXT,
    task        TEXT             -- fetch | score | surface | silence | reflect | null
);

CREATE INDEX IF NOT EXISTS idx_metrics_category_name_time
    ON metrics(category, name, timestamp);
```

---

## Database Migrations

Schema evolution is managed via numbered SQL migration files in `migrations/`. The agent checks and applies pending migrations on startup before any tasks run.

### Migration runner contract

```python
# run.py — called before scheduler starts or any task runs
def apply_migrations(db_path: str) -> None:
    """
    Apply any pending migrations in order.
    Each migration runs in a transaction — if it fails, it rolls back and exits.
    Never applies a migration twice (tracked in schema_migrations table).
    """
```

```sql
-- Created automatically on first run if not exists
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    applied_at  DATETIME NOT NULL
);
```

### `migrations/001_initial.sql`

The initial migration is the full schema from the Storage section. Claude Code must generate this file as the exact DDL for all tables and indexes defined in this spec. It should be idempotent (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS` throughout).

The file must contain, in order:
1. `schema_migrations` table
2. `articles` table with `fetch_state` column and `idx_articles_fetch_state` index
3. `embeddings` table
4. `messages` table with `mood_at_surface` column
5. `interactions` table with `idx_interactions_silence` index
6. `thread_items` table
7. `model_updates` table
8. `surfaced_embeddings` table
9. `ghost_dismissals` table with `idx_ghost_dismissals_expiry` index

```sql
-- migrations/001_initial.sql
-- Keel Phase 1 initial schema
-- Run once on first startup. Idempotent.

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;   -- required for ON DELETE CASCADE to function in SQLite

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    applied_at  DATETIME NOT NULL
);

-- ... (full DDL as defined in Storage section) ...

INSERT OR IGNORE INTO schema_migrations (version, applied_at)
VALUES ('001_initial', datetime('now'));
```

### Adding future migrations

Each new migration is a file named `NNN_description.sql` where `NNN` is zero-padded (e.g. `002_add_project_archival.sql`). The runner applies all files in alphabetical order that aren't already in `schema_migrations`. Migrations are append-only — never modify existing migration files.

---

| Failure | Behavior |
|---------|----------|
| identity.json write fails after model_updates committed | Orphaned audit row logged. Startup reconciliation re-applies the update to identity.json before any tasks run. |
| Migration fails on startup | Log error with migration version. Exit immediately. Do not proceed — running against a partially migrated schema corrupts data. User must fix the migration manually. |
| Source unreachable | Log warning, skip, continue. Retry next cycle. |
| Ollama down | Log error, skip embedding and LLM steps. Store raw articles. Surface skipped until Ollama restored. |
| Vault wrong password | Log error, skip authenticated sources. Never prompt mid-run. |
| Partial feed fetch (timeout) | Store what was fetched. Resume next cycle. |
| DB locked | Retry: exponential backoff, 3 attempts (2s / 4s / 8s). Log and exit if all fail. |
| identity.json missing | Exit with clear message. Do not proceed. Prompt restore from backup or `--init`. |
| identity.json corrupted (invalid JSON) | Exit with clear message. Prompt `--restore-from-backup` or `--init`. Never attempt to parse a malformed file. |

### Backup and Restore

The spec relies on `os.replace()` atomic writes to prevent corruption, but hardware failure, filesystem errors, or bugs can still produce bad states. Users need a recovery path that doesn't require re-running `--init` and losing their model.

**`--backup`** — creates a timestamped snapshot of the full agent state:

```bash
keel --backup
# Creates: store/backups/keel_backup_20260415_0700.tar.gz
# Contains: identity.json, preferences.yaml, sources.yaml, keel.db
```

The scheduler runs `--backup` automatically before each weekly reflect task. Configurable:
```yaml
storage:
  auto_backup: true
  backup_retention: 4        # keep last 4 weekly backups
  backup_path: "store/backups/"
```

**`--restore-from-backup [path]`** — restores from a backup archive:

```bash
keel --restore-from-backup store/backups/keel_backup_20260408_0700.tar.gz
```

Before restoring:
1. Validates the archive is a valid Keel backup (checks for required files)
2. Shows what will be restored and the backup timestamp
3. Asks for confirmation: *"This will replace your current model. Continue? [y/N]"*
4. Creates a backup of the current state before overwriting (`keel_backup_pre_restore_{timestamp}.tar.gz`)
5. Restores and runs startup reconciliation

**`--list-backups`** — shows available backups with timestamps and model summary (interest count, last surface time).

**When the model goes wrong.** If interests have drifted in ways that don't feel right — the system has been penalizing the wrong things, a nuance call rewrote a topic badly, or a run of poor challenge classification has eroded weights — the recovery path is:

```
1. keel --list-backups
2. keel --restore-from-backup [last-known-good]
3. keel --task score --rescore-all   # rescore with restored model
```

This is the answer to "who corrects it?" — the user does, with a model state that was committed before the problem occurred.
| identity.json write conflict | `filelock` prevents concurrent writes. Write operations queue, never collide. **Known limitation**: file locking prevents structural corruption but not semantic conflicts — if reflect decays a topic and the user engages it in the same minute, the later write wins and the earlier update is lost. Transactional identity update semantics (read-modify-write as an atomic unit) are Phase 2. For Phase 1 the window is narrow enough to be acceptable. |
| LLM timeout (challenge) | Skip classification. Item stays in introduce bucket. |
| Scheduler misfire | If within `misfire_grace_time`: run immediately on wake. If beyond: skip, wait for next scheduled run. |
| Service: scoring worker crash | Job returns to queue. Retry up to 3 times. Dead-letter after 3 failures. |
| Service: challenge worker lag | Items stay in introduce bucket. Classification catches up asynchronously. Feed is never blocked. |

---

---

## Monitoring

Keel tracks performance, pipeline, and feed quality metrics continuously. All metrics are stored locally in `keel.db` and never leave the machine. Three interfaces expose them.

### Metrics Schema

```sql
CREATE TABLE metrics (
    id          INTEGER PRIMARY KEY,
    timestamp   DATETIME NOT NULL,
    category    TEXT NOT NULL,   -- system | pipeline | quality | error
    name        TEXT NOT NULL,   -- metric name (see catalogue below)
    value       REAL NOT NULL,
    unit        TEXT,            -- ms | bytes | count | ratio | tokens_per_sec
    task        TEXT             -- which task recorded this (fetch|score|surface|silence|reflect|null)
);

CREATE INDEX IF NOT EXISTS idx_metrics_category_name_time
    ON metrics(category, name, timestamp);
```

Retained for 90 days. The reflect task prunes expired rows weekly.

### Metrics Catalogue

Every task writes metrics on completion. Claude Code must instrument each task to record all of the following:

**System metrics** (written by scheduler on each task start/end):

| Name | Unit | What it measures |
|------|------|-----------------|
| `cpu_percent` | ratio | CPU utilisation at task start |
| `ram_used_gb` | bytes | RAM in use at task start |
| `gpu_vram_used_gb` | bytes | VRAM in use (if GPU present) |
| `ollama_loaded_model` | — | Which model is currently loaded in Ollama |
| `task_duration_ms` | ms | Wall time for the task |

**Pipeline metrics** (written by fetch, score, surface tasks):

| Name | Unit | What it measures |
|------|------|-----------------|
| `articles_fetched` | count | New articles stored this cycle |
| `articles_scored` | count | Articles scored this cycle |
| `articles_surfaced` | count | Articles in today's surface |
| `embed_throughput` | tokens_per_sec | Embedding speed this cycle |
| `llm_latency_ms` | ms | Average LLM call duration this cycle |
| `challenge_calls` | count | Challenge LLM calls made |
| `anti_interest_drops` | count | Items dropped by anti-interest filter |
| `ghost_penalty_hits` | count | Items penalised by active ghost dismissals |

**Feed quality metrics** (written by surface and reflect tasks):

| Name | Unit | What it measures |
|------|------|-----------------|
| `filter_bucket_pct` | ratio | Filter bucket items as fraction of surfaced |
| `introduce_bucket_pct` | ratio | Introduce bucket fraction |
| `challenge_bucket_pct` | ratio | Challenge bucket fraction |
| `edge_items_count` | count | Edge items in surface |
| `world_signal_present` | count | 1 if world signal item included, 0 if skipped |
| `foreign_signal_present` | count | 1 if foreign signal item included |
| `confirmation_ratio` | ratio | Filter items / all scored items (week rolling) |
| `source_diversity` | count | Distinct sources in this surface |
| `exploration_pulse_fired` | count | 1 if exploration pulse ran this cycle |

**Error metrics** (written on any task exception):

| Name | Unit | What it measures |
|------|------|-----------------|
| `error_count` | count | Errors in this task run |
| `error_type` | — | Exception class name |
| `ollama_timeout_count` | count | LLM/embed timeouts this cycle |
| `source_fetch_failures` | count | Sources that failed to fetch |

### `agent/monitor.py`

Reads from the `metrics` table and renders the live dashboard. The dashboard uses `rich` layout panels — no external dependencies beyond what's already in the project.

```python
# agent/monitor.py
def render_dashboard(db: sqlite3.Connection) -> Layout:
    """
    Live rich terminal dashboard. Called every 2 seconds by --monitor command.
    Four panels:

    ┌─────────────────────────────────────────────────────────────────┐
    │  TASK HEALTH             │  RESOURCES                          │
    │  fetch:   ✓ 2h ago       │  CPU:    12%                        │
    │  score:   ✓ 2h ago       │  RAM:    8.4 GB / 32 GB             │
    │  surface: ✓ 07:01        │  VRAM:   unified                    │
    │  silence: ✓ 08:00        │  Ollama: llama3.2 loaded            │
    │  reflect: ✓ Sun 08:00    │                                     │
    ├──────────────────────────┼─────────────────────────────────────┤
    │  PIPELINE (today)        │  FEED QUALITY (7 days)              │
    │  Fetched:   142 items    │  Filter:      24%  ████░            │
    │  Scored:    138 items    │  Introduce:   14%  ██░              │
    │  Surfaced:  5 items      │  Challenge:   8%   █░               │
    │  Embed:     89 tok/s     │  Confirm ratio: 0.71                │
    │  LLM avg:   1.2s         │  Compression: stable                │
    │                          │  Passivity:   ok                    │
    ├──────────────────────────┴─────────────────────────────────────┤
    │  ERRORS (last 24h)                                             │
    │  None                                                          │
    └─────────────────────────────────────────────────────────────────┘
    Press q to quit │ r to refresh │ ? for help
    """
```

**`--monitor` command** refreshes every 2 seconds. Press `q` to quit, `r` to force refresh, `e` to jump to error detail, `m` to toggle between summary and full metrics view.

### Permission on First Run

The first time `--setup` runs, before writing anything to `config/config.yaml`, it shows exactly what will be collected and asks explicit permission:

```
→ Keel Setup

Before I start, I want to be clear about what I collect and where it goes.

I will detect:
  • Your CPU model and core count
  • How much RAM your machine has
  • Whether you have a GPU and how much VRAM it has
  • Whether an NPU is present
  • Whether Ollama is installed

This information is stored in config/config.yaml on this machine only.
It is used to select models and optimise settings.
Nothing is sent anywhere — there is no telemetry, no analytics, no remote calls.

Monitoring runs locally and writes to store/keel.db on this machine only.
Metrics are retained for 90 days then deleted.

Proceed? [Y/n]:
```

If the user answers `n`, setup exits cleanly with instructions for manual configuration. It does not proceed with detection without explicit consent.

**Telemetry is permanently off.** There is no opt-in telemetry. The codebase must never contain any call to an external analytics endpoint. This is a hard constraint, not a preference.

---

## Log Rotation

Keel writes to `logs/keel.log`. Without rotation, this file grows unbounded on long-running installations.

### Agent (local)

Use Python's built-in `RotatingFileHandler` — no system dependency required:

```python
# agent/scheduler.py — logging setup
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "logs/keel.log",
    maxBytes=10 * 1024 * 1024,   # 10 MB per file
    backupCount=5,                # keep last 5 rotated files
)
handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s %(name)s: %(message)s"
))
logging.getLogger().addHandler(handler)
```

This produces `keel.log`, `keel.log.1` … `keel.log.5`. Total log footprint capped at ~60 MB. No cron, no system config, no external dependency.

For systemd deployments, `journald` handles rotation automatically — disable the file handler and let systemd capture stdout/stderr:

```ini
# docs/systemd.md unit file
[Service]
StandardOutput=journal
StandardError=journal
SyslogIdentifier=keel
```

Then: `journalctl -u keel -f` to follow, `journalctl -u keel --since "1 week ago"` for history. Journald rotation is configured in `/etc/systemd/journald.conf` (`SystemMaxUse=500M` is a reasonable ceiling).

### Service

Same `RotatingFileHandler` per worker process. For Docker deployments, write to stdout and let the container runtime handle rotation via `--log-opt max-size=10m --log-opt max-file=5`.

Add `LOG_MAX_BYTES` and `LOG_BACKUP_COUNT` to `config/config.yaml`:

```yaml
logging:
  level: "INFO"
  path: "./logs/keel.log"
  max_bytes: 10485760    # 10 MB
  backup_count: 5
```

---

## Development Mode

Claude Code and contributors need a fast development loop that does not require Ollama, live internet sources, or a populated database. `--dev` mode provides this.

```bash
keel --dev --task fetch     # fetch from fixture files, not live sources
keel --dev --task score     # score using mock embedder
keel --dev --task surface   # surface using mock LLM renderer
keel --dev --chat           # interactive CLI against dev store
keel --dev --fast-forward 7 # simulate 7 days of decay + reflect cycles
```

### What dev mode does

**Separate store** — all dev runs use `store/dev/` instead of `store/`. Never touches the production database or `identity.json`.

**Mock embedder** — `MockEmbedder` returns deterministic vectors derived from a hash of the input text. No Ollama required. Scoring behavior is realistic enough to test bucket assignment and diversity logic.

**Mock LLM** — `MockLLM` returns canned one-sentence summaries based on article title patterns. Challenge classification always returns `neither` unless the title contains a configurable trigger word (default: `"challenge"`). Renderer returns `"[MOCK SUMMARY: {title}]"`.

**Fixture sources** — `--dev` replaces all configured sources with `tests/fixtures/feeds/`. Each fixture file is a JSON array of `RawItem` objects. Provided fixtures cover:
- Normal articles matching common interest topics
- Anti-interest keyword matches (should be hard-dropped)
- Edge-band items (0.40–0.54 similarity range)
- Vague HN-style titles that need quick-fetch
- Adversarial/satirical content for challenge classification testing
- Foreign signal candidates (low relevance)

**Time injection** — `--fast-forward N` runs N simulated days: applies decay, records silence for all unseen surfaced items, runs reflect. Each simulated day takes ~1 second. Lets contributors test the full lifecycle (decay → dormant → inactive, exploration period transition, drift detection flags) without waiting.

**Seed identity** — dev mode auto-creates a `store/dev/identity.json` with 5 pre-seeded interests if none exists, so contributors can start testing immediately without running `--init`.

**Seeded randomness** — dev mode seeds all random calls with a fixed value for reproducibility. Set via `KEEL_DEV_SEED` environment variable (default: `42`). This affects edge item selection (random fraction), foreign signal selection, and diversity floor ordering. Without a fixed seed, dev runs with mock components still produce different results across runs, making debugging harder. In production mode, no seed is set — randomness is genuine.

### Dev mode structure

```
tests/
├── fixtures/
│   ├── feeds/
│   │   ├── normal.json          # Standard articles across topics
│   │   ├── edge_band.json       # Items in 0.40–0.54 similarity range
│   │   ├── anti_interest.json   # Items that should be hard-dropped
│   │   ├── challenge.json       # Items for challenge classification testing
│   │   └── foreign.json        # Low-relevance items for foreign signal pool
│   └── identity_dev.json        # Pre-seeded dev identity model
├── mocks/
│   ├── embedder.py              # MockEmbedder — deterministic vectors from hash
│   └── llm.py                   # MockLLM — canned summaries and classification
└── conftest.py                  # pytest fixtures: dev identity, fixture items, frozen time
```

### Running the full dev loop

```bash
# Start fresh dev environment
keel --dev --init-dev    # seeds store/dev/ with fixture identity

# Run one full cycle
keel --dev --task fetch
keel --dev --task score
keel --dev --task surface

# Inspect result
keel --dev --chat

# Simulate a week of usage
keel --dev --fast-forward 7

# Check drift detection output
keel --dev --task reflect

# Run all tests
pytest tests/ -v
```

No Ollama. No internet. No waiting. A contributor should be able to clone the repo and have a working development loop running in under 5 minutes.

---

## Tech Stack

| Component | Library | Notes |
|-----------|---------|-------|
| Language | Python 3.11+ | |
| Scheduler (agent) | APScheduler 3.x | Blocking mode; systemd/nohup for persistence |
| Web framework (service) | FastAPI | Async; WebSocket support; use Pydantic models for API layer |
| Feed parsing | feedparser | RSS + Atom; ETag support |
| Content extraction | trafilatura | |
| Embeddings (agent) | Ollama (nomic-embed-text) or sentence-transformers | Swappable via `embed_provider` config |
| Embeddings (service) | sentence-transformers (bge-small-en-v1.5) | In-process; no Ollama contention |
| Vector operations | numpy | Cosine similarity, MSD for drift detection |
| LLM | Protocol-injected — `OllamaLLM`, `AnthropicLLM`, or `OpenAILLM` | Swappable via `llm.provider` config; no core changes required |
| Storage | SQLite + sqlite-utils | WAL mode for service |
| Credential encryption | `cryptography` (Fernet/AES-256-GCM) | |
| File locking | `filelock` | Prevents identity.json race conditions |
| Reddit (OAuth) | PRAW | Optional; for > 10 subreddits |
| HTTP client | `httpx` | Sync + async in one library |
| CLI display | `rich` | Live display for conversational thread |
| CLI framework | `click` | Command routing for run.py |
| Dev mock embedder | `MockEmbedder` (built-in) | Deterministic vectors from hash — no Ollama needed |
| Dev mock LLM | `MockLLM` (built-in) | Canned summaries for development loop |

---

## Setup

### keel-agent

```bash
git clone https://github.com/yourusername/keel
cd keel
pip install -r requirements.txt

# Install Ollama and pull models
ollama pull llama3.2
ollama pull nomic-embed-text

# Configure sources
cp config/sources.example.yaml config/sources.yaml

# For unattended scheduled runs, set vault key in shell profile
# Add to ~/.bashrc or ~/.zshrc (restrict file permissions: chmod 600 ~/.bashrc)
export KEEL_VAULT_KEY="your-master-password"

# Initialize identity model
keel --init

# Run manually
keel --task fetch
keel --task surface

# Run on schedule
nohup keel --schedule > logs/keel.log 2>&1 &

# Chat
keel --chat

# Vault
keel --vault add --service reddit --key client_id --value abc123

# Status
keel --status
```

### keel-service

```bash
cd service
pip install -r requirements.txt

# Configure global source pool
cp config/sources.example.yaml config/sources.yaml

# Initialize DB
python manage.py init-db

# Start API server
uvicorn api.app:app --host 0.0.0.0 --port 8000

# Start workers (separate process)
python workers/run.py

# Create first user
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "your-name"}'
# Returns: { "id": "...", "api_key": "..." }
```

---

## Testing Strategy

Three categories of tests, each with distinct requirements:

### Core scoring tests (deterministic)

Scoring must be deterministic and testable without Ollama running. Use `SentenceTransformerEmbedder` in tests — it runs in-process without a server dependency.

Key requirements:
- **Freeze time** for decay and reflect tests — inject `as_of_date` parameter rather than calling `date.today()` directly anywhere in core. All decay and state transition functions already take `as_of_date` — enforce this discipline throughout.
- **Synthetic feeds** — a `tests/fixtures/` directory with small pre-built `RawItem` lists covering: normal articles, anti-interest matches, edge-band items, HN-style vague titles, adversarial content.
- **Scoring replay** — given a fixed `IdentityModel` and `RawItem` list, `score()` must return identical results every run. No randomness in the scoring path (random edge selection happens in the surfacer, not the scorer).

### Agent integration tests

Test the full fetch → score → surface loop against synthetic data. Mock source adapters return fixture items. Mock LLM returns deterministic strings. Test:
- Interaction types write correct values to identity model
- Silence detection fires after 48h (using frozen time)
- Reflect task computes correct drift signals
- Cold start produces a valid identity model from a known init conversation

### CLI smoke tests

`keel --task fetch --dry-run` — fetch sources, print what would be stored, write nothing. Every task should support `--dry-run`. This is the primary tool for verifying a new installation works before the first real surface.

```python
# tests/core/test_scorer.py — example pattern
from datetime import date
from core.scoring.scorer import score
from tests.mocks.embedder import MockEmbedder   # use mock in core tests, not real embedder

def test_score_deterministic(sample_identity, sample_items):
    embedder = MockEmbedder()
    result1 = score(sample_items, sample_identity, embedder)
    result2 = score(sample_items, sample_identity, embedder)
    assert [r.bucket for r in result1] == [r.bucket for r in result2]

def test_anti_interest_hard_drop(sample_identity, sample_items):
    sample_identity.anti_interests = ["bitcoin"]
    bitcoin_item = make_item(title="Bitcoin hits new high")
    results = score([bitcoin_item], sample_identity, embedder)
    assert results[0].bucket == "none"
    assert results[0].interest_score == 0.0
```

Add `--dry-run` to Phase 1 checklist. Add `tests/fixtures/` with at least 20 synthetic items covering all source types and edge cases.

---

---

## Hardware Detection and Setup

`keel --setup` must be run once before `--init`. It detects the machine's hardware, installs all required dependencies, pulls the right LLM and embedding models for the detected hardware profile, runs a short benchmark, and writes an optimised `config/config.yaml`. The user never has to know which model to pull or what batch size to use.

**The correct first-run sequence is:**
```bash
pip install -e .
keel --setup    # detect hardware, install Ollama, pull models, write config
keel --init     # onboarding conversation, seeds identity
keel --schedule # start agent
```

`--setup` is safe to re-run. It detects what's already installed, skips steps that are complete, and re-benchmarks if hardware has changed.

---

### Hardware Detection

`agent/setup/detect.py` — runs at `--setup` time. Produces a `HardwareProfile` dataclass.

```python
@dataclass
class HardwareProfile:
    cpu_cores: int
    cpu_brand: str              # "Intel" | "AMD" | "Apple"
    ram_gb: float
    gpu_vendor: str | None      # "NVIDIA" | "AMD" | "Intel" | "Apple" | None
    gpu_name: str | None
    gpu_vram_gb: float | None   # None if shared/unified memory
    unified_memory: bool        # True for Apple Silicon, AMD APUs with shared RAM
    unified_memory_gb: float | None
    has_npu: bool               # True if NPU detected (AMD XDNA, Intel NPU, Apple ANE)
    cuda_available: bool
    rocm_available: bool
    mps_available: bool         # Apple Metal Performance Shaders
    ollama_installed: bool
    ollama_version: str | None
```

Detection logic:

```python
# agent/setup/detect.py
import platform, subprocess, shutil
import torch  # only imported if available — graceful fallback

def detect_hardware() -> HardwareProfile:
    cpu_info = _get_cpu_info()      # platform + /proc/cpuinfo on Linux
    ram_gb   = _get_ram_gb()        # psutil.virtual_memory().total
    gpu_info = _detect_gpu()        # torch.cuda / torch.backends.mps / rocm-smi
    npu      = _detect_npu()        # check for /dev/accel* or Windows NPU APIs
    ollama   = _detect_ollama()     # shutil.which("ollama") + version check
    return HardwareProfile(...)
```

**GPU detection priority order:**
1. `torch.cuda.is_available()` → NVIDIA CUDA
2. `torch.backends.mps.is_available()` → Apple Silicon Metal
3. `subprocess.run(["rocm-smi"])` exits 0 → AMD ROCm
4. Check for Intel Arc: `intel_extension_for_pytorch` importable
5. None found → CPU-only mode

**NPU detection:**
- AMD XDNA (Ryzen AI): `/dev/accel/accel0` exists OR `ryzen_ai` in `/proc/cpuinfo` flags
- Intel NPU: `openvino` package importable + Intel NPU device listed
- Apple ANE: covered by MPS — no separate detection needed

---

### Hardware Profiles and Model Selection

Based on the detected hardware, `--setup` selects the optimal models:

| Profile | Condition | LLM | Embedder | Notes |
|---------|-----------|-----|----------|-------|
| **High-end GPU** | VRAM >= 16GB (NVIDIA/AMD) | `llama3.2` (8B) | `nomic-embed-text` via Ollama | Full quality |
| **Mid-range GPU** | VRAM 8–16GB | `llama3.2` (8B, Q4_K_M) | `nomic-embed-text` via Ollama | Quantised for fit |
| **Low-end GPU / APU** | VRAM/unified 4–8GB | `llama3.2:3b` | `nomic-embed-text` via Ollama | Smaller model |
| **Unified memory (large)** | unified >= 16GB (Apple/AMD APU) | `llama3.2` (8B) | `nomic-embed-text` via Ollama | Shared RAM handles it |
| **Unified memory (small)** | unified 8–16GB | `llama3.2:3b` | `bge-small-en-v1.5` (local) | Embedder in-process |
| **CPU only** | No GPU detected | `llama3.2:3b` | `bge-small-en-v1.5` (local) | Warn: slow, still functional |

**Quantisation selection** — Ollama model tags:

| Available VRAM/RAM | Model tag |
|---|---|
| >= 16GB | `llama3.2` (default, full precision) |
| 8–16GB | `llama3.2:latest` with `Q4_K_M` via Modelfile |
| 4–8GB | `llama3.2:3b` |
| < 4GB | `llama3.2:3b-instruct-q4_K_M` |

The setup task writes the selected model name into `config/config.yaml`. `run.py` reads it. The user never touches model names directly.

---

### Dependency Installation

`--setup` installs everything needed. It does not assume anything is pre-installed except Python 3.11+.

```python
# agent/setup/installer.py

def run_setup(profile: HardwareProfile) -> None:
    _check_python_version()
    _install_python_deps(profile)
    _install_ollama_if_missing(profile)
    _pull_ollama_models(profile)
    _install_sentencetransformers_if_needed(profile)
    _run_benchmark(profile)
    _write_optimised_config(profile)
    _print_setup_summary(profile)
```

**Python dependencies** — already handled by `pip install -e .`. Setup verifies they installed correctly by importing each one:

```python
def _install_python_deps(profile: HardwareProfile) -> None:
    required = ["apscheduler", "click", "feedparser", "filelock",
                "numpy", "requests", "rich", "pyyaml", "sqlite_utils",
                "trafilatura", "cryptography"]
    missing = [pkg for pkg in required if not _importable(pkg)]
    if missing:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", "."],
            check=True
        )
```

**PyTorch with hardware backend** — installed conditionally:

```python
def _install_pytorch(profile: HardwareProfile) -> None:
    if profile.cuda_available:
        # Already has CUDA torch — skip
        return
    if profile.rocm_available:
        subprocess.run([sys.executable, "-m", "pip", "install",
            "torch", "--index-url",
            "https://download.pytorch.org/whl/rocm6.0"], check=True)
    elif profile.mps_available:
        subprocess.run([sys.executable, "-m", "pip", "install", "torch"], check=True)
    else:
        subprocess.run([sys.executable, "-m", "pip", "install",
            "torch", "--index-url",
            "https://download.pytorch.org/whl/cpu"], check=True)
```

**Ollama installation** — if not found:

```python
def _install_ollama_if_missing(profile: HardwareProfile) -> None:
    if profile.ollama_installed:
        print(f"✓ Ollama {profile.ollama_version} already installed")
        return

    system = platform.system()
    if system == "Linux":
        subprocess.run(
            "curl -fsSL https://ollama.com/install.sh | sh",
            shell=True, check=True
        )
    elif system == "Darwin":
        print("Install Ollama from https://ollama.com/download/mac")
        print("Then re-run: keel --setup")
        sys.exit(1)
    elif system == "Windows":
        print("Install Ollama from https://ollama.com/download/windows")
        print("Then re-run: keel --setup")
        sys.exit(1)
```

On Linux, the install script handles ROCm and CUDA detection automatically. Ollama's own installer picks the right GPU backend.

**Model pull:**

```python
def _pull_ollama_models(profile: HardwareProfile) -> None:
    models = _select_models(profile)   # returns {"llm": "llama3.2:3b", "embed": "nomic-embed-text"}

    for role, model in models.items():
        print(f"Pulling {role} model: {model}")
        result = subprocess.run(["ollama", "pull", model])
        if result.returncode != 0:
            print(f"Failed to pull {model}. Check Ollama is running: ollama serve")
            sys.exit(1)
        print(f"✓ {model} ready")
```

---

### Benchmark and Config Optimisation

After models are pulled, `--setup` runs a short benchmark to measure actual throughput on this machine and writes optimal config values.

```python
def _run_benchmark(profile: HardwareProfile) -> BenchmarkResult:
    """
    Runs 3 tests:
    1. Embed 20 short texts → measures tokens/sec for embedder
    2. LLM complete() with 50-token prompt → measures generation latency
    3. Score 50 items against 5 interests → measures scoring throughput

    Returns optimal chunk sizes and concurrency settings.
    """
```

**What gets tuned in `config/config.yaml`:**

```yaml
# Written by --setup based on benchmark results
llm:
  provider: "ollama"
  model: "llama3.2"           # selected by hardware profile
  embed_provider: "ollama"
  embed_model: "nomic-embed-text"
  embed_chunk_size: 8         # tuned: higher on fast GPU, lower on CPU
  llm_timeout_seconds: 30     # tuned: latency-based
  backend: "rocm"             # cuda | rocm | mps | cpu — detected

hardware:
  gpu_vendor: "AMD"
  gpu_name: "Radeon 890M"
  unified_memory: true
  unified_memory_gb: 32
  has_npu: true
  profile: "unified_large"    # profile name for diagnostics
```

The `hardware:` block is read-only after setup — it's documentation of what was detected, not runtime config. Tasks read from `llm:` only.

---

### Setup Output

A successful `--setup` run prints:

```
→ Keel Setup

Detecting hardware...
  CPU:  AMD Ryzen AI 9 HX 370 (12 cores)
  RAM:  32.0 GB unified memory
  GPU:  AMD Radeon 890M (integrated, ROCm available)
  NPU:  Detected (AMD XDNA 2)
  Profile: unified_large

Installing dependencies...
  ✓ Python packages verified
  ✓ PyTorch (ROCm) installed
  ✓ Ollama 0.3.12 already installed

Pulling models...
  ✓ llama3.2 (8B) — 4.7 GB
  ✓ nomic-embed-text — 274 MB

Benchmarking...
  Embedding:  142 tokens/sec
  LLM:        18 tokens/sec (generation)
  Scoring:    50 items in 0.4s

Optimising config...
  embed_chunk_size: 10  (fast GPU — higher throughput)
  llm_timeout:      45s (conservative for 8B on unified memory)

✓ Setup complete. Config written to config/config.yaml

Next step: keel --init
```

If anything fails, setup exits with a clear message and the exact command to fix it. It never leaves the system in a half-configured state — if model pull fails, it removes partial downloads and reports cleanly.

---

### Re-setup on Hardware Change

If the machine changes (new GPU, ROCm update, model upgrade needed), `--setup` can be re-run:

```bash
keel --setup --redetect   # force full re-detection even if config exists
keel --setup --models-only  # skip hardware detection, just re-pull models
```

`--redetect` overwrites the `hardware:` block and re-benchmarks. The `llm:` block is updated with new model selections. The identity model, preferences, and sources are untouched.

---

## Implementation Guide for Claude Code

This section gives Claude Code the build order, file contracts, and decisions already made so it doesn't need to invent them.

### Build Order (Phase 1)

Follow this sequence strictly. Each layer depends on the previous.

```
1.  core/models.py              — all data shapes AND core protocols: RawItem, ScoredArticle,
                                   Interest, IdentityModel, FetchContext, ModelUpdate,
                                   LLMClient (protocol), plus all other dataclasses
```
2.  core/identity/store.py      — IdentityModelStore protocol only (no implementations)
3.  core/identity/model.py      — to_dict, from_dict (pure serialization)
4.  core/identity/updater.py    — apply_decay, apply_interaction, transition_states,
                                   nuance_interest (pure functions)
5.  core/scoring/embedder.py    — Embedder protocol only (no implementations)
6.  core/scoring/scorer.py      — score() pure function
7.  core/scoring/challenger.py  — classify_batch() — takes injected LLMClient
8.  core/sources/protocol.py    — FeedSource protocol, FetchContext, RawItem
9.  core/expansion/expander.py  — find_edge_candidates(), score_world_signal() (pure)
10. core/expansion/mood.py      — apply_mood_thresholds(), infer_mood() (pure)
11. agent/setup/detect.py       — HardwareProfile detection (CPU, GPU, NPU, Ollama)
12. agent/setup/installer.py    — Ollama install, model pull, dep verification
13. agent/setup/benchmark.py    — throughput benchmark → optimised config values
14. agent/store.py              — JsonStore implementing IdentityModelStore (file IO)
15. agent/embedders.py          — OllamaEmbedder, SentenceTransformerEmbedder
16. agent/ledger.py             — audit log write/read (DB IO)
17. agent/llm.py                — OllamaLLM, AnthropicLLM, OpenAILLM
18. agent/resources.py          — OllamaResourceManager (priority lock)
19. agent/sources/rss.py        — feedparser adapter
20. agent/sources/hn.py         — Algolia API adapter with two-pass
21. agent/sources/reddit.py     — public JSON adapter with two-pass
22. agent/sources/url.py        — trafilatura adapter
23. agent/vault/vault.py        — AES-256 vault
24. agent/vault/session.py      — build_session() → FetchContext with credentials
25. agent/surface/thread.py     — write_message(), read_history(), KeelEvent
26. agent/surface/renderer.py   — render_item(), assemble_surface_message()
27. agent/tasks/fetch.py        — fetch all sources, update fetch_state
28. agent/tasks/score.py        — calls core.scorer.score() with injected deps
29. agent/tasks/silence.py      — daily silence with one-per-surfacing-event rule
30. agent/tasks/surface.py      — priority chain, diversity floor, mood, exploration
31. agent/tasks/reflect.py      — calls core updater, reads signals, writes summary
32. agent/scheduler.py          — APScheduler setup, SIGTERM handling
33. agent/surface/cli.py        — rich REPL with polling loop
34. agent/init.py               — cold start conversation; seeds identity model
35. run.py                      — entry point; --setup wires hardware; all subcommands
36. tests/mocks/embedder.py     — MockEmbedder (deterministic hash vectors)
37. tests/mocks/llm.py          — MockLLM (canned responses)
38. tests/mocks/store.py        — InMemoryStore implementing IdentityModelStore
39. tests/conftest.py           — fixtures, frozen dates
40. tests/core/test_scorer.py   — deterministic scoring tests (no IO)
41. tests/core/test_decay.py    — decay and state transition tests (no IO)
42. migrations/001_initial.sql  — initial schema
```

### Key Contracts Claude Code Must Respect

**core/ is pure processing. No IO. No storage. No user details. No concrete implementations.**

Core contains exactly three kinds of things:
1. **Data shapes** — dataclasses that describe what things look like (`models.py`)
2. **Protocols** — interfaces that describe what things can do (`IdentityModelStore`, `Embedder`, `FeedSource`, `LLMClient`)
3. **Pure functions** — take data in, return data out, no side effects (`updater.py`, `scorer.py`, `challenger.py`, `mood.py`, `expander.py`)

Core never opens a file. Never writes to a database. Never makes a network call. Never knows a user's name, source URL, or credential. Never instantiates a concrete storage class, a concrete embedder, or a concrete LLM client. All of those are injected by the application layer.

The agent does a lot of its work by calling core functions — that is the intended design. `fetch.py` fetches and stores. `score.py` calls `core.scorer.score()` with injected embedder and identity model. `reflect.py` calls `core.updater.apply_decay()` and `core.updater.transition_states()`. Core does the computation. Agent does the orchestration and IO.

**Concrete implementations live in the application layer:**
- `JsonStore` → `agent/store.py`
- `SqliteStore` → `service/store.py`
- `OllamaEmbedder`, `SentenceTransformerEmbedder` → `agent/embedders.py`
- `OllamaLLM`, `AnthropicLLM`, `OpenAILLM` → `agent/llm.py`
- Audit ledger write/read → `agent/ledger.py`
- Source adapters → `agent/sources/`
- Vault and session building → `agent/vault/`

### Data Flow Trace

This is the complete path from fetch to surface. Every step maps to a file. Claude Code must not deviate from this flow.

```
FETCH CYCLE (triggered by APScheduler every 6h)
─────────────────────────────────────────────
agent/tasks/fetch.py
  ↓ loads source configs from config/sources.yaml
  ↓ calls agent/vault/session.py → build_session() → FetchContext
  ↓ instantiates agent/sources/{rss,hn,reddit,url}.py adapters
  ↓ calls adapter.fetch(context) → list[RawItem]      [core protocol]
  ↓ deduplicates by URL against DB
  ↓ writes new articles to DB with fetch_state='ready_to_score'
  ↓ calls agent/tasks/score.py (continuation, not scheduled)

SCORE CYCLE (continuation of fetch)
─────────────────────────────────────────────
agent/tasks/score.py
  ↓ loads identity model via agent/store.py JsonStore  [core protocol]
  ↓ loads articles WHERE fetch_state='ready_to_score'
  ↓ calls agent/embedders.py OllamaEmbedder            [core protocol]
      via agent/resources.py OllamaResourceManager (sequential lock)
  ↓ calls core/scoring/scorer.py score(items, identity, embedder)
      → list[ScoredArticle]                            [pure function]
  ↓ updates articles in DB: bucket, interest_score, fetch_state='scored'
  ↓ calls core/scoring/challenger.py classify_batch()  [pure, injected LLM]
      via agent/resources.py OllamaResourceManager (one item at a time)
  ↓ updates articles with challenge classification

SURFACE CYCLE (APScheduler cron at surface_time)
─────────────────────────────────────────────
agent/tasks/surface.py
  ↓ loads identity model via agent/store.py JsonStore
  ↓ loads scored articles from DB
  ↓ calls core/expansion/mood.py apply_mood_thresholds()  [pure]
  ↓ calls core/expansion/expander.py find_edge_candidates() [pure]
  ↓ calls core/expansion/expander.py score_world_signal()   [pure]
  ↓ applies priority chain + diversity floor + exploration pulse
  ↓ selects items for surface
  ↓ calls agent/surface/renderer.py render_item() via LLM
  ↓ writes surface message to agent/surface/thread.py
  ↓ emits KeelEvent to CLI queue
  ↓ updates articles: fetch_state='surfaced', surfaced_at, surfaced_msg_id

INTERACTION (user input in CLI)
─────────────────────────────────────────────
agent/surface/cli.py
  ↓ receives user input
  ↓ calls core/identity/updater.py apply_interaction(model, interaction)
      → (new_model, list[ModelUpdate])                 [pure function]
  ↓ writes ModelUpdate rows to DB via agent/ledger.py  [write-ahead]
  ↓ saves new_model via agent/store.py JsonStore       [atomic write]

SILENCE CYCLE (APScheduler daily)
─────────────────────────────────────────────
agent/tasks/silence.py
  ↓ loads surfaced items with no interaction > 48h
  ↓ applies mood awareness check (skip if depth mode)
  ↓ calls core/identity/updater.py apply_interaction() for each silence
      → (new_model, list[ModelUpdate])
  ↓ writes ModelUpdate rows via agent/ledger.py
  ↓ saves updated model via agent/store.py

REFLECT CYCLE (APScheduler weekly)
─────────────────────────────────────────────
agent/tasks/reflect.py
  PHASE 1 (locked):
  ↓ acquires identity lock
  ↓ loads model via agent/store.py
  ↓ calls core/identity/updater.py apply_decay()
      → (new_model, list[ModelUpdate])                 [pure function]
  ↓ calls core/identity/updater.py transition_states()
      → (new_model, list[ModelUpdate])                 [pure function]
  ↓ writes ModelUpdate rows via agent/ledger.py
  ↓ saves new_model via agent/store.py
  ↓ releases lock

  PHASE 2 (unlocked):
  ↓ reads drift signals from DB (velocity, compression, passivity, etc.)
  ↓ reads source health from DB
  ↓ calls core/expansion/mood.py infer_mood()          [pure]
  ↓ calls LLM for narrative synthesis (if signals present)
  ↓ writes weekly summary message via agent/surface/thread.py
  ↓ runs ghost_dismissals cleanup (DELETE WHERE expires_at < now)
  ↓ auto-backup if enabled
```

This trace must hold after every code change. If a task in agent needs data, it reads from the DB. If it needs computation, it calls a core pure function. Core never reads from the DB. Core never writes to anything.

**core/ has no LLM or resource manager.** `core/` receives an already-configured `LLMClient` and `Embedder`. It never imports `OllamaResourceManager`, never references Ollama by name, never knows whether the LLM is local or cloud. `OllamaResourceManager` lives in `agent/resources.py` and is wired at startup in `run.py` only when `config.llm.provider == "ollama"`.

**Swapping LLM requires zero core changes.** Change `config.llm.provider` and the implementation injected in `run.py`. Nothing else changes.

**Source adapters take `FetchContext`, not `requests.Session`.** `FetchContext` holds an optional session and optional credentials. HTTP adapters use `context.session`. Non-HTTP adapters (email, file) use `context.credentials`. Never pass a raw `requests.Session` directly.

**Atomic identity updates.** Every function that modifies `IdentityModel` must follow: `with store.lock(user_id): model = store.load(); updated = pure_fn(model); store.save(updated)`. No exceptions. LLM calls must never happen while the identity lock is held.

**`fetch_state` lifecycle.** Articles are inserted with `fetch_state='pending_content'` if they need a content fetch (HN/Reddit two-pass mid-range items) or `fetch_state='ready_to_score'` otherwise. Score task queries `WHERE fetch_state='ready_to_score'`. After scoring: `fetch_state='scored'`. After surfacing: `fetch_state='surfaced'`.

**Score is not scheduled.** Score runs as fetch's continuation (`fetch_and_score()` in `run.py`), not as an independent APScheduler job. Only `fetch`, `surface`, `silence`, and `reflect` are registered jobs.

**Foreign signal never writes to identity.** Items drawn for foreign signal are never passed to `apply_interaction()`. If the user explicitly says "add this to my model," that is a separate `given` provenance interaction, not automatic absorption.

**Dev mode uses seeded randomness.** All `random` and `np.random` calls in dev mode use `KEEL_DEV_SEED` (default `42`). Production: no seed.

**Nuance audit entries store topic strings.** `model_updates.value_before` and `value_after` store human-readable topic strings, not interest IDs.

**Grace period check in `transition_states()`.** Skip `Active → Inactive` for any interest where `(as_of - interest.first_seen).days < 14`.

**Epsilon floor detection.** Use `interest.weight <= 0.105` everywhere weight floor is tested. Never `== 0.10`.

**Reflect runs in two phases.** Phase 1 acquires identity lock, applies decay and transitions, saves, releases. Phase 2 runs without the lock. LLM calls are always in Phase 2.

### `run.py` Startup Sequence

`run.py` is the entry point for every command. Before doing anything else, it runs a fixed startup sequence. Claude Code must implement this exact order:

```
1. Python version check (sys.version_info >= 3.11, else exit)
2. Load config/config.yaml
3. Load config/preferences.yaml (if exists)
4. Load config/sources.yaml (if exists)
5. apply_migrations(db_path)          — run any pending migrations, exit on failure
6. reconcile_identity(db, store)      — re-apply orphaned model_updates to identity.json
7. Clean up identity.tmp.json (if exists from crashed write)
8. Wire dependencies:
     llm      = build_llm(config)          # OllamaLLM | AnthropicLLM | OpenAILLM
     embedder = build_embedder(config)     # OllamaEmbedder | SentenceTransformerEmbedder
     store    = JsonStore(store_path)
     sources  = load_sources(sources_yaml) # instantiates agent/sources/ adapters
9. Dispatch to subcommand (--init | --schedule | --chat | --task | --measure | etc.)
```

Steps 1–8 run for every command including `--init`. Step 8 skips sources if `sources.yaml` doesn't exist yet (first run). The scheduler is only started by `--schedule`. All other subcommands run once and exit.

```python
# run.py — abbreviated structure
@click.group()
def cli(): pass

@cli.command()
def setup(): ...           # hardware detection, dependency install, model pull, config optimise

@cli.command()
def init(): ...            # onboarding conversation

@cli.command()
def schedule(): ...        # start APScheduler + CLI REPL

@cli.command()
def chat(): ...            # open CLI REPL without scheduler (debugging)

@cli.command()
@click.option("--task", type=click.Choice(["fetch","score","surface","silence","reflect"]))
def task(task): ...        # run a single task manually

@cli.command()
@click.option("--command", type=click.Choice(["scoring-distribution","interest-health",
                                               "surface-quality","challenge-efficacy",
                                               "drift","silence"]))
def measure(command): ...  # measurement reports

@cli.command()
def status(): ...          # last run times, DB size, model summary

@cli.command()
def backup(): ...

@cli.command()
@click.argument("path")
def restore_from_backup(path): ...

@cli.command()
def list_backups(): ...

@cli.command()
def update_preferences(): ...
```

---

### `pyproject.toml`

Claude Code must generate `pyproject.toml` for the project. Use `setuptools` as the build backend. This is the authoritative package definition — `requirements.txt` files are generated from it.

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "keel"
version = "0.1.0"
description = "Personal feed agent. The account is the agent."
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"
dependencies = [
    "apscheduler>=3.10",
    "click>=8.1",
    "feedparser>=6.0",
    "filelock>=3.12",
    "numpy>=1.26",
    "ollama>=0.1.8",
    "requests>=2.31",
    "rich>=13.7",
    "sentence-transformers>=2.6",
    "trafilatura>=1.8",
    "cryptography>=42.0",
    "pyyaml>=6.0",
    "sqlite-utils>=3.35",
    "psutil>=5.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "freezegun>=1.4",
    "responses>=0.25",
]

[project.scripts]
keel = "run:cli"

[tool.setuptools.packages.find]
where = ["."]
include = ["core*", "agent*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### `LICENSE`

MIT license. Claude Code must create a `LICENSE` file at the repo root with the standard MIT text, year 2025, author "A Perceptual Keel".

### `setup.sh`

Claude Code must create `setup.sh` at the repo root. This is the single command a new user runs after cloning. It must be idempotent — safe to run multiple times.

```bash
#!/usr/bin/env bash
# Keel setup script
# Usage: bash setup.sh
# Safe to re-run. Skips steps already completed.

set -e

echo "=== Keel setup ==="

# 1. Python version check
python3 --version | grep -E "3\.(11|12|13)" > /dev/null 2>&1 || {
    echo "ERROR: Python 3.11+ required. Install from https://python.org"
    exit 1
}

# 2. Virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# 3. Install dependencies
echo "Installing Python dependencies..."
pip install -e ".[dev]" --quiet

# 4. Ollama check / install
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# 5. Pull required models (skip if already present)
echo "Pulling Ollama models (this may take a few minutes on first run)..."
ollama pull llama3.2 2>/dev/null || true
ollama pull nomic-embed-text 2>/dev/null || true

# 6. Create default config if not present
if [ ! -f "config/config.yaml" ]; then
    echo "Creating default config..."
    cp config/config.yaml.example config/config.yaml
fi
if [ ! -f "config/sources.yaml" ]; then
    cp config/sources.yaml.example config/sources.yaml
fi

# 7. Create store directory
mkdir -p store logs

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next: run 'keel --init' to set up your identity model"
echo "Then: run 'keel --schedule' to start the background agent"
echo "Then: run 'keel --chat' to open the conversation interface"
echo ""
echo "Or run 'keel --dev --chat' to try without Ollama using mock components"
```

`setup.sh` must be executable (`chmod +x setup.sh` noted in README).

### Config examples

Claude Code must create `config/config.yaml.example` and `config/sources.yaml.example` with sensible defaults and comments on every field. These are the files a new user copies and edits. They must contain every key from the Configuration Reference section with its default value and a one-line comment explaining it.

### GitHub repo structure

The repo root must contain exactly:
```
LICENSE
README.md
setup.sh
pyproject.toml
config/
    config.yaml.example
    sources.yaml.example
    preferences.yaml.example
core/
agent/
migrations/
tests/
run.py
docs/
    systemd.md
    hardware.md
```

`docs/systemd.md` — unit file for running the scheduler as a systemd service on Ubuntu. `docs/hardware.md` — notes on running with Ollama on various hardware (CPU-only, iGPU, ROCm, CUDA).

The README already in the spec is the public-facing README. It must cover: clone → setup.sh → --init → --schedule → --chat as the complete getting-started path, in that order, with no assumed knowledge beyond having Python 3.11+ installed.

---

### `tests/fixtures/` Schema

`--dev` mode replaces all configured sources with fixture feeds. Each fixture file is a JSON array of `RawItem` objects. `RawItem` has the following fields:

```python
@dataclass
class RawItem:
    id: str             # unique per source — URL for most, e.g. "https://..."
    source: str         # source name matching sources.yaml key
    source_type: str    # "rss" | "hn" | "reddit" | "url"
    title: str
    url: str
    content: str | None  # None if fetch_state will be pending_content
    published_at: datetime | None
    fetched_at: datetime
    external_score: int  # 0 for RSS; HN points / Reddit upvotes for those sources
    external_score_prev: int  # 0 on first fetch
```

Fixture files live at `tests/fixtures/feeds/{source_name}.json`. The dev-mode fetch task loads these instead of making network calls.

**Required fixture coverage — Claude Code must generate all of these:**

```
tests/fixtures/feeds/
    rss_general.json         # 10 typical RSS items across diverse topics
    hn_high_score.json       # 5 HN items with high external_score (filter candidates)
    hn_mid_score.json        # 5 HN items scoring 0.50-0.72 (introduce candidates)
    reddit_tech.json         # 5 Reddit items from a tech subreddit
    anti_interest_match.json # 3 items containing anti-interest keywords
    edge_band.json           # 5 items designed to score 0.40-0.54 (edge candidates)
    challenge_material.json  # 3 items with stance that challenges test interests
    foreign_signal.json      # 5 low-relevance items (score < 0.30) for foreign signal pool
    empty_feed.json          # [] — tests empty source graceful handling
```

Each item in a fixture file must have realistic `title`, `content` (minimum 100 words), and `url`. `fetched_at` should be set to a relative offset from the test's frozen date. `MockEmbedder` produces deterministic vectors from content hash — fixture content must be distinct enough that items don't accidentally hash to the same vector.

---

### `README.md`

Claude Code must generate a detailed `README.md` that a technically capable person can follow from zero to running agent without needing to read the spec. Every command must be copy-pasteable. Every decision must be explained.

```markdown
# Keel

**Your feed agent. Your identity. Your machine.**

Keel is a personal feed agent that runs locally. It reads sources you configure,
learns what you care about through your engagement, and surfaces a curated briefing
to a terminal thread every morning. No platform. No account. No algorithm that
doesn't belong to you.

The account is the agent. Your identity model — a plain JSON file — is the only
thing that decides what reaches you. Copy it to another machine and your agent
continues from where it left off.

---

## Contents

- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Setup](#setup)
- [First run](#first-run)
- [Daily use](#daily-use)
- [Commands](#commands)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Sources](#sources)
- [Your identity model](#your-identity-model)
- [Backup and restore](#backup-and-restore)
- [Known behavioral properties](#known-behavioral-properties)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)
- [Contributing](#contributing)

---

## How it works

1. **You set up your identity** — a 5-minute conversation with the agent tells it
   what you care about, what you want less of, and how you like to read.

2. **It fetches in the background** — every 6 hours, Keel pulls from your
   configured sources (RSS, Hacker News, Reddit, arbitrary URLs).

3. **It scores against your model** — each item is embedded and compared to your
   interests. High-relevance items surface. Adjacent items introduce new territory.
   Some items push back on what you think. One item per cycle has nothing to do
   with your model at all — that is intentional.

4. **You get a morning briefing** — a message appears in your terminal thread at
   the time you configured. 4–7 items at the resolution that fits each one.

5. **Your responses shape the model** — engaging, dismissing, refining a topic,
   or saying "not this kind" all update your identity model. Silence is also
   a signal.

6. **Every Sunday it reflects** — decay, drift detection, source health, weekly
   summary. The model evolves. It never locks in.

---

## Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| OS | Linux, macOS, Windows (WSL2) | Ubuntu 22.04+ |
| Python | 3.11 | 3.12 |
| RAM | 8 GB | 16 GB+ |
| Storage | 2 GB | 10 GB |
| Ollama | 0.3+ | Latest |
| GPU | None (CPU works, slower) | AMD/NVIDIA with 8GB+ VRAM |

**Ollama is required** for local LLM and embedding. Keel will install it
automatically on Linux. On macOS and Windows, install from https://ollama.com first.

**No internet connection is required after setup** — Keel runs fully locally.
Your identity model, your sources, and your briefings never leave your machine.

---

## Installation

```bash
# Clone the repo
git clone https://github.com/[owner]/keel.git
cd keel

# Install Python dependencies
pip install -e .

# Verify Python version
keel --version
```

That is all. Setup handles everything else.

---

## Setup

Setup detects your hardware, installs Ollama if needed, pulls the right models
for your machine, benchmarks performance, and writes an optimised configuration.

```bash
keel --setup
```

**What it does — and asks permission before each step:**

```
→ Keel Setup

I need to collect some information about your system to configure
Keel correctly. Here is what I will detect:

  • CPU model, core count
  • Available RAM
  • GPU vendor, model, and available VRAM (if any)
  • Whether an NPU is present
  • Whether Ollama is installed and which version

This information stays on your machine. It is written to
config/config.yaml under the [hardware] section. Nothing is
sent anywhere.

Proceed with hardware detection? [Y/n]:
```

After detection it shows what it found and proposes the model selection:

```
Hardware detected:
  CPU:  AMD Ryzen AI 9 HX 370 (12 cores)
  RAM:  32.0 GB unified memory
  GPU:  AMD Radeon 890M (ROCm available)
  NPU:  Detected (AMD XDNA 2)

Based on your hardware, I will use:
  LLM:       llama3.2 (8B)   — 4.7 GB download
  Embedding: nomic-embed-text — 274 MB download

These models will be pulled via Ollama and run locally.
Total download: ~5.0 GB

Continue? [Y/n]:
```

You can override model selection:
```bash
keel --setup --llm llama3.2:3b        # smaller/faster
keel --setup --embed bge-small-en-v1.5 # in-process, no Ollama needed
```

Setup takes 5–15 minutes depending on download speed.
Re-run any time: `keel --setup --redetect`

---

## First run

After setup, run the onboarding conversation:

```bash
keel --init
```

Keel asks five questions in a natural conversation — what you're thinking about,
what you want less of, how you read, whether you're working on anything specific,
and whether you want to be challenged. From your answers it builds your initial
identity model, selects sources, and fetches immediately so you see results the same session.

**Configure sources before or during this conversation.** The agent will propose
sources based on what you say — you confirm, drop, or swap. No RSS knowledge needed.

---

## Daily use

Start the agent:

```bash
keel --schedule
```

This starts the background scheduler and opens your terminal thread. Leave it
running in a terminal or configure it as a systemd service (see docs/systemd.md).

**Your morning briefing arrives automatically** at the time you set during setup
(default 07:00). Open the thread to read it.

**Interact with what you see:**

```
> read more                      go deeper on the last item
> not this kind — [description]  refine the matched interest
> drop this thread               dismiss the topic
> I'm not that person anymore    remove the interest entirely
> why this?                      explain why this item was surfaced
> show my model                  see your current interest weights
> set mood depth                 switch to deep-focus mode
> help                           show all available commands
```

**That is the full daily loop.** You do not need to do anything else.
The agent fetches, scores, surfaces, and reflects on its own schedule.

---

## Commands

| Command | What it does |
|---------|-------------|
| `keel --setup` | Detect hardware, install deps, pull models, optimise config |
| `keel --setup --redetect` | Force full re-detection (after hardware change) |
| `keel --setup --models-only` | Re-pull models without re-detecting hardware |
| `keel --init` | Onboarding conversation — builds identity, sources, preferences |
| `keel --schedule` | Start agent + open terminal thread |
| `keel --chat` | Open terminal thread without starting scheduler |
| `keel --task fetch` | Run fetch manually |
| `keel --task score` | Run score manually |
| `keel --task surface` | Run surface manually |
| `keel --task silence` | Run silence task manually |
| `keel --task reflect` | Run reflect manually |
| `keel --status` | System health, last task times, DB size, model summary |
| `keel --monitor` | Live monitoring dashboard (rich terminal) |
| `keel --measure scoring-distribution` | Bucket distribution report |
| `keel --measure interest-health` | Interest weights and state over time |
| `keel --measure surface-quality` | Source and bucket diversity |
| `keel --measure challenge-efficacy` | Challenge classification quality |
| `keel --measure drift` | All 5 drift signals |
| `keel --measure silence` | Silence signal quality |
| `keel --model` | Show current identity model |
| `keel --model --snapshot` | Export model state as JSON |
| `keel --backup` | Create timestamped backup |
| `keel --list-backups` | Show available backups |
| `keel --restore-from-backup [path]` | Restore from backup |
| `keel --forget --topic [topic]` | Remove interest |
| `keel --forget --topic [topic] --ghost-dismiss` | Remove + suppress semantic neighborhood |
| `keel --forget --topic [topic] --scrub` | Remove + erase from audit log |
| `keel --archive-project --topic [topic]` | Archive project interest |
| `keel --update-preferences` | Update preferences without full re-init |
| `keel --show-below-threshold` | Show top 10 filtered items with scores |
| `keel --vault add --service [name] --key [key] --value [val]` | Store credential |

---

## Configuration

Three configuration files are generated during setup and onboarding:

**`config/config.yaml`** — system configuration. Written by `--setup`, tuned by benchmark.
Covers LLM settings, scoring thresholds, scheduler timing, storage paths.
Edit manually to change thresholds after measuring with `--measure`.

**`config/preferences.yaml`** — your preferences. Written during `--init`.
Covers surface time, density, resolution, silence behaviour, challenge tolerance.
Edit directly or use `keel --update-preferences`.

**`config/sources.yaml`** — your sources. Written during `--init`, editable at any time.
Each source has a name, type (rss/hn/reddit/url), URL where applicable,
enabled flag, and fetch interval. Add, remove, or disable sources here.

Key thresholds you may want to tune after 2–4 weeks:

| Setting | Default | Effect of raising | Effect of lowering |
|---------|---------|------------------|-------------------|
| `scoring.filter_threshold` | 0.72 | Fewer items surface | More items surface |
| `scoring.introduce_threshold` | 0.55 | Fewer introductions | More introductions |
| `diversity.confirmation_ratio_alert_threshold` | 0.90 | Later echo-chamber alert | Earlier alert |
| `expansion.pulse_every_n_surfaces` | 7 (auto-decreases) | Less exploration | More exploration |

Run `--measure scoring-distribution` after any threshold change to verify the effect.

---

## Monitoring

Keel tracks metrics continuously. View them three ways:

**Quick status** — last task times, error count, DB size:
```bash
keel --status
```

**Live dashboard** — real-time metrics in a rich terminal view:
```bash
keel --monitor
```

The dashboard shows:
- Task health panel: last run, next scheduled run, duration, status for each task
- Resource panel: CPU%, RAM usage, GPU/VRAM usage (if available), Ollama status
- Pipeline panel: items fetched today, scored, surfaced; LLM latency, embed throughput
- Feed quality panel: bucket distribution (last 7 days), confirmation ratio trend, active drift signals
- Error panel: last 10 log errors with timestamps

**Quality reports** — deeper analysis of specific subsystems:
```bash
keel --measure scoring-distribution  # is the threshold producing the right mix?
keel --measure interest-health       # are weights moving? are interests decaying correctly?
keel --measure drift                 # all 5 drift signals with trend data
```

Metrics are stored in the `metrics` table in `keel.db` and retained for 90 days.
They are never sent anywhere.

---

## Sources

Sources are configured in `config/sources.yaml`. Four types are supported in Phase 1, with a fifth optional type for exogenous discovery:

**RSS/Atom** — any feed URL:
```yaml
- name: Aeon
  type: rss
  url: https://aeon.co/feed.rss
  enabled: true
  fetch_interval_hours: 24
```

**Hacker News** — top stories via Algolia API:
```yaml
- name: Hacker News
  type: hn
  enabled: true
  fetch_interval_hours: 6
```

**Reddit** — public subreddit (no account needed for public subreddits):
```yaml
- name: r/MachineLearning
  type: reddit
  url: r/MachineLearning
  enabled: true
  fetch_interval_hours: 12
```

**Single URL** — a specific page, extracted via trafilatura:
```yaml
- name: Simon Willison's blog
  type: url
  url: https://simonwillison.net/atom/everything/
  enabled: true
  fetch_interval_hours: 24
```

**Wildcard (optional)** — fetches from a set of user-defined sources treated as exogenous. Unlike standard sources, wildcard items are *never* scored against the identity model and are *never* surfaced in the main feed. They exist only as candidates for foreign signal selection. This gives the agent a genuine escape hatch from the configured source topology — items that couldn't be reached by walking the embedding manifold of existing sources.

The use case: if all configured sources are tech/philosophy, the embedding space has no path to ceramics or regional politics. Wildcard sources inject items from genuinely outside the user's domain, available exclusively to the foreign signal slot.

```yaml
- name: wildcard-pool
  type: wildcard
  urls:
    - https://www.lrb.co.uk/feeds/rss        # essays
    - https://spectrum.ieee.org/rss           # engineering
    - https://publicdomainreview.org/feed     # history/arts
  enabled: false                              # opt-in, disabled by default
  fetch_interval_hours: 168                  # weekly — low volume by design
  max_items_per_fetch: 10
```

Wildcard sources are opt-in and disabled by default. They do not participate in scoring, silence tracking, or interest reinforcement. Items from wildcard sources that the user explicitly engages with enter as `provenance: chosen` — the same as any foreign signal item the user saves.

**Authenticated sources** — credentials go in the vault, not the config:
```bash
keel --vault add --service substack --key email --value you@example.com
keel --vault add --service substack --key password --value yourpassword
```

---

## Your identity model

Everything Keel knows about you lives in `store/identity.json`.
It is plain text. You can open it, read it, and edit it directly.

```bash
keel --model          # human-readable summary
keel --model --snapshot  # full JSON export
```

**To take your model to another machine:**
```bash
cp store/identity.json /new-machine/store/identity.json
cp config/preferences.yaml /new-machine/config/
cp config/sources.yaml /new-machine/config/
```

Run `--setup` on the new machine, then `keel --schedule`. No re-init needed.

---

## Backup and restore

Keel automatically backs up before every weekly reflect. To back up manually:

```bash
keel --backup          # creates store/backups/keel_backup_{timestamp}.tar.gz
keel --list-backups    # show all available backups
```

To restore:
```bash
keel --restore-from-backup store/backups/keel_backup_20260415_0700.tar.gz
```

Restore prompts for confirmation, backs up current state first, then restores and reconciles.

---

## Known behavioral properties

**Heavy readers who rarely respond** will see contemplative interests drift
downward over 6–8 weeks. The system interprets silence as a weak negative
signal. Use "more like this" in the thread to anchor interests you process
quietly. Or set `silence_enabled: false` in `config/preferences.yaml`.

**The first 7 days use looser thresholds.** The model doesn't know you yet
and needs data. Items from a wider relevance range surface during this period.
Thresholds adjust gradually after.

**Foreign signal is not broken.** One item per surface cycle will seem
completely unrelated to your interests. It is selected to be maximally
different from everything else in today's surface. This is intentional.

**The model never locks in.** High-weight interests get fewer confirmations
and more edge content automatically. The exploration pulse fires regardless of
mood. The system is designed to keep the door open.

**The weekly reflect may say "nothing notable."** If no drift signals fired
and no source issues were found, Keel says so and skips the LLM call. This
is not a bug. A quiet week is a good week.

**The model only knows what it surfaces.** Keel learns from your interactions with the items it chose to show you — not from what you searched, read elsewhere, or thought about silently. This is by design (sovereignty: no surveillance), but it means early configuration choices have more inertia than the decay math implies. If your initial interests were narrow, exploration mechanisms will widen gradually — but they cannot overcome a source topology that doesn't reach certain domains. Wildcard sources are the explicit escape hatch for this.

**Memory grows; abstraction doesn't.** After 90 days, Keel has accumulated thousands of articles, embeddings, and interactions. It has not distilled them into higher-order concepts. It knows you read 47 articles about AI safety; it doesn't know you've developed a coherent view on it. Synthesis and connection resolution (Phase 2) are the beginning of an answer. A true semantic compression layer — one that builds evolving abstractions from accumulated reading — does not exist in Phase 1.

---

## Troubleshooting

**"Ollama isn't running"**
```bash
ollama serve          # start Ollama in another terminal
# or as a service:
sudo systemctl start ollama
```

**"Surface is empty or very sparse"**
- Run `keel --show-below-threshold` to see what's being filtered
- Check `--measure scoring-distribution` — if filter% is very low, threshold may be too high
- Add more sources or lower `scoring.filter_threshold` in config.yaml

**"Everything surfaces — nothing is filtered"**
- Check `--measure scoring-distribution` — if filter% is very high, threshold may be too low
- Raise `scoring.filter_threshold` slightly (0.74–0.76)

**"Challenge items are always dismissed"**
- Run `--measure challenge-efficacy` — if challenge/confirm/neither ratios are skewed, the classifier is over-triggering
- Raise `scoring.challenge_similarity_min` or lower per-interest challenge_mode to `adjacent`

**"The model drifted in a direction I don't want"**
- Run `keel --list-backups` and restore from a known-good point
- Then rescore: `keel --task score --rescore-all`

**"Ollama is using too much RAM"**
- Switch to a smaller model: `keel --setup --llm llama3.2:3b`
- Or switch embedding to in-process: `keel --setup --embed bge-small-en-v1.5`

**Logs**
```bash
tail -f logs/keel.log
keel --status          # see error count and last error
keel --monitor         # live error panel
```

---

## Architecture

Keel has two layers:

**`core/`** — pure computation. No IO, no storage, no network. Protocols and pure
functions only: the identity model schema, scoring logic, decay and reinforcement
functions, edge detection, mood thresholds. Core never knows where you are,
what sources you use, or what credentials you have. It receives data, computes
results, returns them.

**`agent/`** — everything else. Reads from the database, calls core functions with
the results, writes back. Handles sources, credentials, scheduling, the terminal
thread, the CLI, and all file IO. The agent is the body. Core is the brain.

Your identity model (`store/identity.json`) is the single source of truth for
what the system knows about you. The database (`store/keel.db`) holds article
history, audit logs, and metrics. Both stay on your machine.

---

## Contributing

```bash
pip install -e ".[dev]"
pytest tests/core/      # unit tests — no IO, fast
pytest tests/agent/     # integration tests — mocked sources and LLM
pytest tests/e2e/       # end-to-end simulation — runs 90-day simulation
```

All core tests must have zero IO. Use `MockEmbedder`, `MockLLM`, and
`InMemoryStore` from `tests/mocks/`. Never import `OllamaEmbedder` or
`JsonStore` in a core test.

See `DEFECTS.md` for known issues found during the build simulation.
```

---

### Files Claude Code Should Create Fresh

Do not use any existing scaffold files as ground truth — they were built against earlier spec versions. Build from this spec directly. The scaffold exists only as structural reference for file layout.

### Configuration Reference

All thresholds and tunables that Claude Code should wire to `config/config.yaml`:

```yaml
llm:
  provider: "ollama"          # ollama | anthropic | openai
  model: "llama3.2"           # model name for the provider
  base_url: "http://localhost:11434"  # Ollama default; or OpenAI-compatible base URL
  api_key: ""                 # required for anthropic/openai; leave empty for ollama
  embed_model: "nomic-embed-text"     # Ollama embedding model (ignored for SentenceTransformer)
  embed_provider: "ollama"    # ollama | sentence_transformers
  embed_chunk_size: 5         # articles per embedding batch chunk; lower = more foreground responsiveness
  summary_max_tokens: 80
  intro_max_tokens: 60

scoring:
  filter_threshold: 0.72
  introduce_threshold: 0.55
  challenge_similarity_min: 0.60
  filter_max_items: 20
  introduce_max_items: 5
  challenge_max_items: 3

diversity:
  max_consecutive_same_thread: 3
  max_items_per_source: 3
  confirmation_ratio_alert_threshold: 0.90
  confirmation_ratio_alert_weeks: 3

expansion:
  edge_enabled: true
  edge_probe_rate: 0.3
  edge_similarity_min: 0.40
  edge_similarity_max: 0.54
  edge_random_fraction: 0.4
  world_signal_enabled: true
  world_signal_frequency: "daily"
  foreign_signal_enabled: true
  foreign_signal_frequency: "daily"
  foreign_signal_selection: "adversarial"   # adversarial | random
  foreign_signal_quality: "standard"        # standard | strict | minimal
  foreign_signal_filters:
    block_keywords: []            # user-configurable blocklist for foreign signal only
    min_content_length: 100       # drop near-empty pages
    require_language: []          # optional: restrict to specific languages
  pulse_every_n_surfaces: 7       # mandatory exploration pulse; minimum 5, not configurable lower

mood:
  default_reset_hours: 24
  momentum: 0.3

drift:
  compression_alert_msd_drop_pct: 0.30

surfacing:
  scheduled_time: "07:00"
  threshold_surface: true
  threshold_score: 0.90
  threshold_sources: ["rss", "url"]
  stale_penalty_per_day: 0.02    # effective score decay per day for queued items
  max_stale_penalty: 0.30        # cap; prevents items going below zero

silence:
  window_hours: 48
  cap_per_surfacing: 3
  absence_threshold_days: 5      # skip silence recording if user absent this many days

logging:
  level: "INFO"
  path: "./logs/keel.log"
  max_bytes: 10485760
  backup_count: 5

storage:
  db_path: "./store/keel.db"
  retention_days: 90                   # prune unsurfaced articles and their embeddings after this many days
  surfaced_embedding_retention: "permanent"  # surfaced item embeddings are never pruned

provenance_promotion_threshold: 3    # engagements before interpreted → selected
ghost_dismiss_days: 14               # days temporary negative bias lasts after --ghost-dismiss
ghost_dismiss_threshold: 0.70        # cosine similarity threshold for ghost penalty (surgical default)
ghost_dismiss_penalty: -0.20         # score penalty applied to ghost-matching items
source_health_window_days: 30        # days without introduce-threshold items before flagging
active_interest_threshold: 0.70
interest_saturation_threshold: 0.85   # above this, surface shifts edge-heavy for that interest
weight_floor: 0.10
weight_floor_epsilon: 0.105
grace_period_days: 14
exploration_days: 7
exploration_interactions: 50
exploration_introduce_threshold: 0.45
exploration_edge_probe_rate: 0.6
exploration_pulse_start_interval: 7   # starting pulse interval (surfaces between pulses)
exploration_pulse_minimum_interval: 4  # floor; never goes below this
exploration_pulse_age_step_days: 30   # interval decreases by 1 every N days
silence_window_hours: 48
silence_cap: 3
silence_cooldown_days: 14
engaged_cooldown_days: 30
```

---

## Iterative Development and Efficacy Measurement

Building Keel is not a single implementation pass. The system has behavioral parameters — thresholds, decay rates, reinforcement weights — that only reveal their correctness through use. Claude Code must support iterative cycles that measure whether the system is working as intended.

### What "Working" Means at Each Stage

| Stage | What to verify |
|-------|---------------|
| **Core loop alive** | Fetch runs, articles stored, scoring produces non-trivial buckets |
| **Interest model responding** | Engagement updates weights; decay changes them over time; interests transition states correctly |
| **Surface quality** | Surfaced items feel relevant; not all from same source; mood thresholds shift the mix |
| **Drift detection honest** | Reflect flags real patterns; compression signal fires when content narrows |
| **Challenge working** | Challenge bucket items genuinely tension the thread; not just random |

### Measurement Commands

All measurement commands run against the live `store/keel.db`. They produce reports, not mutations.

```bash
# Scoring distribution — are thresholds producing the right bucket mix?
keel --measure scoring-distribution
# Output: {filter: N, introduce: N, challenge: N, none: N, anti_interest_drops: N}
# Target: filter 15-30% of scored items, introduce 10-20%, challenge 5-10%

# Interest health — are weights moving? are states transitioning?
keel --measure interest-health
# Output: per-interest weight over last 4 weeks, state transitions, dormant/inactive counts

# Surface quality — are surfaced items diverse?
keel --measure surface-quality [--last N]
# Output: source distribution, thread distribution, bucket distribution, edge/world/foreign counts

# Challenge efficacy — is challenge mode finding real tension?
keel --measure challenge-efficacy
# Output: challenge classification distribution (challenge/confirm/neither ratios),
#         false positive estimate (challenge items user dismissed immediately)

# Drift signals — current state of all 5 drift metrics
keel --measure drift
# Output: velocity, concentration, compression (MSD trend), source diversity, edge engagement, passivity (user_initiated_pct trend)

# Silence quality — is silence signal being recorded correctly?
keel --measure silence
# Output: silence counts per interest, double-tap incidents, cap hits
```

### Development Cycle

One full cycle validates a behavioral hypothesis about the system:

```
1. Configure hypothesis (e.g. "filter_threshold 0.72 is too tight — most items scoring 0.68-0.72")
2. keel --dev --task fetch          # populate dev store with fixture items
3. keel --dev --task score          # score with current thresholds
4. keel --measure scoring-distribution  # measure bucket mix
5. Adjust threshold in config.yaml
6. keel --dev --task score --rescore-all  # rescore all items with new threshold
7. keel --measure scoring-distribution  # compare
8. keel --dev --fast-forward 7      # simulate week of decay + reflect
9. keel --measure interest-health   # verify states transitioning correctly
10. keel --dev --chat               # manual inspection of surface quality
```

`--rescore-all` rescores all articles in `store/dev/keel.db` from scratch using current thresholds. Does not re-embed — only recomputes bucket assignment from stored similarity scores.

### Long Testing Cycles

Some behaviors only appear after extended simulated time. Use `--fast-forward` with measurement checkpoints:

```bash
# Simulate 30 days with weekly measurement snapshots
for week in 1 2 3 4; do
    keel --dev --fast-forward 7
    keel --measure drift >> logs/drift_week_$week.json
    keel --measure interest-health >> logs/interests_week_$week.json
done

# Check compression trend
keel --measure compression-trend --from logs/drift_week_*.json
# Output: MSD values per week, flag if 30% drop threshold would have triggered
```

### Threshold Tuning Guide

When measurement reveals a problem, use this guide:

| Symptom | Likely cause | Adjustment |
|---------|-------------|------------|
| Too few filter items (< 10%) | `filter_threshold` too high | Lower to 0.68–0.70 |
| Too many filter items (> 40%) | `filter_threshold` too low | Raise to 0.74–0.76 |
| No challenge items ever | `challenge_similarity_min` too high or prompt too conservative | Lower to 0.55, review prompt |
| All challenge items dismissed | Classifier too aggressive | Review challenge prompt, raise `challenge_similarity_min` |
| Interests decay too fast | `decay_rate` defaults too aggressive | Change default from `slow` to `permanent` for chosen interests |
| Edge items never engaged | `edge_similarity_min` too low — items genuinely not adjacent | Raise to 0.44–0.46 |
| Compression fires too often | MSD threshold too sensitive | Raise `compression_alert_msd_drop_pct` to 0.40 |
| Compression never fires | MSD threshold too lenient | Lower to 0.20–0.25 |

### Efficacy Definition

The system is working when, after 2–4 weeks of real use:

1. **Weight movement**: at least 3 interests show measurable weight change (up or down) from initial values
2. **Bucket diversity**: surface messages contain items from at least 2 different buckets on average
3. **Source diversity**: no single source accounts for > 40% of surfaced items over any 7-day window
4. **Challenge engagement**: at least 20% of challenge items receive a non-silence interaction
5. **Drift detection signal**: at least one drift flag fires in the first 4 weeks of use — if nothing fires, the thresholds are too lenient or the corpus is too small

If any of these fail after 2 weeks, run `--measure` across all dimensions and adjust thresholds before concluding the system doesn't work.

### `--rescore-all` Contract

Rescores all articles from stored similarity scores. Does not re-fetch or re-embed.

```bash
keel --task score --rescore-all [--dev]
```

- Reads all articles from DB where `fetch_state IN ('scored', 'ready_to_score')`
- Recomputes `interest_score`, `bucket`, `resolution` using current identity model and config thresholds
- **Loads active (non-expired) ghost vectors from `ghost_dismissals` table** and computes ghost penalties dynamically against stored article embeddings from the `embeddings` table. Ghost penalties are not stored in `match_reason` — they must be recomputed fresh each time `--rescore-all` runs.
- Updates `fetch_state` back to `scored`
- Does not change `match_reason` (similarities to active interests are preserved)
- Does flag `ghost_penalized=true` on any article that receives a ghost penalty during the rescore
- Useful for: threshold tuning, identity model changes, bucket assignment debugging, post-ghost-dismiss cleanup

**Ghost penalty computation in rescore loop:**
```python
# Load active ghost vectors
active_ghosts = db.execute(
    "SELECT embedding FROM ghost_dismissals WHERE expires_at > ?",
    [datetime.now().isoformat()]
).fetchall()

# For each article with a stored embedding:
article_emb = load_embedding(db, article_id)
ghost_penalized = any(
    cosine_similarity(article_emb, ghost_emb) >= 0.55
    for ghost_emb, in active_ghosts
)
if ghost_penalized:
    interest_score -= 0.20
    bucket = "none"
```

---

## 90-Day Simulation and Gap Analysis

This section is a cynical walkthrough of the full user journey from install to day 90. It identifies gaps, defines fixes, and specifies the end-to-end tests Claude Code must implement to verify the system is working at each stage. Claude Code must not consider Phase 1 complete until all tests in this section pass.

---

### Day 0: Installation

**What happens:**
User clones repo. Runs `keel --init`.

**What can go wrong:**

**Missing: Python version enforcement.** The spec uses `match` statements, union types (`X | Y`), and `dataclasses.replace()` — requires Python 3.11+. No enforcement defined.

*Fix:* Add to `run.py` startup:
```python
import sys
if sys.version_info < (3, 11):
    sys.exit("Keel requires Python 3.11+. Current: " + sys.version)
```

**Missing: `requirements.txt` is referenced but never defined.** Claude Code must generate it. Required packages:

```
# requirements.txt
apscheduler>=3.10
click>=8.1
feedparser>=6.0
filelock>=3.12
numpy>=1.26
ollama>=0.1.8
requests>=2.31
rich>=13.7
sentence-transformers>=2.6
trafilatura>=1.8
cryptography>=42.0      # vault AES-256
pyyaml>=6.0
```

Dev/test extras:
```
# requirements-dev.txt
pytest>=8.0
pytest-asyncio>=0.23
freezegun>=1.4           # freeze dates in decay tests
responses>=0.25          # mock HTTP for source tests
```

**Missing: Timezone handling in APScheduler.** `preferences.yaml` defines `timezone` and `surface_time`, but the spec never shows how APScheduler consumes them. APScheduler's `CronTrigger` takes a `timezone` argument. If not set, it uses the system timezone, which may not match the user's preference.

*Fix:* Scheduler setup must read timezone from preferences:
```python
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

prefs = load_preferences()
tz = ZoneInfo(prefs.get("timezone", "UTC"))
hour, minute = prefs["surface_time"].split(":")

scheduler.add_job(
    surface,
    CronTrigger(hour=int(hour), minute=int(minute), timezone=tz),
    misfire_grace_time=1800,
    max_instances=1
)
```

**Missing: Source URL validation during onboarding.** LLM proposes source URLs. Some may be wrong or dead. `--init` should validate each source by attempting a single fetch before writing `sources.yaml`.

*Fix:* After extraction, for each proposed source, attempt `feedparser.parse(url)` or a HEAD request. If it fails: show the user which sources couldn't be reached and ask whether to include them anyway. Don't silently write dead sources.

---

### Day 0 → Day 1: First Surface

**What happens:**
Day Zero fetch runs. APScheduler starts. First scheduled surface fires at `surface_time`.

**The exploration cliff problem.** Exploration lowers `introduce_threshold` to `0.45`. This means many items surface and the user engages with some. Each engagement reinforces interests. But the initial weight is `0.70` — already high. If the user only engages twice in 7 days, some interests stay at `0.70`, others may have decayed slightly. When exploration ends and threshold snaps to `0.72`, interests at `0.70` are now below filter threshold. The user gets a sparse or empty surface on day 8 with no explanation.

*Fix:* The threshold transition must use momentum blending, not a hard snap. On the first surface after `exploration_end_at` is set, apply: `effective_threshold = explore_threshold * blend + normal_threshold * (1 - blend)` where blend decays over 3 surface cycles. Add `exploration_blend_cycles: 3` to config. Also: the surface message on exploration end must explicitly state what changed:

```
→ Keel

Exploration period complete (50 interactions).
Thresholds adjusting over the next few days.
If your feed feels thinner this week, that's why — 
say "show me what I'm missing" to see what's below threshold.
```

**Missing: `--show-below-threshold` command.** Users need a way to see what's being filtered. Not in the spec.

*Fix:* Add CLI command that surfaces the top 10 items below current threshold with their scores.

---

### Days 1–7: Exploration Period

**What happens:**
Daily silence at 08:00. Surface at `surface_time`. Fetch every 6 hours.

**What can go wrong:**

**User doesn't open CLI for 3 days.** Silence task fires daily. With one-silence-per-surfacing-event rule (already fixed), this is contained. But the absence guard (5 days) means days 3 and 4 still accumulate silence. Interests seeded at `0.70` with `slow` decay and 2 silence hits are now at approximately `0.66`. By day 7, some interests may have dropped enough to approach the floor — especially with `fast` decay rate. Users who don't engage at all during exploration end up with a broken model at the cliff.

**Missing: Minimum weight protection during exploration.** Interests added during exploration should not be eligible for state transitions until exploration ends.

*Fix:* In `transition_states()`, skip any transitions if `model.exploration_end_at is None` — the model is still bootstrapping.

**The reflect task fires on Sunday at 08:00. What if `--init` ran on a Saturday?** First reflect fires the next day — 24 hours after setup. The reflect task will find no meaningful signal (< 7 days of data). Drift signals can't fire. Mood inference has one day of data.

*Fix:* Reflect task checks: if `(today - model.created_at).days < 7`, skip drift signals and mood inference. Write a brief message: *"Not enough data yet for weekly reflect. Check back next week."*

---

### Days 7–14: Post-Exploration

**What happens:**
Exploration period ends. Thresholds normalize (with momentum blending). First real reflect fires.

**What can go wrong:**

**Missing: Reflect narrative LLM prompt.** The reflect task writes a weekly summary message. The spec defines what signals to check (drift, source health, mood inference) but never defines the LLM prompt that synthesizes them into a readable weekly message. This is a critical contract — Claude Code will invent something.

*Fix:* Define the reflect narrative prompt:

```
System: "You write brief weekly summaries for a personal feed agent.
         Be direct. No filler. Max 150 words.
         You are given structured facts — use them. Do not speculate beyond the data.
         Reference specific topics by name. Do not explain what the agent is."

User: "Weekly reflect data:
       {json.dumps(reflect_data, indent=2)}

       Write a brief weekly summary. Ground every observation in the specific
       facts above — do not add interpretations not supported by the data.
       Cover only what actually happened: weight changes, transitions, signals,
       source issues, mood pattern. One question at the end if warranted.
       Max 150 words."
```

**`reflect_data` must be causally grounded.** The LLM cannot produce an honest narrative if it's given vague signals. Every field must be a specific fact, not a category label. The reflect task is responsible for extracting top-N concrete facts before calling the LLM:

```json
{
  "week": "2026-W15",
  "top_weight_increases": [
    {"topic": "AI self-awareness", "from": 0.68, "to": 0.74, "cause": "3 engage interactions"},
    {"topic": "local-first software for mobile", "from": 0.55, "to": 0.61, "cause": "1 go_further"}
  ],
  "top_weight_decreases": [
    {"topic": "startup recruiting", "from": 0.42, "to": 0.31, "cause": "decay (slow, 14 days)"}
  ],
  "state_transitions": [
    {"topic": "web3 governance", "from": "active", "to": "dormant", "cause": "3 cycles at floor"}
  ],
  "worth_it_items": [
    {"title": "The Hard Problem of AI Consciousness", "topic": "AI self-awareness"}
  ],
  "regret_items": [],
  "consolidation_candidates": [
    {"topics": ["AI safety", "AI alignment doom"], "similarity": 0.87}
  ],
  "drift_signals": {
    "velocity": null,
    "compression": {"msd_drop_pct": 0.18, "weeks_below_threshold": 1},
    "source_diversity": null,
    "passivity": null
  },
  "exploration_budget_usage": {"used_pct": 0.22, "challenge_items": 1, "edge_items": 1},
  "source_health": [],
  "mood_inferred": "depth",
  "mood_confidence": "medium",
  "silence_summary": {"total_silence_events": 8, "interests_affected": ["startup recruiting"]},
  "threshold_misses": 2
}
```

The LLM must work from these specific facts. A summary that says "you seem more interested in AI lately" without citing the weight increase from 0.68 to 0.74 is a failure of the prompt, not acceptable output. The structured data is the ground truth. The LLM's job is to make it readable, not to interpret it.

**Missing: Challenge LLM response validation.** The challenge prompt returns one word. What if the LLM returns "Challenge" (capitalized), "neither." (with period), or "I think this is a challenge" (full sentence)? No normalization defined.

*Fix:* Post-process: `response.strip().lower().split()[0]`. If result not in `{"challenge", "confirm", "neither"}`: log and default to `"neither"`. Never crash on malformed response.

---

### Days 14–30: Normal Operation

**What happens:**
Full pipeline running. Interests drifting. Source rot accumulating. Challenge items appearing.

**What can go wrong:**

**Missing: User interaction reference.** Once the user is past onboarding, how do they know what they can say to the agent? The spec defines interaction types (`engage`, `go_further`, `dismiss`, `nuance`, etc.) and CLI commands, but there's no help text or command reference that surfaces during normal operation. A user on day 20 won't remember what commands exist.

*Fix:* Add `--help` command to the CLI REPL (separate from `click` help). In-conversation: typing `help` or `?` shows a brief interaction reference:

```
→ Keel

Commands during a surface session:
  read more / go further       — deep dive on the last item
  not this kind — [refinement] — nuance the matched interest
  drop this thread             — dismiss the topic
  I'm not that person anymore  — discontinuity (hard remove)
  show my model                — current interest weights
  why this?                    — explain last item's match
  set mood [mood]              — change current mood
  forget [topic]               — remove interest
  help                         — this message
```

**Missing: Nuance feedback.** When the user says "not this kind — more mobile than desktop," `nuance_interest()` fires and the LLM rewrites the topic string. The user has no immediate confirmation of what it was changed to. They must run `--model` to see.

*Fix:* `nuance_interest()` must respond inline:
```
→ Keel
Updated: "local-first software" → "local-first software for mobile"
This takes effect on the next score cycle.
```

**Missing: Ghost dismissal expiry notification.** When a ghost dismissal expires (14 days after `--forget --ghost-dismiss`), the semantic neighborhood becomes unblocked again. The user has no awareness of this happening. Items from that neighborhood start resurfacing.

*Fix:* The reflect task checks `ghost_dismissals` for entries expiring in the past week. If found, include in reflect message: *"Ghost suppression on 'startup culture' expired. Related content may reappear."*

---

### Days 30–60: Model Evolution

**What happens:**
Some interests go dormant or inactive. First source rot flags. Possible nuance calls. Ghost dismissals cycling.

**What can go wrong:**

**The ghost dismissal pool exhaustion.** By day 30, if the user has fired multiple ghost dismissals, the scoring pipeline checks each candidate against all active ghost vectors. With 5 ghost dismissals and 500 scored items, this is 2,500 cosine similarity computations per scoring cycle. This is fine at 5 vectors. At 20+ it becomes expensive. No cap defined.

*Fix:* Cap active ghost vectors at 10. If a new `--ghost-dismiss` would exceed 10, warn the user and ask which existing ghost to remove, or silently drop the oldest expired entry. Phase 2 evolution path: merge ghost vectors with cosine similarity ≥ 0.80 into a single negative centroid, allowing suppression radius to scale without increasing computation overhead.

**DB growth.** `surfaced_embeddings` is never pruned (explicitly designed this way for compression tracking). At 1 surface per day × 90 days × ~10 items × embedding size (~768 floats × 4 bytes = 3KB per embedding), this is approximately 2.7MB. Not a crisis. But `articles` table with `content` stored grows faster — 500 articles × average 2KB content = 1MB/month minimum. At 90 days with 6-hour fetch cycles and 200 articles/fetch from multiple sources, this could reach 50–100MB. No DB size monitoring defined.

*Fix:* Add `--status` output to include DB size. Add a warning in reflect if DB exceeds configurable threshold (`storage.warn_size_mb: 500`). The existing 90-day retention prunes `articles` already — confirm `content` text is included in that prune, not just the row.

**Audit log unbounded growth.** The 90-day retention policy covers `articles` and their embeddings. But `messages`, `interactions`, and `model_updates` have no pruning strategy. Every interaction writes a row. Every reflect cycle writes rows. After 2–3 years of daily use, these tables contain tens of thousands of rows. `--measure` queries that scan interaction history will degrade on lower-end machines.

*Fix:* Add a yearly aggregation task. On January 1 (or the first reflect cycle of the new calendar year), rows in `interactions` and `model_updates` older than 365 days are aggregated into a monthly summary table and deleted:

```sql
CREATE TABLE IF NOT EXISTS interactions_monthly (
    year_month   TEXT NOT NULL,           -- e.g. "2026-03"
    interest_id  TEXT,
    engage_count INTEGER DEFAULT 0,
    silence_count INTEGER DEFAULT 0,
    dismiss_count INTEGER DEFAULT 0,
    regret_count  INTEGER DEFAULT 0,
    acknowledged_count INTEGER DEFAULT 0,
    go_further_count INTEGER DEFAULT 0,
    PRIMARY KEY (year_month, interest_id)
);
```

`messages` older than 365 days have their `content` field truncated to NULL — the message skeleton (timestamp, task type, id) is preserved for thread continuity, but the text is released. The `--measure` commands fall back to `interactions_monthly` for data older than 365 days. Configurable:

```yaml
storage:
  audit_retention_days: 365      # full detail kept for this many days
  audit_aggregation_enabled: true
```

**Missing: `--update-preferences` command.** User wants to change their surface time from 07:00 to 08:30. They have to edit `preferences.yaml` manually and restart. No CLI path defined.

*Fix:* Add `keel --update-preferences` which re-opens a brief preferences conversation (not the full onboarding), updates `preferences.yaml`, and restarts the scheduler.

---

### Days 60–90: Long-term Behavior

**What happens:**
Drift detection firing. Source health cycling. Possible compression alerts. Foreign signal pool potentially thin.

**What can go wrong:**

**Foreign signal pool exhaustion.** By day 60, the system has learned the user well. Most fetched items score ≥ 0.55 (above introduce threshold). The low-relevance pool (`< 0.55`) shrinks. If fewer than 10 items are in the pool, minimax pre-filtering to top-50 by content length is trivially the whole pool. This is fine — but what if the pool is empty? The `select_adversarial_foreign()` function receives an empty candidates list and crashes or returns 0 on an empty list.

*Fix:* Guard: if the low-relevance pool is empty, skip foreign signal for this cycle and log: `"Foreign signal skipped: no candidates below introduce threshold."` Don't crash. Don't surface a filter item as foreign signal.

**Compression alert oscillation.** MSD requires 3 consecutive weekly drops of 30%+. If the user uses `wander` mode for one week, MSD spikes (diverse content), resetting the streak. The compression signal may never fire even if the underlying pattern is real. Conversely, 3 weeks of `depth` mode will always trigger compression because depth mode intentionally narrows the surface.

*Fix:* The compression alert must check whether the user was in `depth` mode during the weeks in question. If depth mode was active for ≥ 2 of the 3 weeks, suppress the compression alert — the narrowing was intentional. Add `mood_at_surface` data to `surfaced_embeddings` table.

**Missing: DB cleanup job for expired ghost_dismissals.** Ghost dismissal rows with `expires_at < now()` accumulate indefinitely. The scoring pipeline filters them by `WHERE expires_at > ?` so they don't affect scoring, but they waste space.

*Fix:* The reflect task runs `DELETE FROM ghost_dismissals WHERE expires_at < ?` at the start of each weekly run. Log count of deleted rows.

**Reflect message quality degrades over time.** The reflect LLM prompt produces a 150-word message. By week 12, with no drift signals firing and no source health issues, the data passed to the prompt is nearly empty. The LLM will produce filler — "Things look stable this week." That's useless.

*Fix:* If `reflect_data` has no signals worth reporting (no drift, no source rot, no notable weight changes), skip the LLM call entirely and write a fixed message:

```
→ Keel (week 12)

Nothing notable shifted this week.
Interests stable. Sources healthy. No drift signals.
```

Only invoke the LLM when there's something to synthesize.

---

### End-to-End Tests: Claude Code Must Implement These

Claude Code must not consider Phase 1 complete until all of the following tests pass. These are in addition to the unit tests defined in the Implementation Guide.

**File: `tests/e2e/test_journey.py`**

```python
# End-to-end journey tests using MockLLM, MockEmbedder, fixture sources
# Run with: pytest tests/e2e/ -v --timeout=120

class TestDay0:
    def test_python_version_check(self):
        """Exit with clear message if Python < 3.11"""

    def test_init_produces_three_files(self, tmp_path):
        """--init writes identity.json, preferences.yaml, sources.yaml"""

    def test_extraction_validation_catches_malformed(self, mock_llm_bad_json):
        """If LLM returns invalid JSON, validation fails gracefully without writing files"""

    def test_source_validation_warns_on_dead_url(self, mock_dead_feed):
        """Dead source URLs produce a warning, not a hard failure"""

    def test_day_zero_surface_fires_immediately(self, initialized_agent):
        """--init triggers fetch+score+surface without waiting for 07:00"""

    def test_ollama_fallback_on_unavailable(self, ollama_unavailable):
        """Clear error message if Ollama not running. No silent failure."""


class TestExplorationPeriod:
    def test_no_state_transitions_during_exploration(self, agent_day3):
        """Active→Inactive transition does not fire while exploration_end_at is None"""

    def test_exploration_ends_at_50_interactions(self, agent_with_interactions):
        """exploration_end_at is set after 50 apply_interaction() calls"""

    def test_exploration_ends_at_7_days(self, agent_day8):
        """exploration_end_at is set at day 7 even with < 50 interactions"""

    def test_threshold_momentum_blend_on_exploration_end(self, agent_day8):
        """Threshold does not hard-snap from 0.45 to 0.72. Blends over 3 cycles."""

    def test_exploration_end_surface_message(self, agent_day8):
        """Surface message on exploration end contains transition notification"""

    def test_early_reflect_skips_drift(self, agent_day3):
        """Reflect fired within 7 days of init skips drift signals and mood inference"""


class TestSilenceBehavior:
    def test_one_silence_per_surfacing_event(self, agent_with_surfaced_item):
        """Daily silence task records exactly one silence per (article_id, message_id)"""

    def test_silence_suspended_in_depth_mode(self, agent_in_depth_mode):
        """Silence task does not run when mood='depth' and mood_inferred=False"""

    def test_silence_skips_invisible_items(self, agent_depth_surfaced):
        """Items below mood threshold at surface time receive no silence penalty"""

    def test_absence_guard(self, agent_absent_6_days):
        """Silence not recorded if user absent >= 5 days"""


class TestScoringPipeline:
    def test_challenge_response_normalization(self, mock_llm_malformed_challenge):
        """Challenge LLM returning 'Challenge.' or full sentence is normalized, not crash"""

    def test_stale_embeddings_skipped_during_model_change(self, agent_with_model_change):
        """Articles with stale embeddings are not scored during transition window"""

    def test_ghost_dismissal_penalty_applied(self, agent_with_ghost):
        """Items matching ghost vector receive -0.20 score penalty"""

    def test_ghost_penalty_not_applied_after_expiry(self, agent_with_expired_ghost):
        """Items matching expired ghost vector receive no penalty"""

    def test_world_signal_respects_source_dismissals(self, agent_with_dismissed_source):
        """World signal candidates do not include articles from dismissed sources"""

    def test_foreign_signal_empty_pool_graceful(self, agent_high_relevance_corpus):
        """Foreign signal skipped cleanly if low-relevance pool is empty"""


class TestReflectTask:
    def test_reflect_writes_ghost_cleanup(self, agent_with_expired_ghost):
        """Reflect deletes expired ghost_dismissals rows"""

    def test_reflect_skips_llm_when_nothing_notable(self, agent_stable_week):
        """Reflect writes fixed 'nothing notable' message without LLM call if no signals"""

    def test_reflect_includes_ghost_expiry_notice(self, agent_ghost_expiring):
        """Reflect message mentions ghost suppression expiry if relevant"""

    def test_source_health_flagged_at_30_days(self, agent_dead_source_30_days):
        """Source with 0 introduce-threshold items in 30 days flagged in reflect"""

    def test_compression_alert_suppressed_in_depth_mode(self, agent_depth_3_weeks):
        """Compression alert does not fire if depth mode was active for >= 2 of 3 weeks"""


class TestLongTerm:
    def test_90_day_simulation(self, tmp_path):
        """
        Full 90-day simulation using --fast-forward.
        Asserts at checkpoints:
          Day 7:  exploration_end_at set, interests have moved
          Day 14: at least one interest weight changed from initial 0.70
          Day 30: first source health check has run, reflect has fired 4x
          Day 60: at least one interest has transitioned state
          Day 90: no crash, DB readable, --model produces valid output
        """

    def test_db_size_monitoring(self, agent_day90):
        """--status includes DB size. Warn threshold configurable."""

    def test_ghost_cap_at_10_vectors(self, agent_with_11_ghost_dismissals):
        """11th ghost dismissal warns user and does not add to active ghost vectors"""

    def test_interests_survive_60_days_no_engagement(self):
        """Permanent-decay interests at weight > 0.70 survive 60 days without engagement"""

    def test_fast_decay_interests_go_dormant_in_14_days(self):
        """fast-decay interest seeded at 0.70 reaches floor within 14 days"""


class TestCLIInteractions:
    def test_help_command_in_repl(self, agent_running):
        """Typing 'help' in chat shows interaction reference"""

    def test_nuance_shows_before_after(self, agent_running):
        """Nuance interaction responds inline with old→new topic string"""

    def test_show_below_threshold(self, agent_running):
        """'show me what I'm missing' surfaces top 10 below-threshold items with scores"""

    def test_update_preferences(self, agent_running):
        """keel --update-preferences updates preferences.yaml without full re-init"""
```

**Running the full test suite:**
```bash
# Unit tests only (no Ollama, no network)
pytest tests/core/ tests/mocks/ -v

# Integration tests (no Ollama, mocked sources)
pytest tests/agent/ -v

# End-to-end journey tests (no Ollama, mocked everything)
pytest tests/e2e/ -v --timeout=120

# Full suite
pytest tests/ -v --timeout=120

# 90-day simulation only
pytest tests/e2e/test_journey.py::TestLongTerm::test_90_day_simulation -v -s
```

---

### Gaps Added to Phase 1 Checklist

The following items were identified by the simulation and must be in the Phase 1 checklist:

- Python 3.11+ version check on startup
- `requirements.txt` and `requirements-dev.txt`
- APScheduler timezone from `preferences.yaml`
- Source URL validation during onboarding
- Threshold momentum blending on exploration end (not hard snap)
- Exploration end surface message
- `--show-below-threshold` CLI command
- Minimum weight protection: no state transitions during exploration
- Early reflect guard (< 7 days: skip drift and mood inference)
- Reflect narrative LLM prompt (defined above)
- Challenge response normalization (`strip().lower().split()[0]`)
- In-REPL `help` command
- Nuance inline confirmation (old→new topic string)
- Ghost dismissal expiry notification in reflect
- Ghost dismissal cap at 10 active vectors
- Ghost dismissal cleanup in reflect (`DELETE WHERE expires_at < ?`)
- DB size monitoring in `--status`
- `storage.warn_size_mb` config
- `--update-preferences` command
- Reflect skips LLM when no signals (fixed message instead)
- Compression alert suppressed when depth mode was active ≥ 2 of 3 weeks
- Foreign signal empty pool guard (skip cleanly, log, don't crash)
- `mood_at_surface` added to `surfaced_embeddings` for compression context
- `tests/e2e/test_journey.py` with full 90-day simulation

---

## E2E Simulation: Build Validation

This section defines a complete end-to-end simulation that Claude Code must run before declaring the build complete. It uses a concrete user persona, a scripted interaction sequence, deliberate defect injection scenarios, and explicit pass criteria. Claude Code runs this entirely in dev mode — no real sources, no Ollama, no network.

**Purpose**: find defects through simulated use, fix them, and rerun until the system passes clean. Not a unit test. A living simulation of a real user across 90 days of operation.

---

### Simulated Persona

**Name**: Dev User (fixture identity, not a real person)

**Onboarding answers** (used to drive `--init` with MockLLM):

```
Phase 1 — Current thinking:
  "I've been thinking about how AI systems learn and whether
   self-awareness can emerge from prediction. Also local-first
   software, and the philosophy of impermanence."

Phase 2 — What to avoid:
  "Cryptocurrency. Anything to do with NFTs."

Phase 3 — Reading mode:
  "I read carefully and rarely respond quickly. I go deep."

Phase 4 — Active projects:
  "I'm writing a series of essays on epistemic sovereignty."

Phase 5 — Challenge tolerance:
  "Yes, show me things that push back. I want friction."
```

**Expected extraction output** — what MockLLM must return when the extraction prompt fires:

```json
{
  "identity": {
    "interests": [
      {
        "id": "int_001",
        "topic": "AI self-awareness and prediction",
        "weight": 0.70,
        "provenance": "chosen",
        "decay_rate": "slow",
        "challenge_mode": "adjacent",
        "state": "active",
        "first_seen": "{today}",
        "last_reinforced": "{today}",
        "lifetime_engagements": 0
      },
      {
        "id": "int_002",
        "topic": "local-first software",
        "weight": 0.70,
        "provenance": "chosen",
        "decay_rate": "slow",
        "challenge_mode": "adjacent",
        "state": "active",
        "first_seen": "{today}",
        "last_reinforced": "{today}",
        "lifetime_engagements": 0
      },
      {
        "id": "int_003",
        "topic": "philosophy of impermanence",
        "weight": 0.70,
        "provenance": "chosen",
        "decay_rate": "permanent",
        "challenge_mode": "adjacent",
        "state": "active",
        "first_seen": "{today}",
        "last_reinforced": "{today}",
        "lifetime_engagements": 0
      },
      {
        "id": "int_004",
        "topic": "epistemic sovereignty and AI",
        "weight": 0.85,
        "provenance": "project",
        "decay_rate": "permanent",
        "challenge_mode": "friction",
        "state": "active",
        "first_seen": "{today}",
        "last_reinforced": "{today}",
        "lifetime_engagements": 0,
        "project_archived_at": null
      }
    ],
    "anti_interests": ["cryptocurrency", "NFT", "crypto"],
    "dismissals": [],
    "presentation": {
      "default_resolution": "summary",
      "max_items_per_surface": 5
    },
    "mood": "open",
    "mood_set_at": null,
    "mood_inferred": false
  },
  "preferences": {
    "challenge_tolerance": "high",
    "default_resolution": "summary",
    "surface_density": 4,
    "reading_mode": "deep",
    "silence_enabled": true,
    "surface_time": "07:00",
    "surface_days": ["mon","tue","wed","thu","fri","sat","sun"],
    "timezone": "UTC"
  },
  "sources": [
    {"name": "HN", "type": "hn", "enabled": true, "fetch_interval_hours": 6},
    {"name": "LessWrong", "type": "rss",
     "url": "https://www.lesswrong.com/feed.xml", "enabled": true, "fetch_interval_hours": 12},
    {"name": "Aeon", "type": "rss",
     "url": "https://aeon.co/feed.rss", "enabled": true, "fetch_interval_hours": 24}
  ]
}
```

---

### Simulation Script

Claude Code runs this script in sequence. Each phase has commands, assertions, and expected defects to catch. **Fix every failing assertion before proceeding to the next phase.**

```bash
# Setup: initialize dev environment
export KEEL_DEV=1
export KEEL_DEV_SEED=42
keel --dev --init-dev   # seeds dev store with persona above
```

---

#### Phase 1: Initialization (Day 0)

```bash
keel --dev --init
```

**Assert:**
- [ ] `store/dev/identity.json` exists and is valid JSON
- [ ] `config/preferences.yaml` exists with `reading_mode: deep` and `surface_density: 4`
- [ ] `config/sources.yaml` exists with 3 sources
- [ ] `store/dev/keel.db` exists with all tables created
- [ ] `schema_migrations` table has `001_initial` row
- [ ] Day Zero fetch runs automatically — at least 1 article in DB after init
- [ ] Day Zero surface message written to thread (check `messages` table)
- [ ] Surface opening line contains "still guessing" (0-10 interactions exploration framing)
- [ ] Anti-interests `["cryptocurrency", "NFT", "crypto"]` in identity.json
- [ ] `int_004` has `provenance: project`, `weight: 0.85`, `state: active`

**Defects to catch:**
- Extraction produces malformed JSON → validation must catch and prompt retry, not write partial files
- `project_archived_at` field missing from Interest dataclass → causes deserialization error
- Day Zero surface fires before DB migration completes → migration must run first in startup sequence

---

#### Phase 2: Exploration Period (Days 1–7)

```bash
# Simulate 7 days with interactions
keel --dev --task fetch
keel --dev --task score

# Simulate reading 3 items and dismissing 1
keel --dev --simulate-interaction --type engage --article-id 1
keel --dev --simulate-interaction --type engage --article-id 2
keel --dev --simulate-interaction --type dismiss --article-id 3 --level article

# Check surface framing at different interaction counts
keel --dev --task surface
```

**Assert:**
- [ ] Surface opening line after 3 interactions still contains "still guessing" (< 10)
- [ ] `int_001.lifetime_engagements` = 2 (two engage interactions matched it)
- [ ] Anti-interest items are hard-dropped — no articles with "cryptocurrency" in title/content
- [ ] No state transitions fired (exploration_end_at is None → transitions skipped)
- [ ] `--measure scoring-distribution` shows items across multiple buckets
- [ ] Project interest `int_004` at weight 0.85 produces filter-bucket items

```bash
# Fast-forward to day 7 to trigger exploration end
keel --dev --fast-forward 7
keel --dev --task surface
```

**Assert:**
- [ ] `exploration_end_at` is set in identity.json
- [ ] Surface opening line no longer contains exploration framing
- [ ] Surface message contains exploration transition notification
- [ ] Threshold blend applied — not hard snap from 0.45 to 0.72
- [ ] No surface items below blended threshold

**Defects to catch:**
- `transition_states()` fires during exploration → must check `exploration_end_at is None`
- Exploration framing persists past 50 interactions → must check interaction count not just day count
- Grace period not applied — `int_001` (14 days old) gets marked inactive after one silence → grace period check missing from `transition_states()`

---

#### Phase 3: Normal Operation (Days 7–30)

```bash
# Run a full week
keel --dev --fast-forward 7
keel --dev --measure interest-health
keel --dev --measure scoring-distribution
```

**Assert:**
- [ ] At least 2 interests have weight different from initial 0.70
- [ ] `int_003` (permanent decay) has not decayed — weight unchanged
- [ ] `int_004` (project, permanent) has not decayed
- [ ] `int_001` and `int_002` (slow decay) show slight decay if not reinforced
- [ ] Filter bucket: 15-30% of scored items
- [ ] Introduce bucket: 10-20%
- [ ] Challenge bucket: 5-10% (MockLLM must return "challenge" for challenge_material fixture items)
- [ ] Foreign signal item present in surface — labeled correctly
- [ ] Edge items present in surface (at least 1 per cycle)

```bash
# Test nuance interaction
keel --dev --simulate-interaction \
  --type nuance --interest-id int_002 \
  --instruction "specifically for mobile, not desktop"
```

**Assert:**
- [ ] `int_002.topic` changed to "local-first software for mobile"
- [ ] Response contains old→new confirmation: `"local-first software" → "local-first software for mobile"`
- [ ] Only `int_002` embedding invalidated in `identity_hash.txt` — not all interests
- [ ] `model_updates` row has `value_before: "local-first software"`, `value_after: "local-first software for mobile"`

```bash
# Trigger first reflect
keel --dev --task reflect
```

**Assert:**
- [ ] Phase 1 (locked) completed in < 500ms
- [ ] Decay applied to `int_001` and `int_002` (not permanent interests)
- [ ] `model_updates` rows written BEFORE `identity.json` updated (write-ahead)
- [ ] Reflect message written to thread
- [ ] Source health check ran (3 sources checked)
- [ ] No drift signals fire at day 14 (too early for meaningful signals)
- [ ] `ghost_dismissals` cleanup ran (no rows yet, but query must not crash)

**Defects to catch:**
- Nuance rewrites wrong interest (ID lookup fails) → must use exact ID match
- Write-ahead violated — JSON written before model_updates → startup reconciliation test
- Reflect Phase 2 calls LLM when no signals present → must use fixed message instead
- Challenge classification blocks for 5+ seconds → OllamaResourceManager not yielding between items

---

#### Phase 4: Mood and Silence Behaviour (Days 14–21)

```bash
# Set depth mode and run silence
keel --dev --simulate-interaction --type mood_set --mood depth

# Fast-forward 2 days without any interaction
keel --dev --fast-forward 2
keel --dev --task silence
```

**Assert:**
- [ ] Silence task does NOT run (depth mode + mood_inferred=False → silence suspended)
- [ ] No silence interactions in `interactions` table for these 2 days
- [ ] Interest weights unchanged from silence (no penalty applied)

```bash
# Reset mood and run silence after 3 days
keel --dev --simulate-interaction --type mood_set --mood open
keel --dev --fast-forward 3
keel --dev --task silence
```

**Assert:**
- [ ] Silence runs now (mood is open)
- [ ] Items surfaced > 48h ago with no interaction get exactly ONE silence record each
- [ ] Running silence task again immediately adds NO new silence records (one-per-surfacing rule)
- [ ] Items below mood threshold at surface time skipped (check `mood_at_surface` in messages)

```bash
# Test absence guard
keel --dev --fast-forward 6   # 6 days absent
keel --dev --task silence
```

**Assert:**
- [ ] Silence NOT recorded for any item (absent 6 days > 5-day threshold)
- [ ] Log contains "silence skipped: user absent 6 days"

**Defects to catch:**
- Silence fires during depth mode → mood check missing from silence task
- Multiple silence records per surfacing event → one-per-surfacing rule not enforced
- Absence guard threshold off-by-one → test both 4 days (should run) and 5 days (should skip)

---

#### Phase 5: Discontinuity and Ghost Dismissal (Day 21)

```bash
# Forget a topic with ghost dismissal
keel --dev --forget --topic "local-first software for mobile" --ghost-dismiss
```

**Assert:**
- [ ] `int_002` removed from `identity.json`
- [ ] `thread_items` rows for `int_002` deleted
- [ ] `ghost_dismissals` table has 1 row with correct embedding and `expires_at = today + 14`
- [ ] Confirmation message shown before execution
- [ ] `model_updates` has discontinuity record

```bash
# Score new items — ghost penalty must apply
keel --dev --task fetch
keel --dev --task score
keel --dev --measure scoring-distribution
```

**Assert:**
- [ ] Items semantically similar to "local-first software for mobile" receive -0.20 penalty
- [ ] Items below filter threshold after ghost penalty NOT in filter bucket
- [ ] Items completely unrelated to `int_002` unaffected

```bash
# Fast-forward past ghost expiry
keel --dev --fast-forward 15
keel --dev --task reflect   # reflect cleanup should delete expired ghost
```

**Assert:**
- [ ] `ghost_dismissals` table is empty after reflect
- [ ] Log contains "deleted 1 expired ghost dismissal(s)"
- [ ] Reflect message mentions ghost suppression expiry

```bash
# Test --scrub flag
keel --dev --forget --topic "philosophy of impermanence" --scrub
```

**Assert:**
- [ ] `int_003` removed from identity.json
- [ ] All `model_updates` rows referencing "philosophy of impermanence" have topic replaced with `[FORGOTTEN]`
- [ ] Numerical deltas (weight values) preserved
- [ ] Distinct confirmation warning shown (separate from standard --forget confirmation)

**Defects to catch:**
- `thread_items` not cleared on discontinuity → ghost items resurface via similarity
- Ghost penalty applied after expiry → expiry check not using `expires_at > now()`
- Scrub replaces numerical values not just strings → must only replace topic strings
- Ghost dismissal cap: add 11 ghost dismissals, verify 11th is rejected with warning

---

#### Phase 6: Drift Detection and Echo Chamber Prevention (Days 30–90)

```bash
# Simulate 30 days of heavily confirmatory engagement
# (user only engages with filter-bucket items, never edge or challenge)
keel --dev --fast-forward 30 --interaction-pattern confirmatory
keel --dev --measure drift
```

**Assert:**
- [ ] `confirmation_ratio` > 0.85 for 2+ consecutive weeks
- [ ] Confirmation ratio intervention fired (filter items halved in recent surfaces)
- [ ] Passivity signal: `user_initiated_pct` near 0.0 (no user-initiated messages in pattern)
- [ ] Passivity flag in reflect message (fires once per 4 weeks)
- [ ] Exploration pulse interval has decreased from 7 (model is 30+ days old → interval = 6)

```bash
# Verify interest saturation behaviour
# int_001 should be near 0.85+ after heavy engagement
keel --dev --measure interest-health
```

**Assert:**
- [ ] If any interest at weight >= 0.85: surface for that interest contains max 1 filter item
- [ ] Freed slots filled with edge items in that interest's neighborhood
- [ ] `challenge_mode` temporarily promoted (surface only, not written to identity.json)

```bash
keel --dev --fast-forward 30
keel --dev --measure drift
```

**Assert:**
- [ ] Compression MSD trend computed across 3 weeks
- [ ] If MSD dropped 30%+: compression alert in reflect
- [ ] Compression alert suppressed if depth mode was active >= 2 of 3 weeks
- [ ] Source health: any source with 0 introduce-threshold items in 30 days flagged in reflect

```bash
# Full 90-day mark
keel --dev --fast-forward 30
keel --dev --status
keel --dev --model --snapshot
```

**Assert:**
- [ ] `--status` shows DB size, last run time for all tasks, no errors
- [ ] `--model --snapshot` produces valid JSON with all active interests and weights
- [ ] At least 1 interest has transitioned state (active → dormant or inactive)
- [ ] `int_003` (permanent decay) still active at original weight
- [ ] `int_004` (project) still active, weight unchanged
- [ ] Exploration pulse interval is 4 (90+ days → minimum floor)
- [ ] No unhandled exceptions in logs across entire 90-day run

---

#### Phase 7: Backup and Restore

```bash
keel --dev --backup
keel --dev --list-backups
```

**Assert:**
- [ ] Backup file created in `store/dev/backups/`
- [ ] Backup contains `identity.json`, `preferences.yaml`, `sources.yaml`, `keel.db`
- [ ] `--list-backups` shows backup with timestamp and interest count

```bash
# Corrupt identity.json deliberately
echo "CORRUPTED" > store/dev/identity.json
keel --dev --status   # should detect and prompt restore
keel --dev --restore-from-backup store/dev/backups/[latest]
keel --dev --status   # should be healthy again
```

**Assert:**
- [ ] Corrupted `identity.json` detected on startup → clear error, no crash
- [ ] Restore prompts confirmation before overwriting
- [ ] Restore creates a backup of corrupted state before overwriting
- [ ] After restore: `--status` shows healthy, `--model --snapshot` valid
- [ ] Startup reconciliation runs after restore

**Defects to catch:**
- Restore overwrites without pre-backup → user loses corrupted state history
- Restore succeeds but scheduler starts before reconciliation runs → data inconsistency

---

### Defect Resolution Protocol

When any assertion fails, Claude Code must:

1. **Identify root cause** — which file, which function, which edge case
2. **Write a failing test** in `tests/e2e/test_simulation.py` that captures the defect
3. **Fix the implementation**
4. **Verify the fix** — the written test passes AND all previously passing assertions still pass
5. **Document the defect** in a `DEFECTS.md` file:

```markdown
## DEFECTS.md

| # | Phase | Defect | Root cause | Fix | Test |
|---|-------|--------|-----------|-----|------|
| 1 | Init  | ... | ... | ... | test_... |
```

Do not proceed to the next phase until all assertions in the current phase pass.

---

### Pass Criteria

The build is complete when ALL of the following are true:

```bash
# All unit tests pass (no IO)
pytest tests/core/ -v --timeout=30
# Result: 0 failed

# All agent integration tests pass
pytest tests/agent/ -v --timeout=60
# Result: 0 failed

# Full e2e simulation passes
pytest tests/e2e/test_simulation.py -v -s --timeout=300
# Result: 0 failed

# 90-day journey tests pass
pytest tests/e2e/test_journey.py -v --timeout=300
# Result: 0 failed

# No errors in 90-day simulated logs
keel --dev --fast-forward 90 2>&1 | grep -i "error\|exception\|traceback"
# Result: empty (no errors)

# --status shows healthy state
keel --dev --status
# Result: all tasks have last_run, DB size reasonable, no error flags

# --model --snapshot produces valid output
keel --dev --model --snapshot | python -m json.tool
# Result: valid JSON, all interests have required fields
```

`DEFECTS.md` must exist and contain every defect found during simulation with its fix documented.

Only when all seven commands above return clean results is the Phase 1 build considered complete.

---


- [ ] keel-core: IdentityModel, IdentityModelStore protocol, Embedder protocol, scorer, challenger, expander, mood — protocols and pure functions only
- [ ] keel-agent: scheduler with misfire config, fetch/score/silence/surface/reflect tasks
- [ ] Conversational thread (CLI with rich, polling loop for real-time updates)
- [ ] All interaction types including silence, mood, forgetting, legibility queries
- [ ] Cold start init with merge/replace option
- [ ] Anti-interests keyword blacklist
- [ ] Diversity floor + confirmation ratio tracking
- [ ] Mood system: explicit setting, inference, soft confirmation, 24h reset
- [ ] Edge expansion: edge topic detection, configurable probe rate, explicit framing
- [ ] World signal: ambient corpus scoring independent of identity model
- [ ] Legibility: `--model` inspector, audit log, in-thread attribution footer
- [ ] Drift detection in reflect: velocity, concentration, source diversity, edge engagement
- [ ] Intentional forgetting: discontinuity interaction type, `--forget` CLI command
- [ ] Error resilience across all failure modes
- [ ] `--dry-run` flag on all tasks
- [ ] Dev mode: `--dev` flag, separate store, MockEmbedder, MockLLM, fixture sources
- [ ] Dev mode: `--fast-forward N` for simulating decay and reflect cycles
- [ ] Dev mode: `--init-dev` to seed development environment
- [ ] `tests/fixtures/` with synthetic feed items covering all source types and edge cases
- [ ] Core scoring tests (deterministic, no Ollama dependency)
- [ ] Agent integration tests with mocked sources and LLM
- [ ] `--status` command
- [ ] `--model --snapshot` command for current model state
- [ ] HN/Reddit two-pass quick-fetch with `fetch_state` column
- [ ] `nuance_interest()` function in `core/identity/updater.py`
- [ ] Project provenance type: `--archive-project` CLI command, archive/reactivate lifecycle
- [ ] `MetaPreferences` dataclass: exploration_bias, depth_bias, stance_bias — inference in reflect, explicit set in chat
- [ ] Wildcard source type: fetches exogenous items for foreign signal only, never scored
- [ ] Longitudinal mood memory in reflect: cycle detection, domain correlation, duration patterns
- [ ] Dormant reactivation signal in reflect: flag dormant interests with 3+ scoring items this cycle
- [ ] `acknowledged` interaction type: resets `last_reinforced`, no weight change
- [ ] QA context: top-5 articles, 100-char summary truncation, configurable via `qa.top_k` and `qa.summary_truncate`
- [ ] Tangential stance class: four-class classifier (`challenge | confirm | tangential | neither`), tangential routes to introduce bucket
- [ ] Audit log retention: `interactions_monthly` aggregation table, yearly rollup, message content truncation at 365 days
- [ ] Epsilon floor logic (`weight <= 0.105`) in updater state transitions
- [ ] Silence double-tap guard (24h cooldown per article+message pair)
- [ ] `KeelEvent` dataclass in `agent/surface/thread.py`
- [ ] `migrations/` folder with initial schema migration
- [ ] Dev mode: seeded RNG via `KEEL_DEV_SEED` env var
- [ ] Onboarding conversation: 5-phase LLM interview (`agent/init.py`)
- [ ] `agent/store.py` — `JsonStore` implementing `IdentityModelStore` (moved from core)
- [ ] `agent/embedders.py` — `OllamaEmbedder`, `SentenceTransformerEmbedder` (moved from core)
- [ ] `agent/ledger.py` — audit log write/read (moved from core)
- [ ] `tests/mocks/store.py` — `InMemoryStore` implementing `IdentityModelStore` for tests
- [ ] `run.py` startup sequence: version check → migrations → reconciliation → wire deps → dispatch
- [ ] `agent/monitor.py` — live rich dashboard with 4 panels (task health, resources, pipeline, feed quality)
- [ ] `--monitor` command — refreshes every 2 seconds, `q` to quit, `r` to refresh, `e` for error detail
- [ ] `metrics` table in schema with catalogue of all tracked metrics
- [ ] All tasks instrument metrics on completion (system, pipeline, quality, error categories)
- [ ] Metrics retention: prune rows older than 90 days in weekly reflect cleanup
- [ ] Setup permission prompt — explicit consent before hardware detection, no silent collection
- [ ] No telemetry — hard constraint, no external analytics calls anywhere in codebase
- [ ] `agent/setup/detect.py` — `HardwareProfile` dataclass, GPU/NPU/Ollama detection
- [ ] `agent/setup/installer.py` — Python dep verification, Ollama install (Linux auto, Mac/Win guided), model pull
- [ ] `agent/setup/benchmark.py` — embed throughput + LLM latency benchmark → writes optimised config
- [ ] Hardware profile → model selection table (6 profiles from CPU-only to high-end GPU)
- [ ] `--setup --redetect` and `--setup --models-only` flags
- [ ] `pyproject.toml` with correct dependencies, `keel` entry point, dev extras
- [ ] `tests/fixtures/feeds/` — 9 fixture files covering all scenarios (see fixture schema section)
- [ ] `README.md` covering quick start, commands, config, known behavioral properties
- [ ] `--dev --simulate-interaction` command: `--type`, `--article-id`, `--interest-id`, `--instruction`, `--mood`
- [ ] `--dev --interaction-pattern confirmatory` for fast-forward: simulates passive engagement only
- [ ] `tests/e2e/test_simulation.py` — persona-driven e2e simulation (see E2E Simulation section)
- [ ] `DEFECTS.md` — generated during simulation run, documents every defect found and fixed
- [ ] `DEVIATIONS.md` — documents any deliberate deviations from spec with rationale
- [ ] Core unit tests have zero IO: no files, no DB, no network — `InMemoryStore` + `MockEmbedder` + `MockLLM` only
- [ ] Extraction prompt: single LLM call producing identity + preferences + sources JSON
- [ ] Post-extraction validation before writing any files
- [ ] `config/preferences.yaml` schema and writer
- [ ] `preferences.yaml` as override layer: surfacing and silence tasks read it before `config.yaml`
- [ ] Source suggestion during onboarding (LLM proposes based on stated interests)
- [ ] `OllamaResourceManager` in `agent/resources.py` — priority lock for shared VRAM (not core/)
- [ ] `LLMClient` protocol in core; `OllamaLLM`, `AnthropicLLM`, `OpenAILLM` in `agent/llm.py`
- [ ] `FetchContext` replacing `requests.Session` in `FeedSource` protocol
- [ ] `TaskStatus` protocol: `FileTaskStatus` for agent, `DbTaskStatus` for service
- [ ] Write-ahead contract: SQLite `model_updates` written before `identity.json`; startup reconciliation
- [ ] `--rescore-all` loads active ghost vectors from DB for dynamic penalty computation
- [ ] Sub-batch embedding chunking with lock release between chunks (`llm.embed_chunk_size`)
- [ ] `total_interactions` field in IdentityModel; `apply_interaction()` triggers exploration end at 50
- [ ] Stale queue penalty: time-based effective score decay for surface assembly sorting
- [ ] Fetch acquires lock briefly for source resumption (only exception to no-lock rule)
- [ ] `model_updates.value_after` stores full serialized Interest object for atomic reconciliation
- [ ] `nuance_interest()` reactivates inactive/dormant interests: resets weight to 0.40, state to active
- [ ] `ON DELETE CASCADE` on `thread_items.article_id` and `embeddings.article_id`
- [ ] `PRAGMA foreign_keys=ON` in initial migration
- [ ] Toxicity gating on foreign signal candidates (`foreign_signal_filters` config block)
- [ ] Injection pool admin-only; `--check-injection-pool` command
- [ ] Mandatory exploration pulse every 7 surfaces regardless of mood
- [ ] Silence absence protection: skip silence recording if user absent 5+ days
- [ ] Event queue bounded at 100; `new_message` events have priority over status events
- [ ] Day Zero Ollama fallback: health check, clear error message, titles-only mode if embedding available
- [ ] API key lifecycle: rotation, revocation, 24h grace period, status endpoint
- [ ] Challenge render framing: non-punitive system prompt; UX tone principle enforced throughout
- [ ] Strict sequential pipeline: all embeddings before any LLM calls
- [ ] Silence: one penalty per surfacing event (not per day)
- [ ] Adversarial foreign signal: minimax formulation not centroid distance
- [ ] Foreign signal Day 1 fallback: least-popular by external_score, not random
- [ ] Exploration threshold transition: 3-cycle momentum blending, not hard cut
- [ ] `exploration_end_at` field in IdentityModel; source health window starts from it
- [ ] `store/task_status.json` advisory file; surface task defers up to 30min if score in progress
- [ ] Reflect two-phase split: Phase 1 locked (decay + transitions only), Phase 2 unlocked (all IO + LLM)
- [ ] Edge engagement drift flag includes mood context caveat
- [ ] Challenge dismissal rate tracking in reflect (> 70% dismissal → suggest adjacent mode)
- [ ] `idx_model_updates_timestamp` index in initial migration
- [ ] `surfaced_embeddings` never pruned by retention_days; storage cost documented
- [ ] World signal respects source dismissals at assembly time
- [ ] Day Zero surface on `--init`: immediate fetch + surface, no 23h wait
- [ ] Per-interest embedding cache (composite hash, atomic invalidation)
- [ ] Ghost dismissal: `--ghost-dismiss` flag, `ghost_dismissals` table, 14-day bias
- [ ] Silence mood awareness: skip items invisible at current mood threshold
- [ ] Provenance promotion: `interpreted` → `selected` at 3+ engagements
- [ ] `--forget --scrub` flag: replace topic strings in audit log with `[FORGOTTEN]`
- [ ] Source health check in reflect task
- [ ] Adversarial foreign signal selection (lowest cosine to surface centroid)
- [ ] `--measure` commands: scoring-distribution, interest-health, surface-quality, challenge-efficacy, drift, silence
- [ ] `--task score --rescore-all` for threshold tuning without re-embedding
- [ ] `--task score --reembed-all` for embedding model migration
- [ ] Embedding model versioning: `model` + `dims` columns, stale detection on startup, batch re-embedding
- [ ] `--fast-forward N` with measurement checkpoint support
- [ ] Python 3.11+ version check on startup (`sys.version_info`)
- [ ] `requirements.txt` and `requirements-dev.txt` (see 90-day simulation section)
- [ ] APScheduler timezone from `preferences.yaml` (`ZoneInfo` + `CronTrigger(timezone=...)`)
- [ ] Source URL validation during onboarding (feedparser parse attempt before writing sources.yaml)
- [ ] Threshold momentum blending on exploration end: 3-cycle blend, not hard snap
- [ ] Exploration end surface message (explicit notification of transition)
- [ ] `--show-below-threshold` CLI command (top 10 filtered items with scores)
- [ ] No state transitions during exploration (`transition_states()` skips if `exploration_end_at is None`)
- [ ] Early reflect guard: skip drift + mood inference if `(today - created_at).days < 7`
- [ ] Reflect narrative LLM prompt (defined in 90-day simulation section)
- [ ] Challenge response normalization: `strip().lower().split()[0]`, default `"neither"` on malformed
- [ ] In-REPL `help` / `?` command showing interaction reference
- [ ] Nuance inline confirmation: respond with old→new topic string immediately
- [ ] Ghost dismissal expiry notification in reflect message
- [ ] Ghost dismissal cap: max 10 active vectors; warn on 11th
- [ ] Ghost dismissal cleanup in reflect: `DELETE FROM ghost_dismissals WHERE expires_at < ?`
- [ ] DB size monitoring in `--status`; `storage.warn_size_mb` config threshold
- [ ] `--update-preferences` command (brief re-interview, no full re-init)
- [ ] Reflect skips LLM call when no signals: fixed "nothing notable" message
- [ ] Compression alert suppressed if depth mode active ≥ 2 of 3 compression-check weeks
- [ ] `mood_at_surface` added to `surfaced_embeddings` for compression context
- [ ] Foreign signal empty pool guard: skip cleanly and log, never crash
- [ ] `--backup` command: timestamped tar.gz of identity.json + preferences.yaml + sources.yaml + keel.db
- [ ] Auto-backup before weekly reflect (configurable, default: keep 4 backups)
- [ ] `--restore-from-backup [path]`: validate, confirm, backup current state, restore, reconcile
- [ ] `--list-backups`: show available backups with timestamps and model summary
- [ ] Interest saturation: `weight >= 0.85` reduces filter items, reallocates to edge, temporary challenge_mode promotion
- [ ] Exploration pulse scaling with model age: interval decreases from 7 to 4 over 90 days
- [ ] Confirmation ratio hard intervention: auto-halve filter items when ratio > 0.85 for 2 weeks
- [ ] Design principle #20: permanently provisional model — never stops exploring
- [ ] Exploration confidence signaling: surface opening line changes with interaction count (0-10, 11-25, 26-49)
- [ ] Cognitive passivity detection: `user_initiated_pct` in reflect, `passivity_flag` drift signal, fires at most once per 4 weeks
- [ ] `tests/e2e/test_journey.py` with full 90-day simulation (all TestDay0 through TestLongTerm classes)

### Phase 2 — Depth + Service
- [ ] keel-service: FastAPI app, SqliteStore, scoring + challenge worker pools
- [ ] Scoring API (Model A feed integration)
- [ ] Feed API with webhook (Model B feed integration)
- [ ] SentenceTransformerEmbedder for service
- [ ] Synthesis resolution — cluster related items across sources
- [ ] Connection resolution — link current items to past thinking
- [ ] Web UI for browsing thread and inspecting identity model
- [ ] Substack paywalled content via email forwarding + parsing
- [ ] WebSocket for real-time thread updates in service

### Phase 3 — Portability + Ecosystem
- [ ] Identity model export / import between agent and service — format is `identity.json` with `version` field already defined; export produces a self-contained portable file; import validates schema version before applying; incompatible versions prompt user to migrate or reject
- [ ] Multi-device agent sync (your server only)
- [ ] Notes system integration (Obsidian, Logseq, plain Markdown)
- [ ] Pluggable source adapters (newsletters, podcast transcripts, academic feeds)
- [ ] Platform SDK — thin wrapper around feed integration protocol

---

## Design Principles

1. **The agent is the account.** Identity, preferences, and behavior model are one thing.
2. **Core is a library.** No IO, no opinions about deployment. Applications provide those.
3. **The world prompts it too.** User message is one input type. Sources, thresholds, silence, and mood are others.
4. **It has already read the thing.** The agent renders at the right resolution. Links are footnotes.
5. **Dismissal is as important as affinity — in importance, not in effect.** Both write to the same model. Dismissal shapes the model as significantly as engagement does. But the mechanics are asymmetric by design: negative signals are stronger and flatter, positive signals are graded. Symmetry of importance, not symmetry of effect.
6. **Interests are alive.** Provenance, weight, decay, nuance — not a flat list.
7. **Confirmation is not the goal.** The agent tracks its own echo chamber risk and expands its own edges.
8. **The user is always legible to themselves.** Every update, every inference, every action that wrote to the model — visible, traceable, correctable at any time.
9. **Forgetting is a right.** Discontinuity is not decay. The user can break the continuity on purpose.
10. **Fail gracefully, never silently.** A scheduled agent that fails without logging is worse than one that doesn't run.
11. **Sovereignty is non-negotiable.** The service is self-hosted. Your identity model lives in your infrastructure.
12. **Your frame, not theirs.** Content arrives in a space you own. No platform chrome.
13. **Everything evolves.** The agent you have in a year is not the one you started with.
14. **Identity is not only a graph.** The system models identity as a weighted graph evolving over time. But mood, edge expansion, world signal, and discontinuity introduce field dynamics — external forcing, temporary transformation, hard breaks. These two models coexist and occasionally produce tension. That tension is not a bug. It is an honest reflection of what identity actually is.
15. **Something must refuse the model.** Foreign signal exists so the system cannot become a closed ecology of meaning. One item per cycle that the system does not score, does not learn from, and does not absorb. It is seen. That is all.
16. **Dismissal is not yet fully constitutive.** Currently, dismissal adjusts weights. The next evolution is dismissal that reshapes scoring geometry — de-weighting entire semantic neighborhoods through repeated rejection, not just individual topics. This is named here as a known evolution path, not a current feature.
17. **Moods are self-modification rituals.** Users will cycle moods not to get different content but to become a different cognitive version of themselves for a while. This is intended behavior, not a side effect. The system is designed to support it honestly.
18. **The system should be able to answer: what do I currently believe about this user?** `--model --snapshot` produces a JSON summary of current model state — active interests with weights, mood, last surface time, drift flags from last reflect. If you can't answer that question quickly, debugging becomes archaeology.
19. **`identity.json` is the agent.** Not the software. Not the database. The file. Everything the system has learned about you — every weight, every decay rate, every provenance, every transition — is in `identity.json`. It is human-readable JSON. It is 5–20KB. You can copy it to a USB drive and take it with you. You can open it in a text editor and read it. You can move it to a different machine, point a new install at it, and your agent continues from exactly where it left off. The database (`keel.db`) holds articles and audit history — useful but not essential. The identity is the file. Leaving does not mean losing your model. It means copying a file.
20. **The model is permanently provisional.** No amount of engagement earns the right to stop exploring. A system that has learned the user well must work harder to keep the door open, not less. High confidence in what is known creates an obligation to surface what isn't. No interest is ever fully understood. No weight is ever so high that the system stops questioning it. The exploration pulse shortens as the model matures. Saturation shifts the surface toward edges. The door never closes — that is a design constraint, not a preference.

---

*Built alongside the essay "Your Agent" — https://open.substack.com/pub/aperceptualdrifter/p/your-agent?r=7x5h5j&utm_medium=ios*
