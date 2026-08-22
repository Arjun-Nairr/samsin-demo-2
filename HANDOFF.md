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

## Working tree (superseded — see Sequence B section below for current state)

*(Original Sequence A note, kept for history: at the time this was written,
Sequence A's files were staged with `git add -A` but not yet committed.
They were committed shortly after, in commit `a0054a7`, then pushed to
`https://github.com/Arjun-Nairr/samsin-demo-2` along with a follow-up fix
commit `f5cbaf6`. See "Git status" under Sequence B below for the accurate,
current state.)*

## Next recommended milestone (Sequence B — now implemented, see below)

---

# Sequence B — Organic Instagram Posts

## Milestone completed

One hardcoded Aelfric Eden Instagram account (`aelfricedenofficial`) →
ScrapeCreators Instagram Posts API (`GET /v2/instagram/user/posts`) → raw
public posts/reels → deterministic cleanup → normalized organic-content
JSON, printed by a separate CLI. Sequence A's package (`ad_fetcher`) was
not modified — only imported from (`get_api_key`, `ScrapeCreatorsError`).

## Files added

```
src/organic_fetcher/
  __init__.py
  config.py                  ACCOUNT_HANDLE, BRAND_LABEL, PLATFORM;
                              re-exports ad_fetcher.config.get_api_key
  scrapecreators_client.py   isolated HTTP call to /v2/instagram/user/posts,
                              imports API_BASE + ScrapeCreatorsError from
                              ad_fetcher's client (same exception type,
                              same retry shape - not merged into one module)
  normalizer.py               deterministic cleanup, carousel resolution
  service.py                   wires client + normalizer, rejects a
                                missing/non-list `items` as a provider error
  main.py                      CLI: same stdout/stderr/exit-code contract
tests/
  test_organic_normalizer.py
  fixtures_organic/  (video_post, carousel_post, carousel_post_video_first,
                       image_post, zero_engagement_video, malformed,
                       missing_id, missing_media, unsupported_media_type,
                       duplicate_post, empty_response,
                       malformed_items_response)
```

Files changed: `README.md` (Sequence B sections added), `HANDOFF.md` (this
section). **No files in `src/ad_fetcher/` or `tests/fixtures/` were
touched.**

## Files removed

None.

## Key implementation decisions

- **Reuse, not refactor**: imported `ad_fetcher.config.get_api_key` (it's
  provider-agnostic — just reads `SCRAPECREATORS_API_KEY`) and
  `ad_fetcher.scrapecreators_client.ScrapeCreatorsError` (so both CLIs'
  error handling is the same shape) rather than duplicating them. Did
  **not** extract a shared HTTP-retry helper between the two clients —
  that would mean editing Sequence A's file for a second call site, which
  the brief explicitly said not to do. The ~30-line retry loop is
  duplicated once, isolated per package.
- **`post_id` = the API's `id` field, not `pk`.** Live-confirmed: `pk` is
  `null` on every item under `trim=true`. `id` is the real stable ID.
- **`permalink` is read directly from the API's `url` field** — present
  on every real item, including reels (which use `/p/<code>/`, not
  `/reel/...`). Shortcode construction is fallback-only, per spec.
- **Carousel resolution** iterates `carousel_media[]` for the first
  supported item (image or video) with a usable URL — not blindly index 0
  — and always pulls engagement metrics from the **top-level container**,
  never the sub-item, because live data confirms sub-items carry media
  fields but never their own `play_count`/`like_count`/`comment_count`.
- **`organic_view_count`** prefers `ig_play_count` over `play_count`,
  falls back to `null` only when both are absent/`None` — a real `0` is
  never coerced to `null` (verified by a dedicated test).
- **One request, no pagination, no limit**: the endpoint doesn't take a
  page-size param and Sequence B doesn't loop on `next_max_id`/`more_available` —
  whatever one page returns (12 items on every call made this session) is
  the whole batch, per spec.
