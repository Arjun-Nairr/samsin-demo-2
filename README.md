# Samsin Ad Intelligence

Three small, mostly-independent pieces against the ScrapeCreators API and
one Postgres database:

- **Sequence A** (`ad_fetcher`): paid Meta/Facebook ad-library ads for one
  hardcoded competitor (Aelfric Eden).
- **Sequence B** (`organic_fetcher`): public organic Instagram posts/reels
  for one hardcoded account (`aelfricedenofficial`).
- **Sequence C** (`competitive_memory`): runs Sequence A's fetch, then
  persists/upserts the normalized ads into a `competitor_ads` table in
  Neon PostgreSQL, and reports which ads are newly discovered this run —
  the "active competitive memory" that a later (not-yet-built) analysis
  stage will read from. Sequence B (organic Instagram posts) is entirely
  separate — it is not stored in Neon, not matched against ads, and not a
  prerequisite for running Sequence C at all.

One provider call each, no pagination, no scheduling, no scoring, no AI
analysis yet. See `HANDOFF.md` for design history and what's deferred.

## Setup

1. Create a ScrapeCreators account at https://scrapecreators.com and get one
   API key from your dashboard.
2. For Sequence C only: create a free Neon project at https://neon.tech,
   open its dashboard, and copy the **pooled** connection string (the one
   with `-pooler` in the hostname) — Neon's pooled string is just an
   ordinary PostgreSQL connection string to this app, no special handling
   needed.
3. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and set `SCRAPECREATORS_API_KEY=<your key>` and (for
   Sequence C) `DATABASE_URL=<your Neon pooled connection string>`.
   (Alternatively, set either directly in your shell — an env var, when
   set, always wins over `.env`.)
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   This is the one dependency in the whole repo: `psycopg[binary]`, needed
   only for Sequence C. Sequences A and B still use nothing but the Python
   standard library.

The one competitor (`Aelfric Eden`) is configured in one place:
[`src/ad_fetcher/config.py`](src/ad_fetcher/config.py) — the `COMPETITOR` dict.
Sequence C reuses this configuration; there is no second place a
competitor is named.

The one Instagram account for Sequence B (`aelfricedenofficial`) is
configured in [`src/organic_fetcher/config.py`](src/organic_fetcher/config.py).

## Run tests

```bash
python -m unittest discover -s tests -v
```

Runs Sequence A's, B's, and C's tests together — a regression in one shows
up when you run the others. (Don't hardcode the count here — it changes
every time a test is added; run the command above to see the current
number and confirm `OK`.) None of these tests touch a live database, make
a live ScrapeCreators request, spend API credits, or need network access —
Sequence C's database tests use a small in-memory fake connection.

## Run Sequence A (paid ads)

```bash
cd src
python -m ad_fetcher.main
```

Prints only the final JSON to stdout on success; errors go to stderr with a
non-zero exit code (safe to check with `$?` / `%ERRORLEVEL%`), and the
error text never includes the API key.

### Expected output shape

```json
{
  "count": 5,
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
    }
  ]
}
```

## Run Sequence B (organic Instagram posts)

```bash
cd src
python -m organic_fetcher.main
```

Same contract: stdout=JSON only on success, stderr+non-zero exit on
failure, API key never printed.

### Expected output shape

```json
{
  "count": 12,
  "organic_posts": [
    {
      "platform": "instagram",
      "post_id": "3954222268720362185_11087474383",
      "shortcode": "DbgODP6BDLJ",
      "brand": "Aelfric Eden",
      "account_handle": "aelfricedenofficial",
      "post_type": "video",
      "caption": "The first day fit starts here. Back to School Sale is now live.",
      "published_at": "2026-08-01T16:00:08+00:00",
      "permalink": "https://www.instagram.com/p/DbgODP6BDLJ/",
      "media_url": "https://scontent-atl3-1.cdninstagram.com/o1/v/t2/...",
      "thumbnail_url": "https://scontent-atl3-3.cdninstagram.com/v/...",
      "organic_view_count": 123483,
      "organic_like_count": 3,
      "organic_comment_count": 13
    }
  ]
}
```

### Sequence B design notes

- **`post_id` is the API's `id` field, not `pk`.** Confirmed live: `pk` is
  always `null` under `trim=true`. `id` (e.g.
  `"3954222268720362185_11087474383"`) is the real stable, unique ID.
- **`permalink` comes straight from the API's `url` field** (present on
  every observed item, including reels — which use `/p/<code>/`, not
  `/reel/<code>/`). Shortcode-construction (`/p/<code>/`) is fallback-only,
  for the rare case `url` is missing. Not downloaded/persisted (Sequence B
  has no storage, same as Sequence A).
- **`post_type` is always `image` or `video`**, never `"carousel"` —
  carousels are resolved to whichever supported item is picked (see below),
  matching Sequence A's two-value `media_type` contract.
- **`organic_view_count` prefers the documented
  Instagram-specific `ig_play_count`** when present, else the generic
  `play_count`, else `null`. A real `0` is preserved, never turned into
  `null`.
- **Carousel selection**: iterates `carousel_media[]` in order and uses the
  **first item with a supported type and a usable media URL** (not
  necessarily index 0) — image or video. Confirmed live: carousel sub-items
  carry their own `media_type`/`video_versions`/`image_versions2`, but
  **never** their own `play_count`/`like_count`/`comment_count` — those
  only exist on the container. So media is taken from the selected
  sub-item, but engagement metrics always come from the top-level item.
