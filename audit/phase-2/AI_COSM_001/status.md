# AI_COSM_001 / AI_COSM_002 — Cosmetics labeling — DONE

## Summary

Auto-detects cosmetic labels via INCI ingredient header or cosmetic-
class keyword, then verifies EU 1223/2009 + FDA 21 CFR 701 required
elements:

- INCI ingredient list
- Net quantity
- PAO symbol (period-after-opening token, e.g. `12M`)
- Batch / lot code

Aggregates missing into AI_COSM_001 (warning).

AI_COSM_002 (advisory) flags INCI nomenclature issues — first non-
water ingredient (typical reorder violation) and excess lower-case
tokens (non-INCI nomenclature).

## Files

- `packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/cosmetics.py`
  — body now real, tier flipped from `gpu` → `cpu`,
  `credits_per_run=1`.
- `packages/engine/tests/analyzers/test_regulatory_batch9b.py`
  (`TestCosmetics`).

## Verification

`uv run pytest tests/analyzers/test_regulatory_batch9b.py::TestCosmetics`
→ 4/4 green.

Silent on non-cosmetic content. Complete-label test silent. Missing-
elements test fires AI_COSM_001. INCI-reorder test fires AI_COSM_002.
