# T1-STR04 — Page size matches expected

## What the check detects

Compares each page's effective trim dimensions (in mm) to a
tenant-declared expected product size. New ID `LPDF_BOX_010`,
severity warning.

Two new profile fields (`ThresholdConfig`):

- `expected_page_width_mm: float | None` — product width
- `expected_page_height_mm: float | None` — product height
- `expected_page_size_tolerance_mm: float = 0.5` — tolerance, PitStop-compatible default

Check is **disabled by default** — only fires when BOTH width + height
fields are set on the profile. Tenants who run a fixed-size workflow
(business cards, A4 letterhead, postcard, package die) opt in.

## Input

`document.pages[*].trim_box` (or `media_box` fallback) + the three new
profile fields. Uses `page.trim_box.x1 - x0` (not the `effective_width`
property, which uses crop box), because the product is defined by the
trim box, not the crop / media containing the bleed.

Rotation-aware: `page.rotate in (90, 270)` swaps width/height before
comparison.

UserUnit-aware: multiplies by `page.user_unit` before converting to mm.

## Orientation tolerance

The check accepts **either orientation** of the declared product. A
tenant declaring `210 × 297` (A4 portrait) won't get a finding on a
`297 × 210` A4 landscape page of the same product. Two matches are
computed per page:
- portrait: `|actual_w - exp_w| ≤ tol AND |actual_h - exp_h| ≤ tol`
- landscape: `|actual_w - exp_h| ≤ tol AND |actual_h - exp_w| ≤ tol`

If either passes, silent. Otherwise emit.

## Output shape

```
Finding(
    inspection_id="LPDF_BOX_010",
    severity=Severity.WARNING,
    message="Page 1 is 210.00x250.00mm, expected 210.00x297.00mm (+/- 0.5mm tolerance)",
    details={
        "actual_width_mm": 210.0,
        "actual_height_mm": 250.0,
        "expected_width_mm": 210.0,
        "expected_height_mm": 297.0,
        "tolerance_mm": 0.5,
    },
    iso_clause="ISO 15930-7:2010 6.2.4",
)
```

## Read-only

Confirmed. Reads page `trim_box` / `media_box` rectangles + three profile
fields. Emits findings. No pikepdf writes, no profile writes.

## Profile membership

Not set in any bundled profile (all absent → check never fires by
default). Tenants configure via rules editor JSON tab. Deferred follow-up
(`FUP-1` in followups.md): dedicated "expected page size" widget in the
Rules tab when the first threshold-editing pattern lands.

## Verification

`tests/analyzers/test_expected_page_size.py` — 11 cases:
- Disabled: both fields absent / only width / only height → silent
- Within tolerance: exact match, 0.3mm off default tolerance, landscape
  rotation accepted
- Out of range: 210x250 vs A4 fires, A3 vs A4 fires, tight tolerance
  catches what loose didn't
- Rotation: `/Rotate 90` page matches landscape-equivalent expected
- Integration: analyze() routes through the check

All pass.

## Outcome

New profile fields + new inspection_id + new test file (+176 LOC).
`status.md` set to `verified`.
