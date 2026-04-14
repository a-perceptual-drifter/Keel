-- keel: body prefetch status for articles
ALTER TABLE articles ADD COLUMN body_status TEXT;
CREATE INDEX IF NOT EXISTS idx_articles_body_status ON articles(body_status);
