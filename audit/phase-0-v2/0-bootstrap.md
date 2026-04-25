# Phase 0.0 — v2 Bootstrap

**Date:** 2026-04-25
**Branch:** `claude/add-preflight-testing-4C2b3` (feature) ; main is up-to-date with v1 work merged
**Operator:** Quincy

## Acknowledgment

Entering Phase 0 — Self-introspection and discovery against
`lintpdf-check-audit-playbook-v2.md` (the v2 combined playbook).

**Read-only constraint:** internalized. lintPDF NEVER mutates input PDFs.
Every check is pure inspection; remediation is structured advice in the
report, never a modified file.

**Production-readiness contract:** internalized. No `TODO`, `FIXME`,
`XXX`, `HACK`, `PLACEHOLDER`, `Lorem ipsum`, `stub`, `mock`, "implementation
pending", or "coming soon" in production paths. No commented-out code.
No skipped tests. No deferred deliverables. CI must enforce a grep
against production directories.

**Config cascade:** internalized. Tenant → workflow → per-call override,
identical across HTTP API, SDK, and desktop app. Single canonical store.
Legacy patterns get migrated, not grandfathered.

## Bootstrap actions completed

| Step | Action | Status |
|------|--------|--------|
| 1 | Confirm v2 playbook readable | ✓ — content authoritative in conversation context |
| 2 | Create `audit/` directory | ✓ — already existed (v1 work) |
| 3 | Move v1 playbook to `audit/_archive/v1/` | ✓ — `git mv audit/lintpdf-check-audit-playbook.md audit/_archive/v1/lintpdf-check-audit-playbook.md` |
| 4 | Save v2 playbook to repo root + `audit/` | **deferred** — see below |
| 5 | Extract Appendix A as `lintpdf-v2-universe-enumeration.md` at root + `audit/` | **deferred** — see below |
| 6 | Verify both files exist with line counts + SHA256 | **deferred** — pending step 4/5 |
| 7 | Confirm to operator | this file |
| 8 | Begin Phase 0.1 | proceeding |

## Deferral rationale (steps 4–6)

The v2 playbook (~1,100 lines) and universe enumeration (~700 lines) total
~1,800 lines / ~70KB. Operator pasted both as a single chat message rather
than saving as files; retyping them verbatim across tool calls would consume
~25–30KB of output-context tokens and many tool calls.

Pragmatic path agreed at start of Phase 0: operator saves both files himself
via clipboard paste; assistant copies them into `audit/` and verifies with
SHA256 once they exist on disk. Within this session, conversation context
is authoritative for v2 playbook content and is referenced by all Phase 0
deliverables.

If operator subsequently issues `retype`, assistant will write both files
incrementally via Bash heredocs.

## Persistence contract

This bootstrap file IS persisted. All subsequent Phase 0 deliverables ARE
persisted. The only deferred persistence is the verbatim playbook + universe
files themselves, which are duplicated content (already in conversation
history). No information is lost.

## Phase 0 plan

| Section | Deliverable | Status |
|---------|-------------|--------|
| 0.0 | Bootstrap (this file) | done |
| 0.1 | Repo inventory | next |
| 0.2 | Existing check inventory + v1→v2 projection | pending |
| 0.3 | Infrastructure inventory | pending |
| 0.4 | Blast radius map | pending |
| 0.5 | BYO mode readiness | pending |
| 0.6 | Viewer & overlay infrastructure | pending |
| 0.7 | Config cascade audit (incl. desktop) | pending |
| 0.8 | Surface parity check (API/SDK/desktop) | pending |
| End | Q&A gate to operator | pending |

## v1 → v2 treatment policy (operator-confirmed)

Most-comprehensive approach: re-project v1's 93 closed gaps + 421 inspection
catalog IDs into v2's F-/C-/I-/TR-/P-/LA-/M-/L-/D-/W-/BR-/B-/T-/S-/V-/WF-/R-/ISO-/EPM-
taxonomy as the v2 baseline (gives v1 credit, avoids redoing working code),
then run a clean v2 audit on top to surface what v1 didn't deliver:
Tier-0 primitives, EPM module, BYO viewer-only, Wave V (viewer/decisions/
webhooks/toggles), production-readiness CI grep, Phase 5 doc/marketing audit,
surface parity (API/SDK/desktop).

This is more work than either alone but is the only honest way to close
the gap without double-work or silent omission.

## v1 baseline summary (from prior work merged to main)

- Catalog: 421 inspection IDs in `packages/app/lib/rules/check-catalog.json`
- v1 gap-mapping: 93/93 present at `audit/phase-1/gap-mapping.json`
- 11 implementation batches landed (Batch 1–11 + sub-batches 9a/9b/9c, 10a/10b)
- Engine analyzers shipped: spot taxonomy, transparency T2-TRN04..06, metadata
  T2-XMP01 / T4-A10 / T5-N09 / T5-N10, hairline T2-RB02/03, PDF/VT structure,
  GS1 AI / UDI / EU DPP barcode validators, regulatory bodies (alcohol,
  cannabis, cosmetics), tobacco warning area, GWG 2022 profile pack (45
  profiles), accessibility trio T4-A06/07/09
- Last merge to main: `ebabd5c` (Batch 11 — promote 5 partials to present)

The 93/421 numbers are v1-specific; v2's universe is 412 artifacts (84 Tier-0
primitives + 328 user-facing) which v1 did not enumerate. Phase 0.2 will
produce the v1 → v2 projection.
