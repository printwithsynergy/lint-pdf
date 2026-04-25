# Tier-0 Batch 06 — Transparency-stack predicates

**Wave:** 0 (Tier-0 primitives)
**Category:** Transparency-stack
**Primitive count:** 9
**EM estimate:** 0.20
**Date:** 2026-04-25

Per universe enumeration §4.6.

## Primitives

| Primitive | Inputs | Returns |
|-----------|--------|---------|
| `in_isolated_group(state)` | graphics-state | bool |
| `in_knockout_group(state)` | graphics-state | bool |
| `has_smask(state)` | graphics-state OR ExtGState dict | bool |
| `smask_is_alpha(smask_dict)` | SMask dict | bool — Subtype = Alpha |
| `smask_is_luminosity(smask_dict)` | SMask dict | bool — Subtype = Luminosity |
| `page_transparency_group_present(page)` | PdfPage | bool |
| `page_blending_color_space(page)` | PdfPage | str or None |
| `extgstate_alpha(extgstate_dict, *, kind="fill")` | ExtGState dict | float — CA / ca |
| `extgstate_blend_mode(extgstate_dict)` | ExtGState dict | str — BM |

## Module

`packages/engine/src/lintpdf/primitives/transparency_stack.py`

## POC migration

Pick one usage in `transparency.py` that inspects ExtGState dictionaries
(extending the Batch 5 POC).

## Read-only / no-stub

- ✓ Pure functions; no mutation; ruff + mypy clean.
