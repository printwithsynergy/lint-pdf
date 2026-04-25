# T2-GWG01 — Full GWG 2022 commercial-print profile set

## Scope

Ship 30 GWG 2022 commercial-print profiles covering:

- Sheet-fed offset (5 stocks: coated, light coated, uncoated,
  text/bond, board)
- Web-offset heatset (5 stocks: coated, improved, MFC, SNP, uncoated)
- Web-offset coldset (3 stocks: SNP, newsprint, improved-news)
- Magazine offset (3 stocks: glossy, matte, supplement-LWC)
- Newspaper (2 stocks: standard newsprint, improved newsprint)
- Digital print (6 variants: toner / inkjet × coated / uncoated /
  board / on-demand)
- Large format / sign-display (6 variants: photo, fine art, banner,
  POS, billboard, vehicle wrap)

Total **30**.

## Approach

Variants are template-driven, not hand-edited:

- One generator script —
  `packages/engine/scripts/generate_gwg_profiles.py` — walks a
  `(SubstrateSpec × WorkflowSpec)` matrix and writes one JSON per
  combination. Stable JSON output (deterministic key order, trailing
  newline) so re-runs are no-ops when the matrix hasn't changed.
- Threshold deltas live in the matrix (`tac_limit`, `min_dpi`,
  `min_bleed_mm`, `hairline_threshold`); everything else inherits
  from a shared base profile (PDF/X-4 conformance, GWG enable list,
  the standard `LPDF_FONT_016/017` disables).
- The script supports `--check` mode that exits non-zero when the
  on-disk profiles drift from the generator output, suitable for CI
  parity gating.

## Files emitted

`packages/engine/src/lintpdf/profiles/builtin/gwg-2022-*.json` —
one file per combination, e.g.
`gwg-2022-sheetfed-offset-coated.json`,
`gwg-2022-web-heatset-mfc.json`, etc. Profile id (the file stem) is
how the existing registry / API picks them up; no other wiring
needed.

## Why a generator instead of 30 hand-edited files

- The legitimate variation across GWG-2022 commercial print is in
  ~4 thresholds. Hand-writing 30 files is 26 copies of the same
  shape, which drifts the moment one substrate's threshold
  changes.
- The `--check` mode lets CI catch the "edited the JSON forgot to
  re-run the script" footgun.
- Leaves the legacy 6 GWG-2022 files (`gwg-2022-coated-offset.json`,
  etc.) in place for back-compat with existing tenant configs that
  reference them — the new files complement, they don't replace.

## Verification

```sh
uv run python scripts/generate_gwg_profiles.py --check
```

→ exits 0 with `GWG profiles up-to-date (45 files)` when in sync.

`pytest tests/profiles/test_registry.py` continues to pass — the
legacy profile ids are still resolvable.
