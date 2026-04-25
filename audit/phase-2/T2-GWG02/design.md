# T2-GWG02 — GWG 2022 packaging profile pack

## Scope

Ship 15 GWG 2022 packaging profiles covering offset / flexo /
gravure × substrate combinations:

- Folding carton (3 variants: offset, digital, flexo)
- Corrugated (3 variants: post-print, pre-print, litho-laminate)
- Flexo label (3 variants: paper, film, clear)
- Flexo film (3 variants: PE, PP, laminate)
- Gravure (3 variants: paper, film, foil)

Total **15**.

## Approach

Same template generator as T2-GWG01 (`generate_gwg_profiles.py`,
`_packaging()` matrix). Substrate base specs encode realistic
threshold ranges:

- Folding carton: TAC 320 %, 300 dpi, 3 mm bleed, 0.30 hairline.
- Corrugated: TAC 260 %, 200 dpi, 5 mm bleed, 0.50 hairline.
- Flexo label: TAC 280 %, 240 dpi, 3 mm bleed, 0.40 hairline.
- Flexo film: TAC 260 %, 200 dpi, 5 mm bleed, 0.50 hairline.
- Gravure: TAC 300 %, 300 dpi, 3 mm bleed, 0.30 hairline.

Per-variant overrides handle film vs paper, clear-on-clear (which
needs a white underprint and slightly tighter TAC), and laminate /
foil cases.

## Files emitted

`packages/engine/src/lintpdf/profiles/builtin/gwg-2022-packaging-*.json`
— 15 new files. Legacy `gwg-2022-packaging.json` stays for
back-compat.

## Verification

`uv run python scripts/generate_gwg_profiles.py --check` —
exits 0 with both T2-GWG01 (30) and T2-GWG02 (15) variants
in sync.

## Out of scope

- Substrate-specific spot-ink configurations (white ink layers,
  hot-foil stamping). These layer atop the shared GWG base and
  belong in tenant-level brand specs, not the platform profile.
