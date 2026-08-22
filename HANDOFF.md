# Handoff — Sequence A

## Milestone completed

Sequence A: one hardcoded competitor (Aelfric Eden) → ScrapeCreators Meta
Ad Library Company Ads API → deterministic cleanup → normalized JSON list,
printed to stdout by a CLI.

## Starting point

No existing repository matched the brief. `Downloads/samsin-pricing-demo`
is the only Samsin-related project on disk, but it's an unrelated pipeline
(Samsin's own product pricing → flyer generation → Instagram posting) with
no Apify code, no ad-library concept, and not a git repo. Confirmed with
the user this is a fresh build, not a migration — no Apify code existed to
remove.

## Files added

```
samsin-ad-intelligence/
  .env                              (git-ignored, blank key placeholder)
  .env.example
  .gitignore
  README.md
  HANDOFF.md
  src/ad_fetcher/
    __init__.py
    config.py               competitor config, .env loader, API key resolution
    scrapecreators_client.py   isolated HTTP call (urllib, stdlib)
    normalizer.py            pure deterministic cleanup, no HTTP knowledge
    service.py               wires client + normalizer into the output contract
    main.py                  CLI: stdout=JSON only, stderr=diagnostics, exit code
  tests/
    test_normalizer.py
    fixtures/  (image_ad, video_ad, carousel_ad, missing_media,
                unsupported_media, malformed, missing_id, duplicate_ad,
                empty_results — all shaped to the real documented schema)
```

Nothing removed — nothing pre-existing to remove.

## Key implementation decisions

- **Provider isolation**: only `scrapecreators_client.py` knows this is
  HTTP/ScrapeCreators-shaped. `normalizer.py` and `service.py` work on
  plain dicts, so swapping providers later doesn't touch cleanup logic.
- **Synchronous, ephemeral**: this is a single small CLI batch (~20 ads),
  not a background job — a sync `urllib.request` call is simpler and
  sufficient; adding async/queues would be complexity with no payoff at
  this volume. Output is not persisted; regenerating it is one cheap call.
- **Stdlib only**: `urllib` for HTTP, a 20-line `.env` parser matching the
  pattern already used in the sibling `samsin-pricing-demo` project. No
  `requests`/`python-dotenv` added for what a few lines cover.
- **Advertiser identity — companyName, not company-search**: the documented
  Company Ads endpoint accepts `companyName` directly, so Sequence A skips
  the company-search/resolution call entirely (fewer requests, fewer
  credits). **This means identity has not been independently verified
  against a returned `page_id`/URL** — see "Blocked" below.
- **Request count / cost**: one Company Ads call per run (documented at 1
  credit/request), no pagination loop, capped to 20 ads after
  normalization. No company-search call. No per-ad "Ad Details" calls —
  the Company Ads response already carries every field Sequence A needs.
- **One deterministic primary asset per ad**: carousel/DCO ads use
  `cards[0]`, falling back to top-level `snapshot` fields for anything the
  card omits. Documented in README.
- **`snapshot_url` is constructed**, not returned by the API: Meta's own
  stable public Ad Library URL format built from `ad_archive_id`.

## Commands run

```
git init
python -m unittest tests.test_normalizer -v      → 13 passed
cd src && python -m ad_fetcher.main               → exit 1, stderr:
  "error: Missing SCRAPECREATORS_API_KEY. Set it in .env or the environment before running."
git add -A && git status --porcelain              → confirms .env absent, all other files staged
```

## Test results

All 13 tests pass, covering: valid image ad, valid video ad, carousel (primary
card selection), missing media, unsupported media type, malformed record,
missing ad ID, duplicate ID (keep-first), empty results, and provider-error
handling that never leaks the API key (checked directly against source, no
live call needed for that assertion).

## Live-fetch status: BLOCKED — no credentials available

No `SCRAPECREATORS_API_KEY` was available in this session. **No live
fetch has been attempted or claimed.** All verification above is
fixture-based, built directly from the current official ScrapeCreators
docs (`/v1/facebook/adlibrary/company/ads/` and
`/v1/facebook/adlibrary/search/companies/`), fetched during this session —
not guessed.

**Advertiser identity is therefore also unverified.** Config uses
`companyName: "Aelfric Eden"` (exact spelling from the brief). Before
trusting a real run: call the company-search endpoint once
(`GET /v1/facebook/adLibrary/search/companies?query=Aelfric Eden`), confirm
the returned `name`/`page_alias`/`ig_username` genuinely matches the
official Aelfric Eden storefront (not a lookalike/fan page), and — only if
worth the extra request — swap the verified `pageId` into
`config.COMPETITOR` in place of `companyName`. This is a one-time
resolution, not a per-run cost.

**Exact next step for whoever has a key**: add it to `.env`, run
`cd src && python -m ad_fetcher.main`, confirm real output matches the
contract shape, and paste a sanitized sample (strip nothing but the key —
ad content is already public) into this file's "Sanitized example output"
section below.

## Sanitized example output

Fixture-derived (not live) — shape matches what a real run will produce:

```json
{
  "count": 3,
  "ads": [
    {
      "ad_id": "111111111111111",
      "brand": "Aelfric Eden",
      "body": "New drop: oversized graphic tees.",
      "headline": "",
      "cta": "Shop Now",
      "media_type": "image",
      "media_url": "https://scontent.xx.fbcdn.net/ad-image-1.jpg",
      "started_at": "2025-06-15T15:06:40+00:00",
      "is_active": true,
      "snapshot_url": "https://www.facebook.com/ads/library/?id=111111111111111"
    },
    {
      "ad_id": "444444444444444",
      "brand": "Aelfric Eden",
      "body": "Behind the scenes of our summer collection.",
      "headline": "",
      "cta": "Learn More",
      "media_type": "video",
      "media_url": "https://video.xx.fbcdn.net/ad-video-hd.mp4",
      "started_at": "2025-06-27T04:53:20+00:00",
      "is_active": true,
      "snapshot_url": "https://www.facebook.com/ads/library/?id=444444444444444"
    },
    {
      "ad_id": "666666666666666",
      "brand": "Aelfric Eden",
      "body": "Card 1: cropped hoodie, 4 colorways.",
      "headline": "Cropped Hoodie",
      "cta": "Shop Now",
      "media_type": "image",
      "media_url": "https://scontent.xx.fbcdn.net/card-1.jpg",
      "started_at": "2025-07-08T18:40:00+00:00",
      "is_active": false,
      "snapshot_url": "https://www.facebook.com/ads/library/?id=666666666666666"
    }
  ]
}
```

## Known limitations

- Media URLs are third-party CDN URLs (`scontent`/`video.xx.fbcdn.net`) and
  are not durable — they can expire. Not downloaded or persisted by design
  (Sequence A has no storage).
- `headline` will be `""` for the overwhelming majority of real ads (no
  documented headline field outside carousel cards).
- Company-search identity verification is unperformed (see Blocked above).
- Credit usage for a real run cannot be reported yet (no live call made).

## Working tree

Clean except for tracked new files (all staged with `git add -A`, nothing
committed — no commit was made per "don't push/commit without being asked"
carried forward from prior project conventions). `.env` confirmed absent
from `git status --porcelain` output.

## Next recommended milestone (not implemented)

Enrichment: fetch public Facebook/Instagram posts and reels for organic
engagement (`GET /v1/facebook/profile/reels`, `GET /v1/facebook/post`,
Instagram equivalents), store as `organic_view_count` (never
`ad_view_count`), keep `ad_started_at` separate from
`organic_post_published_at`, match ads to posts only via explicit shared
URL/ID or exact creative match (never text similarity alone), and leave
unmatched ads `unknown` rather than zero. No ranking/weighting in that
milestone either — that stays a separate, later, user-approved decision.

---

## Report

**Verified working**: normalizer cleanup rules (all 10 required cases),
output contract shape, CLI stdout/stderr/exit-code contract, missing-key
error path, `.env` git-ignore.

**Verified only with fixtures**: all field-extraction logic (image/video/
carousel paths), dedup, ordering, limit — fixtures built from the current
official docs, not guessed, but not run against a real response.

**Blocked pending credentials**: any live ScrapeCreators call, advertiser
identity verification via company-search, real credit-cost report.

**Intentionally deferred** (per spec, documentation only — not built):
organic post/reel enrichment, matching/confidence scoring, ranking/
weighting, OpenClaw integration, cron/scheduling, multi-competitor support.
