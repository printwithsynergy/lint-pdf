# Tier-0 Batch 02 — Color-space predicates

**Wave:** 0 (Tier-0 primitives)
**Category:** Color-space
**Primitive count:** 17 (13 type predicates + 4 inspection helpers)
**EM estimate:** 0.35
**Design date:** 2026-04-25

## What this batch detects

Pure-function predicates that classify a PDF color-space (resolved dict
or name token) into one of the standard PDF color-space families, plus
helpers for inspecting alternate space, tint transform, and ICC profile
metadata.

Per universe enumeration §4.2.

## Primitives in this batch

**13 type predicates** (all return bool, signature `(cs: Any) -> bool`):

| Primitive | Notes |
|-----------|-------|
| `cs.is_DeviceCMYK` | name `/DeviceCMYK` |
| `cs.is_DeviceRGB` | name `/DeviceRGB` |
| `cs.is_DeviceGray` | name `/DeviceGray` |
| `cs.is_CalRGB` | array first-element `/CalRGB` |
| `cs.is_CalGray` | array first-element `/CalGray` |
| `cs.is_Lab` | array first-element `/Lab` |
| `cs.is_ICCBased` | array first-element `/ICCBased` |
| `cs.is_Separation` | array first-element `/Separation` |
| `cs.is_DeviceN` | array first-element `/DeviceN` |
| `cs.is_NChannel` | DeviceN with `Subtype = NChannel` |
| `cs.is_Indexed` | array first-element `/Indexed` |
| `cs.is_Pattern` | name `/Pattern` or array first-element `/Pattern` |
| `cs.is_Shading` | shading-dict context (rare; only in SMask Form XObjects) |

**4 inspection helpers:**

| Primitive | Returns | Notes |
|-----------|---------|-------|
| `cs.alternate_space(cs)` | `Any \| None` | The alternate (process) space for Separation, DeviceN, ICCBased — None otherwise |
| `cs.tint_transform_is_zero(cs)` | `bool` | True when Separation/DeviceN tint transform is the zero function (signal of a stray "All" or empty plate) |
| `cs.icc_profile_version(cs)` | `"v2" \| "v4" \| None` | Inspects ICC profile bytes for v2 vs v4 marker |
| `cs.icc_profile_class(cs)` | `"input" \| "display" \| "output" \| "abstract" \| "color_space" \| "device_link" \| "named_color" \| None` | ICC profile class header field |

## Architecture

**Module:** `packages/engine/src/lintpdf/primitives/color_space.py`

**Input shape:** A "color space" can be:
1. A name token (str): `"DeviceRGB"`, `"/DeviceRGB"`, or pikepdf `Name`
2. A list/array: `["CalGray", {...params}]` or `["DeviceN", ["C","M","Y","K"], alt, tint]`
3. A pikepdf `Array` or `Dictionary` already resolved to Python types
4. A name pointing into page Resources `/ColorSpace` dict

For unresolved name references in resources, callers must resolve first;
predicates operate on resolved values only.

**Public API:**

```python
from typing import Any

def is_DeviceCMYK(cs: Any) -> bool: ...
def is_DeviceRGB(cs: Any) -> bool: ...
# ... etc
def alternate_space(cs: Any) -> Any | None: ...
def tint_transform_is_zero(cs: Any) -> bool: ...
def icc_profile_version(cs: Any) -> str | None: ...
def icc_profile_class(cs: Any) -> str | None: ...
```

## Tint-transform-zero detection

A Separation or DeviceN color space carries a tint transform function. If
the function is a constant 0 sampled across [0, 1], it produces no ink —
indicating a stray plate (e.g. an `All` color that nobody wired up).

Detection:
- Function dict's FunctionType:
  - **Type 0** (sampled): all sample values are 0
  - **Type 2** (exponential): C0 == C1 == [0]
  - **Type 3** (stitching): all subfunctions are zero (recursive check)
  - **Type 4** (PostScript): minimal in-house Type-4 evaluator. PDF Type 4
    is a small deterministic subset of PostScript (math, comparison,
    boolean, control-flow, stack manipulation). Evaluated at sample points
    `[0.0, 0.5, 1.0]`; all-zero result → constant zero. Pure-Python
    interpreter (~150 LOC); no Ghostscript subprocess; no new dep.

## ICC profile version + class

ICC profile bytes are stored in an ICCBased stream. Per ICC.1:2010 spec:
- Bytes 8-11 = profile version (v2 = 0x02 first byte; v4 = 0x04 first byte)
- Bytes 12-15 = profile/device class ASCII (e.g. `"prtr"` = output, `"mntr"` = display)

The helper reads bytes 0-15 of the ICC stream content (no full decoding;
just header fields).

## POC migration target

Pick one analyzer that has an inline `if cs == "DeviceRGB"` or equivalent.
Candidates: `color.py`, `gamut_analyzer.py`, `dieline_quality.py`.

Recommended: `color.py` — high-traffic analyzer with multiple inline
checks. Migrate one helper function (e.g. `_classify_color_space`) to use
`color_space.is_DeviceRGB(cs)` etc. directly.

## Test plan

`packages/engine/tests/primitives/test_color_space.py`:
- One test per type predicate (13 × 3 cases = 39 tests)
- One test per helper (4 helpers × 3-5 cases each = ~20 tests)
- Edge cases: nested ICCBased, NChannel as DeviceN+Subtype, Pattern as
  name vs array, Indexed with base ICCBased, malformed arrays
- Total target: 60+ tests

## Read-only / no-stub confirmation

- ✓ No PDF mutation
- ✓ No `TODO`/`FIXME`/`stub`/`mock`/placeholder
- ✓ Tests pass before commit
- ✓ ruff + mypy clean

## Q&A for operator (per playbook §2.1)

1. **API casing:** universe §4.2 uses PascalCase predicates (`is_DeviceCMYK`).
   Object-class Batch 1 used snake_case (`is_text`). Should color-space
   keep PascalCase to match universe enumeration verbatim, or migrate
   to snake_case (`is_device_cmyk`) for Pythonic consistency? Recommend
   **PascalCase** to honor universe enumeration as the canonical reference
   for predicate names.
2. **Tint-transform Type 4 (PostScript):** zero detection requires a
   PostScript interpreter to verify constant-zero. Recommend returning
   False (conservatively non-zero) and logging a debug message that
   detection was skipped.
3. **Indexed color base recursion:** if base of Indexed is ICCBased, does
   `is_ICCBased` return True for the Indexed cs as a whole? Recommend
   **False** — Indexed IS a wrapper; its type is "Indexed" regardless
   of base. Callers wanting the base should call `alternate_space()`.
4. **NChannel detection:** `[/DeviceN names alt tint /attrs]` where attrs
   has `Subtype: NChannel`. Recommend `is_NChannel` returns True only
   when both the array starts with `/DeviceN` AND the attrs subtype
   is `/NChannel`; `is_DeviceN` returns True for any DeviceN-prefixed
   array (NChannel is a subtype of DeviceN per spec).
