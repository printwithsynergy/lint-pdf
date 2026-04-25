# T1-CMP02 LPDF_DOC_009 — Review questions

## Behavior

**Q1.** Two failure modes (`below_minimum`, `above_maximum`) collapsed into one inspection_id with `details.failure_mode` distinguishing them. Acceptable, or split into LPDF_DOC_009 (below) / LPDF_DOC_010 (above)?

**Q2.** Version parsing: `"1.6"` → `(1, 6)`, `"2.0"` → `(2, 0)`, `"1.10"` → `(1, 10)`. Malformed inputs (`"garbage"`, `"1"`, `"1.2.3"`, `"1.x"`) return `None` and silently skip the check. Is silent-skip the right fail-safe behaviour, or would an explicit "cannot parse PDF version header" finding be preferable?

**Q3.** The check fires independently of page count (my integration test caught the issue — the original DocumentAnalyzer has `if len(pages) < 2: return findings` that gated page-consistency checks; I moved the version check BEFORE that early return). Single-page PDFs evaluate fine now. Confirm.

## Profile

**Q4.** Per-profile defaults seeded (Q&A answer = (a)+(b)):

| Profile | min | max |
|---|:-:|:-:|
| `pdfx1a-magazine-ads` | 1.3 | 1.4 |
| `pdfx3-european` | 1.4 | 1.4 |
| GWG 2022 (6 variants: coated/uncoated offset, digital, newspaper, packaging, sign-display) | 1.6 | — |
| GWG sheet-fed / web-offset | 1.4 | — |
| `hp-indigo-epm` | 1.5 | — |
| `iso-12647-compliance` | 1.4 | — |
| `ecg-readiness` | 1.6 | — |
| `lintpdf-default` / `-strict` / `-advisory-only` | (untouched — opt-in) | — |

Question: should `lintpdf-default` also get a conservative `min=1.4` to catch PDFs older than modern baseline? Or is "opt-in only" correct?

**Q5.** The bundled GWG 2022 profiles all carry `conformance: pdfx4`, and PDF/X-4 requires ≥ 1.6. Setting `min_pdf_version: 1.6` on them is redundant if the conformance check already catches that — but LPDF_DOC_009 catches it faster and gives the tenant a specific "version too old" message instead of a generic "failed X-4 conformance." Agreed this is useful double-coverage, or remove the duplicate?

## Remediation guidance

**Q6.** Current emit:

> "PDF version 1.4 is below the PDFX-4 minimum (1.6)"

Includes the profile name for context. Good, or should it also name the upstream fix path ("Re-export from InDesign with Compatibility: Acrobat 8 or later")?

## Output format

**Q7.** `details` carries `pdf_version`, `min_pdf_version`, `max_pdf_version`, `profile_name`, `failure_mode`. Add anything?

## Severity

**Q8.** Default `warning`. This is the middle option — below `error` (which would block the preflight hard) and above `advisory` (which would be easy to ignore). Agreed, or change per-profile? For example PDF/X-1a-2003 could escalate to `error` since version mismatch there typically means the PDF isn't actually conformant.

## Read-only

**Q9.** Confirmed: reads `document.version` + two profile fields, emits a finding. No pikepdf writes, no profile writes, no re-saves. ✅

## Rules-editor UI

**Q10.** Per-Q&A answer (b), the two fields should be surfaced in the rules editor. Current status:
- JSON tab: ✅ Editable (standard ThresholdConfig path — any profile editor can set them via the raw JSON).
- Rules tab: ❌ No dedicated "PDF version constraints" section yet. The Rules tab currently shows per-check severity cards but has no threshold-editing widget at all — this would be a new pattern.

My recommendation: defer the dedicated Rules-tab UI to a follow-up PR so the check can land end-to-end today. Tenants who care can already override via the JSON tab. When the Rules-tab threshold pattern lands for any threshold (min_dpi, tac_limit, etc.), min_pdf_version/max_pdf_version get added in the same pass.

Confirm: defer Rules-tab widget? Or block this check's merge until the widget is built?
