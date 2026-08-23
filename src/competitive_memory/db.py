"""Neon/PostgreSQL persistence, isolated from ScrapeCreators fetching and
from normalization - this file is the only place that knows SQL exists.
Plain psycopg3 + direct SQL, no ORM. One connection per CLI invocation.

Never logs, prints, or includes DATABASE_URL (or any exception that might
carry it) in a raised message - PersistenceError messages are hand-written,
never str(exc) of a connection failure.
"""
import os

import psycopg

from ad_fetcher.config import load_env  # reused .env parser, not duplicated


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
    """One connection per CLI invocation. Neon's pooled connection string
    works here unchanged - it's just an ordinary PostgreSQL DSN to psycopg."""
    dsn = get_database_url()
    try:
        return psycopg.connect(dsn)
    except psycopg.Error as exc:
        # Deliberately not including str(exc) or the DSN - a libpq
        # connection error can embed host/port details.
        raise PersistenceError(
            f"Could not connect to the database ({exc.__class__.__name__})."
        ) from exc


_INSERT_SQL = """
    INSERT INTO competitor_ads
        (ad_id, brand, body, headline, cta, media_type, latest_media_url, snapshot_url, started_at, is_active)
    VALUES
        (%(ad_id)s, %(brand)s, %(body)s, %(headline)s, %(cta)s, %(media_type)s, %(media_url)s, %(snapshot_url)s, %(started_at)s, %(is_active)s)
"""

# first_seen_at/created_at are intentionally absent - untouched, preserves
# the original discovery time. analysis_status is intentionally absent -
# preserves whatever an (unbuilt-yet) analysis stage may have set.
# started_at/is_active use COALESCE: a null in *this* fetch never erases a
# previously known value - satisfies both "don't erase a real started_at
# with null" and "don't flip is_active on absence of the field".
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
