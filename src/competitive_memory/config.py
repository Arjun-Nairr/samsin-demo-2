"""Sequence D config: the active competitor scope, analysis batch size,
and every ranking constant in one place - per the brief, thresholds/
windows/weights live together here, not scattered across ranking.py.

Reuses ad_fetcher's locked competitor identity (one page ID, one source of
truth) instead of duplicating it - see ad_fetcher/config.py for how it was
verified.
"""
from ad_fetcher.config import COMPETITOR

ACTIVE_PAGE_ID = COMPETITOR["page_id"]

# --- Part 3: analysis persistence ---
# Small and configurable, per the brief - not a full backlog dump in one call.
PENDING_BATCH_SIZE = 10

# --- Part 4: ranking ---
# weight = RECENCY_WEIGHT*recency + LONGEVITY_WEIGHT*longevity + RECURRENCE_WEIGHT*recurrence
# Weights sum to 1.0; each component score is normalized to [0, 1] before weighting.
RECENCY_WEIGHT = 0.5
LONGEVITY_WEIGHT = 0.3
RECURRENCE_WEIGHT = 0.2

# Recency: 1.0 for an ad that started today, decaying linearly to 0.0 for
# one that started this many days ago (or longer). A proxy for freshness,
# not a claim about performance.
RECENCY_WINDOW_DAYS = 30

# Longevity: 0.0 for a just-discovered ad, rising linearly to 1.0 once
# it's been observed running this many days. A proxy for "the advertiser
# is still running it" - not proof it's profitable.
LONGEVITY_WINDOW_DAYS = 60

# Recurrence: collation_count (never times_seen - that's an observation
# counter, not variant evidence) at or above this value scores 1.0; below
# it scores proportionally; missing evidence scores a neutral 0.0, never
# an invented count.
RECURRENCE_CAP = 5

# Ads scoring below this are dropped from the ranked context entirely.
MIN_WEIGHT_THRESHOLD = 0.2

# Compact context size - only the top N survive, ordered by weight.
TOP_N = 10
