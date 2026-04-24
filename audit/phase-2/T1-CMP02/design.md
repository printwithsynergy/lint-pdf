# T1-CMP02 — PDF version check (threshold against profile expectation)

## What the check detects

Flags PDFs whose version header doesn't match the range the active preflight profile expects. Two flavours:

1. **Too old**: `document.version` < profile's `min_pdf_version` (e.g., a PDF 1.3 submitted to a PDF/X-4 workflow that wants ≥ 1.6).
2. **Too new**: `document.version` > profile's `max_pdf_version` (e.g., a PDF 2.0 file submitted to a PDF/X-1a-2001 workflow that wants exactly 1.4).

**Status: partial** (playbook v3.1 classification).

LPDF_META_004 (metadata.py) already fires on **header vs XMP consistency mismatch** ("header says 1.4 but XMP claims 1.6"). That's a different rule — it checks internal consistency, not workflow-fitness. This new rule checks workflow-fitness: does the PDF version match what the active preflight profile expects?

## Input

- `document.version: str` — e.g. `"1.6"`, `"2.0"`. Already parsed by the builder.
- Profile-level config: `profile.min_pdf_version: str | None`, `profile.max_pdf_version: str | None`. New optional fields — absent means "any version OK."

## Output shape

```
Finding(
    inspection_id="LPDF_DOC_009",               # next in the LPDF_DOC_* family
    severity=Severity.WARNING,
    message="PDF version 1.3 is below the profile minimum 1.6 (workflow: PDFX-4)",
    details={
        "pdf_version": "1.3",
        "min_pdf_version": "1.6",
        "max_pdf_version": None,
        "profile_name": "PDFX-4",
        "failure_mode": "below_minimum" | "above_maximum",
    },
    iso_clause="ISO 32000-2:2020 7.5.2 / ISO 15930-7:2010 6.2.1",
)
```

Severity **warning** — the PDF still renders but the workflow's RIP / OPI chain may choke on features that shifted between versions. Tenants can escalate to error via the rules editor.

## Remediation guidance

> This PDF is version `{pdf_version}`, but the `{profile_name}` profile expects `{min_pdf_version}` (or higher/lower, depending on mode). Re-save the document in Acrobat Pro via "File > Save As Other > Optimized PDF" with the target version set, or re-export from your source app (InDesign / Illustrator) with a matching "Compatibility" setting in the Export dialog.

## Confirm read-only

Reads `document.version` (already a string) and two profile fields. Emits a finding. No PDF mutation.

## Profile membership + default ranges

New optional profile fields: `min_pdf_version`, `max_pdf_version`. Default ranges per profile:

| Profile | min | max |
|---|:--:|:--:|
| PDFX-1a-2001 | 1.3 | 1.4 |
| PDFX-1a-2003 | 1.4 | 1.4 |
| PDFX-3-2002 | 1.3 | 1.4 |
| PDFX-3-2003 | 1.4 | 1.4 |
| PDFX-4 | 1.6 | — |
| PDFX-6 | 2.0 | — |
| PDFA-1b | 1.4 | 1.4 |
| PDFA-2b/2u | 1.7 | — |
| PDFA-3u | 1.7 | — |
| PDFA-4 | 2.0 | — |
| GWG 2022 base | 1.6 | — |
| Internal debug | — | — |

Profiles that don't set either field silently opt out. Tenant-authored profiles can add overrides via the rules editor once the schema is extended.

## Edge cases

1. **Profile with neither `min_pdf_version` nor `max_pdf_version`** — skip silently. No finding.
2. **Version parsing** — treat as tuples: `"1.6"` → `(1, 6)`. `"1.10"` (rare) → `(1, 10)`. Bail if unparseable.
3. **2.0 vs 1.7** — ordering is tuple-based so `1.7 < 2.0` is correct.
4. **Missing `document.version`** — emit a different advisory ("PDF version header absent"). Rare; pikepdf almost always recovers it.
5. **Header / XMP inconsistency** — out of scope; LPDF_META_004 already covers that.

## Q&A gate

One open question:

1. **Profile-field plumbing.** `PreflightProfile` in `packages/engine/src/lintpdf/profiles/schema.py` needs two new optional fields (`min_pdf_version`, `max_pdf_version`). Safe — backwards-compatible optional Pydantic fields. Do I also:
   - **(a)** Set the defaults listed above on the bundled PDF/X-* and PDF/A-* profiles (`packages/engine/src/lintpdf/profiles/builtin/...`)? Default recommendation: yes, baked into the bundled profile JSON so every tenant gets them without opt-in.
   - **(b)** Surface the two fields in the app-side rules editor? Default recommendation: yes, add to the Checks tab under a new "PDF version constraints" section so tenants can override per profile. Requires WS-12 `CHECK_CATALOG` regen.

Preference?

## Implementation notes

- New field on `PreflightProfile` schema: `min_pdf_version: str | None = None`, `max_pdf_version: str | None = None`.
- New method on `DocumentAnalyzer._check_pdf_version_against_profile(document, profile)`. Gated behind `profile is not None and (profile.min_pdf_version or profile.max_pdf_version)`.
- `DocumentAnalyzer` currently takes no profile arg. Pass it via constructor: `DocumentAnalyzer(min_pdf_version=..., max_pdf_version=...)` — matches the `min_dpi`/`max_dpi` pattern on `ImageAnalyzer`.
- Orchestrator (`profiles/orchestrator.py`) wires profile → constructor at instantiation time.
- Add `LPDF_DOC_009` to `check_names.py`.
- Update bundled profile JSON files (PDF/X-* / PDF/A-*) with the default ranges above.
- Tests: construct profile with `min_pdf_version="1.6"` and document with `version="1.4"` → finding. Profile with no constraint + version 1.4 → no finding. Version "2.0" + max "1.4" → finding with failure_mode=above_maximum.
