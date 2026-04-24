# Phase 2 — Sequencing memo (operator-approved 2026-04-24)

Operator answers from Phase 1 Q&A:

1. **Sequencing** → recommended order.
2. **veraPDF shim** → one generic endpoint (efficiency + clarity both win).
3. **T5-N07 WCAG contrast** → request for higher score; on re-check T5-N07 is already `present` (AI_WCAG_001, AI_WCAG_002, LPDF_ACCESS_012 in `ai/analyzers/color_compliance/wcag_contrast.py`). Not in backlog — no bump required.
4. **Unmapped KEEP defaults** → blanket-approve across 12 AI categories (99 IDs) — see `audit/phase-1/unmapped-triage.md`.
5. **Batch size** → 3 per batch.

## Decisions locked

### Ordering — first 10 batches (sequenced)

Batches sequenced so each lands with low risk and each unlocks the next. Every batch = 3 checks per the playbook default.

| Batch | Gap IDs | Theme | Rationale |
|:---:|---|---|---|
| 1 | `T1-CMP02`, `T1-CMP03`, `T1-I07` | Tier-1 cheap cleanups (pikepdf one-liners) | Establish Phase-2 pattern. Each is a single field read + one finding. Smallest risk surface. |
| 2 | `T1-CMP04`, `T1-CMP06`, `T1-F04` | Tier-1 cheap cleanups (continued) | Same pikepdf style. `T1-F04` needs OS/2 fsType parse — slightly chunkier but still cheap. |
| 3 | `T1-CMP01`, `T4-A02`, `T4-A01` | veraPDF shim + 3 rules on top | One HTTP shim lands once; three rules consume it. Biggest batch in wall-clock but also biggest unblock. |
| 4 | `T1-STR04`, `T2-XMP02`, `T2-XMP03` | Profile-aware + metadata | `T1-STR04` needs an `expected_page_size` profile field → piggyback on profile work. XMP02/03 are metadata reads. |
| 5 | `T3-D02`, `T3-D03`, `T3-D15` | **Tier-3 dieline wedge — first strike** | The easiest 3 Tier-3s: z-order scan (content-stream order), dieline-overprint flag read, CutContour-visible detection. Dieline detector already exists — feeds all three. |
| 6 | `T3-D01`, `T3-D05`, `T3-D10` | Tier-3 dieline (continued) | Raster-compare for content-on-dieline, polygon containment for content-outside-dieline, varnish coverage. |
| 7 | `T3-D04`, `T3-D13`, `T3-D12` | Tier-3 dieline + cross-over | Bleed-extension math, registration-risk on fine vectors, substrate-aware TAC. |
| 8 | `T3-D11`, `T2-SPT02`, `T2-SPT03` | Spot-name normaliser cluster | `T3-D11` (canonical spot taxonomy) unlocks `T2-SPT02` (C/U/CP/HC suffix) + `T2-SPT03` (deprecated CV/CVC) with shared infrastructure. |
| 9 | `T2-ISO03`, `T2-ISO04`, `T2-ISO05` | ISO 19593-1 spot taxonomy | White subtypes, varnish/coating types, auto-suggest tagging. Builds on the batch-8 normaliser. |
| 10 | `T2-ISO01`, `T2-ISO02`, `T3-D14` | ISO 19593-1 completion + braille | Structural Type + Position taxonomy + braille validation (pharma niche). |

Remaining 19 backlog items (5 easy T2, 8 hard T2/T4/T5, 6 small-volume T5) cluster into 6-7 more batches. Sequencing will be revisited at batch 10.

### veraPDF shim shape (Batch 3)

Single endpoint in the engine:

```
POST /internal/verapdf/validate
Body: pdf_bytes, flavour (PDFA_1B|PDFA_2B|...|PDFX_1A|...|PDFUA_1)
Returns: {
  passed: bool,
  profile: str,
  failures: [{clause, message, count, locations}],
  raw_report_xml: str  # for operator debug
}
```

- Engine calls the veraPDF Java sidecar once per (pdf_bytes, flavour) pair.
- Result cached on `Job.id` so multiple rules sharing a flavour don't re-invoke.
- Each rule (`T1-CMP01`, `T4-A01`, `T4-A02`) filters the shared `failures` list for its own clause set.
- No XML-parsing duplication; one `parse_verapdf_report()` helper in `packages/engine/src/lintpdf/conformance/verapdf_client.py` (module already exists — extend rather than create).

### Read-only constraint re-affirmed

Every check in Batches 1-10 is pure inspection. None writes to the input PDF. All remediation guidance is emitted as structured report content, never as a PDF mutation. If a check's natural implementation tempts mutation (e.g., "auto-set Trapped to False"), the design note calls it out and reworks it as inspection + guidance.

### Batch cadence

Per playbook §2.5:

```
Batch N complete: <gap_ids>.
Next batch proposed: <gap_ids>.
Any pivots? (Y/N)
```

Operator-approval required between batches.
