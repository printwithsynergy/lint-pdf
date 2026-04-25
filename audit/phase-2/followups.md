# Phase 2 — deferred follow-ups

Tracked here so nothing slips. Each entry becomes its own commit / PR
when the triggering pattern is ready.

## FUP-1 — Rules-tab "PDF version constraints" widget ✅ DONE

**Trigger:** operator re-scoped 2026-04-24: "I want done and not deferred."

**Shipped as** `packages/app/components/rules/ThresholdsPanel.tsx`
mounted at the top of the Rules tab on `/dashboard/rulesets/[id]` +
`/dashboard/admin/rulesets`.

- Collapsible "Thresholds" section, first block = PDF version
  constraints (min / max).
- Two text inputs with `<datalist>` dropdown (1.3 / 1.4 / 1.5 / 1.6 /
  1.7 / 2.0).
- Live validation: rejects non-version strings, flags `min > max`.
- Empty → stripped (no `undefined` key in JSON tab on round-trip).
- Live-syncs `profile.thresholds.min_pdf_version` /
  `max_pdf_version` through the existing RulesEditor
  `onChange` hook; saves via WS-16's PATCH route unchanged.

**New shared pattern.** The `ThresholdsPanel` container is
deliberately generic so subsequent threshold groups (TAC limit,
expected page size from T1-STR04, hairline threshold, etc.) can land
in the same block without restructuring the page. When Phase-2
Batch 2+ thresholds want UI surfaces, extend `ThresholdsPanel` with
additional section components — one pattern to learn, not one widget
per profile field.

## FUP-2 — Review-question answers inbox

Waiting on operator answers for the Batch 1 review-question docs:

- `audit/phase-2/T1-I07/review-questions.md`: Q1 SPLIT (addressed —
  commit pending in this session).
- `audit/phase-2/T1-F04/review-questions.md`: Q2 tradeoff written at
  `T1-F04/q2-tradeoff.md`; Q1 / Q3-Q9 still open.
- `audit/phase-2/T1-CMP02/review-questions.md`: Q10 deferred; Q1-Q9
  still open.

Each `status.md` stays unlisted (not "verified") until the remaining
questions are answered.

## FUP-3 — T1-F04 bits 8/9 optional promotion

See `T1-F04/q2-tradeoff.md`. Recommendation: keep current info-only
design. If operator overrules: promote bit 8 (`no_subsetting`) with
conditional firing (only when `font.subset == True`) as LPDF_FONT_016.
Bit 9 (`bitmap_only`) is harder and can stay info-only regardless.

## FUP-4 — docs-parity for LPDF_IMG_018/019/020, LPDF_FONT_015, LPDF_DOC_009

Per `CLAUDE.md` docs-parity rule: every new check surfacing in the
rules editor should land in `packages/web/src/content/docs/checks.md`
(if it exists) and any JSX API reference. Batch 1 landed the checks
in the engine + catalog but the marketing docs haven't been touched.

**Next step:** audit `packages/web/src/content/docs/` for a checks
reference file; if absent, add an entry per new ID in
`ChecksPage.tsx`. This can roll up into Phase 4 (Documentation +
Release Prep) per the playbook.