- **Two hardcoded Aelfric Eden identifiers now exist independently**:
  Sequence A's `companyName` (Meta ad library) and Sequence B's Instagram
  `handle`. Neither was cross-verified against the other (e.g. confirming
  the Instagram account is the one actually linked to the ad library page)
  — flagging this as unverified, not silently assuming they're the same
  entity just because both say "Aelfric Eden".

## Commands run

```
python -m unittest discover -s tests -v          → 28 passed (13 Sequence A + 15 Sequence B)
cd src && python -m organic_fetcher.main          → exit 0, 12 posts, real live output
```

(Sequence A's suite was re-run as part of the same `discover` command
specifically to check for regressions — none found.)

## Test results

15 Sequence B tests, all passing: valid image post, valid video/reel,
carousel resolving to its first supported item (tested for both an
image-first and a video-first carousel), a real-zero-engagement post
(`0` stays `0`, not `null`), malformed record, missing post ID, missing
media, unsupported media type, duplicate post ID (keep-first), empty
results, missing-key error (no request made), error messages never
containing the key (checked directly against source), and a non-list
`items` response correctly raising a provider error distinct from a
genuinely empty result.

All 13 Sequence A tests still pass, unmodified, in the same run — no
regression.

## Live-fetch status: DONE — verified against the real API

Ran `cd src && python -m organic_fetcher.main` with the existing
`SCRAPECREATORS_API_KEY` from `.env`. Exit 0, valid JSON to stdout only.

**Real-schema discoveries** (this is why the "make one live request first"
step in the brief mattered):

1. `pk` is `null` on every item under `trim=true` — `id` is the real
   stable ID. Not documented explicitly; found by inspection.
2. The API returns a ready-made permalink at `url` for every item,
   including reels, in the `/p/<code>/` form — not `/reel/<code>/` as
   might be assumed. Used directly; shortcode construction is dead code on
   real data (still kept as the documented fallback).
3. `carousel_media[]` sub-items have their own `media_type` and creative
   fields but **no** `play_count`/`ig_play_count`/`like_count`/`comment_count` —
   confirmed by inspecting an actual carousel response, not assumed.
   Engagement is read from the container item unconditionally.
4. Video items also carry `image_versions2` (the poster/cover frame) —
   used as `thumbnail_url`.

**Live run stats** (one CLI invocation, `python -m organic_fetcher.main`):

- Raw item count: 12
- Normalized count: 12 (0 rejected this run — every raw item had usable
  media; earlier schema-inspection calls during development did surface
  carousels whose selected item lacked view counts, which is expected and
  correctly `null`, not a rejection)
- By post type: 7 video, 5 image (5 of the 6 raw `carousel_container`
  items resolved to an image first-item; 1 resolved to a video first-item)
- Video posts with a view count: 6 of 7 (the one video without a view
  count is the carousel-resolved video — carousels never carry
  `play_count`, confirmed per point 3 above)
- Missing likes: 0 of 12. Missing comments: 0 of 12. Missing views: 6 of
  12 (all accounted for: 5 image posts + 1 carousel-resolved video, all
  correctly `null` per the schema, not a bug)

**Credits used this session (Sequence B total, across dev + verification)**:
3 requests, 3 credits charged — one initial schema-inspection probe (done
deliberately before writing any code, per the brief), one CLI run for the
stats above, one additional raw-response check to confirm the exact
`credits_charged`/`credits_remaining` values. The shipped CLI itself makes
exactly **one** request per invocation, as required — the extra 2 were
this session's own verification overhead, not something the delivered code
does repeatedly.

## Sanitized example output

Real live output (one real image post, one real reel; media URLs
truncated — signed tokens only, nothing else altered):

