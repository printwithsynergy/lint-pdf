# T2-GWG01 — Commercial-print profile set — DONE

## Summary

30 commercial-print GWG 2022 profile JSONs emitted from the new
template generator at
`packages/engine/scripts/generate_gwg_profiles.py`. Covers sheet-fed
offset (5 variants), web heatset (5), web coldset (3), magazine (3),
newspaper (2), digital print (6), and large-format / sign-display
(6).

## Files

- `packages/engine/scripts/generate_gwg_profiles.py` (new) — driver
  with `_commercial_print()` matrix.
- `packages/engine/src/lintpdf/profiles/builtin/gwg-2022-*.json`
  — 30 new files (legacy 6 GWG-2022 files retained for back-compat).

## Verification

`uv run python scripts/generate_gwg_profiles.py --check` →
`GWG profiles up-to-date (45 files)`.

## Notes

Profile shape (PDF/X-4 conformance, LPDF_* + PDFX4-* enables, the
standard FONT_016/017 disables) is identical across variants;
substrate-specific deltas are confined to `tac_limit`, `min_dpi`,
`min_bleed_mm`, and `hairline_threshold`.
