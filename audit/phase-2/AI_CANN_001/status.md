# AI_CANN_001 / AI_CANN_002 — Cannabis labeling — DONE

## Summary

Auto-detects cannabis packaging via THC/CBD potency phrase or
cannabis-class keyword, then verifies the multi-state common
requirements:

- "Keep out of reach of children"
- Cannabis warning symbol declaration
- Potency declaration

Aggregates missing into AI_CANN_001 (warning).

AI_CANN_002 (advisory) flags per-serving doses above the CO 10 mg
threshold and arithmetic mismatches between declared per-serving ×
servings and declared total mg.

## Files

- `packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/cannabis.py`
  — body now real, tier flipped from `gpu` → `cpu`,
  `credits_per_run=1`.
- `packages/engine/tests/analyzers/test_regulatory_batch9b.py`
  (`TestCannabis`).

## Verification

`uv run pytest tests/analyzers/test_regulatory_batch9b.py::TestCannabis`
→ 4/4 green.

Silent on non-cannabis content. Complete-label test silent. Missing-
elements test fires AI_CANN_001. Arithmetic-mismatch test fires
AI_CANN_002.
