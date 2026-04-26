# lintPDF Check Audit + Implementation Playbook

> **Purpose.** Drive Claude Code through a full agentic loop: audit what preflight checks lintPDF currently implements, compare against the prioritized gap list, plan implementations for missing checks, implement them, and iterate — using **Question & Answer gating** at every ambiguity instead of guessing.
>
> **Mode.** Discovery-first. Phase 0 is mandatory. Do not write code before Phase 0 completes and the operator (Quincy) has answered outstanding questions.
>
> **Operator.** Quincy. Terse, direct, INTJ. Wants cliff-notes summaries, not verbose progress narration. Ask concrete questions; don’t ask obvious ones.

-----

## Launch instructions (save this file, then paste the prompt below)

**Step 1.** Save this entire file to the root of the lintPDF repo as `lintpdf-check-audit-playbook.md`. If an `audit/` directory doesn’t exist at the repo root, the playbook will create it.

**Step 2.** Open Claude Code in the lintPDF repo root and paste this prompt verbatim:

```
Read `lintpdf-check-audit-playbook.md` at the repo root. This is your
authoritative operating document for this session and every future session
you're invoked on this repo. Follow it literally.

CRITICAL PRODUCT CONSTRAINT: lintPDF is read-only. It NEVER modifies,
rewrites, re-saves, flattens, re-tags, or otherwise mutates any input PDF.
Every check is pure inspection. Where a check would naturally imply a fix
(e.g., "set dieline to overprint"), lintPDF emits structured remediation
guidance in its report — never a mutated file. If you ever find yourself
writing code that produces a modified PDF as output, stop immediately and
redesign.

Before any other action:
1. Confirm you can read the playbook. Reply with a one-line acknowledgment
   that lists the phase you're entering and the first action you'll take,
   and that you've internalized the read-only constraint.
2. Save a copy of the playbook into `audit/lintpdf-check-audit-playbook.md`
   (create the `audit/` directory if it doesn't exist). This becomes the
   persisted, session-stable reference. All phase artifacts you produce go
   under `audit/phase-<N>/...` as specified.
3. Start Phase 0 — Self-introspection and discovery. Do not skip steps.
   Do not write production code in Phase 0.
4. Respect every Q&A gate. When a gate is reached, stop and ask me the
   numbered questions. Wait for my answers before proceeding.
5. Cliff-notes summaries only at phase boundaries. Full detail goes in the
   phase log files, never in chat.

If anything in the playbook conflicts with another instruction source, the
playbook wins. If the playbook is ambiguous on a specific point, ask — do
not guess.

Begin.
```

**Step 3.** Answer Claude Code’s Phase 0 questions when it asks. Phase gates are your decision points.

-----

-----

## Core operating principles

1. **lintPDF is READ-ONLY. Never mutates PDFs. Ever.** This is a hard product constraint, not a preference. lintPDF inspects, measures, reports, and returns findings. It **does not** write, patch, re-save, re-encode, flatten, convert, re-tag, or otherwise modify any input PDF. There is no “auto-fix” output that touches the file. If a check’s natural expression in other tools includes a fix (e.g., PitStop’s auto-overprint-correct), lintPDF’s equivalent emits a **recommended remediation** in the report JSON — a structured description of what *should* change and where — never a mutated PDF. Any design note, code path, or backlog item that implies file mutation is a bug. Reject it or rewrite it as a reporting-only check.
1. **Q&A gates, not guessing.** Whenever you hit a decision point that isn’t determinable from the codebase, stop and ask Quincy a numbered question. Never “pick a reasonable default” silently. Batch questions (3–5 at a time) when possible.
1. **Phase gates.** Each phase has an explicit completion criterion. Do not start Phase N+1 until Phase N’s criterion is met and its summary is written to the phase log.
1. **Blast radius before code.** Every file you would touch gets identified, blast radius assessed, and confirmed with Quincy before edits begin.
1. **Source of truth is the gap list.** The Tier 1–5 gap list at the bottom of this file is the canonical check inventory. If you discover a check that exists in the codebase but isn’t in the gap list, flag it as “unmapped” and ask.
1. **No silent scope creep.** If implementing check X reveals the need for check Y, Y is a new ticket, not an in-flight addition.
1. **Cliff-notes in, cliff-notes out.** Your summaries at phase boundaries are ≤10 bullets. Full detail goes in the phase log file, not chat.

-----


## Phase 0 — Self-introspection and discovery

