---
title: "Viewer Capabilities & On-Demand Fill-In"
description: "How the viewer gates preflight tools based on per-job capabilities and how to fill gaps on demand."
section: "preflight"
order: 25
---

# Viewer Capabilities & On-Demand Fill-In

Every LintPDF job carries a `data_capabilities` map — a set of boolean flags that tells the viewer which preflight tools have authoritative data to work with. Capabilities are populated differently in each submission mode:

| Mode | `findings` | `separations` | `tac` | `tac_runs` | `fonts` | `images` | `layers` |
|---|---|---|---|---|---|---|---|
| Engine (default) | ✓ | ✓ | ✓ | ✓ (tracks `tac`) | ✓ | ✓ | ✓ when present |
| External | depends on report | usually ✗ | usually ✗ | usually ✗ | depends on report | depends on report | ✓ when present |
| Minimal | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ when present |

The viewer reads `capabilities` from `GET /api/v1/viewer/jobs/{job_id}/config` and renders each preflight tool accordingly:

- **`true`** → tool is fully active.
- **`false`** and fill-in supported → tool renders a **Load** button that triggers on-demand fill-in.
- **`false`** and fill-in unsupported (`layers` only) → tool is hidden.

## The capability registry

| Capability | Fillable | Backing analyzer | Viewer tool |
|---|---|---|---|
| `findings` | ✓ | Full engine pipeline (all 500+ checks) | Findings panel |
| `separations` | ✓ | Spot-color analyzer | Separations viewer + ink channel rasters |
| `tac` | ✓ | Ink-coverage analyzer | TAC heatmap overlay |
| `tac_runs` | ✗ (derived on demand) | Same CMYK raster as `tac` plus `pdftotext -bbox` | Per-text-run tooltip on the TAC overlay (hover to read each run's mean TAC%) |
| `tiles_warmed` | ✗ (set by background task) | `lintpdf.viewer.warm_tiles` Celery task | Flips to `true` once every page tile is cached in S3. Drives the viewer's browser-side prefetch pass. Tracked in Redis at `lintpdf:tile-warm:{job_id}`; poll `/api/v1/viewer/jobs/{job_id}/tile-warming` for progress. |
| `fonts` | ✓ | Font analyzer | Font inspector |
| `images` | ✓ | Image analyzer | Image inventory |
| `layers` | ✗ | Extracted from PDF at job creation; not re-derivable | Layers panel |
| `thumbnails` | ✓ (always populated on `complete`) | Page rasterizer | Page thumbnails strip |
| `metadata` | ✓ (always populated on `complete`) | PDF metadata extractor | Document info panel |

Unknown capability names are ignored; the map is forward-compatible.

## Triggering fill-in

```bash
curl -X POST https://api.lintpdf.com/api/v1/viewer/jobs/{job_id}/capabilities/separations \
  -H "Authorization: Bearer lpdf_live_..."
```

Response:

```json
{
  "job_id": "d4e5f6a7-...",
  "capability": "separations",
  "status": "queued",
  "task_id": "celery-a1b2c3..."
}
```

`status` values:

- `queued` — a Celery task has been enqueued; poll `/config` to see the capability flip.
- `already_filled` — the capability is already `true`; no-op.

The endpoint requires `Authorization: Bearer <key>` and the `preflight:submit` permission. There's no separate permission for capability fill-in — if you can submit jobs, you can fill capabilities.

## Polling pattern

```python
import time, requests

def fill_and_wait(job_id, capability, timeout=60):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    requests.post(
        f"https://api.lintpdf.com/api/v1/viewer/jobs/{job_id}/capabilities/{capability}",
        headers=headers,
    ).raise_for_status()

    deadline = time.time() + timeout
    while time.time() < deadline:
        config = requests.get(
            f"https://api.lintpdf.com/api/v1/viewer/jobs/{job_id}/config",
            headers=headers,
        ).json()
        if config["capabilities"].get(capability) is True:
            return config
        time.sleep(1)
    raise TimeoutError(f"Capability {capability} did not fill within {timeout}s")

fill_and_wait("d4e5f6a7-...", "separations")
```

## Error responses

| Status | Reason |
|---|---|
| `400` | `capability` is not in the registry. |
| `404` | Job does not exist or is not owned by your tenant. |
| `409` | Job is not in `complete` state — wait for completion before requesting fill-in. |
| `422` | Capability is known but not fillable on this job (typically `layers` on a PDF with no OCGs). |

## Share links and fill-in

Share links preserve the capability state captured at report-mint time. Capability fill-in performed after a share link was minted does **not** retroactively surface in that link — the link continues to show the set of capabilities that were filled when the token was created. This matches the broader "share links are immutable captures" rule; see [Share Links](/docs/share-links).

To refresh a share link with newly-filled capabilities, revoke the old token and mint a new one.

## Tile pre-warming

Every completed job fires a background Celery task (`lintpdf.viewer.warm_tiles`) that pre-renders each page's tile into S3 at the default viewer DPI (150) plus the thumbnail DPI (72). This removes the ~500–2000 ms Ghostscript render from the viewing path — reviewers get warmed cache hits on every page click.

Progress lives in Redis at `lintpdf:tile-warm:{job_id}` as a hash with `status`, `rendered`, `total`, `dpi`, `started_at`, `updated_at`, `completed_at` fields. The viewer polls a dedicated endpoint every 1.5 s:

```bash
curl https://api.lintpdf.com/api/v1/viewer/jobs/{job_id}/tile-warming \
  -H "Authorization: Bearer lpdf_live_..."
```

Response:

```json
{
  "job_id": "d4e5f6a7-...",
  "status": "in_progress",
  "rendered": 7,
  "total": 20,
  "dpi": 150,
  "percent": 35,
  "started_at": "2026-04-14T10:22:13.441Z",
  "completed_at": null,
  "error": null
}
```

`status` values:

- `pending` — job isn't `complete` yet, or completed before the warming feature shipped.
- `in_progress` — worker is rendering; `rendered` increments per page.
- `complete` — every page tile is in S3. The viewer kicks off a browser-side prefetch pass at this point.
- `failed` — worker crashed; `error` carries a short message.
- `disabled` — warming is off (no Redis configured, or the `LINTPDF_TILE_WARMING_ENABLED` env gate is false). The viewer silently falls back to on-demand render.

The same endpoint is mirrored for share-link viewers at `/api/v1/viewer/public/{token}/tile-warming` — no auth, token-gated. Once warming settles, the `tiles_warmed` capability on `/config` flips to `true` and the viewer starts prefetching tile bytes into the browser's HTTP cache so page clicks paint in <20 ms.

### Warming configuration

| Env var | Default | Description |
|---|---|---|
| `LINTPDF_TILE_WARMING_ENABLED` | `true` | Global kill switch. Set to `false` to disable auto-enqueue on job completion — the `/tile-warming` endpoint then reports `status="disabled"` and the viewer falls back to on-demand rendering. |
| `LINTPDF_TILE_WARMING_PER_TENANT_MAX` | `3` | Maximum concurrent warming tasks per tenant. Enforced via a Redis semaphore at `lintpdf:tile-warm-sem:{tenant_id}`. Bulk-upload tenants that exceed the cap get their jobs re-queued with a ~20 s delay until a slot frees, so one tenant can't starve the worker pool. `0` disables the cap. |
| `LINTPDF_TILE_WARMING_INCLUDE_SEPARATIONS` | `true` | When on, warming also renders CMYK channel + spot-color rasters into S3 so the first click on the Separations panel / Densitometer doesn't pay the ~2 s Ghostscript cost. Turn off for tenants whose workflow never opens the separations UI — halves total warm time on large PDFs. |
| `LINTPDF_TILE_HOT_CACHE_ENABLED` | `false` | Opt-in Redis byte-cache for the default-DPI tile endpoint. When on, tiles served within 15 minutes skip even the S3 GET (~1–3 ms instead of ~100–200 ms). Off by default because PNG tiles are 50–500 KB and Redis memory is precious on smaller plans. Production tenants with a generously sized Redis can flip this on per-environment. |

### Admin warming dashboard

Every `warm_viewer_tiles` run persists a `tile_warm.complete` or `tile_warm.failure` event into two capped Redis lists so super-admins can inspect warming health without spelunking Railway logs:

- `lintpdf:tile-warm-events:{tenant_id}` — per-tenant list, capped at 500, 7-day TTL.
- `lintpdf:tile-warm-events:_all` — global list across every tenant, same cap + TTL.

Event payload (identical to the structured log emitted alongside):

```json
{
  "event": "tile_warm.complete",
  "job_id": "…",
  "tenant_id": "…",
  "page_count": 20,
  "dpi": 150,
  "thumbnails": true,
  "duration_s": 12.4,
  "error": null,
  "recorded_at": "2026-04-14T10:22:25.441Z"
}
```

Three super-admin endpoints expose the data (all require the `X-Admin-Key` header):

| Endpoint | Description |
|---|---|
| `GET /api/v1/admin/tile-warming/events?tenant_id=&limit=` | Last N events newest-first. Omit `tenant_id` for the global feed; `limit` clamps to 1..500 (default 100). |
| `GET /api/v1/admin/tile-warming/summary?since_hours=` | Aggregates over the last `since_hours` (1..168, default 24): total completes/failures, p50/p95/p99 duration, per-tenant breakdown, top 5 error messages. |
| `GET /api/v1/admin/tile-warming/jobs/{job_id}` | Current Redis status hash for the job plus the subset of `_all` events that match. |

When Redis is not configured every endpoint returns `{"events": [], "status": "no_redis"}` (or the per-response equivalent) with HTTP 200 so callers can render an informational banner instead of an error. Structured `tile_warm.*` log lines continue to emit regardless — Redis persistence is additive.

The super-admin dashboard at `/dashboard/admin/warming` polls `/summary` and `/events` every 5 s and surfaces a summary strip, per-tenant health table, top error messages, and a filterable live event feed.

## Counting and billing

Each capability fill-in counts as one analyzer invocation against your plan. Typical cost is one-fifth to one-tenth of a full engine run, depending on the capability:

- `findings` fill-in ≈ one full engine run (it *is* a full engine run).
- `separations`, `tac`, `fonts`, `images` — one analyzer each, billed at the single-analyzer rate.

Check your plan's analyzer-invocation allowance at [Pricing](/pricing).

## Related

- [Preflight Modes](/docs/preflight-modes)
- [External Preflight Imports](/docs/external-imports)
- [Viewer-Only Submissions](/docs/viewer-only-mode)
- [Share Links](/docs/share-links)
