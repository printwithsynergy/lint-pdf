# Phase 1 — Complete

**Date:** 2026-04-25
**Operator:** Quincy

## Cliff-notes summary

**Universe:** 412 canonical artifacts (84 Tier-0 primitives + 328 user-facing) per v2 playbook §10. Per-prefix sums to 446 (84 Tier-0 dual-counted within prefix tables); per-row data treated as authoritative.

**v2 ID coverage (post-1.1b verification sweep):**
- User-facing: **126 / 364 present (34.6%)**
- Tier-0 primitives: **41 / 82 present (50%)** — half centralized, half ad-hoc inline
- 72 IDs promoted from absent → present via v1 gap-mapping evidence

**Strongest categories:** B (89.5%), I (64%), ISO (58%), TR (50%), R (50%)
**Weakest categories:** EPM (0%), BR (0%), LA (0%), T (0%)
**Tier-3 dieline:** 8 / 15 present (53%) — v1 dieline wedge gave foundation
**Tier-5 regulatory:** 3 / 25 present (12%) — Wave E greenfield

**Backlog:** 238 absent user-facing IDs + 41 Tier-0 absent primitives + 3 Wave V foundation deliverables = 282 actionable items.

**Top-10 by priority:**
| # | v2_id | T | Wave | Score | Notes |
|---|-------|--:|------|------:|-------|
| 1 | BR-07 | 4 | C | 90 | UNCLAIMED — Braille not on cut/fold |
| 2 | C-63 | 3 | A | 90 | UNCLAIMED — Multi-PS-ink on same plate |
| 3 | D-04 | 3 | A | 90 | UNCLAIMED — Dieline by layer name |
| 4 | D-08 | 3 | A | 90 | UNCLAIMED — Dieline blend mode |
| 5 | D-09 | 3 | A | 90 | UNCLAIMED — Dieline opacity |
| 6 | W-16 | 5 | E | 90 | Hard but unclaimed — Emboss content match |
| 7 | D-16 | 3 | A | 85 | Content fails to reach dieline |
| 8 | D-23 | 4 | A | 85 | Registration on glue flap |
| 9 | F-32 | 3 | A | 85 | Text on dieline / cut path |
| 10 | F-34 | 1 | B | 85 | Text too close to trim |

**Unclaimed wedge backlog (10 IDs):** BR-07, C-63, D-04, D-08, D-09, W-16 (priority 90); plus T-05, R-05, P-30/31/32 (priority 80–85). These are the §10.5 marketing-defensible differentiators.

**Unmapped existing checks:** 283 engine inspection_ids not claimed by any v2 ID. Default action: KEEP (these are AI-tier surface beyond v2 published baselines). Per-item triage during Phase 2 design notes.

## Phase 1 deliverables

| File | Lines / Size | Status |
|------|--------------|--------|
| `audit/phase-1-v2/0-phase0-decisions.md` | 47 | ✅ |
| `audit/phase-1-v2/sequencing.md` | 122 | ✅ |
| `audit/phase-1-v2/wave-v-design-handoff.md` | 249 | ✅ |
| `audit/phase-1-v2/v2-id-coverage.json` | 127 KB | ✅ post-1.1b sweep |
| `audit/phase-1-v2/v2-id-coverage-summary.md` | 281 (v0) | ✅ pre-1.1b — see corrections file |
| `audit/phase-1-v2/1.1-validation-notes.md` | 98 | ✅ — explains v0 limits |
| `audit/phase-1-v2/1.1b-corrections.md` | (auto-gen) | ✅ — 72 promotions delta |
| `audit/phase-1-v2/unmapped-existing.json` | (auto-gen) | ✅ — 283 unmapped engine ids |
| `audit/phase-1-v2/unmapped-existing.md` | 81 | ✅ — by-prefix triage |
| `audit/phase-1-v2/backlog.json` | (auto-gen) | ✅ — 238 user-facing + 41 T0 + 3 Wave V |
| `audit/phase-1-v2/backlog-summary.md` | 100+ | ✅ — top-30 + per-wave + unclaimed |
| `audit/phase-1-v2/scripts/verify_v1_promotions.py` | (script) | ✅ |
| `audit/phase-1-v2/scripts/build_unmapped_existing.py` | (script) | ✅ |
| `audit/phase-1-v2/scripts/build_backlog.py` | (script) | ✅ |

