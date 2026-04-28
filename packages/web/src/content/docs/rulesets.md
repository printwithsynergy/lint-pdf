---
title: "Rulesets"
description: "Built-in and custom Rulesets for LintPDF preflight profiles."
section: "core"
order: 5
---

# Rulesets

A Ruleset is a preflight profile — a collection of Checks and thresholds that define what LintPDF checks for. Every submission requires a Ruleset.

## Built-in Rulesets

| Ruleset      | Standard    | Checks | Use Case                                     |
| ------------ | ----------- | ------ | -------------------------------------------- |
| GWG Sheetfed | GWG 2022    | 196    | Commercial offset, sheetfed lithography      |
| GWG Digital  | GWG 2022    | 180    | Digital printing, wide-format, variable data |
| PDF/X-4      | ISO 15930-7 | 120    | ISO exchange standard, transparency support  |
| Packaging    | ISO 15416   | 210    | Packaging, labels, barcode grading           |

## Custom Rulesets

Growth, Scale, and Enterprise plans can create custom Rulesets. Start from a built-in base and override specific thresholds, enable or disable individual Checks, and name your profile for reuse across submissions.

## Rules editor

The dashboard ships a structured **Rules editor** at `/dashboard/rulesets` so you can audit and tune a profile's check list without hand-writing JSON.

Three tabs operate on the same profile:

- **Rules** — checks grouped by category (Image quality, Color, Fonts, Packaging, …). Each row exposes a severity dropdown (`error` / `warning` / `advisory` / `off`) and an enable toggle. Per-category bulk actions disable everything in the group or reset to catalog defaults; two profile-wide actions demote every active error to advisory or reset the whole profile.
- **JSON** — raw `PreflightProfile` JSON with live validation. Invalid payloads surface the parse error inline and keep the underlying profile untouched until you fix the syntax.
- **Diff** — every check whose effective state differs from the baseline profile, showing `was → now` severity chips. Makes it easy to review exactly what changed before saving.

The editor reads a generated catalog (`packages/app/lib/rules/check-catalog.json`) produced by `packages/engine/scripts/export_check_catalog.py`. The catalog pulls from the same `CHECK_NAMES` registry the reports and viewer use, so a new inspection_id added to the engine surfaces automatically in the editor on the next `pnpm catalog:generate` run. CI enforces drift via `pnpm catalog:check`.

A check's **default severity** is baked into the catalog (conformance + ICC checks default to `error`; most image, color, and print-production checks default to `warning`; everything else `advisory`). Overrides live in the profile's `checks.severity_overrides` block as `{ "LPDF_IMG_001": "error" }`; `"off"` there (or membership in `checks.disabled`) disables the check entirely.

## Engine mode only

Rulesets only apply when `preflight_source=engine`. In `external` mode the findings come pre-classified from your upstream preflight tool (PitStop, callas, Acrobat, or a native LintPDF payload); LintPDF does not re-run rule evaluation against those findings. In `minimal` mode no analyzers run at all. See [Preflight Modes](/docs/preflight-modes) for the full decision matrix.

