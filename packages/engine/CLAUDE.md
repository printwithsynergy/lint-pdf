# Engine — Agent Notes

## Viewer capabilities

When you add an analyzer that computes a **data_capability** (separations, TAC, fonts, images, layers, or anything newly exposed to the viewer), you MUST:

1. Register the capability name in the viewer capability map (see `lintpdf/api/routes/viewer.py` — the `get_viewer_config` handler and the `POST .../capabilities/{capability}` on-demand endpoint).
2. Add the flag to `FindingResponse` / `JobResponse` surfaces if the capability implies a new per-finding field.
3. Document it in `packages/web/src/content/docs/viewer-capabilities.md` (fillable table + analyzer description) and the `ApiViewerSection.tsx` config FieldTable.
4. If the capability is **not** on-demand-fillable (e.g., `layers` — PDF optional-content groups can only be discovered at ingest), state that explicitly in both places. Silent "load button does nothing" is the worst UX.

Single rule: the viewer capability registry and the docs stay 1:1. If you only change one, reviewers should bounce the PR.

## External parsers

Each `external_format` enum value (`pitstop_xml`, `callas_json`, `callas_xml`, `acrobat_xml`, `lintpdf_json`) has exactly one parser under `lintpdf/imports/` and exactly one sample in `docs/examples/`. Adding a new built-in format means all three:

1. New parser under `lintpdf/imports/<vendor>.py`, registered in `lintpdf/imports/detect.py`.
2. New `docs/examples/<vendor>-report.{xml,json}` sample that round-trips through the parser cleanly.
3. New row in the `external_format` enum appendix (`ApiEnumsSection.tsx`) and the supported-formats table in `external-imports.md`.

## No format autopsies

Parsers must fail cleanly with a `422` carrying the field path that broke. Never swallow a parse error and emit zero findings — the caller will assume their report was clean.
