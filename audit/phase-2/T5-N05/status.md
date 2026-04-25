# T5-N05 — Wine / spirits warning statements — DONE (Batch 11)

`AI_ALC_003` (warning for wine, advisory for spirits) emits when
the broader `AI_ALC_001` triggers and additional wine/spirits-
specific TTB 27 CFR 4 / 5 + EU 1308/2013 issues apply:

Wine (TTB 27 CFR 4 / EU 1308/2013):
- Missing `Contains Sulfites` / `Contains Sulphites` (TTB
  27 CFR 4.32(e), required when SO2 > 10ppm).
- `Estate Bottled` claim without an appellation (TTB 4.26).
- `Vintage YYYY` claim without an appellation (TTB 4.27).

Spirits (TTB 27 CFR 5):
- Missing proof statement (advisory — ABV alone is allowed but
  proof is the historical norm).

Files:
- `packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/alcohol.py`
  — extends the existing `AlcoholLabelingAnalyzer` with new
  pattern set (`_WINE_KEYWORDS`, `_SPIRITS_KEYWORDS`,
  `_SULFITES_PATTERN`, `_PROOF_PATTERN`,
  `_ESTATE_BOTTLED_PATTERN`, `_VINTAGE_PATTERN`,
  `_APPELLATION_PATTERN`) and emits `AI_ALC_003`.
- `packages/engine/tests/analyzers/test_batch11.py` — 5 cases.
