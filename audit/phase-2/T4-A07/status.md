# T4-A07 — Heading hierarchy skip — DONE

## Summary

Walks `/StructTreeRoot` collecting heading levels in document order
(`/H1`..`/H6`). Any forward jump > 1 level (e.g. H1 → H3) is a
"skip"; emits one `LPDF_ACCESS_HEADING_SKIP` warning summarising
`skip_count`, `worst_skip_from`, `worst_skip_to`. Going back up
the hierarchy (H3 → H2) is allowed and silent.

## Files

- `packages/engine/src/lintpdf/analyzers/accessibility.py`
  (`_check_heading_skip`)
- `packages/engine/src/lintpdf/reports/check_names.py`
  (`LPDF_ACCESS_HEADING_SKIP` registered)
- `packages/engine/tests/analyzers/test_accessibility_batch9a.py`
  (`TestHeadingSkip` — 3 cases)

## Verification

`uv run pytest tests/analyzers/test_accessibility_batch9a.py -v`
→ 3/3 green for the heading-skip suite.

## Catalog

`packages/app/lib/rules/check-catalog.json` — entry present,
default severity `warning`, category `accessibility`.
