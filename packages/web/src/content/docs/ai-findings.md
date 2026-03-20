---
title: "Reading AI Findings"
description: "Understanding AI findings in your Report: source field, categories, severity levels, and filtering."
---

# Reading AI Findings

AI findings appear in the same Report as core engine findings. This guide explains how to identify, interpret, and filter AI-specific findings.

## The Source Field

Every finding in a Report includes a `source` field:

- `source: "engine"` — Core engine finding (rule-based, deterministic)
- `source: "ai"` — AI-powered finding (model-based, includes confidence score)

```json
{
  "inspection_id": "ai.fda.nutrient_order",
  "severity": "error",
  "message": "Nutrient 'Trans Fat' appears after 'Cholesterol' — FDA requires Trans Fat immediately after Saturated Fat",
  "page": 1,
  "source": "ai",
  "category": "regulatory.fda",
  "confidence": 0.97,
  "credits_consumed": 2,
  "model_version": "lintpdf-compliance-v1"
}
```

## AI-Specific Fields

AI findings include additional metadata beyond core engine findings:

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | Always `"ai"` for AI findings |
| `category` | string | AI category (e.g., `"regulatory.fda"`, `"barcode"`, `"content_quality"`) |
| `confidence` | number | Model confidence score (0.0 to 1.0) |
| `credits_consumed` | number | Credits consumed for this inspection (1 for Text, 2 for Vision) |
| `model_version` | string | Model version that produced the finding |

## Categories

AI findings are grouped into categories:

| Category | Prefix | Description |
|----------|--------|-------------|
| Barcode Detection | `ai.barcode.*` | Barcode identification, decode, and validation |
| Content Quality | `ai.content.*` | Spell check, language, duplicate detection |
| Color Compliance | `ai.color.*` | Brand palette, contrast ratio |
| Regulatory: FDA | `ai.fda.*` | FDA nutrition and labeling |
| Regulatory: EU | `ai.eu_fir.*` | EU Food Information Regulation |
| Regulatory: GHS/CLP | `ai.ghs.*` | Chemical labeling |
| Regulatory: Pharma | `ai.pharma.*` | Pharmaceutical packaging |
| Brand Verification | `ai.brand.*` | Logo and palette matching |
| Visual Quality | `ai.vision.*` | Image quality, content safety |

## Severity Levels

AI findings use the same three severity levels as core engine findings:

- **Error** — Critical issue that would prevent production (e.g., missing FDA required field, GHS pictogram below minimum size)
- **Warning** — Issue that should be resolved but may not block production (e.g., spell check finding, brand palette deviation)
- **Info** — Informational finding (e.g., language detected, barcode type identified)

## Filtering AI Findings

### In the API Response

Filter findings by source in your code:

```javascript
const report = await fetch(`${API_BASE}/api/v1/reports/${id}`, { headers }).then(r => r.json());

// AI findings only
const aiFindings = report.findings.filter(f => f.source === "ai");

// Core engine findings only
const engineFindings = report.findings.filter(f => f.source === "engine");

// AI findings by category
const fdaFindings = report.findings.filter(f => f.category === "regulatory.fda");
```

### In the Report Summary

The Report summary includes AI-specific counts:

```json
{
  "summary": {
    "total_findings": 8,
    "error": 2,
    "warning": 3,
    "info": 3,
    "ai_findings": 5,
    "ai_credits_consumed": 8,
    "engine_findings": 3
  }
}
```

## Confidence Scores

AI findings include a confidence score between 0.0 and 1.0. Higher values indicate greater model certainty.

- **0.95+** — High confidence. Treat as equivalent to a rule-based finding.
- **0.80-0.95** — Medium confidence. Review recommended.
- **Below 0.80** — Lower confidence. Manual verification recommended.

LintPDF only reports findings with confidence above a minimum threshold (default 0.75). You can adjust this threshold in your AI settings.
