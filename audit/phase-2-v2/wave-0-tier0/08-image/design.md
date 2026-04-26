# Tier-0 Batch 08 — Image predicates

**Wave:** 0 (Tier-0 primitives)
**Category:** Image
**Primitive count:** 13
**EM estimate:** 0.25
**Date:** 2026-04-25

Per universe enumeration §4.8.

## Primitives

| Primitive | Inputs | Returns |
|-----------|--------|---------|
| `color_space(image)` | image dict / event | str or None |
| `bit_depth(image)` | image | int (default 8) |
| `filter_name(image)` | image | str or list of str ("DCTDecode", "FlateDecode", etc.) |
| `has_jpeg(image)` | image | bool — DCTDecode in filter chain |
| `has_jpeg2000(image)` | image | bool — JPXDecode |
| `has_jbig2(image)` | image | bool — JBIG2Decode |
| `dpi_native(image)` | image | tuple[float, float] or None — Width × Height / size |
| `dpi_effective(image, ctm)` | image + 6-tuple CTM | tuple[float, float] |
| `has_icc_profile(image)` | image | bool |
| `icc_matches_oi(image, output_intent_icc)` | image + OI dict | bool |
| `has_alpha(image)` | image | bool — explicit alpha channel |
| `has_smask(image)` | image | bool — SMask key present |
| `is_inline(image)` | image | bool |

## Module

`packages/engine/src/lintpdf/primitives/image.py`

## POC migration

`image.py` analyzer has inline `cs == "DeviceRGB"` checks; pick one to replace with `image_p.color_space(img) == "DeviceRGB"`.

## Read-only / no-stub

- ✓ Pure functions; no PDF mutation; ruff + mypy clean
