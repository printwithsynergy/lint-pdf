---
title: "EPM Candidacy Verdict"
description: "Tier verdict for HP's CMY-only Extended Print Mode — rejection drivers, advisories, and IndiChrome upsell hint."
section: "preflight"
order: 80
---

# EPM Candidacy Verdict

HP's **Extended Print Mode** (EPM) is a CMY-only press path that skips the K plate to gain throughput. EPM works for a wide range of jobs but breaks on certain content (rich blacks, tiny non-K text, deep-coverage K fills, mixed substrates). LintPDF scores every job against the 16 `LPDF_EPM_*_REJECT` codes plus the legacy `LPDF_EPM_001..018` set and produces a single tier verdict.

## Tiers

| Tier | Meaning |
|---|---|
| `pass` | No EPM-related findings. Job runs cleanly on the EPM path. |
| `pass_with_advisory` | Tier-C advisory findings only — verdict is still PASS but operators should review. |
| `marginal` | Exactly one Tier-B soft-rejection finding fired. Treat as borderline. |
| `reject` | Any Tier-A finding, or two or more Tier-B findings — job is **not** an EPM candidate. |

## Three-tier code structure

| Tier | Behavior | Example codes |
|---|---|---|
| **A — hard reject** | Single occurrence rejects | `LPDF_EPM_GAMUT_OUT_REJECT`, `LPDF_EPM_K_COVERAGE_REJECT`, `LPDF_EPM_RICH_BLACK_REJECT`, `LPDF_EPM_SUBSTRATE_REJECT`, `LPDF_EPM_TEXT_SIZE_REJECT` |
| **B — soft reject** | Single → `marginal`, two+ → `reject` | `LPDF_EPM_PROCESS_COUNT_REJECT`, `LPDF_EPM_BLEED_REJECT`, `LPDF_EPM_PAGE_COUNT_REJECT`, `LPDF_EPM_IMAGE_RES_REJECT`, `LPDF_EPM_TRIM_REJECT` |
| **C — advisory** | Inform without changing tier | `LPDF_EPM_SPOT_COUNT_REJECT`, `LPDF_EPM_FEATURE_SIZE_REJECT`, `LPDF_EPM_MIXED_SPACES_REJECT`, `LPDF_EPM_TRAPPING_REJECT`, `LPDF_EPM_TRIM_BLEED_REJECT`, `LPDF_EPM_PAGE_GEOM_REJECT` |

## Endpoint

```
GET /api/v1/jobs/{job_id}/epm
Authorization: Bearer lpdf_live_...
```

```json
{
  "job_id": "abc",
  "tier": "marginal",
  "rejection_drivers": ["LPDF_EPM_BLEED_REJECT"],
  "advisories": ["LPDF_EPM_TRAPPING_REJECT"],
  "recommends_indichrome": false,
  "legacy_codes_fired": [],
  "epm_findings_count": 2
}
```

## Inline on JobResponse

The verdict is also surfaced inline on `GET /api/v1/jobs/{id}` under `epm_verdict`. List endpoints (`GET /api/v1/jobs`) leave it `null` — scoring per row is skipped to keep list latency cheap.

```json
GET /api/v1/jobs/abc

{
  "job_id": "abc",
  "epm_verdict": { "tier": "marginal", … },
  "decisions_count": 1,
  …
}
```

## Where it shows up

- **Dashboard preflight report** — EPM verdict card pinned at the top with tier badge, rejection drivers, advisories, and IndiChrome hint.
- **HTML / PDF / JSON / annotated PDF reports** — EPM verdict header at the top of every artefact, plus a top-level `epm` block in the JSON.
- **Desktop** — verdict card on `ResultDetail` for completed jobs.
- **SDK + plugin + Postman** — same tenant-scoped endpoint, same shape.

## IndiChrome substrate hint

`recommends_indichrome: true` fires when at least one Tier-A finding is `LPDF_EPM_005`-shaped (saturated spot/Lab outside CMY gamut). HP's IndiChrome substrate widens the gamut enough to bring the color back into reach, so the dashboard surfaces an upsell card pointing the operator at the substrate change.

## Threshold tuning

EPM thresholds (rich-black recipe, TAC limits, ΔE budget) live in the per-tenant `epm_thresholds` ToggleOverride. See [Toggles](/docs/toggles) for how to override at TENANT, WORKFLOW, or CALL scope.
