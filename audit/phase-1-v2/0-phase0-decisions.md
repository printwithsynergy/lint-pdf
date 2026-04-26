# Phase 0 Q&A — Operator Decisions

**Date:** 2026-04-25
**Operator:** Quincy

## Decisions

### Q1 — Wave V foundation sequencing
**Decision: Parallel with Tier-0 primitives.**

Wave V V-07 (toggle resolver), V-08 (audit log), V-12 (legacy migration)
ship in parallel with Wave 0 Tier-0 primitives. Primitive registry
introduces no toggleable knobs so no inconsistent foundation. Wave A's
first toggleable knob waits for V-12 to land.

**Implication:** Phase 2 sequence becomes:

```
Phase 2.0 (Tier-0 primitives, 3.0 EM)        \
                                                  ─── parallel ───
Wave V V-07 / V-08 / V-12 (~3.5 EM subset)    /

Then: Wave B (T1 catch-up) → Wave A (T3 wedge) → Phase 2.EPM
      → Wave V remaining (V-01..V-06, V-09..V-11, V-13)
      → Wave D → Wave C → Wave E
```

### Q2 — Remediation plan
**Decision: All 14 rows approved as listed.**

`audit/phase-0-v2/0.7-config-cascade-audit.md §0.7.2` rows R-Q1..R-Q20
approved. Wave V V-07/V-08/V-12 design starts immediately.

### Q4 — Phase 1 ID projection
**Decision: Full per-ID semantic projection.**

Phase 1.1 reads every analyzer's emit logic and explicitly matches each
v2 ID against existing engine emits. ~2–3 day exercise per playbook.
Highest accuracy; most complete backlog upfront. **No heuristic
shortcuts.**

### Q5 — Phase 5 timing
**Decision: Hybrid — incremental code-facing docs + end-loaded marketing.**

- **Per-wave (incremental):** OpenAPI 3.1, Postman collection delta,
  reference docs for shipped checks, SDK reference, changelog entry
- **End-loaded at v2.0 launch:** Marketing site, sales collateral,
  comparison pages, blog/social campaign, knowledge base sweep,
  legacy URL 301 reconciliation

## Implicit

### Q3 — v2 playbook + universe enumeration disk persistence
**Status: deferred (no operator request for retype).** Conversation context
is authoritative for v2 playbook content during this session. If operator
later requests `retype`, assistant writes the files via Bash heredoc chunks.