**Goal.** Understand the lintPDF codebase well enough to answer: *which of the ~1,500 checks catalogued in the competitive analysis does lintPDF already implement, even partially?*

**Do not write any production code in Phase 0.** Read-only exploration, plus a machine-readable audit file.

### 0.1 Repo inventory

1. Read the root `README.md`, `package.json`, `tsconfig.json`, `.env.example`, and any top-level `ARCHITECTURE.md` / `CONTRIBUTING.md` / `docs/` entries.
1. Map the directory structure (max depth 4). Summarize each top-level folder in one sentence.
1. Identify the entry points:
- The PDF parsing layer (which library — pdfcpu, pdf-lib, mupdf, etc.?)
- The check/rule definition layer (where are checks declared?)
- The profile layer (how are checks grouped into profiles?)
- The reporting layer (what does output JSON look like?)
- The API surface (HTTP routes, CLI, SDK export?)
1. Run the existing test suite with `npm test` (or equivalent) and record: passing count, failing count, coverage % if reported.

**Deliverable.** `audit/phase-0/repo-inventory.md` with the above.

**Q&A gate.** Before proceeding, ask Quincy:

- "I found the check layer at `<path>`. Is that the only place, or are there checks scattered elsewhere?"
- "Tests in `<path>` — is this the authoritative suite, or are there integration tests elsewhere?"
- Any question where the repo structure is genuinely ambiguous.

### 0.2 Existing check inventory

Build a machine-readable file listing every check lintPDF currently has.

**Format.** `audit/phase-0/existing-checks.json`:

```json
{
  "checks": [
    {
      "id": "string (internal lintPDF identifier)",
      "human_name": "string",
      "category": "font | color | image | transparency | structure | metadata | packaging | accessibility | other",
      "source_file": "relative path",
      "emits_remediation_guidance": true,
      "profiles_using_it": ["PDF/X-4", "GWG-Sheet"],
      "description": "what it actually detects, 1 sentence",
      "notes": "any quirks"
    }
  ]
}
```

> `emits_remediation_guidance` = does the check's report output include structured "how to fix this upstream" guidance (for the designer, prepress op, or automation layer outside lintPDF)? lintPDF itself never mutates the PDF.

**Method.** Grep/ripgrep the codebase for check definitions. Read each one. Do not paraphrase descriptions — record what the code actually does. If a check's behavior is unclear from reading it, add `"needs_clarification": true` and list it in the Q&A batch.

**Deliverable.** The JSON file + a 1-page Markdown summary at `audit/phase-0/existing-checks-summary.md` (counts by category, notable gaps you already see).

### 0.3 Blast radius map

For each file that will likely be touched during implementation:

- Path
- Current LOC
- Exports consumed by which other files (ripgrep for imports)
- Test coverage of that file
- Risk level: low / medium / high

**Deliverable.** `audit/phase-0/blast-radius.md`.

**Q&A gate (end of Phase 0).** Send Quincy a cliff-notes summary:

```
Phase 0 complete.

Repo: <N lines, <M files, <test result>.
Existing checks: <X> implemented, <Y> partial, <Z> need clarification.
Check layer lives at: <path>
Profile layer: <path>
Test pattern: <describe>

Questions before Phase 1:
1. ...
2. ...
3. ...

Blocking: none | <list>
Ready to map Phase 0 → gap list when you answer.
```

**Completion criterion.** Quincy says "proceed" or answers outstanding questions.

-----

## Phase 1 — Gap mapping

**Goal.** Cross-reference `existing-checks.json` against the **canonical gap list** (Tier 1–5 at the bottom of this file). Produce the implementation backlog.

### 1.1 Match

For each check in the gap list (Tiers 1–5):

- Search `existing-checks.json` for a match by semantic equivalence (not just name).
- Record one of: `present` / `partial` / `absent` / `unmapped_existing` (exists in code but not in gap list).

### 1.2 Backlog

Produce `audit/phase-1/backlog.json` — one entry per missing or partial check:

```json
{
  "backlog": [
    {
      "gap_id": "T1-F01",
      "tier": 1,
      "human_name": "Font not embedded",
      "status": "absent | partial",
      "priority_score": 1-100,
      "difficulty": "easy | medium | hard",
      "dependencies": ["T1-STR01 (TrimBox parser)"],
      "references": {
        "competitive_analysis_section": "1.1 Font checks",
        "incumbent_examples": "PitStop CheckFontEmbedding, pdfToolbox Font not embedded"
      },
      "remediation_guidance_shape": "optional — what structured recommendation the report should emit for this finding (e.g., 'list which fonts need to be embedded; suggest that the designer re-export with Subset All Fonts 100%')",
      "open_questions": ["any ambiguity for Quincy"]
    }
  ]
}
```