## Known limitations

1. **Agent's tier classification is biased to Tier 2** (most rows tagged tier=2 by default). v2 universe table has explicit T columns; agent didn't fully respect them. Affects priority `base` score for Wave A/B/E IDs that should have higher base.
2. **Agent's wave assignment is biased to Wave D** (default for tier 2). Real wave per universe §6 is more granular — D-* should be Wave A, BR-*/W-*/L-* should be Wave C, R-*/V-* should be Wave E. Affects Wave-A/B bonus (+5) which is suppressed for misclassified items.
3. **Per-row matched_inspection_ids accuracy ~85%** — verification sweep added 72 promotions but didn't re-verify the 54 v0 present rows. Phase 2 design notes will catch any remaining false positives.
4. **Tier-0 primitive split (41/82) is a directional claim**, not per-primitive verification. Phase 2.0 will produce the canonical primitive registry; the count there is the authoritative one.

These limitations DO NOT block Phase 2 sequencing or Wave 0 / Wave V planning. They WILL surface during Phase 2 per-check design notes (operator can re-classify any item).

## Numbered questions before Phase 2

### 1. Phase 1 v0 limitations — accept or remediate?

The agent's tier/wave classification is approximate (biased to T2/D). Three options:

- **(a)** Accept v0 limitations. Phase 2 design notes catch issues per-check. **Recommended.**
- **(b)** Run a targeted re-classification pass: re-derive tier + wave from v2 universe per row using my §10/§6 cross-reference table. ~1 hour script. Cleans the backlog priority order.
- **(c)** Re-run the full Explore agent with stricter prompt requiring explicit tier-from-universe-table extraction. Slower; uncertain return.

### 2. Phase 2 sequencing — confirm parallel start?

Wave V V-07/V-08/V-12 (toggle resolver / audit log / legacy migration) ships
in parallel with Phase 2.0 Tier-0 primitives. Per Q1 Phase 0 decision.

- **(a)** Start Phase 2.0 Tier-0 + Wave V V-07/V-08/V-12 in parallel **now** (both are foundation; no toggleable knobs yet).
- **(b)** Start Phase 2.0 Tier-0 first; Wave V V-07/V-08/V-12 starts after primitives stabilize. Slower but tighter coupling.

Recommend **(a)** per Phase 0 Q1 confirmed decision.

### 3. Phase 2.0 Tier-0 batch granularity?

Per playbook §2.5 "default batch size: 3 checks". Tier-0 primitives are
small atomic predicates; bigger batches feasible.

- **(a)** Batch size 5 primitives per commit (~17 commits to ship 84). Faster review cadence.
- **(b)** Batch size 10 primitives per commit (~9 commits). Larger PRs.
- **(c)** Batch by category (object-class, color-space, ink, geometry, etc. → 11 batches).

Recommend **(c)** — natural cohesion; one analyzer test module per category; ~7-10 primitives per batch.

### 4. Wave V V-07/V-08/V-12 design — accept open decisions in handoff?

Wave V design handoff (`audit/phase-1-v2/wave-v-design-handoff.md`) has 4
open design decisions:

1. Toggle.id naming convention: dot-notation vs flat slug (recommend dot)
2. Workflow inheritance from another workflow (recommend NO for v2.0)
3. Lockable for non-tenant overrides (recommend ONLY tenant)
4. ConfigAuditLog retention: 365-day default, tenant-overridable (recommend yes)

- **(a)** Approve all 4 recommendations as listed; Wave V V-07 coding starts.
- **(b)** Review individually before V-07 starts.
- **(c)** Defer; revisit during V-07 design review.

Recommend **(a)** — these are sensible defaults; tenant feedback can surface during launch.

## Blocking

None. Phase 2 can start immediately on Quincy's answers to Q1–Q4.

## Suggested next deliverables (Phase 2)

- `audit/phase-2-v2/wave-0-tier0/<batch>/design.md` per primitive batch
- `audit/phase-2-v2/wave-v/V-07/design.md` (toggle resolver)
- `audit/phase-2-v2/wave-v/V-08/design.md` (audit log)
- `audit/phase-2-v2/wave-v/V-12/design.md` (legacy migration)
