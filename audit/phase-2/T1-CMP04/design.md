# T1-CMP04 — JavaScript / action dictionaries present

## Status: already implemented

The gap-list entry maps cleanly to three existing inspection_ids
covering every flavour of JavaScript / action embedding:

| inspection_id | Trigger | Severity |
|---|---|---|
| `LPDF_STRUCT_001` | `/AA`, `/OpenAction`, or `/Names /JavaScript` dict at catalog level | error |
| `LPDF_STRUCT_008` | `/JS` or `/JavaScript` action anywhere in the catalog action chain | error |
| `LPDF_STRUCT_014` | Any non-JavaScript action (`/Launch`, `/GoTo`, `/URI`, etc.) | warning |

Code: `packages/engine/src/lintpdf/analyzers/structure.py:47-57, 150-185`.

## Why this design

Three distinct IDs (rather than one collapsed finding) because:

- Severity should differ by action class. JS is hard-blocked in print workflows (error); benign /GoTo navigation actions are informational (warning at most).
- Tenants can tune per class via the rules editor (disable /GoTo warnings while keeping JS errors).
- Reporting clarity — a split makes the "this PDF has 3 JavaScripts" vs "this PDF has 5 /Launch actions" distinction visible in the report.

This matches the approach Quincy approved for T1-I07 (split-per-mode), applied retroactively.

## Read-only

Confirmed. Catalog walks + action-chain inspection. No writes, no re-saves.

## Profiles

Present in every bundled profile's enabled pattern (`LPDF_*` / `LPDF_STRUCT_*`). PDF/X-1a through PDF/X-6 all treat the JS IDs as hard errors per ISO 15930-7 §6.2.8.

## Verification

`uv run pytest tests/analyzers/test_structure.py` — existing tests cover all three IDs. No new test scaffolding needed.

## Outcome

No code change. Gap-mapping corrected to `present`. `status.md` set to `verified`.
