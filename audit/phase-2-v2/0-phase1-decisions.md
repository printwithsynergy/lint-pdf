# Phase 1 Q&A — Operator Decisions

**Date:** 2026-04-25
**Operator:** Quincy

## Decisions

### Q1 — v0 limitations
**Decision: Accept; catch in Phase 2 design notes.**

Phase 1.1 agent's tier/wave classification biases (defaulted to T2 / Wave D)
are accepted as v0 baseline. Per-check Phase 2 design notes will catch and
correct individual misclassifications during design review.

### Q2 — Phase 2 sequencing
**Decision: Parallel start now.**

Phase 2.0 Tier-0 primitives + Wave V V-07/V-08/V-12 ship simultaneously.
No inconsistent-foundation risk because primitives have no toggleable knobs.

### Q3 — Tier-0 batch granularity
**Decision: By category (~11 batches).**

Batches:

| # | Category | Primitive count (approx) |
|--:|----------|--:|
| 01 | Object-class predicates | 8 |
| 02 | Color-space predicates | 14 |
| 03 | Ink predicates | 7 |
| 04 | Geometry / page-box predicates | 10 |
| 05 | Stroke / fill predicates | 5 |
| 06 | Transparency-stack predicates | 6 |
| 07 | Text predicates | 10 |
| 08 | Image predicates | 8 |
| 09 | Page / structure predicates | 5 |
| 10 | Document / metadata predicates | 10 |
| 11 | Barcode predicates | 7 |
| | **TOTAL** | **~84** |

### Q4 — Wave V V-07/V-08/V-12 design defaults
**Decision: All 4 approved as listed.**

1. Toggle.id naming: **dot-notation** (e.g. `checks.F-22.severity_override`)
2. Workflow inheritance from another workflow: **NO** for v2.0; revisit v2.1
3. Lockable scope: **only tenant** for v2.0
4. ConfigAuditLog retention: **365 days default**, tenant-overridable

Per-batch operator review continues per playbook §2.3.
