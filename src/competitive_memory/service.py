"""refresh_competitive_memory(): fetch Sequence A's paid ads (reusing its
service unmodified) -> persist/upsert in Neon -> return newly discovered
ads. Synchronous, one connection per call - matches the small one-shot CLI
batch pattern already used by Sequences A and B.
"""
from ad_fetcher.service import fetch_and_normalize as fetch_and_normalize_ads

from . import db


def refresh_competitive_memory(conn=None) -> dict:
    """`conn` is injectable (tests pass a fake); a real CLI run leaves it
    None and this function owns the one connection for this invocation."""
    fetched = fetch_and_normalize_ads()
    ads = fetched["ads"]

    owns_connection = conn is None
    if owns_connection:
        conn = db.connect()
    try:
        result = db.upsert_ads(conn, ads)
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
