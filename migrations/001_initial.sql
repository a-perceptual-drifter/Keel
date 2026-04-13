-- keel Phase 1 initial schema
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY,
    source          TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    url             TEXT UNIQUE NOT NULL,
    title           TEXT,
    content         TEXT,
    summary         TEXT,
    published_at    DATETIME,
    fetched_at      DATETIME NOT NULL,
    fetch_state     TEXT NOT NULL DEFAULT 'ready_to_score',
    interest_score  REAL,
    match_reason    TEXT,
    external_score  INTEGER DEFAULT 0,
    external_score_prev INTEGER DEFAULT 0,
    bucket          TEXT,
    resolution      TEXT,
    surfaced_at     DATETIME,
    surfaced_msg_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_articles_fetch_state ON articles(fetch_state);

CREATE TABLE IF NOT EXISTS embeddings (
    article_id  INTEGER PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
    embedding   BLOB NOT NULL,
    model       TEXT NOT NULL,
    dims        INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    timestamp       DATETIME NOT NULL,
    task            TEXT,
    parent_id       INTEGER REFERENCES messages(id),
    mood_at_surface TEXT
);

CREATE TABLE IF NOT EXISTS interactions (
    id          INTEGER PRIMARY KEY,
    article_id  INTEGER REFERENCES articles(id),
    message_id  INTEGER REFERENCES messages(id),
    type        TEXT NOT NULL,
    detail      TEXT,
    timestamp   DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_interactions_silence
    ON interactions(article_id, message_id, type)
    WHERE type = 'silence';

CREATE TABLE IF NOT EXISTS thread_items (
    topic_id    TEXT NOT NULL,
    article_id  INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    similarity  REAL NOT NULL,
    week        TEXT NOT NULL,
    PRIMARY KEY (topic_id, article_id)
);

CREATE TABLE IF NOT EXISTS model_updates (
    id              INTEGER PRIMARY KEY,
    timestamp       DATETIME NOT NULL,
    interest_id     TEXT,
    update_type     TEXT NOT NULL,
    field           TEXT NOT NULL,
    value_before    TEXT,
    value_after     TEXT,
    triggered_by    TEXT,
    article_id      INTEGER REFERENCES articles(id)
);
CREATE INDEX IF NOT EXISTS idx_model_updates_timestamp ON model_updates(timestamp);

CREATE TABLE IF NOT EXISTS surfaced_embeddings (
    id          INTEGER PRIMARY KEY,
    message_id  INTEGER REFERENCES messages(id),
    centroid    BLOB NOT NULL,
    week        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ghost_dismissals (
    id          INTEGER PRIMARY KEY,
    embedding   BLOB NOT NULL,
    topic       TEXT NOT NULL,
    created_at  DATETIME NOT NULL,
    expires_at  DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ghost_dismissals_expiry ON ghost_dismissals(expires_at);

CREATE TABLE IF NOT EXISTS metrics (
    id          INTEGER PRIMARY KEY,
    timestamp   DATETIME NOT NULL,
    category    TEXT NOT NULL,
    name        TEXT NOT NULL,
    value       REAL NOT NULL,
    unit        TEXT,
    task        TEXT
);
CREATE INDEX IF NOT EXISTS idx_metrics_category_name_time
    ON metrics(category, name, timestamp);

CREATE TABLE IF NOT EXISTS source_stats (
    source       TEXT PRIMARY KEY,
    score_mean   REAL NOT NULL,
    score_stddev REAL NOT NULL,
    sample_count INTEGER NOT NULL,
    updated_at   DATETIME NOT NULL
);
