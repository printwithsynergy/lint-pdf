# T3-D12 — Ink limit per substrate (auto-TAC profile)

## What the check detects

When a profile declares a `substrate` field, fires an advisory when
the PDF's observed TAC doesn't match the substrate-appropriate limit.
Complements `LPDF_INK_001` (TAC threshold exceeded) with
substrate-specific context so tenants see the RIGHT limit for their
paper / press combo instead of a generic default.

New inspection_id: `LPDF_INK_SUBSTRATE`. Severity **advisory**.

## Supported substrates + default TAC limits

| Substrate | Default TAC |
|---|:--:|
| `uncoated_offset` | 280% |
| `coated_offset` | 300% |
| `newsprint` | 240% |
| `digital` | 320% |
| `flexo` | 260% |
| `gravure` | 300% |
| `large_format` | 280% |

## Detection

Runs alongside the existing InkCoverageAnalyzer. For each page's
observed TAC:

1. Read `profile.thresholds.substrate` (new field). Skip if absent.
2. Look up `substrate_tac_limit = SUBSTRATE_TAC[substrate]`.
3. If observed max TAC > substrate_tac_limit → emit
   `LPDF_INK_SUBSTRATE` advisory.
4. Separately, if `profile.tac_limit` is explicitly set AND differs
   from `substrate_tac_limit` by > 10%, emit an advisory noting the
   mismatch (tenant may have hand-tuned it).

## Output

```
Finding(
    inspection_id="LPDF_INK_SUBSTRATE",
    severity=Severity.ADVISORY,
    message="Observed max TAC 310% exceeds uncoated offset substrate limit (280%)",
    details={
        "substrate": "uncoated_offset",
        "substrate_tac_limit": 280.0,
        "profile_tac_limit": 300.0,
        "observed_tac_pct": 310.0,
        "worst_page_num": 2,
    },
)
```

## Profile schema addition

New field on `ThresholdConfig`:

```python
substrate: str | None = Field(
    default=None,
    description="Target substrate (affects auto-TAC; values: uncoated_offset, coated_offset, newsprint, digital, flexo, gravure, large_format). Absent → no substrate advisory.",
)
```

## Read-only / profile membership

Confirmed read-only. Advisory severity — never blocks. Opt-in by
setting `substrate` on the profile.

## Implementation notes

Lives in `packages/engine/src/lintpdf/analyzers/ink_coverage_analyzer.py`
alongside `LPDF_INK_001`. Piggybacks on the already-computed per-page
TAC so cost is O(1) beyond the existing analyzer.

## Q&A gate

No open questions.
