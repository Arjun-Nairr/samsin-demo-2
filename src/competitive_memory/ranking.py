"""Sequence D, Part 4: deterministic V1 ranking over completed analyses.

weight = RECENCY_WEIGHT*recency + LONGEVITY_WEIGHT*longevity + RECURRENCE_WEIGHT*recurrence

All weights/windows/thresholds live in config.py, not here. This is a
compact-context builder, not a creative brief - OpenClaw converts this
ranked context into a brief later; nothing here does that.

Every component score is a PROXY, not a performance claim:
- recency: how recently the ad started (or was first seen, if the
  provider never gave a start date) - not whether it's working.
- longevity: how long it's been observed running - an advertiser keeping
  an ad live is circumstantial evidence they value it, not proof it's
  profitable.
- recurrence: collation_count (distinct creative variants under the same
  campaign, per the provider) - never times_seen, which only counts how
  many times *our own fetch* has observed the ad and says nothing about
  the advertiser's creative variants.

Scores are computed fresh every time this is called (real "now"), so
recency naturally shifts day to day without a separate scheduled job.
"""
import json
import sys
from datetime import datetime, timezone

from . import config, db
from .db import PersistenceError


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _parse_dt(value):
    """Accepts either an ISO string (from db.py's JSON-safe rows, or a
    test fixture) or an already-aware datetime - returns an aware
    datetime, or None if there's nothing usable."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _score_ad(ad: dict, now: datetime) -> dict:
    started_at = _parse_dt(ad.get("started_at"))
    first_seen_at = _parse_dt(ad.get("first_seen_at"))
    last_seen_at = _parse_dt(ad.get("last_seen_at"))

    # Recency fallback: if the provider never gave a real start date, use
    # when we first observed the ad instead of dropping the ad entirely -
    # documented here, not a silent/invented substitution. first_seen_at
    # is always set (DB default), so this fallback always resolves.
    effective_start = started_at or first_seen_at
    age_days = max(0.0, (now - effective_start).total_seconds() / 86400)
    recency = _clamp01(1 - age_days / config.RECENCY_WINDOW_DAYS)

    # Longevity: proxy only, see module docstring.
    longevity_days = max(0.0, ((last_seen_at or effective_start) - effective_start).total_seconds() / 86400)
    longevity = _clamp01(longevity_days / config.LONGEVITY_WINDOW_DAYS)

    # Recurrence: collation_count only. Missing evidence -> neutral 0.0,
    # never an invented count, never substituted with times_seen.
    collation_count = ad.get("collation_count")
    recurrence = _clamp01(collation_count / config.RECURRENCE_CAP) if isinstance(collation_count, int) else 0.0

    weight = (
        config.RECENCY_WEIGHT * recency
        + config.LONGEVITY_WEIGHT * longevity
        + config.RECURRENCE_WEIGHT * recurrence
    )

    return {
        "ad_id": ad["ad_id"],
        "brand": ad["brand"],
        "body": ad["body"],
        "headline": ad["headline"],
        "cta": ad["cta"],
        "media_type": ad["media_type"],
        "media_url": ad["media_url"],
        "snapshot_url": ad["snapshot_url"],
        "analysis_result": ad.get("analysis_result"),
        "weight": round(weight, 4),
        "component_scores": {
            "recency": round(recency, 4),
            "longevity": round(longevity, 4),
            "recurrence": round(recurrence, 4),
        },
    }


def compute_ranked_context(conn=None) -> dict:
    """`conn` is injectable (tests pass a fake); a real call leaves it
    None and owns/closes its own connection, matching every other Sequence
    D entrypoint."""
    owns_connection = conn is None
    if owns_connection:
        conn = db.connect()
    try:
        completed = db.list_completed_analyses(conn, page_id=config.ACTIVE_PAGE_ID)
    finally:
        if owns_connection:
            conn.close()

    now = datetime.now(timezone.utc)
    scored = [_score_ad(ad, now) for ad in completed]
    scored = [s for s in scored if s["weight"] >= config.MIN_WEIGHT_THRESHOLD]
    scored.sort(key=lambda s: s["weight"], reverse=True)
    top = scored[: config.TOP_N]

    return {"count": len(top), "context": top}


def main() -> int:
    try:
        output = compute_ranked_context()
    except PersistenceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # never str(exc) - see ad_fetcher/organic_fetcher/main.py
        print(f"error: unexpected failure ({exc.__class__.__name__}).", file=sys.stderr)
        return 1

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
