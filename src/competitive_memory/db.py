"""Neon/PostgreSQL persistence, isolated from ScrapeCreators fetching and
from normalization - this file is the only place that knows SQL exists.
Plain psycopg3 + direct SQL, no ORM. One connection per CLI invocation.

Never logs, prints, or includes DATABASE_URL (or any exception that might
carry it) in a raised message - PersistenceError messages are hand-written,
never str(exc) of a connection failure.
"""
import os
import time
from datetime import datetime

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from ad_fetcher.config import load_env  # reused .env parser, not duplicated

# Bounded connection policy: a Neon cold-start/transient blip gets one retry,
# but a real outage fails fast rather than hanging the caller (and, upstream
# in service.py, this runs *before* any ScrapeCreators credit is spent).
CONNECT_TIMEOUT_SECONDS = 17
MAX_CONNECT_ATTEMPTS = 2
CONNECT_RETRY_DELAY_SECONDS = 2


class PersistenceError(Exception):
    """Raised for any database failure. Message is safe to print."""


def get_database_url() -> str:
    """Env var wins over .env, same override rule as SCRAPECREATORS_API_KEY."""
    url = os.environ.get("DATABASE_URL") or load_env().get("DATABASE_URL")
    if not url:
        raise PersistenceError(
            "Missing DATABASE_URL. Set it in .env or the environment before running."
        )
    return url


def connect() -> psycopg.Connection:
    """One connection per CLI invocation (or per migration run). Neon's
    pooled connection string works here unchanged - it's just an ordinary
    PostgreSQL DSN to psycopg.

    Retries only connection-level failures (psycopg.OperationalError) up to
    MAX_CONNECT_ATTEMPTS, with a short fixed delay - a transient Neon
    cold-start/blip gets one second chance; anything else (bad credentials,
    a real outage) fails after that, not indefinitely.
    """
    dsn = get_database_url()
    last_error = None
    for attempt in range(1, MAX_CONNECT_ATTEMPTS + 1):
        try:
            return psycopg.connect(dsn, connect_timeout=CONNECT_TIMEOUT_SECONDS)
        except psycopg.OperationalError as exc:
            last_error = exc
            if attempt < MAX_CONNECT_ATTEMPTS:
                time.sleep(CONNECT_RETRY_DELAY_SECONDS)

    # Deliberately not including str(last_error) or the DSN - a libpq
    # connection error can embed host/port details.
    raise PersistenceError(
        f"Could not connect to the database after {MAX_CONNECT_ATTEMPTS} attempts "
        f"({last_error.__class__.__name__})."
    ) from last_error


_INSERT_SQL = """
    INSERT INTO competitor_ads
        (ad_id, brand, body, headline, cta, media_type, latest_media_url, snapshot_url,
         started_at, is_active, page_id, collation_id, collation_count)
    VALUES
        (%(ad_id)s, %(brand)s, %(body)s, %(headline)s, %(cta)s, %(media_type)s, %(media_url)s,
         %(snapshot_url)s, %(started_at)s, %(is_active)s, %(page_id)s, %(collation_id)s, %(collation_count)s)
"""

# first_seen_at/created_at/analysis_status/analysis_* are intentionally
# absent - untouched, preserves the original discovery time and whatever
# an analysis stage has already recorded. started_at/is_active/page_id/
# collation_id/collation_count all use COALESCE: a null in *this* fetch
# never erases a previously known value - satisfies "don't erase a real
# started_at/is_active/evidence field with null" uniformly, in SQL, not
# scattered Python conditionals.
_UPDATE_SQL = """
    UPDATE competitor_ads SET
        brand = %(brand)s,
        body = %(body)s,
        headline = %(headline)s,
        cta = %(cta)s,
        media_type = %(media_type)s,
        latest_media_url = %(media_url)s,
        snapshot_url = %(snapshot_url)s,
        started_at = COALESCE(%(started_at)s, started_at),
        is_active = COALESCE(%(is_active)s, is_active),
        page_id = COALESCE(%(page_id)s, page_id),
        collation_id = COALESCE(%(collation_id)s, collation_id),
        collation_count = COALESCE(%(collation_count)s, collation_count),
        last_seen_at = NOW(),
        times_seen = times_seen + 1,
        updated_at = NOW()
    WHERE ad_id = %(ad_id)s
"""

_SELECT_EXISTING_SQL = "SELECT ad_id FROM competitor_ads WHERE ad_id = ANY(%s)"


def upsert_ads(conn, ads: list) -> dict:
    """One query to find which ad_ids already exist, then insert the new
    ones and update the rest, all in one transaction. A changed signed CDN
    URL alone never makes an ad "new" - only ad_ids absent from the table
    are inserted; everything else is an update, however much its fields
    changed. Returns inserted/updated counts plus the ads newly inserted
    this run (in ad_fetcher's own normalized shape - `media_url` etc. -
    ready to hand to a future analysis step)."""
    ad_ids = [ad["ad_id"] for ad in ads]

    try:
        with conn.cursor() as cur:
            existing_ids = set()
            if ad_ids:
                cur.execute(_SELECT_EXISTING_SQL, (ad_ids,))
                existing_ids = {row[0] for row in cur.fetchall()}

            new_ads = [ad for ad in ads if ad["ad_id"] not in existing_ids]
            existing_ads = [ad for ad in ads if ad["ad_id"] in existing_ids]

            for ad in new_ads:
                cur.execute(_INSERT_SQL, ad)
            for ad in existing_ads:
                cur.execute(_UPDATE_SQL, ad)

        conn.commit()
    except psycopg.Error as exc:
        conn.rollback()
        raise PersistenceError(
            f"Database operation failed and was rolled back ({exc.__class__.__name__})."
        ) from exc

    return {
        "inserted_count": len(new_ads),
        "updated_count": len(existing_ads),
        "ready_for_analysis": new_ads,
    }