**Priority scoring rule.**

- Base = `110 - (tier * 20)` → Tier 1 = 90, Tier 2 = 70, Tier 3 = 50, Tier 4 = 30, Tier 5 = 10
- +15 if the finding carries actionable, structured remediation guidance lintPDF could uniquely articulate (e.g., "which fonts, where used, what to do upstream in Illustrator/InDesign to resolve")
- +10 if check is on the "dieline-adjacent differentiator" list (see Tier 3)
- −10 if difficulty is `hard` and tier > 2
- Cap at 100, floor at 1

### 1.3 Unmapped-existing list

Any check lintPDF has that isn't in the gap list → list separately at `audit/phase-1/unmapped-existing.md`. For each, ask Quincy: "Keep, rename to match gap taxonomy, or deprecate?"

**Q&A gate (end of Phase 1).** Cliff notes to Quincy:

```
Phase 1 complete.

Gap list: 5 tiers, ~85 checks.
Status:
  present: X   partial: Y   absent: Z
Unmapped existing: N (see unmapped-existing.md)

Top-10 backlog by priority score:
  1. T1-F01 Font not embedded — score 90, easy
  2. ...

Questions:
1. Unmapped existing check "<name>" — keep/rename/deprecate?
2. T3-D06 Barcode-vs-fold-line needs a barcode decoder library — prefer zbar, ZXing-Node, or roll minimal internal?
3. ...

Ready to start Phase 2 on top-N once you pick the batch size.
```

**Completion criterion.** Quincy approves the backlog priority order and answers open questions.

-----

## Phase 2 — Per-check implementation loop

For each check in the approved backlog (in priority order), run this sub-loop. **Batch size: whatever Quincy picks** (default 3 checks per batch).

### 2.1 Design note (per check)

Before touching code, write `audit/phase-2/<gap_id>/design.md`:

- What the check detects, in one paragraph
- Input: which parts of the PDF does it inspect? (objects, content streams, xref, metadata)
- Output shape: what does the check emit in the report JSON? (severity, location, offending objects, counts, etc.)
- Remediation guidance: what structured advice does the report carry for upstream fixers? (e.g., "Font X used on page 3 is not embedded — re-export from Illustrator with 'Subset fonts when percent of characters used is less than 100%'")
- **Confirm read-only:** state explicitly that this check performs no PDF mutation. If the natural implementation tempts mutation (e.g., "rewrite overprint flag"), stop and rework as pure inspection + guidance.
- Profiles: which profiles (PDF/X-4, GWG-Sheet-2022, Packaging-Flexo-2022, etc.) should include this check by default?
- Edge cases: list 3–5 weird PDFs that would stress-test this check.
- Q&A gate questions, if any.

**Q&A gate.** If design has open questions, ask Quincy before coding. Otherwise, proceed.

### 2.2 Implementation

- Follow existing code conventions (from Phase 0 inventory).
- Add the check to the check registry.
- Wire it into the relevant profiles (ask if ambiguous).
- Update TypeScript types / interfaces.

**Discipline:** One check per commit. Commit message format:

```
feat(check): add <gap_id> <human-name>

Tier <N> check: <one-line description>
Profiles: <list>
Remediation guidance: <yes — describe / none>
Read-only: confirmed (no PDF mutation)
```

### 2.3 Validation (Q&A-style, per Quincy's clarification)

"QA = question & answer." So validation is not automated test fixtures — it's an operator review gate.

For each implemented check, produce `audit/phase-2/<gap_id>/review-questions.md`:

1. **Behavior questions.** "Does this correctly flag <edge case>? Example: <show rendered output>."
1. **Profile questions.** "I added this to profiles <list>. Is that right for our market?"
1. **Remediation guidance questions** (if applicable). "Report emits guidance: <describe>. Is the wording clear for a designer? Should it name a specific Illustrator/InDesign menu path, or stay tool-agnostic?"
1. **Output format questions.** "Report JSON shape: <show>. Good, or change structure?"
1. **Severity questions.** "Default severity: <warning|error>. Override per profile?"
1. **Read-only confirmation.** "Confirmed: this check reads the PDF only. No code path here writes, patches, or re-saves the input. Correct?"

