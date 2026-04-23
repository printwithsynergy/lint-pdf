---
title: "Entitlements & AI Feature Grants"
description: "Per-feature AI grants, the master kill-switch, monthly spend caps, and the resolver merge order."
section: "platform"
order: 70
---

# Entitlements & AI Feature Grants

LintPDF's AI features — audit, OCR, dieline detection, art-size measurement, legend-vs-art swatch classification, similarity embedding, Sonnet fallback routing, and the internal Opus red-team — are each gated individually. A tenant has access to a feature only when **both**:

1. The master `ai_enabled` switch is on, AND
2. The feature name appears in the tenant's effective `ai_features` list.

This is the **AND-gate**: one without the other means no call fires.

## The eight flags

| Flag | What it enables |
|---|---|
| `audit` | Per-finding AI verdicts on every preflight ([AI Accuracy Audit](./ai-audit)). |
| `ocr` | Claude vision OCR for outlined PDFs — recovers a text layer when `< 5` chars are extractable per page. |
| `dieline` | Dieline detection — name-match first (`CutContour`, `Dieline`, etc.), Sonnet fallback when `sonnet_fallback` is also granted. |
| `art_size` | Trim-size measurement from the dieline centerline. Requires `dieline`. |
| `legend` | Legend-vs-art swatch classification. Position-based when the dieline is known; Sonnet fallback on ambiguity. |
| `similarity` | OpenCLIP image embedding for the duplicate-detector inspector (runs on Modal). |
| `sonnet_fallback` | Opts the tenant into Sonnet 4.6 visual reasoning when the name-match or position heuristics can't decide. Every feature that can fall back to Sonnet respects this flag. |
| `internal_opus` | Internal Opus 4.7 red-team pass. Admin-only, manually triggered from `/dashboard/admin/health`. Never touches the customer request path. |

## Plan baselines

| Plan | `ai_features` floor |
|---|---|
| Free / Viewer / Starter | *(empty — no AI)* |
| Growth | `["audit"]` |
| Scale | `["audit", "ocr", "dieline", "art_size", "legend"]` |
| Enterprise | Scale + `["similarity", "sonnet_fallback"]` |

Admins can grant additional flags per-tenant at `/dashboard/admin/tenants/[id]`. Per-tenant grants **union** with the plan baseline — a plan-tier flag is never silently stripped.

## Resolver merge order

Effective entitlements are the union of four layers, applied in this order:

1. `PLAN_LIMITS[tenant.plan]` — hardcoded baseline
2. `plan_limit_overrides[plan].ai_features` — ops-editable plan-wide override
3. `tenant.entitlement_overrides.ai_features` — legacy JSON blob
4. `tenant.ai_features` — dedicated per-tenant column

Missing flag = off. Unknown flag names are silently dropped by the resolver (and rejected at the admin PATCH schema), so a typo at a call site never accidentally allows an AI call.

## Monthly spend cap

`monthly_ai_credits` is a per-tenant cap in **integer cents** (`500` = $5.00). Cost accrues from every Claude call — each logged to `ai_usage_logs` with the model, input/output/cache token breakdown, and cost in cents. Sub-cent calls (common for cached Haiku turns) round **up** to 1 cent so quota math stays truthful.

When a tenant hits their cap mid-month:

- **Non-AI preflight keeps running** — no 402, no job rejection.
- AI features no-op silently.
- One `LPDF_AI_QUOTA_EXCEEDED` warning is attached to the job so the viewer can surface the cap hit.
- The cap resets at the first of the next calendar month (UTC).

## Feature-locked findings

When a job needs a feature the tenant doesn't have, the engine skips the AI call and emits one `LPDF_FEATURE_LOCKED` informational finding per locked feature. The viewer renders these as an upsell chip — customers see exactly which AI features would fire on this PDF if they upgraded or asked an admin to grant access.

The finding is idempotent per `(job, feature)` — rerunning audit won't duplicate the chip.

## Admin controls

Every grant, cap, and override is editable live from the admin dashboard:

- `/dashboard/admin/tenants/[id]` — per-tenant grants + `ai_enabled` master switch + `monthly_ai_credits_override`
- `/dashboard/admin/plans/[plan]` — plan-wide `ai_features` + cap defaults
- `/dashboard/admin/ai/usage` — per-tenant × feature × month spend rollup with CSV export
- `/dashboard/admin/health` — Claude probe, outage-banner override, Opus audit on any job, golden-corpus benchmark runner
