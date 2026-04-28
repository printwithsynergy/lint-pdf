---
title: "AI troubleshooting"
description: "FAQ, common errors, and the full error-code reference for AI inspections."
section: "ai"
order: 14
---

# AI troubleshooting

Everything that can go wrong with AI inspections, plus answers to the questions we get most often.

## FAQ

### General

#### What are AI credits?

AI credits are the billing unit for AI-powered inspections. Text-tier inspections (text analysis, barcode decode) cost 1 credit. Vision-tier inspections (vision models, regulatory compliance) cost 2 credits. Credits are purchased separately from your plan subscription.

#### How do I enable AI features?

AI features are in invite-only alpha. Email [sales@lintpdf.com](mailto:sales@lintpdf.com) with your account ID and use case. Once enabled, configure AI categories under **Settings → AI Inspections** in the dashboard.

#### Do AI features replace the core engine?

No. The core engine runs 500+ deterministic, rule-based checks plus the 91-check PDF/X-4 conformance suite (ISO 15930-7), and is not affected by AI features. AI inspections run alongside core engine checks and produce additional findings in the same report — the `source` field distinguishes them (`"engine"` vs. `"ai"`).

#### Which plans support AI features?

All paid plans: Starter, Growth, Scale, and Enterprise. Credits are purchased separately from your subscription.

### Credits & billing

#### How much do AI inspections cost?

Text-tier inspections cost 1 credit ($0.12 pay-per-use, or less with volume packages starting at $0.10/credit). Vision-tier inspections cost 2 credits. See the pricing page for package options.

#### Do credits expire?

No. Credits purchased through packages never expire. Pay-per-use credits are billed as consumed.

#### What happens when I run out of credits?

AI inspections are skipped. Core engine checks continue normally. The report includes an info note saying which AI inspections were skipped. Configure the `ai.credits.depleted` webhook to be notified.

#### Can I set a spending limit?

Yes. For pay-per-use billing, set a monthly cap under **Settings → AI Billing**. When the cap is reached, AI inspections are skipped for the remainder of the billing cycle.

### Checks

#### Why did my AI check fail?

Common reasons:

- **Insufficient credits** — balance was zero. Purchase credits or enable auto top-up.
- **Circuit breaker tripped** — vision capacity was constrained; retry in a few minutes.
- **Category not enabled** — enable under Settings → AI Inspections.
- **File too large** — AI has a 100 MB limit. Core engine checks still run.
- **Unsupported format** — some AI inspections require rasterised page content; encrypted or malformed PDFs may fail here.

#### What is the circuit breaker?

Vision-tier inspections use a circuit-breaker pattern. When vision infrastructure is at capacity the breaker trips and vision inspections are gracefully skipped. Text inspections and core engine checks are unaffected. The breaker auto-resets once capacity recovers.

#### How accurate are AI findings?

Every AI finding includes a confidence score (0.0–1.0). Findings are only reported above a configurable minimum threshold (default 0.75). Regulatory compliance inspections typically have confidence > 0.90. Adjust the threshold under Settings → AI Inspections.

#### Can I adjust the confidence threshold?

Yes — Settings → AI Inspections. Lower thresholds produce more findings but may include false positives. Higher thresholds reduce noise but may miss edge cases.

### Configuration

#### How do I set up brand colors?

Settings → AI Brand → Color Palette. Add hex values + set the Delta E tolerance (default 5). See [Brand config](./brand-config).

#### How do I upload reference logos?

Settings → AI Brand → Logos. Upload PNG, SVG, PDF, or EPS variations. More variations = better matching.

#### Can I add words to the spell-check dictionary?

Yes — Settings → AI Brand → Dictionary. Brand names, product names, and technical terms get exempted from the spell checker.

#### How do I use AI presets in a ruleset?

Include `ai_preset` in your submit request or configure AI categories in a custom ruleset. See [Presets](./presets).

### Technical

#### Text vs. vision tier?

Text-tier runs text analysis (spell check, barcode decode, palette matching) with sub-second latency at 1 credit each. Vision-tier runs vision-based analysis (regulatory panels, logo matching, image quality) with 1–5 s latency at 2 credits each.

#### Does AI processing affect submit latency?

AI inspections run in parallel with core engine checks. Text-tier adds minimal latency; vision-tier may add 1–5 s. The core engine portion of your report is available as soon as core processing completes, even if AI inspections are still running.

#### Are AI findings in PDF reports?

Yes. AI findings appear in PDF, JSON, and HTML reports alongside core engine findings. In PDF reports they carry an "AI" badge.

#### Can I use AI via API only?

Yes. All AI features are available via the API. The dashboard is just a UI for configuration.

---

## Error code reference

AI-specific error codes that may appear in API responses or report info notes.

| Error code                | What it means                                                            | Resolution                                                         |
| ------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `ai.credits.insufficient` | Credit balance is zero or insufficient for the requested inspections    | Purchase credits or enable auto top-up                             |
| `ai.credits.depleted`     | Credits ran out mid-processing — some inspections were skipped          | Top up credits; skipped inspections noted in the report            |
| `ai.circuit_breaker.open` | Vision capacity constrained — vision inspections temporarily unavailable | Retry in a few minutes; text inspections unaffected                |
| `ai.category.disabled`    | Requested AI category is not enabled on this account                     | Enable under Settings → AI Inspections                             |
| `ai.not_enabled`          | AI features are not enabled on this account                              | Request access via [sales@lintpdf.com](mailto:sales@lintpdf.com)   |
| `ai.preset.not_found`     | The specified preset ID does not exist                                   | `GET /api/v1/ai/presets` to list valid presets                     |
| `ai.file.too_large`       | File exceeds the 100 MB AI limit                                         | Reduce file size; core engine checks still run                     |
| `ai.rasterization.failed` | Page could not be rasterised for a vision-based inspection               | Check for encryption, malformed structure, or unsupported features |
| `ai.brand.no_palette`     | Brand palette inspection requested but no palette configured             | Configure under Settings → AI Brand                                |
| `ai.brand.no_logos`       | Logo matching requested but no reference logos uploaded                  | Upload under Settings → AI Brand                                   |
| `ai.model.timeout`        | AI model processing exceeded timeout threshold                           | Retry; if persistent, contact support                              |

## Related

- [AI overview](./overview) — setup walkthrough
- [Credits](./credits) — billing model
- [Monitoring](./monitoring) — usage dashboards
