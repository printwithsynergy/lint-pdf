# T4-A09 — Encryption screen-reader permission — DONE

## Summary

When `document.is_encrypted`, reads `/Encrypt /P` (32-bit signed).
Bit 10 (`0x200`, ISO 32000-2 Table 22) governs accessibility
extraction. When clear, screen readers can't extract text —
emits one `LPDF_ACCESS_SCREEN_READER` warning with
`screen_reader_allowed=False` and the raw `p_value` in details.
Silent on unencrypted documents and on documents where /Encrypt
omits /P.

## Files

- `packages/engine/src/lintpdf/analyzers/accessibility.py`
  (`_check_screen_reader_permission`)
- `packages/engine/src/lintpdf/reports/check_names.py`
  (`LPDF_ACCESS_SCREEN_READER` registered)
- `packages/engine/tests/analyzers/test_accessibility_batch9a.py`
  (`TestScreenReaderPermission` — 4 cases)

## Verification

`uv run pytest tests/analyzers/test_accessibility_batch9a.py -v`
→ 4/4 green for the screen-reader suite.

## Catalog

`packages/app/lib/rules/check-catalog.json` — entry present,
default severity `warning`, category `accessibility`.
