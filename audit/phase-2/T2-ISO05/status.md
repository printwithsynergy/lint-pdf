# T2-ISO05 — ISO 19593-1 ProcessingSteps suggestion — DONE

## Summary

For every spot ink whose canonical category maps to an ISO 19593-1
ProcessingSteps group (Cutting / KissCutting / Folding / Perforating
/ White / Varnish / VarnishFree), the analyzer emits one
`LPDF_PSTEP_SUGGEST` advisory suggesting the operator wire the
matching `/ProcessingSteps /Group` entry.

Builds on the T3-D11 spot taxonomy (no second walker — same pikepdf
pass collects the spot names).

## Files

- `packages/engine/src/lintpdf/analyzers/spot_name_normaliser.py`
  — added `ISO_19593_GROUP_BY_CANONICAL` mapping table and
  `suggest_processing_steps()` function. Public API extended via
  `__all__`.
- `packages/engine/src/lintpdf/queue/tasks.py` — wires both
  `check_spot_naming` and `suggest_processing_steps` into the
  result-collection + DB-persistence paths so findings land in the
  job results JSON and the `JobFinding` rows.
- `packages/engine/src/lintpdf/reports/check_names.py` — registers
  `LPDF_PSTEP_SUGGEST` (advisory).
- `packages/engine/tests/analyzers/test_processing_steps_suggest.py`
  — 7 unit tests using pikepdf-built synthetic PDFs.

## Verification

`uv run pytest tests/analyzers/test_processing_steps_suggest.py`
→ 7/7 green. Tests cover empty input, no-spots, CutContour →
Cutting, KissCut → KissCutting, unknown spot silent, multi-spot
emits one each, and a contract test asserting every canonical
name has an ISO mapping.

## Catalog

`packages/app/lib/rules/check-catalog.json` regenerated to include
`LPDF_PSTEP_SUGGEST` after this batch.
