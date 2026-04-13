# Keel — pending work

Things we've discussed but haven't built yet. Not a spec, not a contract — a scratchpad so nothing falls off.

---

## Runtime source management (REPL)

Give the REPL commands to list, inspect, modify, and debug feed sources without hand-editing `config/sources.yaml`.

### Commands to add

- `sources` — list configured sources: type, enabled state, last-fetch count, last error (if any)
- `source add <type> <name> <arg>` — e.g. `source add rss hn-frontpage https://...`, `source add reddit rust rust`
- `source remove <name>`
- `source enable <name>` / `source disable <name>`
- `source test <name>` — dry-run fetch one source, print count + any error, do **not** write to DB
- `source creds <name> <key>=<value> ...` — attach credentials (Reddit OAuth, etc.)
- `fetch <name>` — fetch just one source into the DB (today's `fetch` is all-or-nothing)

### Design decisions still open

1. **Persistence of REPL edits**
   - Option A: rewrite `config/sources.yaml` on every mutation. Simple, survives restart, but PyYAML strips comments — any hand-written YAML comments get lost on first REPL write.
   - Option B: layered — hand-edits stay in `config/sources.yaml`, REPL edits go to `config/sources.runtime.yaml` and merge on load. Preserves comments; more moving parts.
   - **Leaning**: A. Accept the comment loss; document it.

2. **Credential storage**
   - Option A: encrypted at rest in `store/credentials.enc` via `cryptography` (already a dep), unlocked with a passphrase once per session. Safer, but adds an unlock dance to every REPL start.
   - Option B: plain `config/credentials.yaml`, `.gitignore`d. Zero friction, relies on filesystem perms.
   - **Leaning**: B for a solo local tool. Revisit if Keel ever runs on shared hardware.

3. **Fetch error surface**
   - Today `fetch_all` swallows per-source exceptions silently. Change it to return `[(name, count, error_or_none)]`.
   - Persist last result in a new `source_status` SQLite table: `name, last_fetch_at, last_count, last_error, consecutive_failures`.
   - `sources` reads from that table for the diagnostic view.

### Suggested slicing

- **Slice 1 — observability (safe, no config mutation)**
  - Per-source error capture in `fetch_all`
  - `source_status` table + migration
  - `sources` command (list + last-fetch status)
  - `source test <name>` (dry-run)
  - `fetch <name>` (per-source fetch)

- **Slice 2 — mutation**
  - `source add` / `source remove` / `source enable` / `source disable`
  - Rewrite `config/sources.yaml` on change

- **Slice 3 — credentials**
  - `source creds <name> <k>=<v>`
  - Plain `config/credentials.yaml` (gitignored)
  - Wire creds through `FetchContext` to `RedditSource` etc.

Start with Slice 1. Everything else layers on top.

---

## Other pending items

(Nothing else yet. Add as they come up.)
