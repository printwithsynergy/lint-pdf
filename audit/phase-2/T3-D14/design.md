# T3-D14 — Braille area (ISO 19593-1) integrity

## What the check detects

Pharma packaging uses an embossed / printed Braille spot for
accessibility. ISO 19593-1 defines the Braille processing step;
WHO + EU 92/27 mandate dot dimensions (1.4-1.6mm diameter, 2.5mm
spacing) and clearance from other inks (ink in the Braille area
fills in the dots → unreadable).

New inspection_id: `LPDF_BRAILLE_INTEGRITY`. Severity **warning**.

## Scope simplification

The full spec covers dot diameter, spacing, height, and reflectance.
This first-cut implementation ships **two signals**:

1. **Detection**: Braille spot present? (Names: `Braille`,
   `BrailleStep`, `Braille1`, `Marburg Medium` — closed list.)
2. **Clearance**: Does any non-Braille ink paint inside the Braille
   bbox area? Inks inside Braille zones fill in the dots.

Dot-dimension verification (1.4-1.6mm diameter) is deferred — it
needs vector path geometry beyond the current walker.

## Preconditions

- Braille spot detected via name match in resource colour spaces.
- The dieline_quality walker has captured Braille-spot paint bboxes
  (dot positions).

## Detection

Extend the walker:

1. Add `_is_braille_name()` matcher with the closed list above.
2. Track Braille-spot paint bboxes separately.
3. Track non-Braille paint bboxes whose centre falls inside the
   Braille union bbox.
4. Emit two findings:
   - **Always**: presence advisory listing dot count + total area
     (informational; "Braille detected, N dots, ~X cm²").
   - **Conditional**: clearance violation when ≥1 non-Braille paint
     bbox sits inside the Braille zone.

Combined into a single LPDF_BRAILLE_INTEGRITY emission with
`details.has_clearance_violation` boolean. Severity escalates to
warning when violation present; advisory when only presence is
informational.

## Output

```
Finding(
    inspection_id="LPDF_BRAILLE_INTEGRITY",
    severity=Severity.WARNING,  # or ADVISORY if no violation
    message="Braille zone contains 3 non-Braille paint operation(s) — dots will fill in",
    details={
        "braille_spot": "Braille",
        "dot_count": 24,
        "braille_area_cm2": 3.4,
        "has_clearance_violation": True,
        "violation_count": 3,
    },
)
```

## Read-only / profile

Confirmed read-only. Pharma niche — disabled by default in non-
pharma profiles. Bundled `pdfx1a-magazine-ads` etc. don't enable it
unless the tenant adds Braille spots to the artwork.

## Q&A gate

No open questions.
