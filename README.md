# Samsin Ad Intelligence

Seven small, mostly-independent pieces spanning competitor intelligence
(ScrapeCreators + Neon), Samsin's own creative production (Gemini +
ImgBB + Instagram), and orchestration (OpenClaw):

- **Sequence A** (`ad_fetcher`): paid Meta/Facebook ad-library ads for one
  hardcoded, verified competitor (currently **Billionaire Boys Club
  Icecream**, `page_id` `142427132456114`) — static images/memes only, US
  only. **Note**: this replaced PacSun, whose live catalog had ~0 static
  image/meme ads even with a wide `status=ALL` + 60-day window (their mix
  was 100% Dynamic Creative Optimization and video) — see "Known
  limitations" in `HANDOFF.md`.
- **Sequence B** (`organic_fetcher`): public organic Instagram posts/reels
  for the same competitor's handle (`bbcicecream`).
- **Sequence C** (`competitive_memory`): runs Sequence A's fetch, then
  persists/upserts the normalized ads into a `competitor_ads` table in
  Neon PostgreSQL, and reports which ads are newly discovered this run —
  the "active competitive memory." Sequence B is entirely separate — not
  stored in Neon, not matched against ads, not a prerequisite for C.
- **Sequence D** (`competitive_memory.analysis` / `.ranking`): turns that
  memory into agent-ready tools — a scoped, retryable queue of pending
  static ads for a future external analysis step (OpenClaw, not built
  here) to read and write results into, plus a deterministic ranked
  "compact context" payload over completed analyses.
- **Sequence E** (`samsin_reference`, `creative_generation`,
  `manual_publishing`): fetches Samsin's own real T-shirt catalog from
  their public storefront, generates Gemini image candidates from a real
  garment reference, and manually (dry-run by default) publishes a chosen
  candidate to Instagram. Entirely independent of the paid-ad pipeline
  above and of the old samsin-pricing-demo project — fresh code throughout.
- **Sequence F** (`skills/samsin-ad-pipeline`, `pipeline_run`): an OpenClaw
  skill that orchestrates Sequences C-E end to end (refresh → analyze →
  rank → pick a product → brief → generate → select → publish-boundary)
  without reimplementing any of them, run either manually or on OpenClaw's
  own native 12-hour cron. `pipeline_run` is the one new piece of code
  this needed: a small stdlib-only stale-aware exclusive run lock
  (`.samsin_pipeline.lock`) so a manual run and the scheduled run can
  never overlap.

One provider call each (Sequences A-D), no pagination, no scoring beyond
Sequence D's documented V1 weighting proxy, no autonomous visual/creative
QA (a human/agent always picks the candidate, never an unattended
critic), no automatic Instagram *publishing* anywhere by default -
Sequence F's automation runs in `dry-run` mode until a human explicitly
switches one job to `publish`. See `HANDOFF.md` for design history and
what's deferred.

## Setup

1. Create a ScrapeCreators account at https://scrapecreators.com and get one
   API key from your dashboard.
2. For Sequence C only: create a free Neon project at https://neon.tech,
   open its dashboard, and copy the **pooled** connection string (the one
   with `-pooler` in the hostname) — Neon's pooled string is just an
   ordinary PostgreSQL connection string to this app, no special handling
   needed.
3. For Sequence E: get a `GEMINI_API_KEY` from https://aistudio.google.com
   (**billing must be enabled on that project** - the free tier has zero
   quota for image-generation models, confirmed live), an `IMGBB_API_KEY`
   from https://api.imgbb.com, and an Instagram Graph API `IG_USER_ID` +
   access token (`IG_LONG_LIVED_TOKEN` or `IG_SHORT_LIVED_TOKEN`) for the
   account you want to post to. If you only have the token, you can
   resolve the numeric `IG_USER_ID` with one read-only call:
   `GET https://graph.instagram.com/{version}/me?fields=id,username&access_token=<token>`.
4. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and set whichever keys the sequences you're running
   need (see `.env.example` for the full list). An env var, when set,
   always wins over `.env`.
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   Two dependencies in the whole repo: `psycopg[binary]` (Sequence C) and
   `Pillow` (Sequence E - needed for a real, deterministic image resize/
   crop step; see "Sequence E" below for why). Sequences A and B still use
   nothing but the Python standard library.

The one competitor is configured in one place:
[`src/ad_fetcher/config.py`](src/ad_fetcher/config.py) — the `COMPETITOR`
dict (`name` + verified `page_id`). Every other sequence reuses this; there
is no second place a competitor is named. The current value (Billionaire
Boys Club Icecream, `page_id` `142427132456114`) was verified via a live
diagnostic fetch that found 16 usable active US static-image ads — see the
comment above `COMPETITOR` in that file.

