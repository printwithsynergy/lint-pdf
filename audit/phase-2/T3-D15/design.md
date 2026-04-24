# T3-D15 — CutContour spot used as visual print content

## What the check detects

Flags PDFs where the dieline spot is used in a **fill** operation
(not just stroke). A proper dieline is a single-ink stroked outline
that the cutting machine follows — it should never appear as a
filled area. Filling with the dieline spot creates a solid coloured
area that the cutter will mistakenly follow as a massive closed
path, then the finished job is cut to pieces.

The canonical trigger is the **Canva export bug** (flagged `UNIQUE`
in the playbook): Canva lets users recolour shapes to any swatch
including imported spot colours, then exports those filled shapes
as dieline-spot fills. Zero other preflight engines catch this.

New inspection_id: `LPDF_DIE_AS_ART`. Severity **error** — this
always ruins production.

## Input / preconditions

- `DielineResult.spot_name` populated.
- `pdf_bytes` — content-stream walk.

## Detection

Walk the page-1 content stream. For each operator:

1. Track current non-stroke (fill) colour state. `sc`/`scn` lowercase
   are fill-colour setters; `SC`/`SCN` uppercase are stroke setters.
2. When a paint operator runs (`f`, `F`, `f*`, `B`, `B*`, `b`, `b*`),
   check if the CURRENT fill colour is the dieline spot. The `B`/`b`
   variants stroke AND fill — fill colour still matters.
3. Also flag when the filled area is large — vs a 1pt tick mark
   that's filled for rendering convenience. Threshold: area > 50 pt²
   (~ 6mm × 6mm patch). Below that, emit as advisory (likely
   intentional).

## Output

```
Finding(
    inspection_id="LPDF_DIE_AS_ART",
    severity=Severity.ERROR,
    message="Dieline spot 'CutContour' used as fill on page 1 (area ~ X cm²) — cutter will follow the filled region",
    page_num=1,
    details={
        "spot_name": "CutContour",
        "fill_area_pts2": X,
        "fill_area_cm2": X * 0.000124,
        "fill_operator_count": N,
        "first_violation_op_idx": M,
    },
    iso_clause="ISO 19593-1 §5.3 (Cutter Processing Step)",
)
```

## Remediation guidance

> The dieline spot `{spot_name}` is applied as a fill, not just a
> stroke. In the source file (likely Canva / Illustrator):
>   - Open the shape's swatch.
>   - Change the FILL colour to the intended print ink (Black or
>     CMYK / brand spot).
>   - Keep the stroke colour on the dieline spot if the shape
>     should still be cut.
>
> The dieline layer should carry zero filled shapes.

## Read-only

Confirmed. Content-stream walk inspects operators + graphics state.
No writes to the PDF.

## Profiles

Universal **error** across every profile. Catching the Canva export
bug is a marketing differentiator, not a niche preflight.

## Edge cases

1. **No dieline detected** → silent.
2. **Dieline used ONLY as stroke** (canonical case) → silent.
3. **Tiny filled elements** (area < 50pt²) → emit as advisory, not
   error. Matches the playbook "threshold" hint without suppressing.
4. **Rectangle with `re` then `B`** — `re` defines a path; `B`
   strokes AND fills. Track current fill colour; if it's the
   dieline spot, fire.
5. **Filled text in dieline spot** — the `Tj` operator uses the
   fill colour when rendering mode 0 (default). Covered by the
   same fill-colour check; text sits in a filled glyph outline.

## Q&A gate

No open questions.