Present these to Quincy in a cliff-notes batch. Wait for answers. Make revisions. Mark check `verified` only after his approval.

### 2.4 Per-check completion

A check is done when:

- Design note exists
- Code is merged to a feature branch
- Review questions are answered and changes applied
- `audit/phase-2/<gap_id>/status.md` says `verified`

### 2.5 Batch completion

After each batch:

```
Batch N complete: <gap_ids>.
Next batch proposed: <gap_ids>.
Any pivots? (Y/N)
```

Wait for Quincy's answer before starting the next batch.

-----

## Phase 3 — Integration and profile audit

After all approved backlog items are verified:

### 3.1 Profile completeness

For each profile lintPDF ships (PDF/X-1a, X-3, X-4, X-6, PDF/A-1b..4, GWG 2022 variants, Packaging-Offset/Flexo/Gravure, etc.), list every check in that profile. Cross-check against the incumbent profile definitions referenced in the competitive analysis. Flag missing checks per profile.

**Deliverable.** `audit/phase-3/profile-audit.md`.

### 3.2 Report schema audit

Verify the output JSON schema handles all new check types cleanly. If any new check required an ad-hoc shape, propose a schema normalization.

### 3.3 Public API surface audit

List every new check exposed via HTTP API / SDK / CLI. Confirm naming, parameter shapes, and backward compatibility.

**Q&A gate.** Cliff notes to Quincy:

```
Phase 3 complete.

Profile gaps still open: N
Schema changes proposed: <list>
API surface additions: <list>
Breaking changes: <list or "none">

Ready for Phase 4 (docs + ship) or more iteration?
```

-----

## Phase 4 — Documentation and release prep

Only enter Phase 4 when Quincy says "ship."

### 4.1 Changelog

`CHANGELOG.md` entry per check added. Group by tier.

### 4.2 Docs

For each new check:

- Public doc page (if lintPDF has user-facing docs)
- API reference entry
- Example input/output
- Which profiles include it

### 4.3 Marketing cut-list

Identify the 5–10 checks from the implementation that are most defensible as competitive differentiators — especially Tier 3 dieline-adjacent ones. Draft one-liner feature bullets for landing page / LinkedIn / sales collateral.

**Deliverable.** `audit/phase-4/marketing-bullets.md`.

### 4.4 Final Q&A

```
Phase 4 complete. Ready to tag release.

New checks: N
Tier 1/2/3/4/5: <counts>
Unique-to-lintPDF checks: <list>
Breaking changes: <list>

Version bump proposal: v<x.y.z>
Tag? (Y/N)
```

-----

## Canonical gap list (source of truth)

This is the authoritative list. Do not edit without operator approval. Check IDs are stable across phases.

### Tier 1 — Table stakes (~35 items)

|gap_id  |check                                             |difficulty|notes                   |
|--------|--------------------------------------------------|----------|------------------------|
|T1-F01  |Font not embedded                                 |easy      |                        |
|T1-F02  |Type 3 font usage                                 |easy      |                        |
|T1-F03  |Subset vs full embedding detection                |easy      |BaseFont name tag prefix|
|T1-F04  |Protected font (no-embed license bit)             |medium    |OS/2 fsType             |
|T1-F05  |Text below minimum point size                     |medium    |needs CTM math          |
|T1-F06  |ToUnicode missing                                 |easy      |                        |
|T1-C01  |DeviceRGB in CMYK workflow                        |easy      |                        |
|T1-C02  |Spot color list + count                           |easy      |                        |
|T1-C03  |Ambiguous spot name definitions                   |medium    |need name normalizer    |
|T1-C04  |Total Area Coverage above threshold               |medium    |requires raster pipeline|
|T1-C05  |Overprint on white / 0% fill                      |easy      |                        |
|T1-C06  |Black text not overprinting / 100%K knockout      |easy      |                        |
|T1-C07  |Output intent missing or wrong ICC                |easy      |                        |
|T1-C08  |Registration color used in print content          |easy      |                        |
|T1-I01  |Effective resolution below min — color images     |medium    |CTM × image W/H         |
|T1-I02  |Effective resolution below min — gray images      |medium    |                        |
|T1-I03  |Effective resolution below min — 1-bit images     |medium    |                        |
|T1-I04  |Image color space mismatch (RGB in CMYK job)      |easy      |                        |
|T1-I05  |JPEG compression quality below threshold          |hard      |inspect DCT tables      |
|T1-I06  |Non-90° rotation / shear on image                 |medium    |CTM decomposition       |
|T1-I07  |Missing image / broken reference                  |easy      |                        |
|T1-STR01|TrimBox / BleedBox presence                       |easy      |                        |
|T1-STR02|Box nesting Media⊇Bleed⊇Trim⊇Art                  |easy      |                        |
|T1-STR03|Bleed amount insufficient                         |easy      |                        |
|T1-STR04|Page size matches expected                        |easy      |                        |
|T1-STR05|Page size consistency across pages                |easy      |                        |
|T1-STR06|Empty pages detection                             |medium    |                        |
|T1-STR07|Hairline strokes under minimum width              |medium    |                        |
|T1-CMP01|PDF/X conformance verify (X-1a…X-6)               |hard      |consider embedding vPDF |
|T1-CMP02|PDF version check                                 |easy      |                        |
|T1-CMP03|Encryption / password set                         |easy      |                        |
|T1-CMP04|JavaScript / action dictionaries present          |easy      |                        |
|T1-CMP05|Annotations / form fields inside BleedBox         |easy      |                        |
|T1-CMP06|Embedded files / attachments                      |easy      |                        |
|T1-TRN01|Live transparency present                         |easy      |                        |
|T1-TRN02|Blend modes other than Normal                     |easy      |                        |
|T1-TRN03|Blending color space defined on transparency group|easy      |                        |

