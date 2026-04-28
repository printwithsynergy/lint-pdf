---
title: "Standards & conformance"
description: "PDF/X, G7/GRACoL/ISO 12647, ECG, and HP Indigo EPM readiness in one place."
section: "color"
order: 3
---

# Standards & conformance

LintPDF checks files against every major print standard — PDF/X conformance, G7/GRACoL/ISO 12647 process control, Extended Gamut (ECG) readiness, and HP Indigo Enhanced Productivity Mode (EPM). This page consolidates all three into one reference.

> **Readiness, not certification.** LintPDF verifies files are *prepared* correctly. Actual certification requires physical print verification by an accredited body.

## PDF/X & general standards compliance

Classic standards compliance for offset, sheetfed, and certified workflows.

### G7 pre-compliance — `GRD_STD_001`

G7 is an IDEAlliance specification for achieving gray balance across every printing process. LintPDF checks:

- OutputIntent references a G7-compatible condition (GRACoL, SWOP).
- TAC within G7 spec limits (300–320 %).
- File structure supports the G7 calibration workflow.

### GRACoL compliance — `GRD_STD_002`

GRACoL (General Requirements for Applications in Commercial Offset Lithography) defines requirements for commercial offset:

- OutputIntent references a GRACoL-compatible profile.
- TAC does not exceed 340 % (GRACoL 2006 Coated specification).
- Minimum reproducible dot ≥ 3 %.

### ISO 12647 compliance — `GRD_STD_003`

ISO 12647 defines process control for half-tone color separations, proofs, and production prints:

- OutputIntent ICC profile matches known ISO 12647-2 reference conditions.
- TAC limits per declared printing condition.
- Profile compatibility with ISO 12647-2 specifications.

### Run the PDF/X standards bundle

Use the `iso-12647-compliance` profile:

```json
{
  "profile_id": "iso-12647-compliance"
}
```

## Extended Gamut (ECG) readiness

Extended Gamut Color (also called Expanded Color Gamut, or CMYKOGV) uses 7 inks instead of 4 — CMYK plus Orange, Green, and Violet — to reproduce a wider slice of Pantone. Research against FOGRA55 shows 57.6 % of Pantone colors match at ΔE ≤ 2, 82.7 % at ΔE ≤ 3, and ~90 % at ΔE ≤ 3.7.

### ECG checks

| Check         | What it verifies                                             |
| ------------- | ------------------------------------------------------------ |
| `GRD_ECG_001` | ECG readiness assessment with spot color inventory           |
| `GRD_ECG_002` | Per-spot color ECG achievability (ΔE against FOGRA55 gamut)  |
| `GRD_ECG_003` | 7-channel TAC verification (300 % FOGRA55 limit)             |
| `GRD_ECG_004` | DeviceN colorant consistency for CMYKOGV                     |
| `GRD_ECG_005` | Max 3-ink build validation                                   |

### Run ECG readiness

Use the `ecg-readiness` profile or enable ECG mode in your preflight profile:

```json
{
  "thresholds": {
    "ecg_mode": true,
    "ecg_tac_limit": 300.0,
    "target_output_condition": "fogra55_ecg"
  }
}
```

## HP Indigo EPM readiness

HP Indigo Enhanced Productivity Mode (EPM) runs presses with **CMY inks only — no Black (K) channel**. LintPDF catches files that will break in EPM workflows.

### Why EPM matters

- K100 text will **not print** (no K ink to deposit).
- Rich blacks using K need to be converted to CMY composite blacks.
- Gray balance relies entirely on CMY mixing → higher color-shift risk.
- Every CMYK image needs a K-free alternative.

### EPM checks

| Check         | What it catches                           | Severity |
| ------------- | ----------------------------------------- | -------- |
| `GRD_EPM_001` | K channel usage detection                 | Warning  |
| `GRD_EPM_002` | Pure black text (K100) detection          | Error    |
| `GRD_EPM_003` | CMY composite black quality               | Warning  |
| `GRD_EPM_004` | CMY-only TAC recalculation                | Warning  |
| `GRD_EPM_005` | Spot color K-dependency in fallbacks      | Advisory |
| `GRD_EPM_006` | Image K channel dependency                | Warning  |
| `GRD_EPM_007` | Registration color in EPM mode            | Advisory |
| `GRD_EPM_008` | Gray balance risk                         | Warning  |

### Run EPM readiness

Use the `hp-indigo-epm` profile:

```sh
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_..." \
  -F "file=@artwork.pdf" \
  -F "profile_id=hp-indigo-epm"
```

## Related

- [Color management](./management) — output intent, ICC profiles, profile-aware TAC
- [Color quality score](./quality-score) — single-number color readiness summary