- **`thumbnail_url`** is the video's poster-frame image
  (`image_versions2`) — populated for video posts (including a
  video-first carousel), left `null` for image posts since it would just
  duplicate `media_url`.
- Signed Instagram CDN media URLs (`cdninstagram.com`) expire, same caveat
  as Sequence A's Facebook CDN URLs, unrelated to Meta ad performance.
- **Organic metrics are never conflated with ad metrics.** `organic_view_count`
  is never renamed `ad_view_count`, and Sequence B never touches Sequence
  A's output — matching them is explicitly Sequence C's (undocumented,
  unimplemented) job.

## Run Sequence C (persist paid ads to Neon)

One-time setup — apply the migration (safe to re-run; only ever creates
the table if it doesn't already exist, never drops or alters anything):

```bash
cd src
python -m competitive_memory.migrate
```

Then, for every refresh:

```bash
cd src
python -m competitive_memory.main
```

Same contract as Sequences A and B: stdout=JSON only on success, stderr +
non-zero exit on failure, neither `SCRAPECREATORS_API_KEY` nor
`DATABASE_URL` is ever printed, logged, or included in an error message.

This fetches Sequence A's normalized ads, upserts them into `competitor_ads`
by `ad_id` (the primary key — this is the whole deduplication mechanism,
no separate dedup table), and reports which ads were newly discovered.
This command is the intended integration point for a future scheduler or
OpenClaw — neither is built here.

### Expected output shape

```json
{
  "fetched_count": 20,
  "inserted_count": 7,
  "updated_count": 13,
  "ready_for_analysis_count": 7,
  "ready_for_analysis": [
    {
      "ad_id": "123",
      "brand": "Aelfric Eden",
      "body": "...",
      "headline": "...",
      "cta": "...",
      "media_type": "image",
      "media_url": "https://...",
      "started_at": "2026-08-01T00:00:00+00:00",
      "is_active": true,
      "snapshot_url": "https://..."
    }
  ]
}
```

`ready_for_analysis` uses Sequence A's own normalized shape — `media_url`,
not the database column name `latest_media_url` — so this output is a
drop-in continuation of Sequence A's contract, not a new one.

### What `first_seen_at`, `last_seen_at`, and `times_seen` mean

- **`first_seen_at`** — set once, by the database (`DEFAULT NOW()`), the
  first time an `ad_id` is ever inserted. Never overwritten afterward.
- **`last_seen_at`** — updated to the current database time on every run
  that ad appears in the fetch again. Tells you how recently it was still
  running, independent of whether anything about it changed.
- **`times_seen`** — increments by exactly 1 per run the ad appears in,
  regardless of how many of its fields changed that run. It's an
  observation counter, not a content-change counter.

### Important limitations (read before trusting this for analysis)

- **Media URLs expire.** Meta's and Instagram's CDN URLs carry short-lived
  signed tokens. `latest_media_url` is *the latest one seen*, useful
  immediately, **not durable storage** — this milestone does not download
  or persist competitor media anywhere (no ImgBB upload, no local copy).
  A stored ad's URL from three days ago may already be dead. The intended
  future flow is: new ad discovered → persisted → analyzed *in the same
  run*, while the URL is still fresh → analysis result stored — not
  implemented yet.
- **A changed signed URL alone is never "new."** Only an `ad_id` absent
  from the table triggers an insert / a `ready_for_analysis` entry. If the
  same ad's CDN URL rotates between runs, that's an update, not a new
  discovery.
- **Missing from a fetch ≠ inactive.** Each run is a small first-page
  batch (~20 ads), not the advertiser's full account. An ad absent from
  today's batch is not evidence it stopped running — `is_active` is only
  ever changed when the provider explicitly returns a boolean for that ad
  in the fetch that mentions it; it is never flipped to `false` (or to
  anything) just because the ad wasn't in this batch.
- **No weighting, scoring, or AI analysis yet.** `analysis_status` starts
  `'pending'` and is not otherwise touched by this milestone — no
  weighting formula has been approved, and no analysis schema exists yet
  (it will be designed from real Gemini trials, not guessed in advance).

## Design notes

- **`headline` is usually `""`.** The documented Company Ads response has no
  separate headline field for single-image/video ads (only `snapshot.body.text`,
  and `title` is `null` in every observed example). For carousel/DCO ads,
  `cards[0].title` is used as the headline — see below.
- **Carousel/multi-card ads**: we pick `cards[0]` as the one deterministic
  primary creative (body/headline/cta/media), falling back to the top-level
  `snapshot` fields for anything the card itself omits. One ad → one record,
  never expanded into several.
- **`snapshot_url`** is not a field ScrapeCreators returns. It's Meta's own
  public, stable Ad Library URL format (`facebook.com/ads/library/?id=<ad_archive_id>`),
  built from the ID the API does return — not a guessed or invented value.
- **Missing values**: text fields default to `""`, everything else to `null`
  (JSON `null`). Never invented.
- **No pagination loop.** One request, first page of results, capped at 20
  after normalization — matches the "small demo batch, don't crawl the
  account" requirement and keeps ScrapeCreators credit usage to ~1 request
  per run (its documented cost is 1 credit/request).
- **Why no company-search step**: the Company Ads endpoint accepts
  `companyName` directly, so no separate advertiser-resolution call is
  needed to run this. See `HANDOFF.md` for the identity-verification status.
- **Impressions/reach/spend/views are not fetched or displayed.** Ordinary
  commercial Meta ads don't expose competitor performance metrics publicly;
  `started_at` is when the paid ad began running, not when the creative was
  produced.
