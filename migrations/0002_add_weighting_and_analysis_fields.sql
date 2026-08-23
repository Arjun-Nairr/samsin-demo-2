-- Sequence D: weighting evidence + the analysis-persistence boundary.
-- Plain SQL, no migration framework. Safe to run more than once
-- (ADD COLUMN IF NOT EXISTS throughout) - never drops, never deletes rows,
-- never alters existing columns. One statement (psycopg3's cursor.execute
-- doesn't support multiple statements per call, so all seven columns are
-- added in one ALTER TABLE rather than several). Apply with the same
-- command as 0001: cd src && python -m competitive_memory.migrate

ALTER TABLE competitor_ads
    -- Weighting evidence (Part 2). Missing provider values stay NULL - the
    -- application never fabricates a value for these. page_id is also the
    -- scoping key every Sequence D query filters on, so old rows from a
    -- previous competitor (inserted before this column existed) are NULL
    -- here and are correctly excluded by any `WHERE page_id = '<id>'`
    -- query without ever being deleted.
    ADD COLUMN IF NOT EXISTS page_id TEXT,
    ADD COLUMN IF NOT EXISTS collation_id TEXT,
    ADD COLUMN IF NOT EXISTS collation_count INTEGER,
    -- Analysis-persistence boundary (Part 3). No AI model is called by
    -- this repository - these columns exist so an external agent
    -- (OpenClaw, later) can read pending work and write back a result
    -- through a clean contract.
    ADD COLUMN IF NOT EXISTS analysis_result JSONB
        CHECK (analysis_result IS NULL OR jsonb_typeof(analysis_result) = 'object'),
    ADD COLUMN IF NOT EXISTS analysis_attempts INTEGER NOT NULL DEFAULT 0
        CHECK (analysis_attempts >= 0),
    ADD COLUMN IF NOT EXISTS analysis_error TEXT,
    ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMPTZ;
