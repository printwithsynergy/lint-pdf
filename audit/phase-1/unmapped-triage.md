# Phase 1 — Unmapped existing checks: triage decisions

**Operator decision (2026-04-24):** blanket-approve KEEP for all 12 AI categories.

## Approved: KEEP (no action required)

| Category | ID count | Decision |
|---|---:|---|
| `ai_color_compliance` | 38 | KEEP — lintPDF differentiator (ECG/EPM analyzers unique) |
| `ai_barcode` | 25 | KEEP — barcode-content validation suite unique |
| `ai_regulatory_compliance` | 10 | KEEP — supplements Tier-5 niche line |
| `ai_image_analysis` | 5 | KEEP — pixel-level image quality + NSFW detection |
| `ai_symbol_detection` | 5 | KEEP — regulatory symbol detection |
| `ai_document_classification` | 4 | KEEP — auto-preflight-profile + file classification |
| `ai_trend_analysis` | 4 | KEEP — submission-quality SPC |
| `ai_text_analysis` | 2 | KEEP — text-as-outlines aggregation + spelling |
| `ai_nlp_interfaces` | 2 | KEEP — multi-language scan / translation |
| `ai_logo_verification` | 2 | KEEP — brand-spec aware |
| `ai_file_comparison` | 2 | KEEP — version-diff and similarity |
| `ai_dieline_detection` | 2 | KEEP — feeds Tier-3 dieline rules |
| **Total** | **101** | **KEEP** |

## Deferred: MIXED categories (per-ID triage in Phase 3)

The remaining ~210 unmapped IDs in MIXED categories (`color`, `image`, `fonts`, `structure`, etc.) are Tier-1 supplements — additional checks within canonical families. These will be triaged during **Phase 3.1 profile completeness audit** when each check is mapped to the profiles that include it. Expected outcome: mostly keep, with 10-20 IDs renamed for clarity to align with gap-list taxonomy.

No code changes required for Phase 2 based on this triage.
