# T3-D03 — Dieline overprint (not knockout)

## What the check detects

Flags PDFs where the dieline Separation is set to **knockout** instead
of **overprint**. When a cutter spot is set to knockout, painting the
dieline punches holes through underlying inks — the finished print
has a stripe of white along every cut line, which no customer ever
wants.

New inspection_id: `LPDF_DIE_KNOCKOUT`. Severity **warning**.

## Input / preconditions

- `DielineResult.spot_name` is populated (source in `{"name", "vision"}`).
- `pdf_bytes` — re-open for graphics-state inspection.

## Detection

Walk the page-1 content stream. For each operator that paints using
the dieline spot (`SC`/`SCN` set-stroke-colour followed by a stroke
operator like `S`, `b`, `B`), inspect the graphics state at that
moment:

1. `OP` (stroking overprint) boolean — default `false` in PDF
2. `OPM` (overprint mode) integer — 0 or 1

For a proper dieline:
- `OP=true` — strokes in the dieline spot overprint underlying inks.
- `OPM=1` — the non-zero-component overprint mode (preserves underlying inks everywhere the dieline spot is 0%).

If `OP=false` at any dieline paint operator, emit the finding.

## Output

```
Finding(
    inspection_id="LPDF_DIE_KNOCKOUT",
    severity=Severity.WARNING,
    message="Dieline 'CutContour' is set to knockout (stroke OP=false) — underlying inks will have gaps along cut lines",
    page_num=1,
    details={
        "spot_name": "CutContour",
        "op_value": false,
        "opm_value": 0,
        "first_violation_op_idx": N,
    },
    iso_clause="ISO 32000-2:2020 11.7 / ISO 19593-1 §5.3",
)
```

## Remediation guidance

> In Illustrator / InDesign, select the dieline layer, open
> Window > Attributes, and tick "Overprint Stroke". Re-export.
> For CorelDRAW, use Tools > Color Management > Spot Colors.
> The dieline should overprint so underlying inks remain
> continuous along the cut.

## Read-only

Confirmed. Graphics-state inspection reads the current `OP`/`OPM`
values via pikepdf's content-stream walker. No writes.

## Profiles

Universal warning — applies to every packaging / flexo / gravure /
offset profile.

## Edge cases

1. **No dieline detected** → silent.
2. **Dieline present but never stroked** (e.g. image-only
   representation) → silent; no violation possible.
3. **`OP` set via ExtGState dictionary** (the more common path than
   inline `gs` operator) — the content-stream walker resolves the
   current graphics state, so ExtGState-set `OP` is visible.
4. **Mixed OP state across operators** (some painted with OP=true,
   some with OP=false) — fire once with the first violation index.
   Most PDFs with the bug have a single global gstate setting.

## Q&A gate

No open questions.
