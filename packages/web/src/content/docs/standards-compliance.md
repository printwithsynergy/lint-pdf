---
title: "Standards Compliance"
description: "G7, GRACoL, and ISO 12647 readiness checking."
section: "color"
order: 3
---

# Standards Compliance

LintPDF checks your files against major print standards. These are readiness checks — we verify your file is prepared correctly for standards-compliant printing.

> **Note:** LintPDF performs readiness checking, not certification. Certification requires physical print verification by an accredited body.

## G7 Pre-Compliance (GRD_STD_001)

G7 is an IDEAlliance specification for achieving gray balance across all printing processes. LintPDF checks:

- OutputIntent references a G7-compatible condition (GRACoL, SWOP)
- TAC within G7 specification limits (300-320%)
- File structure supports G7 calibration workflow

## GRACoL Compliance (GRD_STD_002)

GRACoL (General Requirements for Applications in Commercial Offset Lithography) defines requirements for commercial printing. LintPDF checks:

- OutputIntent references a GRACoL-compatible profile
- TAC does not exceed 340% (GRACoL 2006 Coated specification)
- Minimum reproducible dot ≥3%

## ISO 12647 Compliance (GRD_STD_003)

ISO 12647 defines process control for half-tone colour separations, proofs, and production prints. LintPDF checks:

- OutputIntent ICC profile matches known ISO 12647-2 reference conditions
- TAC limits per declared printing condition
- Profile compatibility with ISO 12647-2 specifications

## Usage

Use the `iso-12647-compliance` preset:

```json
{
  "profile_id": "iso-12647-compliance"
}
```
