# Tier-0 Batch 05 — Stroke / fill predicates

**Wave:** 0 (Tier-0 primitives)
**Category:** Stroke / fill
**Primitive count:** 8
**EM estimate:** 0.20
**Design date:** 2026-04-25

Per universe enumeration §4.5.

## Primitives

| Primitive | Inputs | Returns |
|-----------|--------|---------|
| `has_fill(op)` | content-stream operator string | bool — True for `f f* B B* b b*` |
| `has_stroke(op)` | content-stream operator string | bool — True for `S s B B* b b*` |
| `fill_color(state)` | graphics-state Mapping | Any — current fill color values, or None |
| `stroke_color(state)` | graphics-state Mapping | Any — current stroke color values, or None |
| `width(state)` | graphics-state Mapping | float — current line width (default 1.0 per PDF spec) |
| `effective_width(state, ctm)` | graphics-state + 6-tuple CTM | float — width × min(scale_x, scale_y) for hairline detection |
| `opacity(state, *, kind="fill")` | graphics-state + kind | float — `ca` for fill or `CA` for stroke; default 1.0 |
| `blend_mode(state)` | graphics-state Mapping | str — current BM (default "Normal") |

## Module

`packages/engine/src/lintpdf/primitives/stroke_fill.py`

## POC migration target

`hairline.py` already has stroke-width math inline; further migration to
`effective_width` would consolidate the formula. Pick one usage.

## Read-only / no-stub

- ✓ Pure functions; no PDF mutation
- ✓ Tests pass; ruff + mypy clean
