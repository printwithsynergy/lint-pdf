# T5-N04 — Tobacco warning panel-area — DONE

`LPDF_TOBACCO_WARNING_AREA` (warning) fires on tobacco / cigarette
artwork (auto-detected via tobacco keywords + warning phrases)
when the warning text's bounding region covers less than the
configured fraction of the page surface. Default threshold 30 %;
operators tighten to 50 % (FDA), 65 % (EU TPD2), or 75 %
(AU/NZ) via `TenantAIConfig.tobacco_warning_min_fraction`.

Bbox derives from the union of text events ≥ 8 pt on the page,
which approximates the principal display panel reasonably well
for typical pack faces.

Files:
- `packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/tobacco.py`
  (new analyzer registered via `@register_ai_analyzer`).
- `packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/__init__.py`
  — exports `TobaccoWarningAnalyzer`.
- `packages/engine/tests/analyzers/test_batch10b.py` — 2 cases.
