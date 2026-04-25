# Tier-0 Batch 03 — Ink predicates

**Wave:** 0 (Tier-0 primitives)
**Category:** Ink
**Primitive count:** 10
**EM estimate:** 0.30
**Design date:** 2026-04-25

## What this batch detects

Pure-function predicates that classify spot-color "inks" — process vs spot,
reserved names (Cyan, Magenta, Yellow, Black, All, None, Registration),
ISO 19593-1 processing-step grouping, library matching (Pantone, HKS,
Roland, custom), and Lab / alternate-CMYK extraction.

Per universe enumeration §4.3.

## Primitives in this batch

| Primitive | Returns | Notes |
|-----------|---------|-------|
| `ink.name(spot)` | `str \| None` | Bare spot/process name (no leading slash) |
| `ink.is_process(name)` | `bool` | True for Cyan/Magenta/Yellow/Black/Gray/CMYK |
| `ink.is_spot(name)` | `bool` | True for non-reserved, non-process names |
| `ink.is_reserved_name(name)` | `bool` | True for Cyan/Magenta/Yellow/Black/All/None/Registration |
| `ink.lab_value(spot_cs)` | `tuple[float, float, float] \| None` | L\*a\*b\* if alt is Lab |
| `ink.alt_cmyk(spot_cs)` | `tuple[float, float, float, float] \| None` | CMYK alt-values from Type-2 fn |
| `ink.alt_lab(spot_cs)` | `tuple[float, float, float] \| None` | Lab alt-values from Type-2 fn |
| `ink.matches_library(name, library)` | `bool` | Pantone / HKS / Roland / custom regex |
| `ink.is_processing_step(name)` | `bool` | ISO 19593-1 reserved spot name |
| `ink.processing_step_group(name)` | `str \| None` | Structural / Braille / Information / Positions / White / Varnish / Custom |
| `ink.processing_step_type(name)` | `str \| None` | Cutting / Folding / Glueing / Perforation / etc. |

## Architecture

**Module:** `packages/engine/src/lintpdf/primitives/ink.py`

**Input shape:**
- For `ink.name`: a Separation/DeviceN array `["Separation", "PANTONE 185 C", alt, tint]`
- For others: bare or slash-prefixed name strings

## ISO 19593-1 reserved names

The engine already has spot-name normalization at
`packages/engine/src/lintpdf/analyzers/spot_name_normaliser.py` (597 LOC,
shipped in v1 Sub-batch 9c with `ISO_19593_GROUP_BY_CANONICAL`). This
batch wraps that normalizer in primitive form for reuse across all v2
checks that consume processing-step semantics.

**Re-use, don't duplicate:** primitives import from spot_name_normaliser;
they're a thin wrapper, not a re-implementation.

## Library matching

**Pantone:** name pattern `^PANTONE \d+\s*[A-Z]?$` (e.g., "PANTONE 185 C", "PANTONE Reflex Blue C")
**HKS:** `^HKS \d+[KNZE]?$` (HKS K = coated, N = uncoated, Z = newsprint, E = continuous-form)
**Roland Pantone Matching System:** `^RAL \d+$` (German RAL classic)
**Custom:** caller-supplied regex pattern

## POC migration target

`dieline_quality.py` or `color.py` has inline reserved-name checks. Pick a
helper that classifies a spot color (e.g., `_is_dieline_spot`) and migrate
to use `ink.is_processing_step` / `ink.processing_step_group`.

## Test plan

- One test per predicate
- Edge cases: PANTONE Reflex Blue (no number), Lab tuple unpacking,
  CMYK 4-tuple from Type 2 with C0/C1, malformed function dicts, missing
  alt space
- Total target: 35+ tests

## Q&A for operator (per playbook §2.1)

1. **Library list:** start with Pantone + HKS + Roland; add others
   (TOYO, DIC, ANPA) on demand. Recommend yes.
2. **`ink.is_process`:** include `Black` (the K plate spot for some files)
   even though it's typically inferred from DeviceCMYK? Recommend yes —
   `Black` as a Separation is common in pre-separated files.
3. **Custom library:** pass-through regex or structured rules (prefix +
   number range)? Recommend pass-through regex for v2.0 simplicity;
   structured rules can come later.
4. **`processing_step_group` return:** lowercase strings vs Title-Case?
   Recommend Title-Case to match ISO 19593-1 group names verbatim
   (Structural, Braille, Information, Positions, White, Varnish, Custom).
