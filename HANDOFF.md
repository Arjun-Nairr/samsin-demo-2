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

## Live-fetch status: DONE — verified against the real API

`SCRAPECREATORS_API_KEY` was added to `.env` and a real fetch was run:
`cd src && python -m ad_fetcher.main` → exit 0, 30 raw results, 1 credit
charged, 98 credits remaining on the key's account at that point.

**Real-schema bug found and fixed**: the documented example shows
`images: [{ "url": "..." }]`, but every real `IMAGE`-format ad instead
returned `original_image_url` / `resized_image_url` (no `url` key at all).
This silently rejected all 8 real image ads (0 image ads passed) before
the fix. Fixed in `normalizer.py` to check `url` → `original_image_url` →
`resized_image_url`, preferring the original over the resized copy. The
`image_ad.json` fixture was updated to match the real shape so this can't
regress silently. All 13 tests still pass after the fix.

Also observed live: a `display_format` value of `"DPA"` (Dynamic Product
Ads) not in the documented enum. Correctly rejected as unsupported — the
spec restricts Sequence A to `image`/`video` only, and DPA is a distinct
dynamic-catalog ad format, not a mislabeled image/video.

Real run after the fix: 30 raw results → 8 IMAGE, 12 VIDEO, 10 DPA
(rejected as unsupported) → 20 normalized ads (correctly capped at the
`BATCH_SIZE` limit), 0 duplicates or malformed records encountered.

**Advertiser identity was not independently re-verified via company-search**
this session (no separate call was made — `companyName: "Aelfric Eden"` was
used directly, as documented in README). The real page name returned in
the fetched results was `"Aelfric Eden"` for every ad, consistent with the
brief, but this is not the same as cross-checking `page_id`/URL against the
company-search endpoint. Recommended before this feeds anything
higher-stakes: one `GET /v1/facebook/adLibrary/search/companies?query=Aelfric
Eden` call, confirm the official storefront, optionally pin the verified
`pageId` into `config.COMPETITOR`.

## Sanitized example output

Real live-fetch output (media URLs are Meta CDN links with long signed
tokens — truncated below with `...` for readability only; nothing else
altered):

```json
{
  "count": 20,
  "ads": [
    {
      "ad_id": "2176804236421543",
      "brand": "Aelfric Eden",
      "body": "Ready to switch up your streetwear game? Extra 15% OFF with Code: AE15 #AelfricEden #NewIn #StreetStyle #DoubleWaist #FashionDeals",
      "headline": "",
      "cta": "Shop now",
      "media_type": "video",
      "media_url": "https://video-lga3-3.xx.fbcdn.net/o1/v/t2/f2/m366/AQP3mVuAcSM0...mp4?...",
      "started_at": "2026-03-18T07:00:00+00:00",
      "is_active": true,
      "snapshot_url": "https://www.facebook.com/ads/library/?id=2176804236421543"
    },
    {
      "ad_id": "891219893505716",
      "brand": "Aelfric Eden",
      "body": "Final Sale! Limited stock! Shop Now & Own the New School Year! #tee #tracksuit #sweatpants #hoodie #jacket #jeans #outfitinspo #streetwear #fashion #aelfriceden",
      "headline": "Aelfric Eden Big Sale",
      "cta": "Shop now",
      "media_type": "video",
      "media_url": "https://video-lga3-3.xx.fbcdn.net/o1/v/t2/f2/m366/AQPOiUPmNcsx...mp4?...",
      "started_at": "2026-07-16T07:00:00+00:00",
      "is_active": true,
      "snapshot_url": "https://www.facebook.com/ads/library/?id=891219893505716"
    }
  ]
}
```

(18 more ads omitted here — see the live run output captured in this
session's transcript for the full 20. Every `ad_id` was unique, every
`brand` was `"Aelfric Eden"`, `is_active` was `true` on all 20, and
`started_at` ranged from January to August 2026.)

## Known limitations

- Media URLs are third-party CDN URLs (`scontent`/`video.xx.fbcdn.net`) and
  are not durable — they carry signed, time-limited tokens and will expire.
  Not downloaded or persisted by design (Sequence A has no storage).
- `headline` is `""` on most real ads (16/20 in the live run) — confirmed
  live, not just a guess from the docs. Only some campaigns set a headline.
- Company-search identity verification (`page_id`/URL cross-check) was not
  performed this session — `companyName` matching was relied on instead.
- Carousel/DCO `cards[]` extraction (including the real image-field name
  fix) has never been exercised against a real ad with non-empty `cards` —
  all 30 live results had `cards: []`. Still fixture-only for that path.

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
error path, `.env` git-ignore, **and now a real live fetch** (20 normalized
ads from 30 raw results, 1 credit charged) — including catching and fixing
a real schema mismatch between the docs and the live API (image URL field
name).

**Verified only with fixtures**: carousel/DCO `cards[]` extraction path —
no real ad in the live batch had non-empty `cards`, so that logic is
untested against real data.

**Blocked / not done**: company-search advertiser identity verification
(companyName was used directly and matched on every live result, but
`page_id`/URL was never independently cross-checked).

**Intentionally deferred** (per spec, documentation only — not built):
organic post/reel enrichment, matching/confidence scoring, ranking/
weighting, OpenClaw integration, cron/scheduling, multi-competitor support.
