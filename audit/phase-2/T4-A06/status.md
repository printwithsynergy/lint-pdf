# T4-A06 — Table structure (TH /Scope) — DONE

## Summary

Walks `/StructTreeRoot` for `/Table` elements; under each `/TR` row,
each `/TH` cell must carry either `/A /Scope` or `/A /Headers`.
Missing both → one `LPDF_ACCESS_TABLE_STRUCTURE` warning per page-
level analysis with aggregate `missing_scope_count` and
`table_count` in `details`.

## Files

- `packages/engine/src/lintpdf/analyzers/accessibility.py`
  (`_check_table_structure`)
- `packages/engine/src/lintpdf/reports/check_names.py`
  (`LPDF_ACCESS_TABLE_STRUCTURE` registered)
- `packages/engine/tests/analyzers/test_accessibility_batch9a.py`
  (`TestTableStructure` — 3 cases)

## Verification

`uv run pytest tests/analyzers/test_accessibility_batch9a.py -v` →
3/3 green for the table-structure suite.

## Catalog

`packages/app/lib/rules/check-catalog.json` — entry present, default
severity `warning`, category `accessibility`.
