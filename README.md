# Samsin Ad Intelligence — Sequence A

Fetches recent Meta (Facebook/Instagram) ad-library ads for one hardcoded
competitor via the ScrapeCreators API, and normalizes them into a small
JSON contract. This is Sequence A only: one competitor, one provider call,
no database, no scheduling, no scoring.

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

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Run the fetcher

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
