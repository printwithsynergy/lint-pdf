# T2-ISO02 — Positions taxonomy — DONE

`LPDF_PSTEP_POSITIONS` (advisory) emitted for every spot whose
normalised name matches a positioning-aid token (registration,
trim mark, crop mark, colour bar, control strip, media wedge…).
Suggests the spot belong in the ISO 19593-1 `Positions`
ProcessingSteps group.

Files:
- `packages/engine/src/lintpdf/analyzers/spot_name_normaliser.py`
  — adds `POSITION_TOKENS` + `suggest_position_tagging()`.
- `packages/engine/src/lintpdf/queue/tasks.py` — wires it in.
- `packages/engine/tests/analyzers/test_batch10a.py` — 3 cases.
