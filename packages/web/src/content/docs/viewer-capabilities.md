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
