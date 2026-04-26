# Path A — Marketing Fix Scope (Wave A T3 + Wave B T1 + EPM Core)

**Goal:** Honestly cross 500+ user-facing checks
**Date:** 2026-04-26
**Status:** scoped; first exemplar shipping in-session, remainder iterative

## Net-new check budget

| Wave | Checks | Estimated EM (with docs parity) |
|------|--------|---------------------------------|
| Wave B T1 catch-up (P-03 + P-04) | 2 | 0.5 |
| Wave A T3 dieline wedge | 8 | 3.5 |
| Phase 2.EPM Core | 22 (8 disqualifiers + 14 soft signals) | 2.5 |
| **Total** | **32** | **~6.5 EM** |

421 baseline + 32 = **453**. To cross 500 honestly, the next 47 IDs come
from Wave D T2 parity (mostly LA-* line-art and P-* page geometry).

## Wave A T3 — 8 IDs to ship

Picked for high-value × low cost (each can lean on Tier-0 primitives we
just shipped). Each check needs analyzer + profile-manifest entry + markdown
docs + JSX docs + curl example per CLAUDE.md docs parity rule.

| v2 ID | Title | Tier-0 primitives consumed | Existing infra |
|-------|-------|----------------------------|----------------|
| D-01 | Dieline detection by spot name | `ink.is_spot()`, `ink.spot_name()` | `dieline.py` already detects |
| D-04 | Dieline detection by layer name pattern | `object_class` + OCG inspection | `dieline.py` |
| D-07 | Dieline knockout vs overprint | `ink.overprint_fill/stroke()` | `dieline_quality.py` (LPDF_DIE_KNOCKOUT) |
| D-08 | Dieline blend mode ≠ Normal | `transparency_stack.blend_mode()` | NEW |
| D-09 | Dieline opacity < 100% | `transparency_stack.alpha_constant()` | NEW |
| D-15 | Content extends beyond dieline | geometry bbox + dieline polygon | `dieline_quality.py` (LPDF_DIE_CONTENT_OUTSIDE) |
| P-30 | Bleed beyond dieline | `page.bleed_box()` + dieline path | NEW |
| F-32 | Text on dieline path | `text.*` + dieline detection | NEW |

Three of these (D-01, D-07, D-15) already have analyzer code that emits
`LPDF_*` codes — we just need to register the v2 ID alongside the
`LPDF_*` code in `reports/check_names.py` and the profile manifests.
Five (D-04, D-08, D-09, P-30, F-32) need new analyzer modules.

## Wave B T1 — 2 IDs to ship

| v2 ID | Title | Approach |
|-------|-------|----------|
| P-03 | TrimBox missing | New `page_geometry_box.py` analyzer; `page.trim_box()` returns the same as crop_box → flag |
| P-04 | BleedBox missing | Same module; `page.bleed_box()` returns crop_box → flag |

Both emit `LPDF_PAGE_TRIMBOX_MISSING` / `LPDF_PAGE_BLEEDBOX_MISSING`.

## EPM Core — 22 IDs

Out of scope for this scope doc. Lives in `packages/engine/src/lintpdf/analyzers/epm_analyzer.py`
which currently has stubs. Needs separate design doc.

## Per-ID delivery checklist

Every shipped ID needs ALL of:
1. Analyzer emits `LPDF_*` finding with `v2_id` set
2. `reports/check_names.py` `CheckInfo(v2_ids=("D-08",))` added
3. Profile manifest entry in `packages/engine/src/lintpdf/profiles/builtin/*.json`
4. Markdown doc in `packages/web/src/content/docs/checks/<id>.md` plus
   registration in `packages/web/src/lib/doc-sections.ts`
5. JSX entry in `packages/web/src/components/docs/pages/ChecksPage.tsx`
6. Example payload `docs/examples/check-<id>.json` if user-facing
7. Tests (positive + negative)

## In-session deliverable

This session ships **one exemplar end-to-end** so the next session has
a working pattern: D-08 (Dieline blend mode ≠ Normal). Choice driven
by:
- Uses primitives we just shipped (`transparency_stack.blend_mode()`)
- Net-new code (no overlap with existing dieline_quality.py)
- Self-contained — no cross-cutting profile changes needed
