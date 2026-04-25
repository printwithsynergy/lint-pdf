# T3-D01 — Content on dieline layer (OCG-based)

## What the check detects

Flags paint operators executed inside a marked-content block tagged
with a dieline-named OCG where the operator's colour is NOT the
dieline spot. A clean dieline layer holds only dieline-coloured
strokes; ANY non-dieline content on that layer is accidental
placement that follows the layer on/off state in the viewer and
typically prints on the cutter plate by mistake.

New inspection_id: `LPDF_DIE_LAYER_CONTENT`. Severity **warning**.

## Scope simplification

The playbook entry names "per-separation raster compare" as the
full-scope detection approach. This implementation ships the
**OCG-based** detection first — detects ~80% of the real-world
problem cases (designers drop an image onto the Dieline layer in
Illustrator) without needing Ghostscript-rendered separation plates.

Raster-compare extension is tracked as a follow-up
(`audit/phase-2/followups.md`) once pixel-composited detection
becomes cheap enough to run inside the preflight hot path.

## Detection

Extend the existing `dieline_quality._walk_page_one()` with BDC /
EMC marked-content tracking:

1. `BDC /OC /Resource` opens a marked-content block tagged with the
   named OCG referenced by `/Resource`. Look up the OCG via
   `/Resources /Properties /<Resource>` to get the OCG dict, then
   read its `/Name`.
2. Maintain `ocg_stack: list[str]` of currently-open dieline-named
   OCGs.
3. For each paint operator, when `ocg_stack` is non-empty AND the
   current stroke or fill colour is NOT the dieline spot, count it.
4. `EMC` pops the top entry.

Dieline-name matching reuses the existing `_name_matches()` helper
from `dieline.py` — accepts "dieline", "cutcontour", "die line",
"cut", "crease", "perf", etc. (case-insensitive, multi-token).

## Output

```
Finding(
    inspection_id="LPDF_DIE_LAYER_CONTENT",
    severity=Severity.WARNING,
    message="Dieline layer 'Dieline' contains N non-dieline paint operation(s) on page 1 — artwork on the cutter plate",
    details={
        "ocg_names": ["Dieline"],
        "foreign_paint_count": N,
        "first_violation_op_idx": M,
    },
)
```

## Read-only

Confirmed. BDC/EMC walker reads content-stream tokens; no writes.

## Profile membership

Universal warning — packaging / flexo / gravure all share the
"clean cutter plate" convention.

## Edge cases

1. No dieline OCG → silent (precondition).
2. Dieline OCG with only dieline-spot content → silent (normal).
3. Form XObject invoked inside a dieline OCG — same scope limit as
   T3-D02; the walker doesn't recurse into `Do` invocations.
4. Nested marked-content blocks — stack-tracked, one level per
   BDC/EMC pair.

## Q&A gate

No open questions.
