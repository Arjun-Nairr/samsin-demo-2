---
name: samsin-ad-pipeline
description: Run the Samsin competitor-analysis, creative-generation, and Instagram publishing demo through the repository's existing CLIs. Use for manual dry runs, explicitly approved publishing runs, and the approved 12-hour OpenClaw automation.
user-invocable: true
---

# Samsin ad pipeline

Run the existing pipeline; do not reimplement its providers or business logic. Reliability is more important than creative quality.

## Modes

- Default to `dry-run`. It may upload to ImgBB and create/poll an Instagram container, but must not publish.
- Use `publish` only when the invocation or installed automation explicitly authorizes publication.
- Never change from `dry-run` to `publish` based on model judgment.

## Run boundary

Work from the repository root and execute Python modules from `src/`.

**Always invoke the interpreter by its full path**:
`C:\Users\dwish\AppData\Local\Programs\Python\Python312\python.exe`.
This machine has three different `python.exe` on PATH (a Microsoft Store
alias stub and a separate minimal install besides this one); bare
`python` resolves unpredictably depending on the calling environment and
has been observed, live, to land on an interpreter without a working
certificate bundle - causing real `CERTIFICATE_VERIFY_FAILED` errors
against `shopsamsin.com` that the correct interpreter never hits. Every
`python -m ...` command below means this exact executable, not bare
`python`.

Before any paid or externally mutating call:

1. Acquire the lock: `python -m pipeline_run.main acquire --run-id <run-id> --mode dry-run|publish`. This exclusively creates `.samsin_pipeline.lock` with the UTC timestamp, run ID, and mode already recorded - do not implement locking yourself.
2. If that command exits non-zero (`error: lock held by ...`), stop and exit without doing any work. If its JSON output has `"stale_replaced": true`, the previous lock was older than 60 minutes and was safely replaced - report that in the run log.
3. Create `.openclaw_runs/<run-id>/run.json` and `run.log`. Record each completed stage and its output paths, never credentials or full environment values.
4. On a normal exit (success or handled failure), release the lock: `python -m pipeline_run.main release`. Preserve the run directory either way.

Do not run this workflow simultaneously from another machine.

## Workflow

Stop on an unhandled failure. Never invent missing data.

When saving a CLI's JSON output to a run-directory file, write it with an
explicit UTF-8 encoding (e.g. Python's `open(path, "w", encoding="utf-8")`
around the parsed JSON) rather than a raw shell `>` redirect - a live run
showed PowerShell's default redirection encoding produces UTF-16, which
every other tool in this repo reads as UTF-8 and would fail to parse.

### 1. Refresh competitor ads

From `src/`, run:

```text
python -m competitive_memory.main
```

Allow at most one ScrapeCreators refresh per pipeline run. Save its JSON output in the run directory.

### 2. Analyze pending ads

Run:

```text
python -m competitive_memory.analysis_cli pending 1
```

Analyze exactly the one returned ad (not five - one model-led competitor ad is the only generation inspiration this pipeline uses) using its real copy and `media_url`. Prefer an ad that actually shows a model wearing the product; if the one pending ad returned doesn't, analyze it anyway (never invent a different one) and note that plainly. Inspect the image with the configured vision model. Save exactly this JSON shape:

```json
{
  "pose_and_body_orientation": "short evidence-based description",
  "camera_crop_and_angle": "short description",
  "model_styling": "short description of the model's clothing/hair/styling as shown",
  "dominant_colors_and_treatment": ["dominant color or color-grading note"],
  "background": "short description",
  "lighting": "short description",
  "overall_visual_style": "short description",
  "reusable_samsin_inspiration": ["general pattern that Samsin may reinterpret"],
  "confidence": 0.0
}
```

`confidence` must be between 0 and 1. Describe only visible or supplied evidence. Do not claim performance, copy a competitor layout, or include competitor branding as inspiration.

Write the analysis to a run-directory JSON file, then pipe that file to:

```text
python -m competitive_memory.analysis_cli save <ad_id>
```

If the ad cannot be downloaded or analyzed, run `analysis_cli fail` with a short safe reason and record the degraded fallback (empty competitor inspiration) rather than substituting a different ad. Never include URLs with signed query strings, tokens, or credentials in the error.

### 3. Rank context

