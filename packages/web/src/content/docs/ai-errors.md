---
title: "AI Errors"
description: "AI-specific error codes that may appear in API responses or Report info notes."
section: "ai"
order: 13
---

# AI Error Reference

AI-specific error codes that may appear in API responses or Report info notes.

| Error Code                | Description                                                              | Resolution                                                         |
| ------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `ai.credits.insufficient` | Credit balance is zero or insufficient for requested inspections         | Purchase credits or enable auto top-up                             |
| `ai.credits.depleted`     | Credits ran out during processing — some inspections were skipped        | Top up credits; skipped inspections noted in Report                |
| `ai.circuit_breaker.open` | Vision capacity constrained — Vision inspections temporarily unavailable | Retry in a few minutes; Text inspections unaffected                |
| `ai.category.disabled`    | Requested AI category is not enabled on this account                     | Enable the category in Settings > AI Inspections                   |
| `ai.not_enabled`          | AI features are not enabled on this account                              | Request access via sales@lintpdf.com                               |
| `ai.preset.not_found`     | The specified AI preset ID does not exist                                | Use GET /api/v1/ai/presets to list valid presets                   |
| `ai.file.too_large`       | File exceeds 100MB limit for AI processing                               | Reduce file size; core engine checks still run                     |
| `ai.rasterization.failed` | Page could not be rasterized for vision-based inspection                 | Check for encryption, malformed structure, or unsupported features |
| `ai.brand.no_palette`     | Brand palette inspection requested but no palette configured             | Configure brand palette in Settings > AI Brand                     |
| `ai.brand.no_logos`       | Logo matching requested but no reference logos uploaded                  | Upload reference logos in Settings > AI Brand                      |
| `ai.model.timeout`        | AI model processing exceeded timeout threshold                           | Retry; if persistent, contact support                              |
