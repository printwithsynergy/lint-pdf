---
title: "Color Quality Score"
description: "Understanding and customizing the 0-100 Color Quality Score."
section: "color"
order: 2
---

# Color Quality Score

Every preflight report includes a **Color Quality Score** — a 0-100 weighted composite that rates the color readiness of your PDF. No other preflight tool offers this.

## How It Works

The score starts at 100 and is reduced by deductions based on color-related findings:

### Critical Disqualifiers (Score Floors)

These cap the maximum score:

| Issue                         | Maximum Score |
| ----------------------------- | ------------- |
| RGB in CMYK workflow          | 20            |
| Missing OutputIntent in PDF/X | 25            |
| Corrupt ICC profiles          | 30            |

### Deduction Categories

| Category     | Weight | What's Checked                                                    |
| ------------ | ------ | ----------------------------------------------------------------- |
| Color Spaces | 25%    | Color space usage, device-dependent warnings, workflow compliance |
| Ink Coverage | 25%    | TAC limits, per-separation coverage, black generation             |
| Profiles     | 20%    | ICC profiles, output intent, gamut compliance                     |
| Spot Colors  | 15%    | Naming, fallback values, DeviceN structure                        |
| Overprint    | 15%    | Dangerous overprint patterns, registration color                  |

### Score Interpretation

| Range  | Grade     | Meaning                         |
| ------ | --------- | ------------------------------- |
| 90-100 | Excellent | Press-ready with confidence     |
| 75-89  | Good      | Minor issues, likely printable  |
| 50-74  | Fair      | Review needed before production |
| 25-49  | Poor      | Significant color issues        |
| 0-24   | Critical  | Not suitable for production     |

## Customizing Weights

Users can adjust category weights in their Preflight Profile to match their workflow:

```json
{
  "thresholds": {
    "color_score_weights": {
      "color_spaces": 30.0,
      "ink_coverage": 20.0,
      "profiles": 20.0,
      "spot_colors": 15.0,
      "overprint": 15.0
    }
  }
}
```

## API Response

The score appears in every preflight report response:

```json
{
  "color_quality_score": 87,
  "color_quality_grade": "Good",
  "color_score_breakdown": {
    "color_spaces": 25.0,
    "ink_coverage": 22.0,
    "profiles": 20.0,
    "spot_colors": 10.0,
    "overprint": 10.0
  }
}
```