The one Instagram account for Sequence B (handle `bbcicecream`) is
configured in [`src/organic_fetcher/config.py`](src/organic_fetcher/config.py) —
not independently re-verified via company-search this session, see the
comment in that file.

## Run tests

Install dependencies first (`pip install -r requirements.txt` — see
Setup step 4 above), otherwise `test_competitive_memory.py` and
`test_cli_error_handling.py` fail to import (`psycopg` not installed),
even though they never open a real database connection.

```bash
python -m unittest discover -s tests -v
```

Runs every sequence's tests together — a regression in one shows up when
you run the others. (Don't hardcode the count here — it changes every time
a test is added; run the command above to see the current number and
confirm `OK`.) None of these tests touch a live database, make a live
ScrapeCreators/Gemini/ImgBB/Instagram request, spend API credits, or need
network access —
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
      "brand": "PacSun",
      "body": "New drop: oversized graphic tees.",
      "headline": "",
      "cta": "Shop Now",
      "media_type": "image",
      "media_url": "https://scontent.xx.fbcdn.net/ad-image-1.jpg",
      "started_at": "2025-06-15T15:06:40+00:00",
      "is_active": true,
      "snapshot_url": "https://www.facebook.com/ads/library/?id=111111111111111",
      "page_id": "7133041750",
      "collation_id": "333333333333333",
      "collation_count": 1
    }
  ]
}
```

`media_type` is always `"image"` now — Sequence D made the paid-ad contract
static-image-only. The request itself asks ScrapeCreators for
`media_type=IMAGE_AND_MEME`, `country=US`, `status=ACTIVE`, and the
verified `pageId` (not a fuzzy `companyName` search); the normalizer also
defensively rejects any video/DPA/unsupported record that slips through
regardless. `page_id`/`collation_id`/`collation_count` are new evidence
fields (Sequence D) kept for future weighting — `null` when the provider
doesn't supply them, never fabricated.

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
      "brand": "PacSun",
      "account_handle": "pacsun",
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

One-time setup — apply every migration under `migrations/` (safe to re-run
any time, including after a new migration file is added; each is
idempotent - `CREATE TABLE IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` -
never drops a table, deletes a row, or alters an existing column):

```bash
cd src
python -m competitive_memory.migrate
```

Currently applies `0001_create_competitor_ads.sql` (the base table) and
`0002_add_weighting_and_analysis_fields.sql` (Sequence D's evidence and
analysis-persistence columns).

Then, for every refresh:

```bash
cd src
python -m competitive_memory.main
```

Same contract as Sequences A and B: stdout=JSON only on success, stderr +
non-zero exit on failure, neither `SCRAPECREATORS_API_KEY` nor
`DATABASE_URL` is ever printed, logged, or included in an error message.

This connects to Neon **first**, before calling ScrapeCreators — if the
database is unreachable, no paid request is made and no credit is spent.
The connection attempt is bounded: an explicit ~17s `connect_timeout`,
retried once (one ~2s delay) only for a connection-level failure, never
retried indefinitely. Once connected, it fetches Sequence A's normalized
ads, upserts them into `competitor_ads` by `ad_id` (the primary key — this
is the whole deduplication mechanism, no separate dedup table), and
reports which ads were newly discovered. This command is the intended
integration point for a future scheduler or OpenClaw — neither is built
here.

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
      "brand": "PacSun",
      "body": "...",
      "headline": "...",
      "cta": "...",
      "media_type": "image",
      "media_url": "https://...",
      "started_at": "2026-08-01T00:00:00+00:00",
      "is_active": true,
      "snapshot_url": "https://...",
      "page_id": "7133041750",
      "collation_id": "...",
      "collation_count": 1
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
- **No AI analysis in this repository.** `analysis_status` starts
  `'pending'`; Sequence D adds the persistence *boundary* an external
  agent (OpenClaw, not built here) will use to read pending work and
  write results back — see "Sequence D" below. No model is called by
  anything in this codebase.

## Sequence D — agent-ready tools (pending queue, analysis results, ranking)

Three additional capabilities, all reusing Sequence A/C's existing
normalized ads and the same Neon table (two new columns groups added by
migration `0002`, see below) — no new table, no queue service, no ORM.

### List pending analysis work

```bash
cd src
python -m competitive_memory.analysis_cli pending [limit]
```

Returns configured-competitor, image-only rows with a usable current
`media_url` and `analysis_status` of `pending` **or** `failed` (a failed
attempt is retried here, never permanently lost) — pending rows first,
oldest first within each group. `limit` defaults to a small, configurable
batch (`config.PENDING_BATCH_SIZE`), not a full backlog dump.

```json
{ "pending": [ { "ad_id": "...", "brand": "PacSun", "media_url": "...", "analysis_status": "pending", "analysis_attempts": 0, "...": "..." } ] }
```

### Save a completed analysis

```bash
cd src
python -m competitive_memory.analysis_cli save <ad_id>   < result.json
```

Reads the analysis result JSON from **stdin** (not argv) — large payloads
and shell-escaping are never fragile this way. The result must be a JSON
*object*; anything else (a string, a list, a number) is rejected. An
unknown `ad_id`, or one belonging to a different competitor than the
currently configured one, is rejected identically — both look like
"unknown" to the caller, since the query is scoped by `page_id`.

### Mark an analysis attempt failed

```bash
cd src
python -m competitive_memory.analysis_cli fail <ad_id> "error message"
```

(Omit the message to read it from stdin instead.) Increments
`analysis_attempts`, records `analysis_error`, and leaves the row
`analysis_status = 'failed'` — still returned by `pending` above, so
nothing is lost; a future retry policy can decide when to give up.

### Ranked competitive context

```bash
cd src
python -m competitive_memory.ranking
```

Computes `weight = 0.5×recency + 0.3×longevity + 0.2×recurrence` over
every **completed** analysis for the configured competitor, drops
anything below a configurable minimum threshold, and returns the
configurable top-N by weight. All weights/windows/thresholds live
together in [`src/competitive_memory/config.py`](src/competitive_memory/config.py).
Scores are computed fresh on every call (real "now"), so recency shifts
day to day automatically — no scheduled score-update job exists or is
needed.

```json
{
  "count": 3,
  "context": [
    {
      "ad_id": "...", "brand": "PacSun", "body": "...", "headline": "...",
      "cta": "...", "media_type": "image", "media_url": "...",
      "snapshot_url": "...", "analysis_result": { "...": "whatever the agent returned" },
      "weight": 0.7123,
      "component_scores": { "recency": 0.8, "longevity": 0.5, "recurrence": 1.0 }
    }
  ]
}
```

**These are proxies, not performance claims** — documented explicitly in
`ranking.py`:
- **Recency** uses `started_at`; if the provider never gave one, it falls
  back to `first_seen_at` (a real timestamp, just less precise) rather
  than dropping the ad or inventing a date.
- **Longevity** (how long an ad has been observed running) is
  circumstantial evidence the advertiser values it — not proof it's
  profitable.
- **Recurrence** uses `collation_count` (distinct creative variants under
  the same campaign, per the provider) only. **`times_seen` is never
  substituted here** — it only counts how many times *this project's own
  fetch* has observed the ad, and says nothing about the advertiser's
  creative variants. Missing `collation_count` scores a neutral `0.0`,
  never an invented count.

This does not generate a creative brief — that conversion is OpenClaw's
job, in a later milestone.

## Sequence E — Creative Generation and Manual Publishing

Three independent pieces, all fresh code with **no dependency on the old
samsin-pricing-demo project**: `samsin_reference` (fetch), `creative_generation`
(Gemini), `manual_publishing` (ImgBB + Instagram).

### Fetch Samsin's real T-shirt catalog

```bash
cd src
python -m samsin_reference.main
```

Reads Samsin's live public Shopify storefront directly (`shopsamsin.com`)
— no credentials, no ScrapeCreators involved. Restricted to T-shirts.

```json
{
  "count": 7,
  "products": [
    {
      "title": "STAR T-SHIRT WHITE",
      "handle": "star-t-shirt-radiostar",
      "product_url": "https://shopsamsin.com/products/star-t-shirt-radiostar",
      "price": 38.9,
      "currency": "USD",
      "in_stock": true,
      "garment_image_urls": ["https://cdn.shopify.com/.../StarT-Shirt-Radiostar.jpg"],
      "model_image_urls": [],
      "all_image_urls": ["..."]
    }
  ]
}
```

- **`in_stock`** comes from Shopify's storefront AJAX endpoint
  (`/products/<handle>.js`), confirmed live to be the reliable source —
  the public `/products.json` listing endpoint omits `available` entirely
  on this store. `null` (never `true`) when genuinely unknown.
- **`model_image_urls` is `[]` for every real product right now.**
  Confirmed by checking all 31 products' images and the homepage: Samsin's
  current catalog is pure flat-lay/garment photography, no on-body shots
  anywhere. Classification is alt-text-keyword-based (best-effort, see
  `samsin_reference/config.py`) and every image still appears in
  `all_image_urls` regardless, so nothing is ever silently dropped.
- Price/availability/products are read directly from the live site, never
  invented — a product with no usable image is excluded entirely rather
  than guessed at.

### Generate Gemini image candidates

```bash
cd src
python -m creative_generation.main generate \
    --brief ../creative_brief.json --product ../star_product.json \
    --garment <garment_image_url_or_local_path>
    # add --model-reference <path_or_url> if one exists for the product
