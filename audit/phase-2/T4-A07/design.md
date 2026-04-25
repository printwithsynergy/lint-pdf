# T4-A07 — Heading hierarchy H1..H6 no-skip

## What the check detects

Walks the structure tree for `/H1`-`/H6` elements and flags any skip
in the heading sequence (e.g., a `/H3` directly under a `/H1`
without an intermediate `/H2`). Skipped headings break screen-reader
navigation and confuse outline-based browsing per WCAG 1.3.1.

New inspection_id: `LPDF_ACCESS_HEADING_SKIP`. Severity **warning**.

## Detection

1. Walk `/StructTreeRoot /K` recursively in document order.
2. Track the current "open" heading level (deepest non-skip
   ancestor).
3. When a heading element appears whose level > current_open + 1,
   record a skip.
4. Emit one finding with the count of skips + the worst (largest
   gap) example.

## Output

```
Finding(
    inspection_id="LPDF_ACCESS_HEADING_SKIP",
    severity=Severity.WARNING,
    message="3 heading hierarchy skip(s) detected (worst: H1 → H4)",
    details={
        "skip_count": 3,
        "worst_skip_from": "H1",
        "worst_skip_to": "H4",
    },
)
```

## Read-only / profiles

Confirmed read-only. Universal warning.
