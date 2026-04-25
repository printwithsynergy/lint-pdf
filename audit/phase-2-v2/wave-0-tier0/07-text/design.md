# Tier-0 Batch 07 — Text predicates

**Wave:** 0 (Tier-0 primitives)
**Category:** Text
**Primitive count:** 14
**EM estimate:** 0.30
**Date:** 2026-04-25

Per universe enumeration §4.7. Predicates over a TextRenderedEvent / text-state context.

## Primitives

| Primitive | Inputs | Returns |
|-----------|--------|---------|
| `font_name(text)` | text event / state | str or None |
| `font_subtype(text)` | text event / state | str or None (Type1, TrueType, CIDFontType0, etc.) |
| `font_is_embedded(text)` | text event / state | bool |
| `font_is_subset(text)` | text event / state | bool — by BaseFont name prefix `XXXXXX+` |
| `font_has_to_unicode(text)` | text event / state | bool |
| `font_to_unicode_complete(text)` | text event / state | bool — every used glyph maps to Unicode |
| `font_widths_consistent(text)` | text event / state | bool |
| `glyph_uses_notdef(text)` | text event / state | bool |
| `is_artificial_bold(text)` | text event / state | bool — synthesized weight via `Tr` 2 + width |
| `is_artificial_italic(text)` | text event / state | bool — text-state matrix has shear |
| `is_artificial_outline(text)` | text event / state | bool — `Tr` 1 |
| `rendering_mode(text)` | text event / state | int 0-7 (Tr) |
| `size_pt(text)` | text event / state | float — font size as set by Tf |
| `effective_size_pt(text, ctm)` | text event + CTM | float — size × text-matrix × CTM scale |

## Module

`packages/engine/src/lintpdf/primitives/text.py`

## POC migration

`hairline.py` already migrated; pick `font.py` or `text.py` analyzer for
font-embedding / size checks.

## Read-only / no-stub

- ✓ Pure functions; no PDF mutation; ruff + mypy clean
