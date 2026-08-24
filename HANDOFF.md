# Handoff — Sequences A, B, C, D & E

## Current status (read this first)

- **Competitor replaced: PacSun → Billionaire Boys Club Icecream.** PacSun
  was confirmed twice, live, to have ~0 usable static image/meme ads (see
  Sequence E, Part 1 below) - it has now actually been replaced, not just
  flagged. New competitor: `page_id 142427132456114`, Instagram handle
  `bbcicecream`, verified via a live diagnostic fetch that found 16 usable
  active US static-image ads. Changed in one place -
  `src/ad_fetcher/config.py`'s `COMPETITOR` dict - and
  `src/organic_fetcher/config.py`'s `ACCOUNT_HANDLE`/`BRAND_LABEL` (the
  Instagram handle was **not** independently re-verified via
  company-search this session, same caveat PacSun's handle originally
  had). All 155 offline tests still pass unchanged - `competitive_memory`
  scopes everything off `ad_fetcher.config.COMPETITOR` already, so no
  other file needed a code change. Live-verified: one real
  `competitive_memory.main` run (1 ScrapeCreators credit) fetched 16 ads,
  inserted 16 new rows into Neon, all with `page_id = 142427132456114`,
  all `media_type = image` with a usable `latest_media_url`, all
  `analysis_status = pending`. One of those 16 (`ad_id
  2360284104778799`) had an explicitly-artificial test analysis
  (`__synthetic_test_analysis__: true`) saved via `analysis_cli save` to
  smoke-test the persistence boundary, its real ranked-context payload
  captured via `competitive_memory.ranking` (see "Competitor replacement
  verification" below for the full payload), then manually reset back to
  `analysis_status = pending` with `analysis_result`/`analysis_attempts`/
  `analysis_error`/`analyzed_at` all cleared - confirmed via a direct
  `SELECT` after the reset. No fake analysis remains in the database.
  Sequence B (`organic_fetcher`) was **not** re-run live this session -
  identity updated, not live-verified, consistent with how Sequence B was
  handled during the PacSun switch in Sequence D.
- Three inaccuracies in this file, corrected this session: (1) the
  Aelfric Eden rows were already correctly stated as deleted (not
  "still exist") as of the prior Sequence E pass - re-checked, no change
  needed. (2) Sequence D's credit total was already reconciled to 3 in
  the prior Sequence E pass - re-checked, no change needed. (3) the
  ranking smoke-test synthetic-row disclosure was already present from
  the prior Sequence E pass - re-checked, no change needed. (These three
  corrections were made during Sequence E; this session verified they are
  still accurate rather than re-doing them.)
- **Sequence E** (superseded by the entries above for anything
  competitor-identity-related; the Gemini/ImgBB/Instagram pipeline
  described below is unaffected by the competitor swap) (`samsin_reference`, `creative_generation`,
  `manual_publishing`) — **implemented, 30 tests offline, fully
  live-verified end to end**: real Samsin catalog fetch → 2 real Gemini
  candidates → human picks one → real ImgBB upload → real Instagram
  publish. **A real post is now live**: `media_id 18386960494162488`,
  https://www.instagram.com/p/DcZEKJ-HL2J/, on `test.account4289`. See
  "Sequence E" at the bottom for the full story, including a real
  first-attempt creative-quality miss (not caught by deterministic checks
  - correctly so, since those never claim to judge quality) and a real
  Gemini dimension bug that required adding Pillow.
- **PacSun update (relevant to Sequence A)**: the Part 1 diagnostic this
  session (`status=ALL`, 60-day window, still `country=US`+`IMAGE_AND_MEME`)
  confirms PacSun has **zero** usable static image/meme ads right now,
  not just under the narrower `status=ACTIVE` filter from Sequence D. Per
  the brief: production config was **not** changed, and this is reported
  as "PacSun should be replaced" for Sequence A - see "Sequence E, Part 1"
  below for the exact numbers.

- **Competitor changed in Sequence D**: everything below that predates
  Sequence D refers to **Aelfric Eden**. The active competitor is now
  **PacSun** (`page_id` `7133041750`, verified via ScrapeCreators'
  company-search endpoint — see `ad_fetcher/config.py`). **Correction**:
  the old Aelfric Eden rows do **not** still exist — at the user's
  explicit direction, all 18 of them were deleted (exact `brand =
  'Aelfric Eden'` match, inspected before deleting) during Sequence D's
  live verification, so PacSun's data would show cleanly. `competitor_ads`
  had 0 rows immediately after. `page_id` scoping is still the mechanism
  that *would* exclude a different competitor's rows if any existed - it's
  just moot right now since none do. See "Sequence D" at the bottom for
  the full verification and "Sequence E" for what's changed since (PacSun
  found to have no usable static ads at all, even with a wider window).
- **Sequence A** (paid Meta ads, `ad_fetcher`) — **implemented, tested, live-verified** for Aelfric Eden originally; **re-verified for PacSun in Sequence D** with a corrected, verified-`pageId` request (see below).
- **Sequence B** (organic Instagram posts, `organic_fetcher`) — **implemented, tested, live-verified** for Aelfric Eden; identity updated to PacSun's verified handle (`pacsun`) in Sequence D, not re-run live (Sequence B was explicitly out of scope for Sequence D's live verification).
- **Sequence C** (Neon persistence of paid ads, `competitive_memory`) —
  **implemented, tested offline (84 tests), and now fully live-verified**,
  including a real repeated run proving idempotent insert/update
  behavior. An earlier session's live attempt spent a ScrapeCreators
  credit and then failed at the database-connection step — root-caused to
  a call-order bug (fetch happened before the DB connection was
  established) and fixed in the "Sequence C — Neon Reliability Fix"
  section at the bottom of this file, which also adds bounded
  connect-timeout/retry and closes a generic-exception secret-leak path
  across all three CLIs. Both a fresh-insert run and a repeat-fetch
  idempotence run have now succeeded for real against Neon.
  *(Note: an earlier part of this file used "Sequence C" to mean a future
  ads↔organic-post matching audit. That name has been reassigned to this
  persistence milestone instead — see the marked note where that occurs.)*
- **Sequence D** (`competitive_memory.analysis` / `.ranking`) — paid-ad
  source corrected to a verified `pageId` (static-image-only contract),
  weighting evidence (`page_id`/`collation_id`/`collation_count`) added
  via migration `0002`, an analysis-persistence boundary (pending queue,
  save/fail, all competitor-scoped) added, and a deterministic V1 ranking
  function added. **113 tests offline, all passing.** Live verification:
  see "Sequence D" at the bottom for the exact outcome and credits spent.
- Ads↔organic-post matching, AI analysis (model calls), weighting *beyond*
  Sequence D's documented V1 proxy, and everything else in the various
  non-goals lists — **still not implemented**, documented only.
- Everything below this point is presented in the order it was written,
  oldest first, so history is preserved. Where an older section's status
  claim has since changed, it is marked **(superseded)** with a pointer to
  the current statement — do not read an unmarked older section as current
  without checking for a later update.
- The Neon project used for verification had one pre-existing table,
  `hermes_runs` (28 rows, unrelated to this repo — from a different,
  separate project). It was dropped with explicit user confirmation after
  the mismatch between the brief's description and what was actually
  found was surfaced first. See "Neon verification status" for the exact
  sequence of events.
- Git status as of the start of the Sequence C milestone: clean, `HEAD`
  and `origin/main` both at `9bb184e`. Committed and pushed since — check
  `git log`/`git status` directly for the current authoritative state
  rather than trusting a specific commit hash written here, since this
  file is not guaranteed to be updated the instant something is pushed.

## Milestone completed (Sequence A)

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

## Git status at the time Sequence B was written (superseded)

*(This section describes a since-resolved intermediate state — Sequence B's
new files, listed below as untracked, were committed as `b3e44a2` and
pushed to `origin/main` shortly after this was written. For the actual
current git status, see "Cleanup pass" at the bottom of this file.)*

```
$ git status
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean   (as of the start of this session,
                                          before Sequence B's new files)
```

At that point the tree had these untracked/modified paths:

```
new:      src/organic_fetcher/{__init__,config,scrapecreators_client,normalizer,service,main}.py
new:      tests/test_organic_normalizer.py
new:      tests/fixtures_organic/*.json  (12 files)
modified: README.md
modified: HANDOFF.md
```

