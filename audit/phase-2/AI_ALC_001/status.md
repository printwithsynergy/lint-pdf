# AI_ALC_001 / AI_ALC_002 — Alcohol labeling — DONE

## Summary

Auto-detects alcohol labels via ABV pattern or product-class keyword,
then verifies TTB / EU required elements:

- ABV declaration
- TTB Government Warning (US)
- Country of origin / "Product of"

Aggregates missing items into one AI_ALC_001 (warning).

AI_ALC_002 (advisory) flags ABV format issues — implausible
percentages, non-preferred unit text, decimal precision > 1.

## Files

- `packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/alcohol.py`
  — body now real, tier flipped from `gpu` → `cpu`,
  `credits_per_run=1`.
- `packages/engine/tests/analyzers/test_regulatory_batch9b.py`
  (`TestAlcohol`).

## Verification

`uv run pytest tests/analyzers/test_regulatory_batch9b.py::TestAlcohol`
→ 4/4 green.

Silent on non-alcohol content. Complete-label test silent. Missing-
elements test fires AI_ALC_001 with the expected `missing_elements`
list. Format test fires AI_ALC_002.