Run (unchanged, existing Sequence D behavior - preserved even though this pipeline no longer uses its output as the brief's inspiration source):

```text
python -m competitive_memory.ranking
```

This still reflects all completed analyses in Neon, old-schema and new-schema alike, and remains useful on its own. It is **not** where step 5's `competitor_inspiration` comes from - that's built directly from the single ad just analyzed in step 2, identified by its real `ad_id`, so the brief carries forward that ad's own concrete observations rather than an aggregate.

### 4. Select a Samsin product

Run:

```text
python -m samsin_reference.main
```

**Hardcoded for this demo**: the product is always `star-t-shirt-radiostar`
(STAR T-SHIRT WHITE). Select that exact handle from the real returned
catalog - do not pick a different product, and do not skip the real fetch
(price/availability/garment image still come from the live call, never
invented). Save the selected product object unchanged as `product.json`.

The matching official model reference for this one product is hardcoded
in `samsin_reference.config.KNOWN_MODEL_REFERENCES["star-t-shirt-radiostar"]`
(a real, manually-confirmed Samsin storefront URL - automatic model-photo
classification is a documented future improvement, not built here since
Samsin's catalog otherwise has zero classified model images). Read that
value and carry it forward as `model_reference` for steps 5-7.

### 5. Create the brief

Write `creative_brief.json` in the run directory with only:

```json
{
  "tone": "basic streetwear advertisement direction",
  "notes": "simple composition guidance grounded in the selected product",
  "source_competitor_ad_id": "<the ad_id analyzed in step 2>",
  "competitor_inspiration": "concrete observations from that one ad's analysis - pose, crop/angle, styling, colors, background, lighting - never generic 'streetwear' language",
  "caption": "truthful caption using only verified product information"
}
```

`competitor_inspiration` must read like it came from that specific ad
(reference its actual pose, crop, colors, lighting, etc. from step 2's
analysis), not a generic mood summary. Do not introduce discounts,
scarcity, prices, products, logos, slogans, or claims absent from the
inputs. The Samsin model reference itself is not an "invented person" -
it's the real, hardcoded official Samsin photo for this product; never
add any *other* person or model. The image prompt must remain text-free
as enforced by the existing generator.

**Minimum quality rule** (part of the brief's `notes`, not a separate
critic or prompt system): the generated creative must visibly differ from
the source catalog image. Require a contrasting textured or colored
background, directional shadows, dynamic framing, and 1-2 neutral
streetwear props. No rendered text, invented branding, prices, discounts,
or unsupported claims.

### 6. Generate two candidates

From `src/`, run the existing generator with the run-directory brief/product files, the selected garment image, and the hardcoded model reference from step 4:

```text
python -m creative_generation.main generate --brief <brief-file> --product <product-file> --garment <garment-url> --model-reference <model-reference-url>
```

Both references are passed through to the existing generator unchanged - it already supports `--model-reference`, nothing new was built here. The command must return exactly two candidates. Do not call Gemini again unless step 7 authorizes the single retry.

### 7. Select a candidate

Reject candidates that failed deterministic checks. Inspect passing images with the configured vision model and reject any candidate showing obvious model-identity drift (a different face, hair, or person than the model reference), altered shirt graphics/colors (not the real white tee with the exact star graphic), or invented text/claims - these are hard rejections, not preferences. Among the remaining candidates, select the clearer basic advertisement that best preserves the real model and shirt and clears the minimum quality rule above (visibly differs from the source catalog image via background/shadow/framing/props - not just a plain reproduction of the garment reference).

If neither candidate clears the quality floor, allow exactly one existing-command retry:

```text
python -m creative_generation.main retry --run-dir <generated-run-dir>
```

Do not retry again. If semantic vision inspection is merely inconclusive (not a hard rejection) but a candidate passed deterministic checks, select the first passing candidate and record the degraded fallback. **This fallback never applies to a hard rejection** (model-identity drift, altered shirt graphics/colors, or invented text/claims) - if every candidate, including the one retry, is hard-rejected, stop the run, record the rejection reasons and preserve every candidate/manifest for inspection, and report the failure rather than silently selecting a rejected image.

### 8. Publish boundary

For `dry-run`, run without `--publish`:

```text
python -m manual_publishing.main --image <selected-image> --brief <brief-file>
```

For explicitly authorized `publish`, add `--publish` once.

Never retry an Instagram publication after an ambiguous timeout, connection loss, or provider error; stop and require manual confirmation of account state. Respect the repository's 180-second cooldown. One run may create at most one ImgBB upload/Instagram container chain.

## Completion

Update the run record with the selected ad IDs, ranked-context path, selected product handle, brief path, generated manifest path, selected candidate path, publication mode, and final status. Return a short summary with those paths and any degraded fallback. Never output secrets.

The OpenClaw automation owns the 12-hour schedule and durable run history. Do not create another scheduler or a second custom state system.