```

`creative_brief.json` is loosely typed - whatever's present is used:
```json
{
  "tone": "bold, editorial streetwear advertisement",
  "notes": "additional creative direction",
  "competitor_inspiration": "style/mood only - never literal copy",
  "caption": "used later by manual_publishing, never drawn into the image"
}
```

Generates exactly `NUM_CANDIDATES` (default 2) 1080×1350 PNGs plus one
`manifest.json`, all under `generated_creatives/<handle>_<run_id>/`:

```json
{
  "product": {"title": "...", "handle": "...", "product_url": "..."},
  "prompt": "...",
  "model": "gemini-2.5-flash-image",
  "candidates": [
    {"index": 1, "output_path": "...", "format": "png", "passed_checks": true, "check_error": null}
  ]
}
```

- **A real, live-confirmed finding**: Gemini does not reliably honor an
  exact pixel size requested via prompt text alone — it returned
  `1024x1024` for a requested `1080x1350`. A deterministic resize +
  center-crop step (`generator._cover_resize`, Pillow) now guarantees the
  exact target dimensions regardless of the model's native output size.
  This is why Pillow is a real dependency here, not stdlib-only.
- **Checks are deterministic only** — valid image, correct dimensions,
  readable format. No semantic/visual judgment of whether the creative is
  actually good. **A first real attempt with a weak, over-conservative
  brief produced a near-exact reproduction of the flat garment reference**
  — technically a "valid 1080x1350 PNG," completely useless as an ad.
  Deterministic checks cannot and do not catch this; only a human
  reviewing the actual image caught it, which is exactly the intended
  division of labor (a human picks the candidate now; OpenClaw does
  semantic QA later — no autonomous visual critic exists here).
- **Manual retry** (reuses the *same* saved prompt/references - a real
  retry, not a new creative direction):
  ```bash
  python -m creative_generation.main retry --run-dir <existing run dir>
  ```

### Manually publish (ImgBB → Instagram)

```bash
cd src
python -m manual_publishing.main --image <path> --brief ../creative_brief.json
# add --publish to actually post (dry-run is the default)
```

Dry-run uploads to ImgBB and creates+polls the Instagram media container —
both reversible, nothing has posted — then stops. Only `--publish` calls
the actual publish endpoint, and only after a **180-second cooldown**
since the last real publish (tracked in a local, gitignored
`.manual_publish_state.json` — dry runs never check or touch it).

```json
{"dry_run": false, "image_url": "https://i.ibb.co/...", "creation_id": "...", "published": true, "media_id": "..."}
```

- Caption comes verbatim from the creative brief's `"caption"` field —
  never invents an offer/discount.
- Container readiness is polled with bounded retries
  (`CONTAINER_POLL_MAX_ATTEMPTS`/`_DELAY_SECONDS` in `manual_publishing/config.py`)
  — never indefinite.
- Credentials and the Graph API version are entirely environment-driven
  (`IMGBB_API_KEY`, `IG_USER_ID`, `IG_LONG_LIVED_TOKEN`/`IG_SHORT_LIVED_TOKEN`,
  `IG_GRAPH_API_VERSION`, default `v21.0`) — never printed in any output or
  error message.

## Sequence F — OpenClaw Orchestration

Orchestrates Sequences C-E through an OpenClaw skill
(`skills/samsin-ad-pipeline/SKILL.md`) - it describes tool order, inputs/
outputs, and failure rules, and runs the existing CLIs directly. No
provider logic, ranking, generation, or publishing code is duplicated
here.

### The one new piece of code: the run lock

`src/pipeline_run/` is a small stdlib-only stale-aware exclusive lock so a
manual invocation and the scheduled automation can never run at the same
time:

```bash
cd src
python -m pipeline_run.main acquire --run-id <id> --mode dry-run|publish
python -m pipeline_run.main release
```

`.samsin_pipeline.lock` is created with `open(path, "x")` (atomic create-
or-fail on both POSIX and Windows). A lock younger than 60 minutes blocks
a new acquire; older than that, it's treated as stale, replaced, and
reported as such. Everything else the skill needs - run-directory
records, Neon's own `analysis_status` column, and OpenClaw's own cron run
history - already exists; nothing else was built.

### Installing/inspecting the skill

```bash
openclaw skills install "<repo>/skills/samsin-ad-pipeline" --as samsin-ad-pipeline
openclaw skills list        # shows samsin-ad-pipeline as "ready"
openclaw skills info samsin-ad-pipeline
openclaw skills check
```

### The isolated agent and its permissions

A dedicated OpenClaw agent (`samsin-pipeline`) runs this skill, workspace
pinned to this repo, model pinned to `opencode-go/deepseek-v4-flash-vision-exp`:

```bash
openclaw agents add samsin-pipeline --workspace "<repo>" --model opencode-go/deepseek-v4-flash-vision-exp --non-interactive
```

Its tool policy is scoped down in `~/.openclaw/openclaw.json` to only
`exec`, `read`, `write` (no browser, no messaging/channel tools, no other
agent's sessions) - everything this pipeline needs to run the repo's
Python CLIs and write run-directory files, nothing else:

```json
{ "agents": { "list": [ { "id": "samsin-pipeline", "tools": {
  "allow": ["exec", "read", "write"],
  "deny": ["edit", "apply_patch", "browser", "gateway", "process", "sessions_list", "sessions_send", "sessions_history", "session_status"]
} } ] } }
```

(A `tools.profile` override is deliberately *not* set on this agent - a
live run showed that pairing `profile: "minimal"` with an `allow` list
strips every tool before the allow-list is even applied, leaving nothing
callable. Leaving the profile unset inherits the already-scoped global
`"coding"` profile, which the `allow`/`deny` pair then narrows further.)
This does not touch the global exec policy (still whatever it was before
this milestone) - only this one agent's tool surface changed.

### The 12-hour automation

```bash
openclaw cron add --name samsin-ad-pipeline-12h \
  --cron "0 */12 * * *" --tz Asia/Dubai \
  --agent samsin-pipeline --model opencode-go/deepseek-v4-flash-vision-exp \
  --thinking high --session isolated --tools exec,read,write \
  --expect-final --message "Use the samsin-ad-pipeline skill. Run the pipeline in dry-run mode..."