### Tier 2 — Strong competitive (~20 items)

|gap_id  |check                                                              |difficulty|notes                  |
|--------|-------------------------------------------------------------------|----------|-----------------------|
|T2-GWG01|Full GWG 2022 profile set (sheet/web/mag/news/digital/large-format)|medium    |ship all 30 profiles   |
|T2-GWG02|Full GWG 2022 packaging profiles (offset/flexo/gravure × product)  |medium    |15 variants            |
|T2-ISO01|ISO 19593-1 full Structural Type taxonomy (all 23 types)           |medium    |                       |
|T2-ISO02|ISO 19593-1 Positions taxonomy                                     |medium    |                       |
|T2-ISO03|ISO 19593-1 White subtypes                                         |easy      |                       |
|T2-ISO04|ISO 19593-1 Varnish/Coating types                                  |easy      |                       |
|T2-ISO05|Auto-suggest ISO 19593-1 tagging from spot name                    |medium    |UNIQUE differentiator  |
|T2-SPT01|Pantone library matching                                           |medium    |                       |
|T2-SPT02|Spot suffix convention (C/U/CP/HC)                                 |easy      |                       |
|T2-SPT03|Deprecated name detection (CV/CVC)                                 |easy      |                       |
|T2-SPT04|Spot-as-process warning                                            |medium    |                       |
|T2-TRN04|Blending CS vs OutputIntent mismatch                               |medium    |                       |
|T2-TRN05|Transparency on spot color                                         |easy      |                       |
|T2-TRN06|Soft mask on text                                                  |medium    |                       |
|T2-TRN07|Page-level transparency group knockout flag                        |easy      |                       |
|T2-RB01 |Rich black construction recommendation                             |medium    |substrate-tied defaults|
|T2-RB02 |Reverse (knockout) text minimum stroke                             |medium    |                       |
|T2-RB03 |White text below minimum size combo check                          |easy      |                       |
|T2-XMP01|GWG XMP audit-trail namespace                                      |easy      |                       |
|T2-XMP02|Info dict vs XMP consistency                                       |easy      |                       |
|T2-XMP03|Trapped flag True/False required (not Unknown)                     |easy      |                       |

### Tier 3 — Dieline-focused differentiators (~15 items, lintPDF's wedge)

|gap_id|check                                                |difficulty|notes                                                           |
|------|-----------------------------------------------------|----------|----------------------------------------------------------------|
|T3-D01|Content on dieline layer (rendered)                  |medium    |per-separation raster compare                                   |
|T3-D02|Dieline z-order on top                               |easy      |content stream order scan                                       |
|T3-D03|Dieline overprint (not knockout) — detect + recommend|easy      |report emits remediation: set dieline spot to overprint upstream|
|T3-D04|Bleed extending beyond dieline by X mm               |medium    |path offset math                                                |
|T3-D05|Content outside dieline polygon                      |medium    |containment test                                                |
|T3-D06|Barcode quiet zone vs dieline/fold/crease            |hard      |**UNCLAIMED — high differentiator**                             |
|T3-D07|Text near fold line                                  |medium    |**UNCLAIMED — high differentiator**                             |
|T3-D08|Small vector element won't die-cut cleanly           |medium    |**UNIQUE**                                                      |
|T3-D09|White underprint coverage vs dieline                 |medium    |high value for flexible packaging                               |
|T3-D10|Varnish coverage validation (VarnishFree respect)    |easy      |                                                                |
|T3-D11|Spot-name heuristic normalizer (public table)        |easy      |ship as open standard                                           |
|T3-D12|Ink limit per substrate (auto-TAC profile)           |easy      |presentation win                                                |
|T3-D13|Registration risk on fine vector details             |medium    |extend small-text-on-multi-sep to vectors                       |
|T3-D14|Braille area (ISO 19593-1) integrity                 |hard      |pharma niche                                                    |
|T3-D15|CutContour spot used as visual print content         |easy      |**UNIQUE — catches Canva mistakes**                             |

