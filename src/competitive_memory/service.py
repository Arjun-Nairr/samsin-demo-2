"""refresh_competitive_memory(): establish Neon connection -> only if that
succeeds, fetch Sequence A's paid ads (reusing its service unmodified) ->
persist/upsert in Neon -> return newly discovered ads. Synchronous, one
connection per call.

Connect-before-fetch is deliberate: a database preflight failure must never
cost a ScrapeCreators credit. See db.py for the connection's own bounded
timeout/retry policy.
"""
from ad_fetcher.service import fetch_and_normalize as fetch_and_normalize_ads

from . import db


def refresh_competitive_memory(conn=None) -> dict:
    """`conn` is injectable (tests pass a fake) and is never closed here -
    the caller owns it. A real CLI run leaves it None; this function then
    owns the one connection it opens for this invocation and always closes
    it, on every path (success, fetch failure, or upsert failure)."""
    owns_connection = conn is None
    if owns_connection:
        conn = db.connect()  # may raise PersistenceError - nothing to fetch or close yet

    try:
        fetched = fetch_and_normalize_ads()  # only reached once the connection is live
        result = db.upsert_ads(conn, fetched["ads"])
    finally:
        if owns_connection:
            conn.close()

    return {
        "fetched_count": fetched["count"],
        "inserted_count": result["inserted_count"],
        "updated_count": result["updated_count"],
        "ready_for_analysis_count": len(result["ready_for_analysis"]),
        "ready_for_analysis": result["ready_for_analysis"],
    }
