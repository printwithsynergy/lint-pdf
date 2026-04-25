# T1-F04 LPDF_FONT_015 — Review questions

## Behavior

**Q1.** Detection covers TrueType (sfnt version 0x00010000) and OpenType/CFF (version `b"OTTO"`). Type 1 and Type 3 fonts are skipped because they have no OS/2 table. Acceptable, or do we want an explicit "Type 1 font: cannot verify licence, manual check required" advisory for Type 1?

**Q2.** Five fsType bits are classified:
- **Bits 1-3** (restricted / preview-and-print / editable) → emit advisory
- **Bit 8** (no-subsetting) → info detail only, no severity bump
- **Bit 9** (bitmap-only) → info detail only, no severity bump

Bit 0 (installable) and value=0 are silent. Is this split right, or do we want bit 8 / bit 9 to also trigger findings? Argument for: a font with "no subsetting" set that the PDF *did* subset is a licence violation worth flagging.

**Q3.** When multiple embedding-restriction bits are set (e.g., bits 1+3), all flags are reported in `details.fs_type_flags` in ascending bit order. Is that the right order, or should the "strictest" restriction come first (restricted → preview-and-print → editable)?

## Profile

**Q4.** Advisory severity applied universally across all bundled profiles. Confirm, or should specific profiles (e.g., commercial print where licence compliance matters) escalate to warning?

## Remediation guidance

**Q5.** The emit message format today:

> "Font 'ABCDEF+Helvetica-Bold' has restricted embedding licence (fsType=0x0004: preview_and_print_embedding)"

Includes the font name, the hex fsType value, and the flag names. Operator-readable? Or should we suppress the hex and translate to plain English — "...has a 'preview and print only' embedding restriction"?

## Output format

**Q6.** `details` carries: `font_name`, `base_font`, `font_type`, `fs_type_value`, `fs_type_flags`, `no_subsetting`, `bitmap_only`. Add anything — maybe the font vendor (OS/2 achVendID field)?

## Severity

**Q7.** Default `advisory`. Confirmed, or different per profile?

## Read-only

**Q8.** Confirmed: `_extract_font_file_bytes()` opens `pikepdf.open(io.BytesIO(pdf_bytes))` read-only, walks the font tree, calls `.read_bytes()` on FontFile streams, discards pikepdf objects after. No writes, no re-saves. The design doc's read-only statement holds. ✅

## Scope

**Q9.** The analyzer now takes `pdf_bytes` via constructor (matching the `AdvancedColorAnalyzer` WS-8 pattern). This re-opens the PDF once per preflight run. Acceptable overhead, or do we want to share the already-open pikepdf doc from the orchestrator? (The existing re-open overhead is ~30-100ms on a 20MB PDF — same as the WS-8 pattern that already ships.)
