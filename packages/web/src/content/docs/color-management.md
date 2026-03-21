---
title: "Color Management"
description: "ICC profile validation, gamut checking, ink coverage analysis, and the Color Quality Score."
---

# Color Management

LintPDF includes comprehensive color management inspections that detect color-related issues before they reach press. All color checks are deterministic, CPU-only, and included in paid plans at no extra cost.

## Overview

The color management suite includes:

- **ICC Profile Validation** — Structural integrity, version compatibility, corruption detection
- **Output Intent Validation** — PDF/X compliance, condition cross-referencing
- **Spot Color Analysis** — Inventory, fallback validation, naming consistency, DeviceN structure
- **Ink Coverage Analysis** — TAC heatmap data, per-separation coverage, channel count
- **Overprint Analysis** — Dangerous patterns, RGB overprint, registration color misuse
- **Advanced Color Analysis** — Black generation profiling, ink savings estimation, trapping risk
- **Gamut Checking** — Boundary testing against target printing conditions
- **Color Quality Score** — Novel 0-100 composite score (see dedicated guide)

## Configuration

### Per-Request Color Settings

Include color configuration in your Check-In request:

```json
{
  "file": "...",
  "flight_plan": "gwg-sheetfed-offset",
  "color": {
    "target_condition": "fogra39_coated",
    "tac_threshold": 320,
    "gamut_check": true,
    "epm_mode": false
  }
}
```

### Available Output Conditions

| Condition             | Region        | Use Case                 |
| --------------------- | ------------- | ------------------------ |
| fogra39_coated        | Europe        | Coated offset (legacy)   |
| fogra51_premium       | Europe        | Premium coated, M1       |
| fogra52_uncoated      | Europe        | Uncoated white           |
| gracol2006_coated     | North America | Sheetfed coated          |
| swop2006_coated       | North America | Web offset               |
| japancolor2001_coated | Japan/Asia    | Sheetfed coated          |
| srgb                  | Universal     | RGB validation           |
| fogra55_ecg           | Europe        | Extended gamut (CMYKOGV) |

### Custom ICC Profiles

Upload your own ICC profiles for gamut checking:

```bash
curl -X POST https://api.lintpdf.com/api/v1/tenants/{id}/color-config/profiles \
  -H "Authorization: Bearer lpdf_..." \
  -F "file=@custom_profile.icc" \
  -F "name=Custom Coated"
```

## Check Reference

### ICC Profile & Output Intent (GRD*ICC*\*)

| Check       | Description                        | Severity |
| ----------- | ---------------------------------- | -------- |
| GRD_ICC_001 | ICC profile structural validation  | Aground  |
| GRD_ICC_002 | ICC profile version compatibility  | Advisory |
| GRD_ICC_003 | ICC profile corruption detection   | Aground  |
| GRD_ICC_004 | Output intent structure validation | Squall   |
| GRD_ICC_005 | Output condition cross-reference   | Advisory |
| GRD_ICC_006 | Multiple output intent consistency | Squall   |

### Spot Color & DeviceN (GRD*SPOT*\*)

| Check        | Description                        | Severity        |
| ------------ | ---------------------------------- | --------------- |
| GRD_SPOT_001 | Spot color inventory & consistency | Advisory/Squall |
| GRD_SPOT_002 | Spot color fallback validation     | Advisory        |
| GRD_SPOT_003 | Spot color naming issues           | Squall/Advisory |
| GRD_SPOT_004 | DeviceN structural validation      | Aground/Squall  |
| GRD_SPOT_005 | DeviceN process color consistency  | Squall/Advisory |

### Ink Coverage (GRD*INK*\*)

| Check       | Description                  | Severity        |
| ----------- | ---------------------------- | --------------- |
| GRD_INK_001 | TAC heatmap data             | Advisory        |
| GRD_INK_002 | Per-separation ink coverage  | Advisory        |
| GRD_INK_003 | Ink channel count validation | Squall/Advisory |

### Gamut Checking (GRD*GAMUT*\*)

| Check         | Description                    | Severity        |
| ------------- | ------------------------------ | --------------- |
| GRD_GAMUT_001 | Per-object gamut boundary test | Squall/Advisory |
| GRD_GAMUT_002 | Gamut volume comparison        | Advisory        |
| GRD_GAMUT_003 | Out-of-gamut summary           | Advisory        |

### Standards Compliance (GRD*STD*\*)

| Check       | Description          | Severity        |
| ----------- | -------------------- | --------------- |
| GRD_STD_001 | G7 pre-compliance    | Squall/Advisory |
| GRD_STD_002 | GRACoL compliance    | Squall/Advisory |
| GRD_STD_003 | ISO 12647 compliance | Squall/Advisory |
