# Phase 0 — Per-check semantics research approach

**Operator directive (Q2):** Phase 1 will land "implement the body" work for stub analyzers and extend coverage on existing checks. *Before* implementing any check, research what it actually means — both the regulation/spec text and PitStop's industry-standard interpretation. Same rule applies to extending or repairing every existing check.

This document defines the research workflow so Phase 1 + 2 don't reinvent it per check.

## Inputs (already on disk — no web fetch needed for most checks)

| Source | Location | Use for |
|---|---|---|
| Enfocus PitStop checks catalog | `grounded-research/specs/pitstop-checks-catalog.md` (285 lines) | Industry-standard naming, severity bands, threshold defaults, category grouping |
| GWG 2022 specification | `grounded-research/specs/gwg-2022-specification.md` (1,704 lines) | Print-pipeline rules: TAC, hairline limits, font embedding, image resolution, overprint behaviour |
| ISO 32000-2 chapter notes | `grounded-research/specs/ISO32000-2-CH7-INDEX.md`, `iso32000-2-ch7-syntax.md`, `iso32000-2-ch8-graphics.md`, `iso32000-2-ch9-text.md`, `iso32000-2-ch11-transparency.md` | Authoritative PDF spec semantics (what each operator/object means) |
| ISO 15930-7 (PDF/X-4) | `grounded-research/specs/iso15930-7-pdfx4.md`, `README-PDFX4.md`, `PDFX4-QUICK-REFERENCE.txt` | PDF/X-4 conformance check semantics |
| ICC v4 reference | `grounded-research/specs/icc1-2022-color-profiles.md`, `icc1-2022-tag-reference.md`, `icc1-2022-validation-checklist.md` | ICC profile checks |
| PDF/UA + supplements | `grounded-research/specs/pdfua-and-supplements.md` | Accessibility (LPDF_ACCESS_*) checks |
| Competitive intel | `grounded-research/specs/COMPETITIVE-INTELLIGENCE-INDEX.md` + `grounded-research/17-19-competitive-intelligence.md` | What competitors flag, severity defaults, pricing context |
| Existing analyzer source | `packages/engine/src/lintpdf/analyzers/<file>.py` + `packages/engine/src/lintpdf/ai/analyzers/<sub>/<file>.py` | What lintPDF currently does (or doesn't) |
| Existing tests | `packages/engine/tests/analyzers/test_<file>.py` | Behavioural expectations already pinned |
| WS-12 catalog metadata | `packages/app/lib/rules/check-catalog.json` | Friendly name, description, default severity (when present) |

For checks that touch a regulation **not** in `grounded-research/specs/` (TTB alcohol, FDA NLEA / 21 CFR 101, EU 1169 amendments past 2024, Prop 65, USDA NOP, EU Cosmetics Reg 1223/2009, state-level cannabis), one targeted WebSearch + WebFetch per regulation is acceptable; cite the URL in the per-check research note.

## Per-check research template

Every check that lands in the Phase 1 backlog gets one row in `audit/phase-1/check-research/<inspection_id>.md` with this shape:

```markdown
# <inspection_id> — <friendly name>

## Source of truth
- Spec: <e.g. ISO 32000-2 §8.4.5 / GWG 2022 §A1.4 / FDA 21 CFR 101.9>
- PitStop equivalent: <PitStop check name + category, citing pitstop-checks-catalog.md line>
- Competitor equivalent: <Callas pdfToolbox / Markzware FlightCheck if known>
- lintPDF current behaviour: <"emits in <file>:<line>" / "stub" / "absent">

## Semantic definition
<2-4 sentences: what is the underlying problem this check detects? In what
production context does it bite (digital press / flexo / offset / web /
foil-stamp / packaging)? Cite spec section + page.>

## Inputs the analyzer needs
- <ordered list — e.g. "every TextRenderedEvent with effective_x_height_mm",
  "ICC output intent dict", "page MediaBox + TrimBox", "tenant.industry_type">

## Pass / fail rule
<Pseudocode for the decision. Reference shared helpers (text_metrics,
nfp_detector, _gates) where applicable.>

## Severity defaults
- lintPDF default: <advisory|warning|error>
- PitStop default: <quote>
- Rationale for any divergence: <1 sentence>

## Edge cases / known false-positive vectors
- <e.g. "outlined glyphs (rendering_mode=3) — use bbox height not Tf">
- <e.g. "Prop 65 'WARNING' must not match GHS 'WARNING'">

## Phase 2 implementation outline
- Files to touch: <list>
- New helpers needed: <list>
- Tests required: <list of cases — minimum: one true positive, one true negative,
  one regression-from-known-FP>

## Read-only constraint
Confirm: this check is pure inspection. Remediation is structured guidance in
the report — no PDF mutation. Spell out the remediation text the report should
emit when the check fails.

## Research log
- <date> — <agent or operator initials> — <what was checked / decided>
```

## Stub analyzer triage (Phase 1.A backlog)

The four catalogued stubs (`AI_ALC_001`, `AI_CANN_001`, `AI_COSM_001`, `AI_ORG_001`) plus the four uncatalogued stubs flagged in `blast-radius-ai.md` each get a one-page research note **before** Phase 2 picks the first one for implementation. The research note answers three questions:

1. **Is this regulation real and enforced?** (TTB and FDA NLEA: yes. State cannabis: per-state, big surface area. EU Cosmetics: yes, mandatory INCI nomenclature. USDA Organic: yes for "Organic"/"100% Organic" claims.)
2. **What signal does the analyzer need?** (Pixel-level OCR? Vector text spans? Symbol detection? Specific-language text scan? Spot/Pantone colour match?)
3. **Is the signal feasible without GPU inference, or is `tier=gpu` non-negotiable?** (If non-negotiable, the catalog should mark the check as "GPU-only" so non-GPU tenants don't see a toggle that does nothing. If feasible on CPU via deterministic vector-text scan + token list, downgrade `tier` and implement.)

Phase 2 picks stubs in order of (regulation enforcement risk × tenant demand × feasibility-without-GPU).

## Existing-check research (Phase 1.B backlog)

For every existing check that scored **high blast radius** in `blast-radius.md` AND has known-disputed Opus rows in `docs/audits/raw/*.json`, run the same research template and capture:

- The **Opus dispute reason** verbatim (e.g. "x-height 0.17 mm at 1.0 pt on a 19 mm logo — calculation ignored CTM scale").
- Which spec the dispute resolution should cite (e.g. ISO 32000-2 §8.3.4 — text-state to user-space transform composition).
- Whether the fix is rule-tightening (Phase 2) or rule-replacement (Phase 3).

Phase 1 priority scoring uses the result.

## Out of scope for Phase 1 research

- New rule families that aren't in the playbook's Tier 1-5 gap list.
- Re-litigating decisions already locked in earlier WS plans (effective x-height helper, NFP detector, Prop 65 proximity exclusion).
- Catalog naming convention normalisation (`ai:fda` vs `ai_regulatory_compliance`) — purely cosmetic, not blocking research.

## Why this approach

Quincy's directive: don't shortcut to "implement the stub" — research first. Most stubs hit regulations where the wrong heuristic creates **legal liability for the print buyer** (e.g. flagging a non-Prop-65 product as Prop-65-compliant or vice versa). One bad stub is worse than no stub. The per-check note forces the spec citation and the false-positive analysis before any code lands.