They were committed as `b3e44a2` ("Sequence B: organic Instagram posts
fetcher for aelfricedenofficial") and pushed to
`https://github.com/Arjun-Nairr/samsin-demo-2` in the same session, once
the user explicitly authorized it.

## What remains for Sequence C

See the "What remains for Sequence C" section at the very bottom of this
file (in "Cleanup pass") for the current, single copy of this scope note —
kept in one place instead of two copies that could drift apart.

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

**Intentionally deferred at the time this was written** *(superseded — organic
enrichment is no longer deferred, it shipped as Sequence B; see the section
below)*: ~~organic post/reel enrichment~~, matching/confidence scoring,
ranking/weighting, OpenClaw integration, cron/scheduling, multi-competitor
support.

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

---

# Cleanup pass (hardening, no new sequence)

Scope: documentation corrections, two normalization edge-case bugs, stronger
provider-error tests, and a note on an existing reusable Instagram-publishing
sandbox for a future integration. **Sequence C was not started.**

## Starting state

`git status` before any edit: clean, `HEAD` and `origin/main` both at
`b3e44a2` (the Sequence B commit). Confirmed with `git rev-parse HEAD` and
`git rev-parse origin/main` — both printed the same hash.

## Documentation fixes

- Title changed from "Handoff — Sequence A" to "Handoff — Sequences A & B"
  to reflect that both are now implemented.
- Added a "Current status" section at the top so a future agent doesn't
  have to read the whole file's history to know what's actually current.
- The Sequence A report's "Intentionally deferred" line used to list
  "organic post/reel enrichment" as deferred — contradicted by Sequence B
  existing. Struck through and marked superseded, pointing at the Sequence
  B section instead of just deleting the historical statement.
- The Sequence B "Git status (current, accurate)" section was itself stale
  the moment Sequence B got committed and pushed — retitled "at the time
  Sequence B was written (superseded)" and pointed at this section.
- No fresh GitHub remote re-verification was performed as part of this
  cleanup beyond the `git rev-parse origin/main` check above (that's a
  local check of the tracking ref, not a live fetch from GitHub) — not
  claiming more than that.

## Bugs fixed

1. **First-candidate-only media selection (both sequences).** Both
   normalizers picked `candidates[0]` / `versions[0]` unconditionally, so a
   malformed or URL-less first entry caused the whole record to be
   rejected even when a later candidate had a perfectly good URL. Real
   ScrapeCreators responses return multiple candidates at different
   resolutions/qualities — provider order is not a validity guarantee.
   Fixed in `organic_fetcher/normalizer.py` (`_image_url`, video branch of
   `_resolve_single_media`) and `ad_fetcher/normalizer.py`
   (`_resolve_creative`'s image and video branches) to scan every
   candidate in provider order and take the first one that's actually a
   valid `http(s)://` URL. The deterministic **carousel/card primary-item**
   rule (which item is selected) is untouched — this only changes how a
   URL is picked *within* an already-selected item.
2. **Boolean timestamps silently accepted (both sequences).** `bool` is a
   subclass of `int` in Python, so `isinstance(True, int)` is `True`. Both
   normalizers used `isinstance(x, (int, float))` to gate timestamp
   conversion, so `"taken_at": true` or `"start_date": false` would have
   silently produced a bogus `1970-01-01T00:00:0(0|1)Z` instead of being
   treated as invalid. Fixed in both `normalize_post` (`taken_at`) and
   `normalize_ad` (`start_date`) by adding `and not isinstance(x, bool)`.
   The record itself is not rejected — only the date field becomes `null`,
   consistent with "missing values stay `null`, never invented."
3. **`organic_fetcher.service` didn't validate the top-level response
   shape.** It called `raw.get("items")` directly; if the provider (or a
   bug) ever returned a bare list/string/`null` instead of a JSON object,
   this would raise an unhandled `AttributeError` rather than a clean
   `ScrapeCreatorsError`. Fixed by checking `isinstance(raw, dict)` first
   and raising `ScrapeCreatorsError("...was not a JSON object.")` — kept
   distinct from the existing missing/non-list `items` check, which stays
   for the case where the top level *is* a dict but `items` itself is
   wrong shape (still distinct from a genuinely empty `items: []`).

## Files changed

```
src/ad_fetcher/normalizer.py         candidate-scan fix, bool-timestamp fix
src/organic_fetcher/normalizer.py    candidate-scan fix, bool-timestamp fix
src/organic_fetcher/service.py       top-level dict validation
tests/test_normalizer.py             +9 tests (candidate fallback x2, bool
                                      timestamp, 5 mocked provider-error tests)
tests/test_organic_normalizer.py     +9 tests (candidate fallback, bool
                                      timestamp, 4 top-level-shape tests,
                                      4 mocked provider-error tests, +1
                                      helper for patching the service layer)
tests/fixtures/video_ad_later_candidate.json        new
tests/fixtures/image_ad_later_candidate.json        new
tests/fixtures/boolean_start_date.json              new
tests/fixtures_organic/video_post_later_candidate.json  new
tests/fixtures_organic/boolean_timestamp.json           new
HANDOFF.md                           this section + corrections above
```

`README.md` was reviewed and left unchanged - its documented output
contracts and run commands were checked against the current code and are
still accurate.

No files removed. No files in `ad_fetcher`/`organic_fetcher` were renamed;
no architecture, matching, scoring, database, OpenClaw, scheduling,
Facebook-organic-fetching, or Instagram-publishing code was added, per
scope.

## Provider-error test strengthening

Per the brief, the existing source-code-scanning "does the string `api_key`
appear near a `raise`" tests were **kept, not deleted** (they're cheap and
still catch an obvious mistake), and **supplemented** with behavioral tests
that mock `urllib.request.urlopen` (and `time.sleep`, to keep the retry
loop's tests instant) and assert on the actual raised `ScrapeCreatorsError`
message for: HTTP 401 (auth failure), HTTP 500 (generic non-2xx),
`TimeoutError`, `urllib.error.URLError` (network failure), and malformed
JSON in the response body — five behavioral tests per sequence, all
asserting a fake secret key string never appears in the exception text.
`organic_fetcher`'s service-layer tests additionally cover a bare
list/string/`null` top-level response (new) and the existing non-list
`items` case, using a small in-file context-manager helper that swaps
`organic_fetcher.service.fetch_instagram_posts` for a stub — no mocking
library beyond stdlib `unittest.mock`, no new test framework.

## Tests run

```
python -m unittest discover -s tests -v
```

**Result: 45 passed, 0 failed** (13 original Sequence A + 6 new Sequence A
+ 15 original Sequence B + 11 new Sequence B). Ran in 0.031s — confirms no
live network calls were made (a real HTTP round-trip would be visibly
slower, and none of these tests touch the real network or `.env` key at
all; the mocked tests use a fake in-test key string, never the real one).

No live ScrapeCreators requests were made anywhere in this cleanup pass —
zero credits spent. Both CLIs' output contracts (`ad_fetcher.main` /
`organic_fetcher.main`) were verified unchanged by inspection: no field was
added, removed, or renamed in either `normalize_ad`'s or `normalize_post`'s
return dict; only internal URL-selection and timestamp-validation logic
changed.

## Git status (current, committed and pushed)

The cleanup changes were committed and pushed once the user explicitly
authorized it, after this file's cleanup-pass content (everything above
this line) was already written:

```
git add -A
git commit -m "Cleanup/hardening pass: fix candidate-selection and bool-timestamp bugs" → b23d505
git push                                                                                 → b3e44a2..b23d505  main -> main
```

`git status --porcelain` is now empty; `HEAD` and `origin/main` both sit at
`b23d505`. `README.md` was left untouched — its documented commands and
output contracts were checked against the current code and are still
accurate. `.env` was not read, printed, modified, or committed at any
point (confirmed absent from every `git status`/`git add` output above).

## Reusable Instagram-publishing sandbox (for a future integration only)

A separate, unrelated project — `C:\Users\dwish\Downloads\samsin-pricing-demo`
(Samsin's own pricing/flyer/Instagram-posting pipeline, not part of this
repo) — already contains a **live-tested** Instagram publishing path.
Documented here for later reuse; **nothing was run, uploaded, published, or
copied into this repo during this cleanup.**

Confirmed by reading (not running) the following files in that project:

- [`instagram/post_to_instagram.py`](../samsin-pricing-demo/instagram/post_to_instagram.py) —
  two-step Graph API publish: `POST /{ig_user_id}/media` (creates a
  container from a public `image_url` + caption) then
  `POST /{ig_user_id}/media_publish` (publishes it), with a small bounded
  retry around container creation for observed host-side flakiness.
  Hardcoded Graph API base: `https://graph.instagram.com/v21.0`.
- [`hosting/upload_image.py`](../samsin-pricing-demo/hosting/upload_image.py) —
  uploads a local image to imgbb (`api.imgbb.com/1/upload`) to get the
  public `image_url` Instagram's Graph API requires (it fetches the image
  itself; there's no binary-upload path for feed posts). 1-day expiry —
  intentional, since Meta re-hosts its own copy at publish time and the
  imgbb copy only needs to survive the few seconds between the two calls.
- `config/settings.py` and `PROJECT_STATUS.md` — confirm credentials are
  referenced (not hardcoded) via environment variables `IG_USER_ID`,
  `IG_LONG_LIVED_TOKEN` (or `IG_SHORT_LIVED_TOKEN`), and `IMGBB_API_KEY`,
  and that `PROJECT_STATUS.md` records multiple real, successful posts
  already made to a burner account, `test.account4289`.

**Facts worth carrying into a future integration:**

- Instagram's standard image-publishing flow *requires* a publicly
  reachable `image_url` — it does not accept a local file or binary
  upload for this endpoint.
- The existing imgbb handoff in that sandbox already satisfies that
  requirement and is proven working (real posts went live with it).
- **Reuse that sandbox rather than rebuilding it** when a future milestone
  needs to publish anything — the two-step container/publish flow, the
  retry-on-flakiness behavior, and the imgbb handoff are already
  correct and live-tested.
- Its Graph API version is hardcoded to `v21.0`, and it uses an existing
  long/short-lived token — **both must be revalidated** (version still
  current, token not expired/revoked) before that integration begins;
  neither was checked as part of this cleanup.
- No credentials were copied, and the old project's `.env` was not opened,
  read, or printed at any point.

## What remains for Sequence C — superseded naming, see below

*(At the time this was written, "Sequence C" meant a future deterministic
audit of whether advertisements can be matched to organic posts. The next
milestone actually built and named "Sequence C" was something else instead
— Neon persistence of paid ads. See the "Sequence C — Neon Persistence"
section below for what Sequence C actually is now. The ads↔organic-post
matching audit described here is still unbuilt and unscheduled; it simply
no longer has a sequence letter reserved for it.)*

Deterministic audit of whether advertisements can be matched to organic
posts using stable IDs, explicit URLs, or exact creative evidence. Not
started, not scoped further than that one sentence, per the original brief.

---

# Sequence C — Neon Persistence

## Milestone completed

`Sequence A paid-ad fetch → normalize → persist/upsert into Neon
PostgreSQL (`competitor_ads`, keyed by `ad_id`) → identify newly
discovered ads → return them for a future (not-yet-built) analysis step.`
This is the persistent "active competitive memory." No AI analysis,
weighting, matching, generation, scheduling, or Instagram publishing was
added — all explicitly deferred per the brief.

## Starting point

Read `README.md` and this entire file, inspected every source/test file,
ran `git status` (clean, `HEAD`/`origin/main` at `9bb184e`) and the full
test suite (45 passed) before changing anything. `psycopg` was not
installed in this environment; installed it locally (`pip install
"psycopg[binary]>=3,<4"`, matching the declared dependency) so the new
tests could actually run — no other environment changes made.

## Files added

```
requirements.txt                            psycopg[binary]>=3,<4 — the
                                             only third-party dependency
                                             in the whole repo
migrations/0001_create_competitor_ads.sql   plain SQL, CREATE TABLE IF
                                             NOT EXISTS, idempotent
src/competitive_memory/
  __init__.py
  db.py             isolated SQL: connect(), upsert_ads() — the only file
                     that knows this is PostgreSQL
  service.py        refresh_competitive_memory() — reuses
                     ad_fetcher.service.fetch_and_normalize() unmodified
  main.py           CLI, same stdout/stderr/exit-code contract as A and B
  migrate.py        applies the migration; `python -m competitive_memory.migrate`
tests/
  test_competitive_memory.py   15 tests, in-memory fake connection/cursor,
                                no live database anywhere
```

## Files changed

```
src/ad_fetcher/service.py   preflight fix - see below
.env.example                added DATABASE_URL= (blank)
tests/test_normalizer.py    +7 tests for the preflight fix
README.md                   Sequence C usage, setup, output shape, Neon
                             account/connection-string instructions;
                             de-hardcoded the stale "28 tests" count
HANDOFF.md                  this section + the superseded-naming note above
```

No files removed. No files in `ad_fetcher/normalizer.py`,
`ad_fetcher/scrapecreators_client.py`, or anything in `organic_fetcher/`
were touched — Sequence B remains exactly as it was, and is not a
prerequisite for Sequence C.

## Required preflight fix (done first, before any database code)

`ad_fetcher.service.fetch_and_normalize()` called `raw.get("results") or
[]` directly, assuming `raw` was always a dict — the same gap
`organic_fetcher.service` already had fixed in the prior cleanup pass.
Fixed identically: reject a non-dict top-level response, and distinguish a
missing/non-list `results` (provider error) from a valid empty `results:
[]` (zero ads, not an error). Sequence A's successful output contract
(`{"count": N, "ads": [...]}`) is byte-for-byte unchanged for every
previously-passing case — confirmed by every pre-existing Sequence A test
still passing, plus the new `test_valid_empty_results_is_not_an_error`
test asserting the exact old shape for the empty case.

## Key implementation decisions

- **Reuse, not duplication**: `competitive_memory.service` imports
  `ad_fetcher.service.fetch_and_normalize` directly — Sequence C does not
  re-fetch or re-normalize anything itself, it only persists what
  Sequence A already produces. `db.py` imports `ad_fetcher.config.load_env`
  for the `.env` parser (one parser, one behavior, reused a third time).
- **`ad_id` is the entire deduplication mechanism** — no separate
  dedup/processed-ad table, matching the brief exactly. One `SELECT ad_id
  ... WHERE ad_id = ANY(%s)` per run determines the insert/update split;
  no per-row existence query (avoids N+1 for the ~20-row batch).
- **One transaction per run**: the existence check, every insert, and
  every update happen inside one `try`/`except psycopg.Error` block,
  committed once at the end or rolled back entirely on any failure — no
  partial persistence is possible, verified by a dedicated rollback test.
