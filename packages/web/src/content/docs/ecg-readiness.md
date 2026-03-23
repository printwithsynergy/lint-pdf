---
title: "Extended Gamut (ECG) Readiness"
description: "CMYKOGV extended gamut preflight with FOGRA55 checks."
section: "color"
order: 4
---

# Extended Gamut Readiness

LintPDF can assess your files for Extended Gamut Color (ECG) printing using CMYK plus Orange, Green, and Violet inks.

## What Is ECG?

Extended Gamut (also called Expanded Color Gamut or CMYKOGV) uses 7 inks instead of 4 to reproduce a wider range of colors. Research shows 57.6% of Pantone colors match at ΔE ≤2, 82.7% at ΔE ≤3, and ~90% at ΔE ≤3.7.

## Checks

| Check       | Description                                                 |
| ----------- | ----------------------------------------------------------- |
| GRD_ECG_001 | ECG readiness assessment with spot color inventory          |
| GRD_ECG_002 | Per-spot color ECG achievability (ΔE against FOGRA55 gamut) |
| GRD_ECG_003 | 7-channel TAC verification (300% FOGRA55 limit)             |
| GRD_ECG_004 | DeviceN colorant consistency for CMYKOGV                    |
| GRD_ECG_005 | Max 3-ink build validation                                  |

## Usage

Use the `ecg-readiness` preset or enable ECG mode in your Preflight Profile:

```json
{
  "thresholds": {
    "ecg_mode": true,
    "ecg_tac_limit": 300.0,
    "target_output_condition": "fogra55_ecg"
  }
}
```
