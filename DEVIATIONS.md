# DEVIATIONS.md

Deliberate departures from the spec in the Phase 1 build, with rationale.

## 1. Ollama / sentence-transformers moved to optional extras

The spec lists `ollama` and `sentence-transformers` as base dependencies, but
this makes the package heavy and blocks installs in environments where neither
is available. Both are moved into optional extras (`[ollama]`, `[sbert]`) so
Phase 1 can install and run against mock backends for tests. `setup.sh` still
installs and pulls the Ollama models for end-user machines.

## 2. `sentence-transformers` / Ollama adapters import lazily

`agent/embedders.py` and `agent/llm.py` import their heavy deps inside the
implementation classes so the module can always be imported for protocol
purposes, and so tests that use mocks don't require the backend libraries.

## 3. Phase 1 scope is intentionally MVP

Every Phase 1 feature is implemented to a working baseline; many long-tail
quality gates from the 90-day simulation (confirmation-ratio intervention,
ghost-dismiss pool compaction, audit aggregation) are scaffolded but not yet
exercised by e2e assertions. Subsequent passes will fill them in.