### Tier 4 — Accessibility and archival (~10 items)

|gap_id|check                                       |difficulty|notes        |
|------|--------------------------------------------|----------|-------------|
|T4-A01|PDF/UA-1 Matterhorn machine-checkable subset|hard      |embed veraPDF|
|T4-A02|PDF/A-1b / 2b / 2u / 3u / 4 verification    |hard      |embed veraPDF|
|T4-A03|Tag structure root / Marked=true            |easy      |             |
|T4-A04|Figure Alt / ActualText presence            |easy      |             |
|T4-A05|Language specification (doc + inline)       |easy      |             |
|T4-A06|Table structure (TH scope, Headers/IDs)     |medium    |             |
|T4-A07|Heading hierarchy H1..H6 no-skip            |medium    |             |
|T4-A08|ToUnicode on all fonts                      |easy      |             |
|T4-A09|Encryption permission bit 10 (screen reader)|easy      |             |
|T4-A10|ViewerPreferences DisplayDocTitle=true      |easy      |             |

### Tier 5 — Long-tail niche (~10 items, watch don't prioritize)

|gap_id|check                                          |difficulty|notes                          |
|------|-----------------------------------------------|----------|-------------------------------|
|T5-N01|PDF/VT-1/2/3 validation                        |hard      |low volume                     |
|T5-N02|INCI / cosmetics min type size                 |medium    |regulation-aware               |
|T5-N03|FDA Nutrition Facts layout                     |hard      |                               |
|T5-N04|Tobacco warning % panel area                   |medium    |                               |
|T5-N05|Wine / spirits warning statements              |medium    |                               |
|T5-N06|UDI / EU DPP QR content validation             |hard      |watch 2026-2030 mandate        |
|T5-N07|WCAG 2.1/2.2 contrast on print artwork         |medium    |**UNIQUE — zero engines cover**|
|T5-N08|GS1 AI syntax inside GS1-128 / DataMatrix / QR |medium    |embed GS1 validator            |
|T5-N09|Digimarc / anti-counterfeit watermark detection|hard      |skip                           |
|T5-N10|Grain direction preservation                   |hard      |CAD-requiring, skip            |

-----

## Quincy's Q&A style — calibration

- Ask in numbered lists.
- Max 5 questions per batch.
- Offer 2–4 options per question when possible; open-ended only when necessary.
- Never ask obvious questions.
- Never ask the same question twice.
- If the answer could reasonably be inferred from the competitive analysis or the gap list in this file, infer and state the assumption inline, don't ask.
- Cliff notes > prose. Bullets > paragraphs.
- When in doubt on architectural choices, propose 2 options with tradeoffs.

-----

## Stop conditions

Halt and wait for operator input if:

- **Any code path you're about to write would mutate a PDF, re-save it, flatten it, re-tag it, or otherwise produce a modified PDF as output.** This is a hard product violation. Stop. Redesign as inspection + structured remediation guidance only.
- A check's implementation would require a new runtime dependency > 5MB.
- A check's implementation requires refactoring >3 existing files.
- Any test currently passing would need to be changed to accommodate the new check.
- You discover that an existing lintPDF check contradicts the canonical gap list's definition.
- You're about to make the third consecutive guess in a single phase.

-----

## End state

When all approved tiers are shipped, verified, documented, and released, produce a final summary at `audit/final-report.md`:

- Total checks added, by tier
- Checks now unique to lintPDF vs all incumbents (the marketing wedge)
- Remaining gap list items deferred and why
- Next recommended initiative (e.g., "Tier 5 EU DPP watchlist automation")
- Suggested version bump and release date

Report this to Quincy as the final cliff-notes batch.
