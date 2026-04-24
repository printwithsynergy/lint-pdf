# T3-D10 — Varnish coverage validation (VarnishFree respect)

## What the check detects

Flags PDFs where a varnish / coating spot is painted inside a
region marked as VarnishFree — i.e., a "no coating here" directive
that the artwork ignored.

Common names for the mask spot: `VarnishFree`, `NoVarnish`,
`CoatingFree`, `NoCoating`. Common names for the varnish spot
itself: `Varnish`, `UV Varnish`, `AquaCoat`, `AQ`, `Gloss`, `Matte`,
`SpotUV`, `SoftTouch`.

New inspection_id: `LPDF_DIE_VARNISH_COLLISION`. Severity
**warning**.

## Scope simplification

Full implementation: render each spot's plate, binary-AND, flag
overlap area. Ships-later scope.

**First-cut scope**: spot-name presence + content-stream paint
bbox overlap check.

1. Walk page-1 resources for Separation colour spaces matching
   either list.
2. If BOTH a varnish-spot AND a VarnishFree-spot are present:
   - Collect paint bboxes for each.
   - Compute intersection area (axis-aligned).
   - If intersection area > 50 pt² (matches T3-D15 tiny-threshold),
     emit the finding.
3. If only one kind is present, silent.

## Output

```
Finding(
    inspection_id="LPDF_DIE_VARNISH_COLLISION",
    severity=Severity.WARNING,
    message="Varnish spot 'UV Varnish' overlaps VarnishFree region by ~3.2 cm²",
    details={
        "varnish_spot": "UV Varnish",
        "varnish_free_spot": "VarnishFree",
        "overlap_area_pts2": X,
        "overlap_area_cm2": Y,
        "intersection_bbox_pts": [x0, y0, x1, y1],
    },
)
```

## Spot-name matching

Two closed lexical sets used (not heuristic / not AI-assisted,
matches the existing `_name_matches` pattern in dieline.py):

```
VARNISH_SPOTS = {"varnish", "uv varnish", "uv", "aquacoat", "aq",
                 "gloss", "matte", "spotuv", "softtouch", "coating"}
VARNISH_FREE_SPOTS = {"varnishfree", "varnish free", "novarnish",
                      "no varnish", "coatingfree", "coating free",
                      "nocoating", "no coating"}
```

Normalisation: lowercase, strip leading `/`, collapse
whitespace/hyphens/underscores. Matches `SpotUV`, `spot uv`,
`spot-uv`, etc.

## Read-only

Confirmed. Walks Separation colour-spaces and content-stream
bboxes; no writes.

## Profile membership

Universal warning across packaging profiles (universal enable is
safe — the check silently no-ops on non-packaging PDFs because
VarnishFree spots are essentially packaging-only).

## Edge cases

1. No varnish spot in the PDF → silent.
2. VarnishFree spot present but no varnish → silent (no way to
   collide).
3. Varnish + VarnishFree both present but non-overlapping → silent.
4. Overlap area < 50 pt² → silent (tiny overlap likely a
   rounding / registration artefact).

## Q&A gate

No open questions.
