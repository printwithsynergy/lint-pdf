---
title: "HP Indigo EPM Readiness"
description: "HP Indigo Enhanced Productivity Mode (CMY-only) preflight checks."
---

# HP Indigo EPM Readiness

HP Indigo Enhanced Productivity Mode (EPM) runs presses with CMY inks only — no Black (K) channel. LintPDF detects files that will have issues in EPM workflows.

## Why This Matters

In EPM mode:
- K100 text will not print (it produces nothing without K ink)
- Rich blacks using K need to be converted to CMY composite blacks
- Gray balance relies entirely on CMY mixing, increasing color shift risk
- All CMYK images need K-free alternatives

## Checks

| Check | Description | Severity |
|-------|-------------|----------|
| GRD_EPM_001 | K channel usage detection | Squall |
| GRD_EPM_002 | Pure black text (K100) detection | Aground |
| GRD_EPM_003 | CMY composite black quality | Squall |
| GRD_EPM_004 | CMY-only TAC recalculation | Squall |
| GRD_EPM_005 | Spot color K-dependency in fallbacks | Advisory |
| GRD_EPM_006 | Image K channel dependency | Squall |
| GRD_EPM_007 | Registration color in EPM mode | Advisory |
| GRD_EPM_008 | Gray balance risk | Squall |

## Usage

Use the `hp-indigo-epm` preset:

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_..." \
  -F "file=@artwork.pdf" \
  -F "profile_id=hp-indigo-epm"
```