```json
[
  {
    "platform": "instagram",
    "post_id": "3956409305604079263_11087474383",
    "shortcode": "Dbn_U0ulL6f",
    "brand": "Aelfric Eden",
    "account_handle": "aelfricedenofficial",
    "post_type": "image",
    "caption": "Pick your back-to-school character. Which look is your vibe this semester? Anniversary Sale is live. Up to 40% Off selected styles. More surprises await online. #aelfriceden",
    "published_at": "2026-08-04T16:26:04+00:00",
    "permalink": "https://www.instagram.com/p/Dbn_U0ulL6f/",
    "media_url": "https://scontent-dfw5-2.cdninstagram.com/v/t51.82787-15/7646...",
    "thumbnail_url": null,
    "organic_view_count": null,
    "organic_like_count": 648,
    "organic_comment_count": 19
  },
  {
    "platform": "instagram",
    "post_id": "3954222268720362185_11087474383",
    "shortcode": "DbgODP6BDLJ",
    "brand": "Aelfric Eden",
    "account_handle": "aelfricedenofficial",
    "post_type": "video",
    "caption": "The first day fit starts here. Back to School Sale is now live. Up to 40% Off selected styles. #aelfriceden",
    "published_at": "2026-08-01T16:00:08+00:00",
    "permalink": "https://www.instagram.com/p/DbgODP6BDLJ/",
    "media_url": "https://scontent-dfw5-1.cdninstagram.com/o1/v/t2/f2/m86/AQMj...",
    "thumbnail_url": "https://scontent-dfw6-1.cdninstagram.com/v/t51.82787-15/7761...",
    "organic_view_count": 123485,
    "organic_like_count": 3,
    "organic_comment_count": 13
  }
]
```

## Known limitations (Sequence B)

- No plain (non-carousel) image post appeared in any live batch this
  session — all top-level `image`-typed records in the real run came from
  carousel resolution. The plain-image-post code path is covered by a
  realistic synthetic fixture (`image_post.json`), not real data.
- Instagram CDN media URLs are signed and will expire — not
  downloaded/persisted, same posture as Sequence A.
- The Instagram handle and the Facebook ad-library `companyName` were
  each hardcoded independently and never cross-verified as the same real
  business (see design decisions above).
- `play_count`/`like_count`/`comment_count` accuracy is whatever
  Instagram's API reports — ScrapeCreators' own docs note play counts "can
  sometimes be inaccurate." Not something this code can correct for.

## Git status (current, accurate)

```
$ git status
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean   (as of the start of this session,
                                          before Sequence B's new files)
```

After adding Sequence B's files, the tree has these untracked/modified
paths, **none of which have been committed or pushed**:

```
new:      src/organic_fetcher/{__init__,config,scrapecreators_client,normalizer,service,main}.py
new:      tests/test_organic_normalizer.py
new:      tests/fixtures_organic/*.json  (12 files)
modified: README.md
modified: HANDOFF.md
```

Per the brief: **not committing, pushing, or deploying this** unless
explicitly told to.

## What remains for Sequence C (documentation only — not implemented)

Deterministic audit of whether advertisements can be matched to organic
posts using stable IDs, explicit URLs, or exact creative evidence.

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

### Sequence B additions to this report

**Verified working**: all 15 normalizer/service tests, output contract
shape, CLI stdout/stderr/exit-code contract, missing-key error path, real
zero-vs-null distinction, non-list-`items` provider-error handling, **and a
real live fetch** (12/12 raw items normalized, 3 credits charged across
this session's dev+verification calls) — including three real-schema
discoveries not evident from the docs (`pk` always null, ready-made
permalinks, carousel sub-items never carrying their own engagement).

**Verified only with fixtures**: the plain (non-carousel) image-post code
path — no real post of that exact shape appeared in any live batch this
session, only carousel-resolved images.

**Blocked / not done**: cross-verification that the Instagram handle and
the Facebook ad-library `companyName` refer to the same real business.

**Intentionally deferred** (per spec, documentation only — not built):
Sequence C's matching audit, Facebook posts/reels, any ranking/weighting/
scoring, views-per-day, AI/vision, persistence, multi-competitor support.
