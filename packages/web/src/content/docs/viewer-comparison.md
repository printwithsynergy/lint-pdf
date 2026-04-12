---
title: "Viewer File Comparison"
description: "Open two jobs side-by-side and render a per-page diff heatmap."
section: "viewer-workflow"
order: 41
---

# Viewer File Comparison

The viewer's compare mode takes two existing jobs and renders a pixel-level diff heatmap for each page. Typical uses: versioning (proof-of-change against last-approved), printer-to-designer round-trip QA, and regression checks after a ripping or trapping stage.

## Create a comparison

Both jobs must already be complete. They don't need to be in the same mode — you can compare an `engine`-mode job against a `minimal`-mode job — but they must have the same page count.

```bash
curl -X POST https://api.lintpdf.com/api/v1/viewer/compare \
  -H "Authorization: Bearer lpdf_live_..." \
  -H "Content-Type: application/json" \
  -d '{
    "job_id_1": "d4e5f6a7-...",
    "job_id_2": "a1b2c3d4-..."
  }'
```

Response:

```json
{
  "comparison_id": "cmp_8e7d6c5b4a3f",
  "job_1": { "job_id": "d4e5f6a7-...", "file_name": "brochure-v1.pdf" },
  "job_2": { "job_id": "a1b2c3d4-...", "file_name": "brochure-v2.pdf" },
  "page_count": 12
}
```

Errors:

- `400` — jobs have different page counts.
- `403` — one or both jobs are not owned by your tenant.
- `404` — one or both jobs don't exist or are not complete.

## Fetch a diff page

```bash
curl "https://api.lintpdf.com/api/v1/viewer/compare/{comparison_id}/pages/{page_num}/diff?dpi=150" \
  -H "Authorization: Bearer lpdf_live_..." \
  --output page-2-diff.png
```

Returns an RGBA PNG. Query param `dpi` defaults to 150, accepted range 72–600.

## Heatmap colors

| Color | Meaning |
|---|---|
| Transparent | Pixels match within a small ΔE tolerance. |
| Green | Ink present in `job_1` but missing in `job_2`. |
| Red | Ink present in `job_2` but missing in `job_1`. |
| Amber | Both sides carry ink but the color differs beyond tolerance. |

The alpha channel is proportional to the magnitude of the difference — faint tints for borderline pixels, full opacity for large deviations. Compose the diff PNG on top of a rendered page tile for the interactive experience:

```javascript
const tile = await fetch(
  `/api/v1/viewer/jobs/${jobId1}/pages/${pageNum}/tile?dpi=150`,
);
const diff = await fetch(
  `/api/v1/viewer/compare/${comparisonId}/pages/${pageNum}/diff?dpi=150`,
);
// Draw tile, then diff with globalAlpha=0.7
```

## Lifetime

Comparisons expire 24 hours after creation. The resulting diff tiles are cached in-flight; once the comparison expires the diff endpoints return `410 Gone`. Re-create the comparison to regenerate.

## Related

- [Viewer Capabilities & On-Demand Fill-In](/docs/viewer-capabilities)
- [Approval Verdicts](/docs/viewer-verdict)
