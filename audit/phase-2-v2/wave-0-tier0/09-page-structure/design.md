# Tier-0 Batch 09 — Page / Structure predicates

**Wave:** 0 (Tier-0 primitives)
**Category:** page / doc
**Primitive count:** 11
**EM estimate:** 0.20
**Date:** 2026-04-25

Per universe enumeration §4.9.

## Primitives

### page.* (geometry boxes & layout)

| Primitive | Inputs | Returns |
|-----------|--------|---------|
| `media_box(page)` | page dict / event | tuple[float,float,float,float] or None |
| `trim_box(page)` | page | rect tuple or None (falls back to crop, then media) |
| `bleed_box(page)` | page | rect tuple or None |
| `crop_box(page)` | page | rect tuple or None |
| `art_box(page)` | page | rect tuple or None |
| `size_pt(page)` | page | (w_pt, h_pt) from MediaBox + UserUnit |
| `orientation(page)` | page | "portrait" / "landscape" / "square" |
| `rotation(page)` | page | int (0/90/180/270 normalized) |
| `user_unit(page)` | page | float (default 1.0) |
| `has_oversize_bleed(page, max_pt)` | page + threshold | bool — bleed > max distance from trim |

### doc.* (document-level)

| Primitive | Inputs | Returns |
|-----------|--------|---------|
| `page_count(doc)` | doc | int |
| `has_structure_tree(doc)` | doc | bool — Catalog has /StructTreeRoot |

## Module

`packages/engine/src/lintpdf/primitives/page.py` — both page.* and doc.* live here (small surface).

## POC migration

`page_geometry.py` analyzer hand-rolls `media_box - trim_box` and orientation; can flip to `page_p.size_pt()` + `page_p.orientation()`.

## Read-only / no-stub

- ✓ Pure functions; no mutation; ruff + mypy clean
