# Phase 2.EPM — Design Memo and Q&A Gate

**Status:** opened during Wave A/B closeout (2026-04-26). Inventory and
defensible v2-ID mapping shipped this session; **scoring algorithm,
EPM-Advanced (ICC), AI-Explain (LLM), and BYO schema integration are
all gated behind operator decisions** captured below. Do not start
implementation work in those areas without explicit Quincy approval.

## What's already in the codebase

`packages/engine/src/lintpdf/analyzers/epm_analyzer.py` — 18 LPDF_EPM_*
checks shipped under a different conceptual model than the playbook's
EPM-A / EPM-B / EPM-C structure. The existing checks are detection
oriented (does the document use K? is the rich-black recipe weak? is
the toner limit exceeded?) rather than candidacy-scoring oriented
(qualified / review / reject + 0–100 score).

| LPDF code | Existing description | Playbook v2 ID(s) |
|-----------|----------------------|-------------------|
| LPDF_EPM_001 | K-channel usage detection | — |
| LPDF_EPM_002 | Pure black text in CMYK or DeviceGray | EPM-A4 |
| LPDF_EPM_003 | Weak CMY composite black (K=0, C+M+Y < 200%) | — |
| LPDF_EPM_004 | CMY-only TAC threshold | EPM-A5 |
| LPDF_EPM_005 | Spot color CMYK fallback contains K | — |
| LPDF_EPM_006 | CMYK image K-channel dependency | — |
| LPDF_EPM_007 | Registration colour (all CMYK ≥ 90%) | EPM-B2 |
| LPDF_EPM_008 | Gray-balance risk (near-equal CMY, K=0) | EPM-A7, EPM-C4 |
| LPDF_EPM_009 | Total-toner TAC exceeds device limit | EPM-A5 |
| LPDF_EPM_010 | Per-channel ink limit (single channel >95%) | — |
| LPDF_EPM_011 | Spot-colour fidelity advisory | — |
| LPDF_EPM_012 | Variable-data document indicators | — |
| LPDF_EPM_013 | Custom halftone in ExtGState | — |
| LPDF_EPM_014 | Output Intent profile-class mismatch | EPM-C8 |
| LPDF_EPM_015 | White-ink underlayer detected | — |
| LPDF_EPM_016 | Overprint simulation mode | — |
| LPDF_EPM_017 | High object count (RIP performance) | — |
| LPDF_EPM_018 | Thin stroke below digital-press minimum | EPM-A4 |

**Defensible mapping shipped this session:** 6 distinct EPM v2 IDs
(EPM-A4, EPM-A5, EPM-A7, EPM-B2, EPM-C4, EPM-C8) covered via 7 LPDF
codes. These are the unambiguous overlaps; the rest of the playbook's
22 EPM IDs are absent from the existing analyzer and require new code
or a structural reframing.

## Gaps vs playbook §2.EPM

### Hard disqualifiers (EPM-A1..A8) — not implemented

| ID | Playbook spec | Status |
|----|---------------|--------|
| EPM-A1 | Job has no color pages (100% B&W) | absent — would need per-page K-only/DeviceGray detection plus an aggregate page-classifier. The opposite signal exists in LPDF_EPM_001 ("uses K") but the playbook's A1 is "all-K → don't bother with EPM, route CMYK". |
| EPM-A2 | Unwanted spot colour present (whitelist/blacklist) | absent — needs tenant-defined whitelist plus PANTONE regex. LPDF_EPM_005 covers a related but different concern (K in spot fallback). |
| EPM-A3 | Rich-black coverage exceeds page % threshold | absent — needs page-level rasterised area % calc. |
| EPM-A4 | Small black text / thin black lines below threshold | **partial** via LPDF_EPM_002 + LPDF_EPM_018. The playbook spec says "ignore <0.1mm × 3–7mm trim marks; fail on hairlines and sub-min text" — current checks fire on any pure-K text, not just below-threshold size. |
| EPM-A5 | Maximum ink coverage exceeds EPM TAC | **present** via LPDF_EPM_004 + LPDF_EPM_009. |
| EPM-A6 | ΔE to EPM gamut exceeds threshold | **absent — requires ICC engine.** Stop condition (see §"Stop conditions" below). |
| EPM-A7 | ΔC (neutral gray deviation) | **partial** via LPDF_EPM_008. The playbook spec is operator-calibrated with optional black-text exclusion; current implementation is a fixed CMY-near-equal heuristic. |
| EPM-A8 | PDF rendering / parse error | absent in epm_analyzer; LPDF_DOC_001..LPDF_DOC_004 + structure analyzer cover related parse cases. Needs rollup. |

### Strong negative signals (EPM-B1..B6) — not implemented

| ID | Playbook spec | Status |
|----|---------------|--------|
| EPM-B1 | High % of pure-K pages (route to EPM+ instead) | absent. Inverse of LPDF_EPM_001 + needs EPM+ routing logic. |
| EPM-B2 | Registration colour in artwork (not marks) | **present** via LPDF_EPM_007. Need to add "not marks" exclusion (registration in slug area is fine). |
| EPM-B3 | Skin-tone heavy photography (>15% pixels) | **absent — EPM-Advanced.** Needs rasterisation + classification. Stop condition. |
| EPM-B4 | Brand-critical PANTONE with K≥15% in alternate | absent — needs tenant brand-spot list. |
| EPM-B5 | Deep-shadow imagery (>50% area at L*<25) | **absent — EPM-Advanced.** Needs Lab conversion. Stop condition. |
| EPM-B6 | RGB source with no Output Intent | partial — LPDF_ICC_* covers Output Intent absence; not currently rolled up into EPM. |

