# T1-I07 LPDF_IMG_018 — Review questions

Per playbook §2.3 — operator review gate before marking the check `verified`.

## Behavior

**Q1.** Three failure modes collapsed into one inspection_id:
- `dangling_indirect_ref` — entry is `None` or a pikepdf cycle-detection sentinel string
- `missing_subtype` — dict with no `/Subtype` key
- `wrong_subtype` — dict with `/Subtype` that isn't `/Image` or `/Form`

Does this collapse make sense, or should each failure mode have its own inspection_id (LPDF_IMG_018 / 019 / 020) so tenants can set per-mode severity?

**Q2.** Usage-blind scope was chosen per design Q&A — the check fires whether the content stream's `Do` operator calls the broken entry or not. Is the noise floor acceptable on PDFs with lots of inherited / unused resources?

## Profile

**Q3.** Added to all profiles by default as `error` severity. No profile should accept a broken ref — agreed? If there's any workflow where "unused broken ref OK" is acceptable (debug profiles, vendor-round-trip testing), we'd add a `checks.disabled: ["LPDF_IMG_018"]` entry to that profile.

## Remediation guidance

**Q4.** The emit message today says:

> "Image XObject 'Im3' on page 2 has a broken reference (dangling_indirect_ref)"

Is "dangling_indirect_ref" too technical for the end-user report? Suggested alternative wording — "not found in the PDF's object tree" / "file is corrupt at object X". Pick one or we stay with the internal token.

## Output format

**Q5.** `details` carries `resource_name`, `failure_mode`, `resolved_subtype`. Add anything else — e.g., the raw xref entry data, the content-stream Do ops that reference the broken name, the resource-dict JSON dump?

## Severity

**Q6.** Default severity is `error`. Confirm, or downgrade to `warning` and let tenants escalate per profile?

## Read-only

**Q7.** Confirmed: the check reads `page.resources["/XObject"]` items() + inspects types. No pikepdf writes. No re-save. The design doc's explicit read-only statement remains accurate after implementation. ✅
