# T1-F04 — Protected font (no-embed license bit)

## What the check detects

Flags embedded TrueType / OpenType / CFF fonts whose OS/2 table's **fsType** field advertises a license restriction that forbids or limits embedding. The PDF file *did* embed the font bytes, so the artwork will render, but the font's license declared in its OS/2 table may prohibit redistribution — when that happens the artwork is a compliance landmine for the tenant.

fsType bits (ISO/IEC 14496-22 §5.2.3 / Microsoft OpenType spec):

| Bit | Flag | Meaning |
|---:|---|---|
| 0 | `INSTALLABLE_EMBEDDING` | No restriction |
| 1 | `RESTRICTED_LICENSE_EMBEDDING` | Must not embed unless permission is granted |
| 2 | `PREVIEW_AND_PRINT_EMBEDDING` | Read-only embedding only |
| 3 | `EDITABLE_EMBEDDING` | Viewer may print or edit; no further redistribution |
| 8 | `NO_SUBSETTING` | Font must be embedded in full (cannot subset) |
| 9 | `BITMAP_ONLY` | Only bitmap data may be embedded |

The check emits **advisory** when bits 1-3 are set (the designer's tool didn't respect the font vendor's policy). Installable (bit 0) is silent — no finding. Bit 8 / bit 9 restrictions are informational — emitted as details on the finding but don't change severity (some foundries sell "strict" licenses that limit subsetting to specific weights).

## Input

- `document: SemanticDocument` — already carries per-page `fonts: dict[str, PdfFont]`.
- `PdfFont.font_descriptor: dict[str, Any] | None` — contains `/FontFile2` (TrueType) or `/FontFile3` (CFF / OpenType) as a pikepdf Stream when embedded.

The analyzer extracts the sfnt table directory from the stream bytes, locates the **OS/2** table, reads `fsType` (uint16 at offset 8 within that table), and classifies the bits.

No network call, no global state. Pure bytes-in / finding-out.

## Output shape

```
Finding(
    inspection_id="LPDF_FONT_015",          # new ID slot after 014
    severity=Severity.ADVISORY,
    message="Font 'ABCDEF+Helvetica-Bold' has restricted embedding license (fsType=0x0004 Preview & Print)",
    page_num=page_num,
    details={
        "base_font": "Helvetica-Bold",
        "font_name": "F2",
        "font_type": "TrueType",
        "fs_type_value": 4,
        "fs_type_flags": ["preview_and_print_embedding"],
        "no_subsetting": False,
        "bitmap_only": False,
    },
    iso_clause="ISO 32000-2:2020 9.8.2 / OpenType OS/2 §5.2.3",
    object_id=font.name,
    object_type="font",
)
```

## Remediation guidance

Emitted on the finding's `details.remediation`:

> The font "{base_font}" carries a {flag_name} license bit that restricts embedding. Verify your licence grants embedding for this use (web / print / packaging distribution) before shipping this PDF. If the vendor provides an "installable" licence tier, re-export with that font weight; otherwise replace with a font whose OS/2.fsType is clear (bit 0).

Human-readable tool-specific advice lives in the report HTML template (ships with the catalog description, not inline per-finding).

## Confirm read-only

Nothing in this check writes to the PDF. The sfnt-table parser reads
bytes from `font_descriptor["/FontFile2"].read_bytes()` and inspects
them. No mutation, no re-save, no wrapped object returned to the caller.

## Profile membership

| Profile | Include by default? |
|---|:--:|
| PDF/X-1a | Yes — advisory |
| PDF/X-3 | Yes — advisory |
| PDF/X-4 | Yes — advisory |
| PDF/X-6 | Yes — advisory |
| PDF/A-1b..4 | Yes — advisory |
| GWG 2022 sheet/web/mag/news/digital | Yes — advisory |
| GWG 2022 packaging (flexo/offset/gravure) | Yes — advisory |
| Internal debug profile | Yes — advisory |

Default severity stays advisory everywhere. Tenants can escalate to warning/error via the rules editor if their workflow requires stricter licence enforcement.

## Edge cases

1. **Standard 14 fonts** — not embedded, no OS/2 table to read. Skip (already handled by `font.is_standard_14()` guard).
2. **Type 3 fonts** — user-drawn glyphs, no sfnt table. Skip.
3. **Type 1 fonts** (`/FontFile`) — pre-OpenType format with no fsType field. Skip with no finding.
4. **CID fonts** — the OS/2 table lives in the DescendantFonts[0] FontFile, not the CIDFont descriptor. Walk the DescendantFonts chain to find the sfnt bytes.
5. **Corrupt sfnt** — if the table directory parse fails, emit no finding and log a debug warning (don't flood the report with parse errors).
6. **fsType bit 3 AND 1 both set** — some old Adobe-signed fonts had this pattern. Report as `["restricted_license_embedding", "editable_embedding"]` — the stricter bit wins for messaging purposes.

## Q&A gate

No open questions. Implementation greenlit — all decisions match playbook constraints.

## Implementation notes

- New helper `packages/engine/src/lintpdf/analyzers/_font_sfnt.py` with `parse_fstype(font_file_bytes: bytes) -> FsTypeInfo | None`.
- `FsTypeInfo` dataclass: `value: int`, `flags: list[str]`, `no_subsetting: bool`, `bitmap_only: bool`.
- ~60 LOC inline sfnt parser: big-endian struct unpack of the 12-byte sfnt header (version + numTables + searchRange + entrySelector + rangeShift), then 16-byte table records (tag + checksum + offset + length), find "OS/2", read uint16 at table_offset + 8.
- Extend `FontAnalyzer._check_font` in `font.py` with a new branch (post LPDF_FONT_014) that calls `parse_fstype` on the font file bytes and emits LPDF_FONT_015 when flags are non-installable.
- Add one new entry to `check_names.py`: `LPDF_FONT_015 = ("Restricted Font Embedding License", "Font OS/2 fsType bit restricts or prohibits embedding.")`.
- Test fixture: two synthetic TrueType fonts — one with `fsType=0` (no finding), one with `fsType=0x0004` (finding). Build via `struct.pack` in the test setup; no real font binaries committed.
