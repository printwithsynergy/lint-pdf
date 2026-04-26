# Phase 1 — Sequencing Memo

**Date:** 2026-04-25
**Decision source:** `audit/phase-1-v2/0-phase0-decisions.md` Q1
**Operator:** Quincy

## Sequencing decision

Wave V foundation (V-07 toggle resolver, V-08 audit log, V-12 legacy
migration) ships **in parallel** with Phase 2.0 Tier-0 primitives. Wave A's
first toggleable knob waits for V-12 to land.

## Detailed timeline

```
            Phase 2.0 — Tier-0 primitives (3.0 EM)         ┐
            (84 atomic predicates → primitives/ module)    │
                                                           │ parallel
            Wave V V-07/V-08/V-12 (~3.5 EM subset)         │
            (toggle registry + cascade resolver +          │
             config audit log + legacy migration script)   ┘
                                ▼
                        Wave V V-07/V-08/V-12 verified
                        Tier-0 primitives shippable
                                ▼
                Wave B (T1 catch-up, 1.0 EM)
                (per-v2-ID gap from Phase 1.1 — fine-grained)
                                ▼
                Wave A (T3 dieline wedge, 3.5 EM)
                (D-* + adjacent F-/P-/L-/T- expansions)
                                ▼
                Phase 2.EPM (2.5 EM)
                (Core + Advanced + AI-Explain + BYO §9)
                                ▼
            ┌────────────────────────────────────────┐
            │ Wave V remaining (V-01..V-06,           │
            │ V-09..V-11, V-13)                       │
            │ ~6 EM, parallel from here               │
            └────────────────────────────────────────┘
                                ▼
                Wave D (T2 parity, 2.0 EM)
                                ▼
                Wave C (T4 packaging specialty, 4.0 EM)
                                ▼
                Wave E (T5 regulatory, 2.0 EM)
                                ▼
                Phase 3 — Integration & profile audit (0.5 EM)
                                ▼
                Phase 4 — Internal release prep (1.0 EM)
                                ▼
                Phase 5 — End-loaded marketing sweep (~6 EM)
                (incremental code-facing docs already shipped per wave)
                                ▼
                                v2.0 release tag
```

## Critical-path EM tally

| Phase / Wave | EM | Dependencies |
|--------------|---:|--------------|
| Phase 2.0 — Tier-0 | 3.0 | none |
| Wave V V-07/V-08/V-12 | 3.5 | none (parallel with Tier-0) |
| Wave B | 1.0 | Tier-0 |
| Wave A | 3.5 | Tier-0 + Wave V V-07 |
| Phase 2.EPM | 2.5 | Tier-0 + ICC engine for Advanced |
| Wave V remaining | 6.0 | Tier-0 + Wave V V-07/V-08/V-12 |
| Wave D | 2.0 | Tier-0 + Wave V V-07 |
| Wave C | 4.0 | Tier-0 + Wave A + Wave V V-07 |
| Wave E | 2.0 | Tier-0 + Wave V V-07 + Phase 2.EPM (for VDP/EPM-AI overlap) |
| Phase 3 | 0.5 | all waves |
| Phase 4 | 1.0 | Phase 3 |
| Phase 5 (incremental) | spread across waves | per wave |
| Phase 5 (end-loaded marketing) | ~6 | all waves complete |
| **TOTAL** | **~35 EM** | (subtracting v1's ~4 EM already burned) |

## Why this order

1. **Tier-0 first because every wave consumes primitives.** Building user-facing checks before primitives means re-implementing the predicate stack per check. Centralizing first reduces total LOC across waves and locks in a uniform testable foundation.

2. **Wave V V-07/V-08/V-12 parallel with Tier-0 because foundations have no toggleable knobs.** The primitive registry doesn't need a tenant override or audit log — primitives are pure functions. Wave V foundation work touches the app + Prisma + tRPC + desktop, which don't overlap with primitive code in the engine.

3. **Wave B before Wave A because T1 gaps make a tool look amateur.** Even though v1 closed all 93 v1 gaps, Phase 1.1 will identify v2-specific T1 gaps (likely 1–3 IDs); fix those before launching the differentiator wedge.

4. **Wave A immediately after because it's the marketing story.** T3 dieline wedge defines lintPDF's identity. v1 already covered 15 of the 24 wedge IDs; Wave A is the expansion to all 24 D-* slots + adjacent F/P/L/T checks.

5. **Phase 2.EPM after Wave A because EPM reuses Wave A's per-separation rasterization.** The marginal cost of EPM Core is lower if Wave A ships first.

6. **Wave V remaining (V-01..V-06, V-09..V-11, V-13) parallel from Phase 2.EPM onward because the finding-emission contract is stable.** Once the §7 `remediation` field is wired into FindingResponse and Tier-0 primitives are shipping, the viewer overlay can evolve in parallel without coupling to subsequent check waves.

7. **Wave D parity backfills in parallel with EPM.** Most Wave D IDs are extensions of existing analyzers (color.py, transparency.py, font.py, image.py, page_geometry/*) — small per-ID cost.

8. **Wave C is where the packaging-native vertical case-study material comes from.** Braille decoding (BR-05) is the single hardest item; allocate accordingly.

9. **Wave E is paid add-on territory** — pharma, alcohol, tobacco, cosmetics, FDA UDI, EU DPP. Off by default; tenants enable via tier flag.

## Locking decisions

- **Tier-0 primitives module location:** `packages/engine/src/lintpdf/primitives/`
- **Wave V V-07/V-08/V-12 location:** `packages/app/server/routers/{workflow,toggle,audit}.ts` + `packages/app/prisma/schema/{workflows,toggles,audit-log}.prisma` + `packages/app/scripts/migrate-legacy-config.ts`
- **EPM module location:** `packages/engine/src/lintpdf/epm/`
- **BYO §9 endpoint location:** `packages/engine/src/lintpdf/api/routes/byo.py` + `packages/engine/src/lintpdf/byo/`

## Hard rule reminder

Per playbook §17.3: **No new toggle is added on top of an inconsistent
foundation.** Wave V V-07 + V-08 + V-12 must complete before Wave A's
first toggleable knob lands. Tier-0 primitives have no toggleable knobs,
so Tier-0 work is unblocked.

## Risk callouts

1. **Shared DB migration risk** — Wave V V-12 needs the `startup.sh` raw-SQL fallback per CLAUDE.md "Shared Database" section. Dry-run in staging with full engine-table seed.
2. **Per-tenant cascade resolver perf** — every job now passes through resolver. Cache resolved config per tenant+workflow; invalidate on config write.
3. **Desktop sync protocol** — V-13 needs careful design to avoid silent config drift between offline edits and server canonical.
4. **EPM Advanced device-link** — gated on ICC engine integration. Until that lands, EPM-Advanced is dark; EPM-Core ships independently.
5. **LLM cost cap default-off** — EPM AI-Explain stays off until tenant explicitly sets cost cap. Per playbook §16.6: silent no-op with audit-log entry if cost cap unset.

## Approval

Quincy approved sequencing in Phase 0 Q&A Q1 ("Parallel with Tier-0 — Recommended"). No further sign-off required for this memo.

If sequencing changes mid-stream (e.g., Wave A wedge needs to ship faster for marketing), revisit this memo and re-run the dependency graph.
