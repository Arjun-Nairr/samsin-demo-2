# Handoff — Sequences A, B & C

## Current status (read this first)

- **Sequence A** (paid Meta ads, `ad_fetcher`) — **implemented, tested, live-verified.**
- **Sequence B** (organic Instagram posts, `organic_fetcher`) — **implemented, tested, live-verified.**
- **Sequence C** (Neon persistence of paid ads, `competitive_memory`) —
  **implemented, tested offline (67 tests). Neon migration and a direct
  smoke test (insert/select/delete) are real, live-verified.** A real
  end-to-end `competitive_memory.main` run spent 1 ScrapeCreators credit
  and then failed at the database-connection step with a transient-looking
  `OperationalError` — a follow-up bare connection check succeeded, but
  **no successful real end-to-end run has been observed yet.** See the
  "Neon verification status" subsection under "Sequence C — Neon
  Persistence" for the exact sequence of what was and wasn't verified.
  *(Note: an earlier part of this file used "Sequence C" to mean a future
  ads↔organic-post matching audit. That name has been reassigned to this
  persistence milestone instead — see the marked note where that occurs.)*
- Ads↔organic-post matching, AI analysis, weighting, and everything else
  in Sequence C's non-goals list — **not implemented**, documented only.
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
