# T1-F04 Q2 — Reasons for/against bumping fsType bits 8 & 9

Current design: bits 8 (no_subsetting) and 9 (bitmap_only) are captured
as `details.no_subsetting` / `details.bitmap_only` booleans but don't on
their own produce a finding. Only bits 1-3 fire LPDF_FONT_015.

## Arguments FOR bumping bits 8/9 to their own findings

1. **Bit 8 = direct licence violation when subset mismatch.** If a font
   declares `no_subsetting` AND the PDF embedded a subset (`font.subset
   == True`), the embedder ignored the vendor's explicit instruction.
   That's a clear licence breach worth flagging, separate from bits 1-3.
2. **Bit 9 similar.** `bitmap_only` + embedded outlines = same pattern.
3. **Discoverability.** Keeping them as "details on a non-existent
   finding" means a tenant searching the rules editor for "no
   subsetting" sees nothing — the concept exists only as a silent
   metadata field on other findings.
4. **Per-profile severity.** If bits 8/9 had their own IDs
   (LPDF_FONT_016 / 017), strict commercial-print workflows could
   escalate them to warning or error while lenient workflows leave them
   at advisory.

## Arguments AGAINST

1. **High false-positive rate.** Many commercial fonts ship with
   `no_subsetting` set as a blanket vendor policy, and PDF toolchains
   (Acrobat, InDesign, Ghostscript) silently treat it as a hint, not a
   hard rule. Most subset-forbidden-but-subset cases are routine
   — promoting them to findings will spam tenant reports.
2. **Hard to act on.** Even if flagged, a tenant can't fix it without
   re-licensing the font or switching to an installable-tier
   equivalent. The remediation path is long, cost-bearing, and rarely
   practical for a single PDF job.
3. **Already capturable by the existing finding.** Tenants who really
   care can filter the LPDF_FONT_015 firings by
   `details.no_subsetting == True` — the information is present; it
   just isn't its own row.
4. **OpenType spec ambiguity.** The fsType spec treats bits 8/9 as
   "additional permissions" flags, not as "violations if not
   respected." A font with `no_subsetting` set still allows
   embedding; the restriction is on *how* it's embedded.

## Recommendation

**Keep the current design (info-only).** The false-positive rate from
promoting these bits is high enough that most tenants would disable
them immediately or ignore the resulting noise. Tenants with strict
licence-compliance workflows can filter LPDF_FONT_015 findings by the
existing `details.no_subsetting` / `details.bitmap_only` booleans, or
open a per-vendor ticket with the foundry if they believe the
embedding violates the licence.

If you want to address the discoverability concern (argument #3 FOR),
the cheap fix is to document bits 8/9 in the LPDF_FONT_015 description
(already done — the check_names.py entry references "licence
restriction" broadly) and add a note in the web docs that the
`details` dict distinguishes strict vs advisory licence bits.

## Alternative (if you overrule)

If you want to promote bits 8/9 anyway:

- LPDF_FONT_016 — `no_subsetting` set but PDF subset the font
  (conditional on `font.subset == True` so it only fires on actual
  violations, not unused-but-declared `no_subsetting` bits).
- LPDF_FONT_017 — `bitmap_only` set but PDF embedded outlines (no
  trivial way to detect "outlines embedded" without parsing the font
  program further; could approximate by checking if `font_type` is
  TrueType / OpenType vs a bitmap-only format).

The `no_subsetting`-with-subset pattern is the more defensible check
— it has a clear pass/fail criterion. The `bitmap_only` check is
harder to implement correctly.

Your call.
