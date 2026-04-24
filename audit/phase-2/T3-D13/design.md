# T3-D13 — Registration risk on fine vector details

## Status: already implemented

Two existing inspection_ids cover the full-scope "fine vector with
multi-ink content = registration risk" pattern that T3-D13 proposes:

| inspection_id | Trigger | Severity |
|---|---|:--:|
| `LPDF_STROKE_004` | Multi-ink stroke (>1 CMYK ink > 1%) with line width < 0.5pt | warning |
| `LPDF_STROKE_007` | Multi-ink stroke with line width in 0.5-1.0pt range | advisory |

Code: `packages/engine/src/lintpdf/analyzers/hairline.py:195-241`.

## Why this covers T3-D13

The playbook describes T3-D13 as "extend existing small-text-on-multi-sep to vectors." That's literally what the existing LPDF_STROKE_004/007 pair does:

- **Small**: line width threshold (default 0.5pt / 1.0pt).
- **Multi-sep**: `>1 non-zero CMYK ink component` check on the stroke colour.
- **Vectors**: fires on `PathPaintingEvent`, not `TextRenderedEvent`.
- **Registration risk**: exactly the finding semantics.

Splitting across two IDs (warning < 0.5pt, advisory 0.5-1.0pt) matches
the per-mode approach Quincy approved for T1-I07: tenants who want
stricter / looser control tune each severity band independently.

## What's NOT covered (future scope)

The existing emission is PER-STROKE — a page with 500 fine multi-ink
strokes produces 500 findings. A per-page aggregation pattern (like
WS-7's `LPDF_ADV_005` rollup) could cap the noise.

Tracked in `audit/phase-2/followups.md` as FUP-5 (post-Phase-2
polish — no action needed for Batch 6).

## Read-only / profile membership

Both existing checks are read-only (confirmed) and enabled in every
bundled profile via the default `LPDF_*` / `LPDF_STROKE_*` pattern.

## Outcome

No new code. Gap-mapping updated to `present`. `status.md` set to
`verified`.