- **`COALESCE` does the "don't erase, don't wrongly flip" work in SQL,
  not Python**: `started_at = COALESCE(%(started_at)s, started_at)` and
  `is_active = COALESCE(%(is_active)s, is_active)` mean a `null` in this
  run's fetch (Sequence A already normalizes "provider didn't say" to
  `null`) never overwrites a previously known value — this is also how
  "don't mark absent ads inactive" and "don't erase a real `started_at`"
  end up being the same one-line mechanism, not two.
- **A changed signed media URL never triggers a "new ad"**: the insert/
  update split is based purely on `ad_id` presence, computed *before* any
  row is written. `latest_media_url` is still refreshed on every update
  (so the next stage always has the freshest usable link) — it just never
  causes an ad to reappear in `ready_for_analysis`.
- **No database code in the provider client or normalizer.**
  `scrapecreators_client.py` and `normalizer.py` are untouched by this
  milestone; `db.py` is the only file that imports `psycopg`.
- **Credential safety**: `db.py` never interpolates `str(exc)` from a
  connection failure into a raised message (a libpq connection error can
  embed host/port), and never touches the DSN in the update/insert SQL
  text itself (SQL is static, parameters are passed separately — no
  string-built SQL anywhere in this file).
- **Dependency file choice**: the repo had no `requirements.txt`,
  `pyproject.toml`, or any dependency manifest before this — added the
  simplest one (`requirements.txt`, one line) consistent with a
  stdlib-only project gaining its first-ever dependency. No `pyproject.toml`
  packaging metadata was introduced for one runtime dependency.

## Database schema

One migration, one table, exactly the columns specified in the brief —
[`migrations/0001_create_competitor_ads.sql`](migrations/0001_create_competitor_ads.sql).
`CREATE TABLE IF NOT EXISTS` — safe to run more than once, never drops,
never deletes. Constraints added only where they directly protect the
contract: `media_type IN ('image','video')`, `times_seen >= 1`,
`analysis_status IN ('pending','processing','complete','failed')`. No
weighting columns, no analysis JSON column, no separate duplicate/score/
run-history/competitor/processed-ad tables — all explicitly deferred per
the brief.

## Commands actually run

```
git status                                        → clean, HEAD/origin/main at 9bb184e
python -m unittest discover -s tests -v            → 45 passed (before any change)
pip install "psycopg[binary]>=3,<4"                → installed (dev/test environment only)
python -m unittest discover -s tests -v            → 67 passed (after all changes:
                                                       45 original + 7 preflight-fix
                                                       tests + 15 Sequence C tests)
cd src && python -c "import competitive_memory.db, ...main, ...migrate"
                                                    → all modules import cleanly (syntax/
                                                       import sanity check, no execution)
cd src && python -m competitive_memory.migrate     → exit 1, stderr:
  "error: Missing DATABASE_URL. Set it in .env or the environment before running."
  (real, unmocked - genuinely no DATABASE_URL configured; confirms the
   clear-error path end-to-end without touching a network or database)
```

`python -m competitive_memory.main` was deliberately **not** run for real:
with no `DATABASE_URL` configured, it would still make a real (paid,
credit-charging) ScrapeCreators call before failing at the database step —
spending a credit to prove nothing. The missing-`DATABASE_URL` path is
already fully verified via the migration command above and via unit tests.

## Test results

**67 tests total, all passing** (up from 45 at the start of this
milestone): the original 45, 7 new for the Sequence A preflight fix
(top-level list/string/number/null, missing `results`, non-list `results`,
valid empty `results: []`), and 15 new for Sequence C persistence,
covering every one of the 16 required cases in the brief — the 4 above
plus: missing `DATABASE_URL`; new ad inserted; repeated ad updated not
duplicated; `first_seen_at` preserved; `last_seen_at` changes; `times_seen`
increments exactly once per run (checked across 3 consecutive runs, not
just 2); existing `analysis_status` preserved; a null `started_at` doesn't
erase a real one; a changed signed media URL doesn't trigger rediscovery;
a simulated mid-batch database failure rolls back and leaves zero trace of
the failed batch; two separate credential-leak checks (a connection
failure and a query failure, both confirmed to never contain a
placeholder secret or DSN); and a service-level test confirming
`ready_for_analysis` contains only the truly-new ad from a mixed batch,
using Sequence A's own `media_url` key rather than the database's
`latest_media_url` column name.

The Sequence C tests use a purpose-built in-memory `FakeConnection` that
implements the *exact* semantics of `db.py`'s three fixed SQL statements
(not a generic SQL engine) — buffering writes until a simulated `commit()`
so a simulated failure can prove `rollback()` really discards them. No
live database, no live ScrapeCreators request, no credits, no network
access anywhere in the standard test run.

## Neon verification status: PARTIALLY LIVE-VERIFIED (migration + smoke test yes, full pipeline no)

A real `DATABASE_URL` was provided later in this session (a Neon project
that turned out to already contain one unrelated table, `hermes_runs`, 28
rows — from a different project, the Hermes trading agent, not this repo.
Confirmed with the user before touching it, given the description
("previous rendition") didn't match what was actually found; user
explicitly confirmed dropping it).

**What was actually run against the real database, in order:**

1. Connected and listed tables: found only `hermes_runs` (28 rows) — did
   **not** assume this matched the brief's "previous rendition" framing
   and surfaced the mismatch before acting.
2. On explicit user confirmation: `DROP TABLE IF EXISTS hermes_runs` —
   the **only** destructive statement run this session, against the one
   table confirmed with the user by name.
3. `cd src && python -m competitive_memory.migrate` — real run, exit 0,
   printed `migration applied: competitor_ads table is ready.`
4. Verified via `information_schema` that `competitor_ads` is now the
   **only** table in the database, with all 16 columns, types, nullability,
   and defaults matching the migration file exactly (checked column by
   column, not just "table exists").
5. Real smoke test: inserted `ad_id = '__sequence_c_smoke_test__'`,
   selected it back (confirmed `times_seen=1`, `analysis_status='pending'`,
   `first_seen_at == last_seen_at` — the exact insert-path defaults the
   brief specifies), deleted only that exact row, then confirmed via
   `COUNT(*)` that the table was back to 0 rows. **Migration and smoke
   test are genuinely live-verified**, not fixture-only.
6. Attempted one real end-to-end run: `cd src && python -m
   competitive_memory.main`. **This spent 1 real ScrapeCreators credit**
   (the fetch step runs before the database step) but then failed at
   `db.connect()` with `OperationalError` — the CLI's own error handling
   worked correctly (clear stderr message, exit 1, no credential leaked),
   but **no ads were persisted and no `ready_for_analysis` output was
   produced** for that run.
7. To isolate the cause, ran a bare connection attempt (no ScrapeCreators
   call, no additional credit) immediately after: it succeeded
   (`connected OK`). Every other connection this session (steps 1, 3, 5)
   also succeeded. This strongly suggests step 6's failure was transient
   connection flakiness from this sandbox to Neon (connections in this
   session ranged from ~2 minutes to noticeably longer, never instant),
   **not** a code, schema, or credential defect — but this is an inference
   from consistent evidence, not a confirmed root cause, and it is not the
   same thing as a successful end-to-end run.

**What this means concretely: the full "fetch → persist → report" pipeline
has not yet been successfully demonstrated against the real database in
one run.** Migration and direct SQL operations against Neon are
proven working; `competitive_memory.main`'s happy path is not yet proven
working live, only via the 67 offline tests plus code review.

## Live ScrapeCreators verification status: ATTEMPTED, 1 CREDIT SPENT, RESULT INCONCLUSIVE

One real ScrapeCreators call was made as part of step 6 above. The fetch
itself likely succeeded (Sequence A's own fetch code is unchanged and
separately live-verified in its own milestone) but its result was never
observed, because the process failed at the database step immediately
after and the CLI does not log intermediate fetch results — by design, it
only ever prints the final JSON or an error, never partial state. So: one
credit was spent, but there is no sanitized fetched-ad output to show for
it from this attempt. Sequence A's original live-fetch verification (from
its own milestone) is unaffected by the preflight fix in this milestone.

## Sanitized real output

None available yet — the one real end-to-end attempt (see above) did not
reach the point of producing output. See "Test results" above for the
fixture/fake-verified shape of what a successful run produces, and see the
real, verified smoke-test row values in step 5 above (`times_seen=1`,
`analysis_status='pending'`, `first_seen_at == last_seen_at`) for confirmed
real database behavior on that narrower slice.

## Known limitations

- **The full fetch→persist pipeline is not yet proven end-to-end against
  the real database** — see "Neon verification status" above. This is the
  single most important open item.
- Direct SQL operations (migration, insert, select, delete) against Neon
  are proven working. The `upsert_ads()` INSERT/UPDATE SQL specifically
  has *not* been exercised against real data yet — only the simpler
  smoke-test INSERT was, and only the fake connection has exercised the
  UPDATE statement's exact text.
- Connections to this specific Neon project from this sandbox are slow
  (roughly 2+ minutes each) and were unreliable at least once — a
  production/scheduled caller should expect to need a generous timeout
  and should not assume a single connection attempt will always succeed
  quickly.
- No index beyond the primary key (`ad_id`) was added — not needed at
  ~20 rows per run and no query pattern yet justifies one.
- `hermes_runs` (28 rows, unrelated Hermes trading agent data) was
  permanently deleted from this Neon project this session, with explicit
  user confirmation after the mismatch with the brief's description was
  surfaced. That data is not recoverable from this repo.

## Working tree

Not committed as of the point Neon verification above concluded. Commit
and push happened afterward, once explicitly requested — see the current
`git log`/`git status` for the authoritative state; this file is not
updated retroactively every time something is committed.

## Exact next recommended milestone

Migration and direct-SQL verification against the real Neon database are
done (see "Neon verification status" above). Three items remain:

1. **Get one successful real end-to-end `competitive_memory.main` run.**
   The last attempt spent 1 credit and failed at `db.connect()` with a
   transient-looking error; a bare connection retried successfully right
   after. Next attempt: run `cd src && python -m competitive_memory.main`
   again, expect it may need a generous timeout (observed connections to
   this Neon project ranged from ~2 minutes up), and this time capture the
   actual JSON output. If it fails at the DB step again with the same
   error pattern, that's worth investigating as a real issue rather than
   assuming flakiness a second time.
2. Once step 1 succeeds once, **run it a second time** (only if the extra
   credit cost is acceptable) to confirm idempotent upsert behavior for
   real: `inserted_count: 0` and the same ads reported under
   `updated_count` rather than duplicated rows.
3. **The actual next *build* milestone** (separate from verification):
   design the AI-analysis schema from real Gemini trials against a handful
   of `ready_for_analysis` ads, store it in a new column only after that
   schema is validated (not guessed in advance, per the brief) —
   explicitly not started, not scoped further than that here.

The ads↔organic-post matching audit (previously reserved as "Sequence C"
before this milestone claimed that name) remains a separate, later,
optional option — still just the one sentence describing it, above.

---

# Sequence C — Neon Reliability Fix

## Root cause (confirmed, not just inferred)