openclaw cron edit <id> --no-deliver --clear-channel --clear-to --clear-account   # no external delivery
```

Operational commands:

```bash
openclaw cron show <id>                          # schedule, next run, delivery
openclaw cron status                             # scheduler-wide status
openclaw cron runs --id <id>                      # durable run history (this IS the run history - no separate system)
openclaw cron run <id> --wait --wait-timeout 30m  # force a run now and wait for it
openclaw cron disable <id>                        # pause the schedule
openclaw cron enable <id>                         # resume it
openclaw daemon restart                           # restart the gateway safely (config changes need this)
```

**Known live-discovered quirks** (all worked around, not silently
ignored):

- The pinned model does not support an explicit `"high"` thinking level -
  OpenClaw logs a warning and silently uses `"off"` for that call. Not a
  code defect; the model/thinking pairing is simply unsupported.
- `openclaw config`/`gateway status`/`daemon status`/`daemon restart`
  reliably print their correct result and then hang on process exit in
  this OpenClaw build/environment (`exit 124` after already succeeding).
  Any script driving these must read stdout before the timeout, not treat
  the timeout itself as failure.
- Files the pipeline writes must use an explicit UTF-8 encoding
  (documented in the skill) - a live run showed shell `>` redirection
  under PowerShell defaults to UTF-16, which the rest of this repo's
  tooling can't read as JSON without `encoding="utf-16"`.
- `python` is ambiguous on this machine (three different installs on
  PATH); the skill now pins the exact interpreter path it needs.

## Design notes

- **`headline` is usually `""`.** The documented Company Ads response has no
  separate headline field for single-image ads (only `snapshot.body.text`,
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
- **Verified page ID, not a fuzzy lookup**: Sequence D switched the Company
  Ads request from a `companyName` search to a verified `pageId` — the
  company-search endpoint is used *once*, offline, to resolve and confirm
  the identity (see `ad_fetcher/config.py`'s comment above `COMPETITOR`),
  not on every run. `country=US` and `media_type=IMAGE_AND_MEME` are also
  sent server-side, on top of the normalizer's own defensive rejection.
- **Impressions/reach/spend/views are not fetched or displayed.** Ordinary
  commercial Meta ads don't expose competitor performance metrics publicly;
  `started_at` is when the paid ad began running, not when the creative was
  produced.
