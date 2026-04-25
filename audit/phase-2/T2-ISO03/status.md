# T2-ISO03 — White subtypes — DONE

`LPDF_PSTEP_WHITE_SUBTYPE` (advisory) emitted for every White spot
whose name carries a subtype hint (Underprint / Overprint / Print /
Knockout). Suggests the more-specific ISO 19593-1 White subtype.

Files:
- `packages/engine/src/lintpdf/analyzers/spot_name_normaliser.py`
  — adds `WHITE_SUBTYPE_TOKENS` + `check_white_subtype_specificity()`.
- `packages/engine/src/lintpdf/queue/tasks.py` — wires it in.
- `packages/engine/tests/analyzers/test_batch10a.py` — 3 cases.
