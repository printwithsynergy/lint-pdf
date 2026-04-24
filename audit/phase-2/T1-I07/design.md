# T1-I07 — Missing image / broken reference

## What the check detects

Flags pages whose `/Resources /XObject` dictionary references an image resource name that isn't resolvable — the indirect reference dangles (no xref entry, null object, or a non-image type). Content streams that `Do` one of these names will print a blank rectangle or be silently dropped by the RIP, and the tenant has no way of knowing upstream.

Two variants collapse into the one inspection_id:

1. **Dangling ref** — `/Resources /XObject /Im1` points to an indirect reference that doesn't exist in the xref (pikepdf raises on dereference).
2. **Wrong type** — the ref resolves but `/Subtype != /Image` (e.g., a `/Form` XObject with no content, or a dict missing `/Subtype` entirely).

The check does NOT fire when an XObject is defined but simply unused — many tools emit unused resources. It fires only when the resource is referenced from a content-stream `Do` operator AND dereference fails.

## Input

- `document: SemanticDocument.pages[*].resources["/XObject"]` — may contain both dict keys → indirect refs and direct inline dicts.
- `events: list[ContentStreamEvent]` — specifically the absence of `ImagePlacedEvent` when a `/Do` op references a name that's in the XObject dict.

Actually simpler: walk each page's `/Resources /XObject` dict, dereference every value, check `/Subtype == /Image` for image candidates. Flag dangling refs.

Content-stream scanning is NOT needed — the page-resources walk catches the broken case whether the Do op exists or not. That's stricter than the playbook description (which says "referenced"), but matches how PitStop / pdfToolbox handle it: "broken resource = broken resource" regardless of usage.

## Output shape

```
Finding(
    inspection_id="LPDF_IMG_018",
    severity=Severity.ERROR,
    message="Image XObject 'Im3' on page 2 has a broken reference",
    page_num=2,
    details={
        "resource_name": "Im3",
        "failure_mode": "dangling_indirect_ref" | "wrong_subtype" | "missing_subtype",
        "resolved_subtype": "/Form" | None,
    },
    iso_clause="ISO 32000-2:2020 8.10 / 7.3.10",
    object_id="Im3",
    object_type="xobject",
)
```

Severity **error**, not warning — a broken image ref produces a visibly wrong PDF every single time. No tenant ever wants this.

## Remediation guidance

> Image XObject `{resource_name}` on page `{page_num}` resolves to {resolved_subtype or 'a missing object'}. The content stream will render a blank region. Fix upstream: in Illustrator / InDesign, relink or remove the broken placement before exporting.

## Confirm read-only

Check reads `page.resources["/XObject"]` and calls `obj.dereference()` / `obj.get("/Subtype")` via pikepdf. No writes, no re-saves. pikepdf objects returned from dereferencing are discarded immediately after type inspection.

## Profile membership

| Profile | Include by default? |
|---|:--:|
| PDF/X-1a..X-6 | Yes — error |
| PDF/A-1b..4 | Yes — error |
| All GWG 2022 | Yes — error |
| Internal debug | Yes — error |

Universal check. No profile should ever want a broken image reference to pass.

## Edge cases

1. **Intentional null resources** — some tools emit `/Im1 null` as a placeholder. Treat as dangling → fire.
2. **Form XObjects inside /XObject dict** — these are legit for page-local reusable graphics. Skip (Subtype=/Form is not a failure).
3. **Inherited resources** — if the page has no local `/XObject` but inherits from the Pages tree, walk the inherited dict. Builder already resolves inheritance into `page.resources`.
4. **PostScript XObjects** (Subtype=/PS — deprecated) — treat as a broken image ref; PostScript XObjects have no rendering semantics in modern PDF.
5. **Recursive reference cycles** — extremely rare, but cap dereference depth at 3 and log if hit.

## Q&A gate

One open question — pretty sure of the answer, worth stating:

1. **Scope: usage-aware or usage-blind?** The playbook says "missing image / broken reference" without specifying whether to require content-stream usage. I defaulted to **usage-blind** — if a broken XObject is in the page's resource dict, flag it regardless of whether the content stream calls `Do`. Rationale: detection noise is low (broken refs are rare), and catching unused broken refs protects tenants who edit the PDF downstream. If you'd prefer usage-aware (only flag when actually placed), say so and I'll scope to content-stream `Do` ops.

## Implementation notes

- New method `ImageAnalyzer._check_broken_image_refs(document: SemanticDocument) -> list[Finding]`.
- Called from `ImageAnalyzer.analyze()` after the existing event-loop body.
- Iterates `document.pages`, walks `page.resources.get("/XObject", {}).items()`, dereferences each value, checks `/Subtype`.
- Uses `contextlib.suppress(Exception)` around the dereference since pikepdf raises different exception types (KeyError / ObjectError / PdfError) depending on the failure mode — the exception type tells us which `failure_mode` to emit.
- Add `LPDF_IMG_018` to `check_names.py` (already has 017; 018 is next).
- Test fixture: hand-craft a minimal PDF with a page resource dict that includes a dangling `/Im1 99 0 R` indirect reference. Assert one finding with `failure_mode="dangling_indirect_ref"`. Second fixture with `/Im2` pointing to a `/Form` XObject — assert `failure_mode="wrong_subtype"`. Third with a valid image — assert no finding.
