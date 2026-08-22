# Samsin Ad Intelligence

Two independent, small CLIs against the ScrapeCreators API:

- **Sequence A** (`ad_fetcher`): paid Meta/Facebook ad-library ads for one
  hardcoded competitor (Aelfric Eden).
- **Sequence B** (`organic_fetcher`): public organic Instagram posts/reels
  for one hardcoded account (`aelfricedenofficial`).

Both: one provider call, no pagination, no database, no scheduling, no
scoring. They do not talk to each other — see `HANDOFF.md` for why (organic
vs. paid metrics must stay separate) and what Sequence C would add.

## Setup

1. Create a ScrapeCreators account at https://scrapecreators.com and get one
   API key from your dashboard.
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and set `SCRAPECREATORS_API_KEY=<your key>`.
   (Alternatively, set `SCRAPECREATORS_API_KEY` directly in your shell —
   an env var, when set, wins over `.env`.)
3. No third-party dependencies to install — everything here uses the Python
   standard library (`urllib`, `json`, `unittest`). Any Python 3.10+ works.

The one competitor (`Aelfric Eden`) is configured in one place:
[`src/ad_fetcher/config.py`](src/ad_fetcher/config.py) — the `COMPETITOR` dict.

The one Instagram account for Sequence B (`aelfricedenofficial`) is
configured in [`src/organic_fetcher/config.py`](src/organic_fetcher/config.py).

## Run tests

```bash
python -m unittest discover -s tests -v
```

Runs both Sequence A's and Sequence B's tests together (28 total) — a
regression in one shows up when you run the other.

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