# --- Part 3: the analysis-persistence boundary --------------------------
# No AI model is called anywhere in this file (or this repository, this
# milestone). These functions only let an external agent (OpenClaw, later)
# read pending work and write back a result through a clean, scoped
# contract. `ready_for_analysis` from one refresh run is not the only way
# to find pending work - it's re-queryable from Neon at any later time via
# list_pending_analysis(), which is exactly the point: a crash, a restart,
# or simply running the agent hours after the fetch must not lose work.

def _jsonable(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _jsonable_row(row: dict) -> dict:
    return {k: _jsonable(v) for k, v in row.items()}


_LIST_PENDING_SQL = """
    SELECT ad_id, brand, body, headline, cta, media_type,
           latest_media_url AS media_url, snapshot_url, started_at,
           is_active, page_id, collation_id, collation_count,
           first_seen_at, last_seen_at, times_seen, analysis_status,
           analysis_attempts
    FROM competitor_ads
    WHERE page_id = %(page_id)s
      AND media_type = 'image'
      AND analysis_status IN ('pending', 'failed')
      AND latest_media_url IS NOT NULL
      AND latest_media_url <> ''
    ORDER BY (analysis_status = 'pending') DESC, first_seen_at ASC
    LIMIT %(limit)s
"""


def list_pending_analysis(conn, page_id: str, limit: int) -> list:
    """Configured-competitor, image-only, usable-media-URL rows with
    analysis_status pending OR failed (failed work is retried here, not
    lost - pending is prioritized over retries, oldest first within each).
    Scoped by page_id so a different/previous competitor's rows (page_id
    NULL or different) are never returned."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_LIST_PENDING_SQL, {"page_id": page_id, "limit": limit})
        rows = cur.fetchall()
    return [_jsonable_row(r) for r in rows]


_MARK_COMPLETE_SQL = """
    UPDATE competitor_ads SET
        analysis_status = 'complete',
        analysis_result = %(result)s,
        analysis_error = NULL,
        analyzed_at = NOW(),
        analysis_attempts = analysis_attempts + 1,
        updated_at = NOW()
    WHERE ad_id = %(ad_id)s AND page_id = %(page_id)s
    RETURNING ad_id
"""


def save_analysis_result(conn, ad_id: str, page_id: str, result) -> None:
    """Marks one ad's analysis complete. `result` must be a JSON object
    (a dict) - never an arbitrary string or list. Rejects an ad_id that
    doesn't exist, or exists but belongs to a different competitor
    (page_id mismatch) - both look identical to the caller: "unknown"."""
    if not isinstance(result, dict):
        raise PersistenceError("Analysis result must be a JSON object.")
    try:
        with conn.cursor() as cur:
            cur.execute(_MARK_COMPLETE_SQL, {"ad_id": ad_id, "page_id": page_id, "result": Jsonb(result)})
            updated = cur.fetchone()
        if updated is None:
            conn.rollback()
            raise PersistenceError(f"Unknown ad_id for the configured competitor: {ad_id!r}.")
        conn.commit()
    except psycopg.Error as exc:
        conn.rollback()
        raise PersistenceError(
            f"Database operation failed and was rolled back ({exc.__class__.__name__})."
        ) from exc


_MARK_FAILED_SQL = """
    UPDATE competitor_ads SET
        analysis_status = 'failed',
        analysis_error = %(error)s,
        analysis_attempts = analysis_attempts + 1,
        updated_at = NOW()
    WHERE ad_id = %(ad_id)s AND page_id = %(page_id)s
    RETURNING ad_id
"""


def mark_analysis_failed(conn, ad_id: str, page_id: str, error_message: str) -> None:
    """Marks one attempt failed - `analysis_attempts` still increments, so
    a retry policy elsewhere can eventually give up, but the row stays
    'failed' (re-queryable via list_pending_analysis) rather than being
    lost. Never analyzed_at - only a real success sets that."""
    try:
        with conn.cursor() as cur:
            cur.execute(_MARK_FAILED_SQL, {"ad_id": ad_id, "page_id": page_id, "error": error_message})
            updated = cur.fetchone()
        if updated is None:
            conn.rollback()
            raise PersistenceError(f"Unknown ad_id for the configured competitor: {ad_id!r}.")
        conn.commit()
    except psycopg.Error as exc:
        conn.rollback()
        raise PersistenceError(
            f"Database operation failed and was rolled back ({exc.__class__.__name__})."
        ) from exc


# --- Part 4: ranking support ---------------------------------------------

_LIST_COMPLETED_SQL = """
    SELECT ad_id, brand, body, headline, cta, media_type,
           latest_media_url AS media_url, snapshot_url, started_at,
           is_active, page_id, collation_id, collation_count,
           first_seen_at, last_seen_at, analysis_result
    FROM competitor_ads
    WHERE page_id = %(page_id)s
      AND analysis_status = 'complete'
"""


def list_completed_analyses(conn, page_id: str) -> list:
    """Every completed analysis for the configured competitor - the raw
    material ranking.py scores. Unscoped by design (no threshold/limit
    here) - that's ranking.py's job, over data this function just fetches."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_LIST_COMPLETED_SQL, {"page_id": page_id})
        rows = cur.fetchall()
    return [_jsonable_row(r) for r in rows]
