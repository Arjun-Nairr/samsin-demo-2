-- Sequence C: the persistent "active competitive memory" table.
-- Plain SQL, no migration framework. Safe to run more than once
-- (CREATE TABLE IF NOT EXISTS) - never drops, never deletes rows.
-- Apply with: cd src && python -m competitive_memory.migrate

CREATE TABLE IF NOT EXISTS competitor_ads (
    ad_id             TEXT PRIMARY KEY,
    brand             TEXT NOT NULL,
    body              TEXT NOT NULL DEFAULT '',
    headline          TEXT NOT NULL DEFAULT '',
    cta               TEXT NOT NULL DEFAULT '',
    media_type        TEXT NOT NULL CHECK (media_type IN ('image', 'video')),
    latest_media_url  TEXT NOT NULL,
    snapshot_url      TEXT,
    started_at        TIMESTAMPTZ,
    first_seen_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active         BOOLEAN,
    times_seen        INTEGER NOT NULL DEFAULT 1 CHECK (times_seen >= 1),
    analysis_status   TEXT NOT NULL DEFAULT 'pending'
                          CHECK (analysis_status IN ('pending', 'processing', 'complete', 'failed')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
