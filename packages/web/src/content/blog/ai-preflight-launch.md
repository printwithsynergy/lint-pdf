---
title: "Introducing AI-Powered Preflight: 33 New Checks for LintPDF"
date: "2026-03-16"
author: "Think Neverland"
category: "Product Updates"
excerpt: "LintPDF adds 33 AI checks across 14 categories — barcode detection, regulatory compliance, content quality, image analysis, logo verification, and more. Invite-only alpha, credit-based, same Report format."
tags: ["launch", "ai", "product"]
---

Today we are launching AI-powered preflight checks for LintPDF. This adds 33 new checks across 14 categories — barcode detection, content quality, file comparison, color compliance, trend analysis, dieline detection, regulatory compliance, image analysis, document classification, logo verification, spatial analysis, NLP interfaces, text analysis, and symbol detection.

## What AI Adds (and What It Does Not Replace)

The core LintPDF engine runs 250+ deterministic, rule-based checks. Fonts, color spaces, images, transparency, page geometry, barcodes, PDF/X compliance — these checks are fast, precise, and reproducible. They are not going anywhere.

AI checks handle the things rules cannot: "Does this nutrition panel follow FDA ordering requirements?" "Is this logo the correct version?" "Are the GHS pictograms large enough?" These are visual, contextual, and semantic questions that require a different kind of analysis.

AI findings appear in the same Report as core engine findings. The `source: "ai"` field distinguishes them, so you can filter, route, or display them however you need.

## The 14 Categories

The 33 AI checks are organized into 14 categories across two processing tiers:

### Text Tier (1 credit, sub-second latency)

- **Barcode Detection (7)** — Decode verification, QR validation, barcode dimensions, pharma serialization, content validation, QR human readable matching, barcode+QR content match.
- **Content Quality (3)** — Spell checking with custom dictionaries, language detection, duplicate/near-duplicate submission detection.
- **File Comparison (1)** — Visual and structural diff between file versions to catch unintended changes.
- **Color Compliance (2)** — Brand palette validation against uploaded color definitions, WCAG text contrast ratio checking.
- **Trend Analysis (1)** — Statistical process control tracking of submission quality over time.
- **Dieline Detection (1)** — Detect dieline layers by naming convention and validate structure.
- **Regulatory Compliance (4)** — FDA nutrition facts (21 CFR 101.9), EU FIR 1169/2011, GHS CLP 1272/2008, pharma font compliance.

### Vision Tier (2 credits, 1-5 second latency)

- **Image Analysis (3)** — Visual quality assessment, NSFW content screening, image similarity detection.
- **Document Classification (2)** — Automatic file type classification, optimal Ruleset suggestion.
- **Logo Verification (1)** — Match detected logos against uploaded brand reference files.
- **Spatial Analysis (1)** — Safe zone violation detection relative to trim, fold, and perforation zones.
- **NLP Interfaces (2)** — Natural language Ruleset creation, plain-English Report interpretation.
- **Text Analysis (2)** — Multi-language translation, text-as-outlines detection.
- **Symbol Detection (2)** — Regulatory symbol identification, processing step fallback detection.

## Invite-Only Alpha

AI features are launching as an invite-only alpha. We are onboarding accounts individually to ensure quality, gather feedback, and tune our models against real-world packaging artwork.

If you are interested, email [sales@lintpdf.com](mailto:sales@lintpdf.com) with a brief description of your use case. We prioritize accounts with active regulatory compliance needs (food, chemical, pharmaceutical packaging).

## Credit-Based Billing

Core preflight checks remain unlimited on paid plans. AI checks are metered separately using a credit system:

- **Text-tier checks** (text analysis, barcode decode, spell check): 1 credit each
- **Vision-tier checks** (vision models, regulatory panel detection, logo matching): 2 credits each

Credits can be purchased pay-per-use at $0.12/credit or in volume packages:

| Package | Credits | Price | Per Credit |
|---------|---------|-------|------------|
| Starter | 100 | $10 | $0.10 |
| Growth | 500 | $40 | $0.08 |
| Scale | 2,000 | $120 | $0.06 |
| Enterprise | 10,000 | $500 | $0.05 |

Credits never expire. Credit balance is visible in the Dashboard and exposed via the API. You can set low-balance alerts via Webhooks.

## Seven Pre-Built Presets

We have created seven curated AI presets for common use cases:

1. **fda-food-label** — 21 CFR 101.9 nutrition panel validation with barcode and content checks
2. **eu-food-label** — Regulation 1169/2011 compliance including allergen emphasis and x-height
3. **pharma-eu** — EU FMD serialization, Braille placeholder, and font compliance
4. **ghs-chemical** — CLP 1272/2008 pictogram detection, signal words, and H/P statements
5. **packaging-qc** — Barcode grading, dieline detection, safe zones, and image quality
6. **brand-compliance** — Logo verification, brand palette enforcement, and spell checking
7. **full-ai-scan** — All 33 checks across every category

Select a preset in your submission request or build custom combinations in your Ruleset.

## Technical Highlights

**Text vs Vision tiers.** Text-based checks (barcode decode, spell check, language detection, palette matching) run on CPU infrastructure with sub-second latency. Vision-based checks (regulatory panel analysis, logo matching, NSFW detection) run on GPU infrastructure with 1-5 second latency.

**Circuit breaker.** Vision-tier checks have a circuit breaker that gracefully degrades when GPU capacity is constrained. If the circuit breaker trips, Vision checks are skipped and the Report includes an info noting which checks were not run. Text checks and core engine checks are unaffected.

**Same Report format.** AI findings use the same structure as core engine findings — `inspection_id`, `severity`, `message`, `page`. The additional `source: "ai"`, `category`, `confidence`, and `credits_consumed` fields are added for AI-specific metadata.

**Tenant-scoped.** AI features are scoped to your tenant. Brand palettes, reference logos, custom dictionaries, and credit balances are all isolated to your account. Admin operations use the `X-Admin-Key` header.

## How to Request Access

1. Email [sales@lintpdf.com](mailto:sales@lintpdf.com) with your account ID and use case.
2. We enable AI features on your account and provision an initial credit balance.
3. Configure your AI categories in the Dashboard or via the API.
4. Submit a file with `ai_preset` or `ai_categories` to run AI checks.

AI features are available on all paid plans (Starter, Growth, Scale, Enterprise). Credits are purchased separately from your plan subscription.

We are building AI preflight the way we built the core engine: detection-only, API-first, and obsessively precise. No hype. Just checks that catch what rules alone cannot.