### Soft signals (EPM-C1..C8) — not implemented

| ID | Playbook spec | Status |
|----|---------------|--------|
| EPM-C1 | Number of distinct K tints | absent — needs K-channel histogram. |
| EPM-C2 | Maximum K value | absent — partial coverage via LPDF_EPM_001. |
| EPM-C3 | K-only page-area % | absent. |
| EPM-C4 | Neutral gray fills (C=M=Y) | **partial** via LPDF_EPM_008. |
| EPM-C5 | Untagged objects | absent — partial coverage via LPDF_ICC_*. |
| EPM-C6 | PDF/X-4 non-compliant | absent in epm_analyzer; veraPDF-driven LPDF_CMP_* covers ISO conformance separately and would need rollup. |
| EPM-C7 | Transparency flattening with K | absent. |
| EPM-C8 | OI mismatched to press ICC | **present** via LPDF_EPM_014. |

### Scoring + decision-band logic — fully absent

The playbook §2.EPM.4 specifies a deterministic weighted formula
yielding a 0–100 score, three decision bands (Qualified / Review /
Reject), per-feature contribution attribution, BYO-mode
evidence-weight penalty, and per-press-target routing. **None of this
exists today.** The existing analyzer emits findings but doesn't
aggregate them into a candidacy decision.

### EPM-AI-Explain — fully absent, gated

LLM-generated 1–3 sentence operator-friendly explanations + aggregate
job-level narrative. Spec is in §2.EPM.6 (verbatim prompt template,
Claude Haiku default, 200-token output budget, hard cost cap per
tenant per month, graceful failover to deterministic templated
strings).

## Stop conditions hit

Per playbook §11, the following are hard halts requiring Quincy's
explicit answer before any further EPM work:

1. **EPM-Advanced is requested but no ICC engine exists in the stack.**
   The checks that need it: EPM-A6 (ΔE to gamut), EPM-A7 fully (ΔC
   calibrated), EPM-B3 (skin-tone classification), EPM-B5 (deep
   shadow). See playbook §2.EPM.8 question 1: "EPM-Advanced ICC
   engine — Little CMS, ArgyllCMS, or service?"

2. **LLM-Explain is requested but no per-tenant cost cap is
   configured.** §2.EPM.8 question 5: "Per-tenant LLM cost cap —
   fixed monthly $? per-job $? or unlimited at enterprise tier?"

3. **BYO schema is canonical for EPM but not yet wired** — `byo`
   ingestion path is greenfield per Phase 0.5. EPM is the canonical
   first consumer (§2.EPM.5) but until Wave V or a dedicated track
   ships the BYO endpoint, EPM Advanced cannot run in viewer-only
   mode.

## Recommended Phase 2.EPM scope split

To make Phase 2.EPM ship-able in stages without violating principle
14 (no deferred work), the wave should be split into three
sub-deliverables, each individually production-grade:

### Phase 2.EPM.0 — alignment (this session, mostly done)

- ✅ Inventory existing analyzer
- ✅ Map defensible v2-ID overlaps (6 IDs covered, 16 remain absent)
- ✅ Document gaps + stop conditions (this memo)
- ⏳ Open Q&A gate to Quincy on:
  1. ICC engine choice (Little CMS vs ArgyllCMS vs service)
  2. Default rich-black recipe (confirm C≥40 / M≥20 / Y≥20 / K≥80)
  3. Default substrate class (coated conservative vs uncoated)
  4. LLM provider for AI-Explain (Claude Haiku / GPT-4o-mini /
     Mistral / local)
  5. Per-tenant LLM cost cap shape (fixed $/month, $/job, or
     enterprise unlimited)
  6. IndiChrome upsell — surface as remediation when EPM rejected
     for spot reasons?
  7. Whether to refactor existing 18 LPDF_EPM_* into the playbook's
     EPM-A/B/C structure (rename + add gaps), or keep them as
     parallel detection-oriented codes with v2_ids as cross-mapping
     glue (current approach).

### Phase 2.EPM.1 — EPM-Core deterministic (post-Q&A)

After Quincy approves the structural decisions, ship:

- The 16 absent EPM-A/B/C checks as new analyzer methods (no ICC,
  no LLM, no BYO-only mode yet)
- Scoring algorithm + decision-band logic per §2.EPM.4
- Press-target routing (Indigo EPM / EPM+ / CMYK / IndiChrome) per
  §2.EPM.7
- Reporting shape per §7 (`category`, `level`, `code`, `evidence`,
  `score_impact`, `remediation`, `byo_data_used`,
  `byo_data_missing`)

### Phase 2.EPM.2 — EPM-Advanced + AI-Explain (gated)

Only after EPM-Core ships and stop-condition answers land:

- ICC engine integration (chosen per Q1)
- ΔE / ΔC heatmap emission
- Skin-tone + deep-shadow classifiers
- LLM explain layer behind feature flag with per-tenant cost cap
- BYO viewer-only mode (depends on Wave V BYO endpoint shipping)

## Read-only constraint

Every EPM check, every score, every AI-Explain sentence, every
remediation suggestion is **inspection + structured guidance only**.
No re-rendering, no flattening, no plate split, no DeviceLink
application that mutates the input. Where competitors auto-correct
(callas DeviceLink, Alwan ColorHub) lintPDF emits remediation
JSON pointing at the upstream fix.

## Action for the next session

1. Present the Q&A gate above to Quincy (7 questions).
2. Wait for answers.
3. Open Phase 2.EPM.1 only after the structural questions (Q7 in
   particular) are answered.

Until then, EPM analyzer behaviour is unchanged; this session's
deliverables are name-cleanup (production readiness per principle
13) + 6-of-22 v2-ID coverage + this memo.
