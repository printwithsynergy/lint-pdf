# Tier-0 Batch 01 — Object-class predicates

**Wave:** 0 (Tier-0 primitives)
**Category:** Object-class
**Primitive count:** 8
**EM estimate:** 0.25
**Design date:** 2026-04-25

## What this batch detects

Pure-function predicates that classify a PDF content-stream object into
one of the standard PDF object types: text, image, path, form xobject,
shading, inline image, clipping path, or pattern.

These are **not user-facing checks** — they are the foundation predicates
that user-facing checks compose. Every Tier 1–5 check in the F-/C-/I-/etc.
universe builds on object-class primitives via `if obj.is_text(): ...`.

## Primitives in this batch

| Primitive | Returns | Inputs | Notes |
|-----------|---------|--------|-------|
| `object.is_text` | bool | content-stream operator + state | True for `Tj`, `TJ`, `'`, `"` operators in `BT...ET` block |
| `object.is_image` | bool | content-stream operator + state | True for `Do` referencing an Image XObject; also `BI...ID...EI` inline images |
| `object.is_path` | bool | content-stream operator + state | True for `S`, `s`, `f`, `f*`, `B`, `B*`, `b`, `b*`, `n` (with stroke/fill state) |
| `object.is_form_xobject` | bool | content-stream operator + state | True for `Do` referencing a Form XObject |
| `object.is_shading` | bool | content-stream operator + state | True for `sh` operator |
| `object.is_inline_image` | bool | content-stream operator | True for `BI...ID...EI` block specifically |
| `object.is_clipping_path` | bool | content-stream state | True when graphics state has active clip stack |
| `object.is_pattern` | bool | color/fill state | True when fill or stroke is a Pattern color-space |

## Architecture

**Module:** `packages/engine/src/lintpdf/primitives/object_class.py`

**Public API:**

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class StreamObject:
    """A single object emitted during content-stream walking.

    Wraps the operator + operand stack + graphics-state snapshot so
    primitives can answer questions in pure-function style.
    """
    operator: str
    operands: tuple
    graphics_state: "GraphicsState"  # opaque to primitives
    page_object_ref: str | None      # for Do; None for inline content
    inline_image_dict: dict | None   # only for BI...EI

def is_text(obj: StreamObject) -> bool: ...
def is_image(obj: StreamObject) -> bool: ...
def is_path(obj: StreamObject) -> bool: ...
def is_form_xobject(obj: StreamObject) -> bool: ...
def is_shading(obj: StreamObject) -> bool: ...
def is_inline_image(obj: StreamObject) -> bool: ...
def is_clipping_path(obj: StreamObject) -> bool: ...
def is_pattern(obj: StreamObject) -> bool: ...
```

## Integration with existing parser

The pikepdf adapter (`packages/engine/src/lintpdf/parser/pikepdf_adapter.py`)
already walks content streams and produces semantic events (e.g.,
`TextRenderedEvent`, `OpacityChangedEvent`). Primitives wrap those events
into the canonical `StreamObject` shape.

**No mutation of existing parser API.** Primitives are an additive layer
that consumers can opt into. Existing analyzers continue to use direct
event types until migrated incrementally.

## Test plan

`packages/engine/tests/primitives/test_object_class.py`:
- One test per primitive
- Fixture-based: small synthetic PDFs with known object types
- Edge cases: nested form xobjects, BI/ID/EI inline images, shading-only fills,
  pattern-fill text, empty content streams, malformed operators

Test count target: 24+ (3+ per primitive).

## Read-only confirmation

These are pure inspection predicates. No mutation of any input PDF. No
file-system writes outside test fixtures. ✓

## Toggle metadata

Per §16: primitives have **no toggleable knobs** — they are foundation
infrastructure. No registry entry. No tenant config. No per-call override.

## BYO mode

Primitives operate over `StreamObject`. In BYO mode, the BYO payload
synthesizes equivalent objects from the supplied per-page event stream
(when present). When BYO supplies only metrics, primitives are not
invoked.

## Profiles

Not profile-applicable. Foundation infrastructure.

## Edge cases (3–5 to stress-test)

1. **Form XObject containing text** — `is_text` should return True for
   the text operators **inside** the form, while `is_form_xobject` is
   True for the `Do` operator at the parent level. Distinct objects.
2. **Inline image with `EI` inside image data** — must not prematurely
   end the inline image. Tested via fixture with binary data containing
   the `EI` byte sequence.
3. **`n` (no-op path) operator** — `is_path` returns True (it's a path
   that has neither fill nor stroke applied, but is still a path object).
4. **Shading via `sh` operator vs shading via Pattern color-space** —
   `is_shading` only True for `sh` operator; pattern-shading is `is_pattern`.
5. **Nested clipping** — `is_clipping_path` reflects the active state;
   nested clip paths are still True throughout.

## Q&A questions for operator (per playbook §2.1)

1. **API style:** module-level functions (`object_class.is_text(obj)`)
   vs methods on `StreamObject` (`obj.is_text()`)? Recommend module-level
   for testability + composability. Confirm?
2. **Primitive registry shape:** export each predicate at the module level
   AND register them in a central `primitives/__init__.py` `REGISTRY` dict
   for runtime introspection? Useful for v2 §16 toggle registry to enumerate
   what predicates exist.
3. **Backward-compat with existing event types:** primitives are additive;
   existing analyzers keep using `TextRenderedEvent`/`OpacityChangedEvent`
   etc. unchanged. Is that acceptable, or should this batch include a
   migration of one analyzer (e.g., `font.py`) as a proof-of-concept?
4. **`is_clipping_path` semantics:** True when there's any active clip in
   the graphics state, OR True only for the `W`/`W*` operator that
   establishes the clip? Recommend: True for any active clip in state
   (consumers usually want "is this object being clipped?", not "is this
   the clip-establishing operator?").

## Read-only / no-stub confirmation

- ✓ No PDF mutation (pure inspection)
- ✓ No `TODO`/`FIXME`/`stub`/`mock`/placeholder in production code
- ✓ All tests pass before commit
- ✓ ruff + mypy clean
