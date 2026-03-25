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
