# T4-A06 — Table structure (TH scope, Headers/IDs)

## What the check detects

Walks the structure tree (`/StructTreeRoot`) for `/Table` elements
and validates that each `/TH` (table header) cell carries:
- `/A /O /Table /Scope /Row|Col` attribute, OR
- `/A /O /Table /Headers [/ID1 /ID2]` attribute, OR
- the table only has one row of headers (auto-mapped row scope).

Without scope or Headers/IDs, screen readers can't associate data
cells with their headers — accessibility fail per WCAG 1.3.1
(Info and Relationships).

New inspection_id: `LPDF_ACCESS_TABLE_STRUCTURE`. Severity **warning**.

## Detection

1. Walk `/StructTreeRoot /K` recursively to find `/Type /Table`
   nodes.
2. For each table, count `/TH` cells lacking `/A /O /Table /Scope`
   AND `/A /O /Table /Headers`.
3. Emit when ≥1 TH cell lacks both.

## Output

```
Finding(
    inspection_id="LPDF_ACCESS_TABLE_STRUCTURE",
    severity=Severity.WARNING,
    message="Table contains 5 header cell(s) without /Scope or /Headers — screen readers can't associate data with headers",
    details={
        "table_count": 1,
        "missing_scope_count": 5,
    },
)
```

## Read-only / profiles

Confirmed read-only. Universal warning (a11y profiles).
