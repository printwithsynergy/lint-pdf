---
title: "AI FAQ"
description: "Frequently asked questions about LintPDF AI inspections."
---

# AI FAQ

## General

### What are AI credits?

AI credits are the billing unit for AI-powered inspections. Text-tier inspections (text analysis, barcode decode) cost 1 credit. Vision-tier inspections (vision models, regulatory compliance) cost 2 credits. Credits are purchased separately from your plan subscription.

### How do I enable AI features?

AI features are in invite-only alpha. Email sales@lintpdf.com with your account ID and use case. Once enabled, configure AI categories in the Dashboard under Settings > AI Inspections.

### Do AI features replace the core engine?

No. The core engine runs 250+ deterministic, rule-based checks and is not affected by AI features. AI inspections run alongside core engine checks and produce additional findings in the same Report. The `source` field distinguishes them.

### Which plans support AI features?

AI features are available on all paid plans: Starter, Growth, Scale, and Enterprise. Credits are purchased separately.

## Credits & Billing

### How much do AI inspections cost?

Text-tier inspections cost 1 credit ($0.12 pay-per-use, or less with volume packages starting at $0.10/credit). Vision-tier inspections cost 2 credits. See the pricing page for package options.

### Do credits expire?

No. Credits purchased through packages never expire. Pay-per-use credits are billed as consumed.

### What happens when I run out of credits?

AI inspections are skipped. Core engine checks continue normally. The Report includes an info noting which AI inspections were skipped. Configure the `ai.credits.depleted` Webhook to be notified.

### Can I set a spending limit?

Yes. For pay-per-use billing, set a monthly spending cap in Settings > AI Billing. When the cap is reached, AI inspections are skipped for the remainder of the billing cycle.

## Checks

### Why did my AI check fail?

Common reasons:

- **Insufficient credits**: Your credit balance was zero. Purchase credits or enable auto top-up.
- **Circuit breaker tripped**: Vision capacity was constrained. Vision inspections are temporarily skipped. Retry in a few minutes.
- **Category not enabled**: The AI category for the requested inspection is not enabled on your account. Enable it in Settings > AI Inspections.
- **File too large**: AI inspections have a 100MB file size limit. Files exceeding this limit skip AI processing.
- **Unsupported format**: Some AI inspections require rasterized page content. Heavily encrypted or malformed PDFs may not rasterize correctly.

### What is the circuit breaker?

Vision-tier inspections use a circuit breaker pattern for capacity management. When Vision infrastructure is at capacity, the circuit breaker trips and Vision inspections are gracefully skipped. Text inspections and core engine checks are unaffected. The circuit breaker automatically resets when capacity is available.

### How accurate are AI findings?

AI findings include a confidence score (0.0 to 1.0). Findings are only reported above a configurable minimum threshold (default 0.75). Regulatory compliance inspections typically have confidence scores above 0.90. The confidence threshold can be adjusted in Settings > AI Inspections.

### Can I adjust the confidence threshold?

Yes. Navigate to Settings > AI Inspections and set the minimum confidence threshold. Lower thresholds produce more findings but may include false positives. Higher thresholds reduce noise but may miss edge cases.

## Configuration

### How do I set up brand colors for palette checking?

Navigate to Settings > AI Brand > Color Palette. Add your approved colors as hex values. Set the Delta E tolerance (default 5). See the AI Brand Configuration guide for details.

### How do I upload reference logos?

Navigate to Settings > AI Brand > Logos. Upload reference versions of your logos (PNG, SVG, PDF, EPS). Upload multiple variations for best matching accuracy. See the AI Brand Configuration guide for details.

### Can I add words to the spell checker dictionary?

Yes. Navigate to Settings > AI Brand > Dictionary. Add brand names, product names, and technical terms. These words will not be flagged by the spell check inspection. See the AI Brand Configuration guide for limits by plan.

### How do I use AI presets in my Ruleset?

Include `ai_preset` in your Submit request or configure AI categories in a custom Ruleset. See the AI Rulesets guide for details.

## Technical

### What is the difference between Text and Vision tiers?

Text-tier inspections run text-based analysis (spell check, barcode decode, palette matching) with sub-second latency at 1 credit each. Vision-tier inspections run vision-based analysis (regulatory panels, logo matching, image quality) with 1-5 second latency at 2 credits each.

### Does AI processing affect my Submit latency?

AI inspections run in parallel with core engine checks. Text-tier inspections add minimal latency. Vision-tier inspections may add 1-5 seconds depending on complexity. The core engine portion of your Report is available as soon as core processing completes, even if AI inspections are still running.

### Are AI findings included in PDF reports?

Yes. AI findings appear in PDF, JSON, and XML reports alongside core engine findings. In PDF reports, AI findings are marked with an "AI" badge.

### Can I use AI features via the API only (no Dashboard)?

Yes. All AI features are available via the API. The Dashboard provides a UI for configuration, but everything can be done programmatically.
