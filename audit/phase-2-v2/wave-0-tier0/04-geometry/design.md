# Tier-0 Batch 04 — Geometry / page-box / path / transform predicates

**Wave:** 0 (Tier-0 primitives)
**Category:** Geometry
**Primitive count:** 23
**EM estimate:** 0.45
**Design date:** 2026-04-25

Per universe enumeration §4.4. Largest batch so far; one module
(`primitives/geometry.py`) with internal sections to keep navigation easy.

## Primitives in this batch

### Box accessors (5)
- `media_box(page)` `crop_box(page)` `trim_box(page)` `bleed_box(page)` `art_box(page)` — return `(x0,y0,x1,y1)` tuple or None

### Box predicates (2)
- `box_contains(outer, inner, *, eps=0.0)` — True iff inner ⊆ outer (with optional float-eps tolerance)
- `box_equals(a, b, *, eps=0.0)` — True iff identical within tolerance

### Object bbox / containment (4)
- `obj_bbox(obj)` — `(x0,y0,x1,y1)` if discoverable from operands or pre-computed
- `obj_intersects(obj, box)` — True iff obj's bbox intersects the box
- `obj_outside(obj, box)` — True iff obj's bbox is entirely outside
- `obj_within(obj, box, *, margin=0.0)` — True iff obj's bbox is fully within the box minus margin

### Path predicates (7)
- `path_is_closed(path)` — last op is `h` / `s` / `b` / `b*`
- `path_self_intersects(path)` — segments cross (uses Shapely if installed; bbox-overlap heuristic otherwise)
- `path_node_count(path)` — count of `m`/`l`/`c`/`v`/`y`/`re`/`h` ops
- `path_is_dashed(state)` — True if graphics state has non-empty dash array
- `path_dash_phase(state)` — float dash phase or 0.0
- `path_miter_limit(state)` — float miter limit
- `path_line_cap(state)` — int 0/1/2 (butt/round/square)

### Transform predicates (5)
- `obj_ctm(obj)` — `(a,b,c,d,e,f)` 6-tuple or None
- `obj_rotation(obj)` — degrees in [0, 360); 0 if no rotation
- `obj_scale_xy(obj)` — `(sx, sy)` tuple from CTM
- `obj_is_mirrored(obj)` — True iff CTM determinant < 0
- `obj_is_skewed(obj)` — True iff CTM `b != 0` or `c != 0` (off-diagonals)

## Input shapes

- **`page`:** `lintpdf.parser.PdfPage` instance (already exposes `media_box` etc.)
- **`box`:** `(x0, y0, x1, y1)` 4-tuple of floats
- **`obj`:** dict with keys `bbox` / `ctm` / etc., or any object with attribute access
- **`path`:** list of `(operator, operands)` tuples (the construction sequence terminated by a paint op)
- **`state`:** graphics state dict with keys `dash_array`, `dash_phase`, `miter_limit`, `line_cap`

## POC migration target

`dieline_quality.py` has a 6-tuple `compose()` matrix-multiply helper for
CTM composition. Migrate one usage to call `obj_rotation` / `obj_scale_xy`
where applicable.

## Read-only / no-stub confirmation

- ✓ No PDF mutation
- ✓ Pure-function predicates
- ✓ Tests pass before commit
- ✓ ruff + mypy clean
