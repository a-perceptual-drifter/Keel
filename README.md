# Keel

**Personal feed agent. The account is the agent.**

Keel is a local-first, privacy-respecting feed agent that reads with you.
It fetches from the sources you configure, scores items against an
identity model that learns from your interactions, and surfaces a small,
considered set each morning — not an infinite scroll.

The identity model is yours. It lives on disk as `identity.json`,
portable, readable, and editable. There is no cloud account; the JSON
file *is* the account.

---

## Quick start

```bash
bash setup.sh           # creates .venv, installs deps, installs Ollama,
                        # pulls llama3.2 + nomic-embed-text
.venv/bin/python run.py init       # seed your identity with topics
.venv/bin/python run.py schedule   # start the background agent
.venv/bin/python run.py chat       # open the conversation surface
```

Or run individual tasks manually:

```bash
.venv/bin/python run.py task --task fetch    # pull from all sources
.venv/bin/python run.py task --task score    # embed + bucket
.venv/bin/python run.py task --task surface  # render today's feed
.venv/bin/python run.py task --task silence  # weak negative signal for ignored items
.venv/bin/python run.py task --task reflect  # weekly decay + state transitions
.venv/bin/python run.py status
```

## How it works

```
fetch (6h)  →  score  →  surface (07:00)  →  you read  →  interactions
                                                              ↓
                                    silence (daily 08:00) ← reflect (weekly Sun)
```

- **fetch** pulls from RSS, Hacker News, Reddit, or any URL; deduplicates
  by URL; stores in SQLite with `fetch_state = ready_to_score`
- **score** embeds each item, compares against your active interests,
  assigns a bucket: `filter` (≥ 0.72), `introduce` (0.55–0.72),
  `challenge` (scored ≥ 0.60, classified as challenging an interest)
- **surface** selects a small set with diversity and mood awareness,
  writes a message to the conversation thread, emits an event to the CLI
- **you** respond with `go further 2`, `dismiss 3`, `noted 1`,
  `nuance 4 specifically for mobile`, etc.
- **silence** catches surfaced items that went 48h without a response
  and applies a weak `-0.02` negative signal
- **reflect** (weekly) applies decay, transitions states, writes a
  narrative summary

## Requirements

| What       | Why                                 | Default                            |
|------------|-------------------------------------|------------------------------------|
| Python 3.11+ | dataclasses, Protocol, generics  | system                             |
| Ollama     | local LLM + embedder                | `llama3.2`, `nomic-embed-text`     |
| SQLite     | article store, audit ledger         | file at `store/keel.db`            |
| filelock   | atomic identity writes              | file at `store/identity.json.lock` |

Swap Ollama for the Anthropic or OpenAI API by editing
`config/config.yaml`: set `llm.provider`, `llm.api_key`, `llm.model`.
Swap the embedder for an in-process model by installing the `[sbert]`
extra and setting `embed_model: bge-small-en-v1.5`.

## Commands

| Command                            | What it does                                |
|------------------------------------|---------------------------------------------|
| `run.py setup`                     | Detect hardware, suggest config             |
| `run.py init`                      | Cold-start identity seed                    |
| `run.py schedule`                  | Start APScheduler + CLI REPL                |
| `run.py chat`                      | Open CLI REPL without scheduler             |
| `run.py task --task <name>`        | Run one task manually                       |
| `run.py status`                    | Show interest count, DB size                |

## Configuration

Edit `config/config.yaml` for LLM + scoring thresholds, `config/sources.yaml`
for feed subscriptions, `config/preferences.yaml` for reading style
(surface density, challenge tolerance, silence window).

## Identity model portability

`store/identity.json` is a plain file. Back it up, version it, move it
to another machine. The interests, weights, decay rates,
meta-preferences, and mood are all there in readable JSON. Nothing is
locked in a proprietary database format.

## Known behavioral properties

- Interest weights decay on a half-life (7/30/90 days depending on
  `decay_rate`) and floor at `0.10` — interests never disappear, they
  go dormant.
- `interpreted` interests (inferred by the agent) promote to `selected`
  after 3 lifetime engagements.
- `apply_interaction` is a pure function: returns `(new_model, updates)`.
  The agent layer writes `updates` to the SQLite audit ledger *before*
  saving the JSON model — write-ahead contract prevents split-brain.
- Reflect runs in two phases: Phase 1 under the identity lock
  (decay + state transitions only), Phase 2 unlocked (LLM narrative).
  LLM calls never happen while holding the identity lock.
- Foreign signal — items drawn from outside your model's reach — is
  never absorbed into the identity model unless you explicitly say so.

## Architecture overview

```
core/       pure processing library — no IO, no storage
            models, updater, scorer, challenger, mood, expansion
agent/      concrete implementations — Ollama, SQLite, file IO,
            scheduler, sources, surface, tasks, CLI
run.py      startup sequence + subcommand dispatch
migrations/ numbered SQL, applied on every startup
tests/      mocks (MockEmbedder, MockLLM, InMemoryStore) + unit + e2e
```

`core/` imports nothing from `agent/`. The application layer injects
all concrete dependencies at startup in `run.py`. This means swapping
the LLM provider, the embedder backend, or the storage format touches
zero code in `core/`.

## Contributing

This is personal software. If you want to fork it and make it yours,
start by editing `config/config.yaml` and `config/sources.yaml`, then
run `setup.sh`. If you find bugs, open an issue with the minimal
sequence that reproduces it. If you want to send patches, keep the
`core/`-is-pure contract intact — no IO in `core/`, no concrete
implementations, no `datetime.now()` without an `as_of` parameter.

## License

MIT. See `LICENSE`.
