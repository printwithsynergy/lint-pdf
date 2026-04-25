# T2-GWG02 — Packaging profile pack — DONE

## Summary

15 packaging GWG 2022 profile JSONs emitted from the same generator
as T2-GWG01. Folding-carton, corrugated, flexo-label, flexo-film,
and gravure substrates × 3 variants each.

## Files

- `packages/engine/scripts/generate_gwg_profiles.py` —
  `_packaging()` matrix.
- `packages/engine/src/lintpdf/profiles/builtin/gwg-2022-packaging-*.json`
  — 15 new files. Legacy `gwg-2022-packaging.json` retained for
  back-compat.

## Verification

`uv run python scripts/generate_gwg_profiles.py --check` →
`GWG profiles up-to-date (45 files)`.
