# T2-SPT03 — Deprecated Pantone naming — DONE

`LPDF_SPOT_DEPRECATED_PANTONE` (advisory) flags spots whose name
ends in a legacy Pantone suffix (CV, CVC, CVU, CVP, CVUX). The
post-2008 Pantone book uses simple `C` / `U` letter codes; CV*
names usually mean the artwork was migrated from a pre-2008
library and the tint behaviour may not match the current Pantone
target.

Files:
- `packages/engine/src/lintpdf/analyzers/spot_name_normaliser.py`
  — adds `_DEPRECATED_PANTONE_SUFFIXES` + `check_deprecated_pantone_names()`.
- `packages/engine/src/lintpdf/queue/tasks.py` — wires it in.
- `packages/engine/tests/analyzers/test_batch10a.py` — 2 cases.