`competitive_memory.service.refresh_competitive_memory()` called the paid
`fetch_and_normalize_ads()` **before** `db.connect()` — verified by reading
the code (not assumed): fetch was on the line before connect. This is
exactly what the failed live run exhibited: one ScrapeCreators credit
spent, then a database `OperationalError`. This is now confirmed as the
actual defect, not just a hypothesis — the same code, reordered, produced
a successful real end-to-end run on the very next live attempt (see "Live
Neon verification" below). Whether the *original* `OperationalError` was
itself a one-off Neon cold-start/network blip or something else is still
not separately provable after the fact — but the call-order bug is real,
fixed, and independently worth fixing regardless of what caused that one
failure.

## Files changed

```
src/competitive_memory/service.py   connect() before fetch; owned
                                     connections close on every path
                                     (success, fetch failure, upsert
                                     failure); injected connections are
                                     never closed
src/competitive_memory/db.py        bounded connect() policy: explicit
                                     connect_timeout, retries only
                                     psycopg.OperationalError, max 2
                                     attempts, one ~2s delay
src/ad_fetcher/main.py              generic exception fallback no longer
src/organic_fetcher/main.py         prints str(exc) - class name only
src/competitive_memory/main.py
tests/test_competitive_memory.py    +17 new tests (connect-retry policy,
                                     connection ordering/lifecycle)
tests/test_cli_error_handling.py    new file, 5 tests - all three CLIs'
                                     secret-leak behavior
README.md                           connect-before-fetch behavior,
                                     bounded retry, deps-before-tests note
HANDOFF.md                          this section
```

No files in `ad_fetcher/normalizer.py`, `organic_fetcher/`, or the
migration SQL were touched. No table, column, index, or ORM was added or
changed — the schema is exactly what it was.

## Connection policy (fix 1 + fix 2)

**Call order**, `service.refresh_competitive_memory()`:
`db.connect()` → (only if that succeeds) `fetch_and_normalize_ads()` →
`db.upsert_ads()` → close (if this call owns the connection). A database
preflight failure now means the ScrapeCreators call never happens at all —
verified by a dedicated test (`test_failed_connection_means_fetch_is_never_called`)
asserting the call sequence is exactly `["connect"]`, nothing more, when
`db.connect()` raises.

**Connection lifecycle**: an injected `conn` (tests, or a future caller
that wants to manage its own connection) is never closed by this function
— only a connection this function itself opened is closed, and it's
closed on every exit path: success, a fetch failure, or an upsert failure
(each verified by its own test). No transaction begins until `upsert_ads`
issues its first statement — `connect()` alone runs no SQL, so holding the
connection open (idle) during the small ScrapeCreators HTTP call costs
nothing extra. Exactly one connection is opened per refresh, same as
before.

**Bounded retry**, `db.connect()`: `connect_timeout=17` passed explicitly
to `psycopg.connect()`; on `psycopg.OperationalError` specifically (never
any other exception type), one retry after a fixed 2-second
`time.sleep()`; at most 2 attempts total, never indefinite. A non-connection
error (anything not `psycopg.OperationalError`) propagates immediately,
unretried — verified by `test_non_operational_error_is_not_retried`. The
raised `PersistenceError` names the exception class and attempt count,
never `str(exc)` or the DSN, with `raise ... from ...` preserving the
original as the cause. `migrate.py` needed no changes to benefit from this
— it already calls `db.connect()`, so the same policy applies there
automatically.

## Secret-leak fix (fix 3)

All three CLIs' generic `except Exception as exc:` fallback changed from
`f"error: unexpected failure: {exc}"` to
`f"error: unexpected failure ({exc.__class__.__name__})."` — the exception
class name is kept for debugging, but the raw message (which, for a truly
unexpected exception, could contain anything) is never printed. The
already-sanitized `ScrapeCreatorsError`/`PersistenceError` messages are
unaffected and still print verbatim (they're hand-written to be safe).
Verified with 5 behavioral tests in `tests/test_cli_error_handling.py`
that inject a fake API key and a fake DSN+password into unexpected
exceptions raised by each CLI's top-level call, capture real stderr via
`main()`, and assert the secret string never appears while the exception
class name does.

## Dependency/run-path verification (fix 4)

Interpreter used throughout: `C:\Users\dwish\AppData\Local\Programs\Python\Python312\python.exe`
(Python 3.12.5) — the only Python this session used for install, tests,
migration, and the live run. `pip install -r requirements.txt` succeeds
(already satisfied — `psycopg[binary]` 3.3.4 was installed in a prior
session); `import psycopg` succeeds; no application code was changed to
work around a missing dependency.

## Concurrency (explicitly out of scope, documented not built)

No advisory lock, queue, or "only one runner" mechanism was added. Nothing
in this repair's tests or the real failure pointed to concurrent
scheduled/manual execution as a cause — the failure was a single-run
ordering bug. **Future consideration, not built**: once a 12-hour
scheduler exists, it and any manual `competitive_memory.main` invocation
could in principle race (e.g. two processes both reading "existing IDs"
before either commits, both then inserting the same new `ad_id` and one
losing to the primary-key constraint). Address this when scheduling is
actually implemented — e.g. a Postgres advisory lock (`pg_advisory_lock`)
held for the duration of one refresh — not before, per the brief.

## Tests run and results

```
pip install -r requirements.txt                    → already satisfied
python -c "import psycopg"                          → OK, version 3.3.4
python -m unittest discover -s tests -v              → 67 passed (before any change)
[edits made]
python -m unittest discover -s tests -v              → 84 passed (after all fixes + new tests)
```

**Exact final count: 84 tests, all passing**, run in ~0.1s (no real
`time.sleep` anywhere in the suite — every retry-delay test mocks
`competitive_memory.db.time.sleep`). Breakdown of the 17 new tests: 5 in
`ConnectRetryTests` + 7 in `RefreshConnectionOrderTests` (both in
`test_competitive_memory.py`) + 5 in the new `test_cli_error_handling.py`
= 17; 67 + 17 = 84, matching the test runner's own count exactly.

New regression coverage maps directly to the brief's 13 required cases:
connect-before-fetch ordering, failed-connection-blocks-fetch,
successful-connection-allows-fetch, fetch-failure-closes-owned-connection,
upsert-failure-closes-owned-connection, successful-refresh-closes-owned-
connection, injected-connection-never-closed, explicit connect_timeout
value, first-attempt-fails-second-succeeds, both-attempts-fail, exactly-
one-retry-delay, DSN-never-in-errors (both a connect-failure and a
query-failure variant), and unexpected-CLI-exceptions-never-expose-secrets
(covering all three CLIs plus a check that sanitized errors still print).

## Live Neon verification

**Step 1 — database-only check (zero ScrapeCreators cost): PASSED.**
`cd src && python -m competitive_memory.migrate` → exit 0, "migration
applied: competitor_ads table is ready." Confirmed directly via
`information_schema`: `competitor_ads` is the only table in the database
(no unrelated table touched), all 16 columns present and correctly typed,
row count was 0 at this point. No credentials printed at any point.

**Step 2 — one real end-to-end refresh: PASSED. 1 ScrapeCreators credit
spent.** `cd src && python -m competitive_memory.main` → exit 0, valid
JSON to stdout. This is the first real end-to-end success this project
has had (the previous milestone's attempt is what this repair fixed).

Sanitized result:
- `fetched_count`: 18, `inserted_count`: 18, `updated_count`: 0,
  `ready_for_analysis_count`: 18 (table was empty going in, so everything
  was new — expected, not a bug)
- A few real `ad_id`s from the response: `739393331770098`,
  `2176804236421543`, `1047150261028278` (full IDs are not secrets; media
  URLs are omitted here as they're long signed CDN links, per the brief)
- Post-run database check: row count **18** (matches `inserted_count`
  exactly), distinct `times_seen` across all rows: **`{1}`** (correct -
  every row is a first-time insert), distinct `analysis_status`: **`{'pending'}`**
  (correct default, untouched), and for every sampled row
  `first_seen_at = last_seen_at` evaluated **true** (correct for a
  brand-new insert).

**Step 3 — second-run idempotence: PASSED. 1 additional ScrapeCreators
credit spent (2 total for this repair's live verification), with explicit
user approval given after being told the cost.** This was the first time
the real `UPDATE` SQL in `upsert_ads` had ever run against actual
Postgres — everything before this was either the `INSERT` path (Step 2)
or the fakes.

`cd src && python -m competitive_memory.main` (run again, same 18 ads
still active) → exit 0, sanitized result:
- `fetched_count: 18, inserted_count: 0, updated_count: 18,
  ready_for_analysis_count: 0` — correctly reports zero newly-discovered
  ads on a repeat fetch of the same ads.
- Post-run database check: row count still **18** (no duplication),
  distinct `times_seen` across all rows: **`{2}`** (incremented exactly
  once, from 1), all 18 rows have `last_seen_at` strictly after
  `first_seen_at` (first-seen preserved, last-seen advanced), distinct
  `analysis_status`: still **`{'pending'}`** (preserved, untouched by the
  update). Every real-database claim in "Preserve existing database
  semantics" is now live-verified, not just fake-verified.

## Sanitized output

See "Step 2" above for the real, sanitized summary. Full ad bodies/
headlines are not secrets (they're public ad copy) and were visible in
the real JSON output during verification; media URLs are intentionally
omitted here as they're long, signed, and not useful once expired.

## Remaining limitations

- The original failure's root cause is now understood at the *code* level
  (wrong call order) and fixed, but whether the specific `OperationalError`
  from the earlier session was Neon cold-start, sandbox network flakiness,
  or something else was never independently isolated - it doesn't need to
  be, now that the call order itself is corrected and a real run has
  succeeded, but it's not being claimed as a solved mystery either.
- No advisory lock/concurrency control exists yet - see "Concurrency"
  above; this is a documented future consideration, not a known bug.
- Connections to this Neon project from this sandbox are still slow in
  absolute terms (historically 2+ minutes to establish) even when they
  succeed - the bounded retry protects against *indefinite* hangs and
  wasted credits, it does not make individual attempts fast.

## Working tree

Not committed as of this line being written. Per the brief ("do not
commit or push unless explicitly instructed"), run `git status --porcelain`
for the exact current list rather than trusting a snapshot written here.

---

# Sequence D — Agent-Ready Competitive Intelligence

## Milestone completed

`Fetch current US static ads → normalize and persist them → retain the
fields required for weighting → expose pending ads for future agent
analysis → accept and persist analysis results → produce a ranked,
compact context payload.` No AI model was called anywhere in this
repository - Part 3 is a persistence *boundary* only, for a future
external agent (OpenClaw) to use.

## Competitor change and verification

The brief's `COMPETITOR_NAME`/`META_PAGE_ID` placeholders were unfilled.
Per the brief's own instruction, work stopped before any edit and the user
was asked. The user proposed **PacSun** with two URLs
(`facebook.com/pacsun`, `instagram.com/pacsun`) and explicitly asked for
cross-verification before use, not direct acceptance.

Verified via `GET /v1/facebook/adLibrary/search/companies?query=pacsun`
(1 ScrapeCreators credit): the top result was unambiguously the official
account - `page_id: "7133041750"`, `name: "PacSun"`, `page_alias: "pacsun"`,
**verification: BLUE_VERIFIED**, 2,256,162 Facebook likes, `ig_username:
"pacsun"`, **ig_verification: true**, 2,678,292 Instagram followers -
clearly distinguished from several unrelated/fan-page results also named
"Pacsun"/"Pacsun energies"/"Pacsunme" in the same search. Matches both
URLs the user gave exactly. Locked in as `COMPETITOR = {"name": "PacSun",
"page_id": "7133041750"}` in `ad_fetcher/config.py`, with the verification
evidence documented in a comment there - not just asserted in this file.

## Files added

```
migrations/0002_add_weighting_and_analysis_fields.sql   one ALTER TABLE,
                                                          7 new columns,
                                                          all IF NOT EXISTS
src/competitive_memory/config.py     NEW - active page ID (reused from
                                      ad_fetcher, not duplicated), analysis
                                      batch size, every ranking constant
src/competitive_memory/analysis.py   NEW - list_pending_analysis/
                                      save_analysis/mark_failed, each owns
                                      and closes its own connection
src/competitive_memory/analysis_cli.py  NEW - CLI dispatcher: pending/
                                      save/fail, stdin for the analysis
                                      JSON, same stdout/stderr/exit
                                      contract as every other CLI here
src/competitive_memory/ranking.py    NEW - compute_ranked_context() +
                                      its own CLI main()
tests/test_analysis_and_ranking.py   NEW - 27 tests
tests/fixtures/dpa_ad.json           NEW - explicit DPA-rejection fixture
```

## Files changed

```
src/ad_fetcher/config.py       COMPETITOR -> {name, page_id}; +COUNTRY,
                                +PAID_MEDIA_TYPE; verification comment
src/ad_fetcher/scrapecreators_client.py   fetch_company_ads() now takes
                                page_id/country/media_type, not company_name
src/ad_fetcher/service.py      passes the new params through
src/ad_fetcher/normalizer.py   SUPPORTED_MEDIA drops VIDEO entirely (see
                                "static-image-only" below); +page_id,
                                +collation_id, +collation_count extraction
src/organic_fetcher/config.py  ACCOUNT_HANDLE/BRAND_LABEL -> pacsun/PacSun
                                (identity only - Sequence B's own logic
                                untouched, per the brief)
src/competitive_memory/db.py   INSERT/UPDATE SQL gains page_id/
                                collation_id/collation_count (COALESCE-
                                protected, same pattern as started_at);
                                +list_pending_analysis, +save_analysis_result,
                                +mark_analysis_failed, +list_completed_analyses
src/competitive_memory/migrate.py   now applies every migrations/*.sql
                                file (sorted), not just 0001 - each file
                                is one statement (psycopg3's cursor.execute
                                doesn't support multiple statements per
                                call, so 0002 is one ALTER TABLE with 7
                                ADD COLUMN clauses, not 7 separate statements)
tests/test_normalizer.py       BRAND->PacSun, page_id param throughout,
                                video test repurposed to a rejection test,
                                +collation/page_id assertions, +request-
                                params test, +DPA test, fixed 2 tests whose
                                expectations depended on video being valid
tests/test_competitive_memory.py   make_ad()/FakeConnection extended for
                                page_id/collation_id/collation_count
README.md                      Sequence D section, updated examples,
                                fixed 2 stale claims (no-weighting,
                                company-search-every-run)
HANDOFF.md                     this section
```

No files removed. No table, index, ORM, migration framework, queue, or
background worker was added. `ad_fetcher/scrapecreators_client.py` and
`organic_fetcher/` (beyond the identity constants) are otherwise untouched.

## Static-image-only: how VIDEO rejection actually works now

Rather than adding a new "is this a video, reject it" check, `VIDEO` was
simply removed from `SUPPORTED_MEDIA` (`ad_fetcher/normalizer.py`). A
video ad's `display_format` no longer maps to any `media_type`, so it's
rejected by the *same* "unsupported media type" path DPA already used -
one shared mechanism for DPA, VIDEO, and any future unrecognized format,
not three separate checks. The dead video-URL-extraction branch (multi-
candidate scanning for `video_hd_url`/`video_sd_url`) was deleted along
with it, and the fixture/test that exercised it
(`video_ad_later_candidate.json`) was removed - it tested a code path that
can no longer be reached.

**Two tests that asserted the old contract had to be rewritten, not just
"preserved"**: `test_valid_video_ad` (previously asserted a video ad
normalizes successfully) is now `test_video_rejected_under_static_image_only_contract`,
and `test_filters_and_preserves_order`'s expected output no longer
includes the video ad's ID. This is an intentional, spec-directed change
(the brief explicitly says "the paid-ad output contract is now static-
image-only"), not an accidental regression - flagged here explicitly
rather than silently changed.

## Weighting evidence and competitor scoping (Part 2)

`page_id`, `collation_id`, `collation_count` are extracted defensively
(`None` if missing/wrong-type, never fabricated - a bad `collation_count`
like a bool or a string is treated as absent, same pattern as every other
optional field in this codebase) and persisted via the same COALESCE
pattern already used for `started_at`/`is_active`: a `null` in a later
fetch never erases a previously-known value.

**`page_id` is now the scoping key for every Sequence D query** -
`list_pending_analysis`, `list_completed_analyses`, `save_analysis_result`,
and `mark_analysis_failed` all filter `WHERE page_id = %(page_id)s`. Old
Aelfric Eden rows (inserted before this column existed, so `page_id` is
`NULL` for all of them) are never deleted, but structurally cannot match
any Sequence D query scoped to PacSun's `page_id`. Verified by a dedicated
test (`test_scoped_to_configured_competitor_excludes_old_rows`) and by a
real live check (see "Live verification" below).

## The analysis-persistence boundary (Part 3)

Three functions in `analysis.py`, one CLI dispatcher
(`analysis_cli.py`), each connection owned and closed per call:

- **`list_pending_analysis(limit)`** - configured-competitor, image-only,
  usable-media-URL rows with `analysis_status` `pending` or `failed`
  (retryable, not lost), pending prioritized, oldest first within each
  group. Re-queryable from Neon at any time - not dependent on any
  in-memory list from whatever process originally inserted the rows
  (verified explicitly, not just assumed).
- **`save_analysis(ad_id, result)`** - rejects a non-dict `result`
  (`PersistenceError`, checked before touching the database), rejects an
  `ad_id` that doesn't exist *or* belongs to a different competitor's
  `page_id` (both look identically "unknown" to the caller - no
  cross-competitor leakage), otherwise sets `analysis_status='complete'`,
  stores `result` in the `JSONB` column via `psycopg.types.json.Jsonb`
  (confirmed the correct wrapper attribute - `.obj` - by inspection, not
  assumed), clears any prior `analysis_error`, stamps `analyzed_at`, and
  increments `analysis_attempts`.
- **`mark_failed(ad_id, error_message)`** - same unknown-ad/wrong-competitor
  rejection, sets `analysis_status='failed'`, records `analysis_error`,
  increments `analysis_attempts`, leaves `analyzed_at` untouched (only a
  real success sets that). The row remains visible to
  `list_pending_analysis` afterward - a failed attempt is never
  permanently lost, verified explicitly.

## Deterministic V1 ranking (Part 4)

`weight = 0.5×recency + 0.3×longevity + 0.2×recurrence`, all constants
in `competitive_memory/config.py` (not scattered through `ranking.py`).
Computed fresh on every `compute_ranked_context()` call using the real
current time - no scheduled score-update job exists, matching the brief's
"do not add a daily score-update job."

- **Recency**: `1 - age_days/RECENCY_WINDOW_DAYS`, clamped to `[0,1]`.
  Falls back to `first_seen_at` when `started_at` is missing - documented
  in the module docstring and tested explicitly, not a silent substitution.
- **Longevity**: `(last_seen_at - effective_start).days / LONGEVITY_WINDOW_DAYS`,
  clamped to `[0,1]` - explicitly documented as a proxy for "the advertiser
  is still running it," not proof of profitability.
- **Recurrence**: `collation_count / RECURRENCE_CAP`, clamped to `[0,1]`.
  **`times_seen` is never read by the scoring function at all** - a
  dedicated test (`test_times_seen_is_never_used_for_recurrence`) sets
  `times_seen=999` with no `collation_count` and confirms recurrence still
  scores a neutral `0.0`, not an inflated value.

Only `analysis_status='complete'` rows for the configured `page_id` are
considered; anything scoring below `MIN_WEIGHT_THRESHOLD` is dropped
entirely; the remainder is sorted by weight descending and capped at
`TOP_N`. The payload includes total weight, every component score, ad
identity/copy, the stored `analysis_result`, `snapshot_url`, and
`media_url` - no creative brief is generated (that's OpenClaw's job,
later).

## Tests run and results

```
python -m unittest discover -s tests -v   → 113 passed
  (86 after Part 1's ad_fetcher/organic_fetcher changes,
   27 more added in tests/test_analysis_and_ranking.py for Parts 2-4)
```

Every item in the brief's 17-point regression list is covered: verified
page-ID/US/IMAGE_AND_MEME request params, defensive video/DPA rejection,
new normalization fields (present and missing-evidence cases), existing-
row updates preserving analysis state, pending work surviving independent
of any in-memory list, competitor scoping excluding old rows (for pending
list, save, *and* ranking - three separate tests), successful save,
failure+retry, unknown-ad rejection (including cross-competitor), non-
object-result rejection, deterministic weighting (exact expected-value
assertion, not just "some positive number"), missing dates/collation
fallbacks, threshold/top-N behavior, no credential leakage, and the full
pre-existing insert/update/idempotence suite (unchanged, still passing).

A migration test (`MigrateTests`) confirms `apply_migration()` executes
exactly as many statements as there are files under `migrations/`, that
both the table-creation and the analysis-columns SQL text are present,
and that the connection commits and closes - without touching a real
database.

No live ScrapeCreators request, live Neon mutation, or model call happens
anywhere in the standard test run.

## Live verification

**Correction: 3 ScrapeCreators credits were spent in this Sequence D
session, not 4** (an earlier draft of this section miscounted) - 1 to
verify PacSun's identity (see above), 1 for the real production refresh,
1 diagnostic call that explained the 0-ads result. The analysis/ranking
demo below used zero ScrapeCreators credits - it's pure database work.
(Sequence E adds one more diagnostic credit on top of this - see the
Sequence E section for the running total across both sessions.)

### Neon reset (user-directed, before this verification)

The user asked to reset the Neon table before running the PacSun
verification, so PacSun's data would be visibly reflected rather than
mixed with old rows. Before deleting anything, the table's actual contents
were inspected (not assumed): **all 18 existing rows had `brand =
'Aelfric Eden'`** - exactly the two runs from the Sequence C reliability
fix's live verification, nothing else. Deleted with an exact `WHERE brand
= 'Aelfric Eden'` match (not a wildcard), confirmed 0 rows remaining
afterward. This is the only bulk deletion in this milestone, and it was
explicit, confirmed-before-acting, and scoped to an exact match.

### Step 1 — migration (0 credits): PASSED

`cd src && python -m competitive_memory.migrate` → exit 0, "migration
applied: competitor_ads table is ready." (Ran against the real Neon
project - by this point `0001` was already applied from Sequence C;
`0002`'s `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...` ran cleanly.)

### Step 2 — real production refresh: PASSED, but with a real finding

`cd src && python -m competitive_memory.main` → exit 0, valid JSON:
**`fetched_count: 0, inserted_count: 0, updated_count: 0,
ready_for_analysis_count: 0`.**

This is not a bug. A diagnostic call (`country=ALL, status=ALL,
media_type=ALL`, 1 credit, approved separately after surfacing the 0-ads
result rather than silently re-querying) confirmed:
- `pageId` targeting is correct - every sampled result's `page_id` is
  `"7133041750"`.
- PacSun's real ad mix (30 sampled) is **DCO 15, VIDEO 6, DPA 5, IMAGE
  4** - `DCO` (Dynamic Creative Optimization) is a real Meta ad format
  neither the original brief nor this normalizer accounts for at all; it
  is correctly rejected by the existing "unsupported media type" path
  (same mechanism as DPA/VIDEO), but it means **PacSun is currently
  running almost no plain static-image ads** - only 4 of 30 sampled, and
  the combination of `status=ACTIVE` + `country=US` narrows even that
  small set to zero in the real production request.

**Presented this finding to the user rather than assuming a bug or
silently loosening the locked `COUNTRY`/`PAID_MEDIA_TYPE` config values.**
User's explicit decision: accept it as a real finding about PacSun's
current campaign mix, not a defect - documented here rather than worked
around.

### Step 3 — old-row exclusion: CONFIRMED (moot after the reset)

The old Aelfric Eden rows this check was meant to verify were deleted (see
"Neon reset" above) before this step, at the user's explicit direction -
so there was nothing left to demonstrate exclusion *against* live. The
exclusion mechanism itself (`WHERE page_id = %(page_id)s`) is verified by
`test_scoped_to_configured_competitor_excludes_old_rows` and by three
other scoping tests offline.

### Step 4 — pending → complete → ranked context: PASSED (synthetic row, since 0 real ads exist)

**To be unambiguous: this step never touched a real PacSun ad.** With zero
real PacSun rows to exercise Part 3/4 against, one unmistakable
**synthetic, fabricated** row was inserted directly (`ad_id =
'__sequence_d_smoke_test__'`, `page_id` = the real configured PacSun page
ID, `media_type='image'`, `collation_count=3`, `started_at` = 5 days ago,
all made up for this test) - the same "exact unmistakable ID, exact-match
cleanup" pattern already established for Sequence C's smoke test. The
ranking arithmetic and database mechanics are genuinely verified; the
underlying ad, its copy, and its "analysis" are not real PacSun data.
Since this row was entirely artificial (no genuine analysis existed to
overwrite), it was **deleted** afterward rather than reset to `pending` -
the brief's "restore to pending ... do not overwrite genuine analysis"
instruction's spirit, applied to the case where there's nothing genuine to
restore to.

```
list_pending_analysis()  → ['__sequence_d_smoke_test__']
save_analysis(ad_id, {"headline_quality": "test", "score": 0.9})  → succeeded
compute_ranked_context() → {
  "ad_id": "__sequence_d_smoke_test__",
  "weight": 0.5616,
  "component_scores": {"recency": 0.8333, "longevity": 0.0833, "recurrence": 0.6},
  "analysis_result": {"score": 0.9, "headline_quality": "test"}
}
```

Hand-verified the arithmetic: `recency = 1 - 5/30 = 0.8333`;
`longevity = 5/60 = 0.0833` (last_seen_at defaulted to insert time, ~5
days after the synthetic started_at); `recurrence = 3/5 = 0.6`
(`collation_count=3`, `RECURRENCE_CAP=5`); `weight = 0.5×0.8333 +
0.3×0.0833 + 0.2×0.6 = 0.5616` - matches the real computed output exactly.
Row deleted afterward; table confirmed back to 0 rows.

### Summary

| Check | Result |
|---|---|
| Migration applies cleanly to real Neon | ✅ |
| Verified `pageId` correctly targets PacSun | ✅ |
| Static-image-only contract holds under real, messier data (DCO discovered) | ✅ |
| Old-competitor row exclusion | ✅ (offline-verified; moot live after user-directed reset) |
| Pending → save → ranked context, real database, real arithmetic | ✅ (synthetic row, cleaned up) |
| Real PacSun static image ads currently in Neon | **0** (real finding, not a defect) |

## Known limitations

- **PacSun currently has ~0 active US static-image ads to persist.** Their
  real ad mix (30 sampled) is dominated by `DCO` (Dynamic Creative
  Optimization, 15/30) and `VIDEO` (6/30) - a real, live-confirmed fact
  about this specific competitor right now, not a defect. `competitor_ads`
  is correctly empty as of this write-up. If/when PacSun runs static image
  ads again, or when a competitor with more static-image inventory is
  chosen, the exact same code should populate rows without any change -
  this was never tested against a real non-empty PacSun batch, though.
- `DCO` is a real Meta ad format observed live that neither the original
  brief nor this normalizer's `SUPPORTED_MEDIA` mapping names explicitly -
  it's correctly rejected via the same "unsupported media type" path as
  DPA/VIDEO (no separate handling needed), but if static-image coverage
  is ever needed from a DCO-heavy advertiser, DCO's creative would need
  its own extraction logic - not built, not scoped into Sequence D.
- Sequence B was not re-run live under the new PacSun identity this
  session - only its two identity constants were changed, and its own
  logic/tests are unaffected (they use their own local test constants,
  not `config.ACCOUNT_HANDLE`), per the brief scoping Sequence B change to
  "identity only."
- `collation_count`'s real-world range hasn't been observed against a real
  PacSun *static-image* ad (the live ranking demo above used a synthetic
  row) - `RECURRENCE_CAP=5` in config.py is a reasonable starting guess,
  not calibrated against real PacSun data yet.
- The ranking weights (0.5/0.3/0.2) and windows (30/60 days) are the
  brief's agreed V1 proxy structure, not independently re-derived or
  tuned here - flagged as a "V1" deliberately.
- No advisory lock/concurrency control exists for the eventual scheduler
  (carried over from the Sequence C reliability fix's same documented,
  intentionally-deferred limitation) - still not needed since nothing
  runs on a schedule yet.

## Working tree (Sequence D)

Committed and pushed - see the top-level "Current status" note and run
`git log`/`git status` for the exact current authoritative state rather
than trusting a specific commit hash written here.

## Exact next milestone (superseded — Sequence E is now built, see below)

*(This section described Sequence E as a future milestone at the time it
was written. Sequence E has since been implemented and live-verified —
see the "Sequence E" section at the very bottom of this file. Kept here
for history.)*

Per the brief:

```
Sequence E:
Samsin product references
→ image-generation tool
→ two candidates
→ visual QA
→ one retry
→ ImgBB
→ manual Instagram publication
```

OpenClaw skills, orchestration, and 12-hour scheduling remain the final
sequence after the external tools (image generation, ImgBB, Instagram
publishing) are proven independently - not started, not scoped further
than that here.

---

# Sequence E — Creative Generation and Manual Publishing

## Milestone completed

`Samsin product references → Gemini image-generation tool → two
candidates → human visual selection (no autonomous critic) → one optional
retry → ImgBB → manual Instagram publication.` **A real post is now
live**: see "Live verification" below.

## Part 1 — PacSun diagnostic (per the brief, at most one call)

One diagnostic ScrapeCreators request: `pageId=7133041750, country=US,
status=ALL, media_type=IMAGE_AND_MEME, start_date=<60 days ago>`.
**1 credit spent.** Result: **30 raw results, `DCO: 25, DPA: 5` — zero
IMAGE/MEME results even under this much wider window.** This confirms
Sequence D's earlier `status=ACTIVE`-only finding wasn't an artifact of
that narrower filter - PacSun genuinely has no static creative inventory
in its Ad Library right now, regardless of active/inactive status or how
far back the window goes.

**Per the brief's explicit instruction**: production config was **not**
changed (still `status=ACTIVE`, no `start_date` param), and DCO support
was **not** built under this deadline. **Reporting: PacSun should be
replaced as the configured competitor** for Sequence A/C/D to produce any
real ad rows going forward. This is a recommendation for a future session,
not something this milestone acted on.

## Files added

```
src/samsin_reference/               NEW package - Part 2
  __init__.py, config.py, client.py, catalog.py, service.py, main.py
src/creative_generation/            NEW package - Part 3
  __init__.py, config.py, gemini_client.py, image_checks.py,
  generator.py, main.py
src/manual_publishing/              NEW package - Part 4
  __init__.py, config.py, imgbb_client.py, instagram_client.py,
  publisher.py, main.py
tests/fixtures_samsin/              products_list.json, detail_star.json,
                                     detail_camo.json
tests/test_samsin_reference.py      11 tests
tests/test_creative_generation.py   15 tests
tests/test_manual_publishing.py     16 tests
creative_brief.json                 example input, kept in repo root
star_product.json                   example input (one real product
                                     record from the live fetch), kept in
                                     repo root
```

## Files changed

```
requirements.txt      +Pillow>=10,<13 - see "A real Gemini bug" below for why
.env.example           +GEMINI_API_KEY, GEMINI_MODEL, GEMINI_API_BASE,
                        +IMGBB_API_KEY, IG_USER_ID, IG_LONG_LIVED_TOKEN,
                        IG_SHORT_LIVED_TOKEN, IG_GRAPH_API_VERSION
.gitignore              +generated_creatives/, +.manual_publish_state.json
README.md               Sequence E section, setup steps, dependency count
HANDOFF.md              this section + corrections listed below
```

No files in `ad_fetcher/`, `organic_fetcher/`, or `competitive_memory/`
were touched by Sequence E itself (only by the Part 1 diagnostic, which
changed no code - see above). No files from the old samsin-pricing-demo
project were read, imported, or copied at any point.

## HANDOFF corrections made this session (per the brief's explicit list)

1. **"Aelfric rows still exist" was wrong** - they were deleted (18 rows,
   exact `brand = 'Aelfric Eden'` match) during Sequence D's live
   verification. Corrected in the "Current status" block and in the
   Sequence D section's own text.
2. **Credit-total reconciliation** - Sequence D's live-verification section
   claimed "4 ScrapeCreators credits" but only ever itemized 3. Corrected
   to state 3 explicitly, with a forward pointer to this session's
   additional 1 (Part 1's diagnostic) for a combined running total of 4
   across both sessions.
3. **Ranking smoke test synthetic-row clarity** - the Sequence D "Step 4"
   section now states explicitly, in its own sentence, that the ranking
   demo used a synthetic/fabricated row, never a genuine PacSun ad.

## Part 2 — Samsin reference fetcher: real-schema discoveries

Live-checked against `shopsamsin.com` before writing any normalization
code (not guessed):

- **`/products.json`'s per-variant `available` field is absent entirely**
  on this store (confirmed: every variant of every product returns no
  `available` key at all via that endpoint). The storefront AJAX endpoint
  `/products/<handle>.js` **does** return a real, reliable `available`
  (confirmed against a genuinely out-of-stock product, `camo-t-shirt`,
  and 6 genuinely in-stock ones) - used instead for stock status, while
  `/products.json` is still used for image alt-text (needed for the
  garment/model classification heuristic).
- **No model/on-body photography exists anywhere in Samsin's live public
  catalog.** Checked all 31 products' image filenames/alt-text and the
  homepage - confirmed zero matches for any model/lifestyle keyword.
  `model_image_urls` is `[]` for every real product as of this session -
  not a heuristic failure, an accurate reflection of what's actually
  there. The classification heuristic itself (alt-text keyword match,
  `samsin_reference/config.py`) is implemented and tested but has never
  had a real positive match to validate against.

## Part 3 — Gemini tool: two real problems found and fixed live

1. **A real Gemini quota/billing issue, not a code bug.** The first
   verification attempt returned HTTP 429 with `limit: 0` for
   `generate_content_free_tier_requests` on `gemini-2.5-flash-preview-image`
   - the associated Google Cloud/AI Studio project had no billing enabled,
   and the Gemini API's free tier allocates zero quota to image-generation
   models. Not resolved by this session's code - the user updated the
   `GEMINI_API_KEY` to one with billing enabled, which then worked
   immediately with no code change.
2. **A real dimension bug, not a code bug on our side either, but one we
   had to work around.** The exact same request that specifies "Output a
   single portrait image, exactly 1080x1350 pixels" in the prompt text
   returned a real `1024x1024` image both times, live, from
   `gemini-2.5-flash-image`. Gemini does not reliably honor an exact pixel
   size requested via prompt text alone. **Fixed by adding Pillow**
   (`generator._cover_resize`) as a deterministic (non-AI) resize +
   center-crop step applied to every candidate before the deterministic
   checks run - guarantees the exact contracted dimensions regardless of
   what size the model natively returns. `image_checks.py` was also
   simplified to use Pillow for reading dimensions/format instead of a
   hand-rolled PNG/JPEG header parser, since Pillow was now a real
   dependency anyway.
3. **A real creative-quality miss that deterministic checks correctly did
   not catch, because they were never supposed to.** The first live
   generation attempt, using a conservative brief ("preserve exact
   design... clean studio background"), produced an image that was
   "technically a valid 1080x1350 PNG" but was, in the user's own words,
   "practically just the T-shirt picture from the site itself" - a
   near-exact reproduction of the flat garment reference, not an
   advertisement. This is exactly the division of labor the brief
   specifies: deterministic checks (format/dimensions) passed correctly;
   only a human looking at the actual image caught the real problem. Fixed
   by rewriting `creative_brief.json` with much more directive creative
   instructions (styled flat-lay with streetwear props - sneakers, cap,
   sunglasses, skateboard - textured background, dynamic angled lighting)
   and re-running `generate` (not `retry`, since retry deliberately reuses
   the exact same prompt - a genuinely different creative direction needed
   a fresh `generate` call). The second attempt was accepted by the user.

## Tests run and results

```
python -m unittest discover -s tests -v   → 155 passed
  (113 before Sequence E + 11 samsin_reference + 15 creative_generation
   + 16 manual_publishing = 155)
```

Every item in the brief's testing list is covered: mocked network calls
throughout (no live ScrapeCreators/Gemini/ImgBB/Instagram call in the
standard suite), including missing-key/credential-leak tests for all three
new provider clients, the deterministic image-dimension/format checks
(using real Pillow-generated PNG/JPEG bytes, not fakes), the resize step
normalizing an off-size model output to the exact target dimensions, the
cooldown state machine (blocks a second real publish within 180s, allows
one after it elapses, dry runs never touch it), bounded container-readiness
polling (never indefinite), and dry-run vs. `--publish` CLI wiring.

## Live verification (full batch, as approved)

**Approved batch**: 0 additional ScrapeCreators credits (Samsin fetch is a
public website), 2 Gemini generations, up to 1 optional retry, 1 ImgBB
upload, 1 real Instagram post. **Actual: 4 Gemini generations were used**
(2 initial + 2 on a second `generate` call after the creative-quality
rejection above - not technically the pre-approved "1 optional retry"
since it was a fresh `generate`, not `retry`; disclosed here rather than
glossed over as within-scope).

1. **Samsin fetch**: real, live, 0 credits. 7 T-shirts found; `camo-t-shirt`
   correctly out of stock, 6 others correctly in stock. **STAR T-SHIRT
   WHITE** selected (in stock, $38.90, 5 garment images, 0 model images).
2. **First Gemini generation** (2 candidates): both passed deterministic
   checks (1080x1350 PNG) but were creatively rejected by the user (see
   Part 3, problem 3, above).
3. **Second Gemini generation** (2 candidates, stronger brief): both
   passed deterministic checks and were creatively accepted. User selected
   candidate 2 (tighter crop, props at the frame edges).
4. **ImgBB upload**: real, succeeded - `https://i.ibb.co/3Y5xKDnj/a5dec31daf4f.png`.
5. **Dry-run publish**: real ImgBB upload + real Instagram container
   creation + real readiness poll, stopped before the publish call, as
   designed. Confirmed the whole pipeline works before the irreversible step.
6. **Real publish**: succeeded. **`media_id: 18386960494162488`.**
7. **Confirmed live** via a read-only Graph API GET on that media id:
   `permalink: https://www.instagram.com/p/DcZEKJ-HL2J/`, `media_type:
   IMAGE`, `caption: "New in: the Star Tee. Available now at
   shopsamsin.com."` (caption matches the creative brief exactly, no
   invented offer).

### Sanitized sample payloads

Real `samsin_reference` output (one product, truncated image list):
```json
{
  "title": "STAR T-SHIRT WHITE", "handle": "star-t-shirt-radiostar",
  "product_url": "https://shopsamsin.com/products/star-t-shirt-radiostar",
  "price": 38.9, "currency": "USD", "in_stock": true,
  "model_image_urls": []
}
```

Real `manual_publishing` output (the actual real-publish result):
```json
{
  "dry_run": false,
  "image_url": "https://i.ibb.co/3Y5xKDnj/a5dec31daf4f.png",
  "creation_id": "18094062641122080",
  "published": true,
  "media_id": "18386960494162488"
}
```

## Known limitations

- **PacSun has no usable static ad inventory right now** - see Part 1
  above. Recommend replacing the configured competitor before the next
  Sequence A/C/D live run is expected to produce real rows.
- **The garment/model image classification heuristic is untested against
  a real positive match** - Samsin's catalog has no model photography at
  all right now, so `model_image_urls` has only ever been observed as `[]`
  live. Covered by fixture tests only for the positive case.
- **The published creative used no model/on-body reference** - by explicit
  user decision, given none exists. If Samsin's catalog gains model
  photography later, `--model-reference` is already wired through the
  CLI/generator and only needs a real URL/path.
- **`competitor_inspiration` was empty in the real creative brief** -
  Sequence D's ranked context table has 0 completed analyses right now (no
  real PacSun ads exist to analyze), so there was no real competitor
  signal to feed into the prompt. This is a direct downstream consequence
  of the Part 1 finding, not a Sequence E defect.
- **The exact Gemini model name (`gemini-2.5-flash-image`) is a
  best-guess default**, confirmed to work live with a billing-enabled key,
  but not independently cross-checked against Google's current model
  catalog/naming - `GEMINI_MODEL` is env-overridable specifically because
  of this uncertainty.
- **One real Instagram post now exists permanently on `test.account4289`**
  (unless manually deleted later) - `media_id 18386960494162488`. Not
  something this milestone can or should undo automatically.
- The 180-second real-publish cooldown was implemented and unit-tested
  but was only exercised live once (a single real publish) - the "blocked
  within cooldown" path was not exercised against the real API this
  session (would require a second real post, not requested).

## Working tree (Sequence E)

Not committed as of this section being written - see "Current status" at
the top of this file and run `git status --porcelain` for the exact
current list.

## What OpenClaw must orchestrate next (Sequence F)

Per the brief, Sequence F is: OpenClaw skills, orchestration, and 12-hour
scheduling - not started, not scoped further here. Concretely, based on
everything built so far, OpenClaw's job will be to:

1. Call `competitive_memory.main` (Sequence C) on a schedule.
2. Call `competitive_memory.analysis_cli pending` (Sequence D) to get
   real work, perform the actual multimodal semantic analysis this
   repository deliberately does not do, and write results back via
   `analysis_cli save`/`fail`.
3. Call `competitive_memory.ranking` (Sequence D) to get the ranked
   context, and convert it into an actual creative brief (`tone`, `notes`,
   `competitor_inspiration`, `caption`) - something no code in this
   repository does; Sequence E only *consumes* a creative brief, it never
   authors one.
4. Call `samsin_reference.main` (Sequence E) to pick a real product.
5. Call `creative_generation.main generate` (Sequence E), perform the
   *semantic* visual QA this repository explicitly does not do (only
   deterministic format/dimension checks exist here), and decide whether
   to `retry`.
6. Call `manual_publishing.main --publish` (Sequence E) - or, for a
   scheduled/autonomous flow, decide whether "manual" review should be
   replaced with an automated approval gate, which is an explicit
   OpenClaw-layer design decision, not something pre-decided here.
7. Own the advisory-locking/concurrency question flagged in the Sequence C
   reliability fix - once a schedule exists, OpenClaw is the natural place
   to serialize scheduled vs. manual runs.

**(superseded)** This used to say "before any of that, replace PacSun" -
that's now done, see "Competitor Replacement — PacSun → Billionaire Boys
Club Icecream" below. Steps 1-7 above are otherwise still accurate and
still not built.

---

# Competitor Replacement — PacSun → Billionaire Boys Club Icecream

## Why

PacSun was confirmed twice, live, across two separate sessions (Sequence
D's original live verification, then Sequence E Part 1's wider-window
diagnostic) to have essentially zero usable static image/meme ads in its
Meta Ad Library - 100% Dynamic Creative Optimization and video, even with
`status=ALL` and a 60-day window. Every downstream sequence (C/D) had
nothing real to persist or analyze. Per explicit instruction, no DCO/DPA
support was built to work around this - the competitor itself was
replaced instead.

## New competitor

- Name: **Billionaire Boys Club Icecream**
- Meta page ID: `142427132456114`
- Instagram handle: `bbcicecream`
- Verified via a live diagnostic fetch this session: 16 usable active US
  static-image ads (see "Live verification" below) - well above any
  reasonable usability bar, unlike PacSun's 0.

## Files changed (smallest consistent diff, no architecture change)

```
src/ad_fetcher/config.py         COMPETITOR dict (name, page_id), BRAND_LABEL,
                                  docstring updated with the replacement rationale
src/organic_fetcher/config.py    ACCOUNT_HANDLE, BRAND_LABEL, docstring updated -
                                  flags that the new handle is not yet
                                  independently re-verified via company-search
README.md                        competitor description + setup note updated
HANDOFF.md                       this section, plus the "Current status" note
                                  at the top
```

**Nothing else needed to change.** `competitive_memory/config.py`'s
`ACTIVE_PAGE_ID = COMPETITOR["page_id"]` already derives from
`ad_fetcher.config.COMPETITOR`, and every query in `competitive_memory/db.py`,
`analysis.py`, and `ranking.py` scopes by that one value - the scoping
design from Sequence D did exactly what it was meant to do here: a
one-competitor swap touched two config files, not the persistence or
ranking logic. No DCO/DPA support, no multi-competitor registry, no new
tables, no schema change.

## Offline tests

`python -m unittest discover -s tests -v` → **155 passed, 0 failed**,
unchanged from before this swap. No test needed updating - the
`competitive_memory`/`ranking` test suites use their own local fixture
constants (e.g. `BRAND = "PacSun"`, `PAGE_ID = "7133041744"`-style
literals in `test_competitive_memory.py` uses `PAGE_ID = "7133041750"`)
to exercise the generic persistence/ranking contract, not the real
configured competitor - so they're correctly unaffected by an identity
change. `test_analysis_and_ranking.py` reads `config.ACTIVE_PAGE_ID`
directly for its own fixture rows, so it would have picked up the new
value automatically either way.

## Live verification

One real `python -m competitive_memory.main` run (cwd `src/`), spending
**1 ScrapeCreators credit**:

```json
{
  "fetched_count": 16,
  "inserted_count": 16,
  "updated_count": 0,
  "ready_for_analysis_count": 16
}
```

All 16 are real `IMAGE`-format ads for Billionaire Boys Club Icecream
(bodies like `"ICECREAM Fall '26 now available."` and `"Billionaire Boys
Club Summer '26 now available."`), `is_active: true`, `started_at`
ranging June-August 2026. Confirmed directly in Neon via `information_schema`-
backed queries (not just trusting the CLI's own report):

- `SELECT COUNT(*), COUNT(DISTINCT page_id) FROM competitor_ads` → `(16, 1)`
- `SELECT page_id, COUNT(*) ... GROUP BY page_id` → `[('142427132456114', 16)]`
- Spot-checked 5 rows: all `media_type = 'image'`, all with a non-empty
  `latest_media_url`, all `analysis_status = 'pending'`.

### Analysis-persistence + ranking smoke test (genuine ad this time, not synthetic)

Unlike Sequence D's original ranking smoke test (which used a fabricated
row because 0 real ads existed at the time), this session had 16 genuine
pending ads to pick from. Selected `ad_id = 2360284104778799` (real ad:
`"Billionaire Boys Club Summer '26 now available."`, `started_at
2026-07-02`).

Saved an **explicitly artificial** test analysis via `analysis_cli save`:

```json
{
  "__synthetic_test_analysis__": true,
  "note": "artificial test payload written by an operator to smoke-test the analysis-persistence boundary and ranking - not a genuine AI analysis of this ad",
  "sentiment": "n/a",
  "test_marker": true
}
```

Real ranked-context payload from `competitive_memory.ranking` (real
arithmetic, against the real database, over a real ad - only the
*analysis content* is synthetic):

```json
{
  "count": 1,
  "context": [
    {
      "ad_id": "2360284104778799",
      "brand": "Billionaire Boys Club Icecream",
      "body": "Billionaire Boys Club Summer '26 now available.",
      "headline": "Billionaire Boys Club Summer '26",
      "cta": "Shop now",
      "media_type": "image",
      "snapshot_url": "https://www.facebook.com/ads/library/?id=2360284104778799",
      "analysis_result": {
        "note": "artificial test payload written by an operator to smoke-test the analysis-persistence boundary and ranking - not a genuine AI analysis of this ad",
        "sentiment": "n/a",
        "test_marker": true,
        "__synthetic_test_analysis__": true
      },
      "weight": 0.2624,
      "component_scores": { "recency": 0.0, "longevity": 0.8746, "recurrence": 0.0 }
    }
  ]
}
```

(`media_url` truncated here for brevity - present and real in the actual
output.) `recency = 0.0` because the ad's `started_at` (2026-07-02) is
outside the 30-day `RECENCY_WINDOW_DAYS`; `longevity = 0.8746` because
it's been observed continuously since `first_seen_at`; `recurrence = 0.0`
because `collation_count` is `null` (ScrapeCreators didn't return
collation evidence for this ad) - all consistent with `ranking.py`'s
documented proxy semantics, not a bug.

**Cleanup**: manually reset that row afterward via a direct `UPDATE
competitor_ads SET analysis_status='pending', analysis_result=NULL,
analysis_attempts=0, analysis_error=NULL, analyzed_at=NULL WHERE ad_id=...`,
then confirmed via a `SELECT` that the row is back to `('2360284104778799',
'pending', None, 0, None)`. **No fake analysis remains in the database.**

## Credits spent this session

1 ScrapeCreators credit (the one `competitive_memory.main` run above). No
Gemini, ImgBB, or Instagram calls were made - explicitly out of scope for
this milestone.

## Known limitations / remaining work

- The Instagram handle `bbcicecream` was **not** independently
  re-verified via ScrapeCreators' company-search endpoint this session
  (unlike PacSun's original page_id, which was cross-checked against
  `facebook.com/pacsun` / `instagram.com/pacsun`) - it was taken directly
  from the brief. Sequence B (`organic_fetcher`) was not re-run live to
  confirm the handle resolves to real posts.
- Sequence D's other ranking constants (`RECENCY_WINDOW_DAYS`,
  `LONGEVITY_WINDOW_DAYS`, `RECURRENCE_CAP`, weights) were not
  re-evaluated for this new competitor's posting cadence - they're
  unchanged from Sequence D's PacSun-era tuning and may not be ideal here,
  but that's a tuning question, not a defect, and out of scope for this
  milestone.
- The other 15 real pending ads are untouched (still genuinely `pending`)
  - ready for a real analysis step (Sequence F/OpenClaw) whenever that's
    built.
- Gemini/ImgBB/Instagram (Sequence E's pipeline) and OpenClaw (Sequence F)
  are both unaffected by this swap and remain exactly as documented in
  their own sections above.

## Git status

Committed and pushed once verification above succeeded - see `git log`/
`git status` for the authoritative current state.

---

# Sequence F — OpenClaw Orchestration: Environment Setup (in progress)

## Status: environment/model verified, orchestration skill NOT built yet

This section covers only the OpenClaw/OpenCode tooling verification and
model configuration required before any Sequence F skill/cron code could
be written. **No skill files, run-lock, logs, resumable state, or tests
have been added to this repo yet** - that is the next step, not done
here. Nothing in `samsin-ad-intelligence` changed as part of this section
except this documentation; all the work below happened in the local
machine's OpenClaw config (`~/.openclaw/openclaw.json`), outside any git
repo.

## What was inspected (per the brief: no guessing at commands/formats)

- **OpenClaw**: already installed globally via npm, `2026.7.1-2 (0790d9f)`.
  Real supported command surfaces inspected directly (`--help` on `skills`,
  `cron`, `config`, `models`, `daemon`) before any config was touched -
  confirmed OpenClaw has its own native `cron` subcommand (add/enable/
  disable/list/run/runs/status), so the brief's "do not use a second
  scheduler unless OpenClaw lacks one" is satisfied by using it directly.
  `openclaw skills list/install/info` confirmed as the real skill-file
  mechanism (not guessed).
- **OpenCode**: not installed or referenced anywhere on this machine at
  the start of this session (not on PATH, not in global npm, no
  "opencode" model in OpenClaw's catalog). Per the brief's explicit stop
  condition, this was reported as a blocker and **not** worked around
  with a fake substitute. Installed properly once authorized: `npm i -g
  opencode-ai` (same trusted npm registry as `openclaw` itself, not a
  piped shell-install script), then its own `postinstall.mjs` (read
  first, confirmed it only fetches the platform-specific binary
  sub-package from npm - no curl-to-shell) was run manually since
  `--allow-scripts` had blocked it automatically. Verified working:
  `opencode --version` -> `1.18.21`.

## OpenCode Go vs OpenCode Zen (real distinction, not interchangeable)

Read directly from `opencode.ai/docs/zen` and `opencode.ai/docs/go`
before configuring anything:

- **Zen** is OpenCode's pay-as-you-go model gateway (any model, billed
  per request).
- **Go** is a separate, cheaper flat subscription ($5 first month, then
  $10/month) scoped to a curated list of open coding models, with its
  own endpoint namespace (`https://opencode.ai/zen/go/v1/...`, model ids
  of the form `opencode-go/<model-id>`) and its own usage limits (5hr/
  weekly/monthly dollar caps).

The user explicitly needed **Go**, not Zen - confirmed before wiring
anything, since the two use different endpoints/ids and would silently
misroute if confused.

## Model configured: `opencode-go/deepseek-v4-flash-vision-exp`

Chosen because Sequence F's Part 7 (selecting the better Gemini candidate
using model vision) needs a vision-capable reasoning model, and this is
the vision-capable member of the Go model family per OpenCode's own docs
(`DeepSeek V4 Flash Vision Exp`, billed with image tokens per their
pricing page).

**Two real, live-discovered config bugs found and fixed** (not guessed -
found via actual error output each time):

1. Setting `agents.defaults.model.primary` to the new model id alone was
   not enough - OpenClaw errored with `Unknown model: ... Found
   agents.defaults.models[...], but no matching
   models.providers["opencode-go"].models[] entry`. Fixed by adding an
   explicit `models.providers.opencode-go.models[]` catalog entry
   (`id`, `name`, `input: ["text","image"]`) matching the exact schema
   from `openclaw config schema`.
2. Once that catalog entry existed but without an explicit `api`/
   `baseUrl`, real requests silently routed to `https://api.openai.com/v1/responses`
   (a live 401 - wrong provider entirely, not an auth problem).
   Root-caused via the actual `model-fetch` debug line in the error
   output, not assumed. Fixed by setting
   `models.providers.opencode-go.api: "openai-completions"` and
   `.baseUrl: "https://opencode.ai/zen/go/v1"` explicitly, matching
   OpenCode Go's documented `/v1/chat/completions` endpoint shape.

Auth itself needed no new wiring - the user's own prior `openclaw
onboard`/`configure` session had already stored a real OpenCode Go key in
OpenClaw's native auth-profile store (`auth.profiles["opencode-go:default"]`,
backed by `~/.openclaw/agents/main/agent/openclaw-agent.sqlite`, not a
plaintext config field). No key was ever printed or committed anywhere;
an `OPENCODE_API_KEY` env var was also set as a Windows user env var
during initial troubleshooting but turned out to be unused once the
existing auth profile was confirmed sufficient - left in place, harmless,
not referenced by any committed config.

Config changes were applied by editing `~/.openclaw/openclaw.json`
directly (not via the `openclaw config set` CLI) after every
`openclaw config`/`openclaw gateway status`/`openclaw daemon status`
invocation was observed to print its real, correct output and then hang
indefinitely on process teardown in this environment (`exit 124` after
already succeeding) - a real, reproducible harness quirk in this OpenClaw
build, not a config or logic bug. Every edit was validated with
`openclaw config validate` (which itself exhibits the same print-then-hang
behavior - output was read before the hang) and applied with
`openclaw daemon restart` (Windows Scheduled Task-backed gateway service).

## Live verification

1. `openclaw models list --provider opencode-go` -> 21 models listed,
   `opencode-go/deepseek-v4-flash-vision-exp` shown with `Auth: yes`,
   tags `default,configured`.
2. Real text+image smoke test: downloaded one genuine BBC/Icecream ad
   image already persisted in Neon (from the competitor-replacement
   milestone), ran `openclaw infer model run --model
   opencode-go/deepseek-v4-flash-vision-exp --file <the real ad jpg>
   --prompt "Describe in one sentence what is visually depicted in this
   image."` -> real `status=200` from
   `https://opencode.ai/zen/go/v1/chat/completions`, real output: "A
   young man with dark dreadlocks stands on a concrete sidewalk against a
   textured beige wall, wearing a pink 'ICECREAM' t-shirt, baggy blue
   denim shorts, white socks, and chunky pink sneakers while looking off
   to the side." - correctly read the real brand name and real garment
   color off the real image, confirming both routing and vision
   capability work end to end before any orchestration code was written.

## Known limitations / what's still open

- OpenClaw's own doctor still flags real, pre-existing gaps unrelated to
  this model fix: no command owner configured
  (`commands.ownerAllowFrom`), gateway auth using a bare token rather
  than a hardened setup, and (at the very start of this session) a
  missing session-store directory - the last one appears to have
  resolved itself once the gateway was actually started/restarted
  (`~/.openclaw/state` now has real session state files), but was never
  independently re-verified as fixed by this session's own doctor run.
- The print-then-hang behavior on `openclaw config`/`gateway status`/
  `daemon status`/`daemon restart` was worked around (read stdout before
  the timeout kills the process) but not fixed - if this repo's future
  Sequence F skill/cron work shells out to any of these commands
  directly, it must apply the same workaround (a bounded timeout that
  treats "printed valid output, then hung" as success) rather than
  treating a non-zero/timeout exit code as failure.
- No Sequence F skill file, run lock, timestamped logs, resumable state,
  or offline tests exist yet - this section is infrastructure-only.

## Next step

Build the actual Sequence F OpenClaw skill (tool order, inputs/outputs,
failure rules per the brief) that orchestrates the existing Python CLIs
end to end, add the run lock + logs + resumable state, prove one manual
dry run, then (only after that succeeds) configure the native `openclaw
cron` schedule for every 12 hours in `Asia/Dubai`. Not started yet.
